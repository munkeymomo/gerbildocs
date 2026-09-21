"""Derive the standalone page from `app/static/index.html`.

    python tools/make_standalone.py                    # -> dist/GerbilDocs.html
    python tools/make_standalone.py --artifact out.html  # body-only, for the artifact wrapper

`app/static/index.html` is the source of truth for the interface. Everything
the desktop edition adds is gated on the bridge being connected, so the same
file opened directly is the standalone edition. This script produces the two
other forms that are wanted:

- the **standalone file** to send to someone: identical to index.html (it
  already works opened directly); copied so the name is right.
- the **artifact source**: the artifact wrapper supplies doctype, head and
  body, so it must not contain them. This strips the document wrapper and
  keeps everything from `<title>` onward.

It asserts on the fragments it removes, so if the wrapper ever changes it
fails rather than shipping a half-stripped page.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "app" / "static" / "index.html"

HEAD_END = "</head>\n<body>\n"
TAIL = "</body>\n</html>\n"


def artifact_source(html: str) -> str:
    assert html.startswith("<!doctype html>"), "index.html no longer starts with the doctype"
    cut = html.index(HEAD_END) + len(HEAD_END)
    body = html[cut:]
    assert body.startswith("<title>"), "expected <title> right after <body>"
    assert body.endswith(TAIL), "index.html no longer ends with </body></html>"
    return body[: -len(TAIL)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", metavar="OUT", help="write the body-only artifact source here")
    ap.add_argument("--standalone", metavar="OUT",
                    default=str(ROOT / "dist" / "GerbilDocs.html"))
    args = ap.parse_args(argv)

    html = SRC.read_text(encoding="utf-8")
    out = Path(args.standalone)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"standalone: {out} ({len(html):,} chars)")
    if args.artifact:
        body = artifact_source(html)
        Path(args.artifact).write_text(body, encoding="utf-8")
        print(f"artifact:   {args.artifact} ({len(body):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
