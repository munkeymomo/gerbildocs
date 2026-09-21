#!/usr/bin/env python3
"""The Templates view gets a "My templates" family and an editor for it."""
import sys, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "app/static/index.html"
s = P.read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("expected %d occurrence(s), found %d:\n%s" % (count, n, old[:220]))
    s = s.replace(old, new, count)


# ------------------------------------------------------------- the editor
sub(r"""function vTemplates(){""",
    r"""const AFF_PLACES=[{k:"block",l:"Block under the names"},{k:"footnote",l:"Footnotes at the foot of the column"}];
const AFF_MARKS=[{k:"number",l:"1, 2, 3"},{k:"letter",l:"a, b, c"}];
const NUM_WHERE=[{k:"footer-centre",l:"Footer, centre"},{k:"footer-right",l:"Footer, right"},
  {k:"footer-left",l:"Footer, left"},{k:"header-right",l:"Header, right"}];
function blankTemplate(){
  return {id:uid("tpl"), family:"My templates", label:"New template", kind:S.kind,
    style:(styleOf().base||"rsc"), abstractLimit:250, abstractMin:0, citation:"numeric",
    affiliations:"block", affMark:"number", sections:["Introduction","Results and discussion","Conclusions"],
    statements:[], notes:[], mine:true, page:pageSetup(null)};
}
/* Deriving from a built-in is the usual way in: take the RSC or ACS shape and
   put your own header on it. The copy is yours from then on. */
function deriveTemplate(id){
  const src=templateById(id); if(!src) return blankTemplate();
  const t=JSON.parse(JSON.stringify(src));
  t.id=uid("tpl"); t.family="My templates"; t.label=src.label+" (mine)"; t.mine=true;
  t.verified=false; t.source=""; t.page=pageSetup(src);
  return t;
}
function bandFields(where, b){
  const w=where; // "header" | "footer"
  return `<div class="stack">
    <div class="hfgrid">
      <div class="fld"><label>Left</label><input class="inp" data-hf="${w}|left" value="${esc(b.left||"")}"></div>
      <div class="fld"><label>Centre</label><input class="inp" data-hf="${w}|centre" value="${esc(b.centre||"")}"></div>
      <div class="fld"><label>Right</label><input class="inp" data-hf="${w}|right" value="${esc(b.right||"")}"></div>
    </div>
    <div class="row" style="align-items:flex-end">
      <div class="fld" style="flex:0 0 150px"><label>Logo</label>
        <label class="btn sm" style="cursor:pointer">${b.logo?"Replace image":"Add image"}<input type="file" accept="image/*" data-hflogo="${w}" hidden></label></div>
      ${b.logo?`<div class="fld" style="flex:0 0 120px"><label>Side</label>
        <select class="inp" data-hfside="${w}">${[["left","Left"],["right","Right"]].map(([k,l])=>`<option value="${k}"${(b.logoSide||"left")===k?" selected":""}>${l}</option>`).join("")}</select></div>
      <div class="fld" style="flex:0 0 auto"><label>&nbsp;</label><button class="btn sm danger" data-hfclear="${w}">Remove logo</button></div>
      <img src="${b.logo}" alt="" style="max-height:34px;width:auto;margin-left:auto">`:`<div class="meta" style="align-self:center">No logo.</div>`}
    </div></div>`;
}
function openTemplateEditor(tpl){
  modalState={tpl};
  drawTemplateEditor();
}
function drawTemplateEditor(){
  const t=modalState.tpl, P=pageSetup(t);
  const body=`<div class="stack">
    <div class="row">
      <div class="fld" style="flex:2 1 240px"><label>Name</label><input class="inp" id="tplName" value="${esc(t.label)}"></div>
      <div class="fld" style="flex:0 0 150px"><label>Document kind</label>
        <select class="inp" id="tplKind">${Object.keys(SUBDOCS).map(k=>`<option value="${k}"${k===t.kind?" selected":""}>${esc(fmtKind(k))}</option>`).join("")}</select></div>
    </div>
    <div class="row">
      <div class="fld" style="flex:0 0 140px"><label>Abstract limit</label><input class="inp" id="tplAbs" type="number" min="0" value="${+t.abstractLimit||0}"></div>
      <div class="fld" style="flex:0 0 140px"><label>Abstract minimum</label><input class="inp" id="tplAbsMin" type="number" min="0" value="${+t.abstractMin||0}"></div>
      <div class="fld"><label>Citation shape</label><input class="inp" id="tplCite" value="${esc(t.citation||"")}" placeholder="superscript numeric"></div>
    </div>
    <div class="row">
      <div class="fld"><label>Author addresses</label>
        <select class="inp" id="tplAff">${AFF_PLACES.map(x=>`<option value="${x.k}"${x.k===(t.affiliations||"block")?" selected":""}>${esc(x.l)}</option>`).join("")}</select></div>
      <div class="fld" style="flex:0 0 150px"><label>Marked with</label>
        <select class="inp" id="tplAffMark">${AFF_MARKS.map(x=>`<option value="${x.k}"${x.k===(t.affMark||"number")?" selected":""}>${esc(x.l)}</option>`).join("")}</select></div>
    </div>
    <div class="fld"><label>Sections, one per line — these are the A headings</label>
      <textarea class="inp" id="tplSecs" rows="6" spellcheck="false">${esc((t.sections||[]).join("\n"))}</textarea></div>
    <div class="fld"><label>Required statements, comma separated</label>
      <input class="inp" id="tplStat" value="${esc((t.statements||[]).join(", "))}"></div>
    <div class="row">
      <div class="fld"><label>Single-column figure width</label><input class="inp" id="tplFw1" value="${esc((t.figureWidths||{}).single||"")}" placeholder="8.3 cm"></div>
      <div class="fld"><label>Double-column figure width</label><input class="inp" id="tplFw2" value="${esc((t.figureWidths||{}).double||"")}" placeholder="17.1 cm"></div>
    </div>
    <div class="fld"><label>Notes to yourself, one per line</label>
      <textarea class="inp" id="tplNotes" rows="3">${esc((t.notes||[]).join("\n"))}</textarea></div>

    <div class="panel"><header><h3>Header</h3></header><div class="bd">${bandFields("header",P.header)}</div></div>
    <div class="panel"><header><h3>Footer</h3></header><div class="bd">${bandFields("footer",P.footer)}</div></div>
    <div class="row" style="align-items:flex-end">
      <label class="chip" style="flex:0 0 auto"><input type="checkbox" id="tplPgNum" ${P.pageNumbers?"checked":""}> Page numbers</label>
      <div class="fld" style="flex:0 0 190px"><label>Page number goes</label>
        <select class="inp" id="tplPgWhere" ${P.pageNumbers?"":"disabled"}>${NUM_WHERE.map(x=>`<option value="${x.k}"${x.k===P.numberIn?" selected":""}>${esc(x.l)}</option>`).join("")}</select></div>
    </div>
    <div class="note"><strong>Fields you can put in a header or footer.</strong> ${HF_TOKENS.map(([k,d])=>`<span class="mono">${esc(k)}</span> ${esc(d)}`).join(" · ")}
      <div style="margin-top:6px">The preview is not paginated, so <span class="mono">{page}</span> shows a dash there and a real page number in Word. The browser's print path cannot count pages either — for numbered PDF pages, export to Word and save as PDF from there.</div></div>
  </div>`;
  modal("Template", body,
    `<button class="btn" data-close>Cancel</button><button class="btn p" id="tplSave">Save template</button>`);
  const t2=modalState.tpl;
  const setBand=(w,k,v)=>{ t2.page=pageSetup(t2); t2.page[w][k]=v; };
  $$("[data-hf]").forEach(el=>el.oninput=()=>{ const [w,k]=el.dataset.hf.split("|"); setBand(w,k,el.value); });
  $$("[data-hfside]").forEach(el=>el.onchange=()=>{ setBand(el.dataset.hfside,"logoSide",el.value); });
  $$("[data-hfclear]").forEach(el=>el.onclick=()=>{ setBand(el.dataset.hfclear,"logo",null); drawTemplateEditor(); });
  $$("[data-hflogo]").forEach(el=>el.onchange=e=>{ const f=e.target.files[0]; if(!f) return;
    const rd=new FileReader(); rd.onload=()=>{ setBand(el.dataset.hflogo,"logo",rd.result); drawTemplateEditor(); };
    rd.readAsDataURL(f); });
  const pn=$("#tplPgNum"); pn.onchange=()=>{ $("#tplPgWhere").disabled=!pn.checked; };
  $("#tplSave").onclick=()=>{
    const lines=v=>v.split("\n").map(x=>x.trim()).filter(Boolean);
    Object.assign(t2,{
      label:$("#tplName").value.trim()||"Untitled template",
      kind:$("#tplKind").value,
      abstractLimit:+$("#tplAbs").value||0,
      abstractMin:+$("#tplAbsMin").value||0,
      citation:$("#tplCite").value.trim(),
      affiliations:$("#tplAff").value,
      affMark:$("#tplAffMark").value,
      sections:lines($("#tplSecs").value),
      statements:$("#tplStat").value.split(",").map(x=>x.trim()).filter(Boolean),
      notes:lines($("#tplNotes").value),
      family:"My templates", mine:true
    });
    const fw1=$("#tplFw1").value.trim(), fw2=$("#tplFw2").value.trim();
    if(fw1||fw2) t2.figureWidths={single:fw1,double:fw2}; else delete t2.figureWidths;
    t2.page=pageSetup(t2); t2.page.pageNumbers=$("#tplPgNum").checked; t2.page.numberIn=$("#tplPgWhere").value;
    if(!S.templates) S.templates=[];
    const i=S.templates.findIndex(x=>x.id===t2.id);
    if(i<0) S.templates.push(t2); else S.templates[i]=t2;
    closeModal(); commit(`Template “${t2.label}” saved`);
  };
}
function vTemplates(){""")

