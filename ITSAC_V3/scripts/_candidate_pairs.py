import json, os, glob
from collections import Counter

BUNDLE = r"C:\Users\xuan1\OneDrive\桌面\PhD论文\llmTraffic\ITSAC_REPRO_WORKSPACE\ITSAC_REPRO_BUNDLE"
OUT = os.path.join(BUNDLE, "outputs", "revision_v3")

# exact 10 runs per city (excludes partial runs + beijing r06 duplicate)
def run_files(campaign, run_names):
    files = []
    for rn in run_names:
        files += glob.glob(os.path.join(OUT, campaign, "search", rn, "llm", "call_*.json"))
    return files

CITIES = {
    "beijing": [
        *run_files("beijing_search_v1_llm", [f"run_{n:02d}" for n in range(1, 7)]),
        *run_files("beijing_search_v1_llm_r07", ["run_01"]),
        *run_files("beijing_search_v1_llm_r08", ["run_01"]),
        *run_files("beijing_search_v1_llm_r09", ["run_01"]),
        *run_files("beijing_search_v1_llm_r10", ["run_01"]),
    ],
    "shanghai": [
        *run_files("shanghai_search_v1_llm", [f"run_{n:02d}" for n in range(1, 8)]),
        *run_files("shanghai_search_v1_llm_r08", ["run_01"]),
        *run_files("shanghai_search_v1_llm_r09", ["run_01"]),
        *run_files("shanghai_search_v1_llm_r10", ["run_01"]),
    ],
    "taipei": [
        *run_files("taipei_search_v1_llm", [f"run_{n:02d}" for n in range(1, 3)]),
        *[f for n in range(3, 11) for f in run_files(f"taipei_search_v1_llm_r{n:02d}", ["run_01"])],
    ],
}

for city, files in CITIES.items():
    counter = Counter(); seen_any = Counter()
    total_calls = total_hits = 0
    for fp in files:
        rec = json.load(open(fp, encoding="utf-8"))
        pair = tuple(sorted(rec.get("pair", [])))
        if len(pair) != 2:
            continue
        total_calls += 1
        seen_any[pair] += 1
        if rec.get("interaction_positive"):
            counter[pair] += 1; total_hits += 1
    print(f"=== {city}: {total_calls} calls, {total_hits} hits ({total_hits/total_calls*100:.1f}%), {len(counter)} distinct positive pairs ===")
    for pair, h in counter.most_common(12):
        print(f"  {pair[0]}+{pair[1]}: {h} hits / {seen_any[pair]} calls")
    print()
