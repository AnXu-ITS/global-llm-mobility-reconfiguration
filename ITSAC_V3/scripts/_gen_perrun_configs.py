import json, os

CFG_DIR = r"C:\Users\xuan1\OneDrive\桌面\PhD论文\llmTraffic\ITSAC_REPRO_WORKSPACE\ITSAC_REPRO_BUNDLE\configs\revision_v3"

# remaining runs per city (feedback LLM only; llm_nofb + non-LLM already done)
REMAINING = {
    "beijing":  [6, 7, 8, 9, 10],
    "shanghai": [8, 9, 10],
    "taipei":   [3, 4, 5, 6, 7, 8, 9, 10],
}

SCHEDULE_SEED = 20260909
POLICY_SEED = 20260910

count = 0
for city, runs in REMAINING.items():
    src = os.path.join(CFG_DIR, f"{city}_search_v1_llm.json")
    base = json.load(open(src, encoding="utf-8"))
    for N in runs:
        cfg = dict(base)
        cfg["campaign"] = f"{city}_search_v1_llm_r{N:02d}"
        cfg["runs"] = 1
        # run_index=1 in the new campaign must reproduce original run N's randomness:
        #   original run N: Random(schedule_seed + N), policy_seed = policy_seed + N
        #   new run 1:      Random(schedule_seed' + 1), policy_seed' + 1
        cfg["schedule_seed"] = SCHEDULE_SEED + (N - 1)
        cfg["policy_seed"] = POLICY_SEED + (N - 1)
        out = os.path.join(CFG_DIR, f"{city}_search_v1_llm_r{N:02d}.json")
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"wrote {os.path.basename(out)} (orig run {N}, schedule_seed={cfg['schedule_seed']}, policy_seed={cfg['policy_seed']})")
        count += 1
print("DONE", count, "per-run configs")
