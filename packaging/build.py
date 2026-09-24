"""Build a distributable application.

    python packaging/build.py                 # onedir bundle in dist/
    python packaging/build.py --installer     # and run Inno Setup over it (Windows)
    python packaging/build.py --zip           # and zip the onedir bundle (portable copy)
    python packaging/build.py --fetch-mathjax # fetch the MathJax bundle first if missing

onedir rather than onefile: it starts noticeably faster, which matters for
something opened dozens of times a day, and it keeps the interface readable on
disk for anyone who wants to look.

This script only orchestrates; it checks its inputs before starting and its
outputs after, and exits non-zero the moment something is not where it should
be. The Windows build itself happens on Windows — locally, or in the GitHub
Actions workflow in `.github/workflows/build.yml`, which is the reference way
to produce the installer.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
NAME = "GerbilDocs"
SPEC = ROOT / "packaging" / "document-desk.spec"
ISS = ROOT / "packaging" / "installer.iss"
MATHJAX = ROOT / "app" / "static" / "vendor" / "mathjax" / "tex-svg-full.js"


def version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def fail(msg: str) -> int:
    print(f"\nbuild failed: {msg}", file=sys.stderr)
    return 1


def find_iscc() -> Path | None:
    for candidate in (
        os.environ.get("ISCC"),
        shutil.which("ISCC"),
        shutil.which("iscc"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"),
    ):
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def bundle_dir() -> Path:
    return DIST / NAME


def bundle_exe() -> Path:
    return bundle_dir() / (NAME + (".exe" if sys.platform.startswith("win") else ""))


def bundled_index() -> Path | None:
    # PyInstaller 6 puts data under _internal/; older versions beside the exe.
    for rel in ("_internal/static/index.html", "static/index.html"):
        p = bundle_dir() / rel
        if p.exists():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--installer", action="store_true", help="also run Inno Setup (Windows)")
    ap.add_argument("--zip", action="store_true", help="also zip the onedir bundle")
    ap.add_argument("--clean", action="store_true", help="remove build/ and dist/ first")
    ap.add_argument("--fetch-mathjax", action="store_true",
                    help="fetch the MathJax bundle first if it is missing (needs network)")
    ap.add_argument("--allow-missing-mathjax", action="store_true",
                    help="build even though MathJax is not bundled (equations need a network)")
    args = ap.parse_args()

    ver = version()
    print(f"{NAME} {ver} — Python {sys.version.split()[0]} on {sys.platform}\n")

    # ---- inputs ----------------------------------------------------------
    if sys.version_info < (3, 11):
        return fail("Python 3.11 or newer is required")
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        return fail("PyInstaller is not installed: pip install -r requirements.txt")
    for required in (SPEC, ISS, ROOT / "app" / "static" / "index.html",
                     ROOT / "desktop" / "launch.py"):
        if not required.exists():
            return fail(f"missing {required.relative_to(ROOT)}")
    if not sys.platform.startswith("win"):
        print("note: not on Windows — this produces a bundle for THIS platform, not a .exe.\n"
              "      The Windows build runs in .github/workflows/build.yml.\n")

    if not MATHJAX.exists() and args.fetch_mathjax:
        rc = subprocess.call([sys.executable, str(ROOT / "tools" / "fetch_mathjax.py")], cwd=ROOT)
        if rc != 0:
            print("MathJax could not be fetched.", file=sys.stderr)
    if MATHJAX.exists():
        print(f"MathJax bundled: {MATHJAX.stat().st_size:,} bytes (included via app/static)")
    elif args.allow_missing_mathjax:
        print("note: MathJax is not bundled — equations will need a network connection\n"
              "      unless the MathML fallback is acceptable.\n")
    else:
        return fail("MathJax is not bundled. Run tools/fetch_mathjax.py, pass --fetch-mathjax,\n"
                    "or pass --allow-missing-mathjax to build a network-dependent copy.")

    if args.clean:
        for d in (ROOT / "build", DIST):
            shutil.rmtree(d, ignore_errors=True)

    # ---- PyInstaller -----------------------------------------------------
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm",
           "--distpath", str(DIST), "--workpath", str(ROOT / "build")]
    print(" ".join(cmd))
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc != 0:
        return fail(f"PyInstaller exited with {rc}")

    # ---- outputs ---------------------------------------------------------
    exe = bundle_exe()
    if not exe.exists():
        return fail(f"expected executable not found: {exe}")
    idx = bundled_index()
    if idx is None:
        return fail("index.html is not inside the bundle — check `datas` in the spec")
    if MATHJAX.exists() and not (idx.parent / "vendor" / "mathjax" / MATHJAX.name).exists():
        return fail("MathJax is on disk but did not make it into the bundle")
    print(f"\nbundle: {bundle_dir()}\n  {exe.name}  {exe.stat().st_size:,} bytes"
          f"\n  {idx.relative_to(bundle_dir())}")

    if args.zip:
        out = DIST / f"GerbilDocs-{ver}-{sys.platform}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for p in bundle_dir().rglob("*"):
                if p.is_file():
                    z.write(p, Path(NAME) / p.relative_to(bundle_dir()))
        print(f"zip:    {out}  {out.stat().st_size:,} bytes")

    if args.installer:
        if not sys.platform.startswith("win"):
            return fail("--installer needs Windows and Inno Setup")
        iscc = find_iscc()
        if iscc is None:
            return fail("Inno Setup (ISCC.exe) not found. Install it, or set ISCC=<path>.")
        out_dir = DIST / "installer"
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [str(iscc), f"/DAppVersion={ver}", f"/O{out_dir}", str(ISS)]
        print(" ".join(cmd))
        rc = subprocess.call(cmd, cwd=ROOT)
        if rc != 0:
            return fail(f"ISCC exited with {rc}")
        setup = out_dir / f"GerbilDocs-{ver}-setup.exe"
        if not setup.exists():
            return fail(f"installer not found where expected: {setup}")
        print(f"\ninstaller: {setup}  {setup.stat().st_size:,} bytes")

    print("\nUnsigned builds trip SmartScreen on other people's machines — budget for a\n"
          "code-signing certificate before this goes out widely.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
