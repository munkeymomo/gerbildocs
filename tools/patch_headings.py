#!/usr/bin/env python3
"""Heading levels (RSC A / B / C) and collapsible sections."""
import sys, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "app/static/index.html"
s = P.read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("expected %d occurrence(s), found %d:\n%s" % (count, n, old[:200]))
    s = s.replace(old, new, count)


# ------------------------------------------------------------------ CSS
sub(r""".ms h2{font-family:var(--serif);font-size:16px;margin:22px 0 7px}""",
    r""".ms h2{font-family:var(--serif);font-size:16px;margin:22px 0 7px}
.ms h3{font-family:var(--serif);font-size:14.5px;font-style:italic;font-weight:600;margin:16px 0 5px}
.ms .runin{font-weight:600;font-style:italic}""")

sub(r""".navi .ct{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--faint)}""",
    r""".navi .ct{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--faint)}

/* ---------- section levels and folding ---------- */
.secfold{background:none;border:0;cursor:pointer;color:var(--faint);font-size:11px;line-height:1;
  padding:3px 4px;border-radius:4px;flex-shrink:0;transition:transform .12s,color .12s}
.secfold:hover{color:var(--ink);background:var(--sunk)}
.secfold[aria-expanded="false"]{transform:rotate(-90deg)}
.panel[data-sec].folded > .bd{display:none}
.panel[data-sec].lv2{margin-left:20px;border-left:2px solid var(--brand-wash)}
.panel[data-sec].lv3{margin-left:40px;border-left:2px solid var(--line)}
.lvsel{width:auto;max-width:132px;padding:3px 6px;font-size:11.5px}
.secfold .n{display:inline-block;width:1em}""")

# ---------------------------------------------------- levels, as one place
sub(r"""function orderedSections(which){""",
    r"""/* RSC calls them A, B and C headings; ACS numbers them. One field, three
   renderings — the level is the document's, the lettering is the style's. */
const HEAD_LEVELS = [
  {k:1, l:"A — section", tag:"h2"},
  {k:2, l:"B — sub-section", tag:"h3"},
  {k:3, l:"C — in-line", tag:null}
];
function secLevel(sec){ const n=+(sec&&sec.level||1); return n>=1&&n<=3?n:1; }
/* A C heading runs into its first paragraph rather than standing on its own. */
function sectionHTML(sec, o){
  const t = fmtInline(esc(sec.title)), lv = secLevel(sec);
  const blocks = sec.blocks || [];
  const rendered = blocks.map(b => previewBlock(b, o));
  if (lv < 3) return `<${lv===2?"h3":"h2"}>${t}</${lv===2?"h3":"h2"}>` + rendered.join("");
  const head = `<span class="runin">${t}</span> `;
  const i = rendered.findIndex(h => h.startsWith("<p>"));
  if (i < 0) return `<p>${head}</p>` + rendered.join("");
  rendered[i] = rendered[i].replace(/^<p>/, "<p>" + head);
  return rendered.join("");
}
function orderedSections(which){""")

sub(r"""    ${orderedSections().map(sec=>`<h2>${esc(sec.title)}</h2>`+(sec.blocks||[]).map(b=>previewBlock(b,o)).join("")).join("")}""",
    r"""    ${orderedSections().map(sec=>sectionHTML(sec,o)).join("")}""")

sub(r"""      ${S.subdocs[sub].sections.map(sec=>`<h2>${fmtInline(esc(sec.title))}</h2>`+(sec.blocks||[]).map(b=>previewBlock(b,{print:true})).join("")).join("")}""",
    r"""      ${orderedSections().map(sec=>sectionHTML(sec,{print:true})).join("")}""")

# ------------------------------------------------------------ the editor
sub(r"""    <section class="panel" data-sec="${sec.id}" style="margin-bottom:10px${moved?";opacity:.85":""}">
      <header>
        <input class="inp" data-sectitle="${sec.id}" value="${esc(sec.title)}" aria-label="Section title" style="max-width:250px;font-weight:600;border-color:transparent;background:transparent"${moved?" disabled":""}>""",
    r"""    const lv=secLevel(sec), open=!ui.folded.has(sec.id);
    return `
    <section class="panel${lv>1?" lv"+lv:""}${open?"":" folded"}" data-sec="${sec.id}" style="margin-bottom:10px${moved?";opacity:.85":""}">
      <header>
        <button class="secfold" data-fold="${sec.id}" aria-expanded="${open}" aria-controls="secbd-${sec.id}"
          title="${open?"Collapse":"Expand"} this section" aria-label="${open?"Collapse":"Expand"} section ${esc(sec.title)}">\u25BC</button>
        <input class="inp" data-sectitle="${sec.id}" value="${esc(sec.title)}" aria-label="Section title" style="max-width:250px;font-weight:600;border-color:transparent;background:transparent"${moved?" disabled":""}>
        ${moved?"":`<select class="inp lvsel" data-seclevel="${sec.id}" aria-label="Heading level">${HEAD_LEVELS.map(h=>`<option value="${h.k}"${h.k===lv?" selected":""}>${esc(h.l)}</option>`).join("")}</select>`}""")

