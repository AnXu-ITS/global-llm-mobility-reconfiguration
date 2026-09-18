"""Set up the SUMO environment from the eclipse-sumo wheel.

`import sumo` sets SUMO_HOME (site-packages/sumo) and PROJ_LIB; the TraCI and
sumolib Python modules live under `sumo/tools`. This helper makes both
importable and keeps SUMO_HOME consistent across the whole project.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SUMO_HOME: str = ""


def setup() -> str:
    global SUMO_HOME
    if SUMO_HOME:
        return SUMO_HOME
    import sumo  # noqa: F401  (sets os.environ['SUMO_HOME'])
    SUMO_HOME = str(Path(sumo.SUMO_HOME))
    tools = str(Path(SUMO_HOME) / "tools")
    for p in (SUMO_HOME, tools):
        if p not in sys.path:
            sys.path.insert(0, p)
    return SUMO_HOME


def binary(name: str) -> str:
    home = setup()
    exe = Path(home) / "bin" / f"{name}.exe"
    if not exe.exists():
        raise FileNotFoundError(f"SUMO binary not found: {exe}")
    return str(exe)
