"""HTTP surface for the desktop edition.

Every route is thin on purpose: validate, call a service in `app/services/`,
return. All of the behaviour worth testing lives in those services and is
tested without starting a server (`tests/`).

Loopback only, and every request carries a per-launch bearer token, so another
process on the same machine cannot drive the API.
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import (APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Request,
                     UploadFile)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .services import attachments as att_svc
from .services import deposit as deposit_svc
from .services import layout as layout_svc
from .services import reveal as reveal_svc
from .services import workspace as ws_svc
from .services.safety import PathEscape, resolve_within
from .services.store import Store
from .services.workspace import NotADocumentFolder, Workspace

API_VERSION = "1.1.0"


# ---------------------------------------------------------------- schemas --

class NewDocument(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    kind: str = "publication"
    base_dir: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)


class SaveState(BaseModel):
    state: dict[str, Any]


class WriteFile(BaseModel):
    relative: str
    text: str | None = None
    base64_data: str | None = Field(default=None, alias="base64")

    model_config = {"populate_by_name": True}


class Deposit(BaseModel):
    rendered: dict[str, Any] = Field(default_factory=dict)


class NewRevision(BaseModel):
    revision: dict[str, Any]


class LibraryPut(BaseModel):
    values: dict[str, Any]


class AdoptFolder(BaseModel):
    root: str = Field(min_length=1)


class LibraryRoot(BaseModel):
    path: str = Field(min_length=1)
    label: str = ""


class LibraryRootsPut(BaseModel):
    roots: list[LibraryRoot]


# ------------------------------------------------------------------ deps ---

def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _store(request: Request) -> Store:
    return request.app.state.store


def require_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    expected = request.app.state.settings.token
    supplied = None
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if supplied is None:
        supplied = request.query_params.get("t")
    if not supplied or supplied != expected:
        raise HTTPException(status_code=401, detail="bad or missing token")


def _open(request: Request, doc_id: str) -> tuple[Store, dict, Workspace]:
    store = _store(request)
    row = store.get_document(doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="no such document")
    return store, row, Workspace(Path(row["root"]))


# ---------------------------------------------------------------- routes ---

router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


@router.get("/health")
def health(request: Request) -> dict:
    s = _settings(request)
    store = _store(request)
    return {
        "ok": True,
        "app": "GerbilDocs",
        "version": API_VERSION,
        "edition": s.edition,
        "profile": {
            "name": s.profile.name,
            "long_name": s.profile.long_name,
            "credit": s.profile.credit,
            "support_url": s.profile.support_url,
            "support_label": s.profile.support_label,
            "licence": s.profile.licence,
            "author": s.profile.author,
        },
        "documents_dir": str(s.paths.documents),
        "app_dir": str(s.paths.root),
        "folder_dialog": getattr(request.app.state, "pick_folder", None) is not None,
        "vault": {
            "path": str(store.path),
            "schema_version": store.schema_version,
            "backup": str(store.backup_path) if store.backup_path else None,
            "notices": list(store.notices),
        },
    }


@router.get("/documents")
def list_documents(request: Request) -> dict:
    return {"documents": _store(request).list_documents()}


@router.get("/documents/discover")
def discover_documents(request: Request, base_dir: str | None = None) -> dict:
    """Document folders on disk that the vault does not list — after a vault
    reset, or documents copied in from another machine."""
    store = _store(request)
    base = Path(base_dir) if base_dir else _settings(request).paths.documents
    found = []
    for folder in ws_svc.discover(base):
        if store.find_by_root(str(folder.root)):
            continue
        found.append({"root": str(folder.root), "title": folder.title,
                      "kind": folder.kind, "saved_at": folder.saved_at})
    return {"base_dir": str(base), "documents": found}


def _library_roots(request: Request) -> list[dict]:
    """The folders the Documents library shows: the default documents folder
    first, always, then whatever the user has added."""
    s = _settings(request)
    default = {"path": str(s.paths.documents), "label": "Documents", "default": True}
    extra = _store(request).get_setting("library_roots", []) or []
    out = [default]
    seen = {str(Path(default["path"]).resolve())}
    for r in extra:
        if not isinstance(r, dict) or not r.get("path"):
            continue
        key = str(Path(r["path"]).resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append({"path": r["path"], "label": r.get("label") or Path(r["path"]).name,
                    "default": False})
    return out


@router.get("/library-roots")
def get_library_roots(request: Request) -> dict:
    return {"roots": _library_roots(request)}


@router.put("/library-roots")
def put_library_roots(request: Request, body: LibraryRootsPut) -> dict:
    """Replace the user's added locations. The default folder cannot be
    removed and is not stored. Paths are kept as given; a folder that does
    not exist is refused rather than silently kept."""
    s = _settings(request)
    default_key = str(s.paths.documents.resolve())
    kept = []
    for r in body.roots:
        p = Path(r.path)
        if not p.is_dir():
            raise HTTPException(status_code=400, detail=f"{r.path} is not a folder")
        if str(p.resolve()) == default_key:
            continue
        kept.append({"path": str(p), "label": r.label or p.name})
    _store(request).put_setting("library_roots", kept)
    return {"roots": _library_roots(request)}


@router.get("/documents/tree")
def documents_tree(request: Request, base_dir: str | None = None, depth: int = 4) -> dict:
    """Every document folder under a library root, as a folder tree, each
    marked with the vault's id when the vault knows it. Reads only."""
    store = _store(request)
    base = Path(base_dir) if base_dir else _settings(request).paths.documents
    depth = max(0, min(8, depth))
    if not base.is_dir():
        raise HTTPException(status_code=404, detail=f"{base} is not a folder")

    def node_dict(n: ws_svc.FolderNode) -> dict:
        docs = []
        for d in n.documents:
            known = store.find_by_root(str(d.root))
            docs.append({"root": str(d.root), "title": d.title, "kind": d.kind,
                         "saved_at": d.saved_at, "id": known["id"] if known else None})
        return {"name": n.name, "path": str(n.path), "documents": docs,
                "children": [node_dict(c) for c in n.children], "total": n.total}

    return {"base_dir": str(base), "tree": node_dict(ws_svc.discover_tree(base, depth))}


