#!/usr/bin/env python3
"""Templates of your own: sections, heading rules, header, footer, page numbers.

A template made once is used by every document after it, so `templates` joins
the app-scoped library rather than living in a document. Pages, headers and
footers are a property of the template because that is what makes a house
report look the same every time.
"""
import sys, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "app/static/index.html"
s = P.read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("expected %d occurrence(s), found %d:\n%s" % (count, n, old[:220]))
    s = s.replace(old, new, count)


# ------------------------------------------------------------------- CSS
sub(r""".sheet .ms h1{font-size:24px}""",
    r""".sheet .ms h1{font-size:24px}
/* The header and footer a template carries, drawn on the preview sheet the way
   they will be set on the page. */
.pgband{display:flex;align-items:center;gap:12px;font-family:var(--sans);font-size:11px;color:var(--muted)}
.pgband > div{flex:1 1 0;min-width:0}
.pgband .c{text-align:center}.pgband .r{text-align:right}
.pgband img{max-height:34px;width:auto;flex:0 0 auto}
.sheet .pgband.head{border-bottom:1px solid var(--line-strong);padding-bottom:8px;margin-bottom:20px}
.sheet .pgband.foot{border-top:1px solid var(--line-strong);padding-top:8px;margin-top:26px}
.hfgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
@media(max-width:700px){.hfgrid{grid-template-columns:1fr}}""")

sub(r"""  .pr .bib{font-size:9pt}""",
    r"""  .pr .bib{font-size:9pt}
  /* Fixed elements repeat on every printed page in Chromium, which is what the
     desktop window is. The page number is not here: the browser print path
     cannot count pages — Word can, and does. */
  .pr-head{position:fixed;top:0;left:0;right:0;font-size:8.5pt;color:#444;border-bottom:.5pt solid #999;padding-bottom:3pt}
  .pr-foot{position:fixed;bottom:0;left:0;right:0;font-size:8.5pt;color:#444;border-top:.5pt solid #999;padding-top:3pt}
  .pr-head img,.pr-foot img{max-height:9mm;width:auto}""")

# --------------------------------------------------- model and defaults
sub(r"""function templateById(id){ return TEMPLATES.find(t=>t.id===id) || null; }""",
    r"""/* Built-ins first, then the user's own. One lookup, so everything that reads a
   template — the compliance check, the byline, the page furniture — gets the
   user's as readily as ours. */
function templateById(id){
  return TEMPLATES.find(t => t.id === id) || (S && S.templates || []).find(t => t.id === id) || null;
}
function userTemplates(){ return (S && S.templates) || []; }
function isUserTemplate(id){ return userTemplates().some(t => t.id === id); }
const BLANK_BAND = () => ({left:"", centre:"", right:"", logo:null, logoSide:"left"});
function pageSetup(tpl){
  const p = (tpl && tpl.page) || {};
  return {
    header: Object.assign(BLANK_BAND(), p.header),
    footer: Object.assign(BLANK_BAND(), p.footer),
    pageNumbers: !!p.pageNumbers,
    numberIn: p.numberIn || "footer-centre"
  };
}
function hasFurniture(P){
  const any = b => b.left || b.centre || b.right || b.logo;
  return any(P.header) || any(P.footer) || P.pageNumbers;
}
/* Fields the author should not have to retype. `{page}` stays a placeholder in
   the preview because the preview is not paginated; Word turns it into a
   field. */
const HF_TOKENS = [["{title}","the document title"],["{runningHead}","the running head"],
  ["{authors}","the author list"],["{firstAuthor}","the first author's surname"],
  ["{date}","today's date"],["{doc}","the sub-document name, e.g. Manuscript"],
  ["{page}","the page number"]];
function hfText(str, pageNo){
  const first = splitName((S.authors[0]||{}).name || "").last;
  return String(str||"")
    .replace(/\{title\}/g, S.title||"")
    .replace(/\{runningHead\}/g, S.runningHead||S.title||"")
    .replace(/\{authors\}/g, S.authors.map(a=>a.name).join(", "))
    .replace(/\{firstAuthor\}/g, first||"")
    .replace(/\{date\}/g, fmtDate(nowISO()))
    .replace(/\{doc\}/g, (SUBDOCS[S.kind].find(x=>x.k===sub)||{}).l || "")
    .replace(/\{page\}/g, pageNo==null ? "\u2014" : String(pageNo));
}
/* One band, three slots and an optional logo. `pageNo` is null where nothing
   can count pages. */
function bandHTML(band, where, P, pageNo){
  const slots = {left:hfText(band.left,pageNo), centre:hfText(band.centre,pageNo), right:hfText(band.right,pageNo)};
  if(P.pageNumbers){
    const [w,slot] = (P.numberIn||"footer-centre").split("-");
    if(w===where){ const n = pageNo==null ? "\u2014" : String(pageNo);
      slots[slot] = (slots[slot]?slots[slot]+" ":"") + n; }
  }
  if(!slots.left && !slots.centre && !slots.right && !band.logo) return "";
  const img = band.logo ? `<img src="${band.logo}" alt="">` : "";
  return `<div class="pgband ${where==="header"?"head":"foot"}">`
    + (band.logo && band.logoSide!=="right" ? img : "")
    + `<div class="l">${esc(slots.left)}</div><div class="c">${esc(slots.centre)}</div><div class="r">${esc(slots.right)}</div>`
    + (band.logo && band.logoSide==="right" ? img : "")
    + `</div>`;
}""")

# ------------------------------------------------------- preview overlay
sub(r"""    <div class="pvbody"><div class="sheet"><article class="ms">${body}</article></div></div>""",
    r"""    <div class="pvbody"><div class="sheet">${pvHead}<article class="ms">${body}</article>${pvFoot}</div></div>""")

sub(r"""  const Sp=styleOf(), body=previewDoc();
  sub=keep;""",
    r"""  const Sp=styleOf(), body=previewDoc();
  const PG=pageSetup(templateById(S.templateId));
  const pvHead=bandHTML(PG.header,"header",PG,1), pvFoot=bandHTML(PG.footer,"footer",PG,1);
  sub=keep;""")

# ------------------------------------------------------------ print path
sub(r"""  return `<div class="pr">
    <div style="font-size:8.5pt;color:#555;border-bottom:.5pt solid #999;padding-bottom:3pt;margin-bottom:10pt">${esc(S.runningHead||S.title)}</div>""",
    r"""  const PG=pageSetup(templateById(S.templateId));
  const head=bandHTML(PG.header,"header",PG,null), foot=bandHTML(PG.footer,"footer",PG,null);
  return `<div class="pr">
    ${head?`<div class="pr-head">${head}</div>`:""}${foot?`<div class="pr-foot">${foot}</div>`:""}
    <div style="font-size:8.5pt;color:#555;border-bottom:.5pt solid #999;padding-bottom:3pt;margin-bottom:10pt">${esc(S.runningHead||S.title)}</div>""")

# ---------------------------------------------------------------- migrate
sub(r"""  if(!Array.isArray(S.folders)) S.folders=["Unfiled"];""",
    r"""  if(!Array.isArray(S.templates)) S.templates=[];
  if(!Array.isArray(S.folders)) S.folders=["Unfiled"];""")

P.write_text(s, encoding="utf-8")
print("patched")
