# Decisions that bind this repository

The full design set — VISION-000, MODEL-001, ARCH-W01, ROADMAP-W01, PLUGIN-001,
DOC-001 (document builder decisions) and DOC-002 (editions and packaging) —
lives in the original workbench project this module was pulled out of, which
remains the system of record for that history. Duplicating them here would
guarantee drift. What follows is only what someone working in this repository
needs in front of them.

## The shape

One interface, two hosts (DOC-002). This repository is the desktop host: the
backend runs locally and the same page runs in a native window. The browser host
is the same page served from a server, talking to the project management base.
Desktop first, because the folder, the collation of raw data into a deposition
set, and working offline at the instrument are filesystem features the browser
edition structurally cannot have.

## The rule everything rests on

Everything reusable is referenced by id, never by name (DOC-001 §11). Samples,
acronyms, figures, tables, equations and citations all sit in text as
`[@kind:id]` and are resolved when the page renders. Rename a sample code and
the manuscript, the SI, every caption and every table header follow. Any feature
that stores a display string in prose breaks this and should be refused.

## Scope boundaries

- **Samples** use the MODEL-001 §5 shape minus the issued-code allocator. Do not
  grow sample features the Workbench model does not have.
- **Attachments** are the Workbench's `blob`/`dataset` relationship in
  miniature. On absorption they become dataset references.
- **The store** is plain `sqlite3` with the interface's JSON as the contract.
  ADR-W03 puts the Workbench on SQLAlchemy and Alembic; building that schema
  before MODEL-001 §8 is settled would mean migrating twice.

## Known gaps, deliberately

- Multi-editor attribution is honest only for serial hand-off. Identity is per
  copy; two people editing at once produces two divergent copies with no merge.
  That is the Phase 5 server's job, not this one's.
- The built-in citation styles are hand-written shapes in the interface. A
  journal's own CSL or BibTeX style can be imported instead and formats
  exactly (see "A citation style can be the journal's own file"); the shapes
  stay, unchanged, for the documents that use them.
- `.ens` import recovers a style's shape, not its field order. The container is
  a nested tag/length/value stream with UTF-16BE strings; the field opcodes
  between the literal separators are undocumented. See DOC-001.

## Local storage (11 September 2026)

- **The vault backs itself up on every open.** `Store` copies the database into
  `backups/` with SQLite's online backup API (so the write-ahead log is
  included) and keeps the last five. A file that fails `PRAGMA quick_check` is
  moved aside as `desk.sqlite.corrupt-<stamp>` — never deleted — the newest
  passing backup is restored, and the library is re-applied from its JSON
  mirror. What happened is in `Store.notices` and on `/api/health`, and the
  interface shows it. Silent loss is the failure mode this is designed against.
- **`schema_version` is a real migration hook.** `MIGRATIONS[n]` takes a
  database at n-1 to n, one step at a time, inside the open. A vault written by
  a newer release raises `VaultTooNew` rather than being downgraded. v2 adds
  `documents.opened_at` so the picker orders by what you were working on, not
  what last auto-saved.
- **The library is mirrored to `<app>/library/<key>.json`** on every write,
  atomically (write-then-rename). This is what `config.AppPaths.library`
  promised and nothing wrote. It is a recovery path and a readable copy, not a
  second source of truth: the database wins unless the database is gone.
- **Writes under the application data folder are the one exception to "nothing
  outside a document folder".** The vault, its backups and the library mirror
  live there; they are the application's own files, never a user path, and no
  user-supplied string reaches them.

## The folder holds the document (11 September 2026)

- **`document.json` is written into the document folder on every save.** Until
  now the folder held exports and data but the document itself lived only in
  the vault, so "a document is a folder" was not true and a lost vault lost
  everything. Now the vault is an index and a cache; the folder is complete on
  its own. `layout.plan_document` lists it first. It holds the document-scoped
  half of the state — the library (references, samples, styles, acronyms) is
  app-scoped and is not in it, which is an open question for hand-off; see
  HANDOFF §6.
- **"Open an existing folder" adopts, it never creates.** `POST
  /documents/adopt` reads the folder's `document.json` and registers it; a
  folder already in the vault is returned, not duplicated; a folder with no
  document is refused with a 400. `GET /documents/discover` lists folders under
  the documents folder that the vault does not know, which is the recovery
  path after a vault reset.
- **Opening a document is what orders the list.** `GET /documents/{id}` sets
  `opened_at`; `list_documents` orders by it. Auto-save no longer reorders the
  picker under you.
