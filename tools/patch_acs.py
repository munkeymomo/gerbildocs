#!/usr/bin/env python3
"""ACS Catalysis, from the author guidelines Mark supplied (12 Sep 2026)."""
import sys, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "app/static/index.html"
s = P.read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("expected %d occurrence(s), found %d:\n%s" % (count, n, old[:220]))
    s = s.replace(old, new, count)


sub(r"""  {
    id:"tpl_acs_catal", family:"ACS", label:"ACS Catalysis — Article",
    kind:"publication", style:"acs", verified:true,
    source:"https://researcher-resources.acs.org/publish/author_guidelines?coden=accacs",
    abstractLimit:300, citation:"superscript numeric",
    sections:["Introduction","Methods","Results and Discussion","Conclusions"],
    statements:["Acknowledgement","Associated Content"],
    experimental:"afterIntro",
    figureWidths:{single:"240 pt (3.33 in)", double:"300–504 pt (4.17–7 in)"},
    notes:["Abstract typically limited to 300 words.",
           "Methods must be a separate section in the main text, detailed enough to reproduce.",
           "No fixed page limit — length follows the subject matter."]
  },""",
    r"""  {
    id:"tpl_acs_catal", family:"ACS", label:"ACS Catalysis — Article",
    kind:"publication", style:"acs", verified:true,
    source:"ACS Catalysis author guidelines (supplied by the author, 12 September 2026)",
    abstractLimit:300, citation:"superscript numeric",
    keywordsMin:5, keywordsMax:8,
    sections:["Introduction","Methods","Results and Discussion","Conclusions"],
    statements:["Associated Content","Author Information","Acknowledgement","Supporting Information"],
    experimental:"afterIntro",
    figureWidths:{single:"240 pt (3.33 in, 8.5 cm)", double:"300–504 pt (4.17–7 in, 17.8 cm)",
                  maxHeight:"23.5 cm (the page type area is 17.8 × 23.5 cm)"},
    graphics:["Black and white line art at 1200 dpi, greyscale at 600 dpi, colour at 300 dpi.",
              "Arial or Helvetica in artwork, nothing smaller than 8 pt.",
              "Do not carry information by colour alone — add symbols, labels or patterns."],
    notes:["Abstracts to Articles are typically limited to 300 words, and an Abstract (TOC) graphic is required.",
           "Five to eight keywords are required.",
           "Methods is a separate section in the main text, either immediately before or immediately after Results and Discussion.",
           "Figures, schemes, charts and tables are numbered with Arabic numerals and placed near the point of first mention — ACS does not collect them at the top of the column the way RSC does, so leave figure placement in line.",
           "No footnotes, except an author-information footnote on the title page and footnotes to tables. Table footnotes take italic superscript letters, read across the row.",
           "Schemes (reaction sequences) and charts (structures without reactions) are numbered separately from figures. The Document Desk has no scheme or chart class yet — number them by hand or file them as figures and say so.",
           "No fixed page limit for Articles — length follows the subject matter."]
  },
  {
    id:"tpl_acs_catal_letter", family:"ACS", label:"ACS Catalysis — Letter",
    kind:"publication", style:"acs", verified:true,
    source:"ACS Catalysis author guidelines (supplied by the author, 12 September 2026)",
    abstractLimit:100, citation:"superscript numeric",
    keywordsMin:5, keywordsMax:8,
    sections:["Introduction","Methods","Results and Discussion","Conclusions"],
    statements:["Associated Content","Author Information","Acknowledgement","Supporting Information"],
    experimental:"afterIntro",
    limits:{words:"2000 in the main text, or about 8 double-spaced pages", displayItems:"4-5 figures"},
    figureWidths:{single:"240 pt (3.33 in, 8.5 cm)", double:"300–504 pt (4.17–7 in, 17.8 cm)",
                  maxHeight:"23.5 cm"},
    graphics:["Black and white line art at 1200 dpi, greyscale at 600 dpi, colour at 300 dpi.",
              "Arial or Helvetica in artwork, nothing smaller than 8 pt."],
    notes:["Letters are restricted to 2000 words or the equivalent — about eight double-spaced pages and four or five figures.",
           "The abstract is brief: under 100 words.",
           "Proofreading time is short, so a Letter should be in final, error-free form at submission.",
           "Everything else follows the Article guidelines."]
  },""")

# The ACS guidelines are explicit about keyword counts; the check should say so.
sub(r"""  if (tpl.limits && tpl.limits.references) {""",
    r"""  const kw = (S.keywords||[]).filter(Boolean).length;
  if (tpl.keywordsMin && kw && kw < tpl.keywordsMin) issues.push({kind:"keywords",
    text:`${kw} keyword${kw===1?"":"s"}; this journal asks for at least ${tpl.keywordsMin}`});
  if (tpl.keywordsMin && !kw) issues.push({kind:"keywords",
    text:`No keywords; this journal asks for ${tpl.keywordsMin}\u2013${tpl.keywordsMax}`});
  if (tpl.keywordsMax && kw > tpl.keywordsMax) issues.push({kind:"keywords",
    text:`${kw} keywords against a maximum of ${tpl.keywordsMax}`});
  if (tpl.limits && tpl.limits.references) {""")

sub(r"""          ${cur.headings?`<div class="note"><strong>Heading levels.</strong>""",
    r"""          ${cur.graphics?`<div class="note"><strong>Graphics.</strong><ul style="margin:5px 0 0;padding-left:16px">${cur.graphics.map(g=>`<li>${esc(g)}</li>`).join("")}</ul></div>`:""}
          ${cur.headings?`<div class="note"><strong>Heading levels.</strong>""")

P.write_text(s, encoding="utf-8")
print("patched")
