"""Re-derive counterfactual verdicts from the saved A/B actions (no LLM calls)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.run_phase3_counterfactual import verdict  # noqa: E402

OUT = ROOT / "runs" / "phase3_offline_decisions"
REPORT = ROOT / "reports" / "LLM_COUNTERFACTUAL_SANITY.md"


def main() -> int:
    rows = [json.loads(l) for l in (OUT / "counterfactual.jsonl").read_text(encoding="utf-8").splitlines()]
    for r in rows:
        r["verdict"] = verdict(r["pair_id"], r["A"]["action"], r["B"]["action"])
    with open(OUT / "counterfactual.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")

    n_pass = sum(1 for r in rows if r["verdict"] == "PASS")
    n_obs = sum(1 for r in rows if r["verdict"] == "OBSERVED")
    n_fail = sum(1 for r in rows if r["verdict"] == "FAIL")
    lines = [
        "# LLM Counterfactual Sanity (Phase 3)", "",
        "9 paired states; only ONE variable changes between A and B. The LLM is",
        "required to produce a *directionally correct* decision change, not to match",
        "the Rule Manager.", "",
        "| pair | variable | A | B | verdict |",
        "|------|----------|---|---|---------|",
    ]
    for r in rows:
        aa, ab = r["A"]["action"], r["B"]["action"]
        a_txt = f"{aa.get('type')} {aa.get('aircraft_id') or ''}".strip()
        b_txt = f"{ab.get('type')} {ab.get('aircraft_id') or ''}".strip()
        lines.append(f"| {r['pair_id']} | {r['variable']} | {a_txt} | {b_txt} | {r['verdict']} |")
    lines += ["", f"**Summary:** {n_pass} PASS / {n_obs} OBSERVED / {n_fail} FAIL (total {len(rows)}).", ""]
    for r in rows:
        lines.append(f"- **{r['pair_id']}** ({r['desc']}): A={r['A']['action'].get('type')} "
                     f"{r['A']['action'].get('aircraft_id') or ''} -> B={r['B']['action'].get('type')} "
                     f"{r['B']['action'].get('aircraft_id') or ''} [{r['verdict']}]")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{n_pass} PASS / {n_obs} OBSERVED / {n_fail} FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
