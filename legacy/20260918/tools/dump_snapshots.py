import json
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\user\OneDrive\桌面\PhD论文\Global LLM-Supervised Reconfiguration of Ground–Low-Altitude Mobility under Disruptions")
run = root / "runs" / "phase2_rule_manager" / "C2_B"
snaps = [json.loads(l) for l in open(run / "snapshots.jsonl", encoding="utf-8")]
for s in snaps:
    gs = s["global_state"]
    t = s["t"]
    gr = gs["ground"]
    air = {a["id"]: (a["status"], a["current_mission"], a["c2_status"]) for a in gs["air"]}
    allm = gs["missions"]["existing"] + gs["missions"]["new"]
    msum = {m["id"]: (m["state"], m["assigned_resource"], m["mode"]) for m in allm}
    print(f"--- t={t} ---")
    print(f"  ground: b1={gr['b1_state']} eta={gr['current_d1_h1_eta_s']} inc={gr['eta_increase_pct']}% acc={gr['accessibility_status']} fb_eta={gr['ground_fallback_eta_s']}")
    print(f"  air: {air}")
    print(f"  missions: {msum}")
    print(f"  trend: {gs['trend']}")
