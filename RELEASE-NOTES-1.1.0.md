# GerbilDocs 1.1.0

A round of work on the parts of writing a paper that are fiddly by hand:
cross-references to more than one thing, adding a section without losing your
place, British versus American spelling, and author names that have to appear
three different ways depending on the journal.

## What's new

A cross-reference can name several things at once. The **Reference…** button
opens a picker: pick a kind on the left — figures, SI figures, tables,
equations, citations, samples, acronyms — tick what you want, and insert them
all. Three figures print as "Figs. S1–3", and the range re-collapses itself if
a figure is later inserted in the middle of the run. Typing `@` still inserts
one thing.

Sections and sub-sections can be added from a strip that rides with the text
rather than only from the top of the view.

A document language, which drives spell-checking and hyphenation, and a
British/American spelling check that no dictionary can do for you — "color"
and "colour" are both real words. Right-click a word for the correction, or
review the whole document from Formatting. Right-click also offers synonyms
for the words scientific prose wears out; hold Shift for your system's own
spelling menu.

An AVS (JVST) submission template — single column, double-spaced, which is
what the journal asks you to send. The existing two-column AVS template is now
labelled as the published look.

Authors are held as given name, initials and surname, so one setting restyles
the entire byline. Organisations have a postcode. The saved people and
organisations panel is a list for adding, with the fields behind an Edit
button. The example document is generic placeholder content.

## Fixed

A `profile.json` carrying a byte-order mark — which Notepad and PowerShell
both write — stopped the application starting. It no longer can.

## Files

- `GerbilDocs-1.1.0-win32.zip` — portable Windows application. Unzip and run
  `GerbilDocs.exe`.
- `GerbilDocs-1.1.0-standalone.html` — single-file browser version, no
  install required.
- `gerbildocs-1.1.0-src.zip` — the source code, MIT licensed.

## Known limitations

The Windows build isn't code-signed, so SmartScreen will warn on first run;
choose "More info" then "Run anyway". Only Windows is built and tested. The
browser version keeps your documents inside that browser rather than as files
on disk.
