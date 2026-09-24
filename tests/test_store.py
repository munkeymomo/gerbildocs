"""The vault: documents, revisions, and the app-level library.

The split between document-scoped and library-scoped state is the thing worth
guarding here — it is what makes "start a new document and your references are
still there" true.
"""

import pytest

from app.services.store import LIBRARY_KEYS, Store


def _store(tmp_path) -> Store:
    return Store(tmp_path / "desk.sqlite")


def _state():
    return {
        "title": "Sub-monolayer titania",
        "kind": "publication",
        "abstract": "Solvent-free photocatalytic coupling…",
        "figures": [{"ref": "F1"}],
        "refs": [{"id": "r1", "title": "A paper"}],
        "samples": [{"id": "sm_07", "code": "TSB-07"}],
        "sampleProps": [{"id": "pd_sa", "label": "BET surface area"}],
        "defs": [{"id": "df_xps", "short": "XPS"}],
        "styleLib": [{"id": "st_afm", "label": "Adv. Funct. Mater."}],
        "me": {"name": "Mark Isaacs"},
    }


def test_state_splits_into_document_and_library():
    s = Store.__new__(Store)  # split_state needs no database
    doc, lib = Store.split_state(s, _state())
    assert "figures" in doc and "abstract" in doc
    for key in ("refs", "samples", "sampleProps", "defs", "styleLib", "me"):
        assert key in lib
        assert key not in doc


def test_library_survives_a_new_document(tmp_path):
    st = _store(tmp_path)
    doc, lib = st.split_state(_state())
    first = st.create_document("Sub-monolayer titania", "publication", str(tmp_path / "a"), doc)
    st.put_library(lib)

    fresh = {"title": "Something else", "kind": "report", "figures": []}
    second = st.create_document("Something else", "report", str(tmp_path / "b"), fresh)

    merged = st.merge_state(st.get_document(second)["state"])
    assert merged["title"] == "Something else"
    assert merged["refs"][0]["title"] == "A paper"
    assert merged["samples"][0]["code"] == "TSB-07"
    assert first != second


def test_library_keys_are_the_only_thing_the_library_accepts(tmp_path):
    st = _store(tmp_path)
    written = st.put_library({"refs": [1], "figures": [2], "nonsense": [3]})
    assert written == ["refs"]
    assert set(st.get_library()) == {"refs"}
    assert set(LIBRARY_KEYS) >= {"refs", "samples", "defs", "styleLib", "templates"}


def test_saving_updates_the_title_and_timestamp(tmp_path):
    st = _store(tmp_path)
    doc_id = st.create_document("Working title", "publication", str(tmp_path / "a"),
                                {"title": "Working title", "kind": "publication"})
    before = st.get_document(doc_id)["updated_at"]
    st.save_document(doc_id, {"title": "Final title", "kind": "publication"})
    row = st.get_document(doc_id)
    assert row["title"] == "Final title"
    assert row["updated_at"] >= before


def test_documents_list_newest_first(tmp_path):
    st = _store(tmp_path)
    a = st.create_document("A", "publication", str(tmp_path / "a"), {})
    b = st.create_document("B", "publication", str(tmp_path / "b"), {})
    st.save_document(a, {"title": "A", "kind": "publication"})
    assert [d["id"] for d in st.list_documents()][0] == a
    assert b in [d["id"] for d in st.list_documents()]


def test_revisions_are_numbered_in_order(tmp_path):
    st = _store(tmp_path)
    doc_id = st.create_document("A", "publication", str(tmp_path / "a"), {})
    assert st.add_revision(doc_id, {"label": "First", "by": "MI", "snapshot": {"x": 1}}) == 1
    assert st.add_revision(doc_id, {"label": "Second", "by": "CP",
                                    "kind": "amendment", "snapshot": {"x": 2}}) == 2
    listed = st.list_revisions(doc_id)
    assert [r["idx"] for r in listed] == [1, 2]
    assert listed[1]["kind"] == "amendment"
    assert st.get_revision(doc_id, 2)["snapshot"] == {"x": 2}


def test_forgetting_a_document_removes_its_revisions(tmp_path):
    st = _store(tmp_path)
    doc_id = st.create_document("A", "publication", str(tmp_path / "a"), {})
    st.add_revision(doc_id, {"label": "First", "by": "MI", "snapshot": {}})
    assert st.delete_document(doc_id) is True
    assert st.get_document(doc_id) is None
    assert st.list_revisions(doc_id) == []


def test_a_missing_document_is_none_not_an_error(tmp_path):
    assert _store(tmp_path).get_document("nope") is None


# ------------------------------------------------------------ opening it ---

