#!/usr/bin/env python3
"""Figure placement (inline / top / bottom of page) and column span."""
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
sub(r""".figcap{font-family:var(--serif);font-size:13px;line-height:1.5;color:var(--ink);margin-top:9px}""",
    r""".figcap{font-family:var(--serif);font-size:13px;line-height:1.5;color:var(--ink);margin-top:9px}
/* A single-column figure is drawn at its real relative width so the caption
   length against the artwork is honest, not just a label saying "single". */
figure.fig-single{max-width:58%}
figure.fig-top{border-bottom:1px solid var(--ink);padding-bottom:8px}
figure.fig-bottom{border-top:1px solid var(--ink);padding-top:8px}
.figplace{font-family:var(--sans);font-size:10px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--faint);margin-bottom:4px}""")

# --------------------------------------------------- the fields and defaults
sub(r"""function composedCaption(f){""",
    r"""/* Where a figure sits on the page, and how wide it is. RSC and ACS both ask
   for figures collected at the top or bottom of a column, ruled off from the
   text; both also distinguish a single-column figure from a double. */
const FIG_PLACEMENTS = [
  {k:"inline", l:"In line, where it appears"},
  {k:"top",    l:"Top of page, ruled below"},
  {k:"bottom", l:"Bottom of page, ruled above"}
];
const FIG_SPANS = [{k:"single", l:"Single column"}, {k:"double", l:"Double column (full width)"}];
function figPlacement(f){ return FIG_PLACEMENTS.some(x=>x.k===(f&&f.placement)) ? f.placement : "inline"; }
function figSpan(f){ return (f&&f.span)==="single" ? "single" : "double"; }
function composedCaption(f){""")

sub(r"""  return `<figure style="margin:0 0 14px"><div class="figframe"><div class="figgrid" style="${grid}">${cells}</div></div>
    <figcaption class="figcap">${composedCaption(f)}</figcaption></figure>`;""",
    r"""  const pl=figPlacement(f), sp=figSpan(f);
  const note = (!o.print && pl!=="inline")
    ? `<div class="figplace">${esc(FIG_PLACEMENTS.find(x=>x.k===pl).l)}</div>` : "";
  return `<figure class="fig-${sp} fig-${pl}" style="margin:0 0 14px"><div class="figframe"><div class="figgrid" style="${grid}">${cells}</div></div>
    ${note}<figcaption class="figcap">${composedCaption(f)}</figcaption></figure>`;""")

# ------------------------------------------------------- composer controls
sub(r"""          <div class="fld"><label>Caption lead-in</label><input class="inp" id="figLead" value="${esc(f.leadIn)}"></div>""",
    r"""          <div class="fld"><label>Caption lead-in</label><input class="inp" id="figLead" value="${esc(f.leadIn)}"></div>
          <div class="row">
            <div class="fld"><label>Placement</label>
              <select class="inp" id="figPlace">${FIG_PLACEMENTS.map(x=>`<option value="${x.k}"${x.k===figPlacement(f)?" selected":""}>${esc(x.l)}</option>`).join("")}</select></div>
            <div class="fld"><label>Width</label>
              <select class="inp" id="figSpan">${FIG_SPANS.map(x=>`<option value="${x.k}"${x.k===figSpan(f)?" selected":""}>${esc(x.l)}</option>`).join("")}</select></div>
          </div>
          ${(()=>{ const t=templateById(S.templateId); return t&&t.figureWidths
            ? `<div class="note">${esc(t.label)} asks for ${esc(t.figureWidths.single)} single column, ${esc(t.figureWidths.double)} double${t.figureWidths.maxHeight?`, at most ${esc(t.figureWidths.maxHeight)} tall`:""}.</div>` : ""; })()}""")

sub(r"""  const fl=$("#figLead"); if(fl) fl.oninput=()=>{ curFig().leadIn=fl.value; save(); refreshFigCaps(); };""",
    r"""  const fl=$("#figLead"); if(fl) fl.oninput=()=>{ curFig().leadIn=fl.value; save(); refreshFigCaps(); };
  const fp=$("#figPlace"); if(fp) fp.onchange=()=>{ curFig().placement=fp.value; commit("Figure placement: "+FIG_PLACEMENTS.find(x=>x.k===fp.value).l); };
  const fsp=$("#figSpan"); if(fsp) fsp.onchange=()=>{ curFig().span=fsp.value; commit("Figure width: "+FIG_SPANS.find(x=>x.k===fsp.value).l); };""")