# ------------------------------------------------- the view: my templates
sub(r"""  const fam = {};
  TEMPLATES.forEach(t => (fam[t.family] = fam[t.family] || []).push(t));""",
    r"""  const fam = {};
  if (userTemplates().length) fam["My templates"] = userTemplates().slice();
  TEMPLATES.forEach(t => (fam[t.family] = fam[t.family] || []).push(t));""")

sub(r"""    <div class="acts">${cur?`<button class="btn" id="tplApply">Add missing sections</button><button class="btn" id="tplClear">Stop using</button>`:""}</div>""",
    r"""    <div class="acts">
      ${cur?`<button class="btn" id="tplApply">Add missing sections</button>${isUserTemplate(cur.id)?`<button class="btn" id="tplEdit">Edit this template</button>`:`<button class="btn" id="tplDerive">Make my own from this</button>`}<button class="btn" id="tplClear">Stop using</button>`:""}
      <button class="btn p" id="tplNew">+ New template</button>
    </div>""")

sub(r"""          <div class="acts"><button class="btn sm" data-tpluse="${t.id}">Use</button></div></li>`).join("")}</ul></div>`).join("")}""",
    r"""          <div class="acts"><button class="btn sm" data-tpluse="${t.id}">Use</button>${t.mine
            ? `<button class="btn sm" data-tpledit="${t.id}">Edit</button><button class="btn sm danger" data-tpldel="${t.id}">Delete</button>`
            : `<button class="btn sm" data-tplcopy="${t.id}">Copy</button>`}</div></li>`).join("")}</ul></div>`).join("")}""")

# The page furniture is worth seeing in the panel beside the notes.
sub(r"""          ${cur.source?`<div class="meta mono" style="word-break:break-all">${esc(cur.source)}</div>`:'<div class="meta">House template — no publisher page.</div>'}""",
    r"""          ${(()=>{ const P=pageSetup(cur); if(!hasFurniture(P)) return "";
            const line=(b,w)=>[b.logo?"logo":"",b.left,b.centre,b.right].filter(Boolean).join(" · ")||"empty";
            return `<div class="note"><strong>Page furniture.</strong> Header: ${esc(line(P.header))}. Footer: ${esc(line(P.footer))}.${P.pageNumbers?` Page numbers ${esc((NUM_WHERE.find(x=>x.k===P.numberIn)||{}).l||"")}.`:" No page numbers."}</div>`; })()}
          ${cur.source?`<div class="meta mono" style="word-break:break-all">${esc(cur.source)}</div>`:'<div class="meta">House template — no publisher page.</div>'}""")

P.write_text(s, encoding="utf-8")
print("patched")
