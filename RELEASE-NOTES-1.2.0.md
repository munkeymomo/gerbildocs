# GerbilDocs 1.2.0

A library of your own, so the method section you wrote last year is one click
away instead of buried in last year's manuscript.

## What's new

**My library** is a view of its own, holding everything that belongs to this
installation rather than to one document: blocks of saved text filed in
folders you name, the people you write with, and the organisations and
addresses they belong to.

**Saved text blocks.** Write an experimental section, a characterisation
method or a data availability statement once, then save it — from **Save to
library** in a section's header, or by right-clicking inside a paragraph. From
then on it goes into any paper from **Library text…** on the block bar,
**Insert ▾ → Text from library**, or the right-click menu.

The picker takes several blocks at once: folders on the left, tick boxes on
the right, and a count of exactly what will be inserted before it is. A saved
block splits back into its paragraphs on insertion and lands at the caret, so
a paragraph you were halfway through is left intact.

Saving a section deliberately leaves its figures, tables and equations behind.
Those belong to the document they were made for; a saved Experimental section
that dragged Figure 3 along with it would be a trap.

## Files

- `GerbilDocs-1.2.0-win32.zip` — portable Windows application. Unzip and run
  `GerbilDocs.exe`.
- `GerbilDocs-1.2.0-standalone.html` — single-file browser version, no
  install required.
- `gerbildocs-1.2.0-src.zip` — the source code, MIT licensed.

## Known limitations

The Windows build isn't code-signed, so SmartScreen will warn on first run;
choose "More info" then "Run anyway". Only Windows is built and tested. The
browser version keeps your documents, and your library, inside that browser
rather than as files on disk.