# ---------------------------------------------------------------- migrate
sub(r"""  if(!Array.isArray(S.folders)) S.folders=["Unfiled"];""",
    r"""  (S.figures||[]).forEach(f=>{ if(!f.placement) f.placement="inline"; if(!f.span) f.span="double"; });
  if(!Array.isArray(S.folders)) S.folders=["Unfiled"];""")

# ------------------------------------------------------------------ DOCX
sub(r"""function wImg(rid,cx,cy,id){""",
    r"""/* A top- or bottom-of-page figure goes in a single borderless cell anchored to
   the page, so the artwork and its caption travel together. That is how Word
   floats a block; a bare paragraph frame would leave the caption behind. */
function wFloatBlock(innerXml, yAlign){
  return `<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>`+
    `<w:tblpPr w:leftFromText="180" w:rightFromText="180" w:vertAnchor="page" w:horzAnchor="margin" w:tblpXSpec="center" w:tblpYSpec="${yAlign}"/>`+
    `<w:tblBorders><w:${yAlign==="top"?"bottom":"top"} w:val="single" w:sz="6" w:color="000000"/></w:tblBorders>`+
    `</w:tblPr><w:tr><w:tc><w:tcPr><w:tcW w:w="5000" w:type="pct"/></w:tcPr>${innerXml}</w:tc></w:tr></w:tbl>`+
    `<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>`;
}
function wImg(rid,cx,cy,id){""")

sub(r"""      else if(b.type==="fig"){
        const f=S.figures.find(x=>x.ref===b.figRef); if(!f) continue;
        const G=cellGeom(LAYOUTS[f.layout]);
        // one image per panel, stacked (Word has no easy grid without tables)
        for(let i=0;i<f.panels.length;i++){
          const pn=f.panels[i], src=pn.src?srcById(pn.src):null; if(!src) continue;
          if(src.dataURL){ media.push({name:`image${media.length+1}.png`,b64:src.dataURL.split(",")[1],cx:maxW,cy:Math.round(maxW*0.62)});
            parts.push(wImg("rId"+(100+media.length),maxW,Math.round(maxW*0.62),100+media.length)); continue; }
          const idx=await pushChart(renderChart(src,{w:560,h:360,print:true}),560,360);
          if(idx){ const m=media[idx-1]; parts.push(wImg("rId"+(100+idx),m.cx,m.cy,100+idx)); }
        }
        parts.push(wP(runsFromHTML(composedCaption(f)),"Caption"));
      }""",
    r"""      else if(b.type==="fig"){
        const f=S.figures.find(x=>x.ref===b.figRef); if(!f) continue;
        if(runIn){ parts.push(wP([{t:runIn,b:true,i:true}],"Normal")); runIn=null; }
        /* A single-column figure is set at 48% of the text width, which is what
           8.3 cm is against the 17.1 cm RSC and ACS both use for a full width. */
        const scale = figSpan(f)==="single" ? 0.48 : 1;
        const wide = Math.round(maxW*scale);
        const fig=[];
        // one image per panel, stacked (Word has no easy grid without tables)
        for(let i=0;i<f.panels.length;i++){
          const pn=f.panels[i], src=pn.src?srcById(pn.src):null; if(!src) continue;
          if(src.dataURL){ media.push({name:`image${media.length+1}.png`,b64:src.dataURL.split(",")[1],cx:wide,cy:Math.round(wide*0.62)});
            fig.push(wImg("rId"+(100+media.length),wide,Math.round(wide*0.62),100+media.length)); continue; }
          const idx=await pushChart(renderChart(src,{w:560,h:360,print:true}),560,360);
          if(idx){ const m=media[idx-1]; const cy=Math.round(m.cy*scale);
            fig.push(wImg("rId"+(100+idx),wide,cy,100+idx)); }
        }
        fig.push(wP(runsFromHTML(composedCaption(f)),"Caption"));
        const pl=figPlacement(f);
        if(pl==="inline") parts.push(fig.join(""));
        else parts.push(wFloatBlock(fig.join(""), pl));
      }""")

P.write_text(s, encoding="utf-8")
print("patched")
