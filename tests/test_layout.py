"""The folder layout is the spec; these tests are what stops it drifting."""

from app.services import layout


def test_slug_is_filesystem_safe():
    assert layout.slug("Understanding the Chemical & Electronic Properties!") == \
        "understanding-the-chemical-electronic-properties"
    assert layout.slug("   ") == "untitled"
    assert layout.slug("Ti–SBA-15 / 0.7 ML") == "ti-sba-15-0-7-ml"
    assert len(layout.slug("x" * 300)) <= 60


def test_subdoc_filenames_follow_the_kind():
    assert layout.subdoc_filename("publication", "si") == "supporting-information.docx"
    assert layout.subdoc_filename("report", "si") == "appendices.docx"
    assert layout.subdoc_filename("grant", "manuscript") == "case-for-support.docx"
    # The labels mirror the interface's, so the file names it draws are these.
    assert layout.subdoc_filename("grant", "cover") == "summary-impact.docx"
    assert layout.subdoc_filename("publication", "manuscript", "pdf") == "manuscript.pdf"


def _grant(parts=None, subdocs=None):
    doc = {"kind": "grant", "title": "A grant", "subdocs": subdocs or {}}
    if parts is not None:
        doc["grantParts"] = parts
    return doc


def test_a_grant_names_its_exports_after_its_own_parts():
    doc = _grant([
        {"k": "g_sum0001", "l": "Summary", "mode": "textbox", "words": 550},
        {"k": "g_va00001", "l": "Vision and Approach", "mode": "attachment", "pages": 6},
        {"k": "g_team001", "l": "Applicant and team capability to deliver", "mode": "textbox"},
    ])
    assert layout.subdoc_filename(doc, "g_va00001") == "vision-and-approach.docx"
    assert layout.subdoc_filename(doc, "g_sum0001", "pdf") == "summary.pdf"
    paths = [p.path for p in layout.plan_document(doc)]
    exports = [p for p in paths if p.endswith(".docx")]
    # One export per part, in the application's order, and nothing from the
    # fixed grant list the parts replaced.
    assert exports == ["summary.docx", "vision-and-approach.docx",
                       "applicant-and-team-capability-to-deliver.docx"]
    assert "case-for-support.docx" not in paths


def test_a_grant_written_before_parts_keeps_its_four_files():
    doc = _grant()
    assert layout.subdocs_for(doc) == layout.SUBDOCS["grant"]
    paths = [p.path for p in layout.plan_document(doc)]
    for expected in ("case-for-support.docx", "justification-of-resources.docx",
                     "summary-impact.docx", "data-management.docx"):
        assert expected in paths
    # An empty list is not a definition either: fall back rather than plan nothing.
    assert layout.subdoc_filename(_grant([]), "manuscript") == "case-for-support.docx"


def test_parts_are_read_only_for_grants():
    """A publication carrying a stray `grantParts` still has its own four files."""
    doc = {"kind": "publication", "grantParts": [{"k": "g_x", "l": "Odd one out"}]}
    assert [k for k, _ in layout.subdocs_for(doc)] == ["manuscript", "si", "cover", "dmp"]
    assert layout.subdoc_filename(doc, "si") == "supporting-information.docx"


def test_two_parts_with_one_name_do_not_share_a_file():
    doc = _grant([{"k": "g_a", "l": "New part"}, {"k": "g_b", "l": "New part"},
                  {"k": "g_c", "l": "New part"}])
    assert layout.subdoc_filenames(doc) == {"g_a": "new-part.docx", "g_b": "new-part-2.docx",
                                           "g_c": "new-part-3.docx"}


def test_a_part_with_no_name_is_filed_under_its_key():
    """The interface does the same (`subdocFilenames`), so the two plans agree."""
    doc = _grant([{"k": "g_first", "l": ""}, {"k": "g_second", "l": "   "}])
    assert layout.subdoc_filenames(doc) == {"g_first": "g-first.docx", "g_second": "untitled.docx"}


def test_a_grant_orders_equations_by_its_parts_not_by_the_dict():
    doc = _grant(
        [{"k": "g_first", "l": "Vision and Approach"}, {"k": "g_second", "l": "Summary"}],
        {"g_second": {"sections": [{"blocks": [{"type": "eq", "latex": "later"}]}]},
         "g_first": {"sections": [{"blocks": [{"type": "eq", "latex": "earlier"}]}]}},
    )
    assert [e["latex"] for e in layout.equations_in_order(doc)] == ["earlier", "later"]


def test_figure_and_table_folders_are_zero_padded():
    assert layout.figure_dir(1) == "figures/figure-01"
    assert layout.figure_dir(12) == "figures/figure-12"
    assert layout.table_dir(3) == "tables/table-03"
    assert layout.data_dir("figure", 2) == "data/figure-02"


def test_attachments_resolve_to_the_figure_or_table_they_support():
    doc = {
        "figures": [{"ref": "F1"}, {"ref": "F2"}],
        "tables": [{"ref": "T1"}],
    }
    assert layout.attachment_dir(doc, "F2") == "data/figure-02"
    assert layout.attachment_dir(doc, "T1") == "data/table-01"
    assert layout.attachment_dir(doc, "F9") == "data/unassigned"


