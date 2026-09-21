# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec. Built by packaging/build.py."""
from pathlib import Path

ROOT = Path(SPECPATH).parent          # noqa: F821 - SPECPATH is injected
APP_NAME = "GerbilDocs"

datas = [(str(ROOT / "app" / "static"), "static")]

a = Analysis(                          # noqa: F821
    [str(ROOT / "desktop" / "launch.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PIL"],
    noarchive=False,
)
pyz = PYZ(a.pure)                      # noqa: F821

exe = EXE(                             # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False, strip=False, upx=False,
    console=False,                     # no console window
    icon=str(ROOT / "packaging" / "app.ico") if (ROOT / "packaging" / "app.ico").exists() else None,
)
coll = COLLECT(                        # noqa: F821
    exe, a.binaries, a.datas,
    strip=False, upx=False, name=APP_NAME,
)
