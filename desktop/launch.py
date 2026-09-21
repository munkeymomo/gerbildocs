"""Launcher for the desktop edition.

Starts the backend on loopback at a port the OS picks, mints a token for this
launch only, and opens a native window on it (ADR-W01). There is no port to
configure and no browser to install: on Windows the window is EdgeWebView2,
which ships with Windows 10 and 11.

`--browser` opens the user's default browser instead, which is how you develop
and how you check something when a webview misbehaves.
"""

from __future__ import annotations

import argparse
import contextlib
import socket
import sys
import threading
import time
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
    args = parser.parse_args(argv)

    settings = load_settings(Path(args.data_dir) if args.data_dir else None)
    settings.port = args.port or free_port(settings.host)
    _route_output_to_log(settings.paths.logs)

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

    try:
        import webview  # pywebview
    except ImportError:
        print("pywebview is not installed; opening the browser instead", file=sys.stderr)
        webbrowser.open(url)
        threading.Event().wait()
        return 0

    window = webview.create_window(WINDOW_TITLE, url, width=1440, height=920,
                                   min_size=(900, 620), confirm_close=False)

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
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
