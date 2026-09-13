import json, os, shutil, sys, time

# usage: reset_stuck.py <campaign> <run_dir_name> <call_index>
campaign = sys.argv[1]   # e.g. taipei_search_v1_llm_r10
run_dir = sys.argv[2]    # e.g. run_01
call_idx = int(sys.argv[3])  # e.g. 38

BUNDLE = r"C:\Users\xuan1\OneDrive\桌面\PhD论文\llmTraffic\ITSAC_REPRO_WORKSPACE\ITSAC_REPRO_BUNDLE"
unit = os.path.join(BUNDLE, "outputs", "revision_v3", campaign, "search", run_dir, "llm")
ledger_path = os.path.join(unit, "proposal_events.jsonl")
call_dir = os.path.join(unit, "proposals", f"call_{call_idx:03d}")

ts = time.strftime("%Y%m%d_%H%M%S")
assert os.path.isfile(ledger_path), "ledger not found"

shutil.copy2(ledger_path, ledger_path + f".bak_{ts}")
if os.path.isdir(call_dir):
    shutil.move(call_dir, call_dir + f"._stuck_{ts}")
    print("moved", call_dir)

kept, dropped = [], 0
with open(ledger_path, encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("call_index") == call_idx:
            dropped += 1
            continue
        kept.append(line)
with open(ledger_path, "w", encoding="utf-8") as f:
    f.write("\n".join(kept) + ("\n" if kept else ""))

print(f"ledger: kept={len(kept)} dropped={dropped} (call_index={call_idx})")
print("done")
