import json, os, glob

BUNDLE = r"C:\Users\xuan1\OneDrive\桌面\PhD论文\llmTraffic\ITSAC_REPRO_WORKSPACE\ITSAC_REPRO_BUNDLE"
OUT = os.path.join(BUNDLE, "outputs", "revision_v3")

def run_stats(campaign_root):
    """Sum calls/hits over COMPLETED run state.json files (excludes partial RUNNING)."""
    calls = hits = 0
    pat = os.path.join(OUT, campaign_root, "search", "run_*", "llm", "state.json")
    for p in glob.glob(pat):
        s = json.load(open(p, encoding="utf-8"))
        if s.get("status") != "COMPLETED":
            continue
        calls += int(s.get("completed", 0) or 0)
        hits += int(s.get("hits", 0) or 0)
    return calls, hits

def perrun_stats(campaign_root):
    """Sum a single-run per-run campaign (run_01)."""
    return run_stats(campaign_root)

# original campaigns: only COMPLETED runs count (partial runs 6/8/3 excluded automatically)
orig_beijing = run_stats("beijing_search_v1_llm")      # runs 1-5 completed
orig_shanghai = run_stats("shanghai_search_v1_llm")    # runs 1-7 completed
orig_taipei = run_stats("taipei_search_v1_llm")        # runs 1-2 completed

per_bj = {n: perrun_stats(f"beijing_search_v1_llm_r{n:02d}") for n in range(6, 11)}
per_sh = {n: perrun_stats(f"shanghai_search_v1_llm_r{n:02d}") for n in range(8, 11)}
per_tp = {n: perrun_stats(f"taipei_search_v1_llm_r{n:02d}") for n in range(3, 11)}

print("=== per-run llm hits (calls, hits) ===")
print("beijing orig(1-5):", orig_beijing)
for n in range(6, 11):
    print(f"  beijing r{n:02d}:", per_bj[n])
print("shanghai orig(1-7):", orig_shanghai)
for n in range(8, 11):
    print(f"  shanghai r{n:02d}:", per_sh[n])
print("taipei orig(1-2):", orig_taipei)
for n in range(3, 11):
    print(f"  taipei r{n:02d}:", per_tp[n])

def tot(orig, per):
    c = orig[0] + sum(v[0] for v in per.values())
    h = orig[1] + sum(v[1] for v in per.values())
    return c, h

bj = tot(orig_beijing, per_bj)
sh = tot(orig_shanghai, per_sh)
tp = tot(orig_taipei, per_tp)
print("=== totals ===")
for name, (c, h) in [("beijing", bj), ("shanghai", sh), ("taipei", tp)]:
    print(f"{name}: {h}/{c} ({h/c*100:.1f}%)" if c else f"{name}: 0/0")