@router.post("/documents/adopt", status_code=201)
def adopt_document(request: Request, body: AdoptFolder) -> dict:
    """Register an existing document folder. Reads its document.json; creates
    nothing on disk. A folder already in the vault is returned, not duplicated."""
    store = _store(request)
    existing = store.find_by_root(body.root)
    if existing:
        row = store.get_document(existing["id"])
        assert row is not None
        return {"id": row["id"], "root": row["root"], "state": store.merge_state(row["state"]),
                "adopted": False}
    try:
        folder = Workspace.read_document_folder(Path(body.root))
    except NotADocumentFolder as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    doc, library = store.split_state(folder.state)
    doc["dir"] = str(folder.root)
    doc.setdefault("title", folder.title)
    doc.setdefault("kind", folder.kind)
    doc_id = store.create_document(folder.title, folder.kind, str(folder.root), doc)
    return {"id": doc_id, "root": str(folder.root), "state": store.merge_state(doc),
            "adopted": True}


@router.post("/documents", status_code=201)
def create_document(request: Request, body: NewDocument) -> dict:
    s = _settings(request)
    base = Path(body.base_dir) if body.base_dir else s.paths.documents
    ws = Workspace.create(base, body.title, body.kind)
    state = dict(body.state)
    state.setdefault("title", body.title)
    state.setdefault("kind", body.kind)
    state["dir"] = str(ws.root)
    ws.ensure_tree(state)
    doc, library = _store(request).split_state(state)
    doc_id = _store(request).create_document(body.title, body.kind, str(ws.root), doc)
    if library:
        _store(request).put_library(library)
    ws.write_document_state(doc)
    return {"id": doc_id, "root": str(ws.root), "state": _store(request).merge_state(doc)}


@router.get("/documents/{doc_id}")
def get_document(request: Request, doc_id: str) -> dict:
    """Fetching a document is opening it: it moves to the top of the list."""
    store, row, _ = _open(request, doc_id)
    store.mark_opened(doc_id)
    return {"id": row["id"], "root": row["root"], "state": store.merge_state(row["state"])}


