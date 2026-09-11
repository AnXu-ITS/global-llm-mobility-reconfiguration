# Experiment 2 — Representative Case Studies (protocol §35)

## CASE-A — simple resource failure  (E2_F1_C1, seed 20240601)

### B0

- failure: F1 on L-UAV-01 at t=360; local contingency: {"aircraft_id": "L-UAV-01", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=2, post=2 (as_if_needs_replan); ground feasible=True eta=181.763
- timeline: t=300 GROUND_FALLBACK_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 GROUND_FALLBACK_STARTED ; t=375 CONTINGENCY_LANDED ; t=482 GROUND_FALLBACK_COMPLETED ; t=542 GROUND_FALLBACK_COMPLETED
- decisions (t, proposed type, result): [(300, 'GROUND_FALLBACK', 'ISSUED'), (360, 'GROUND_FALLBACK', 'ISSUED')]
- outcome: affected=False recovery=False(None) recovery_time=None s, completion_t=482 (time 182 s), deadline violation=True, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B1

- failure: F1 on L-UAV-01 at t=360; local contingency: {"aircraft_id": "L-UAV-01", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=1, post=1 (as_if_needs_replan); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 MISSION_STARTED ; t=375 CONTINGENCY_LANDED ; t=389 MISSION_COMPLETED ; t=410 MISSION_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'REASSIGN', 'ISSUED')]
- outcome: affected=False recovery=False(None) recovery_time=None s, completion_t=410 (time 110 s), deadline violation=False, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B2

- failure: F1 on L-UAV-01 at t=360; local contingency: {"aircraft_id": "L-UAV-01", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=1, post=1 (as_if_needs_replan); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 MISSION_STARTED ; t=375 CONTINGENCY_LANDED ; t=389 MISSION_COMPLETED ; t=410 MISSION_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'REASSIGN', 'ISSUED')]
- outcome: affected=False recovery=False(None) recovery_time=None s, completion_t=410 (time 110 s), deadline violation=False, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B4b

- failure: F1 on L-UAV-01 at t=360; local contingency: {"aircraft_id": "L-UAV-01", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=1, post=1 (as_if_needs_replan); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 GROUND_FALLBACK_STARTED ; t=375 CONTINGENCY_LANDED ; t=410 MISSION_COMPLETED ; t=542 GROUND_FALLBACK_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'GROUND_FALLBACK', 'ISSUED')]
- outcome: affected=False recovery=False(None) recovery_time=None s, completion_t=410 (time 110 s), deadline violation=False, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

---

## CASE-B — critical-chain failure with backup  (E2_F1_C2, seed 20240601)

### B0

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=2, post=1 (as_if_needs_replan); ground feasible=True eta=181.763
- timeline: t=300 GROUND_FALLBACK_STARTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=438 CONTINGENCY_LANDED ; t=482 GROUND_FALLBACK_COMPLETED
- decisions (t, proposed type, result): [(300, 'GROUND_FALLBACK', 'ISSUED')]
- outcome: affected=False recovery=False(None) recovery_time=None s, completion_t=482 (time 182 s), deadline violation=True, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B1

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=1, post=1 (decision_table); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 MISSION_STARTED ; t=379 CONTINGENCY_LANDED ; t=420 MISSION_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'REASSIGN', 'ISSUED')]
- outcome: affected=True recovery=True(AIR) recovery_time=0 s, completion_t=420 (time 120 s), deadline violation=False, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B2

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=1, post=1 (decision_table); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 MISSION_STARTED ; t=379 CONTINGENCY_LANDED ; t=420 MISSION_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'REASSIGN', 'ISSUED')]
- outcome: affected=True recovery=True(AIR) recovery_time=0 s, completion_t=420 (time 120 s), deadline violation=False, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B4b

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=2 (t300 table), pre-asif=1, post=1 (decision_table); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 MISSION_STARTED ; t=379 CONTINGENCY_LANDED ; t=420 MISSION_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'REASSIGN', 'ISSUED')]
- outcome: affected=True recovery=True(AIR) recovery_time=0 s, completion_t=420 (time 120 s), deadline violation=False, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

---

## CASE-C — low-redundancy forced ground fallback  (E2_F1_C3, seed 20240601)

### B0

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=1 (t300 table), pre-asif=1, post=0 (as_if_needs_replan); ground feasible=True eta=181.763
- timeline: t=300 GROUND_FALLBACK_STARTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=438 CONTINGENCY_LANDED ; t=482 GROUND_FALLBACK_COMPLETED
- decisions (t, proposed type, result): [(300, 'GROUND_FALLBACK', 'ISSUED')]
- outcome: affected=False recovery=False(None) recovery_time=None s, completion_t=482 (time 182 s), deadline violation=True, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B1

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=1 (t300 table), pre-asif=0, post=0 (decision_table); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 GROUND_FALLBACK_STARTED ; t=379 CONTINGENCY_LANDED ; t=542 GROUND_FALLBACK_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'GROUND_FALLBACK', 'ISSUED')]
- outcome: affected=True recovery=True(GROUND) recovery_time=0 s, completion_t=542 (time 242 s), deadline violation=True, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B2

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=1 (t300 table), pre-asif=0, post=0 (decision_table); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 GROUND_FALLBACK_STARTED ; t=379 CONTINGENCY_LANDED ; t=542 GROUND_FALLBACK_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'GROUND_FALLBACK', 'ISSUED')]
- outcome: affected=True recovery=True(GROUND) recovery_time=0 s, completion_t=542 (time 242 s), deadline violation=True, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

### B4b

- failure: F1 on M-UAV-02 at t=360; local contingency: {"aircraft_id": "M-UAV-02", "mode": "RETURN", "reason": "civil-UAS lost-link return-to-base (local, manager-independent)", "target_site": "V3"}
- candidate set: pre=1 (t300 table), pre-asif=0, post=0 (decision_table); ground feasible=True eta=181.763
- timeline: t=300 MISSION_STARTED ; t=360 MISSION_INTERRUPTED ; t=360 C2_LOST ; t=360 LOCAL_CONTINGENCY ; t=360 GROUND_FALLBACK_STARTED ; t=379 CONTINGENCY_LANDED ; t=542 GROUND_FALLBACK_COMPLETED
- decisions (t, proposed type, result): [(300, 'DISPATCH', 'ISSUED'), (360, 'GROUND_FALLBACK', 'ISSUED')]
- outcome: affected=True recovery=True(GROUND) recovery_time=0 s, completion_t=542 (time 242 s), deadline violation=True, service damage=0, post-failure rejected=0 (0 failure-related), failed-resource reselection=0

---

