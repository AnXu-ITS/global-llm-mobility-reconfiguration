"""Analyze Experiment 4 results (post-review revision 2026-09-09).

Paired analysis over the frozen 20-seed design:
  - per-arm x per-manager mean tables for the headline metrics;
  - paired Wilcoxon signed-rank (arm vs anchor, per manager) with Holm
    correction across the arm family;
  - Cohen's d (pooled SD) — zero-variance / deterministic shifts reported as
    undefined, never as 0;
  - McNemar's test for paired BINARY metrics (deadline violation, recovery);
  - arm-delta (mean difference vs anchor) with a 95% CI on the paired
    differences.

Reads metrics.json under runs/experiment4/<cohort>/<sub>/<arm_id>/<scenario>/
seed<seed>/<manager>/.  Writes outputs/experiment4_summary.md + .json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scipy import stats
import hashlib
import yaml
from paper_metrics import execution_metrics
from paper_stats import summary, holm as shared_holm

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "experiment4"
OUT = ROOT / "outputs"

ANCHOR_ARM = {"4A": "OBS30", "4B": "D00", "4C": "N05"}

# headline metrics per sub-experiment (continuous unless noted)
COMMON_CONTINUOUS = [
    "critical_mission_completion_time_s",
    "recovery_time_s",
    "failure_to_replan_latency_s",
    "redundant_decision_count",
    "decision_oscillation_count",
    "decision_switch_count",
    "num_manager_decisions",
    "llm_total_tokens",
    "llm_total_prompt_tokens",
]
SUB_CONTINUOUS = {
    "4A": ["failure_discovery_latency_s"],
    "4C": ["legal_selection_count", "illegal_selection_count",
           "absent_selection_count", "constraint_violation_count",
           "prompt_size_chars_mean"],
}
BINARY = ["critical_mission_deadline_violation", "affected_critical", "recovery_success"]


def _num(x) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, bool):
        return float(x)
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_metrics(cohort: str) -> Dict[str, Dict[str, Dict[str, Dict[int, dict]]]]:
    """Validate cohort/version and preserve scenario+seed pairing; correct offline."""
    out = {}
    e4 = yaml.safe_load((ROOT/'config/experiment4_matrix.yaml').read_text(encoding='utf-8'))['experiment4']
    matrix_hash = hashlib.sha256(json.dumps(e4, sort_keys=True, ensure_ascii=False,
                                           separators=(',', ':')).encode()).hexdigest()
    for mf in sorted((RUNS/cohort).glob('*/*/*/seed*/B*/metrics.json')):
        sub,arm,scenario,sd,manager,_ = mf.relative_to(RUNS/cohort).parts
        seed = int(sd.removeprefix('seed'))
        metrics = json.loads(mf.read_text(encoding='utf-8'))
        rc = yaml.safe_load((mf.parent/'run_config.yaml').read_text(encoding='utf-8'))
        meta = json.loads((mf.parent/'run_meta.json').read_text(encoding='utf-8'))
        if rc.get('matrix_version') != 2 or rc.get('matrix_hash') != matrix_hash or meta.get('cohort') != cohort:
            raise ValueError(f'Noncurrent E4 run: {mf}')
        corrected = execution_metrics(mf.parent, metrics)
        if manager == 'B4b':
            records = [json.loads(line).get('llm_metadata') or {} for line in
                       (mf.parent/'manager_outputs.jsonl').read_text(encoding='utf-8').splitlines() if line]
            corrected['llm_call_count'] = len(records)
            corrected['llm_transport_errors'] = sum(r.get('validation_status')=='LLM_TRANSPORT_ERROR' for r in records)
            corrected['llm_structured_retries'] = sum(r.get('retry_count',0) or 0 for r in records)
            corrected['llm_logged_prompt_tokens'] = sum(r.get('prompt_tokens',0) or 0 for r in records)
        out.setdefault((sub,arm,manager), {})[(scenario,seed)] = corrected
    if cohort == 'primary':
        seeds = yaml.safe_load((ROOT/'config/experiment4_seeds.yaml').read_text(encoding='utf-8'))['primary_seeds']
        expected={(sub,a['id'],mgr):{(sid,sd) for sid in e4['exp'+sub.lower()]['scenarios'] for sd in seeds}
                  for sub in ('4A','4B','4C') for a in e4['exp'+sub.lower()]['arms']
                  for mgr in e4['exp'+sub.lower()]['managers']}
        if set(out) != set(expected) or any(set(out[k]) != v for k,v in expected.items()):
            raise ValueError('E4 primary matrix is incomplete or contains unexpected cells')
    return out


def _aligned(a: Dict[int, dict], b: Dict[int, dict], metric: str
             ) -> Tuple[List[float], List[float]]:
    seeds = sorted(set(a) & set(b))
    xa, xb = [], []
    for s in seeds:
        va, vb = _num(a[s].get(metric)), _num(b[s].get(metric))
        if va is None or vb is None:
            continue
        xa.append(va)
        xb.append(vb)
    return xa, xb


def _cohens_d(a: List[float], b: List[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = float(sum(a)) / len(a), float(sum(b)) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    sp = math.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2))
    if sp == 0.0:
        # zero pooled variance: identical distributions -> d=0; a deterministic
        # (constant) shift has an undefined effect size (never reported as 0).
        return 0.0 if ma == mb else None
    return (ma - mb) / sp


def _wilcoxon_paired(a: List[float], b: List[float]) -> Optional[float]:
    if len(a) < 2:
        return None
    # drop pairs whose difference is exactly 0 (Wilcoxon ignores them anyway)
    pairs = [(x, y) for x, y in zip(a, b) if x != y]
    if len(pairs) < 1:
        return 1.0
    try:
        _, p = stats.wilcoxon([p[0] for p in pairs], [p[1] for p in pairs],
                              zero_method="wilcox")
        return float(p)
    except ValueError:
        return None


def _mcnemar(a: List[float], b: List[float]) -> Optional[float]:
    """Paired binary test: a,b are 0/1 indicator lists."""
    if len(a) < 1:
        return None
    b10 = b01 = 0
    for x, y in zip(a, b):
        if x == 1 and y == 0:
            b10 += 1
        elif x == 0 and y == 1:
            b01 += 1
    n_disc = b10 + b01
    if n_disc == 0:
        return 1.0
    # exact binomial two-sided p on the discordant pairs
    p = 2 * min(0.5, stats.binom.cdf(min(b10, b01), n_disc, 0.5))
    return float(p)


def _holm(pvals: List[Optional[float]]) -> List[Optional[float]]:
    adjusted = shared_holm(pvals)
    return [v if p is not None else None for p,v in zip(pvals,adjusted)]


def _mean_ci(diffs: List[float]) -> Optional[Dict[str, float]]:
    n = len(diffs)
    if n < 2:
        return None
    m = float(sum(diffs)) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in diffs) / (n - 1))
    se = sd / math.sqrt(n)
    tcrit = float(stats.t.ppf(0.975, n - 1))
    return {"mean": round(float(m), 3),
            "ci95_low": round(float(m - tcrit * se), 3),
            "ci95_high": round(float(m + tcrit * se), 3)}


def _analyze_sub(sub: str, data, out_lines: List[str]) -> Dict[str, Any]:
    arms = sorted({k[1] for k in data if k[0] == sub}, key=lambda a: (len(a), a))
    managers = sorted({k[2] for k in data if k[0] == sub})
    anchor = ANCHOR_ARM.get(sub)
    metrics = COMMON_CONTINUOUS + SUB_CONTINUOUS.get(sub, []) + BINARY

    out_lines.append(f"\n## {sub}\n")
    sub_json: Dict[str, Any] = {"arms": {}, "managers": managers}

    # Absolute arm values are the primary presentation; don't pool dose arms.
    header = ["arm", "manager", "n", "completion_s", "deadline_rate", "affected_n", "recovered/affected"]
    rows = []
    for arm in arms:
        sub_json['arms'][arm] = {}
        for mgr in managers:
            ds = list(data.get((sub,arm,mgr),{}).values())
            cell = {'n_runs':len(ds), 'metrics':{met:summary([d.get(met) for d in ds],met in BINARY) for met in metrics}}
            if mgr == 'B4b':
                calls=sum(d['llm_call_count'] for d in ds)
                cell['llm_reliability']={'calls':calls,
                    'transport_errors':sum(d['llm_transport_errors'] for d in ds),
                    'structured_retries':sum(d['llm_structured_retries'] for d in ds),
                    'prompt_tokens_per_logged_call':sum(d['llm_logged_prompt_tokens'] for d in ds)/calls if calls else None}
            sub_json['arms'][arm][mgr] = cell
            n_affected = sum(bool(d.get('affected_critical')) for d in ds)
            n_recovered = sum(d.get('recovery_success') is True for d in ds)
            rows.append([arm,mgr,len(ds),round(cell['metrics']['critical_mission_completion_time_s']['mean'],3),
                         round(cell['metrics']['critical_mission_deadline_violation']['mean'],3),n_affected,
                         f'{n_recovered}/{n_affected}' if n_affected else 'N/A'])
    _write_md_table(out_lines, header, rows)

    # --- paired stats vs anchor -----------------------------------------
    for metric in metrics:
        for mgr in managers:
            if anchor not in arms:
                continue
            anchor_d = data.get((sub, anchor, mgr), {})
            if not anchor_d:
                continue
            arm_pvals = []
            arm_rows = []
            for arm in arms:
                if arm == anchor:
                    continue
                d = data.get((sub, arm, mgr), {})
                a, b = _aligned(d, anchor_d, metric)
                if metric in BINARY:
                    p = _mcnemar(a, b)
                else:
                    p = _wilcoxon_paired(a, b)
                arm_pvals.append(p)
                diffs = [x - y for x, y in zip(a, b)]
                ci = _mean_ci(diffs)
                arm_rows.append({
                    "arm": arm, "n": len(a),
                    "p_raw": p,
                    "cohens_d": _cohens_d(a, b) if metric not in BINARY else None,
                    "mean_delta": (round(ci["mean"], 3) if ci else None),
                    "ci95": ci,
                })
            adj = _holm(arm_pvals)
            for i, r in enumerate(arm_rows):
                r["p_holm"] = adj[i]
            key = f"{metric} @ {mgr}"
            sub_json.setdefault("paired", {})[key] = {
                "anchor": anchor, "arms": arm_rows}
            sig = [r["arm"] for r in arm_rows if r["p_holm"] is not None and r["p_holm"] < 0.05]
            if mgr == 'B4b' and metric in ('critical_mission_completion_time_s','critical_mission_deadline_violation','llm_total_prompt_tokens'):
                out_lines.append(f"\n{metric}, B4b vs {anchor}: Holm-significant arms {sig or 'none'}. Full paired deltas and CIs are in JSON.\n")

    return sub_json


def _write_md_table(out: List[str], header: List[str], rows: List[List[str]]) -> None:
    out.append("| " + " | ".join(header) + " |")
    out.append("|" + "|".join(["---"] * len(header)) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")


def main(cohort: str = "primary") -> int:
    data = load_metrics(cohort)
    if not data:
        print(f"no metrics.json found under runs/experiment4/{cohort}")
        return 1
    out_lines = [f"# Experiment 4 summary (cohort `{cohort}`)\n"]
    result: Dict[str, Any] = {"cohort": cohort, "anchor_arm": ANCHOR_ARM,
        "analysis_version":"paper_final_20260910", "matrix_version":2,
        "definitions":{"recovery_success":"conditional on affected_critical; N/A otherwise",
                       "failure_to_replan_latency_s":"first issued critical-mission transport/replan action minus failure time; NO_ACTION excluded",
                       "decision_switch_count":"changes of resource or mode",
                       "decision_oscillation_count":"return to a previously used resource/mode after a switch; descriptive, not necessarily unnecessary",
                       "binary_ci":"Wilson for rates; paired t interval for descriptive risk differences"}}
    for sub in ["4A", "4B", "4C"]:
        result[sub] = _analyze_sub(sub, data, out_lines)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "experiment4_summary.md").write_text("\n".join(out_lines) + "\n",
                                                encoding="utf-8")
    (OUT / "experiment4_summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8")
    corrected = OUT/'paper_final'
    corrected.mkdir(exist_ok=True)
    (corrected/'e4_run_metrics.json').write_text(json.dumps([
        dict(d, paper_manager=mgr) for (sub,arm,mgr),ds in data.items() for d in ds.values()
    ],indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    n_runs = sum(len(seeds) for seeds in data.values())
    print(f"wrote outputs/experiment4_summary.md + .json "
          f"({len(data)} combos, {n_runs} runs)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "primary"))