- **Reveal takes no path from the request.** `POST /documents/{id}/reveal`
  resolves the id through the vault; `POST /reveal?target=documents|app` is the
  only other option. `os.startfile` on Windows, `open` on macOS, `xdg-open`
  elsewhere, detached so the file manager outlives the request.
- **The native folder dialog is a host capability, not a route's business.**
  `launch.py` installs `app.state.pick_folder` after the webview window exists;
  `POST /dialog/folder` returns 501 without it (`--browser` mode, self-check)
  and the interface falls back to a typed path. `/api/health` advertises
  `folder_dialog` so the interface knows which to offer.

## The interface with a vault (11 September 2026)

- **Everything new is gated on `DESK.online`.** The Documents button, the
  Reveal button, the save-status chip, the start screen, the picker and the
  example loader are inert or hidden when the page is opened as a file. The
  standalone copy behaves exactly as before.
- **A new document is a new vault document.** Before, "New document" in the
  desktop edition overwrote the open document's row. Now it posts a blank
  state and switches to the returned one. Library keys are sent only when the
  vault has no value for them: the shared library is replaced wholesale by
  `put_library`, so a blank `refs: []` from a new document would have wiped
  it. `withoutExistingLibrary()` is that guard.
- **The vault is the only source when connected.** `boot()` no longer falls
  back to `localStorage` or the example when the vault is empty. An empty
  vault gets a start screen — new, open a folder, load the example. Nothing is
  seeded unless asked.
- **`migrate()` back-fills from the example only offline.** Connected, missing
  fields become empty, so a real document can never acquire the example's
  samples or acronyms through a migration. Built-in citation styles are not
  example data and are supplied in both modes.
- **The example brings its library only into an empty one.** Citations are
  positional over the shared refs list, so a partial merge would re-point
  existing citations. All or nothing, and never over real data.
- **Switching documents flushes first.** The bridge captures the document id
  when a save is queued, and `open`/`create`/`adopt` await `flush()`; a save
  that fails is kept and retried every five seconds, and `pagehide` fires a
  `keepalive` PUT with whatever is still pending.
- **Two pre-existing crashes fixed** that only a blank document could reach:
  `vSamples` and `vStyles` assumed at least one sample and one reference.
- **`render()` no longer returns early when the vault is connected.** It did,
  which would have left the desktop edition blank below the header. The
  FastAPI layer had never run, so nobody had seen it.

## MathJax offline (11 September 2026)

- **The bundle is `tex-svg-full.js`, not `tex-svg.js`.** The smaller component
  fetches `mhchem` on demand from a path relative to itself, so "one file" was
  never true for `\ce{}`. The full component is one file, ~2.3 MB, and needs
  nothing else. `tools/fetch_mathjax.py` (stdlib only) fetches it, validates
  that it is a script and carries mhchem, and records the SHA-256.
- **The page loads MathJax as a script element it creates**, local first
  (`/static/vendor/mathjax/` when served, `vendor/mathjax/` beside the file in
  a checkout), CDN on error, MathML fallback if both fail. Readiness is
  signalled through MathJax's own `startup.ready` hook rather than a check at
  page bottom, because the script is now asynchronous. The download itself
  could not be tested where this was written; the loader and validator were.

## Building the Windows application (11 September 2026)

- **GitHub Actions on `windows-latest` is the reference build.** Neither the
  authoring environment nor a typical session has Windows, PyInstaller and
  Inno Setup together. `.github/workflows/build.yml` runs the tests and the
  self-check, fetches MathJax, builds the onedir bundle, runs Inno Setup,
  smoke-runs the built executable against `/api/health`, and uploads the
  installer and a portable zip; a `v*` tag attaches them to a release.
- **`packaging/build.py` checks before and after.** Python version,
  PyInstaller present, spec and interface present, MathJax bundled (or
  `--allow-missing-mathjax` said explicitly), then that the executable and
  `index.html` are actually in the bundle, then that the installer exists.
  The version comes from `pyproject.toml` and is passed to Inno Setup, so
  there is one place to bump it.
- **Lint is reported, not enforced, in CI.** `ruff`/`mypy` could not be run
  where this was written and the existing code has lines over the limit. Make
  it blocking once it is green.
- **A windowed build has no console.** `launch.py` sends `sys.stdout`/`stderr`
  to `<app>/logs/desk.log` when PyInstaller leaves them as `None`.

## The Data Management tab is the deposit (20 September 2026)

- **A deposit is a browser, not a text field.** The Data Management
  sub-document used to be prose alone, and "Files & data" was a separate view
  with an overlapping folder tree. They are now one panel — `depositPanelHTML()`
  — drawn in the renamed **Deposit** view and above the Data Management tab's
  sections. The statement stays writable underneath it, because it is the one
  part a person has to write.
