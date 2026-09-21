#!/usr/bin/env python3
"""Inline formatting (bold, italic, underline, super/subscript) and lists.

The paragraph editor is a textarea and stays one: switching the writing surface
to contenteditable would take the @ popup, the undo snapshots, the inline maths
and the id tokens with it. So formatting is notation with a live preview beside
it, in the same spirit as the ^{} and _{} already used in axis labels.
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


# ---------------------------------------------------------------- 1. CSS
sub(r""".ms p{margin:0 0 11px}""",
    r""".ms p{margin:0 0 11px}
.ms ul,.ms ol{margin:0 0 11px;padding-left:24px}
.ms li{margin:0 0 4px}
.ms u{text-decoration:underline;text-underline-offset:2px}
.ms sub{font-size:.7em;vertical-align:sub;line-height:0}""")

sub(r""".blk .blkbar .hint{font-size:11px;color:var(--faint)}""",
    r""".blk .blkbar .hint{font-size:11px;color:var(--faint)}
/* Formatting bar. Same reveal-on-focus rule as the rest of the block chrome. */
.fmtbar{display:flex;gap:2px;align-items:center;flex-wrap:wrap;margin-bottom:4px;opacity:0;transition:opacity .15s}
.blk:hover .fmtbar,.blk:focus-within .fmtbar{opacity:1}
.fmtbar .fb{background:none;border:1px solid transparent;border-radius:5px;min-width:26px;height:24px;padding:0 6px;
  cursor:pointer;color:var(--muted);font-size:12.5px;line-height:1;display:inline-flex;align-items:center;justify-content:center}
.fmtbar .fb:hover{background:var(--sunk);color:var(--ink);border-color:var(--line)}
.fmtbar .sep{width:1px;height:16px;background:var(--line);margin:0 4px}
.fmtbar .fb b{font-weight:700}.fmtbar .fb i{font-style:italic}.fmtbar .fb u{text-decoration:underline}
.fmtbar .fb sup,.fmtbar .fb sub{font-size:.7em}""")

# ------------------------------------------------- 2. notation and renderers
sub(r"""function hasRich(text){ RICH_RE.lastIndex = 0; return RICH_RE.test(String(text ?? "")); }""",
    r"""function hasRich(text){ RICH_RE.lastIndex = 0; return RICH_RE.test(String(text ?? "")); }

/* ---------- inline formatting in body text ----------
   Body prose only honours the braced shifts. The `^2` shorthand is right in an
   axis label but would turn "file_name" into a subscript in a sentence, so the
   loose form is deliberately not accepted here. */
const RICH_BRACE_RE = /(\^|_)\{([^}]*)\}/g;
/* `str` is already HTML-escaped and carries no tags, so these patterns cannot
   reach inside an attribute. Bold before italic, or `**x**` opens an <em>. */
function fmtInline(str){
  let out = String(str);
  out = out.replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/__(?=\S)([\s\S]*?\S)__/g, "<u>$1</u>");
  out = out.replace(/(^|[^*\w])\*(?=\S)([^*\n]*?\S)\*(?!\*)/g, "$1<em>$2</em>");
  out = out.replace(RICH_BRACE_RE, (m, mark, body) =>
    mark === "^" ? "<sup>" + body + "</sup>" : "<sub>" + body + "</sub>");
  return out;
}
/* Line-led lists. A run of `- ` lines is a bullet list, `1. ` a numbered one;
   the typed numbers are ignored — the list renumbers itself. */
function renderBody(text, ctx){
  const lines = String(text ?? "").split("\n");
  const out = []; let para = [], kind = null, items = null;
  const flushPara = () => { if (para.length){ out.push("<p>" + renderInline(para.join("\n"), ctx) + "</p>"); para = []; } };
  const flushList = () => { if (kind){ out.push("<" + kind + ">" + items.map(t => "<li>" + renderInline(t, ctx) + "</li>").join("") + "</" + kind + ">"); kind = null; items = null; } };
  for (const ln of lines){
    const m = /^\s*(?:([-\u2022])|(\d+[.)]))\s+(.*)$/.exec(ln);
    if (m){
      const want = m[1] ? "ul" : "ol";
      flushPara(); if (kind && kind !== want) flushList();
      if (!kind){ kind = want; items = []; }
      items.push(m[3]); continue;
    }
    if (!ln.trim()){ flushPara(); flushList(); continue; }
    flushList(); para.push(ln);
  }
  flushPara(); flushList();
  return out.join("") || "<p></p>";
}
/* The same split, as data, for exporters that need paragraphs and list items
   rather than HTML. One reading of the text, two renderers. */
