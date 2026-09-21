"""Raw data attached to a figure or a table.

The point of this module is that the deposition set is assembled continuously
rather than the night before submission. A file attached to Figure 1 is copied
into `data/figure-01/`, hashed, and recorded; MANIFEST.csv and README.md are
regenerated from the record every time it changes.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from . import layout
from .safety import safe_name
from .workspace import Workspace

__all__ = ["Attachment", "attach_bytes", "attach_file", "manifest_csv",
           "readme_markdown", "data_availability_statement", "rewrite_manifest"]

_CHUNK = 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Attachment:
    id: str
    name: str
    bytes: int
    type: str
    target: str          # figure or table ref, e.g. "F1" / "T1"
    rel_path: str        # relative to the document root
    sha256: str
    added_at: str
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def attach_bytes(ws: Workspace, document: dict, target_ref: str, name: str,
                 data: bytes, attachment_id: str, content_type: str = "",
                 note: str = "") -> Attachment:
    """File raw data that arrived as bytes (an upload from the interface)."""
    rel_dir = layout.attachment_dir(document, target_ref)
    filename = safe_name(name)
    result = ws.write_bytes(f"{rel_dir}/{filename}", data)
    return Attachment(
        id=attachment_id,
        name=filename,
        bytes=result.bytes_written,
        type=content_type or "application/octet-stream",
        target=target_ref,
        rel_path=f"{rel_dir}/{filename}",
        sha256=hashlib.sha256(data).hexdigest(),
        added_at=_now(),
        note=note,
    )


def attach_file(ws: Workspace, document: dict, target_ref: str, source: Path,
                attachment_id: str, content_type: str = "", note: str = "") -> Attachment:
    """File raw data that is already on this machine, without loading it all."""
    rel_dir = layout.attachment_dir(document, target_ref)
    result = ws.copy_in(Path(source), rel_dir)
    rel_path = f"{rel_dir}/{result.path.name}"
    return Attachment(
        id=attachment_id,
        name=result.path.name,
        bytes=result.bytes_written,
        type=content_type or "application/octet-stream",
        target=target_ref,
        rel_path=rel_path,
        sha256=_sha256_of(result.path),
        added_at=_now(),
        note=note,
    )


def _label_for(document: dict, ref: str) -> str:
    for i, f in enumerate(document.get("figures") or [], start=1):
        if f.get("ref") == ref:
            return f"Figure {i}"
    for i, t in enumerate(document.get("tables") or [], start=1):
        if t.get("ref") == ref:
            return f"Table {i}"
    return "Unassigned"


def manifest_csv(document: dict, attachments: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["file", "supports", "bytes", "sha256", "content_type", "added", "description"])
    for a in attachments:
        w.writerow([
            a.get("rel_path") or a.get("name", ""),
            _label_for(document, a.get("target", "")),
            a.get("bytes", 0),
            a.get("sha256", ""),
            a.get("type", ""),
            a.get("added_at", ""),
            a.get("note", ""),
        ])
    return buf.getvalue()


def _human(n: int) -> str:
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.0f} KB"
    return f"{n} B"


def readme_markdown(document: dict, attachments: list[dict]) -> str:
    title = document.get("title", "Untitled")
    authors = ", ".join(a.get("name", "") for a in document.get("authors") or [])
    total = sum(int(a.get("bytes", 0)) for a in attachments)
    groups: dict[str, list[dict]] = {}
    for a in attachments:
        groups.setdefault(_label_for(document, a.get("target", "")), []).append(a)

    lines = [
        f"# Data for: {title}",
        "",
        f"Authors: {authors}" if authors else "",
        "",
        f"This deposit contains {len(attachments)} file(s), {_human(total)} in total, "
        "supporting the figures and tables listed below. Checksums are in `MANIFEST.csv`.",
        "",
    ]
    for label in sorted(groups):
        lines.append(f"## {label}")
        lines.append("")
        for a in groups[label]:
            note = f" — {a['note']}" if a.get("note") else ""
            lines.append(f"- `{a.get('rel_path', a.get('name', ''))}` "
                         f"({_human(int(a.get('bytes', 0)))}){note}")
        lines.append("")
    lines += [
        "## Provenance",
        "",
        f"Generated by GerbilDocs on {_now()}.",
        "",
    ]
    return "\n".join(x for x in lines if x is not None)


def data_availability_statement(document: dict, attachments: list[dict]) -> str:
    if not attachments:
        return ("Attach raw data to a figure or table and this statement is written "
                "from the deposit.")
    repo = document.get("repo") or "[repository]"
    doi = document.get("datasetDoi") or "[DOI to be minted on acceptance]"
    total = sum(int(a.get("bytes", 0)) for a in attachments)
    groups: dict[str, list[dict]] = {}
    for a in attachments:
        groups.setdefault(_label_for(document, a.get("target", "")), []).append(a)
    keys = sorted(groups)
    listed = keys[0] if len(keys) == 1 else ", ".join(keys[:-1]) + " and " + keys[-1]
    detail = "; ".join(f"{k}: {', '.join(a.get('name', '') for a in groups[k])}" for k in keys)
    return (f"The data underpinning this study are openly available from {repo} at {doi}. "
            f"The deposit comprises {len(attachments)} files ({_human(total)}) supporting "
            f"{listed} — {detail}.")


def rewrite_manifest(ws: Workspace, document: dict, attachments: list[dict]) -> dict:
    """Regenerate MANIFEST.csv and README.md. Call after any attachment change."""
    ws.write_text("data/MANIFEST.csv", manifest_csv(document, attachments))
    ws.write_text("data/README.md", readme_markdown(document, attachments))
    return {
        "files": len(attachments),
        "bytes": sum(int(a.get("bytes", 0)) for a in attachments),
        "statement": data_availability_statement(document, attachments),
    }
