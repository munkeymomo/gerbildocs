"""Path safety.

Everything the application writes goes through `resolve_within`. A request may
name a path relative to a document root; it may never escape that root, whether
by `..`, an absolute path, or a symlink.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["PathEscape", "resolve_within", "safe_name"]


class PathEscape(ValueError):
    """A requested path resolved outside the root it was given."""


def resolve_within(root: Path, relative: str) -> Path:
    """Resolve `relative` under `root`, refusing anything that escapes it.

    `root` need not exist yet; its parents are resolved so symlinked temporary
    directories (macOS `/var` -> `/private/var`) do not trip the check.
    """
    if relative is None:
        raise PathEscape("no path given")
    rel = str(relative).replace("\\", "/").strip()
    if not rel:
        raise PathEscape("empty path")
    if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
        raise PathEscape(f"absolute paths are not accepted: {relative!r}")

    root_abs = Path(os.path.realpath(root))
    target = Path(os.path.realpath(root_abs / rel))
    try:
        target.relative_to(root_abs)
    except ValueError as exc:  # pragma: no cover - message only
        raise PathEscape(f"{relative!r} escapes the document folder") from exc
    return target


_BAD = '<>:"|?*\0'


def safe_name(name: str, fallback: str = "file") -> str:
    """A single filename component, safe on Windows and POSIX alike."""
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    cleaned = "".join("_" if c in _BAD or ord(c) < 32 else c for c in base).strip(" .")
    # Windows reserves these regardless of extension.
    stem = cleaned.split(".", 1)[0].upper()
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10))}
    if stem in reserved:
        cleaned = "_" + cleaned
    return cleaned[:180] or fallback
