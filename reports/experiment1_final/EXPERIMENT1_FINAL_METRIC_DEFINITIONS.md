# Experiment 1 Final — Metric Definitions (frozen, Finalization §7)

All metrics are computed **per (scenario, seed, manager) run** from the run
artifacts, and are frozen before the primary rerun. Field names below refer to
`metrics.json` written by `orchestrator/experiment1_runner.py::_metrics`.

Notation: `release_t = 300 s` (mission release), `deadline_s = release_t +
deadline_slack_s` (slack ∈ {180 s CRITICAL, 300 s HIGH}), `comp_t` = simulation
time the critical mission reached a COMPLETED event (from `events.csv`
`MISSION_COMPLETED` / `GROUND_FALLBACK_COMPLETED`).

---

## M1. Critical Mission Completion Time

`critical_mission_completion_time_s = comp_t − release_t` (seconds from release to
completion). Lower = faster. `None` iff the mission did not complete within the
900 s horizon (in this testbed it always completes because ground fallback is
always enabled and 900 s ≫ any ETA; `None` is treated as horizon-censored and
reported separately if it ever occurs).

## M2. Deadline Violation

`critical_mission_deadline_violation = (comp_t > deadline_s)`, a boolean per run.
The **Deadline Violation rate** is the fraction of runs (over the seeds of a
scenario) where it is `True`.

## M3. Existing Service Damage (mathematical definition)

Let `E` = the set of existing (pre-disruption) missions, i.e. every mission with
`id ≠ critical_mission_id`. An existing mission is **damaged** iff its final state
(registry status at shutdown) is in the terminal-disruption set
`{INTERRUPTED, NEEDS_REPLAN, CANCELLED, FAILED}`.

```
ExistingServiceDamage_run = |{ m ∈ E : status(m) ∈ {INTERRUPTED, NEEDS_REPLAN, CANCELLED, FAILED} }|
```

(= `existing_missions_damaged_count`; the ids are `existing_missions_damaged`.)
The **Existing Service Damage rate** for a (scenario, manager) cell is the mean of
`ExistingServiceDamage_run` over the 20 seeds (i.e. expected number of damaged
existing missions per run), or, where a binary damage indicator is more
interpretable, the fraction of runs with `ExistingServiceDamage_run > 0`
(reported explicitly, never conflated).

## M4. Air Intervention Rate

`air_intervention = true` iff at least one **ISSUED** action (from `actions.csv`,
`result=ISSUED`) is of type `DISPATCH` or `REASSIGN` for the critical mission.
(Checker-rejected proposals are NOT interventions — review §7.) The **Air
Intervention Rate** is the fraction of runs with `air_intervention = true`.

## M5. Unnecessary Air Intervention Rate (frozen predicate)

An air intervention is **unnecessary** iff **ALL THREE** conditions hold
(Finalization §7):

1. **Ground could satisfy** — the ground fallback ETA meets the deadline:
   `ground_fallback_eta_s ≤ deadline_slack_s`
   (equivalently `release_t + ground_fallback_eta_s ≤ deadline_s`).
2. **Air provides no material critical benefit** — air does not complete at least
   `θ_time` seconds earlier than ground:
   `ground_fallback_eta_s − critical_mission_completion_time_s < θ_time`.
   **Frozen threshold: `θ_time = 60 s`** (the endurance-margin constant).
3. **Existing air service is interrupted / damaged** — the run issued a `REASSIGN`
   (`reassignment_count > 0`) **or** damaged an existing mission
   (`existing_missions_damaged_count > 0`).

`UnnecessaryAir_run = air_intervention AND (1) AND (2) AND (3)`. The
**Unnecessary Air Intervention Rate** is the fraction of runs where it is `True`.
(A DISPATCH of an *idle* aircraft fails condition 3 and is therefore NOT counted
as "unnecessary" — it is spare-capacity use, not service damage.)

For continuity a secondary "air-when-ground-suffices" rate (condition 1 alone) is
also reported, but it is explicitly labelled as *not* the frozen Unnecessary-Air
metric.

## M6. Time Saving vs B0 (signed)

Per (scenario, seed), paired:
`TimeSaving_vs_B0 = B0.critical_mission_completion_time_s − manager.critical_mission_completion_time_s`.
Positive = manager faster than the no-coordination ground baseline; negative =
slower than ground. Reported as a paired effect (mean ± 95 % CI).

## M7. Reassignment Count

`reassignment_count` = number of ISSUED `REASSIGN` actions (preemptions). Rate =
mean per run over seeds.

## M8. Interrupted Existing Mission Count

`existing_missions_damaged_count` (identical to M3's per-run damage count).
Reported jointly with M3 (they are the same underlying quantity).

## M9. Ground Fallback Rate

Fraction of runs where `critical_mission_final_mode == "GROUND"`
(the critical mission was ultimately served by ground). Complement of air
completion mode; a run may issue air then end in GROUND if the air action was
rejected/aborted, so M9 is defined on **final mode**, not issued actions.

## M10. Disruption Efficiency (frozen)

Signed time saved per unit of existing-service damage, paired per (scenario, seed):

```
DisruptionEfficiency = (B0_completion_time_s − manager_completion_time_s)
                       / (existing_missions_damaged_count + 1)
```

Higher = more critical-mission time saved per unit of service damage; the `+1`
avoids division by zero and makes a damage-free manager's efficiency equal its raw
signed saving. Negative time saving → negative efficiency. Reported as mean ±
95 % CI over seeds.

---

## Statistical-unit note (Finalization §8, §22)

The independent unit is **scenario × simulation seed** (n = 20 per scenario). Each
manager's 20-seed sample is paired across managers on identical (scenario, seed)
initial state. Same-prompt repeats are NOT statistical samples.