_V1_SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL,
    root TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE library (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE revisions (id TEXT PRIMARY KEY, document_id TEXT NOT NULL, idx INTEGER NOT NULL,
    at TEXT NOT NULL, label TEXT NOT NULL, by TEXT NOT NULL, kind TEXT NOT NULL,
    snapshot TEXT NOT NULL);
INSERT INTO meta VALUES ('schema_version', '1');
INSERT INTO documents VALUES ('d1', 'Old', 'publication', '/x/old', '2026-01-01T00:00:00+00:00',
    '2026-02-01T00:00:00+00:00', '{"title": "Old", "kind": "publication"}');
"""


def test_a_fresh_vault_takes_no_backup_but_a_reopened_one_does(tmp_path):
    import sqlite3

    first = _store(tmp_path)
    assert first.backup_path is None
    doc_id = first.create_document("A", "publication", str(tmp_path / "a"), {"title": "A"})

    second = _store(tmp_path)
    assert second.backup_path is not None and second.backup_path.exists()
    assert second.backup_path.parent == tmp_path / "backups"
    # The backup is a complete, independent database with the document in it.
    conn = sqlite3.connect(second.backup_path)
    assert conn.execute("SELECT id FROM documents").fetchone()[0] == doc_id
    conn.close()


def test_only_the_last_few_backups_are_kept(tmp_path):
    from app.services.store import BACKUPS_KEPT

    _store(tmp_path)
    for _ in range(BACKUPS_KEPT + 3):
        _store(tmp_path)
    assert len(list((tmp_path / "backups").glob("desk-*.sqlite"))) == BACKUPS_KEPT


def test_a_corrupt_vault_is_moved_aside_and_the_backup_restored(tmp_path):
    st = _store(tmp_path)
    doc_id = st.create_document("Keep me", "publication", str(tmp_path / "a"),
                                {"title": "Keep me"})
    _store(tmp_path)  # reopening takes a backup that contains the document

    (tmp_path / "desk.sqlite").write_bytes(b"this is not a database" * 100)
    st = _store(tmp_path)

    assert st.get_document(doc_id)["title"] == "Keep me"
    quarantined = list(tmp_path.glob("desk.sqlite.corrupt-*"))
    assert any(p.suffix != ".txt" for p in quarantined), "the bad file must be kept, not deleted"
    assert any("moved to" in n and "restored" in n for n in st.notices)


def test_a_corrupt_vault_with_no_backup_recovers_the_library_from_the_mirror(tmp_path):
    st = Store(tmp_path / "desk.sqlite", library_dir=tmp_path / "library")
    st.put_library({"refs": [{"id": "r1", "title": "Mirrored"}], "samples": []})
    (tmp_path / "desk.sqlite").write_bytes(b"\0" * 4096)  # zeroed header: not a database
    # No backup exists yet (the vault was only ever opened once).
    assert not list((tmp_path / "backups").glob("*.sqlite"))

    st = Store(tmp_path / "desk.sqlite", library_dir=tmp_path / "library")
    assert st.get_library()["refs"][0]["title"] == "Mirrored"
    assert any("new, empty vault" in n for n in st.notices)
    assert any("recovered from its JSON mirror" in n for n in st.notices)


def test_the_library_is_mirrored_as_readable_json(tmp_path):
    import json

    st = Store(tmp_path / "desk.sqlite", library_dir=tmp_path / "library")
    st.put_library({"defs": [{"id": "df_xps", "short": "XPS"}], "nonsense": 1})
    mirrored = json.loads((tmp_path / "library" / "defs.json").read_text(encoding="utf-8"))
    assert mirrored[0]["short"] == "XPS"
    assert not (tmp_path / "library" / "nonsense.json").exists()
    assert not list((tmp_path / "library").glob(".*.tmp")), "no temp file left behind"


def test_a_version_1_vault_is_migrated_in_place(tmp_path):
    import sqlite3

    from app.services.store import SCHEMA_VERSION

    path = tmp_path / "desk.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    conn.close()

    st = _store(tmp_path)
    assert st.schema_version == SCHEMA_VERSION
    row = st.get_document("d1")
    assert row["opened_at"] == "2026-02-01T00:00:00+00:00"  # back-filled from updated_at
    assert any("migrated to schema version 2" in n for n in st.notices)
    # Re-opening does not run it again.
    assert not any("migrated" in n for n in _store(tmp_path).notices)


def test_a_vault_from_a_newer_release_is_refused_not_downgraded(tmp_path):
    import sqlite3

    from app.services.store import VaultTooNew

    path = tmp_path / "desk.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    conn.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
    conn.commit()
    conn.close()
    with pytest.raises(VaultTooNew):
        _store(tmp_path)
    assert path.exists(), "refusing must not touch the file"


def test_documents_list_by_last_opened_and_find_by_root(tmp_path):
    st = _store(tmp_path)
    a = st.create_document("A", "publication", str(tmp_path / "a"), {})
    b = st.create_document("B", "publication", str(tmp_path / "b"), {})
    st.mark_opened(a)
    assert [d["id"] for d in st.list_documents()][0] == a
    assert st.find_by_root(str(tmp_path / "b"))["id"] == b
    assert st.find_by_root(str(tmp_path / "nowhere")) is None


def test_a_user_template_survives_a_document_switch(tmp_path):
    """Templates are app-scoped: made once, used by every document after."""
    st = _store(tmp_path)
    tpl = {"id": "my_report", "label": "Lab report",
           "page": {"pageNumbers": True, "header": {"centre": "{title}"}}}
    st.put_library({"templates": [tpl]})
    a = st.create_document("A", "report", str(tmp_path / "a"),
                           {"title": "A", "kind": "report", "templates": [tpl]})
    b = st.create_document("B", "report", str(tmp_path / "b"),
                           {"title": "B", "kind": "report"})
    # The document's own row never carries them; the library is put back on top.
    assert "templates" not in st.get_document(b)["state"]
    assert st.merge_state(st.get_document(b)["state"])["templates"] == [tpl]
    assert st.merge_state(st.get_document(a)["state"])["templates"] == [tpl]


def test_saved_people_and_organisations_are_app_scoped(tmp_path):
    """A person and their usual organisations are typed once per installation."""
    import json

    st = Store(tmp_path / "desk.sqlite", library_dir=tmp_path / "library")
    person = {"id": "p_mi", "name": "Isaacs, Mark A.", "orcid": "0000-0003-0335-4451",
              "email": "mark@example.ac.uk",
              "orgs": [{"name": "Example University", "dept": "Chemistry",
                        "city": "London", "country": "UK", "ror": ""}],
              "credit": ["Conceptualization"]}
    org = {"id": "ol_fac", "name": "Example Facility", "dept": "Surface Analysis Centre",
           "city": "Didcot", "country": "UK", "ror": ""}
    written = st.put_library({"peopleLib": [person], "orgLib": [org]})
    assert set(written) == {"peopleLib", "orgLib"}

    lib = st.get_library()
    assert lib["peopleLib"] == [person]
    assert lib["orgLib"] == [org]

    mirrored = json.loads((tmp_path / "library" / "peopleLib.json").read_text(encoding="utf-8"))
    assert mirrored[0]["orgs"][0]["name"] == "Example University"
    assert json.loads(
        (tmp_path / "library" / "orgLib.json").read_text(encoding="utf-8")
    )[0]["name"] == "Example Facility"

    # They are library-scoped, so a document's own row never carries them.
    doc, library = st.split_state({"title": "A", "kind": "report",
                                   "peopleLib": [person], "orgLib": [org]})
    assert "peopleLib" not in doc and "orgLib" not in doc
    assert library == {"peopleLib": [person], "orgLib": [org]}
    d = st.create_document("A", "report", str(tmp_path / "a"), doc)
    assert st.merge_state(st.get_document(d)["state"])["peopleLib"] == [person]


def test_settings_round_trip_and_default(tmp_path):
    st = Store(tmp_path / "v.sqlite")
    assert st.get_setting("library_roots", []) == []
    st.put_setting("library_roots", [{"path": "D:/Papers", "label": "Papers"}])
    assert st.get_setting("library_roots") == [{"path": "D:/Papers", "label": "Papers"}]
    st.put_setting("library_roots", [])
    assert st.get_setting("library_roots") == []


def test_saved_text_blocks_are_library_scoped(tmp_path):
    """A saved Experimental section belongs to the installation, not to the
    paper it was written for — that is the whole point of saving it."""
    import json

    st = Store(tmp_path / "v.sqlite", library_dir=tmp_path / "library")
    blocks = [{"id": "sn_1", "title": "XPS experimental", "folder": "Experimental",
               "text": "Spectra were recorded on…\n\nBinding energies were referenced to…",
               "updatedAt": "2026-09-24T12:00:00+00:00"}]
    folders = ["Experimental", "Characterisation", "Unfiled"]

    written = st.put_library({"snippets": blocks, "snippetFolders": folders})
    assert set(written) == {"snippets", "snippetFolders"}

    lib = st.get_library()
    assert lib["snippets"] == blocks
    assert lib["snippetFolders"] == folders

    mirrored = json.loads((tmp_path / "library" / "snippets.json").read_text(encoding="utf-8"))
    assert mirrored[0]["title"] == "XPS experimental"
    assert "\n\n" in mirrored[0]["text"]          # the paragraph break survives

    doc, library = st.split_state({"title": "A", "kind": "report",
                                   "snippets": blocks, "snippetFolders": folders})
    assert "snippets" not in doc and "snippetFolders" not in doc
    d = st.create_document("A", "report", str(tmp_path / "a"), doc)
    merged = st.merge_state(st.get_document(d)["state"])
    assert merged["snippets"] == blocks and merged["snippetFolders"] == folders