sub(r"""      </header>
      <div class="bd stack">
        ${(sec.blocks||[]).map(b=>moved?previewBlock(b):blockEditor(sec,b)).join("") || '<div class="empty">Empty section</div>'}
      </div>
    </section>`;}).join("");""",
    r"""      </header>
      <div class="bd stack" id="secbd-${sec.id}">
        ${(sec.blocks||[]).map(b=>moved?previewBlock(b):blockEditor(sec,b)).join("") || '<div class="empty">Empty section</div>'}
      </div>
    </section>`;}).join("");""")

sub(r"""    return `
    <section class="panel${lv>1?" lv"+lv:""}""",
    r"""    return `
    <section class="panel${lv>1?" lv"+lv:""}""")   # no-op guard: shape is as written

# the old `return \`` that preceded the <section> is now redundant
sub(r"""    const moved=isExp&&(sec.placement||"end")==="si"&&sub==="si";
    return `
    const lv=secLevel(sec), open=!ui.folded.has(sec.id);""",
    r"""    const moved=isExp&&(sec.placement||"end")==="si"&&sub==="si";
    const lv=secLevel(sec), open=!ui.folded.has(sec.id);""")

sub(r"""      <button class="btn" id="addSec">+ Section</button>""",
    r"""      <button class="btn" id="foldAll">${secs.every(x=>ui.folded.has(x.id))?"Expand all":"Collapse all"}</button>
      <button class="btn" id="addSec">+ Section</button>
      <button class="btn" id="addSub">+ Sub-section</button>""")

# --------------------------------------------------------------- wiring
sub(r"""  const addSec=$("#addSec"); if(addSec) addSec.onclick=addSection;""",
    r"""  const addSec=$("#addSec"); if(addSec) addSec.onclick=()=>addSection(1);
  const addSub=$("#addSub"); if(addSub) addSub.onclick=()=>addSection(2);
  on("[data-fold]","click",e=>{ const id=e.currentTarget.dataset.fold;
    if(ui.folded.has(id)) ui.folded.delete(id); else ui.folded.add(id);
    const sec=$(`.panel[data-sec="${id}"]`), btn=e.currentTarget, open=!ui.folded.has(id);
    if(sec) sec.classList.toggle("folded",!open);
    btn.setAttribute("aria-expanded",String(open));
    btn.title=(open?"Collapse":"Expand")+" this section";
    const fa=$("#foldAll"); if(fa) fa.textContent=(S.subdocs[sub].sections||[]).every(x=>ui.folded.has(x.id))?"Expand all":"Collapse all"; });
  const fa=$("#foldAll"); if(fa) fa.onclick=()=>{ const secs=S.subdocs[sub].sections||[];
    if(secs.every(x=>ui.folded.has(x.id))) ui.folded.clear(); else secs.forEach(x=>ui.folded.add(x.id)); render(); };
  on("[data-seclevel]","change",e=>{ const sec=S.subdocs[sub].sections.find(s=>s.id===e.target.dataset.seclevel);
    if(sec){ sec.level=+e.target.value; commit("Heading level changed"); } });""")

sub(r"""function addSection(){ const s={id:uid("s"),kind:"heading",title:"New section",blocks:[{id:uid("b"),type:"p",text:""}]};""",
    r"""function addSection(level){ const lv=level||1;
  const s={id:uid("s"),kind:"heading",level:lv,title:lv===1?"New section":lv===2?"New sub-section":"New in-line heading",blocks:[{id:uid("b"),type:"p",text:""}]};""")

# ------------------------------------------------------------- migrate
sub(r"""  Object.values(S.subdocs||{}).forEach(sd=>(sd.sections||[]).forEach(sec=>{
    if(sec.kind==="experimental"&&!sec.role){ sec.role="experimental"; sec.placement="end"; } }));""",
    r"""  Object.values(S.subdocs||{}).forEach(sd=>(sd.sections||[]).forEach(sec=>{
    if(sec.kind==="experimental"&&!sec.role){ sec.role="experimental"; sec.placement="end"; }
    if(!sec.level) sec.level=1; }));""")

# A template's section list is the A headings; sub-sections are the author's.
sub(r"""  const have = orderedSections("manuscript").map(x=>x.title.toLowerCase());""",
    r"""  const have = orderedSections("manuscript").filter(x=>secLevel(x)===1).map(x=>x.title.toLowerCase());""")

P.write_text(s, encoding="utf-8")
print("patched")