def _doc():
    return {
        "kind": "publication",
        "title": "Sub-monolayer titania",
        "figures": [{"ref": "F1", "panels": [{"src": "P1"}, {"src": None}, {"src": "P3"}]}],
        "tables": [{"ref": "T1"}],
        "plots": [{"id": "P1", "ref": "P1", "name": "Ti 2p"},
                  {"id": "P3", "ref": "P3", "name": "Si 2p"}],
        "subdocs": {
            "si": {"sections": [{"blocks": [{"type": "eq", "latex": "b", "numbered": False}]}]},
            "manuscript": {"sections": [
                {"blocks": [{"type": "p", "text": "prose"},
                            {"type": "eq", "latex": "a", "label": "eq:ke"}]},
            ]},
        },
        "attachments": [
            {"name": "spectra.vms", "target": "F1"},
            {"name": "isotherms.xlsx", "target": "T1"},
        ],
        "revisions": [{"label": "First full draft", "by": "Jane Doe"}],
        "reviews": [{"reviewer": "Reviewer 1", "comments": []}],
    }


def test_plan_covers_every_sub_document():
    paths = [p.path for p in layout.plan_document(_doc())]
    for expected in ("manuscript.docx", "supporting-information.docx",
                     "cover-letter.docx", "data-management.docx"):
        assert expected in paths


def test_plan_places_panels_and_data_where_the_interface_says():
    paths = [p.path for p in layout.plan_document(_doc())]
    assert "figures/figure-01" in paths
    assert "figures/figure-01/figure-01.svg" in paths
    assert "figures/figure-01/P1.plotspec.json" in paths
    assert "figures/figure-01/P3.plotspec.json" in paths
    assert "tables/table-01/table-01.csv" in paths
    assert "data/figure-01/spectra.vms" in paths
    assert "data/table-01/isotherms.xlsx" in paths
    assert "data/MANIFEST.csv" in paths
    assert "drafts/rev-01-first-full-draft.json" in paths
    assert "reviews/reviewer-1.json" in paths


def test_empty_panels_do_not_produce_paths():
    paths = [p.path for p in layout.plan_document(_doc())]
    assert not any(p.endswith("None.plotspec.json") for p in paths)


def test_directories_are_unique_and_ordered():
    dirs = layout.directories(_doc())
    assert dirs == list(dict.fromkeys(dirs))
    assert dirs.index("figures") < dirs.index("figures/figure-01")
    assert "data" in dirs and "data/figure-01" in dirs


def test_a_document_with_nothing_in_it_still_has_a_shape():
    dirs = layout.directories({"kind": "report"})
    assert dirs == ["figures", "tables", "plots", "equations", "data", "references", "drafts"]


def test_plots_and_equations_are_planned_for_the_deposit():
    paths = [p.path for p in layout.plan_document(_doc())]
    assert "plots/P1.csv" in paths
    assert "plots/P3.csv" in paths
    assert "equations/equation-01.tex" in paths
    assert "equations/equation-02.tex" in paths
    assert "equations/equation-03.tex" not in paths


def test_equations_are_ordered_by_sub_document_then_by_block():
    """The manuscript comes before the SI whatever order the dict is in, so
    equation-01 is the first equation a reader meets."""
    eqs = layout.equations_in_order(_doc())
    assert [e["latex"] for e in eqs] == ["a", "b"]


def test_an_unnumbered_equation_is_still_deposited_and_says_so():
    notes = {p.path: p.note for p in layout.plan_document(_doc())}
    assert notes["equations/equation-01.tex"] == "eq:ke · numbered"
    assert notes["equations/equation-02.tex"] == "unnumbered"


def test_the_deposit_readme_is_last_in_the_plan():
    plan = layout.plan_document(_doc())
    assert plan[-1].path == layout.DEPOSIT_FILE == "DEPOSIT.md"
    assert plan[-1].generated is True


def test_a_plot_reference_is_planned_verbatim_so_the_workspace_can_refuse_it():
    """layout plans, it does not sanitise: `resolve_within` is the gatekeeper,
    and it can only refuse what it is actually given."""
    assert layout.plot_csv("../../etc/passwd") == "plots/../../etc/passwd.csv"


def test_the_document_itself_is_first_in_the_plan():
    plan = layout.plan_document(_doc())
    assert plan[0].path == layout.DOCUMENT_FILE == "document.json"
    assert plan[0].generated is True


def test_raw_data_attached_to_a_plot_files_under_that_plot():
    doc = {"figures": [{"ref": "F1"}], "tables": [{"ref": "T1"}],
           "plots": [{"ref": "P1"}, {"ref": "P2"}, {"ref": "P3"}]}
    assert layout.attachment_dir(doc, "P3") == "data/plot-03"
    assert layout.attachment_dir(doc, "F1") == "data/figure-01"
    assert layout.attachment_dir(doc, "P9") == "data/unassigned"


def test_profile_with_a_byte_order_mark_still_loads(tmp_path):
    """Notepad and PowerShell both write a BOM; json.loads refuses one."""
    from app.config import Profile

    p = tmp_path / "profile.json"
    p.write_text('{"name": "Custom"}', encoding="utf-8-sig")
    assert Profile.load(p).name == "Custom"


def test_unreadable_profile_falls_back_instead_of_raising(tmp_path):
    """A cosmetic file must never be able to stop the application starting."""
    from app.config import Profile

    p = tmp_path / "profile.json"
    p.write_text("{ not json", encoding="utf-8")
    assert Profile.load(p).name == "GerbilDocs"
    assert p.read_text(encoding="utf-8") == "{ not json"   # left alone
