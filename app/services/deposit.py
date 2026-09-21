"""Compiling a document's folder into something you could deposit for a DOI.

The interface knows how to draw a figure, a table, a plot and an equation; the
backend knows where each of those belongs. So the interface renders, hands the
result over, and this module files it — every write through the `Workspace`, at
the path `layout.py` planned, and nowhere else.

What comes in is deliberately dumb: strings and base64, no objects. What goes
out is a summary the interface can show without asking again.

Standard library only, like everything else under `app/services/`.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any

from . import layout
from .workspace import Workspace

__all__ = ["compile_deposit", "deposit_markdown"]

# What each kind of generated file is for, in the words DEPOSIT.md uses.
ROLE_FIGURE_SVG = "figure {ref} (vector)"
ROLE_FIGURE_PNG = "figure {ref} (raster)"
ROLE_PLOTSPEC = "plot specification for {ref}"
ROLE_TABLE = "table {ref}"
ROLE_PLOT = "plotted values for {ref}"
ROLE_EQUATION = "equation {n}{label}"
ROLE_RAW = "raw data for {target}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _index_of(items: Any, ref: str) -> int | None:
    """1-based position of the item carrying this ref, or None."""
    for i, item in enumerate(items or [], start=1):
        if isinstance(item, dict) and item.get("ref") == ref:
            return i
    return None


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


class _Written:
    """The running record of what has been filed, and how big it was."""

    def __init__(self, ws: Workspace):
        self.ws = ws
        self.entries: list[dict] = []

    def text(self, relative: str, body: str, role: str) -> None:
        result = self.ws.write_text(relative, body)
        self.entries.append({"path": relative, "role": role, "bytes": result.bytes_written})

    def data(self, relative: str, body: bytes, role: str) -> None:
        result = self.ws.write_bytes(relative, body)
        self.entries.append({"path": relative, "role": role, "bytes": result.bytes_written})

    def json(self, relative: str, obj: Any, role: str) -> None:
        self.text(relative, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), role)

    @property
    def paths(self) -> list[str]:
        return [e["path"] for e in self.entries]

    @property
    def total(self) -> int:
        return sum(int(e["bytes"] or 0) for e in self.entries)


def compile_deposit(ws: Workspace, state: dict, rendered: dict) -> dict:
    """Write everything the interface rendered into the document's folder.

    `rendered` is the interface's half of the work:

        {"figures":   [{"ref", "svg", "png_base64"}],
         "tables":    [{"ref", "csv"}],
         "plots":     [{"ref", "csv", "spec"}],
         "equations": [{"index", "label", "latex", "numbered"}]}

    Anything missing is simply not written; a reference the document does not
    know is skipped rather than guessed at. A reference that would climb out of
    the folder raises `PathEscape` from the workspace, which is the only
    gatekeeper that matters.
    """
    state = state or {}
    rendered = rendered or {}
    out = _Written(ws)
    ws.ensure_tree(state)

    # Plot specifications, by the id a figure panel refers to. The interface
    # sends them with the plots; the document's own copy is the fallback.
    specs: dict[str, Any] = {}
    for pl in state.get("plots") or []:
        if isinstance(pl, dict) and pl.get("id"):
            specs[str(pl["id"])] = pl
    for pl in rendered.get("plots") or []:
        spec = pl.get("spec") if isinstance(pl, dict) else None
        if isinstance(spec, dict) and spec.get("id"):
            specs[str(spec["id"])] = spec

    # -- figures ------------------------------------------------------------
    figures = 0
    for item in rendered.get("figures") or []:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("ref") or "")
        index = _index_of(state.get("figures"), ref)
        if index is None:
            continue
        folder = layout.figure_dir(index)
        stem = folder.rsplit("/", 1)[-1]
        svg = _text(item.get("svg"))
        if svg:
            out.text(f"{folder}/{stem}.svg", svg, ROLE_FIGURE_SVG.format(ref=ref))
        png = _text(item.get("png_base64"))
        if png:
            try:
                raw = base64.b64decode(png, validate=False)
            except (ValueError, TypeError):
                raw = b""
            if raw:
                out.data(f"{folder}/{stem}.png", raw, ROLE_FIGURE_PNG.format(ref=ref))
        figures += 1
        # The panels' sources, so the figure can be rebuilt rather than traced.
        source = next((f for f in state.get("figures") or []
                       if isinstance(f, dict) and f.get("ref") == ref), {})
        for panel in source.get("panels") or []:
            src_id = panel.get("src") if isinstance(panel, dict) else None
            if not src_id or str(src_id) not in specs:
                continue
            out.json(f"{folder}/{src_id}.plotspec.json", specs[str(src_id)],
                     ROLE_PLOTSPEC.format(ref=src_id))

    # -- tables -------------------------------------------------------------
    tables = 0
    for item in rendered.get("tables") or []:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("ref") or "")
        index = _index_of(state.get("tables"), ref)
        csv = _text(item.get("csv"))
        if index is None or not csv:
            continue
        folder = layout.table_dir(index)
        stem = folder.rsplit("/", 1)[-1]
        out.text(f"{folder}/{stem}.csv", csv, ROLE_TABLE.format(ref=ref))
        tables += 1

    # -- plots --------------------------------------------------------------
    plots = 0
    for item in rendered.get("plots") or []:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("ref") or "")
        csv = _text(item.get("csv"))
        if not ref or not csv:
            continue
        out.text(layout.plot_csv(ref), csv, ROLE_PLOT.format(ref=ref))
        plots += 1

    # -- equations ----------------------------------------------------------
    equations = 0
    for n, item in enumerate(rendered.get("equations") or [], start=1):
        if not isinstance(item, dict):
            continue
        latex = _text(item.get("latex")).strip()
        if not latex:
            continue
        label = str(item.get("label") or "").strip()
        body = (f"% equation {n}"
                + (f" — {label}" if label else "")
                + ("" if item.get("numbered") is not False else " (unnumbered)")
                + f"\n{latex}\n")
        out.text(layout.equation_file(n), body,
                 ROLE_EQUATION.format(n=n, label=f" ({label})" if label else ""))
        equations += 1

    # -- the readme, last, because it lists everything above ----------------
    attachments = [a for a in state.get("attachments") or [] if isinstance(a, dict)]
    readme = deposit_markdown(state, out.entries, attachments)
    out.text(layout.DEPOSIT_FILE, readme, "what is in this folder")

    return {
        "written": out.paths,
        "bytes": out.total,
        "compiled_at": _now(),
        "counts": {
            "figures": figures,
            "tables": tables,
            "plots": plots,
            "equations": equations,
            "attachments": len(attachments),
        },
    }


def _fmt_bytes(n: int) -> str:
    n = int(n or 0)
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def _authors(state: dict) -> str:
    names = [str(a.get("name") or "").strip()
             for a in state.get("authors") or [] if isinstance(a, dict)]
    names = [n for n in names if n]
    return ", ".join(names) if names else "—"


def _availability(state: dict) -> str:
    """The data availability statement, only when there is something to say."""
    repo = str(state.get("repo") or "").strip()
    doi = str(state.get("datasetDoi") or "").strip()
    if not repo and not doi:
        return ""
    where = repo or "the repository named below"
    at = f" at {doi}" if doi else ""
    return f"The data underpinning this study are openly available from {where}{at}."


def _attachment_path(state: dict, att: dict) -> str:
    """Where an attachment is, or — for one recorded but never uploaded — where
    it would go. `layout` answers the second, so the two never drift."""
    rel = str(att.get("rel_path") or "").strip()
    if rel:
        return rel
    folder = layout.attachment_dir(state, str(att.get("target") or ""))
    return f"{folder}/{att.get('name', 'file')}"


def deposit_markdown(state: dict, entries: list[dict], attachments: list[dict]) -> str:
    """`DEPOSIT.md`: what is in this folder, for whoever opens it next.

    Kept plain on purpose — a repository's preview pane, a reviewer's text
    editor and `cat` should all show the same thing.
    """
    title = str(state.get("title") or "Untitled")
    lines = [
        f"# {title}",
        "",
        f"**Authors** — {_authors(state)}  ",
        f"**Compiled** — {_now()}  ",
        f"**Document kind** — {state.get('kind', 'publication')}",
        "",
        "This folder was compiled by GerbilDocs. Everything below was generated",
        "from the document, except the raw data, which was supplied by the",
        "authors and is listed with its checksum.",
        "",
    ]

    statement = _availability(state)
    if statement:
        lines += ["## Data availability", "", statement, ""]

    lines += ["## Files", "", "| File | What it is | Size |", "| --- | --- | --- |"]
    for entry in entries:
        lines.append(f"| `{entry['path']}` | {entry['role']} | {_fmt_bytes(entry['bytes'])} |")
    for att in attachments:
        rel = _attachment_path(state, att)
        target = str(att.get("target") or "unassigned")
        lines.append(f"| `{rel}` | {ROLE_RAW.format(target=target)} | "
                     f"{_fmt_bytes(att.get('bytes') or 0)} |")
    lines.append("")

    if attachments:
        lines += ["## Raw data checksums", "", "| File | sha256 | Note |", "| --- | --- | --- |"]
        for att in attachments:
            rel = _attachment_path(state, att)
            digest = str(att.get("sha256") or "—")
            note = str(att.get("note") or "").replace("|", "/")
            lines.append(f"| `{rel}` | `{digest}` | {note} |")
        lines.append("")

    return "\n".join(lines)
