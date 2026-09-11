"""Generate the canonical S0 BlueSky scenario file from scenario_config.yaml.

The .scn file is a textual representation of the same scene the orchestrator
builds programmatically (single source of truth = config + orchestrator.fleet).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod  # noqa: E402
from orchestrator.fleet import build_scene_commands  # noqa: E402

OUT = ROOT / "sim" / "bluesky" / "canonical_s0.scn"


def main() -> int:
    cfg = config_mod.load_config()
    cmds = build_scene_commands(cfg)
    lines = ["# canonical S0 -- low-altitude scene (single WGS84 source: scenario_config.yaml)"]
    for c in cmds:
        lines.append(f"0:00:00.00>{c}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(cmds)} commands)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
