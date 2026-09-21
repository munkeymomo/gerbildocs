#!/usr/bin/env python3
"""A general RSC template, with author addresses as footnotes.

Structure taken from the RSC's own `art-template-2.2.docx`: the byline marks
affiliations with superscript letters and the addresses are footnotes at the
foot of the first column, not a block under the names.
"""
import sys, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "app/static/index.html"
s = P.read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("expected %d occurrence(s), found %d:\n%s" % (count, n, old[:200]))
    s = s.replace(old, new, count)


# The bibliography style is the RSC's own for every journal it publishes; the
# label said Green Chemistry and shipped as though it were specific to it.
sub(r"""      {id:"st_rsc",label:"RSC — Green Chemistry",base:"rsc",source:"built-in",abstractLimit:250,""",
    r"""      {id:"st_rsc",label:"RSC journals (general)",base:"rsc",source:"built-in",abstractLimit:250,""")

# ---------------------------------------------------------- the template
sub(r"""  {
    id:"tpl_rsc_chemsci", family:"RSC", label:"RSC — Chemical Science Edge Article",""",
    r"""  {
    id:"tpl_rsc_general", family:"RSC", label:"RSC — general article (article template 2.2)",
    kind:"publication", style:"rsc", verified:true,
    source:"RSC article template 2.2 (art-template-2.2.docx), supplied by the author",
    abstractLimit:250, abstractMin:50, citation:"superscript numeric",
    affiliations:"footnote", affMark:"letter",
    sections:["Introduction","Results and discussion","Experimental","Conclusions",
              "Author contributions","Conflicts of interest","Data availability",
              "Acknowledgements","Notes and references"],
    statements:["Author contributions","Conflicts of interest","Data availability","Acknowledgements"],
    experimental:"end",
    headings:["A — section, e.g. Introduction, Results and discussion, Experimental",
              "B — sub-section, e.g. Synthetic procedures, Materials and methods",
              "C — in-line, e.g. General procedure for synthesis of compound X"],
    figureWidths:{single:"8.3 cm", double:"17.1 cm", maxHeight:"23.3 cm"},
    notes:["Author addresses are footnotes at the foot of the first column, marked a, b, c in the byline — not a block beneath the names. A corresponding author is marked with * before the letter.",
           "Three heading levels: A for sections, B subordinate to A, C in-line and subordinate to B.",
           "Conclusions, then author contributions, conflicts of interest, data availability, acknowledgements, then notes and references — in that order.",
           "Graphics and tables are placed at the top or bottom of the column after their first citation, with a horizontal bar separating them from the text. Text is never wrapped around a graphic.",
           "Equations stay in the flow of the text.",
           "Abstract is a single paragraph.",
           "Footnotes to the title and authors take †; footnotes to the main text take ‡, §, §§."]
  },
  {
    id:"tpl_rsc_chemsci", family:"RSC", label:"RSC — Chemical Science Edge Article",""")

# ------------------------------------ affiliations: block or footnote, and how marked
sub(r"""function authorLine(clean){
  const orgIdx={}; let n=0;
  S.authors.forEach(a=>{ if(a.org&&!(a.org in orgIdx)) orgIdx[a.org]=++n; });
  const names=S.authors.map(a=>{
    const sup=[a.org?orgIdx[a.org]:null].filter(Boolean).join(",");
    return esc(a.name)+(sup?`<sup>${sup}</sup>`:(clean?"":`<sup class="unres">?</sup>`))+(a.corresponding?"<sup>*</sup>":"")+(a.equal?"<sup>†</sup>":"");
  }).join(", ");
  const affs=Object.entries(orgIdx).map(([id,i])=>{ const o=S.orgs.find(x=>x.id===id)||{};
    return `<sup>${i}</sup> ${esc([o.dept,o.name,o.city,o.country].filter(Boolean).join(", "))}`; }).join("<br>");
  return {names,affs};
}""",
    r"""/* How the byline marks an affiliation, and where the address then goes, is the
   journal's business, so it comes from the template. RSC marks with letters and
   files the addresses as footnotes; most others number them under the names. */
function affStyle(){
  const t=templateById(S.templateId)||{};
  return {mark: t.affMark==="letter" ? "letter" : "number",
          place: t.affiliations==="footnote" ? "footnote" : "block"};
}
const AFF_LETTERS="abcdefghijklmnopqrstuvwxyz";
function authorLine(clean){
  const A=affStyle(), orgIdx={}; let n=0;
  S.authors.forEach(a=>{ if(a.org&&!(a.org in orgIdx)) orgIdx[a.org]=++n; });
  const markOf=i=>A.mark==="letter" ? (AFF_LETTERS[i-1]||String(i)) : String(i);
  /* RSC puts the asterisk before the affiliation letter — "Name,*a" — where a
     numbered byline carries it after. Follow whichever is in use. */
  const names=S.authors.map(a=>{
    const m=a.org?markOf(orgIdx[a.org]):null;
    const star=a.corresponding?"*":"", dag=a.equal?"†":"";
    if(!m) return esc(a.name)+(clean?(star?`<sup>${star}</sup>`:""):`<sup class="unres">?</sup>`)+(dag?`<sup>${dag}</sup>`:"");
    return esc(a.name)+(A.mark==="letter"
      ? `<sup>${star}${m}${dag}</sup>`
      : `<sup>${m}</sup>${star?"<sup>*</sup>":""}${dag?`<sup>${dag}</sup>`:""}`);
  }).join(", ");
  const affs=Object.entries(orgIdx).map(([id,i])=>{ const o=S.orgs.find(x=>x.id===id)||{};
    return `<sup>${markOf(i)}</sup> ${esc([o.dept,o.name,o.city,o.country].filter(Boolean).join(", "))}`; }).join("<br>");
  return {names,affs,place:A.place};
}""")

