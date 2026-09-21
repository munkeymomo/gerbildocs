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
- References are formatted by four hand-written style functions in the
  interface, not by citeproc over CSL. Replacing them is a known piece of work.
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
