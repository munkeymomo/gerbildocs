"""Assemble everything a public release needs, into `release/<version>/`.

    python tools/make_release.py                 # build everything
    python tools/make_release.py --skip-build    # reuse the existing dist/ bundle

It produces three files and a checksum list:

    GerbilDocs-<v>-win32.zip        the portable application (packaging/build.py)
    GerbilDocs-<v>-standalone.html  the single file that runs in a browser
    gerbildocs-<v>-src.zip          the source, MIT, no development scaffolding
    SHA256SUMS.txt                  one line per file

The source archive is NOT the working tree. `PRIVATE` below lists what is
deliberately left out: the development hand-off notes and agent prompts, which
carry machine names and home-directory paths that have no business in a public
download. Everything needed to build and run the application is in.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
RELEASE = ROOT / "release"

# Directories never walked, at any depth.
SKIP_DIRS = {
    ".git", ".venv", "venv", "dist", "build", "release",
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".idea", ".vscode",
}

# Files left out of the public source archive. The first three are development
# scaffolding written for whoever (or whatever) picks the work up next: they
# name the machine it was built on and the paths it was built in.
PRIVATE = {
    "HANDOFF.md",
    "CLAUDE.md",
    "docs/PROMPT-ui-upgrade.md",
}

# Fetched, not authored: 2 MB that `tools/fetch_mathjax.py` puts back.
GENERATED = {
    "app/static/vendor/mathjax/tex-svg-full.js",
    # Written beside it by the same script, and git-ignored for the same
    # reason. Keeping it out is what makes the archive and the public
    # repository identical file for file.
    "app/static/vendor/mathjax/VERSION.json",
}

SKIP_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log", ".sqlite", ".spec~"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "build-log.txt", "build-err.txt"}


def version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def run(*args: str) -> None:
    print("  $", " ".join(args))
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"failed: {' '.join(args)}")


def source_files() -> list[Path]:
    """Every file that belongs in the source archive, in a stable order."""
    out: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.as_posix() in PRIVATE or rel.as_posix() in GENERATED:
            continue
        if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES:
            continue
        out.append(path)
    return out


def write_source_zip(target: Path, ver: str) -> None:
    prefix = f"gerbildocs-{ver}"
    files = source_files()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            z.write(path, f"{prefix}/{path.relative_to(ROOT).as_posix()}")
    print(f"  {len(files)} files")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-build", action="store_true",
                    help="reuse the bundle already in dist/ instead of rebuilding")
    args = ap.parse_args()

    ver = version()
    out = RELEASE / ver
    out.mkdir(parents=True, exist_ok=True)
    print(f"GerbilDocs {ver} -> {out}\n")

    if not args.skip_build:
        print("portable application")
        run("packaging/build.py", "--clean", "--zip")
    built = DIST / f"GerbilDocs-{ver}-win32.zip"
    if not built.exists():
        raise SystemExit(f"missing {built} — run without --skip-build")

    print("\nassembling")
    portable = out / built.name
    portable.write_bytes(built.read_bytes())
    print(f"  {portable.name}")

    standalone = out / f"GerbilDocs-{ver}-standalone.html"
    run("tools/make_standalone.py", "--standalone", str(standalone))

    src = out / f"gerbildocs-{ver}-src.zip"
    print(f"  {src.name}")
    write_source_zip(src, ver)

    notes = ROOT / f"RELEASE-NOTES-{ver}.md"
    if notes.exists():
        (out / "README.md").write_text(notes.read_text(encoding="utf-8"), encoding="utf-8")
        print("  README.md (release notes)")

    sums = out / "SHA256SUMS.txt"
    lines = []
    for path in sorted(out.iterdir()):
        if path.name == sums.name:
            continue
        lines.append(f"{sha256(path)}  {path.name}")
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n{out}")
    for path in sorted(out.iterdir()):
        print(f"  {path.stat().st_size:>12,}  {path.name}")
    print("\nSource archive leaves out, on purpose:")
    for name in sorted(PRIVATE):
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