@router.put("/documents/{doc_id}")
def put_document(request: Request, doc_id: str, body: SaveState) -> dict:
    store, row, ws = _open(request, doc_id)
    doc, library = store.split_state(body.state)
    doc["dir"] = row["root"]
    store.save_document(doc_id, doc)
    if library:
        store.put_library(library)
    made = ws.ensure_tree(doc)
    mirrored = ws.write_document_state(doc)
    return {"saved": True, "folders_created": made, "mirror": str(mirrored.path),
            "saved_at": _store(request).get_document(doc_id)["updated_at"]}  # type: ignore[index]


@router.post("/documents/{doc_id}/reveal")
def reveal_document(request: Request, doc_id: str) -> dict:
    """Show the document's folder in the file manager. The path comes from the
    vault, never from the request."""
    _store_, row, _ws = _open(request, doc_id)
    try:
        did = reveal_svc.reveal(Path(row["root"]))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"revealed": row["root"], "how": did}


@router.post("/reveal")
def reveal_app_folder(request: Request, target: str = "documents") -> dict:
    """Show the documents folder or the application's own folder."""
    s = _settings(request)
    path = {"documents": s.paths.documents, "app": s.paths.root}.get(target)
    if path is None:
        raise HTTPException(status_code=400, detail="target must be 'documents' or 'app'")
    try:
        did = reveal_svc.reveal(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"revealed": str(path), "how": did}


class OpenUrl(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


@router.post("/open-url")
def open_url(request: Request, body: OpenUrl) -> dict:
    """Open a web address in the user's default browser. pywebview's window
    does not follow target=_blank, so the interface asks the host. Only
    http(s) is accepted."""
    if not body.url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="only http(s) links are opened")
    import webbrowser
    try:
        opened = webbrowser.open(body.url, new=2)
    except Exception as exc:  # noqa: BLE001 - report, never crash the host
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"opened": bool(opened), "url": body.url}


@router.post("/dialog/folder")
def pick_folder(request: Request) -> dict:
    """Native folder picker, when the host window provides one. The launcher
    installs `app.state.pick_folder` after the webview is up; without it (the
    `--browser` mode, or the self-check) the interface asks for a typed path."""
    picker = getattr(request.app.state, "pick_folder", None)
    if picker is None:
        raise HTTPException(status_code=501, detail="no native folder dialog in this host")
    chosen = picker()
    return {"path": str(chosen) if chosen else None}


@router.delete("/documents/{doc_id}")
def forget_document(request: Request, doc_id: str) -> dict:
    """Removes it from the list. The folder on disk is left alone, always."""
    store, row, _ = _open(request, doc_id)
    store.delete_document(doc_id)
    return {"forgotten": True, "folder_left_at": row["root"]}


@router.get("/documents/{doc_id}/tree")
def document_tree(request: Request, doc_id: str) -> dict:
    store, row, ws = _open(request, doc_id)
    state = store.merge_state(row["state"])
    return {"root": row["root"], "nodes": ws.tree(state)}


@router.post("/documents/{doc_id}/files")
def write_file(request: Request, doc_id: str, body: WriteFile) -> dict:
    _store_, row, ws = _open(request, doc_id)
    if body.text is None and body.base64_data is None:
        raise HTTPException(status_code=400, detail="give either text or base64")
    try:
        if body.base64_data is not None:
            result = ws.write_bytes(body.relative, base64.b64decode(body.base64_data))
        else:
            result = ws.write_text(body.relative, body.text or "")
    except PathEscape as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"path": str(result.path), "bytes": result.bytes_written, "created": result.created}


@router.post("/documents/{doc_id}/deposit")
def compile_deposit(request: Request, doc_id: str, body: Deposit) -> dict:
    """Write what the interface rendered into the folder, ready to deposit.

    The tree comes back with the summary so the browser does not have to ask
    again to find out what is now on disk.
    """
    store, row, ws = _open(request, doc_id)
    state = store.merge_state(row["state"])
    try:
        summary = deposit_svc.compile_deposit(ws, state, body.rendered)
    except PathEscape as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return dict(summary, root=row["root"], tree=ws.tree(state))


