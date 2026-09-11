"""Select B1 (critical road link / bottleneck) using TraCI's own router.

For each edge on the current D1->H1 shortest route, close it, measure the ETA
increase via getDistanceRoad, reopen it, and pick the edge whose closure
maximises the ETA increase (and for which a detour still exists). This uses the
exact same routing engine as the runtime co-simulation, so the chosen B1 is
guaranteed to produce the accessibility degradation the experiment requires.
"""
import json
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


def main() -> int:
    cfg = config_mod.load_config()
    d1 = cfg["sumo_mapping"]["D1"]["edge_id"]
    h1 = cfg["sumo_mapping"]["H1"]["edge_id"]

    traci.start([binary("sumo"), "-c", str(SUMOCFG), "--no-warnings", "true"], label="b1select")
    traci.simulationStep()

    def eta_between(a, b):
        route = traci.simulation.findRoute(a, b)
        if route.edges is None or len(route.edges) == 0:
            return None, []
        edges = list(route.edges)
        return sum(traci.edge.getTraveltime(e) for e in edges), edges

    # base route + ETA
    base_eta, base_edges = eta_between(d1, h1)
    print(f"base route: {len(base_edges)} edges, ETA={base_eta:.2f}s")

    results = []
    for eid in base_edges:
        traci.edge.setDisallowed(eid, ["passenger"])
        try:
            eta, _ = eta_between(d1, h1)
            inc_pct = (eta - base_eta) / base_eta * 100.0 if eta is not None else None
            results.append({"edge": eid, "eta": eta, "inc_pct": inc_pct, "has_detour": eta is not None})
        except Exception:
            results.append({"edge": eid, "eta": None, "inc_pct": None, "has_detour": False})
        traci.edge.setAllowed(eid, ["passenger"])

    traci.close()

    valid = [r for r in results if r["has_detour"]]
    valid.sort(key=lambda r: -r["eta"] if r["eta"] else -1e9)
    print("\nclosure impact (sorted by detour ETA):")
    for r in results:
        print(f"  {r['edge']:18s} eta={r['eta']} inc%={r['inc_pct']} detour={r['has_detour']}")

    if not valid:
        print("No single-edge closure produced a detour. Falling back to longest-edge midpoint.")
        best = results[len(results) // 2]
    else:
        best = valid[0]

    b1_edge = best["edge"]
    print(f"\nSELECTED B1 = {b1_edge} (inc%={best['inc_pct']}, detour={best['has_detour']})")

    # update config: B1 facility -> midpoint of that edge, sumo_mapping, b1_selection
    import sumolib
    net = sumolib.net.readNet(str(ROOT / "sim" / "sumo" / "network.net.xml"))
    e = net.getEdge(b1_edge)
    bx, by = e.getShape()[len(e.getShape()) // 2]
    lon, lat = net.convertXY2LonLat(bx, by)

    cfg["facilities"]["B1"]["lat"] = lat
    cfg["facilities"]["B1"]["lon"] = lon
    cfg["sumo_mapping"]["B1"]["edge_id"] = b1_edge
    cfg["sumo_mapping"]["B1"]["lane_id"] = b1_edge + "_0"
    cfg["sumo_mapping"]["B1"]["x"] = round(bx, 3)
    cfg["sumo_mapping"]["B1"]["y"] = round(by, 3)
    cfg["b1_selection"] = {
        "edge_id": b1_edge, "is_bridge": False,
        "reason": "TraCI router bottleneck: edge on D1->H1 corridor whose closure maximises ETA increase",
        "base_eta_s": round(base_eta, 2),
        "detour_eta_s": round(best["eta"], 2) if best["eta"] else None,
        "eta_increase_pct": round(best["inc_pct"], 2) if best["inc_pct"] is not None else None,
        "has_detour": best["has_detour"],
        "closure_impact": results,
    }
    CFG_PATH.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, default_flow_style=False),
                        encoding="utf-8")
    print(f"updated {CFG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
