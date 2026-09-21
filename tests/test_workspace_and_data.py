"""Writing into a document folder, and assembling the deposition set."""

import hashlib

import pytest

from app.services import attachments as att
from app.services.safety import PathEscape, resolve_within, safe_name
from app.services.workspace import Workspace


# ------------------------------------------------------------------ safety --

def test_relative_paths_resolve_inside_the_root(tmp_path):
    assert resolve_within(tmp_path, "figures/figure-01/a.png") == \
        (tmp_path / "figures/figure-01/a.png").resolve()


@pytest.mark.parametrize("bad", [
    "../escape.txt",
    "figures/../../escape.txt",
    "/etc/passwd",
    "C:/Windows/system32",
    "",
])
def test_paths_that_leave_the_root_are_refused(tmp_path, bad):
    with pytest.raises(PathEscape):
        resolve_within(tmp_path, bad)


def test_safe_name_strips_what_windows_will_not_take():
    assert safe_name('sp"ec<tra>.vms') == "sp_ec_tra_.vms"
    assert safe_name("../../evil.sh") == "evil.sh"
    assert safe_name("CON.txt").startswith("_")
    assert safe_name("") == "file"


# --------------------------------------------------------------- workspace --

def test_create_makes_a_folder_named_after_the_title(tmp_path):
    ws = Workspace.create(tmp_path, "Sub-monolayer TiO2 on SBA-15")
    assert ws.root.name == "sub-monolayer-tio2-on-sba-15"
    assert (ws.root / "figures").is_dir()
    assert (ws.root / "data").is_dir()


def test_creating_the_same_title_twice_does_not_collide(tmp_path):
    a = Workspace.create(tmp_path, "Same title")
    b = Workspace.create(tmp_path, "Same title")
    assert a.root != b.root
    assert b.root.name == "same-title-2"


