"""Application configuration and the profile.

Nothing installation-specific belongs in a module (ADR-W11). Branding and the
default documents folder live in `profile.json`, which anyone running their
own copy can replace without touching code.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

__all__ = ["AppPaths", "Profile", "FacilityProfile", "Settings", "load_settings"]

APP_NAME = "GerbilDocs"
APP_DIRNAME = "GerbilDocs"

# The names this application (and its predecessor) used to use. If the new
# app-data folder does not exist yet but an old one does, it is picked up
# automatically — see `_app_data_dir()`.
_LEGACY_APP_DIRNAMES = ("HarwellXPS Document Desk",)
_LEGACY_LINUX_DIRNAME = "harwellxps-document-desk"
_LEGACY_DOCUMENTS_DIRNAME = "HarwellXPS"


def _migrate_dir(new: Path, legacy_names: tuple[str, ...]) -> Path:
    """One-time rename of an old app-data folder to the new name.

    If `new` already exists, nothing to do. Otherwise, if a folder under any
    of `legacy_names` (same parent) exists, rename it in place. If the rename
    fails for any reason (permissions, cross-device, …) fall back to using the
    old path as-is rather than losing anything."""
    if new.exists():
        return new
    for name in legacy_names:
        old = new.parent / name
        if old.exists():
            try:
                os.rename(old, new)
                return new
            except OSError:
                return old
    return new


def _app_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return _migrate_dir(Path(base) / APP_DIRNAME, _LEGACY_APP_DIRNAMES)
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
        return _migrate_dir(base / APP_DIRNAME, _LEGACY_APP_DIRNAMES)
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return _migrate_dir(Path(base) / "gerbildocs", (_LEGACY_LINUX_DIRNAME,))


def _default_documents_dir() -> Path:
    new = Path.home() / "Documents" / "GerbilDocs"
    if new.exists():
        return new
    old = Path.home() / "Documents" / _LEGACY_DOCUMENTS_DIRNAME
    if old.exists():
        return old  # user documents are never renamed automatically
    return new


@dataclass
class AppPaths:
    """Where the installation keeps its own things.

    `documents` is the default parent folder for new documents; each document
    gets its own folder inside it. `library` mirrors the app-level collections
    to disk as readable JSON alongside the SQLite store, so the library is
    recoverable with a text editor if the store is ever lost.
    """
    root: Path
    store: Path
    library: Path
    documents: Path
    logs: Path

    @classmethod
    def default(cls, root: Path | None = None) -> "AppPaths":
        r = Path(root) if root else _app_data_dir()
        return cls(
            root=r,
            store=r / "desk.sqlite",
            library=r / "library",
            documents=_default_documents_dir(),
            logs=r / "logs",
        )

    def ensure(self) -> "AppPaths":
        for p in (self.root, self.library, self.documents, self.logs):
            p.mkdir(parents=True, exist_ok=True)
        return self


@dataclass
class Profile:
    name: str = "GerbilDocs"
    long_name: str = "GerbilDocs — papers, reports and grants"
    credit: str = "Created by Dr Mark Isaacs"
    colours: dict = field(default_factory=lambda: {
        "brand": "#175FFF", "spark": "#23F9FF", "ink": "#000000", "paper": "#FFFFFF",
    })
    support_url: str = "https://ko-fi.com/markisaacschem"
    support_label: str = "Buy me a coffee"
    licence: str = "MIT"
    author: str = "Dr Mark Isaacs"
    default_repository: str = ""
    enabled_document_kinds: list = field(default_factory=lambda: ["publication", "report", "grant"])

    @classmethod
    def load(cls, path: Path) -> "Profile":
        """The installation's own settings, or the defaults.

        A profile that cannot be read is reported and ignored. It is a handful
        of cosmetic strings; refusing to start the application over one — which
        is what an uncaught JSONDecodeError here does — is out of all
        proportion. The file is left alone, not repaired or renamed: it is the
        user's, and they may want to fix it themselves.
        """
        if not Path(path).exists():
            return cls()
        try:
            # utf-8-sig, not utf-8: a profile.json edited in Notepad or written
            # by PowerShell carries a byte-order mark, and json.loads refuses
            # it. utf-8-sig strips a BOM if present and is identical to utf-8
            # otherwise.
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("expected an object")
        except (OSError, ValueError) as exc:
            print(f"{path} could not be read ({exc}); using the default profile.",
                  file=sys.stderr)
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        try:
            return cls(**known)
        except TypeError as exc:
            print(f"{path} holds unusable values ({exc}); using the default profile.",
                  file=sys.stderr)
            return cls()

    def save(self, path: Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


# Old name, kept as an alias so anything importing `FacilityProfile` still works.
FacilityProfile = Profile


@dataclass
class Settings:
    paths: AppPaths
    profile: Profile
    token: str
    edition: str = "desktop"
    host: str = "127.0.0.1"
    port: int = 0  # 0 = pick a free one at launch

    @property
    def static_dir(self) -> Path:
        # PyInstaller unpacks bundled data to sys._MEIPASS.
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / "static"


def load_settings(root: Path | None = None, token: str | None = None) -> Settings:
    paths = AppPaths.default(root).ensure()
    profile_path = paths.root / "profile.json"
    profile = Profile.load(profile_path)
    if not profile_path.exists():
        profile.save(profile_path)
    return Settings(
        paths=paths,
        profile=profile,
        token=token or os.environ.get("DESK_TOKEN") or secrets.token_urlsafe(32),
        host=os.environ.get("DESK_HOST", "127.0.0.1"),
        port=int(os.environ.get("DESK_PORT", "0")),
    )
