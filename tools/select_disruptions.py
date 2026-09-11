"""Select the three candidate ground-disruption links B1/B2/B3 for the cropped S0.

For each edge on the current D1->H1 route, close it, measure the free-flow ETA
impact via the TraCI router (findRoute + lane length/maxSpeed), reopen it, and
rank the edges. Then assign:

    B1 = highest  finite-impact edge  (~high accessibility impact)
    B2 = median   finite-impact edge  (~medium)
    B3 = lowest   finite-impact edge  (~low)

B1/B2/B3 are ALTERNATIVE experimental disruptions (never closed together).
Also verifies the crop preserves >=2 valid D1->H1 ground detours (with B1 closed)
and writes everything back into scenario_config.yaml.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.sumo_env import setup, binary  # noqa: E402

setup()
import traci  # noqa: E402
import yaml  # noqa: E402

from orchestrator import config as config_mod  # noqa: E402

CFG_PATH = ROOT / "config" / "scenario_config.yaml"
SUMOCFG = ROOT / "sim" / "sumo" / "canonical.sumocfg"


def ff_eta(edges) -> float:
    """Free-flow ETA (s) along a list of edge ids (lane length / max speed)."""
    eta = 0.0
    for e in edges:
        lane = f"{e}_0"
        speed = max(traci.lane.getMaxSpeed(lane), 1e-3)
        eta += traci.lane.getLength(lane) / speed
    return eta


def route_edges(a, b):
    r = traci.simulation.findRoute(a, b)
    return list(r.edges) if r.edges else []


def main() -> int:
    cfg = config_mod.load_config()
    d1 = cfg["sumo_mapping"]["D1"]["edge_id"]
    h1 = cfg["sumo_mapping"]["H1"]["edge_id"]

    traci.start([binary("sumo"), "-c", str(SUMOCFG), "--no-warnings", "true"], label="bselect")
    traci.simulationStep()

    # --- base route + ETA ---
    base = route_edges(d1, h1)
    base_eta = ff_eta(base)
    print(f"base route: {len(base)} edges, free-flow ETA={base_eta:.2f}s")

    # --- closure impact per edge ---
    results = []
    for eid in base:
        if eid in (d1, h1):
            # closing the origin/destination edge itself disconnects O/D by definition
            results.append({"edge": eid, "eta": None, "inc_pct": None,
                            "has_detour": False, "reason": "origin/destination edge"})
            continue
        traci.edge.setDisallowed(eid, ["passenger"])
        try:
            alt = route_edges(d1, h1)
            eta = ff_eta(alt) if alt else None
        except Exception:
            alt, eta = [], None
        inc = (eta - base_eta) / base_eta * 100.0 if eta is not None else None
        results.append({"edge": eid, "eta": eta, "inc_pct": inc,
                        "has_detour": eta is not None, "reason": ""})
        traci.edge.setAllowed(eid, ["passenger"])

    # --- detour verification: with B1 closed, find >=2 distinct alternative routes ---
    # detour candidates need a B1 first; use the max-impact edge as a provisional B1
    valid = [r for r in results if r["has_detour"]]
    valid_sorted = sorted(valid, key=lambda r: r["eta"])
    prov_b1 = valid_sorted[-1]["edge"]

    traci.edge.setDisallowed(prov_b1, ["passenger"])
    det1 = route_edges(d1, h1)
    det1_eta = ff_eta(det1) if det1 else None
    # additionally block the middle edge of detour1 to force a second detour
    det2 = None
    if det1 and len(det1) > 2:
        mid = det1[len(det1) // 2]
        traci.edge.setDisallowed(mid, ["passenger"])
        try:
            det2 = route_edges(d1, h1)
        except Exception:
            det2 = []
        traci.edge.setAllowed(mid, ["passenger"])
    traci.edge.setAllowed(prov_b1, ["passenger"])
    det2_eta = ff_eta(det2) if det2 else None

    distinct = {frozenset(base)}
    for d in (det1, det2):
        if d:
            distinct.add(frozenset(d))
    num_detours = len(distinct) - 1  # routes besides the base
    print(f"detours with B1 closed: detour1={det1_eta:.2f}s, detour2={det2_eta:.2f}s "
          f"-> {num_detours} distinct alternative route(s)")

    # --- assign B1/B2/B3 from the finite-impact ranking ---
    # levels: low (smallest inc), medium (median inc), high (largest inc)
    if len(valid_sorted) < 3:
        print("WARNING: fewer than 3 finite-impact edges on the route")
    low = valid_sorted[0]
    high = valid_sorted[-1]
    medium = valid_sorted[len(valid_sorted) // 2]
    # ensure the three are distinct
    chosen = [high, medium, low]
    if len({c["edge"] for c in chosen}) < 3:
        # pick distinct by scanning
        picked = [high]
        for c in valid_sorted[::-1]:
            if c["edge"] not in {p["edge"] for p in picked} and c["edge"] != high["edge"]:
                picked.append(c)
            if len(picked) == 3:
                break
        picked.sort(key=lambda r: -(r["inc_pct"] or 0))
        high, medium, low = picked
    assign = {"B1": (high, "high"), "B2": (medium, "medium"), "B3": (low, "low")}

    print("\nclosure impact ranking (sorted by detour ETA):")
    for r in results:
        print(f"  {r['edge']:18s} eta={r['eta']} inc%={r['inc_pct']} detour={r['has_detour']}")
    print("\nASSIGNED:")
    for name, (r, level) in assign.items():
        print(f"  {name} = {r['edge']}  ({level}, inc%={r['inc_pct']})")

    # --- update config ---
    import sumolib
    net = sumolib.net.readNet(str(ROOT / "sim" / "sumo" / "network.net.xml"))
    disruption = {}
    for name, (r, level) in assign.items():
        e = net.getEdge(r["edge"])
        bx, by = e.getShape()[len(e.getShape()) // 2]
        lon, lat = net.convertXY2LonLat(bx, by)
        cfg["facilities"][name] = {
            "type": "disruption_link",
            "lat": lat, "lon": lon,
            "impact_level": level,
            "selection_reason": ("TraCI-router ranked candidate ground-disruption link "
                                 f"({level} D1->H1 ETA impact)"),
        }
        cfg["sumo_mapping"][name] = {
            "edge_id": r["edge"], "lane_id": r["edge"] + "_0",
            "x": round(bx, 3), "y": round(by, 3), "snapped_distance_m": 0.0,
        }
        disruption[name] = {
            "edge_id": r["edge"], "impact_level": level,
            "base_eta_s": round(base_eta, 2),
            "detour_eta_s": round(r["eta"], 2) if r["eta"] else None,
            "eta_increase_pct": round(r["inc_pct"], 2) if r["inc_pct"] is not None else None,
            "has_detour": r["has_detour"],
        }

    cfg["disruption_links"] = {
        "note": "B1/B2/B3 are alternative candidate disruptions (never simultaneous).",
        "base_eta_s": round(base_eta, 2),
        "num_ground_detours_with_b1_closed": num_detours,
        "detour1_eta_s": round(det1_eta, 2) if det1_eta else None,
        "detour2_eta_s": round(det2_eta, 2) if det2_eta else None,
        "links": disruption,
        "closure_impact": results,
    }
    # retire the old single-B1 section
    cfg.pop("b1_selection", None)

    CFG_PATH.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, default_flow_style=False),
                        encoding="utf-8")
    print(f"\nupdated {CFG_PATH}")

    traci.close()
    if num_detours < 2:
        print(f"\n[FAIL] crop preserves only {num_detours} detour(s) -- need >=2; grow the extent")
        return 1
    print(f"\n[OK] crop preserves {num_detours} detour(s) (>=2 required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
