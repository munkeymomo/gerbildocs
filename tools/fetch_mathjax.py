"""Fetch the MathJax bundle so the desktop edition has no network dependency.

    python tools/fetch_mathjax.py            # into app/static/vendor/mathjax/
    python tools/fetch_mathjax.py --check    # exit 0 if it is already there

Standard library only, so it runs from a bare checkout. It takes the *full*
TeX-to-SVG component, `tex-svg-full.js`, not `tex-svg.js`: the smaller one
loads `mhchem` (the `\\ce{}` chemistry macros) on demand from a path relative
to itself, which means a second file and a second thing to get wrong. The full
one carries every TeX extension in a single file (~2.3 MB) and needs nothing
else.

The page prefers this file and falls back to the CDN when it is missing, so a
checkout without it still works — online.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST_DIR = ROOT / "app" / "static" / "vendor" / "mathjax"
FILENAME = "tex-svg-full.js"
VERSION = "3.2.2"

SOURCES = [
    "https://cdnjs.cloudflare.com/ajax/libs/mathjax/{v}/es5/{f}",
    "https://cdn.jsdelivr.net/npm/mathjax@{v}/es5/{f}",
]
MIN_BYTES = 1_500_000  # the full component is well over 2 MB; anything smaller is an error page


def looks_like_mathjax(data: bytes) -> str | None:
    """A reason it is wrong, or None if it looks right."""
    if len(data) < MIN_BYTES:
        return f"only {len(data)} bytes — expected a file over {MIN_BYTES}"
    head = data[:4096].lower()
    if b"<html" in head or b"<!doctype" in head:
        return "got an HTML page, not a script"
    if b"mathjax" not in data[:200_000].lower():
        return "the file does not mention MathJax"
    if b"mhchem" not in data:
        return "no mhchem in the bundle — this is not the full component"
    return None


def fetch(version: str, filename: str, timeout: float = 120.0) -> tuple[bytes, str]:
    last: Exception | None = None
    for template in SOURCES:
        url = template.format(v=version, f=filename)
        print(f"  fetching {url}")
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "GerbilDocs/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
        except (urllib.error.URLError, OSError) as exc:
            print(f"    failed: {exc}")
            last = exc
            continue
        problem = looks_like_mathjax(data)
        if problem:
            print(f"    rejected: {problem}")
            last = RuntimeError(problem)
            continue
        return data, url
    raise RuntimeError(f"could not fetch {filename} {version} from any source: {last}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--version", default=VERSION)
    ap.add_argument("--dest", default=str(DEST_DIR))
    ap.add_argument("--check", action="store_true",
                    help="only report whether the bundle is present")
    ap.add_argument("--force", action="store_true", help="fetch even if it is already there")
    args = ap.parse_args(argv)

    dest_dir = Path(args.dest)
    target = dest_dir / FILENAME
    if args.check:
        if target.exists() and looks_like_mathjax(target.read_bytes()) is None:
            print(f"MathJax is bundled: {target} ({target.stat().st_size:,} bytes)")
            return 0
        print(f"MathJax is NOT bundled at {target}")
        return 1
    if target.exists() and not args.force:
        problem = looks_like_mathjax(target.read_bytes())
        if problem is None:
            print(f"already present: {target} — use --force to refetch")
            return 0
        print(f"present but wrong ({problem}); refetching")

    print(f"MathJax {args.version} -> {target}")
    try:
        data, url = fetch(args.version, FILENAME)
    except RuntimeError as exc:
        print(f"\n{exc}\nNo network here? Run this on a machine with one; the page falls back "
              "to the CDN meanwhile.", file=sys.stderr)
        return 1
    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".js.part")
    tmp.write_bytes(data)
    tmp.replace(target)
    digest = hashlib.sha256(data).hexdigest()
    (dest_dir / "VERSION.json").write_text(json.dumps({
        "file": FILENAME, "version": args.version, "source": url,
        "sha256": digest, "bytes": len(data),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"  {len(data):,} bytes, sha256 {digest[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
