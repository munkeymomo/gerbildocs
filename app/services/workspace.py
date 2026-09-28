"""Creating and writing into a document's folder.

The browser edition has no filesystem; this module is the whole of what the
desktop edition adds. It creates the folder a document lives in, writes exports
and drafts into it, and is the only place that touches user files.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import layout
from .safety import resolve_within, safe_name

__all__ = ["Workspace", "WriteResult", "DocumentFolder", "NotADocumentFolder", "discover",
           "discover_tree", "FolderNode"]

DOCUMENT_FILE_FORMAT = 1

# The marker this application stamps into every `document.json`. A folder
# carrying it is one of ours, whatever else the state does or does not contain.
APP_STAMP = "GerbilDocs"

# Stamps written by earlier releases of this application (or its predecessor
# under its old name). A folder stamped with any of these is still recognised.
LEGACY_STAMPS = ("HarwellXPS Document Desk",)


class NotADocumentFolder(ValueError):
    """The folder has no readable `document.json`."""


@dataclass(frozen=True)
class DocumentFolder:
    """What `document.json` says about the folder it is in."""
    root: Path
    title: str
    kind: str
    saved_at: str
    state: dict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class WriteResult:
    path: Path
    bytes_written: int
    created: bool


class Workspace:
    """A document folder on disk."""

    def __init__(self, root: Path):
        self.root = Path(root)

    # -- creation -----------------------------------------------------------

    @classmethod
    def create(cls, base_dir: Path, title: str, kind: str = "publication") -> "Workspace":
        """Make `<base_dir>/<slug of title>/`, uniquified if it already exists."""
        base = Path(base_dir)
        base.mkdir(parents=True, exist_ok=True)
        name = layout.document_root_name(title)
        root = base / name
        n = 2
        while root.exists():
            root = base / f"{name}-{n}"
            n += 1
        root.mkdir(parents=True)
        ws = cls(root)
        ws.ensure_tree({"kind": kind})
        return ws

    def ensure_tree(self, document: dict) -> list[str]:
        """Create every folder the document's layout calls for. Idempotent."""
        made: list[str] = []
        for rel in layout.directories(document):
            target = resolve_within(self.root, rel)
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
                made.append(rel)
        return made

    # -- writing ------------------------------------------------------------

    def write_bytes(self, relative: str, data: bytes) -> WriteResult:
        target = resolve_within(self.root, relative)
        existed = target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return WriteResult(target, len(data), created=not existed)

    def write_text(self, relative: str, text: str) -> WriteResult:
        return self.write_bytes(relative, text.encode("utf-8"))

    def write_json(self, relative: str, obj) -> WriteResult:
        return self.write_text(relative, json.dumps(obj, indent=2, ensure_ascii=False))

    def copy_in(self, source: Path, relative_dir: str, name: str | None = None) -> WriteResult:
        """Copy a file from anywhere on disk into the document folder."""
        src = Path(source)
        target_dir = resolve_within(self.root, relative_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_name(name or src.name)
        existed = target.exists()
        shutil.copy2(src, target)
        return WriteResult(target, target.stat().st_size, created=not existed)

    # -- reading ------------------------------------------------------------

    def read_bytes(self, relative: str) -> bytes:
        return resolve_within(self.root, relative).read_bytes()

    def exists(self, relative: str) -> bool:
        try:
            return resolve_within(self.root, relative).exists()
        except Exception:
            return False

    def tree(self, document: dict) -> list[dict]:
        """The planned layout, annotated with what is actually on disk."""
        out = []
        for planned in layout.plan_document(document):
            try:
                target = resolve_within(self.root, planned.path)
                present = target.exists()
                size = target.stat().st_size if present and target.is_file() else None
            except Exception:
                present, size = False, None
            out.append({
                "path": planned.path,
                "kind": planned.kind,
                "note": planned.note,
                "generated": planned.generated,
                "present": present,
                "bytes": size,
            })
        return out

    # -- the document itself ------------------------------------------------

    def write_document_state(self, document: dict) -> WriteResult:
        """Mirror the document-scoped state into `document.json`.

        `document` is the vault's half of the state: the library (references,
        samples, styles…) is app-scoped and is not in here. Written whole to a
        temporary name and swapped in, so a crash mid-write leaves the previous
        copy rather than half of the new one."""
        payload = {
            "app": APP_STAMP,
            "format": DOCUMENT_FILE_FORMAT,
            "saved_at": _now(),
            "title": document.get("title", ""),
            "kind": document.get("kind", "publication"),
            "state": document,
        }
        final = resolve_within(self.root, layout.DOCUMENT_FILE)
        tmp = resolve_within(self.root, "." + layout.DOCUMENT_FILE + ".tmp")
        final.parent.mkdir(parents=True, exist_ok=True)
        existed = final.exists()
        text = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        tmp.write_bytes(text)
        os.replace(tmp, final)
        return WriteResult(final, len(text), created=not existed)

    @classmethod
    def read_document_folder(cls, root: Path) -> DocumentFolder:
        """Read a folder's `document.json`. Raises NotADocumentFolder if it is
        missing or unreadable; never creates anything."""
        r = Path(root)
        f = r / layout.DOCUMENT_FILE
        if not r.is_dir():
            raise NotADocumentFolder(f"{r} is not a folder")
        if not f.is_file():
            raise NotADocumentFolder(f"{r} has no {layout.DOCUMENT_FILE}")
        try:
            # utf-8-sig tolerates a byte-order mark on a document.json that has
            # been through an editor; it reads plain utf-8 unchanged.
            data = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise NotADocumentFolder(f"{f} could not be read: {exc}") from exc
        state = data.get("state") if isinstance(data, dict) else None
        if not isinstance(state, dict):
            raise NotADocumentFolder(f"{f} is not a GerbilDocs document")
        # Identity comes from the envelope this application writes, not from a
        # key the interface happens to add. A document created through the API
        # and not yet opened in the interface has no `subdocs`, and used to be
        # unrecognisable here — which made it undiscoverable and unadoptable.
        stamped = isinstance(data, dict) and data.get("app") in (APP_STAMP,) + LEGACY_STAMPS
        if not stamped and "subdocs" not in state:
            raise NotADocumentFolder(f"{f} is not a GerbilDocs document")
        return DocumentFolder(
            root=r,
            title=str(data.get("title") or state.get("title") or r.name),
            kind=str(data.get("kind") or state.get("kind") or "publication"),
            saved_at=str(data.get("saved_at") or ""),
            state=state,
        )

    # -- drafts -------------------------------------------------------------

    def write_revision(self, index: int, revision: dict) -> WriteResult:
        rel = f"drafts/rev-{layout.pad2(index)}-{layout.slug(revision.get('label', 'revision'))}.json"
        payload = dict(revision)
        payload.setdefault("written_at", _now())
        return self.write_json(rel, payload)


def discover(base_dir: Path) -> list[DocumentFolder]:
    """Every immediate sub-folder of `base_dir` that holds a readable document,
    newest save first. Reads only; finds folders the vault does not know."""
    base = Path(base_dir)
    if not base.is_dir():
        return []
    found: list[DocumentFolder] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        try:
            found.append(Workspace.read_document_folder(child))
        except NotADocumentFolder:
            continue
    found.sort(key=lambda d: d.saved_at, reverse=True)
    return found


@dataclass
class FolderNode:
    """One folder in a library tree: the documents directly in it, and the
    sub-folders worth showing (those that hold a document somewhere below)."""
    name: str
    path: Path
    documents: list[DocumentFolder] = field(default_factory=list)
    children: list["FolderNode"] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.documents) + sum(c.total for c in self.children)


_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "$RECYCLE.BIN",
              "System Volume Information"}


def discover_tree(base_dir: Path, depth: int = 4) -> FolderNode:
    """Walk `base_dir` up to `depth` levels for document folders.

    A document folder is a leaf: its own sub-folders (figures/, data/…) are
    never walked. Hidden folders and the usual tool folders are skipped. Empty
    branches are pruned, so the tree the picker draws only has folders with a
    document somewhere below. Reads only."""
    base = Path(base_dir)
    node = FolderNode(name=base.name or str(base), path=base)
    if not base.is_dir() or depth < 0:
        return node
    try:
        children = sorted(base.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return node
    for child in children:
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in _SKIP_DIRS:
            continue
        try:
            node.documents.append(Workspace.read_document_folder(child))
            continue
        except NotADocumentFolder:
            pass
        if depth > 0:
            sub = discover_tree(child, depth - 1)
            if sub.total:
                node.children.append(sub)
    node.documents.sort(key=lambda d: d.saved_at, reverse=True)
    return node
