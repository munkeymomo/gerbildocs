"""Show a folder in the operating system's file manager.

One function, one decision per platform. Nothing here takes a user-supplied
string: the route that calls it resolves a document id to the folder the vault
recorded, so the path is always one the application itself created or adopted.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

__all__ = ["reveal_command", "reveal"]


def reveal_command(path: Path, platform: str | None = None) -> list[str] | None:
    """The command that opens `path` in the file manager, or None on Windows,
    where `os.startfile` is used instead of a subprocess."""
    plat = platform or sys.platform
    if plat.startswith("win"):
        return None
    if plat == "darwin":
        return ["open", str(path)]
    return ["xdg-open", str(path)]


def reveal(path: Path, platform: str | None = None,
           run: Callable[[list[str]], object] | None = None) -> str:
    """Open the folder. Returns a short description of what was done.

    `run` is how the command is launched; the default detaches it so the file
    manager outlives the request. Tests pass a recorder."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} does not exist")
    cmd = reveal_command(p, platform)
    if cmd is None:
        if run is not None:
            run(["startfile", str(p)])
        else:  # pragma: no cover - Windows only
            os.startfile(str(p))  # type: ignore[attr-defined]
        return f"opened {p} with the Windows shell"
    launcher = run or _detach
    launcher(cmd)
    return f"ran {' '.join(cmd)}"


def _detach(cmd: list[str]) -> None:  # pragma: no cover - launches a real process
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
