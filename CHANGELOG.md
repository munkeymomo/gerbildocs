# Changelog

All notable changes to GerbilDocs are recorded here. GerbilDocs is released
under the MIT licence. Dates are ISO.

## 1.2.0 — 2026-09-24

### Added

- **My library**: a view of its own for everything kept on this installation
  rather than in one document. Blocks of saved text, filed in folders you
  name; the people you write with; the organisations and addresses they
  belong to.
- Saved text blocks. Write an experimental section, a data availability
  statement or a characterisation method once, save it with **Save to
  library** in a section header or from the right-click menu inside a
  paragraph, and insert it into any paper afterwards — from **Library text…**
  on the block bar, **Insert ▾ → Text from library**, or the right-click menu.
  The picker takes several at once: folders on the left, tick boxes on the
  right, and a count of what will be inserted before it is. A block splits
  back into its paragraphs on insertion, and goes in at the caret, so a
  paragraph you are halfway through is not disturbed.
- Saving a section leaves its figures, tables and equations behind on purpose.
  They belong to the document they were made for, and a saved Experimental
  section that dragged Figure 3 along with it would be a trap.

### Changed

- The saved people and organisations are now sections of the library view —
  Authors, and Organisations & addresses — as well as the quick-add panel
  beside the byline, from one renderer so the two cannot drift.

### Fixed

- The self-check now compares the interface's copy of the library key list
  against the vault's, so a key added to one and not the other — the mistake
  that silently empties a shared library on the next new document — fails the
  build rather than a user's afternoon.

## 1.1.0 — 2026-09-24

### Added

- A cross-reference can name several things at once. The **Reference…** button
  opens a picker: choose a kind on the left — figures, SI figures, tables,
  equations, citations, samples, acronyms — tick what you want, and insert them
  all. Three figures become "Figs. S1–3", and the range re-collapses itself
  when a figure is inserted in the middle of the run. Non-consecutive numbers
  read as "Figs. 1, 3 and 5", and the label pluralises according to the layout
  ("Figure"/"Figures", "FIG."/"FIGS."). Ticks may cross kinds; one token is
  built per kind and the footer shows the finished text before anything is
  inserted. Typing `@` still inserts one thing, as it did.
- Sections and sub-sections can be added from a strip that rides with the
  text, instead of only from the top of the view. The strip also names the
  section currently under the reader.
- A document language, which is what the browser's spell-checker underlines
  against and what hyphenation follows.
- A British/American spelling check, which no dictionary can do — "color" and
  "colour" are both real words, and only the document's language makes one of
  them wrong. Right-click a word for the correction, or review the whole
  document at once from Formatting.
- A right-click menu in the editor offering that correction and synonyms for
  the words scientific prose wears out. Shift + right-click still reaches the
  system's own spelling menu.
- An AVS (JVST) submission template: single column, double-spaced, which is
  what the journal asks you to send. The existing two-column AVS template is
  now labelled as the published look, not for submission.
- A first-line indent switch, next to the measurement it sets.
- Authors are held as given name, initials and surname, with a name style
  chosen by the layout — "Jane A. Doe", "J. A. Doe" or "Doe, J. A." — so one
  setting restyles the whole byline. Surname particles ("van der", "dos") stay
  with the surname in both the typed and the reference-manager order.
- Organisations have a postcode, printed with the town rather than as another
  comma-separated field.

### Changed

- The saved people and organisations panel is a list for adding, with the
  fields behind an Edit button.
- The example document is now generic placeholder content — invented people,
  an invented journal and an unnamed material — instead of a real manuscript.

### Fixed

- A `profile.json` carrying a byte-order mark, which Notepad and PowerShell
  both write, stopped the application starting. Every JSON file the
  application reads now tolerates one, and a profile that cannot be read is
  reported and ignored rather than being allowed to prevent a launch.

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