def test_ensure_tree_is_idempotent(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    doc = {"kind": "publication", "figures": [{"ref": "F1", "panels": []}]}
    first = ws.ensure_tree(doc)
    second = ws.ensure_tree(doc)
    assert "figures/figure-01" in first
    assert second == []


def test_writes_land_where_the_layout_says(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    r = ws.write_text("manuscript.docx", "not really a docx")
    assert r.path == ws.root / "manuscript.docx"
    assert r.created is True
    again = ws.write_text("manuscript.docx", "replaced")
    assert again.created is False
    assert ws.read_bytes("manuscript.docx") == b"replaced"


def test_a_write_cannot_escape_the_document_folder(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    with pytest.raises(PathEscape):
        ws.write_text("../outside.txt", "no")


def test_tree_reports_what_is_actually_on_disk(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    doc = {"kind": "report"}
    ws.write_text("report.docx", "x")
    nodes = {n["path"]: n for n in ws.tree(doc)}
    assert nodes["report.docx"]["present"] is True
    assert nodes["report.docx"]["bytes"] == 1
    assert nodes["appendices.docx"]["present"] is False


# -------------------------------------------------------------- deposition --

def _doc():
    return {
        "kind": "publication",
        "title": "Sub-monolayer titania",
        "authors": [{"name": "Mark Isaacs"}, {"name": "Arthur Graf"}],
        "figures": [{"ref": "F1"}],
        "tables": [{"ref": "T1"}],
        "repo": "Zenodo",
        "datasetDoi": "10.5281/zenodo.0000000",
    }


def test_attaching_bytes_files_them_under_the_figure(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    doc = _doc()
    ws.ensure_tree(doc)
    payload = b"VAMAS\n" * 100
    rec = att.attach_bytes(ws, doc, "F1", "Ti2p.vms", payload, attachment_id="at_1",
                           content_type="chemical/x-vamas", note="Ti 2p regions")
    assert rec.rel_path == "data/figure-01/Ti2p.vms"
    assert (ws.root / rec.rel_path).read_bytes() == payload
    assert rec.bytes == len(payload)
    assert rec.sha256 == hashlib.sha256(payload).hexdigest()


def test_attaching_a_file_on_disk_copies_and_hashes_it(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    doc = _doc()
    src = tmp_path / "isotherms.xlsx"
    src.write_bytes(b"\x50\x4b\x03\x04fake")
    rec = att.attach_file(ws, doc, "T1", src, attachment_id="at_2")
    assert rec.rel_path == "data/table-01/isotherms.xlsx"
    assert rec.sha256 == hashlib.sha256(b"\x50\x4b\x03\x04fake").hexdigest()
    assert src.exists(), "the original must not be moved"


def test_an_unrecognised_target_still_files_somewhere(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    rec = att.attach_bytes(ws, _doc(), "F9", "stray.csv", b"a,b\n", attachment_id="at_3")
    assert rec.rel_path == "data/unassigned/stray.csv"


def test_manifest_names_what_each_file_supports(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    doc = _doc()
    a = att.attach_bytes(ws, doc, "F1", "Ti2p.vms", b"x" * 10, attachment_id="at_1",
                         note="Ti 2p regions")
    b = att.attach_bytes(ws, doc, "T1", "bet.xlsx", b"y" * 20, attachment_id="at_2")
    rows = att.manifest_csv(doc, [a.to_dict(), b.to_dict()]).splitlines()
    assert rows[0].startswith("file,supports,bytes,sha256")
    assert "Figure 1" in rows[1] and "Ti 2p regions" in rows[1]
    assert "Table 1" in rows[2]


def test_rewriting_the_manifest_writes_both_generated_files(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    doc = _doc()
    a = att.attach_bytes(ws, doc, "F1", "Ti2p.vms", b"x" * 2048, attachment_id="at_1")
    summary = att.rewrite_manifest(ws, doc, [a.to_dict()])
    assert (ws.root / "data/MANIFEST.csv").exists()
    readme = (ws.root / "data/README.md").read_text(encoding="utf-8")
    assert "# Data for: Sub-monolayer titania" in readme
    assert "Figure 1" in readme
    assert summary["files"] == 1 and summary["bytes"] == 2048


def test_the_availability_statement_names_the_repository_and_the_files(tmp_path):
    ws = Workspace.create(tmp_path, "Doc")
    doc = _doc()
    a = att.attach_bytes(ws, doc, "F1", "Ti2p.vms", b"x", attachment_id="at_1")
    b = att.attach_bytes(ws, doc, "T1", "bet.xlsx", b"y", attachment_id="at_2")
    text = att.data_availability_statement(doc, [a.to_dict(), b.to_dict()])
    assert "Zenodo" in text and "10.5281/zenodo.0000000" in text
    assert "Figure 1 and Table 1" in text
    assert "Ti2p.vms" in text and "bet.xlsx" in text


def test_no_attachments_gives_a_prompt_not_a_broken_sentence():
    assert att.data_availability_statement(_doc(), []).startswith("Attach raw data")


# ------------------------------------------------ the document in its folder --

def test_the_document_is_mirrored_into_its_folder_and_read_back(tmp_path):
    import json

    ws = Workspace.create(tmp_path, "Mirrored")
    doc = {"title": "Mirrored", "kind": "report", "subdocs": {"manuscript": {"sections": []}}}
    r = ws.write_document_state(doc)
    assert r.path == ws.root / "document.json" and r.created
    on_disk = json.loads(r.path.read_text(encoding="utf-8"))
    assert on_disk["state"] == doc and on_disk["title"] == "Mirrored"
    assert not list(ws.root.glob(".*.tmp")), "no temp file left behind"

    folder = Workspace.read_document_folder(ws.root)
    assert folder.title == "Mirrored" and folder.kind == "report"
    assert folder.state == doc


def test_a_folder_without_a_document_is_refused_not_created(tmp_path):
    from app.services.workspace import NotADocumentFolder

    (tmp_path / "plain").mkdir()
    with pytest.raises(NotADocumentFolder):
        Workspace.read_document_folder(tmp_path / "plain")
    with pytest.raises(NotADocumentFolder):
        Workspace.read_document_folder(tmp_path / "missing")
    (tmp_path / "plain" / "document.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(NotADocumentFolder):
        Workspace.read_document_folder(tmp_path / "plain")
    (tmp_path / "plain" / "document.json").write_text('{"state": {"no": "subdocs"}}',
                                                       encoding="utf-8")
    with pytest.raises(NotADocumentFolder):
        Workspace.read_document_folder(tmp_path / "plain")
    assert not (tmp_path / "missing").exists()


def test_discover_finds_document_folders_and_ignores_the_rest(tmp_path):
    from app.services.workspace import discover

    a = Workspace.create(tmp_path, "Older")
    a.write_document_state({"title": "Older", "kind": "publication", "subdocs": {}})
    b = Workspace.create(tmp_path, "Newer")
    b.write_document_state({"title": "Newer", "kind": "grant", "subdocs": {}})
    (tmp_path / "newer" / "document.json").write_text(
        (tmp_path / "newer" / "document.json").read_text(encoding="utf-8")
        .replace('"saved_at": "', '"saved_at": "9999-'), encoding="utf-8")
    (tmp_path / "not-a-document").mkdir()
    (tmp_path / "loose-file.txt").write_text("x", encoding="utf-8")

    found = discover(tmp_path)
    assert [d.title for d in found] == ["Newer", "Older"]
    assert discover(tmp_path / "does-not-exist") == []


# -------------------------------------------------------------------- reveal --

def test_reveal_picks_the_platform_command(tmp_path):
    from app.services import reveal

    ran = []
    reveal.reveal(tmp_path, platform="linux", run=ran.append)
    reveal.reveal(tmp_path, platform="darwin", run=ran.append)
    reveal.reveal(tmp_path, platform="win32", run=ran.append)
    assert ran == [["xdg-open", str(tmp_path)], ["open", str(tmp_path)],
                   ["startfile", str(tmp_path)]]


def test_reveal_refuses_a_folder_that_does_not_exist(tmp_path):
    from app.services import reveal

    with pytest.raises(FileNotFoundError):
        reveal.reveal(tmp_path / "gone", platform="linux", run=lambda c: None)


# ------------------------------------------------- identifying our folders --

def test_a_folder_we_stamped_is_ours_even_before_the_interface_touches_it(tmp_path):
    """A document created through the API and not yet opened has no `subdocs`.
    It is still one of our documents, and must be discoverable and adoptable."""
    from app.services.workspace import discover

    ws = Workspace.create(tmp_path, "Fresh")
    ws.write_document_state({"title": "Fresh", "kind": "publication"})

    folder = Workspace.read_document_folder(ws.root)
    assert folder.title == "Fresh"
    assert folder.kind == "publication"
    assert [f.root for f in discover(tmp_path)] == [ws.root]


def test_a_json_file_that_is_not_ours_is_refused(tmp_path):
    from app.services.workspace import NotADocumentFolder

    root = tmp_path / "impostor"
    root.mkdir()
    (root / "document.json").write_text('{"state": {"anything": 1}}', encoding="utf-8")
    with pytest.raises(NotADocumentFolder):
        Workspace.read_document_folder(root)


def test_an_older_document_without_the_stamp_still_opens(tmp_path):
    import json as _json

    root = tmp_path / "legacy"
    root.mkdir()
    (root / "document.json").write_text(
        _json.dumps({"title": "Legacy", "state": {"subdocs": {}, "kind": "report"}}),
        encoding="utf-8")
    folder = Workspace.read_document_folder(root)
    assert folder.title == "Legacy" and folder.kind == "report"


# ---------------------------------------------------------------- library --

def _make_doc(base, name, title):
    ws = Workspace(base / name)
    ws.root.mkdir(parents=True)
    ws.write_document_state({"title": title, "kind": "publication"})
    return ws


def test_discover_tree_finds_documents_in_subfolders_and_prunes_empty_ones(tmp_path):
    from app.services.workspace import discover_tree
    _make_doc(tmp_path, "top-level", "Top")
    _make_doc(tmp_path / "2026" / "papers", "deep", "Deep")
    (tmp_path / "empty" / "nothing").mkdir(parents=True)
    (tmp_path / ".hidden" ).mkdir()
    _make_doc(tmp_path / ".hidden", "secret", "Hidden")
    tree = discover_tree(tmp_path)
    assert [d.title for d in tree.documents] == ["Top"]
    assert [c.name for c in tree.children] == ["2026"]
    assert tree.children[0].children[0].documents[0].title == "Deep"
    assert tree.total == 2


def test_discover_tree_does_not_walk_inside_a_document(tmp_path):
    from app.services.workspace import discover_tree
    ws = _make_doc(tmp_path, "doc", "Doc")
    _make_doc(ws.root / "figures", "nested", "Should not be found")
    tree = discover_tree(tmp_path)
    assert tree.total == 1


def test_discover_tree_respects_depth(tmp_path):
    from app.services.workspace import discover_tree
    _make_doc(tmp_path / "a" / "b" / "c", "deep", "Deep")
    assert discover_tree(tmp_path, depth=1).total == 0
    assert discover_tree(tmp_path, depth=3).total == 1
