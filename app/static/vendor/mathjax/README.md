# MathJax, bundled locally

The interface renders equations with MathJax's SVG output. The desktop edition
should not depend on a CDN, so the bundle lives here:

    python tools/fetch_mathjax.py

That fetches `tex-svg-full.js` (MathJax 3.2.2, ~2.3 MB) — the *full* TeX
component, which carries `mhchem` for `\ce{}` chemistry inside the one file.
The smaller `tex-svg.js` loads mhchem on demand from a path relative to itself,
which is a second file to bundle and a second thing to get wrong.
`VERSION.json` records what was fetched and its SHA-256.

`index.html` tries this file first and falls back to the CDN if it is missing,
so a checkout without it still works — online. `packaging/build.py` warns when
it is absent and `--fetch-mathjax` fetches it; the CI workflow always fetches
it before building. Both `.js` files are gitignored.

Without either, equations use the interface's built-in LaTeX-to-MathML
converter, which every current browser renders natively. That covers
fractions, sub- and superscripts, roots, sums, integrals, Greek and upright
text; it does not cover mhchem or aligned environments.