- **The interface renders, the backend files.** The browser knows how to draw a
  figure, a table, a plot and an equation; only `layout.py` knows where each
  belongs. So the page composes and posts `{figures, tables, plots, equations}`
  to `POST /api/documents/{id}/deposit`, and `services/deposit.py` writes each
  one at its planned path through the `Workspace`. A reference that would climb
  out of the folder is refused by `resolve_within`, which is why `layout.py`
  plans `plots/<ref>.csv` verbatim rather than sanitising the reference itself.
- **New in the plan**: `plots/<ref>.csv` (one per plot), `equations/equation-NN.tex`
  (one per equation block, in reading order across sub-documents, numbered or
  not), and a top-level `DEPOSIT.md`. The `data/README.md` that already existed
  describes the raw data; `DEPOSIT.md` describes the whole folder.
- **No vault, same set.** Standalone, Compile deposit builds the identical files
  in the browser and saves them as `<slug>-deposit.zip`, `DEPOSIT.md` included
  and generated from the same shape. Nothing about the feature requires a
  backend to be understood.
- **The editions table is gone.** It was developer prose about how the product
  is built, sitting in a view a user opens to assemble a submission.

## A grant is made of the funder's parts (27 September 2026)

- **Parts, not four fixed files.** A grant carries `grantParts` — the parts the
  funder asks for, in its order: `{k, l, mode, words, pages, extraPages,
  headings, guidance, showTitle, limits}`. `mode` is `textbox` (pasted into a
  form, a word limit) or `attachment` (laid out and uploaded as a PDF, a page
  limit). Each part is a sub-document with its own tab, galley and export.
  Every other kind keeps its fixed list. `layout.subdocs_for(document)` answers
  for both, and `plan_document` and `equations_in_order` read it, so a grant's
  exports are named after its parts (`vision-and-approach.docx`); two parts
  with one name get `-2`, `-3`. The interface mirrors it in `subdocsOf()` and
  `subdocFilenames()`.
- **Old grants keep their four.** A grant with no `grantParts` becomes the
  legacy four parts on open — same keys, same names, as documents, no limits —
  with its references numbered across the application and listed in the Case
  for Support. Nothing is renamed or dropped; a key the fixed list does not
  know becomes a part too.
- **`si` in a grant is not supporting information.** The old Justification of
  Resources was keyed `si` and so numbered its figures S1, S2. A grant part is
  its own submission: no S prefix and no Experimental section moved into it.
  Papers and reports are unchanged.
- **The title names the application; it prints in no part.** The form asks for
  title, people and summary separately, so no grant part prints the title,
  byline, affiliations, abstract or keywords unless the part is set to show the
  title. The title still names files and fills page headers.
- **References: one list, or one per part.** `grantRefs.mode` is `part` (one
  numbering in part order, the list printed in the part `grantRefs.part` — the
  EPSRC shape) or `inline` (each part numbers from 1 and lists its own). The
  list may be set in its own style (`grantRefs.style`); a numbered list under an
  author–date document style puts numbers in the text. A compact style,
  shipped twice (with and without the DOI), is added to existing libraries by
  shape-and-options rather than shape alone.
- **Presets quote the funder or are not presets.** `GRANT_FORMATS` holds only
  limits read from a call: the EPSRC standard research grant from the supplied
  opportunity text, the New Investigator Award from its ukri.org page (cited in
  the preset). No limit is guessed; a question with none stated has none set.
- **A section may have no heading, in any kind.** A grant part with no preset
  headings starts as one untitled section, so nothing unasked-for is pasted or
  counted. An untitled section prints no heading and takes no number — in a
  paper or report too, where it used to print an empty heading and use up a
  number. That changes numbered output for any paper with an untitled
  section; it is kept deliberately as a fix.
