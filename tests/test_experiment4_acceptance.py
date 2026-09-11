"""Experiment 4 acceptance tests (post-review revision 2026-09-09).

Offline unit tests: no SUMO / BlueSky / LLM calls.  Each `test_*` function is
callable directly with a `tmp_path` argument (pytest is optional).

Covers the review's release gates:
  - config / seeds well-formed;
  - 4C input-scale distractors are deterministic, seed-sensitive, and INERT
    (never change the legal candidate set / viable resources);
  - runner construction + per-arm state (4A observation clock, 4B delay,
    4C distractor count);
  - E3-v2 full-task periodic trigger is inherited (secondary WAITING => due);
  - 4A observation-tick polling (call count ∝ 1/interval);
  - 4B time-slice order (events before same-time pending) + pending versioning
    (supersede) + idempotency (never re-ground an already-ground mission);
  - analysis helper correctness (Cohen's d zero-variance handling, McNemar).
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import config as config_mod                      # noqa: E402
from orchestrator.experiment1_runner import make_manager           # noqa: E402
from orchestrator.experiment4_fleet import generate_distractors    # noqa: E402
from orchestrator.experiment4_runner import (Experiment4BRunner,   # noqa: E402
                                             Experiment4CRunner,
                                             Experiment4Runner)
from orchestrator.registry import Mission, Registry                # noqa: E402


def _load_e4() -> dict:
    with open(ROOT / "config" / "experiment4_matrix.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["experiment4"]


def _scenario(e4: dict, sid: str) -> dict:
    return next(s for s in e4["scenarios"] if s["id"] == sid)


def _arm(e4: dict, sub: str, aid: str) -> dict:
    return next(a for a in e4["exp" + sub.lower()]["arms"] if a["id"] == aid)


def _cfg():
    return config_mod.load_config()


def _p3():
    with open(ROOT / "config" / "phase3_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _sumo():
    return ROOT / "sim" / "sumo" / "canonical.sumocfg"


def _make_runner(sub, arm, scenario, tmp_path, manager_kind="B1"):
    cfg = _cfg()
    e4 = _load_e4()
    p3 = _p3()
    mgr = make_manager(manager_kind, cfg, p3)
    rd = Path(tmp_path) / sub
    rd.mkdir(parents=True, exist_ok=True)
    cls = {"4A": Experiment4Runner, "4B": Experiment4BRunner,
           "4C": Experiment4CRunner}[sub]
    return cls(cfg, e4, sub, arm, scenario, mgr, _sumo(), rd, 20240601,
               phase3_config=p3)


# ---------------------------------------------------------------------------
def test_config_wellformed(tmp_path=None):
    e4 = _load_e4()
    assert int(e4["version"]) == 2
    for sub in ("4A", "4B", "4C"):
        blk = e4["exp" + sub.lower()]
        assert blk["managers"] == ["B0", "B1", "B2", "B4b"]
        assert len(blk["arms"]) >= 5
    # 4A arms are observation intervals; 4C arms are total fleet sizes.
    assert [a["id"] for a in e4["exp4a"]["arms"]] == ["OBS10", "OBS30", "OBS60", "OBS120", "OBS300"]
    assert [a["obs_interval_s"] for a in e4["exp4a"]["arms"]] == [10, 30, 60, 120, 300]
    assert [a["id"] for a in e4["exp4c"]["arms"]] == ["N05", "N10", "N20", "N30", "N50"]
    # scenarios carry a failure block (4A non-aligned t=371; 4B/4C t=360)
    assert _scenario(e4, "E4_REFRESH")["failure"]["time_s"] == 371
    assert _scenario(e4, "E4_ANCHOR")["failure"]["time_s"] == 360
    assert _scenario(e4, "E4_INPUT")["failure"]["time_s"] == 360


def test_seeds_wellformed(tmp_path=None):
    with open(ROOT / "config" / "experiment4_seeds.yaml", encoding="utf-8") as f:
        seeds = yaml.safe_load(f)
    assert len(seeds["primary_seeds"]) == 20
    assert len(seeds["pilot_seeds"]) == 3
    assert len(set(seeds["primary_seeds"])) == 20
    assert all(isinstance(s, int) for s in seeds["primary_seeds"])


def test_distractors_deterministic_and_seed_sensitive(tmp_path=None):
    cfg = _cfg()
    e4 = _load_e4()
    scale = _scenario(e4, "E4_INPUT")["scale"]
    d1 = generate_distractors(cfg, 6, random.Random(20240601), scale)
    d2 = generate_distractors(cfg, 6, random.Random(20240601), scale)
    d3 = generate_distractors(cfg, 6, random.Random(20240602), scale)
    assert d1 == d2, "distractors must be deterministic per seed"
    assert d1 != d3, "distractors must change with seed"


def test_distractors_inert(tmp_path=None):
    """Distractors are UNAVAILABLE / not commandable / incompatible and never
    change the viable (legal) candidate set."""
    cfg = _cfg()
    e4 = _load_e4()
    scale = _scenario(e4, "E4_INPUT")["scale"]
    d = generate_distractors(cfg, 6, random.Random(20240601), scale)
    assert d["n_distractor"] == 6
    assert len(d["distractor_aircraft"]) == 6
    assert len(d["distractor_missions"]) == 6
    assert len(d["distractor_sites"]) == scale["distractor_site_count"]
    for ac in d["distractor_aircraft"]:
        assert ac["status"] == "UNAVAILABLE"
        assert ac["commandable"] is False
        assert ac["reassignable"] is False
        # incompatible with every core landing site (V1..V3)
        assert not (set(ac["landing_site_compatibility"]) & {"V1", "V2", "V3"})
        assert ac["remaining_endurance_s"] == 0.0
    for m in d["distractor_missions"]:
        assert m["priority"] == "LOW"


def test_distractor_counts_match_arms(tmp_path=None):
    from orchestrator.fleet import FLEET
    cfg = _cfg()
    e4 = _load_e4()
    scale = _scenario(e4, "E4_INPUT")["scale"]
    base = len(FLEET)
    for arm in e4["exp4c"]["arms"]:
        n = int(arm["fleet_n"])
        d = generate_distractors(cfg, n - base, random.Random(20240601), scale)
        assert d["n_distractor"] == n - base


def test_runner_construction_and_arm_state(tmp_path):
    e4 = _load_e4()
    r4a = _make_runner("4A", _arm(e4, "4A", "OBS30"), _scenario(e4, "E4_REFRESH"), tmp_path)
    assert r4a.sub == "4A" and r4a.obs_interval_s == 30
    assert r4a.arm_id == "OBS30"
    assert r4a.failure_t == 371

    r4b = _make_runner("4B", _arm(e4, "4B", "D10"), _scenario(e4, "E4_ANCHOR"), tmp_path)
    assert r4b.sub == "4B" and r4b.delay_s == 10
    assert r4b.obs_interval_s == 0  # live-state (Mode A/B frozen) pipeline

    r4c = _make_runner("4C", _arm(e4, "4C", "N10"), _scenario(e4, "E4_INPUT"), tmp_path)
    assert r4c.e4_n_distractor == 6
    assert r4c.e4_n == 10
    # distractor sites injected into facilities before the frozen machinery built
    assert all(f"DX{i}" in r4c.cfg["facilities"] for i in range(1, 7))


def test_full_task_periodic_trigger(tmp_path):
    """E3-v2 fix: secondary WAITING mission must still trigger periodic."""
    r = Experiment4Runner.__new__(Experiment4Runner)
    r.t = 450
    r.critical_t = 300
    r.periodic_s = 30
    r.obs_interval_s = 0
    from types import SimpleNamespace
    r.registry = SimpleNamespace(missions={
        "primary": SimpleNamespace(status="COMPLETED"),
        "secondary": SimpleNamespace(status="WAITING"),
    })
    assert r._periodic_due() is True


def test_4a_observation_polling(tmp_path):
    """Observation-tick polling: extra calls grow as 1/interval."""
    from types import SimpleNamespace
    e4 = _load_e4()
    r = Experiment4Runner.__new__(Experiment4Runner)
    r.critical_t = 300
    r.registry = SimpleNamespace(missions={"m": SimpleNamespace(status="EN_ROUTE")})
    counts = {}
    for arm in e4["exp4a"]["arms"]:
        r.obs_interval_s = arm["obs_interval_s"]
        n = 0
        for t in range(301, 900):
            r.t = t
            if r._periodic_due():
                n += 1
        counts[arm["id"]] = n
    assert counts["OBS10"] > counts["OBS30"] > counts["OBS60"] > counts["OBS120"] > counts["OBS300"]


def test_4b_deferral_and_versioning(tmp_path):
    e4 = _load_e4()
    r = _make_runner("4B", _arm(e4, "4B", "D10"), _scenario(e4, "E4_ANCHOR"), tmp_path)
    decision = {"decision_id": "D001", "simulation_time": 300}
    raw = {"type": "DISPATCH", "aircraft_id": "M-UAV-02",
           "mission_id": "M-CRITICAL-001", "target_site": "V1", "route": ["V1"]}
    norm = dict(raw)
    r._apply_valid_action(300, decision, raw, norm)
    assert len(r.pending_actions) == 1
    assert r.pending_actions[0]["execute_t"] == 310
    assert r.pending_actions[0]["version"] == 1

    # a second decision for the SAME mission supersedes the first (version 2).
    decision2 = {"decision_id": "D002", "simulation_time": 305}
    r._apply_valid_action(305, decision2, raw, norm)
    assert len(r.pending_actions) == 1
    assert r.pending_actions[0]["version"] == 2
    assert r.pending_actions[0]["decision"]["decision_id"] == "D002"


def test_4b_idempotency(tmp_path):
    reg = Registry()
    m = Mission("primary", "medical_blood", "CRITICAL", "V2", "V1", deadline_s=480)
    m.mode = "GROUND"
    reg.add_mission(m)
    r = Experiment4BRunner.__new__(Experiment4BRunner)
    r.registry = reg
    # already in ground transport -> a repeated GROUND_FALLBACK is no longer needed
    assert r._action_no_longer_needed({"type": "GROUND_FALLBACK", "mission_id": "primary"}) is True
    # a fresh AIR dispatch for an unassigned mission is still needed
    m2 = Mission("s2", "medical_blood", "CRITICAL", "V2", "V1", deadline_s=480)
    m2.mode = "AIR"
    reg.add_mission(m2)
    assert r._action_no_longer_needed({"type": "DISPATCH", "mission_id": "s2",
                                       "aircraft_id": "M-UAV-01"}) is False


def test_4b_time_slice_order(tmp_path):
    """Events at time t are applied BEFORE pending actions due at the same t."""
    from types import SimpleNamespace
    r = Experiment4BRunner.__new__(Experiment4BRunner)
    r.t = 359
    r.audit_snapshot_times = []
    r.obs_interval_s = 0
    order = []
    r._apply_scheduled_events = lambda t: order.append(("events", t))
    r.sumo = SimpleNamespace(step=lambda: None)
    r.bs = SimpleNamespace(step=lambda: None, state=lambda: {})
    r._collect_ground = lambda t: {}
    r._update_registry = lambda a: None
    r._process_ground_fallbacks = lambda t: None
    r._log = lambda *a: None
    r._refresh_observation_if_due = lambda t: None
    r._process_pending_actions = lambda t: order.append(("pending", t))
    r._step_once()
    assert order == [("events", 359), ("pending", 359)]


def test_analysis_helpers(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import analyze_experiment4 as A
    # constant shift -> undefined (never 0); identical -> 0
    assert A._cohens_d([110] * 20, [100] * 20) is None
    assert A._cohens_d([100] * 20, [100] * 20) == 0.0
    # all-zero-pair Wilcoxon -> p = 1 (not NaN)
    assert A._wilcoxon_paired([1] * 20, [1] * 20) == 1.0
    # McNemar directional discordance
    p = A._mcnemar([1, 1, 1, 1, 0], [0, 0, 0, 0, 0])
    assert p is not None and 0.0 < p < 1.0
    # Holm is monotone and bounded
    adj = A._holm([0.001, 0.01, 0.05, 0.9])
    assert all(0.0 <= x <= 1.0 for x in adj)
    assert adj == sorted(adj)
