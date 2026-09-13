import json, os

CFG_DIR = r"C:\Users\xuan1\OneDrive\桌面\PhD论文\llmTraffic\ITSAC_REPRO_WORKSPACE\ITSAC_REPRO_BUNDLE\configs\revision_v3"

CITIES = {
    "beijing": 15,   # maximum_single_emergency_braking
    "shanghai": 0,
    "taipei": 0,
}
METHODS = ["random", "heuristic", "ucb", "llm_no_feedback", "llm"]

def campaign_suffix(method):
    return method.replace("_feedback", "").replace("llm_no", "llm_nofb")

for city, ebr in CITIES.items():
    for method in METHODS:
        cfg = {
            "protocol": "itsac_controlled_interactions_v3",
            "campaign": f"{city}_search_v1_{campaign_suffix(method)}",
            "site": city,
            "mode": "search",
            "seed_pool": [701, 702, 703, 704, 705, 706, 707, 708, 709, 710],
            "seed_role": "development_search_not_final_holdout",
            "demand_scale": 1.0,
            "perturbation_window": [200, 800],
            "sumo_timeout_seconds": 180,
            "policy": {
                "simulation_end_s": 3600,
                "minimum_completion_rate": 0.9,
                "minimum_mean_speed": 2.0,
                "minimum_late_speed": 2.0,
                "maximum_remaining_fraction": 0.1,
                "systemic_spillback_edges": 15,
                "maximum_single_emergency_braking": ebr,
                "collision_endpoint_policy": "exclude"
            },
            "methods": [method],
            "runs": 10,
            "calls_per_run": 50,
            "schedule_seed": 20260909,
            "policy_seed": 20260910,
            "ucb_alpha": 1.0,
            "llm": {
                "model": "corp-ai/openai/deepseek-v4-pro",
                "temperature": 0,
                "max_tokens": 32768,
                "timeout_seconds": 360,
                "max_contract_attempts": 5,
                "max_transport_errors": 5,
                "backoff_seconds": 5
            }
        }
        path = os.path.join(CFG_DIR, f"{city}_search_v1_{campaign_suffix(method)}.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("wrote", os.path.basename(path), "-> campaign", cfg["campaign"])
print("DONE", len(CITIES) * len(METHODS), "configs")
