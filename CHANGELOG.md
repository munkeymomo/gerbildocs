# Changelog

All notable changes to GerbilDocs are recorded here. GerbilDocs is released
under the MIT licence. Dates are ISO.

## 1.0.0 — 2026-09-21

First public release.

### Added

- A Write view with block-based editing — paragraphs, figures, tables,
  equations and Gantt charts — across four sub-documents (manuscript,
  supporting information, cover letter, data management plan) that share one
  set of front matter.
- Everything reusable — samples, acronyms, figures, tables, equations,
  citations and work packages — is referenced by id, so renaming one rewrites
  every mention across the document.
- Inline `@` cross-references, a command palette (Ctrl+K), and undo/redo.
- A paginated preview and PDF export built from real pages: paper size,
  margins, columns, headers, footers and page numbers.
- A Formatting view controlling page setup, columns, justification,
  hyphenation, every font, size and colour, caption labels and numbering,
  figure defaults and the author block.
- Layout templates carrying a complete page format, including submission
  templates read off the publishers' own Word templates for ACS, Science,
  Wiley and Nature Communications, plus RSC's article template, the AVS/AIP
  REVTeX two-column page, Elsevier, Physical Review B, an EPSRC case for
  support and a house lab report.
- A visual equation editor with a structural, non-LaTeX editing surface, a
  tabbed symbol picker, operator/formatting/chemistry palettes and a LaTeX
  toggle, plus an Equations view listing equations placed in the text
  alongside unplaced drafts.
- A Symbols dialog in the prose editor with chemistry, physics, Greek, Latin
  and combining-accent tabs.
- A Project plan view with aims and objectives, work packages, milestones and
  a Gantt chart that inserts into the document as a numbered figure.
- A Deposit view that compiles figures (SVG and PNG), tables and plots (CSV),
  equations (TeX), plot specifications (JSON) and attached raw data with
  checksums into the document folder with a generated `DEPOSIT.md`, ready for
  a DOI; run standalone it produces the same set as a zip.
- A Documents library with multiple locations as tabs and a collapsible
  folder tree.
- A reference library with RIS import and several built-in citation styles.
- A draft log with word-level track changes, per-author attribution and
  reviewer-response tooling.
- Word (.docx) export driven by the same format object as the PDF.
- Support for authors who hold several organisations, with saved people and
  organisations reusable across documents.
- Figures with custom row/column grids and half-width text-wrapped
  placement.

### Changed

- GerbilDocs is now a standalone release, no longer tied to any institution.
  It stores its vault in `%APPDATA%\GerbilDocs` and its documents in
  `Documents\GerbilDocs`, adopting the folders used by the earlier HarwellXPS
  Document Desk build automatically on first run.

### Fixed

- Long words no longer overflow the page.
- Choosing a layout now applies that layout's format as a whole, rather than
  leaving earlier overrides in place.
- A document created through the API alone no longer renders blank.
