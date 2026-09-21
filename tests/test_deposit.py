"""Compiling a deposit: it lands where `layout` says, and nowhere else."""

import base64

import pytest

from app.services import layout
from app.services.deposit import compile_deposit
from app.services.safety import PathEscape
from app.services.workspace import Workspace

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n-not-a-real-png").decode()


def _state():
    return {
        "kind": "publication",
        "title": "Sub-monolayer titania on SBA-15",
        "authors": [{"name": "Mark Isaacs"}, {"name": "Chris Parlett"}],
        "repo": "Zenodo",
        "datasetDoi": "10.5281/zenodo.0000000",
        "figures": [{"ref": "F1", "panels": [{"src": "pl_1"}, {"src": None}]}],
        "tables": [{"ref": "T1"}],
        "plots": [{"id": "pl_1", "ref": "P1", "name": "Ti 2p", "series": []}],
        "attachments": [{"id": "at_1", "name": "Ti2p.vms", "target": "F1", "bytes": 704,
                         "rel_path": "data/figure-01/Ti2p.vms", "sha256": "a" * 64,
                         "note": "Ti 2p regions"}],
        "subdocs": {"manuscript": {"sections": [{"blocks": [
            {"type": "eq", "latex": r"E_k = h\nu - E_b - \phi", "label": "eq:ke"},
            {"type": "eq", "latex": r"\theta = I/I_0", "numbered": False},
        ]}]}},
    }


def _rendered():
    return {
        "figures": [{"ref": "F1", "svg": "<svg xmlns='http://www.w3.org/2000/svg'/>",
                     "png_base64": PNG}],
        "tables": [{"ref": "T1", "csv": "Sample,Coverage / ML\nTSB-07,0.7\n"}],
        "plots": [{"ref": "P1", "csv": "Binding energy / eV,0.2 ML\n458.5,1.0\n",
                   "spec": {"id": "pl_1", "ref": "P1", "chartType": "line"}}],
        "equations": [
            {"index": 1, "label": "eq:ke", "numbered": True,
             "latex": r"E_k = h\nu - E_b - \phi"},
            {"index": 2, "label": "", "numbered": False, "latex": r"\theta = I/I_0"},
        ],
    }


def _compile(tmp_path):
    ws = Workspace(tmp_path / "doc")
    return ws, compile_deposit(ws, _state(), _rendered())


def test_every_file_lands_where_the_layout_plans_it(tmp_path):
    ws, summary = _compile(tmp_path)
    planned = {p.path for p in layout.plan_document(_state())}
    for rel in ("figures/figure-01/figure-01.svg", "figures/figure-01/figure-01.png",
                "figures/figure-01/pl_1.plotspec.json", "tables/table-01/table-01.csv",
                "plots/P1.csv", "equations/equation-01.tex", "equations/equation-02.tex",
                "DEPOSIT.md"):
        assert rel in planned, f"{rel} is not in the plan"
        assert (ws.root / rel).is_file(), f"{rel} was not written"
        assert rel in summary["written"]


def test_the_bytes_are_the_ones_that_were_handed_over(tmp_path):
    ws, _ = _compile(tmp_path)
    assert (ws.root / "tables/table-01/table-01.csv").read_text("utf-8").startswith("Sample,")
    assert (ws.root / "figures/figure-01/figure-01.png").read_bytes().startswith(b"\x89PNG")
    tex = (ws.root / "equations/equation-01.tex").read_text("utf-8")
    assert r"E_k = h\nu - E_b - \phi" in tex and "eq:ke" in tex
    assert "(unnumbered)" in (ws.root / "equations/equation-02.tex").read_text("utf-8")


def test_the_plot_specification_behind_a_panel_is_written_beside_the_figure(tmp_path):
    ws, _ = _compile(tmp_path)
    import json
    spec = json.loads((ws.root / "figures/figure-01/pl_1.plotspec.json").read_text("utf-8"))
    assert spec["ref"] == "P1" and spec["chartType"] == "line"


def test_the_readme_lists_every_file_it_wrote(tmp_path):
    ws, summary = _compile(tmp_path)
    readme = (ws.root / "DEPOSIT.md").read_text("utf-8")
    assert "Sub-monolayer titania on SBA-15" in readme
    assert "Mark Isaacs, Chris Parlett" in readme
    for rel in summary["written"]:
        if rel != "DEPOSIT.md":
            assert rel in readme, f"{rel} is missing from DEPOSIT.md"


def test_the_readme_carries_the_statement_and_the_checksums(tmp_path):
    ws, _ = _compile(tmp_path)
    readme = (ws.root / "DEPOSIT.md").read_text("utf-8")
    assert "Zenodo" in readme and "10.5281/zenodo.0000000" in readme
    assert "a" * 64 in readme
    assert "data/figure-01/Ti2p.vms" in readme and "Ti 2p regions" in readme


def test_a_document_with_no_repository_says_nothing_about_availability(tmp_path):
    state = _state()
    state["repo"] = ""
    state["datasetDoi"] = ""
    ws = Workspace(tmp_path / "quiet")
    compile_deposit(ws, state, _rendered())
    assert "Data availability" not in (ws.root / "DEPOSIT.md").read_text("utf-8")


def test_the_summary_counts_what_it_compiled(tmp_path):
    ws, summary = _compile(tmp_path)
    assert summary["counts"] == {"figures": 1, "tables": 1, "plots": 1,
                                 "equations": 2, "attachments": 1}
    assert summary["bytes"] == sum((ws.root / p).stat().st_size for p in summary["written"])


def test_a_reference_the_document_does_not_know_is_skipped(tmp_path):
    ws = Workspace(tmp_path / "unknown")
    summary = compile_deposit(ws, _state(), {"tables": [{"ref": "T9", "csv": "a\n1\n"}]})
    assert summary["counts"]["tables"] == 0
    assert not (ws.root / "tables/table-01/table-01.csv").exists()


def test_a_path_escape_in_a_reference_is_refused(tmp_path):
    ws = Workspace(tmp_path / "escape")
    with pytest.raises(PathEscape):
        compile_deposit(ws, _state(), {"plots": [{"ref": "../../../evil", "csv": "x\n1\n"}]})
    assert not (tmp_path / "evil.csv").exists()
