import json, os, glob

BUNDLE = r"C:\Users\xuan1\OneDrive\桌面\PhD论文\llmTraffic\ITSAC_REPRO_WORKSPACE\ITSAC_REPRO_BUNDLE"
OUT = os.path.join(BUNDLE, "outputs", "revision_v3")

def tally(campaigns, methods):
    """Sum calls/hits for given campaigns (all run dirs), across given methods."""
    calls = hits = 0
    for camp in campaigns:
        root = os.path.join(OUT, camp, "search")
        for m in methods:
            for fp in glob.glob(os.path.join(root, "run_*", m, "call_*.json")):
                rec = json.load(open(fp, encoding="utf-8"))
                calls += 1
                if rec.get("interaction_positive"):
                    hits += 1
    return calls, hits

# llm feedback: exact 10 runs (exclude partial runs + beijing r06 dup)
def llm_files(city, run_range_orig, perrun_nums):
    files = []
    for n in run_range_orig:
        files += glob.glob(os.path.join(OUT, f"{city}_search_v1_llm", "search", f"run_{n:02d}", "llm", "call_*.json"))
    for n in perrun_nums:
        files += glob.glob(os.path.join(OUT, f"{city}_search_v1_llm_r{n:02d}", "search", "run_01", "llm", "call_*.json"))
    return files

def llm_tally(city, run_range_orig, perrun_nums):
    calls = hits = 0
    for fp in llm_files(city, run_range_orig, perrun_nums):
        rec = json.load(open(fp, encoding="utf-8")); calls += 1
        if rec.get("interaction_positive"): hits += 1
    return calls, hits

print("=== FINAL 15-method table (hits/calls) ===")
print(f"{'method':<12}{'beijing':<18}{'shanghai':<18}{'taipei':<18}")
for m in ["random", "heuristic", "ucb", "llm_nofb"]:
    row = []
    for c in ["beijing", "shanghai", "taipei"]:
        camp = f"{c}_search_v1_{m}"
        calls, hits = tally([camp], [m])
        row.append(f"{hits}/{calls} ({hits/calls*100:.1f}%)" if calls else "n/a")
    print(f"{m:<12}{row[0]:<18}{row[1]:<18}{row[2]:<18}")

# llm feedback
llm_cfg = {
    "beijing":  (range(1,7), range(7,11)),
    "shanghai": (range(1,8), range(8,11)),
    "taipei":   (range(1,3), range(3,11)),
}
row = []
for c, (rng, prn) in llm_cfg.items():
    calls, hits = llm_tally(c, rng, prn)
    row.append(f"{hits}/{calls} ({hits/calls*100:.1f}%)" if calls else "n/a")
print(f"{'llm':<12}{row[0]:<18}{row[1]:<18}{row[2]:<18}")
