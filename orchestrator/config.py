"""Load the shared scenario configuration (single geographic truth)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "scenario_config.yaml"


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def facilities(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return config["facilities"]


def bbox(config: Dict[str, Any]) -> Dict[str, float]:
    return config["bbox"]
