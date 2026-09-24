"""End-to-end smoke test of the HTTP surface.

    python -m app.selfcheck

Everything in `app/services/` is covered by `tests/` and runs without a web
framework. This exercises the thin layer on top — routing, auth, multipart
upload, the injected boot script — against a throwaway data folder, and leaves
nothing behind. Run it once after `pip install -r requirements.txt`.
"""

from __future__ import annotations

import base64
import io
import shutil
import sys
import tempfile
from pathlib import Path

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{'  — ' + detail if detail and not ok else ''}")


def main() -> int:
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("fastapi is not installed — run: pip install -r requirements.txt", file=sys.stderr)
        return 2

    from .api import create_app
    from .config import load_settings

    tmp = Path(tempfile.mkdtemp(prefix="desk-selfcheck-"))
    try:
        settings = load_settings(tmp / "appdata", token="selfcheck-token")
        settings.paths.documents = tmp / "documents"
        settings.paths.documents.mkdir(parents=True, exist_ok=True)
        client = TestClient(create_app(settings))
        auth = {"Authorization": f"Bearer {settings.token}"}

        print("\nGerbilDocs — self check\n")

        check("rejects a request with no token", client.get("/api/health").status_code == 401)
        check("rejects a wrong token",
              client.get("/api/health", headers={"Authorization": "Bearer nope"}).status_code == 401)

        r = client.get("/api/health", headers=auth)
        check("health responds", r.status_code == 200 and r.json().get("ok") is True, r.text[:120])

        r = client.get(f"/api/health?t={settings.token}")
        check("accepts the token as a query parameter", r.status_code == 200)
        vault = r.json().get("vault", {})
        check("health reports the vault and its notices",
              vault.get("schema_version", 0) >= 2 and isinstance(vault.get("notices"), list),
              r.text[:200])

        r = client.post("/api/documents", headers=auth, json={
            "title": "Sub-monolayer TiO2 on SBA-15", "kind": "publication",
            "state": {"figures": [{"ref": "F1", "panels": []}], "tables": [{"ref": "T1"}],
                      "refs": [{"id": "r1", "title": "A cited paper"}],
                      "samples": [{"id": "sm_07", "code": "TSB-07"}]},
        })
        ok = r.status_code == 201
        check("creates a document", ok, r.text[:200])
        if not ok:
            return _summary()
        doc = r.json()
        root = Path(doc["root"])
        check("makes the document folder", root.is_dir(), str(root))
        check("makes the sub-folders",
              (root / "figures/figure-01").is_dir() and (root / "data").is_dir())
        check("library came back merged into the state",
              doc["state"].get("refs", [{}])[0].get("title") == "A cited paper")

        r = client.put(f"/api/documents/{doc['id']}", headers=auth,
                       json={"state": dict(doc["state"], abstract="An abstract.")})
        check("saves state", r.status_code == 200 and r.json()["saved"] is True, r.text[:160])

        r = client.get(f"/api/documents/{doc['id']}", headers=auth)
        check("reads state back", r.json()["state"].get("abstract") == "An abstract.")
        check("mirrors the document into its folder",
              (root / "document.json").exists()
              and '"abstract": "An abstract."' in (root / "document.json").read_text("utf-8"))
        r = client.get("/api/documents", headers=auth)
        check("lists the document, with when it was opened",
              r.json()["documents"][0]["id"] == doc["id"]
              and r.json()["documents"][0].get("opened_at"), r.text[:160])

        from .services import reveal as reveal_mod
        launched: list[list[str]] = []
        real_detach = reveal_mod._detach
        reveal_mod._detach = launched.append  # do not open a real file manager here
        try:
            r = client.post(f"/api/documents/{doc['id']}/reveal", headers=auth)
            if sys.platform.startswith("win"):
                check("reveal answers on Windows", r.status_code == 200, r.text[:160])
            else:
                check("reveal launches the platform file manager on the folder",
                      r.status_code == 200 and launched and launched[0][-1] == str(root),
                      r.text[:160])
        finally:
            reveal_mod._detach = real_detach
        r = client.post("/api/open-url", headers=auth, json={"url": "file:///etc/passwd"})
        check("refuses to open anything but http(s)", r.status_code == 400)
        r = client.post("/api/dialog/folder", headers=auth)
        check("folder dialog reports itself absent outside a native window",
              r.status_code == 501, r.text[:120])

        # A second folder the vault does not know about is discoverable and adoptable.
        r2 = client.post("/api/documents", headers=auth,
                         json={"title": "Orphan", "kind": "report", "state": {}})
        orphan_root = Path(r2.json()["root"])
        client.delete(f"/api/documents/{r2.json()['id']}", headers=auth)
        r = client.get("/api/documents/discover", headers=auth)
        check("finds a document folder the vault does not list",
              any(d["root"] == str(orphan_root) for d in r.json()["documents"]), r.text[:200])
        r = client.post("/api/documents/adopt", headers=auth,
                        json={"root": str(orphan_root)})
        check("adopts it", r.status_code == 201 and r.json()["adopted"] is True, r.text[:160])
        r = client.post("/api/documents/adopt", headers=auth,
                        json={"root": str(orphan_root)})
        check("adopting twice returns the same document",
              r.status_code == 201 and r.json()["adopted"] is False)
        r = client.post("/api/documents/adopt", headers=auth, json={"root": str(tmp)})
        check("refuses to adopt a folder with no document in it", r.status_code == 400)

        # The Documents library: roots and the folder tree.
        r = client.get("/api/library-roots", headers=auth)
        check("library roots start with the default documents folder",
              r.status_code == 200 and r.json()["roots"][0]["default"] is True, r.text[:160])
        extra = tmp / "extra-location"
        (extra / "2026" ).mkdir(parents=True)
        r3 = client.post("/api/documents", headers=auth,
                         json={"title": "Elsewhere", "kind": "grant", "state": {},
                               "base_dir": str(extra / "2026")})
        r = client.put("/api/library-roots", headers=auth,
                       json={"roots": [{"path": str(extra), "label": "Extra"}]})
        check("adds a library root", r.status_code == 200 and len(r.json()["roots"]) == 2, r.text[:160])
        r = client.put("/api/library-roots", headers=auth,
                       json={"roots": [{"path": str(tmp / "does-not-exist"), "label": "x"}]})
        check("refuses a root that is not a folder", r.status_code == 400)
        r = client.get("/api/documents/tree", headers=auth, params={"base_dir": str(extra)})
        tree = r.json().get("tree", {})
        found = [d for c in tree.get("children", []) for d in c["documents"]]
        check("the tree finds a document one folder down, with its vault id",
              r.status_code == 200 and any(d["root"] == r3.json()["root"] and d["id"] for d in found),
              r.text[:200])
        r = client.get("/api/documents/tree", headers=auth, params={"base_dir": str(tmp / "nope")})
        check("the tree refuses a missing folder", r.status_code == 404)

        r = client.post(f"/api/documents/{doc['id']}/files", headers=auth,
                        json={"relative": "manuscript.docx",
                              "base64": base64.b64encode(b"PK\x03\x04 not really").decode()})
        check("writes an export into the folder",
              r.status_code == 200 and (root / "manuscript.docx").exists(), r.text[:160])

        r = client.post(f"/api/documents/{doc['id']}/files", headers=auth,
                        json={"relative": "../escape.txt", "text": "no"})
        check("refuses a path that escapes the folder", r.status_code == 400, r.text[:160])

        payload = b"VAMAS data\n" * 64
        r = client.post(
            f"/api/documents/{doc['id']}/attachments", headers=auth,
            data={"target": "F1", "attachment_id": "at_1", "note": "Ti 2p regions"},
            files={"upload": ("Ti2p.vms", io.BytesIO(payload), "chemical/x-vamas")},
        )
        ok = r.status_code == 201
        check("uploads raw data", ok, r.text[:200])
        if ok:
            rec = r.json()["attachment"]
            check("files it under the figure it supports", rec["rel_path"] == "data/figure-01/Ti2p.vms")
            check("copies the bytes", (root / rec["rel_path"]).read_bytes() == payload)
            check("hashes it", len(rec["sha256"]) == 64)
            check("regenerates the manifest", (root / "data/MANIFEST.csv").exists())
            check("regenerates the readme", (root / "data/README.md").exists())
            check("writes a data availability statement",
                  "deposit comprises 1 files" in r.json()["deposit"]["statement"])

        r = client.post(f"/api/documents/{doc['id']}/revisions", headers=auth,
                        json={"revision": {"label": "First full draft", "by": "Mark Isaacs",
                                           "snapshot": {"subdocs": {}}}})
        check("writes a revision to drafts/",
              r.status_code == 201 and (root / "drafts/rev-01-first-full-draft.json").exists(),
              r.text[:160])

        # Compiling the deposit: the interface renders, the backend files it.
        current = client.get(f"/api/documents/{doc['id']}", headers=auth).json()["state"]
        current["subdocs"] = {"manuscript": {"sections": [{"id": "s1", "blocks": [
            {"id": "b1", "type": "eq", "latex": r"E_k = h\nu - E_b - \phi", "numbered": True,
             "label": "eq:ke"}]}]}}
        current["plots"] = [{"id": "pl_1", "ref": "P1", "name": "Ti 2p"}]
        client.put(f"/api/documents/{doc['id']}", headers=auth, json={"state": current})
        r = client.post(f"/api/documents/{doc['id']}/deposit", headers=auth, json={"rendered": {
            "figures": [{"ref": "F1", "svg": "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
                         "png_base64": base64.b64encode(b"\x89PNG not really").decode()}],
            "tables": [{"ref": "T1", "csv": "Sample,Coverage\nTSB-07,0.7\n"}],
            "plots": [{"ref": "P1", "csv": "x,Ti 2p\n458.5,1.0\n", "spec": {"id": "pl_1"}}],
            "equations": [{"index": 1, "label": "eq:ke", "numbered": True,
                           "latex": r"E_k = h\nu - E_b - \phi"}],
        }})
        ok = r.status_code == 200
        check("compiles a deposit", ok, r.text[:200])
        if ok:
            summary = r.json()
            check("writes the table's CSV where the layout says",
                  (root / "tables/table-01/table-01.csv").exists(),
                  str(sorted(summary["written"])[:6]))
            check("writes the equation as TeX",
                  (root / "equations/equation-01.tex").exists()
                  and "E_k" in (root / "equations/equation-01.tex").read_text("utf-8"))
            check("writes the figure and the plot's values",
                  (root / "figures/figure-01/figure-01.svg").exists()
                  and (root / "figures/figure-01/figure-01.png").exists()
                  and (root / "plots/P1.csv").exists())
            check("writes DEPOSIT.md listing what it wrote",
                  (root / "DEPOSIT.md").exists()
                  and "equations/equation-01.tex" in (root / "DEPOSIT.md").read_text("utf-8"))
            check("counts what it compiled",
                  summary["counts"]["tables"] == 1 and summary["counts"]["equations"] == 1
                  and summary["bytes"] > 0, str(summary.get("counts")))
            check("hands back the tree with the new files present",
                  {n["path"]: n for n in summary["tree"]}
                  .get("equations/equation-01.tex", {}).get("present") is True)
        r = client.post(f"/api/documents/{doc['id']}/deposit", headers=auth, json={"rendered": {
            "plots": [{"ref": "../../escape", "csv": "x\n1\n"}]}})
        check("refuses a deposit path that escapes the folder", r.status_code == 400, r.text[:160])

        r = client.get(f"/api/documents/{doc['id']}/tree", headers=auth)
        nodes = {n["path"]: n for n in r.json()["nodes"]}
        check("the tree reports what is really there",
              nodes.get("manuscript.docx", {}).get("present") is True
              and nodes.get("cover-letter.docx", {}).get("present") is False)

        r = client.get("/api/library", headers=auth)
        check("library is app-scoped", r.json()["library"].get("refs") is not None)
        check("library is mirrored to disk as JSON",
              (settings.paths.library / "refs.json").exists(), str(settings.paths.library))

        r = client.get("/")
        html = r.text
        check("serves the interface", r.status_code == 200 and len(html) > 100_000, str(len(html)))
        check("injects the token into the page", settings.token in html)
        check("marks the page as the desktop edition", '__DESK_EDITION="desktop"' in html)

        # The interface is one file with no build step, so the only way to
        # notice a feature being deleted from it is to look.
        for name, needle in [
            ("cross-references can name several things", "function joinRefNums"),
            ("several can be picked at once", "function openRefPicker"),
            ("author names are held in parts", "const NAME_STYLES"),
            ("the document has a language", "function applyLang"),
            ("British/American variants are checked", "function variantFor"),
            ("there is a right-click menu", "function wireContextMenu"),
            ("sections can be added without scrolling", 'class="secbar"'),
            ("AVS has a submission template", 'id:"tpl_avs_submit"'),
            ("organisations have a postcode", "function orgAddress"),
        ]:
            check(name, needle in html, needle)

        # The example document ships to strangers. Nobody's name, employer or
        # research topic belongs in it; the credit line in the header is the
        # one place a person is named on purpose.
        leaked = [w for w in ("HarwellXPS", "UCL", "SBA-15", "Parlett", "ucl.ac.uk")
                  if w in html]
        check("the example names nobody and nothing real", not leaked, ", ".join(leaked))
        check("the credit line is still there", "Created by <b>Dr Mark Isaacs</b>" in html)

        r = client.get("/api/openapi.json", headers=auth)
        check("publishes an OpenAPI schema", r.status_code == 200 and "paths" in r.json())

        return _summary()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _summary() -> int:
    bad = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(bad)} passed, {len(bad)} failed\n")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