function bodyParts(text){
  const lines = String(text ?? "").split("\n");
  const out = []; let para = [], kind = null, items = null;
  const flushPara = () => { if (para.length){ out.push({kind:"p", text:para.join("\n")}); para = []; } };
  const flushList = () => { if (kind){ out.push({kind:kind, items:items}); kind = null; items = null; } };
  for (const ln of lines){
    const m = /^\s*(?:([-\u2022])|(\d+[.)]))\s+(.*)$/.exec(ln);
    if (m){
      const want = m[1] ? "ul" : "ol";
      flushPara(); if (kind && kind !== want) flushList();
      if (!kind){ kind = want; items = []; }
      items.push(m[3]); continue;
    }
    if (!ln.trim()){ flushPara(); flushList(); continue; }
    flushList(); para.push(ln);
  }
  flushPara(); flushList();
  return out;
}""")

sub(r"""  out=esc(out);
  out=out.replace(/\[@fig:""",
    r"""  out=fmtInline(esc(out));
  out=out.replace(/\[@fig:""")

sub(r"""  return `<p>${renderInline(b.text,{blockId:b.id,firstAbbr:o.firstAbbr,seen:o.seen})}</p>`;""",
    r"""  return renderBody(b.text,{blockId:b.id,firstAbbr:o.firstAbbr,seen:o.seen});""")

# Abstract and captions read the same notation.
sub(r"""margin:0 0 16px;font-size:.94em">${esc(S.abstract)}</div>`:""}""",
    r"""margin:0 0 16px;font-size:.94em">${fmtInline(esc(S.abstract))}</div>`:""}""")
sub(r"""  const parts=f.panels.map((p,i)=>p.src?`<b>(${letters[i]})</b> ${esc(p.cap||srcById(p.src)?.caption||"")}`:null).filter(Boolean);
  const n=figNumbers()[f.ref];
  return `<b>Figure ${n}.</b> ${esc(f.leadIn)} ${parts.join("; ")}${parts.length?".":""}`;""",
    r"""  const parts=f.panels.map((p,i)=>p.src?`<b>(${letters[i]})</b> ${fmtInline(esc(p.cap||srcById(p.src)?.caption||""))}`:null).filter(Boolean);
  const n=figNumbers()[f.ref];
  return `<b>Figure ${n}.</b> ${fmtInline(esc(f.leadIn))} ${parts.join("; ")}${parts.length?".":""}`;""")
sub(r"""<b>Table ${n}.</b> ${esc(t.caption)}</figcaption>""",
    r"""<b>Table ${n}.</b> ${fmtInline(esc(t.caption))}</figcaption>""")

# ------------------------------------------------- 3. the bar and the editing ops
sub(r"""function wordCount(t){ return (t||"").trim().split(/\s+/).filter(Boolean).length; }""",
    r"""function wordCount(t){ return (t||"").trim().split(/\s+/).filter(Boolean).length; }
/* Buttons and shortcuts write the notation; the preview beside the editor is
   where the result shows. `pre|post` rides on the button so one handler serves
   all of them. */
const FMT_BUTTONS = [
  {w:"**|**", html:"<b>B</b>", t:"Bold (Ctrl+B)", a:"Bold"},
  {w:"*|*",   html:"<i>I</i>", t:"Italic (Ctrl+I)", a:"Italic"},
  {w:"__|__", html:"<u>U</u>", t:"Underline (Ctrl+U)", a:"Underline"},
  {sep:true},
  {w:"^{|}",  html:"x<sup>2</sup>", t:"Superscript (Ctrl+Shift++)", a:"Superscript"},
  {w:"_{|}",  html:"x<sub>2</sub>", t:"Subscript (Ctrl+Shift+_)", a:"Subscript"},
  {sep:true},
  {l:"ul", html:"\u2022\u2009\u2014", t:"Bullet list", a:"Bullet list"},
  {l:"ol", html:"1.\u2009\u2014", t:"Numbered list", a:"Numbered list"}
];
function fmtBar(bid){
  return `<div class="fmtbar" role="toolbar" aria-label="Formatting">`+FMT_BUTTONS.map(f=>f.sep
    ? `<span class="sep" aria-hidden="true"></span>`
    : `<button type="button" class="fb" data-fmtfor="${bid}" ${f.w?`data-wrap="${esc(f.w)}"`:`data-list="${f.l}"`} title="${esc(f.t)}" aria-label="${esc(f.a)}">${f.html}</button>`
  ).join("")+`</div>`;
}
/* Wrapping toggles: run it twice on the same words and the marks come off,
   whether the selection sits inside them or around them. */
function wrapSel(ta, pre, post){
  if(!ta) return;
  const v=ta.value, a=ta.selectionStart??v.length, b=ta.selectionEnd??a, mid=v.slice(a,b);
  let val, sa, sb;
  if(mid && v.slice(Math.max(0,a-pre.length),a)===pre && v.slice(b,b+post.length)===post){
    val=v.slice(0,a-pre.length)+mid+v.slice(b+post.length); sa=a-pre.length; sb=b-pre.length;
  } else if(mid.length>=pre.length+post.length && mid.startsWith(pre) && mid.endsWith(post)){
    const inner=mid.slice(pre.length, mid.length-post.length);
    val=v.slice(0,a)+inner+v.slice(b); sa=a; sb=a+inner.length;
  } else {
    val=v.slice(0,a)+pre+mid+post+v.slice(b);
    sa=a+pre.length; sb=mid? b+pre.length : a+pre.length;
  }
  ta.value=val; ta.dispatchEvent(new Event("input",{bubbles:true}));
  ta.focus(); ta.setSelectionRange(sa,sb);
}
/* Whole lines, not the selection: a list marker belongs to its line. */
function toggleLines(ta, kind){
  if(!ta) return;
  const v=ta.value, a=ta.selectionStart??0, b=ta.selectionEnd??a;
  const from=v.lastIndexOf("\n",Math.max(0,a-1))+1;
  let to=v.indexOf("\n",b); if(to<0) to=v.length;
  const lines=v.slice(from,to).split("\n");
  const marked = kind==="ul" ? l=>/^\s*[-\u2022]\s+/.test(l) : l=>/^\s*\d+[.)]\s+/.test(l);
  const allMarked = lines.some(l=>l.trim()) && lines.every(l=>!l.trim()||marked(l));
  let n=0;
  const out=lines.map(l=>{
    if(!l.trim()) return l;
    const bare=l.replace(/^\s*(?:[-\u2022]|\d+[.)])\s+/,"");
    if(allMarked) return bare;
    n++; return kind==="ul" ? "- "+bare : n+". "+bare;
  }).join("\n");
  ta.value=v.slice(0,from)+out+v.slice(to);
  ta.dispatchEvent(new Event("input",{bubbles:true}));
  ta.focus(); ta.setSelectionRange(from,from+out.length);
}
function fmtKey(e){
  const ta=e.target; if(!(e.ctrlKey||e.metaKey)||e.altKey) return false;
  const k=(e.key||"").toLowerCase();
  if(e.shiftKey){
    /* The +/= key and the -/_ key, whichever character the layout reports. */
    if(e.key==="+"||e.key==="="){ e.preventDefault(); wrapSel(ta,"^{","}"); return true; }
    if(e.key==="_"||e.key==="-"){ e.preventDefault(); wrapSel(ta,"_{","}"); return true; }
    return false;
  }
  if(k==="b"){ e.preventDefault(); wrapSel(ta,"**","**"); return true; }
  if(k==="i"){ e.preventDefault(); wrapSel(ta,"*","*"); return true; }
  if(k==="u"){ e.preventDefault(); wrapSel(ta,"__","__"); return true; }
  return false;
}""")

sub(r"""  return wrap(`<textarea class="inp" data-block="${sec.id}|${b.id}" rows="4" spellcheck="true" aria-label="Paragraph" aria-autocomplete="list">${esc(b.text)}</textarea>
    <div class="blkbar">""",
    r"""  return wrap(fmtBar(b.id)+`<textarea class="inp" data-block="${sec.id}|${b.id}" rows="4" spellcheck="true" aria-label="Paragraph" aria-autocomplete="list">${esc(b.text)}</textarea>
    <div class="blkbar">""")

# ------------------------------------------------- 4. wiring
sub(r"""  on("[data-block]","keydown",e=>{ if(acKey(e)) return;""",
    r"""  /* mousedown is prevented so the textarea keeps focus and its selection. */
  on("[data-fmtfor]","mousedown",e=>e.preventDefault());
  on("[data-fmtfor]","click",e=>{ const el=e.currentTarget, ta=$(`[data-block$="|${el.dataset.fmtfor}"]`); if(!ta) return;
    if(el.dataset.list) toggleLines(ta,el.dataset.list);
    else { const [pre,post]=el.dataset.wrap.split("|"); wrapSel(ta,pre,post); } });
  on("[data-block]","keydown",e=>{ if(acKey(e)) return; if(fmtKey(e)) return;""")

sub(r"""  ["Ctrl+Enter","In a paragraph: add a new paragraph after it"],""",
    r"""  ["Ctrl+B / Ctrl+I / Ctrl+U","In a paragraph: bold, italic, underline"],
  ["Ctrl+Shift++ / Ctrl+Shift+_","In a paragraph: superscript, subscript"],
  ["Ctrl+Enter","In a paragraph: add a new paragraph after it"],""")

P.write_text(s, encoding="utf-8")
print("patched")
