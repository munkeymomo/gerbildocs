# GerbilDocs 1.0.0

GerbilDocs is a free tool for writing papers, reports and grant applications,
built around the idea that everything you reuse — samples, acronyms,
figures, tables, equations, citations, work packages — should be referenced
by id rather than retyped, so a rename propagates everywhere it's used. This
is the first public release.

The download includes a portable Windows application (no installer, no
admin rights needed), a single-file browser build for trying GerbilDocs
without installing anything, and the full MIT-licensed source.

## Files

- `GerbilDocs-1.0.0-win32.zip` — portable Windows application. Unzip and run
  `GerbilDocs.exe`.
- `GerbilDocs-1.0.0-standalone.html` — single-file browser version, no
  install required.
- `gerbildocs-1.0.0-src.zip` — the source code, MIT licensed.

## Known limitations

The Windows build isn't code-signed, so SmartScreen will warn on first run;
choose "More info" then "Run anyway" to continue. Only Windows is built and
tested for this release. The browser version keeps your documents inside
that browser rather than as files on disk, and can't write a document
folder — use the Windows build if you want your work as folders you can
back up, copy or move.