# ---------------------------------------------------------- the preview
sub(r"""  return `<h1>${fmtInline(esc(S.title))}</h1>
    <div class="authorline">${al.names}</div>
    <div class="afflist">${al.affs||'<span class="unres">no affiliations assigned</span>'}${S.authors.some(a=>a.corresponding)?"<br><sup>*</sup> corresponding author":""}</div>
    ${sub==="manuscript"&&S.abstract?`<div class="abstract" style="border-left:3px solid var(--line-strong);padding-left:12px;margin:0 0 16px;font-size:.94em">${fmtInline(esc(S.abstract))}</div>`:""}""",
    r"""  const affBlock=`<div class="afflist">${al.affs||'<span class="unres">no affiliations assigned</span>'}${S.authors.some(a=>a.corresponding)?"<br><sup>*</sup> corresponding author":""}</div>`;
  const affNote=`<div class="affnotes">${al.affs||'<span class="unres">no affiliations assigned</span>'}${S.authors.some(a=>a.corresponding)?"<br><sup>*</sup> corresponding author.":""}</div>`;
  return `<h1>${fmtInline(esc(S.title))}</h1>
    <div class="authorline">${al.names}</div>
    ${al.place==="footnote"?"":affBlock}
    ${sub==="manuscript"&&S.abstract?`<div class="abstract" style="border-left:3px solid var(--line-strong);padding-left:12px;margin:0 0 16px;font-size:.94em">${fmtInline(esc(S.abstract))}</div>`:""}
    ${al.place==="footnote"?affNote:""}""")

sub(r""".ms .afflist{font-size:11.5px;color:var(--muted);font-family:var(--sans);margin-bottom:16px;line-height:1.45}""",
    r""".ms .afflist{font-size:11.5px;color:var(--muted);font-family:var(--sans);margin-bottom:16px;line-height:1.45}
/* RSC files the addresses as footnotes at the foot of the first column. The
   preview has no columns, so they sit below the abstract, ruled off. */
.ms .affnotes{font-size:10.5px;color:var(--muted);font-family:var(--sans);line-height:1.45;
  border-top:1px solid var(--line-strong);padding-top:7px;margin:0 0 18px;max-width:34em}""")

# ---------------------------------------------------- HTML and Word exports
sub(r"""    bodyHTML=`<article class="ms" style="max-width:none"><h1>${esc(S.title)}</h1>
      <div class="authorline">${al.names}</div><div class="afflist">${al.affs}</div>""",
    r"""    bodyHTML=`<article class="ms" style="max-width:none"><h1>${fmtInline(esc(S.title))}</h1>
      <div class="authorline">${al.names}</div>${al.place==="footnote"?"":`<div class="afflist">${al.affs}</div>`}""")

sub(r"""  if(al.affs) parts.push(wP(runsFromHTML(al.affs.replace(/<br>/g,"\n").replace(/\n/g,"<br>")),"Affil"));
  if(sub==="manuscript"&&S.abstract){""",
    r"""  const affRuns = al.affs ? runsFromHTML(al.affs.replace(/<br>/g,"\n").replace(/\n/g,"<br>")) : null;
  /* Footnote addresses follow the abstract, ruled off, because a real Word
     footnote part is not written here yet — HANDOFF section 6. */
  if(affRuns && al.place!=="footnote") parts.push(wP(affRuns,"Affil"));
  if(sub==="manuscript"&&S.abstract){""")

sub(r"""  if(sub==="manuscript"&&(S.keywords||[]).length) parts.push(wP([{t:"Keywords: ",b:true},{t:S.keywords.join(", ")}],"Abstract"));""",
    r"""  if(sub==="manuscript"&&(S.keywords||[]).length) parts.push(wP([{t:"Keywords: ",b:true},{t:S.keywords.join(", ")}],"Abstract"));
  if(affRuns && al.place==="footnote") parts.push(wP(affRuns,"Affil",'<w:pBdr><w:top w:val="single" w:sz="4" w:color="000000"/></w:pBdr>'));""")

# The heading guidance a template gives is worth showing next to its notes.
sub(r"""          ${cur.limits?`<div class="note"><strong>Limits.</strong> ${Object.entries(cur.limits).map(([k,v])=>`${esc(k)}: ${esc(v)}`).join("; ")}</div>`:""}""",
    r"""          ${cur.headings?`<div class="note"><strong>Heading levels.</strong><ul style="margin:5px 0 0;padding-left:16px">${cur.headings.map(h=>`<li>${esc(h)}</li>`).join("")}</ul></div>`:""}
          ${cur.affiliations==="footnote"?`<div class="note"><strong>Addresses are footnotes</strong>, marked ${esc(cur.affMark==="letter"?"a, b, c":"1, 2, 3")} in the byline, not a block under the names. The preview and the exports follow this while this template is in use.</div>`:""}
          ${cur.limits?`<div class="note"><strong>Limits.</strong> ${Object.entries(cur.limits).map(([k,v])=>`${esc(k)}: ${esc(v)}`).join("; ")}</div>`:""}""")

P.write_text(s, encoding="utf-8")
print("patched")