@router.post("/documents/{doc_id}/attachments", status_code=201)
async def add_attachment(
    request: Request,
    doc_id: str,
    target: str = Form(...),
    attachment_id: str = Form(...),
    note: str = Form(default=""),
    upload: UploadFile = File(...),
) -> dict:
    store, row, ws = _open(request, doc_id)
    state = store.merge_state(row["state"])
    data = await upload.read()
    try:
        record = att_svc.attach_bytes(
            ws, state, target, upload.filename or "data.bin", data,
            attachment_id=attachment_id, content_type=upload.content_type or "", note=note,
        )
    except PathEscape as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = [a for a in (state.get("attachments") or []) if a.get("id") != record.id]
    existing.append(record.to_dict())
    state["attachments"] = existing
    doc, _library = store.split_state(state)
    store.save_document(doc_id, doc)
    summary = att_svc.rewrite_manifest(ws, state, existing)
    return {"attachment": record.to_dict(), "deposit": summary}


@router.delete("/documents/{doc_id}/attachments/{attachment_id}")
def remove_attachment(request: Request, doc_id: str, attachment_id: str,
                      delete_file: bool = False) -> dict:
    store, row, ws = _open(request, doc_id)
    state = store.merge_state(row["state"])
    kept, removed = [], None
    for a in state.get("attachments") or []:
        if a.get("id") == attachment_id:
            removed = a
        else:
            kept.append(a)
    if removed is None:
        raise HTTPException(status_code=404, detail="no such attachment")
    if delete_file and removed.get("rel_path"):
        try:
            resolve_within(ws.root, removed["rel_path"]).unlink(missing_ok=True)
        except PathEscape as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    state["attachments"] = kept
    doc, _ = store.split_state(state)
    store.save_document(doc_id, doc)
    summary = att_svc.rewrite_manifest(ws, state, kept)
    return {"removed": attachment_id, "file_deleted": bool(delete_file), "deposit": summary}


@router.post("/documents/{doc_id}/revisions", status_code=201)
def add_revision(request: Request, doc_id: str, body: NewRevision) -> dict:
    store, row, ws = _open(request, doc_id)
    index = store.add_revision(doc_id, body.revision)
    result = ws.write_revision(index, body.revision)
    return {"index": index, "path": str(result.path)}


@router.get("/documents/{doc_id}/revisions")
def list_revisions(request: Request, doc_id: str) -> dict:
    store, _row, _ws = _open(request, doc_id)
    return {"revisions": store.list_revisions(doc_id)}


@router.get("/library")
def get_library(request: Request) -> dict:
    return {"library": _store(request).get_library()}


@router.put("/library")
def put_library(request: Request, body: LibraryPut) -> dict:
    return {"written": _store(request).put_library(body.values)}


@router.get("/layout/preview")
def layout_preview(request: Request, kind: str = "publication") -> dict:
    """What a new document of this kind would create. Used by the New dialog."""
    plan = layout_svc.plan_document({"kind": kind})
    return {"nodes": [asdict(p) for p in plan]}


# -------------------------------------------------------------- the app ----

def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="GerbilDocs", version=API_VERSION,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.settings = settings
    app.state.store = Store(settings.paths.store, library_dir=settings.paths.library,
                            backups_dir=settings.paths.root / "backups")
    app.include_router(router)

    static_dir = settings.static_dir
    index_path = static_dir / "index.html"

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        if not index_path.exists():
            return HTMLResponse("<h1>index.html is missing from the bundle</h1>", status_code=500)
        html = index_path.read_text(encoding="utf-8")
        boot = (
            "<script>"
            f"window.__DESK_TOKEN={json.dumps(settings.token)};"
            'window.__DESK_API="/api";'
            'window.__DESK_EDITION="desktop";'
            f"window.__DESK_DOCUMENTS_DIR={json.dumps(str(settings.paths.documents))};"
            f"window.__DESK_PROFILE={json.dumps(asdict(settings.profile))};"
            "</script>"
        )
        if "</head>" in html:
            html = html.replace("</head>", boot + "</head>", 1)
        else:
            html = boot + html
        return HTMLResponse(html)

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.exception_handler(PathEscape)
    def _path_escape(_request: Request, exc: PathEscape) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app
