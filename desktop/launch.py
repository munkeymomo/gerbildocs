"""Launcher for the desktop edition.

Starts the backend on loopback at a port the OS picks, mints a token for this
launch only, and opens a native window on it (ADR-W01). There is no port to
configure and no browser to install: on Windows the window is EdgeWebView2,
which ships with Windows 10 and 11.

`--browser` opens the user's default browser instead, which is how you develop
and how you check something when a webview misbehaves. If the native window
cannot start at all, the launcher falls back to the browser by itself rather
than stopping with a traceback.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings  # noqa: E402

WINDOW_TITLE = "GerbilDocs"


def free_port(host: str = "127.0.0.1") -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def wait_until_up(host: str, port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(0.25)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    return False


def _route_output_to_log(logs_dir: Path) -> None:
    """A windowed PyInstaller build has no console: sys.stdout and sys.stderr
    are None, and anything that logs would fail quietly. Send them to a file."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        log = open(logs_dir / "desk.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        if sys.stdout is None:
            sys.stdout = log
        if sys.stderr is None:
            sys.stderr = log
    except OSError:
        pass


def trust_own_dlls() -> int:
    """Clear the "downloaded from the internet" tag from the bundle's own DLLs.

    Unzipping a downloaded zip with Explorer tags every file it writes with an
    NTFS stream named Zone.Identifier. .NET Framework refuses to load a tagged
    file as an assembly, and the native window runs on .NET (pythonnet, Windows
    Forms, WebView2), so a portable copy unzipped from a download stopped at
    start-up with "Failed to resolve Python.Runtime.Loader.Initialize". This
    does for our own DLLs what right-click > Properties > Unblock does.

    Only a frozen Windows build, only files inside its own bundle, and every
    failure is ignored: an installed copy carries no tags, and may sit where
    it cannot be written to. Returns how many tags it cleared.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return 0
    bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    cleared = 0
    for dll in bundle.rglob("*.dll"):
        try:
            os.remove(f"{dll}:Zone.Identifier")
            cleared += 1
        except OSError:
            pass
    return cleared


def check_window() -> int:
    """Load everything the native window needs, open nothing, and report.

    The build runs this against its portable zip after tagging every file the
    way a browser download and Explorer do, so a release that would fail on
    someone else's PC fails the build instead. Exit status 0 means it loads.
    """
    cleared = trust_own_dlls()
    try:
        import webview.platforms.winforms  # noqa: F401 - pythonnet, WinForms, WebView2
    except Exception:  # noqa: BLE001 - any failure here is the answer
        traceback.print_exc()
        print(f"window runtime failed to load ({cleared} tags cleared)", file=sys.stderr)
        return 1
    print(f"window runtime loads ({cleared} tags cleared)")
    return 0


def browser_fallback(url: str, logs_dir: Path) -> None:
    """The native window could not start. The backend is already up, so open
    the same page in the default browser, and give the person a way to quit:
    on Windows, a message box that closes GerbilDocs when it is dismissed."""
    print("the native window did not start; opening the browser instead", file=sys.stderr)
    webbrowser.open(url)
    if sys.platform != "win32":
        threading.Event().wait()
        return
    try:
        import ctypes

        mb_ok, mb_iconinformation, mb_setforeground = 0x0, 0x40, 0x10000
        ctypes.windll.user32.MessageBoxW(
            None,
            "GerbilDocs couldn't open its own window, so it has opened in your "
            "web browser instead.\n\n"
            "Keep this box open while you work. Click OK to close GerbilDocs.\n\n"
            f"What went wrong is recorded in {logs_dir / 'desk.log'}",
            WINDOW_TITLE,
            mb_ok | mb_iconinformation | mb_setforeground,
        )
    except Exception:  # noqa: BLE001 - no message box: keep serving until stopped
        traceback.print_exc()
        threading.Event().wait()


def serve(app, host: str, port: int) -> threading.Thread:
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning",
                            access_log=False, lifespan="on")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="desk-backend", daemon=True)
    thread.start()
    return thread


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=WINDOW_TITLE)
    parser.add_argument("--browser", action="store_true",
                        help="open in the default browser instead of a native window")
    parser.add_argument("--port", type=int, default=0, help="fix the port (default: pick a free one)")
    parser.add_argument("--data-dir", default=None, help="override the application data folder")
    parser.add_argument("--no-open", action="store_true", help="serve only; open nothing")
    parser.add_argument("--check-window", action="store_true",
                        help="load the native window's runtime, open nothing, and exit "
                             "(0 if it loads); the build's download check")
    args = parser.parse_args(argv)

    settings = load_settings(Path(args.data_dir) if args.data_dir else None)
    settings.port = args.port or free_port(settings.host)
    _route_output_to_log(settings.paths.logs)

    if args.check_window:
        return check_window()

    from app.api import create_app
    app = create_app(settings)

    serve(app, settings.host, settings.port)
    if not wait_until_up(settings.host, settings.port):
        print("backend did not start", file=sys.stderr)
        return 1

    url = f"http://{settings.host}:{settings.port}/?t={settings.token}"
    print(f"{WINDOW_TITLE} on {url}")
    print(f"  library   {settings.paths.root}")
    print(f"  documents {settings.paths.documents}")

    if args.no_open:
        threading.Event().wait()
        return 0

    if args.browser:
        webbrowser.open(url)
        threading.Event().wait()
        return 0

    trust_own_dlls()
    try:
        import webview  # pywebview
    except ImportError:
        print("pywebview is not installed; opening the browser instead", file=sys.stderr)
        webbrowser.open(url)
        threading.Event().wait()
        return 0

    try:
        window = webview.create_window(WINDOW_TITLE, url, width=1440, height=920,
                                       min_size=(900, 620), confirm_close=False)
    except Exception:  # noqa: BLE001 - no window is not a reason to stop
        traceback.print_exc()
        browser_fallback(url, settings.paths.logs)
        return 0

    def pick_folder() -> str | None:
        """Native folder dialog for the interface's "Open an existing folder".
        Called on the backend thread while the window is up; pywebview's dialog
        is safe to call from a non-GUI thread once `start()` is running."""
        try:
            chosen = window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as exc:  # noqa: BLE001 - a failed dialog must not kill the request
            print(f"folder dialog failed: {exc}", file=sys.stderr)
            return None
        if not chosen:
            return None
        return str(chosen[0] if isinstance(chosen, (list, tuple)) else chosen)

    app.state.pick_folder = pick_folder
    try:
        webview.start()
    except Exception:  # noqa: BLE001 - a missing or blocked runtime: use the browser
        traceback.print_exc()
        app.state.pick_folder = None  # no window, so no native folder dialog
        browser_fallback(url, settings.paths.logs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