- **EPSRC layouts are single spaced.** `FORMAT_EPSRC` was 1.25 lines; it is now
  Arial at 1.15 on the page (Arial's own single line) and true single spacing
  in Word (`lineSpacing: "single"`). The Je-S rules asked for single spacing
  too, so documents on the Je-S-era `tpl_epsrc` now paginate tighter than they
  did. The house report layout, derived from it, keeps its 1.4.
- **A preset never takes the author's formatting or citation style.** Taking a
  grant format on an existing document changes the layout only if it is a
  different one and the author leaves the box ticked; the confirm dialog lists
  the Formatting-view changes that would be replaced. The citation style is
  left alone — the reference list takes its style from `grantRefs`. Only a new
  document takes the format's layout and style whole.
- **Shipped styles are never edited in place.** Ticking the DOI on a built-in
  compact style switches to its twin (or a copy); a library is de-duplicated by
  id on load, keeping the first, because an earlier build could ship a style a
  second time under an id already present.
- **Grant structure is document-scoped.** Nothing was added to `LIBRARY_KEYS`.

## A plot is made of datasets (27 September 2026)

- **Datasets inside a plot.** `plot.datasets` is the stacking order; each is
  `{id, name, sampleId, scale, visible, type, axis}`. A dataset may hold several
  columns — a spectrum, its envelope and its fitted components are one dataset.
  `plot.series` stays the flat list of traces, each now carrying `ds` (its
  dataset) and `col` (its column slot), so everything that already read
  `series` — the CSV, the list, the summaries — goes on working.
- **Old plots are one dataset.** `migratePlots()` gives a plot without datasets
  exactly one, holding every series, and `renderChart` reads an un-migrated plot
  the same way without changing it. An old plot draws identically.
- **Normalise, then scale, then offset.** Normalising is per dataset by
  default — one factor from its first column, applied to all its columns — so
  the raw data, envelope and components of one spectrum stay consistent with
  each other. Error bars follow the normalising and the scale, never the offset.
- **A dataset linked to a sample prints the sample, live.** `sampleId` is a
  reference, as in prose: renaming the sample renames the label on every plot.
  The typed name is kept as the fallback if the sample is deleted.
- **Column identities are slots, not names.** With `commonColumns` on,
  `columnStyles[col]` styles every trace in that slot across every dataset, and
  the legend lists slots rather than traces.
- **Annotations are in data coordinates** (x and the left y axis, as drawn), so
  a marker at 458 eV stays at 458 eV when the range changes.
- **Opening the data editor and pressing Apply changes nothing.** Traces that do
  not share an x array are aligned row by row in their own order, never keyed
  by value alone, so an out-and-back scan (repeated x) survives the round trip;
  merging datasets never drops or reorders a point.
- **Nothing new is app-scoped.** Plots were already in `LIBRARY_KEYS`; palettes
  are a built-in table, chosen per plot.

## A figure is drawn at its printed size (28 September 2026)

- **Points, from the page.** `figGeom(f)` gives a figure's width from its span
  and the page — the full text width for double; a column, or 58% of a
  one-column page, for single; half of that for a wrapped figure, the widths
  the page CSS gives — its height from the layout's aspect (`cellGeom`), and
  each panel's box from the layout's fractions less a 6 pt gap. A panel is
  drawn in a viewBox of exactly that size, so the plot font in Formatting
  prints at its size. The galley and the Figures view show the same drawing
  scaled.
- **Complete, laid out from the type.** Document panels use `renderChart`'s
  fit mode: axis titles, legend, dataset labels, annotations and error bars
  all drawn; margins worked out from the type; ticks thinned to what fits
  (never to the range's bare ends); category names wrapped, then slanted; a
  title longer than its axis on two lines. A panel too small for its type is
  drawn crowded rather than shrunk — the preview shows it and the remedy is
  the author's (a wider figure or smaller axis type). The editor's preview
  keeps its fixed margins and is unchanged. Thumbnail mode has no callers
  left.
- **The letter is part of the panel.** Plot font, bold, at the plot size, in
  the corner above the plot area; an image keeps a strip for it. A figure of
  one panel has no letter and no "(a)".
- **Word and the deposit place the same grid.** `figureGridSVG` composes the
  panels as the page sets them; Word gets it as one picture at the figure's
  printed width, rasterised at 300 dpi, and the deposit's SVG is in points
  with the caption in the caption font.

## Samples in plots; property uncertainty (28 September 2026)

Asked for by Mark: plot directly against a sample property (atomic % of Fe),
with labels that follow the samples, and error bars from the samples' own
uncertainties. It extends the rule everything rests on — a reference, never a
copy — from prose and tables to plots. It also grows the sample shape by one
field, which the scope note above would otherwise refuse; it is additive, so a
register that takes the samples over maps it or ignores it.

- **A property can carry an uncertainty.** `pd.err` is `"none"` (the default,
  and what `migrate()` gives every older property), `"sd"`, `"se"`, `"ci95"`
  or `"pm"` (a ± that is not specified further); text properties carry none.
  A sample keeps it beside the value, as typed: `sm.propErr[propId]`. In the
  Samples grid such a property has two fields; "2.1 ± 0.3", "2.1+-0.3",
  "2.1 +/- 0.3", "2.1 (0.3)" and the concise "2.1(3)" typed or pasted into the
  value are split into both (`parseValErr`). Values stay strings; they are read
  as numbers only where a number is needed (`propVE`).
- **A value is a number whole, or not at all** (`numText`, `propNum`): digits
  with a decimal point, or with a decimal comma when there is no point ("2,1",
  "2,1 ± 0,3", "2,1(3)"). "1,234" — three digits after a non-zero whole part —
  could be a thousands separator, and "1,234.5" mixes the two conventions, so
  neither is read; nor is "812 (BET)" or "6.4 nm". Nothing is read from a
  prefix. A value that is not a number is left out of the plot and named, as
  typed, in its Left out note; the Samples grid marks the cell as it is typed;
  a table prints it as typed; the table's CSV writes numbers with a point.
- **A sample table prints it three ways** (`t.uncert`): "2.1 ± 0.3" (the
  default), the concise "2.1(3)" — the value padded, never rounded, to the
  uncertainty's last digit — or not at all. The header says "(mean ± SD)"
  unless `t.uncertHead` is false or the kind is a plain ±. The galley, the page
  preview and Word print the same cells. The table's CSV gives every
  uncertainty a column of its own and never puts "±" in a numeric cell;
  hidden means no column.
- **Property values appear nowhere else inline.** Text refers to a sample by
  its code; no token prints a property value, so there is nothing more to
  format.
- **A dataset's source is pasted data or the samples.** `d.source={kind:
  "samples", sampleIds, x:{kind:"code"|"name"|"code-name"|"prop", prop?,
  err?}, keepOrder?, cols:[{kind:"prop", prop, err} | {kind:"typed", values:
  {[sampleId]:number}, err?:{…}}]}` and `d.pointLabels`. It holds references
  only; a typed column holds numbers keyed by sample id. Column k is the trace
  in slot k, whose stored series entry holds only its look (and, for a property
  column, the property's label as a fallback name) — never x or y.
- **One resolver.** `plotView(p)` returns the plot with every sample dataset
  read against the samples as they are now; `renderChart` (so the preview,
  figure panels, the composed figure and Word), `plotCsv` and the editor's
  summaries all read through it, and nothing is written back. A plot with no
  sample dataset is returned as it is, so every older plot draws byte for byte
  as before.
- **x by code or name is categorical on any chart type**: one category per
  sample that has something to draw, in dataset order; line and scatter points
  sit on the categories. **x by a property is numeric**, in x order unless
  `keepOrder`, with a little room at each end. A blank x or y leaves that
  sample out of that trace; the data manager and the plot editor say which and
  why. An axis title left blank is the plotted property's label and unit, live;
  typing one overrides it.
- **Error bars.** A property column's uncertainty is its y error bars; a
  property on x gives x error bars (`series.errX`, drawn with caps, in x's own
  units — normalising and scaling act on y only). Pasted data can have x error
  bars too: the x column takes the same modes as any other (± %, ± fixed,
  custom values by x).
- **Measurements are pasted onto samples in one step** (`measParse`,
  `measApply`). "Paste measurements…" in the sample grid (and in its empty
  state, and when x is a property) takes a block from Excel and makes typed
  columns: one per value column, named from a header row ("series n"
  without one). A column whose header names an uncertainty — "±", "+/-",
  "err", "error", "SD", "s.d.", "stdev", "std", "σ", "SE", "SEM", "95% CI",
  alone or beside a name ("Conversion SD", "Yield (err)") — is the ± of the
  column before it (`measIsErrHead`). Without a header, "every second column
  is the ± of the one before" is a toggle, guessed from the numbers (an even
  number of columns, each second one non-negative and mostly well under its
  value: `measGuessPairs`); each column's role can be changed in the preview
  before Apply. Rows that start with a sample code go to that sample, added
  to the dataset if it is not in it; a code that is not a sample is shown
  unmatched and skipped, or created as a sample with that code when the box
  is ticked (off by default — the code is the one the author typed, so this is
  not code generation). Otherwise rows follow the dataset's order. Values are
  read as every sample value is (`propNum`, `parseValErr`): a decimal comma is
  accepted, "0.42 ± 0.03" in one cell is split, and anything else is flagged
  in the preview and left out. The columns go into this dataset (a typed
  column of the same name is filled, not repeated, and the placeholder column
  a new sample dataset starts with gives way) or each into a dataset of its
  own with the same samples and x — for stacking, or separate axes. The paste
  never changes x.
- **The in-grid paste is as forgiving.** A block wider than the typed columns
  to the right makes more; a header row names the columns it lands in when
  they have no name, and an uncertainty header makes its column the ± of the
  one before.
- **Pasted (non-sample) data reads numbers the same way.** The data grid uses
  `propNum` too, so "2,1" is 2.1 and "1,234", "12.5%" or "n/a" are left out of
  their trace rather than read in part; the grid says which cells, before
  Apply, and when text in x makes every x a category. Numbers already stored
  are read back exactly, so opening the data and applying it changes nothing.
- **Point labels** name each point by its sample's code, placed at the first of
  eight spots round the point that is inside the plot and clear of points,
  error bars, lines and labels already placed; a plot with point labels keeps a
  label's height of room above and below its data.
- **A sample or property a plot uses is not deleted from under it**, as a
  sample a table uses already was not: the Samples view refuses and names
  where it is used. If one goes anyway (another document, an import), the plot
  leaves it out and says so rather than breaking.
- **Nothing new is app-scoped.** Samples, property definitions and plots were
  already in `LIBRARY_KEYS`.

## A style travels as a file (27 September 2026)

- **One file, `.gerbilstyle`.** JSON (a `.json` name is accepted too) made in
  three places: any template in Templates (**Export…**), the Formatting view
  (**Export this formatting…** — the document's resolved format on its
  template's base, as "Save as template" builds it), and Application parts
  (**Export this format…** — the grant's parts and reference settings with its
  layout and formatting). **Import style…** in Templates and in Application
  parts reads one. It carries formatting and structure only: never the
  document's text, references, samples, figures, people or form answers.
- **The fields.**
  `{"gerbildocs":"style", "version":1, "exportedAt", "exportedBy"?, "name",
  "description"?, "kind":"publication"|"report"|"grant", "template",
  "citationStyle"?, "grantFormat"?}`.
  `template` is the layout: `label, style` (citation shape), `citation,
  abstractLimit, abstractMin, keywordsMin, keywordsMax, sections, statements,
  notes, graphics, headings, limits, figureWidths, experimental, source`,
  `format` (the whole resolved format — DEFAULT_FORMAT, the template and the
  Formatting-view changes merged — so the page looks the same whatever a later
  release's defaults are) and `page` (header and footer text, logo, page
  numbers). `citationStyle` is `{id, shipped:true}` for a style that ships with
  the app — its key only — or `{id, shipped:false, label, base, abstractLimit,
  doi, source}` for one the user made. `grantFormat` is `{note, source, parts,
  refs, form}`: parts as `{l, mode, words, pages, extraPages, headings,
  guidance, showTitle, limits}` without their keys; `refs` as `{mode, part,
  style}` where `part` is the printing part's name and `style` a citation style
  written as above; `form` the questions of the form, never the answers.
- **Versions.** `version` is the format's major version, an integer. A file
  with a higher one is refused, naming both versions ("written by a newer
  GerbilDocs, in version 2…; this copy reads version 1"). Within a major
  version fields are only added, so a reader ignores what it does not know —
  and the preview lists what it left out. A fractional `1.4` reads as 1.
- **The file is untrusted.** It is read through a whitelist of keys and types;
  numbers are clamped (font sizes 3–96 pt, margins 0–100 mm, word limits
  1–100,000, pages 1–500…), strings and lists capped, and anything that ends up
  inside an attribute or a style — a font name, a colour, a heading mark, a
  form question's key, a theme's code, a style's id — is held to a pattern.
  A template's id never comes from the file. A logo must be an embedded PNG, JPEG, GIF or
  WebP data URL: one that is not an image at all (`javascript:`, a link) gets
  the whole file refused; an image of another kind (SVG can carry scripts) or
  over ~500 KB is left out and the preview says so. The file is 3 MB at most.
  Every string is drawn through `esc`. A malformed or refused file shows why
  and changes nothing; an accepted one changes nothing until the preview is
  confirmed, and the import is one Undo.
- **Export goes through the same reader,** so what is written is exactly what
  an import accepts: an SVG logo is dropped at export, with a warning, rather
  than producing a file a colleague cannot use.
- **Citation styles are never overwritten.** A shipped one is named by key and
  put back only if the library has lost it. A user-made one already present
  under its id with the same shape (or, shape for shape, under another id) is
  reused; otherwise it is added, under a new id if its own is taken. The
  imported template records the style as `styleId`, and Use, the layout picker
  and a new grant take that style, falling back to the first of the template's
  shape, which is what they always did.
- **A grant format rides on its template.** An imported grant becomes a user
  template of kind `grant` carrying `grantFormat`; nothing was added to
  `LIBRARY_KEYS`. `grantFormatById` finds these after the built-in presets, so
  the New document dialog and the Application parts picker offer them, under
  "Mine", and `applyGrantFormat` applies them exactly as a preset — the layout
  is the template itself, and taking one on an existing grant goes through the
  same confirmation. Parts carry no keys and match by name.
- **Same name, your choice.** A file named like one of My templates is
  imported as a copy ("Name (2)") or replaces it, keeping its id so documents
  that use it follow. "Use it for this document now" is offered when the kind
  matches: a layout switches as Templates' Use does; a grant format opens the
  usual Application parts confirmation.
- **Desktop.** Export saves through `saveFile`, which writes into the root of
  the document's folder, as the response to reviewers and the deposit zip
  already are; the toast names the folder. Import needs no route of its own:
  the page saves its whole state, the vault splits `templates` and `styleLib`
  into the library (each replaced whole) and mirrors them to
  `library/*.json`, and the next document is given them.
- **Names are data, never keys into our own tables** (after review). A font,
  a page size or a form question's key named like an Object member
  ("constructor") used to find Object's own and break rendering for good. Fonts
  and sizes are looked up as own keys; a form's answers are read as the
  document's own; the reader refuses such names; and `migrate()` drops a font
  it cannot draw from the document and every template (`repairLayouts`), so a
  page an earlier build broke opens again. A typed font name is quoted and
  escaped by `fontCSS`, so a stray apostrophe cannot swallow the style after
  it; the reader takes quotes off. `#rgb` colours are written `#rrggbb`, which
  Word and the colour picker need.
- **A layout fits its page, everywhere.** `docFormat()` shrinks margins in
  proportion until at least 20 mm of text width and height remain, and narrows
  the column gap (then the column count) until a column is at least 15 mm. A
  layout that fits is untouched; one that did not used to give Word negative
  picture sizes. The reader fits a file's format the same way and says so.
- **Deleting a template leaves documents standing.** When the open document
  is laid out with it (or was made from its grant format), it keeps a copy,
  `keptLayout` — document-scoped, so its pages, page furniture and form
  questions do not change and the layout picker lists it as kept. In the vault,
  another document laid out with it falls back to the default format with its
  own changes, keeps the id (should the template come back) and says so when
  opened. Deleting asks first whenever anything could change: in the desktop
  edition always, standalone when the open document uses it.
- **The browser edition says when it cannot save.** An import writes the
  state with ~200,000 characters of headroom before it is committed and is
  refused, with nothing changed, when that does not fit; a save that fails
  opens a dialog once a session instead of failing in silence. The desktop
  edition saves to the vault and neither applies.
- **A derived layout is a layout.** Copying a template, "Make my own" and
  "Save as template" drop a grant format, import provenance and description;
  "Save as template" records the document's citation style as `styleId`.

## A citation style can be the journal's own file (28 September 2026)

- **Two formats, one library.** **Import style…** in the Style library (and
  the References view's upload, and the last entry of the citation picker)
  takes a CSL style (`.csl`, the ~10,000 journal styles at zotero.org/styles
  and in the CSL repository), a BibTeX style (`.bst`, the one a journal's
  LaTeX template ships with) or an EndNote `.ens` as before. An imported style
  is a `styleLib` entry like any other — no new library key:
  `{id, label, base:"csl"|"bst", csl|bst:<source>, cslMeta:{title, short,
  format, parent}, source:"imported from <file>", abstractLimit, lastUsed}`.
  The picker and the library tag it CSL or BibTeX.
- **CSL runs on our own processor.** A CSL 1.0.2 processor written for
  GerbilDocs (MIT) sits in its own `<script>` block ("CSL PROCESSOR"). It
  reads no document state; it formats what it is given. citeproc-js was not
  bundled: its CPAL/AGPL licence does not fit an MIT app. It was tested
  against citeproc-js, as a test-only reference, over 30 references of all
  twelve types: bibliography entries and citation clusters match (text and
  markup) for ACS, RSC, APA, Nature, IEEE, Vancouver, Harvard Cite Them Right,
  Chicago author-date, Elsevier with titles, APS and Springer basic; every
  entry and 558 of 560 citations for 28 more common styles; and 94.8 % of
  entries and 98.1 % of citations across a random 150 styles from the
  repository. It does not track notes (ibid.,
  near-note): GerbilDocs has no footnotes, so a note style's citations print
  in the text, and the import says so. Terms are English (en-US and en-GB);
  a style in another language prints English terms, and the import says so.
- **BibTeX runs on bst.js**, its own block immediately before the style
  profiles, through four functions: `bstParse`, `bstRun`, `bstLatexToHTML`,
  `refToBibtex`. The page uses nothing else, so the engine is replaceable.
  Its HTML is reduced to `<i> <b> <u> <sup> <sub> <span class="sc">` before it
  reaches the page. In text a BibTeX style prints `[n]`, `[DR20]` for alpha
  labels, or `(Doe et al., 2020)` from natbib's labels.
- **A dependent style keeps its own name and borrows its parent's layout.**
  ACS Catalysis names `american-chemical-society` and has no layout. When
  the parent is in the library (imported now or later, matched by its id) it
  renders from it; until then it uses the nearest built-in shape
  (american-chemical-society → ACS, royal-society-of-chemistry → RSC, apa,
  nature, elsevier-* → Elsevier, ieee, vancouver, american-physics-society →
  APS, harvard-* → Harvard, springer-basic → Springer; an unknown parent →
  Vancouver when numeric, Harvard otherwise) and says so, with a button to
  import the parent. Resolution happens at render time, so importing or
  removing a parent changes its dependents at once.
- **Order and numbering follow the reference list's style.** When the list's
  style sorts (a CSL `<bibliography><sort>`, a `.bst` that SORTs), the list is
  in the style's order and, for numbered styles, citation numbers follow it —
  acm numbers alphabetically, as LaTeX does. Otherwise numbers stay in order
  of first citation. This is one hook, at the end of `citeScan`, so the
  galley, page preview, Word, plain text, grant word counts, "Copy for the
  form" and the deposit's `cited.ris` all agree; a grant's two reference modes
  are unchanged in kind. Built-in styles never sort, and every output under
  them is byte-for-byte what it was (checked for the galley, pages, plain
  text and Word `document.xml` under nine built-in styles and a grant in both
  modes).
- **The printed forms come from the style.** In-text citations come from the
  CSL `<citation>` layout (superscript, brackets, author–date with year
  suffixes and collapsed ranges); the token system is unchanged. The list is
  set as the style sets it: its own numbers or labels in a margin column
  (second-field-align), or a hanging indent. Word gets the same: a tab and a
  hanging indent, `<w:smallCaps/>` for small caps, superscript runs.
- **An imported style is untrusted.** Parsed with DOMParser as XML, never as
  HTML; a DOCTYPE or ENTITY is refused before parsing (no entity expansion,
  no external fetch); 300 KB at most; nesting and element counts bounded;
  every string escaped on output; formatting read through fixed tables. A
  file that fails is refused with its reason and line number and nothing is
  added. The preview shows the name, kind, citation format, parent status and
  three sample references before anything changes; adding is one Undo.
- **A style cannot hang the page or reach Object.prototype** (after review).
  A 2.5 KB style whose macros each call the next twice, thirty levels deep,
  never finished, and because the library is app-scoped it hung every
  reload and the Style library too. Now, before a style runs:
  - macros that call each other in a loop are refused;
  - each layout's size with every macro written out in full (a `<choose>`
    counted as its dearest branch) must be under 100,000 elements. All 2,863
    independent styles in the CSL repository pass; the largest comes to
    3,047.
  While it runs, every element visited is spent from a budget per operation
  (500,000 plus 50,000 per work; real styles use under 1,400 per work) and
  per task (5,000,000; a 254-reference, 400-citation document uses about
  150,000). Past either, the operation stops, the style is set in a built-in
  shape for the session and says why, and the page redraws; an import that
  trips it is refused. On load, a stored style that fails today's checks
  (let in by an earlier build) is set aside to its built-in shape before
  anything renders, and each Style library row is drawn on its own, so one
  bad style never takes the view or its Remove button with it. A
  `.gerbilstyle` is read by the same checks.
  A style names terms, forms, macros, variables and date parts, and those
  names never key an object with a prototype: term tables, macros, date-part
  overrides and every element's attributes have none; a term's form must be
  one CSL defines; a variable is read only as the item's own. A
  `form="__proto__"` once wrote onto Object.prototype from the import
  preview, and every `fetch` in the page failed after it.
- **A style file carries the source.** A `.gerbilstyle` whose template uses an
  imported style carries `csl` or `bst` with it (and `cslParent`, the parent's
  source, for a dependent style whose parent is in the library). The reader
  holds them to the import's rules — a DOCTYPE refuses the file, anything
  else that fails leaves the style out with a warning — and re-reads
  `cslMeta` from the source rather than trusting the file. `template.style`
  may be `csl` or `bst`. A style is matched by its source as well as its
  label and shape, so the same CSL is not added twice.
- **The undo history holds each style's source once**, as it holds images,
  not once per step.
