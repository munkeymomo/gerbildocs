# Changelog

All notable changes to GerbilDocs are recorded here. GerbilDocs is released
under the MIT licence. Dates are ISO.

## 1.4.1 — 2026-09-28

### Fixed

- **The portable zip starts on other people's PCs.** Unzipped from a
  download with Explorer, 1.4.0 stopped at once with "Failed to resolve
  Python.Runtime.Loader.Initialize". Windows tags every file in a downloaded
  zip as coming from the internet, and .NET will not load tagged DLLs, which
  the app's window needs. GerbilDocs now clears that tag from its own DLLs
  when it starts. If you have the 1.4.0 zip, right-click it, choose
  Properties, tick Unblock, then unzip it again; or download 1.4.1.

### Changed

- **No window, no crash.** If the app's own window can't start for any
  reason, GerbilDocs opens in your web browser instead, with a small box that
  closes it when you're done. What went wrong is written to `desk.log`.
- **Every release is checked as a download.** The build unzips the portable
  zip, tags it the way a download is tagged, and fails unless the window's
  runtime loads.
- **Releases are published by the build, with every file attached**: the
  installer, the portable zip, the standalone page, the source, the notes and
  SHA256SUMS. SourceForge copies them from GitHub automatically.

## 1.4.0 — 2026-09-28

### Added

- **Journal styles, exactly.** Import a journal's own CSL style (`.csl`, from
  zotero.org/styles or the CSL repository) or BibTeX style (`.bst`) from the
  Style library, the References view or the bottom of the citation picker.
  The import shows the style's name, kind and citation format and three of
  your references set in it before anything is added. Citations, the order of
  the reference list and its numbering then follow the style — in the galley,
  the page preview, Word, plain text and word counts. A dependent style such as
  ACS Catalysis uses the nearest built-in shape until you import its parent,
  and says so. Style files carry an imported style with them.
- **Plots straight from your samples.** A dataset can take its rows from
  samples instead of pasted numbers: x by sample code or name, or by any
  property (Fe at.%, say), and columns that are properties or values typed
  against each sample. Nothing is copied — rename a sample or change a
  property and every plot, label and axis title follows. Optional labels on
  each point name the sample. **Paste measurements…** puts a block from Excel
  onto the samples in one step — rows by sample code or in order, one series
  per column named from its header, "± SD" or "err" columns as error bars —
  into this dataset or one dataset per series.
- **Uncertainty on sample properties.** A numeric property can carry an SD,
  SE, 95% CI or a plain ±. Enter "2.1 ± 0.3" in the Samples grid; tables print
  it as ± after the value, in brackets (2.1(3)) or not at all; CSV exports get
  a column of their own; plots from samples draw it as error bars, on x as well
  as y.
- **Style files.** Save how a document looks as a `.gerbilstyle` file and
  hand it to a colleague, who imports it into My templates in one step. A
  file carries the layout, fonts, page furniture, captions and sections, the
  citation style if it is one you made, and for a grant, the funder's
  structure: parts, limits, headings, guidance and where the references go.
  Never any of your text. Export from any template, from the Formatting view,
  or from a grant's Application parts; import from Templates or Application
  parts. The import shows what is inside before anything changes, offers a
  copy or a replacement when the name is taken, and can be undone. Imported
  grant formats appear beside the built-in ones when you start a grant.
- **References in captions.** Every caption field — tables, plots, figure
  lead-ins and panels, Gantt charts — takes `@` references and has a
  **Reference…** button, as paragraphs do.

### Changed

- The Samples page draws every entry box with a charcoal edge, so the grid
  reads as boxes rather than white on white.
- Every caption field shows, under it, the caption exactly as it will print —
  label, numbers and references resolved — and updates as you type.
- Gantt chart headers label every second, third, sixth or twelfth month when
  every month will not fit, so long projects read M3, M6, M9… instead of a
  crush of numbers. Milestone labels that would overlap move onto rows of
  their own, and labels at the right edge turn to the left.
- Deleting a template the open document uses keeps that layout with the
  document, so its pages do not change; you are asked first.
- **Figures print complete.** A plot placed in a figure is drawn with its
  axis titles, legend, labels and annotations, sized to the width it will
  print at, so the Formatting view's plot type size is the size on the page.
  They used to print as thumbnails without axis titles. Word gets the whole
  figure as one picture at 300 dpi, lettered as on the page.
- A figure with a single panel is not lettered and its caption has no "(a)".
- The two-column journal layouts set plot type at 7 pt, the size their
  columns take.
- Charts, Gantt charts and equations go into Word at their true proportions.
- Gantt labels too long for their space end in "…", with the full text on
  hover.

### Fixed

- A citation that appears only in a caption is now numbered and listed. It
  used to be left out of the reference list.
