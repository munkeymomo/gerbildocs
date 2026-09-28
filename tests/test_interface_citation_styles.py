"""The interface is one file, so how its citation-style code is laid out is
part of the contract: the BibTeX engine is pasted into its own block at a
known place, and the CSL processor must not lean on the page's state."""
import re
from pathlib import Path

PAGE_PATH = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"
PAGE = PAGE_PATH.read_text(encoding="utf-8")


def script_blocks() -> list[str]:
    return re.findall(r"<script>(.*?)</script>", PAGE, flags=re.S)


def test_bibtex_engine_block_sits_before_the_style_profiles():
    blocks = script_blocks()
    at = next(i for i, b in enumerate(blocks) if "/* ---------- style profiles" in b)
    engine = blocks[at - 1]
    for name in ("bstParse", "bstRun", "bstLatexToHTML", "refToBibtex"):
        assert name in engine, name
    # Nothing of the page's own goes in the engine's block.
    assert "function styleOf" not in engine and "function citeStyleOf" not in engine


def test_csl_processor_is_its_own_block_and_reads_no_document_state():
    blocks = [b for b in script_blocks() if "CSL PROCESSOR" in b]
    assert len(blocks) == 1
    csl = blocks[0]
    assert "function cslParse" in csl and "function cslEngine" in csl
    # It formats what it is given; the document (S) is the integration's business.
    assert not re.search(r"\bS\.(refs|styleLib|style)\b", csl)
    # citeproc-js is not bundled: its licence (CPAL/AGPL) does not fit an MIT app.
    assert "CSL.Engine" not in PAGE and "Frank Bennett" not in PAGE


def test_citation_style_rules_are_one_block_in_the_stylesheet():
    head = "/* ---- citation styles: CSL and BibTeX ---- */"
    assert PAGE.count(head) == 1
    main_css = PAGE[PAGE.index("<style>\n"):]
    main_css = main_css[: main_css.index("</style>")]
    assert head in main_css
    # Everything from the heading to the next block's heading is a
    # citation-style rule, and nothing else is.
    tail = main_css[main_css.index(head) + len(head):]
    nxt = tail.find("/* ---- ")
    if nxt >= 0:
        tail = tail[:nxt]
    selectors = re.findall(r"([^{}]+)\{", tail)
    assert selectors and all(re.search(r"csl|cite|\.sc\b", s) for s in selectors), selectors


def test_a_dtd_is_refused_before_the_xml_is_parsed():
    csl = next(b for b in script_blocks() if "CSL PROCESSOR" in b)
    parse = csl[csl.index("function cslParse"):]
    assert parse.index("<!DOCTYPE") < parse.index("new DOMParser()")


def csl_block() -> str:
    return next(b for b in script_blocks() if "CSL PROCESSOR" in b)


def test_style_supplied_names_never_key_an_object_with_a_prototype():
    """A style names terms, forms, macros, variables and date parts. None of
    those may reach Object.prototype: form="__proto__" once wrote onto it,
    and every fetch() in the page broke."""
    csl = csl_block()
    for table in ("const a=Object.create(null)", "const macros=Object.create(null)",
                  "const T=Object.create(null)", "const over=Object.create(null)",
                  "this.ordinals=Object.create(null)"):
        assert table in csl, table
    assert "CSL_TERM_FORMS.includes(form)" in csl
    assert "T[form]={}" not in csl and "macros={}" not in csl
    # Variables are read as the item's own, never through its prototype.
    assert not re.search(r"\bit\[v\]|cx\.item\[v\]|\bitem\[name\]", csl)
    assert "function cslOwn" in csl


def test_macros_are_checked_before_a_style_runs():
    """Loops and exponential fan-out (m0 calls m1 twice, m1 calls m2 twice…)
    are refused when the style is read, before any engine exists."""
    csl = csl_block()
    compile_ = csl[csl.index("function cslCompile"):]
    compile_ = compile_[: compile_.index("\n}\n")]
    assert compile_.index("cslMacroCost(") < compile_.index("const style={")
    assert "call each other in a loop" in csl
    limit = int(re.search(r"const CSL_MAX_EXPANDED=(\d+);", csl).group(1))
    assert 10_000 <= limit <= 1_000_000


def test_every_engine_step_spends_from_a_budget():
    csl = csl_block()
    kids = csl[csl.index("CSLEngine.prototype.kids=function"):]
    kids = kids[: kids.index("\n};")]
    assert "cslSpend(this)" in kids
    for op in ('["run"', '["cite"', '["bibliography"', '["bibOrder"'):
        assert op in csl, op
    assert "this.guard(" in csl


def test_a_stored_style_is_held_to_todays_checks_before_anything_renders():
    mig = PAGE[PAGE.index("function citeMigrate()"):]
    mig = mig[: mig.index("\n}\n")]
    assert 'citeParse("csl",src)' in mig and "set aside" in mig
    migrate = PAGE[PAGE.index("function migrate(){"):]
    assert "citeMigrate();" in migrate[: migrate.index("\n}\n")]
    boot = PAGE[PAGE.index("async function boot(){"):]
    boot = boot[: boot.index("\n}\n")]
    assert boot.index("migrate();") < boot.index("render();")


def test_one_style_cannot_take_the_style_library_down():
    view = PAGE[PAGE.index("function vStyles(){"):]
    view = view[: view.index("\n}\n")]
    assert "citeSafe(()=>stylePreviewBib(e,sample)" in view
    assert "citeSafe(()=>citeRowHTML(e)" in view

