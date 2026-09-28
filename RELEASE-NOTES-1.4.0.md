# GerbilDocs 1.4.0

GerbilDocs is a free desktop app for writing scientific papers, reports and
grant applications. You define samples, figures, tables, equations and
references once. The text refers to them by reference, so every number,
code and citation stays right as the document changes.

## New since 1.2

**Stack plots.** A plot is now built from datasets, and one dataset can hold
several columns, such as a spectrum with its envelope and fitted components.
Datasets can be overlaid or stacked, with the offset set as a percentage.
Normalising is per dataset, so fitted components stay in proportion to the
data. Any dataset can be scaled, with the factor shown on the plot as "×5".

**Plot extras.** Plots can also have:

- dataset labels on the traces, linked to your samples;
- error bars;
- combined bar and line charts, with a second y axis;
- shapes and annotations drawn with the mouse;
- one style per column across every dataset;
- eight palettes and a full colour picker.

**Grant applications, the way funders ask for them.** A grant is now the
parts the funder asks for. Each part has its own word or page limit,
headings and guidance, and a status table shows how close each part is to
its limit. Ready-made formats cover the EPSRC standard research grant and
the EPSRC New Investigator Award on the UKRI Funding Service, or you can
build your own.

The title, authors and abstract stay out of the parts, because the funder's
form asks for them separately. References are either one list in their own
part or one list per part, and a compact reference style keeps them inside
tight word limits. Text-box parts copy out as plain text, ready to paste
into the form.

**Style files.** A layout, or a grant's whole structure, can be saved as a
`.gerbilstyle` file. A colleague can import it into their library in one
step.

**Journal styles, exactly.** Import a journal's own CSL style (from
zotero.org/styles) or a BibTeX `.bst` file. Citations, the order of the
reference list and its numbering then follow that style, in the page, in Word
and in word counts.

**Plots straight from your samples.** Plot against a sample property — Fe
at.%, say — or by sample code, with values that stay live: rename a sample or
change a property and the plot follows. Sample properties can carry an
uncertainty (± SD), which tables print and plots draw as error bars.

**References in captions.** Every caption takes `@` references and has a
Reference… button, the same as paragraphs.

**Figures print complete.** A plot placed in a figure now carries its
axis titles, legend and labels, drawn at the width it will print at, so the
plot type size you set is the size on the page.

**Gantt charts** now label months at a readable spacing, even for five-year
projects.

## Files

- `GerbilDocs-1.4.0-win32.zip`: the portable Windows application. Unzip it
  anywhere and run `GerbilDocs.exe`. It starts empty. Your documents are
  kept in `Documents\GerbilDocs` and your library in your user profile,
  never in the application folder.
- `GerbilDocs-1.4.0-standalone.html`: a single-file browser version with
  nothing to install. It opens on an invented example document.
- `gerbildocs-1.4.0-src.zip`: the source code, MIT licensed.

## Known limitations

- Funders change their limits, so check the call document before relying
  on a preset.
- Page counts come from the app's own pagination, and Word may break pages
  slightly differently.
- The Windows build isn't code-signed, so SmartScreen warns on the first
  run. Choose "More info", then "Run anyway".
- Only Windows is built and tested.
