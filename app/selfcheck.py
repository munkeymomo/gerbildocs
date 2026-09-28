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
import re
import shutil
import sys
import tempfile
from pathlib import Path

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{'  — ' + detail if detail and not ok else ''}")


# Names from the design documents, and the product's old name, are for the
# people building it. The selfcheck cannot run the page, so it reads it with
# its comments taken out: what is left is markup, code and the strings a user
# can be shown, and a name found there is one a user could see.
INTERNAL_NAMES = ("MODEL-0", "ADR-W", "ARCH-W", "VISION-0", "ROADMAP-W", "PLUGIN-0",
                  "HANDOFF", "Workbench", "Document Desk", "the Desk ", "TSB-")


def without_comments(html: str) -> str:
    """The page less its comments: HTML comments, block comments in scripts and
    styles, and line comments at the start of a line or after a space. A block
    comment cannot follow a word character or a quote, so `accept="image/*"`
    is not one; a `//` in a URL follows a colon, so it stays."""
    s = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    s = re.sub(r"(?<![\w\"'/*])/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(^|[\s;{}])//[^\n]*", r"\1", s, flags=re.M)


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
                        json={"revision": {"label": "First full draft", "by": "Jane Doe",
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

        # An imported style file lands in two sets that are already app-scoped,
        # templates and styleLib; a grant format rides on its template. The
        # desktop interface saves the whole state and the vault splits the
        # library off, so check that path keeps both and hands them to the
        # next document — and that the exported file itself can be written
        # into the document folder, which is where the desktop edition saves it.
        imported = {"id": "tpl_sfcheck", "family": "My templates", "label": "Imported grant format",
                    "kind": "grant", "mine": True, "style": "compact", "styleId": "st_sfcheck",
                    "sections": [], "statements": [], "notes": [], "format": {"columns": 1},
                    "page": {"header": {}, "footer": {}, "pageNumbers": True, "numberIn": "footer-right"},
                    "imported": {"file": "office.gerbilstyle"},
                    "grantFormat": {"parts": [{"l": "Case for support", "mode": "attachment", "pages": 6}],
                                    "refs": {"mode": "inline", "part": None, "style": "st_sfcheck"},
                                    "form": []}}
        current = client.get(f"/api/documents/{doc['id']}", headers=auth).json()["state"]
        current["templates"] = (current.get("templates") or []) + [imported]
        current["styleLib"] = (current.get("styleLib") or []) + [
            {"id": "st_sfcheck", "label": "Office compact", "base": "compact", "abstractLimit": 250,
             "doi": False, "source": "from a style file"}]
        client.put(f"/api/documents/{doc['id']}", headers=auth, json={"state": current})
        lib = client.get("/api/library", headers=auth).json()["library"]
        check("an imported template, its grant format and its style are kept in the library",
              any(t.get("id") == "tpl_sfcheck" and t.get("grantFormat", {}).get("parts")
                  for t in lib.get("templates") or [])
              and any(s.get("id") == "st_sfcheck" for s in lib.get("styleLib") or []))
        check("the imported template is mirrored to disk",
              "tpl_sfcheck" in (settings.paths.library / "templates.json").read_text("utf-8")
              if (settings.paths.library / "templates.json").exists() else False)
        r = client.post("/api/documents", headers=auth,
                        json={"title": "From an imported format", "kind": "grant",
                              "state": {"kind": "grant", "title": "From an imported format"}})
        fresh = r.json().get("state", {}) if r.status_code == 201 else {}
        check("a new document is given the imported template and style",
              any(t.get("id") == "tpl_sfcheck" for t in fresh.get("templates") or [])
              and any(s.get("id") == "st_sfcheck" for s in fresh.get("styleLib") or []))
        r = client.post(f"/api/documents/{doc['id']}/files", headers=auth,
                        json={"relative": "office-format.gerbilstyle",
                              "text": '{"gerbildocs":"style","version":1}'})
        check("a style file is written into the document folder",
              r.status_code == 200 and (root / "office-format.gerbilstyle").exists(), r.text[:160])

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
            ("text blocks can be saved and reused", "function openSnipPicker"),
            ("the library has a view of its own", "function vLibrary"),
            ("author names are held in parts", "const NAME_STYLES"),
            ("the document has a language", "function applyLang"),
            ("British/American variants are checked", "function variantFor"),
            ("there is a right-click menu", "function wireContextMenu"),
            ("sections can be added without scrolling", 'class="secbar"'),
            ("AVS has a submission template", 'id:"tpl_avs_submit"'),
            ("organisations have a postcode", "function orgAddress"),
            ("Gantt header labels are stepped so they cannot collide", "function ganttLabelStep"),
            ("Gantt labels are fitted with an ellipsis and a hover title", "function ganttLabel"),
            ("every caption field offers the same Reference… picker as a paragraph", 'id="pCapRef"'),
            ("a citation used only in a caption is still numbered and listed", "grab(b.caption)"),
        ]:
            check(name, needle in html, needle)

        # Plots: datasets, stacking, error bars, annotations, palettes. Same
        # guard as above — a feature deleted from the one interface file can
        # only be noticed by looking for it.
        for name, needle in [
            ("plots hold datasets, migrated from the old flat series", "function migratePlot"),
            ("plot data is edited as datasets", "function drawPlotData"),
            ("a dataset splits into one per column, and datasets merge", "function pdmMerge"),
            ("plots stack datasets with an offset", "offsetPct"),
            ("plots normalise per dataset or per column", "function normLin"),
            ("plots carry error bars, including custom values", "function errLookup"),
            ("plots can be drawn on", "function annSVG"),
            ("plots offer palettes and a full colour picker", "const PALETTES"),
            ("a dataset can be named by a linked sample", "function dsLabel"),
            ("a plot can have a right-hand axis", "y2Axis"),
            # Figures: every panel is drawn at its printed size, complete, and
            # Word and the deposit place the same grid the pages print.
            ("figure panels are sized in points from the page", "function figGeom"),
            ("a panel's type is laid out at its printed size", "fit:true"),
            ("Word places each figure as the pages set it", "figureGridSVG(f)"),
            ("a figure of one panel carries no letter and no \"(a)\"", "Journals do not letter a figure of one panel"),
        ]:
            check(name, needle in html, needle)
        check("no figure panel is drawn as a thumbnail (no axis titles or legend)",
              "thumb:true" not in html)

        # Samples in plots, and uncertainty on sample properties: a dataset
        # can be the samples themselves, held by reference and read live.
        for name, needle in [
            ("a plot dataset can come from samples, by reference", "function isSampleDs"),
            ("sample datasets are read live through one resolver", "function plotView"),
            ("the renderer reads every plot through the resolver", "p=plotView(p);"),
            ("plots draw x error bars", "function errLookupX"),
            ("points can be labelled by their sample", "d.pointLabels"),
            ("the data manager edits a dataset made from samples", "function sdsGridHTML"),
            ("a sample property can carry an uncertainty", "const PROP_ERR"),
            ("'2.1 ± 0.3', '2.1+-0.3' and '2.1 (0.3)' are a value and its uncertainty",
             "function parseValErr"),
            ("a sample table prints ±, concise brackets, or neither", "const TBL_UNCERT"),
            ("a table's CSV gives each uncertainty a column of its own",
             "tableCells(t,{csv:true})"),
            ("a sample or property a plot uses is not deleted from under it",
             "function plotsUsingSample"),
            ("measurements pasted onto samples become typed columns in one step",
             "function measParse"),
            ("a header that names an uncertainty attaches as the ± of the column before",
             "function measIsErrHead"),
            ("headerless value and ± pairs are guessed from the numbers", "function measGuessPairs"),
            ("a pasted block wider than the typed columns makes more", "while(slots.length<P.ncols)"),
            ("pasted data reads numbers as samples do (no prefix, a decimal comma)",
             "const num=propNum;"),
            ("the pasted grid says which cells are not numbers", "function pdmNumIssues"),
        ]:
            check(name, needle in html, needle)

        # Grants: a grant is made of the funder's parts, each with its limits,
        # and says so in one file, so the only guard is looking.
        for name, needle in [
            ("a grant's sub-documents are its own parts", "function subdocsOf"),
            ("grant parts have a structure view", "function vGrant"),
            ("funders' formats are presets", "const GRANT_FORMATS"),
            ("the EPSRC standard research grant is a preset", 'id:"epsrc_std"'),
            ("an old grant becomes the legacy four parts", 'id:"legacy"'),
            ("a part's words are counted as they would be pasted", "function partPlain"),
            ("a text box part is copied for the form", "function copyForForm"),
            ("references print in one part, or in each", "function partBib"),
            ("a compact reference style saves words", "function compactBib"),
            ("the Funding Service attachment has its own layout", 'id:"tpl_epsrc_fs"'),
            ("a grant part prints no title, byline or abstract", "function previewGrantPart"),
            ("attachment parts are counted in real pages", "function partPages"),
        ]:
            check(name, needle in html, needle)

        # Style files: a layout, and for a grant the funder's structure, saved
        # as one file and imported into My templates. Same guard as above.
        for name, needle in [
            ("a style file is read through a whitelist", "function readStyleText"),
            ("a newer style file version is refused", "SF_VERSION"),
            ("a style file's logo must be an embedded raster image", "SF_LOGO_RE"),
            ("a style file is written from what the reader accepts", "function sfBundleToFile"),
            ("any template can be exported as a style file", "data-tplexport"),
            ("the Formatting view exports its formatting", 'id="sfExportFmt"'),
            ("Application parts exports the grant's format", 'id="sfExportGrant"'),
            ("style files are imported from Templates", 'id="sfImport"'),
            ("style files are imported from Application parts", 'id="sfImportGrant"'),
            ("an import is previewed before anything changes", "function openStyleImport"),
            ("imported grant formats are offered with the built-in presets",
             "function grantFormatOptions"),
            ("a preset is found among the user's own formats too", "||userGrantFormat(id)||"),
            # From the review of the merged tree: a key or font named like an
            # Object member, layouts that do not fit the page, a template
            # deleted from under a document, and a browser whose storage fills.
            ("fonts are looked up as own keys", "Object.prototype.hasOwnProperty.call(FONT_STACKS,k)"),
            ("form answers are read as the document's own", "Object.assign(Object.create(null),formAnswers())"),
            ("a resolved format is fitted to its page", "function fitFormatToPage"),
            ("migrate() mends fonts and colours an older build let in", "repairLayouts();"),
            ("a document keeps the layout of a template deleted from under it",
             "S.keptLayout.id === id ? S.keptLayout"),
            ("deleting a template in use asks first", "function deleteUserTemplate"),
            ("an import checks the browser has room for it", "function storageHasRoom"),
            ("a save the browser cannot hold says so", "storageFailed(e)"),
        ]:
            check(name, needle in html, needle)

        # Citation styles: a journal's own CSL or BibTeX style, imported into
        # the library. Same guard as above.
        for name, needle in [
            ("CSL styles run on the page's own processor", "function cslParse"),
            ("a CSL style declaring a DOCTYPE or entities is refused",
             "(<!DOCTYPE>/<!ENTITY>)"),
            ("styleOf resolves an imported style", "const c=citeStyleOf(e); if(c) return c;"),
            ("a dependent CSL style stands in with the nearest built-in shape",
             "const CSL_PARENT_SHAPES"),
            ("a list style that sorts sets the order and the numbers",
             "return citeStyleOrder(nums);"),
            ("an imported style prints its own in-text citations", "S.citeText(refs,nums,all)"),
            ("an imported style sets its own list on the page and in exports",
             "function bibListHTML"),
            ("an imported style sets its own list in Word", "function bibDocxParas"),
            ("an imported style's plain-text list counts its own numbers",
             "function bibPlainLines"),
            ("small caps reach Word", "<w:smallCaps/>"),
            ("a style is previewed before it is added", "function styleImportPreview"),
            ("the BibTeX engine has its own block", "function bstParse"),
            ("a style file carries an imported style's source", "citeRefOut(e,o)"),
            ("the citation-style rules are one block of the stylesheet",
             "/* ---- citation styles: CSL and BibTeX ---- */"),
            # From the review of the merged tree: a style that loops or blows up
            # its macros, one that names Object's members, and a library an
            # earlier build let such a style into.
            ("macro loops and blow-ups are refused before a style runs",
             "function cslMacroCost"),
            ("every step of the CSL engine spends from a budget", "cslSpend(this);"),
            ("a term's form is one CSL defines", "CSL_TERM_FORMS.includes(form)"),
            ("a stored style is held to today's checks when the page loads",
             'if(e.base==="csl"){ const P=citeParse("csl",src);'),
            ("one style cannot take the Style library down", "function citeSafe"),
        ]:
            check(name, needle in html, needle)

        # A kind alone plans a grant with no parts: the legacy four. A saved
        # grant's tree is named after its own parts.
        r = client.get("/api/layout/preview", params={"kind": "grant"}, headers=auth)
        paths = [n["path"] for n in r.json().get("nodes", [])] if r.status_code == 200 else []
        check("a grant with no parts yet plans the legacy four exports",
              "case-for-support.docx" in paths and "summary-impact.docx" in paths, str(paths[:6]))
        parts = [{"k": "g_sum", "l": "Summary", "mode": "textbox"},
                 {"k": "g_va", "l": "Vision and Approach", "mode": "attachment"}]
        r = client.post("/api/documents", headers=auth,
                        json={"title": "Parts grant", "kind": "grant",
                              "state": {"kind": "grant", "title": "Parts grant",
                                        "grantParts": parts}})
        gid = r.json().get("id") if r.status_code == 201 else None
        tree = client.get(f"/api/documents/{gid}/tree", headers=auth).json() if gid else {}
        tpaths = [n["path"] for n in tree.get("nodes", [])]
        check("a saved grant's tree names its exports after its parts",
              "vision-and-approach.docx" in tpaths and "case-for-support.docx" not in tpaths,
              str([p for p in tpaths if p.endswith(".docx")]))

        # The fixed sub-document table is written twice, here and in layout.py;
        # the export names the interface draws are only right if they agree.
        from app.services.layout import SUBDOCS as LAYOUT_SUBDOCS
        m = re.search(r"const SUBDOCS = \{(.*?)\n\};", html, re.S)
        page_subdocs = {}
        for kind, body in re.findall(r"(\w+):\[(.*?)\]", m.group(1) if m else ""):
            page_subdocs[kind] = re.findall(r'\{k:"([^"]+)",l:"([^"]+)"\}', body)
        check("the interface's sub-documents match layout.py's",
              page_subdocs == {k: list(v) for k, v in LAYOUT_SUBDOCS.items()},
              str(page_subdocs))

        # The interface keeps its own copy of LIBRARY_KEYS, and a key present
        # in one list and not the other is how a new document silently wipes
        # somebody's shared library. Compare them rather than trusting them.
        from app.services.store import LIBRARY_KEYS
        m = re.search(r"const LIBRARY_KEYS=\[(.*?)\];", html)
        page_keys = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
        check("the interface's library keys match the vault's",
              page_keys == set(LIBRARY_KEYS),
              "only in page: %s; only in vault: %s" % (
                  sorted(page_keys - set(LIBRARY_KEYS)),
                  sorted(set(LIBRARY_KEYS) - page_keys)))

        # The example document ships to strangers. Nobody's name, employer or
        # research topic belongs in it; the credit line in the header is the
        # one place a person is named on purpose.
        leaked = [w for w in ("HarwellXPS", "UCL", "SBA-15", "Parlett", "ucl.ac.uk")
                  if w in html]
        check("the example names nobody and nothing real", not leaked, ", ".join(leaked))
        check("the credit line is still there", "Created by <b>Dr Mark Isaacs</b>" in html)
        shown = without_comments(html)
        internal = [w for w in INTERNAL_NAMES if w in shown]
        check("the interface shows no internal design names or the old product name",
              not internal, ", ".join(internal))
        check("taking the comments out leaves the interface's own text",
              shown.count('class="note') == html.count('class="note')
              and shown.count("placeholder=") == html.count("placeholder="))

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