- Citations are numbered in the order they are printed, so an Experimental
  section placed after the Introduction, or moved to the SI, numbers where it
  appears rather than where it is stored.
- Style files are checked before anything is imported: a damaged, hostile or
  over-large file is refused with a reason and changes nothing.
- The browser version warns when it can no longer save because the browser's
  storage is full, instead of losing edits silently.
- The example document's equation renders as an equation.
- User-facing notes no longer mention internal design documents.
- Plots in a figure print complete: axis titles, legend, dataset labels,
  annotations and error bars, with the axis type at the size set in
  Formatting → Figures and plots. Each panel is drawn at its printed size,
  worked out from the figure's width on the page (a column, the full text
  width, or half for a wrapped figure) and its share of the layout, so the
  pages, the PDF, Word and the deposit's figure files all agree. Word gets
  the figure as the pages set it, panels on their grid and lettered, at
  300 dpi. The panel letter sits in the corner clear of the plot, in the
  plot font; it no longer covers the top tick label.
- A single-column figure on a one-column page prints at the 58% width the
  galley shows. It printed full width.
- A figure of one panel is no longer lettered: no "a" on the panel and no
  "(a)" in its caption, in the pages, Word or the deposit.
- Notes in the Samples view, the guided tour, a template's notes and a
  generated block no longer name internal design documents, an old sample
  code or the product's old name. Opening a folder that is not a document
  says it is not a GerbilDocs document.
- Gantt chart labels are fitted to their space and end in "…" when cut, with
  the full title shown on hover; they were cut mid-word at a fixed number of
  characters. The label column widens for long titles, up to a third of the
  chart.

## 1.3.0 — 2026-09-27

### Added

- **Stack plots.** A plot is now made of datasets, and a dataset can hold
  several columns — a spectrum with its envelope and fitted components is one
  dataset. Arrange datasets overlaid or stacked, with the offset as a
  percentage, bottom-up or top-down, and hide the y tick labels when stacked.
- **Add / edit data is a dataset manager.** Datasets down the left (reorder,
  add, duplicate, delete, hide, split one per column, merge); the paste-from-
  Excel grid on the right for the one selected, with its name, sample link,
  scale, chart type and axis.
- **Normalise and scale.** Normalise to the maximum, to 0–1 or to unit area,
  per dataset (one factor from its first column, so components stay in
  proportion) or per column. Scale any dataset, and show the factor on the plot
  as "×5".
- **Dataset labels** on the traces, above or below, at the left or right,
  showing the typed name or the linked sample's code or name. A linked label
  follows the sample: rename it in Samples and every plot changes.
- **Error bars**: a percentage, a fixed amount, or custom values entered in
  their own x / ±error grid; either side or both.
- **Combined charts and a second axis.** Each dataset can be a line, points,
  bars or a filled area, and sit on the left or a right-hand y axis. Each axis
  has its own label, limits, direction and from-zero; the left may be
  logarithmic.
- **Shapes and annotations** drawn on the plot with the mouse: text, arrows,
  lines, boxes, ellipses, vertical and horizontal marker lines, shaded bands.
  They are held in data coordinates and appear in figures and exports.
- **Common column identities.** One style per column slot across every dataset
  — raw data black, envelope red, a component green with a gradient fill — and
  a legend that lists the slots.
- **Palettes and a full colour picker.** Default, Pastel, Block colours,
  Colour-blind safe (Okabe–Ito), Viridis, Greyscale, Earth tones and Vivid,
  plus the system colour picker and a hex field on every colour control.
- **Grant applications are made of the funder's parts.** Each part is its own
  tab, galley and export, with a word limit (a text box on the funder's form)
  or a page limit (an attachment). The new **Application parts** view sets the
  parts, their limits, headings and the funder's guidance, and shows every
  part's words and pages against its limits.
- **Funder formats**: EPSRC standard research grant (UKRI Funding Service),
  EPSRC New Investigator Award, the legacy four-part case for support, or
  blank. A **Form answers** checklist covers the short questions that are not
  prose — thematic area, core team roles, letters of support, sensitive
  information.
- **Copy for the form**: a text-box part as plain text for pasting, with its
  word count.
- **References in a grant** are either one list in a References part, numbered
  across the whole application, or one list per part.
- **Compact reference style**, with and without the DOI, for any document:
  `Doe J et al. J. Ex. Stud. 12, 345 (2024)`.

### Changed

- Grant parts no longer print the title, authors, affiliations, abstract or
  keywords — the funder's form asks for those separately. The title still
  names the application, its files and its page headers.
- The EPSRC layouts are single spaced, as the funder asks (they were 1.25).
  Documents on the older EPSRC template will paginate tighter.
- An untitled section no longer prints an empty numbered heading, in any kind
  of document; the sections after it are numbered accordingly.
- A grant's Justification of Resources (and any grant part) numbers its figures
  1, 2… rather than S1, S2.

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
