# tools

`make_standalone.py` — **the interface's source of truth is
`app/static/index.html`.** Everything the desktop edition adds is gated on the
bridge being connected, so the same file opened directly is the standalone
edition. This script copies it out under the distribution name and, with
`--artifact`, strips the document wrapper (doctype, head, body) to produce the
source for the artifact page, which supplies its own. It asserts on what it
removes.

    python tools/make_standalone.py --artifact ../artifact.html

`fetch_mathjax.py` — fetches the MathJax bundle into
`app/static/vendor/mathjax/` so the desktop edition renders equations with no
network. Standard library only. See the README there.

`apply_desktop_bridge.py` — **historical.** It patched the bridge *into* the
standalone page when the artifact was the source of truth. The direction is now
the other way (index.html → artifact) and the bridge it inserts is the old one,
so do not run it. Kept for the record of how the first bridge was applied.
