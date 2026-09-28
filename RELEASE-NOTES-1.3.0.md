# GerbilDocs 1.3.0

Stack plots for spectra, and grant applications built the way funders
actually ask for them.

## What's new

**Stack plots.** A plot is now made of datasets, and one dataset can hold
several columns: a spectrum with its envelope and fitted components is one
dataset. Overlay them or stack them with an offset you set as a percentage.
Normalise to the maximum, to 0–1 or to unit area, per dataset, so the
components stay in proportion to the data they were fitted to. Scale any
dataset and show the factor on the plot as "×5".

**Add / edit data** is now a dataset manager: datasets down the left, the
familiar paste-from-Excel grid on the right. Link a dataset to a sample and
its label on the plot follows the sample. Rename the sample once and every
plot changes.

**Labels, error bars and annotations.** Dataset names can sit above or below
each trace, at the left or right. Error bars can be a percentage, a fixed
amount, or your own values in their own grid. Text, arrows, boxes, marker
lines and shaded bands are drawn on the plot with the mouse.

**Combined charts.** Each dataset can be a line, points, bars or a filled
area, on the left or a second right-hand axis, and each axis has its own
limits.

**Common column identities.** Style a column once across every dataset: raw
data in black, the envelope in red, a component in green with a gradient
fill. The legend then lists the columns rather than every trace.

**Colour.** Eight palettes, including colour-blind safe and greyscale, plus a
full colour picker on every colour control.

**Grant applications.** A grant is now the parts the funder asks for, each
with its own word or page limit, headings and guidance, and a status table
showing how far each part is from its limit. There are ready-made formats for
the EPSRC standard research grant and the EPSRC New Investigator Award on the
UKRI Funding Service, or you can build your own. The title, authors and
abstract stay out of the parts, because the funder's form asks for them
separately. References are either one list in their own part, numbered across
the application, or one list per part. A new compact reference style keeps
the list inside tight word limits. Text-box parts copy out as plain text,
ready to paste into the form.

## Files

- `GerbilDocs-1.3.0-win32.zip`: the portable Windows application. Unzip and
  run `GerbilDocs.exe`.
- `GerbilDocs-1.3.0-standalone.html`: a single-file browser version, with
  nothing to install.
- `gerbildocs-1.3.0-src.zip`: the source code, MIT licensed.

## Known limitations

- Funders change their limits. Check the call document before you rely on a
  preset.
- Page counts come from the app's own pagination, and Word may break pages
  slightly differently.
- Annotations are placed against the x axis and the left y axis.
- The Windows build isn't code-signed, so SmartScreen will warn on first run.
  Choose "More info", then "Run anyway".
- Only Windows is built and tested.
