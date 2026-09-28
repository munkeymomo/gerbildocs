"""The desktop launcher's start-up guards (desktop/launch.py).

The real check is the build's: it tags a copy of the portable zip as
downloaded and runs `GerbilDocs.exe --check-window` on Windows. These tests pin
the logic that check depends on, on any platform.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def launch():
    spec = importlib.util.spec_from_file_location("gd_launch", ROOT / "desktop" / "launch.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _fake_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "_internal"
    (bundle / "pythonnet" / "runtime").mkdir(parents=True)
    (bundle / "webview" / "lib").mkdir(parents=True)
    for rel in ("python311.dll",
                "pythonnet/runtime/Python.Runtime.dll",
                "webview/lib/Microsoft.Web.WebView2.Core.dll",
                "base_library.zip"):
        (bundle / rel).write_bytes(b"x")
    return bundle


def test_unblock_does_nothing_outside_a_frozen_windows_build(launch, monkeypatch, tmp_path):
    removed: list[str] = []
    monkeypatch.setattr(launch.os, "remove", removed.append)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert launch.trust_own_dlls() == 0
    assert removed == []


def test_unblock_clears_the_tag_on_every_dll_in_the_bundle_only(launch, monkeypatch, tmp_path):
    bundle = _fake_bundle(tmp_path)
    removed: list[str] = []
    monkeypatch.setattr(launch.os, "remove", removed.append)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert launch.trust_own_dlls() == 3
    assert all(p.endswith(".dll:Zone.Identifier") for p in removed)
    assert {Path(p[: -len(":Zone.Identifier")]).name for p in removed} == {
        "python311.dll", "Python.Runtime.dll", "Microsoft.Web.WebView2.Core.dll"}
    assert all(p.startswith(str(bundle)) for p in removed)


def test_unblock_ignores_files_that_carry_no_tag_or_cannot_be_written(launch, monkeypatch, tmp_path):
    bundle = _fake_bundle(tmp_path)

    def refuse(path: str) -> None:
        if "Python.Runtime" in path:
            raise PermissionError(path)  # read-only install folder
        raise FileNotFoundError(path)    # no tag: the usual case for an installed copy

    monkeypatch.setattr(launch.os, "remove", refuse)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    assert launch.trust_own_dlls() == 0


def test_check_window_reports_a_runtime_that_does_not_load(launch, monkeypatch, capsys):
    import builtins

    real_import = builtins.__import__

    def no_winforms(name, *args, **kwargs):
        if name.startswith("webview"):
            raise RuntimeError("Failed to resolve Python.Runtime.Loader.Initialize")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_winforms)
    assert launch.check_window() == 1
    assert "window runtime failed to load" in capsys.readouterr().err
