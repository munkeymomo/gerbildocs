#!/usr/bin/env python3
"""Real Word headers, footers and page numbers from the active template."""
import sys, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "app/static/index.html"
s = P.read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("expected %d occurrence(s), found %d:\n%s" % (count, n, old[:220]))
    s = s.replace(old, new, count)


sub(r"""function svgToPngB64(svgStr,w,h){""",
    r"""/* A logo's own proportions, so it is scaled to a height rather than squashed
   into a guess. Resolves to null if the image will not load. */
function imgAspect(dataURL){
  return new Promise(res=>{ const i=new Image();
    i.onload=()=>res(i.naturalWidth&&i.naturalHeight ? i.naturalWidth/i.naturalHeight : null);
    i.onerror=()=>res(null); i.src=dataURL; });
}
/* One header or footer part. Three slots on tab stops, which is how Word has
   always set them, plus a real PAGE field where the template asks for one. */
function wHeaderFooterXml(band, P, where, logoRid, logoCx, logoCy){
  const slots={left:hfText(band.left,null),centre:hfText(band.centre,null),right:hfText(band.right,null)};
  const pageAt = P.pageNumbers ? (P.numberIn||"footer-centre").split("-") : null;
  const wantPage = pageAt && pageAt[0]===where ? pageAt[1] : null;
  const run=t=>t?`<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="17"/><w:color w:val="444444"/></w:rPr><w:t xml:space="preserve">${xesc(t)}</w:t></w:r>`:"";
  const pageFld=`<w:fldSimple w:instr=" PAGE "><w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="17"/><w:color w:val="444444"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple>`;
  const slot=k=>run(slots[k])+(wantPage===k?(slots[k]?run(" "):"")+pageFld:"");
  const logo = logoRid ? `<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">`+
    `<wp:extent cx="${logoCx}" cy="${logoCy}"/><wp:docPr id="900" name="Logo"/>`+
    `<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">`+
    `<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="900" name="Logo"/><pic:cNvPicPr/></pic:nvPicPr>`+
    `<pic:blipFill><a:blip r:embed="${logoRid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>`+
    `<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${logoCx}" cy="${logoCy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>`+
    `</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>` : "";
  const onRight = logoRid && band.logoSide==="right";
  const body=`<w:p><w:pPr><w:tabs><w:tab w:val="center" w:pos="4536"/><w:tab w:val="right" w:pos="9072"/></w:tabs>`+
    `<w:pBdr><w:${where==="header"?"bottom":"top"} w:val="single" w:sz="4" w:color="999999"/></w:pBdr>`+
    `<w:spacing w:after="0"/></w:pPr>`+
    (onRight?"":logo)+slot("left")+`<w:r><w:tab/></w:r>`+slot("centre")+`<w:r><w:tab/></w:r>`+slot("right")+(onRight?logo:"")+`</w:p>`;
  const tag = where==="header" ? "w:hdr" : "w:ftr";
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<${tag} xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">${body}</${tag}>`;
}
function svgToPngB64(svgStr,w,h){""")

# ---------------------------------------------------- build the two parts
sub(r"""  const doc=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
""",
    r"""  /* Header and footer come from the template in use; a document with no
     template gets neither, and the section properties say nothing about them. */
  const PG=pageSetup(templateById(S.templateId));
  const hf=[]; // {part, xml, rels, media:[{name,b64}]}
  const LOGO_H=324000; // 9 mm, the usual height for a letterhead mark
  for(const where of ["header","footer"]){
    const band=PG[where];
    const used = band.left||band.centre||band.right||band.logo ||
      (PG.pageNumbers && (PG.numberIn||"footer-centre").split("-")[0]===where);
    if(!used) continue;
    let rid=null, cx=0, cy=LOGO_H, logoMedia=null;
    if(band.logo && /^data:image\//.test(band.logo)){
      const a=await imgAspect(band.logo);
      if(a){ rid="rIdLogo"; cx=Math.round(LOGO_H*a);
        logoMedia={name:`logo-${where}.png`, b64:band.logo.split(",")[1]}; }
    }
    hf.push({where, xml:wHeaderFooterXml(band,PG,where,rid,cx,cy), logo:logoMedia});
  }
  const hfPart = w => `${w}1.xml`;
  const hfRid = w => w==="header" ? "rIdHdr" : "rIdFtr";
  const sectExtra = hf.map(h=>`<w:${h.where}Reference w:type="default" r:id="${hfRid(h.where)}"/>`).join("");

  const doc=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main\"""")

sub(r"""<w:body>${parts.join("")}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1021" w:bottom="1134" w:left="1021"/></w:sectPr></w:body></w:document>`;""",
    r"""<w:body>${parts.join("")}<w:sectPr>${sectExtra}<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1021" w:bottom="1134" w:left="1021" w:header="567" w:footer="567"/></w:sectPr></w:body></w:document>`;""")

sub(r"""<Relationship Id="rIdN" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>""",
    r"""<Relationship Id="rIdN" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
${hf.map(h=>`<Relationship Id="${hfRid(h.where)}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/${h.where}" Target="${hfPart(h.where)}"/>`).join("")}""")

sub(r"""<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>`;""",
    r"""<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
${hf.map(h=>`<Override PartName="/word/${hfPart(h.where)}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.${h.where}+xml"/>`).join("")}</Types>`;""")

sub(r"""    {name:"word/numbering.xml",data:enc.encode(numbering)},""",
    r"""    {name:"word/numbering.xml",data:enc.encode(numbering)},""")

sub(r"""  ].concat(media.map(m=>({name:"word/media/"+m.name,data:b64ToBytes(m.b64)})));""",
    r"""  ].concat(media.map(m=>({name:"word/media/"+m.name,data:b64ToBytes(m.b64)})))
   .concat(hf.flatMap(h=>{
     const out=[{name:"word/"+hfPart(h.where),data:enc.encode(h.xml)}];
     if(h.logo){
       out.push({name:"word/media/"+h.logo.name,data:b64ToBytes(h.logo.b64)});
       out.push({name:`word/_rels/${hfPart(h.where)}.rels`,data:enc.encode(
         `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/${h.logo.name}"/></Relationships>`)});
     }
     return out;
   }));""")

P.write_text(s, encoding="utf-8")
print("patched")
