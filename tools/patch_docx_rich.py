#!/usr/bin/env python3
"""Carry the new inline formatting and lists into the Word export."""
import sys, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "app/static/index.html"
s = P.read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("expected %d occurrence(s), found %d:\n%s" % (count, n, old[:200]))
    s = s.replace(old, new, count)


# --- runs: underline and subscript join italic, bold and superscript ---------
sub(r"""  // tiny subset: <i> <b> <sup> and text
  const out=[]; let i=0, it=false, bo=false, su=false, buf="";
  const flush=()=>{ if(!buf) return;
    out.push({t:buf.replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&nbsp;/g," "),i:it,b:bo,s:su}); buf=""; };""",
    r"""  // tiny subset: <i> <b> <u> <sup> <sub> and text
  const out=[]; let i=0, it=false, bo=false, su=false, sb=false, un=false, buf="";
  const flush=()=>{ if(!buf) return;
    out.push({t:buf.replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&nbsp;/g," "),i:it,b:bo,s:su,sb:sb,u:un}); buf=""; };""")

sub(r"""    else if(t==="<sup>"){flush();su=true;}
    else if(t==="</sup>"){flush();su=false;}""",
    r"""    else if(t==="<sup>"){flush();su=true;}
    else if(t==="</sup>"){flush();su=false;}
    else if(t==="<sub>"){flush();sb=true;}
    else if(t==="</sub>"){flush();sb=false;}
    else if(t==="<u>"){flush();un=true;}
    else if(t==="</u>"){flush();un=false;}""")

sub(r"""    `<w:r><w:rPr>${r.i?"<w:i/>":""}${r.b?"<w:b/>":""}${r.s?'<w:vertAlign w:val="superscript"/>':""}</w:rPr><w:t xml:space="preserve">${xesc(r.t)}</w:t></w:r>`).join("");""",
    r"""    `<w:r><w:rPr>${r.i?"<w:i/>":""}${r.b?"<w:b/>":""}${r.u?'<w:u w:val="single"/>':""}${r.s?'<w:vertAlign w:val="superscript"/>':""}${r.sb?'<w:vertAlign w:val="subscript"/>':""}</w:rPr><w:t xml:space="preserve">${xesc(r.t)}</w:t></w:r>`).join("");""")

# --- paragraphs become paragraphs and list items ----------------------------
sub(r"""      if(b.type==="p"||b.type==="gen"){ parts.push(wP(runsFromHTML(renderInline(b.text||"").replace(/<span class="inlinemath">.*?<\/span>/g,"[math]")),"Normal","<w:jc w:val=\"both\"/>")); }""",
    r"""      if(b.type==="p"||b.type==="gen"){
        for(const part of bodyParts(b.text||"")){
          const line=t=>runsFromHTML(renderInline(t).replace(/<span class="inlinemath">.*?<\/span>/g,"[math]"));
          if(part.kind==="p"){ parts.push(wP(line(part.text),"Normal",'<w:jc w:val="both"/>')); continue; }
          /* Real Word lists, so the numbering is Word's and renumbers on edit. */
          const numId = part.kind==="ul" ? 1 : 2;
          part.items.forEach(t=>parts.push(wP(line(t),"ListParagraph",
            `<w:numPr><w:ilvl w:val="0"/><w:numId w:val="${numId}"/></w:numPr>`)));
        }
      }""")

# --- the numbering part -----------------------------------------------------
sub(r"""   ["Biblio","Bibliography",'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="17"/>','<w:spacing w:after="60"/><w:ind w:left="360" w:hanging="360"/>']]""",
    r"""   ["Biblio","Bibliography",'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="17"/>','<w:spacing w:after="60"/><w:ind w:left="360" w:hanging="360"/>'],
   ["ListParagraph","List Paragraph",'','<w:spacing w:after="60"/><w:ind w:left="720"/><w:contextualSpacing/>']]""")

sub(r"""  const rels=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>""",
    r"""  /* Two abstract numberings — a bullet and a decimal — and one concrete list
     each. Word renumbers an ordered list itself; what the author typed as "1."
     is only a marker in the source text. */
  const numbering=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="&#8226;"/><w:lvlJc w:val="left"/>
<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr></w:lvl></w:abstractNum>
<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>
<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>
</w:numbering>`;
  const rels=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rIdN" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>""")

sub(r"""<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>`;""",
    r"""<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>`;""")

sub(r"""    {name:"word/styles.xml",data:enc.encode(styles)},""",
    r"""    {name:"word/styles.xml",data:enc.encode(styles)},
    {name:"word/numbering.xml",data:enc.encode(numbering)},""")

P.write_text(s, encoding="utf-8")
print("patched")
