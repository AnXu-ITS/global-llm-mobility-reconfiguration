# BlueSky Dynamics Validation (Provenance)

Verifies that UAV trajectory state is advanced by the **BlueSky simulator**, not
by the Python Hub. New test: `tests/test_bluesky_state_provenance.py` +
`outputs/bluesky_state_provenance.csv`.

## Method

The test bypasses the orchestrator entirely: it initializes `BlueSkyAdapter`,
pushes the canonical scene commands (`DT`/`DEFWPT`/`CRE`/`DEST`/`ALT`/`SPD`), and
then reads aircraft state **directly from the BlueSky runtime traffic object
`bs.traf.lat/lon/alt/tas`** at `t = 0, 30, 60, 90, 120`.

## Results

| aircraft | t=0 → t=120 displacement | interpretation |
|----------|-------------------------:|----------------|
| L-UAV-01 (logistics, BUSY) | 1358.5 m | moving (15 m/s cruise, shuttle) |
| EVTOL-01 (passenger, BUSY) | 3636.8 m | moving (40 m/s cruise, shuttle) |
| M-UAV-02 (medical, parked) | 0.0 m | stationary (ALT 100 / SPD 0) |

The two busy aircraft move; the parked aircraft stays put. This is the expected
physical behaviour and proves positions are produced by BlueSky's dynamics
(nothing is "faked" by a Python-side integrator).

## Code-path audit (Q1–Q3)

Data flow (verified in `orchestrator/`):

```
Orchestrator._collect_air()  ->  self.bs.state()               (bluesky_adapter.py:65)
    BlueSkyAdapter.state()   ->  bs.traf.lat/lon/alt/tas ...     (bluesky_adapter.py:65-79)
Orchestrator._update_registry() -> ac.lat, ac.lon = st[...]      (orchestrator.py:284)
```

- `bs.traf.*` are the BlueSky internal traffic arrays, advanced by
  `bs.sim.step()` (the BlueSky simulation loop), not by any Python computation.
- The orchestrator calls `bs.step()` exactly once per step and only **reads**
  `bs.traf` (via `state()`), then **mirrors** it into the registry
  (`ac.lat, ac.lon = st["lat"], st["lon"]`). The registry is a *cache*, not a
  source of truth.
- `haversine(...)` appears only for *arrival detection* (distance to destination
  vs `ARRIVAL_RADIUS_M`), never to propagate position.

### Q1 — Is aircraft position updated by BlueSky simulation dynamics?

**Yes.** Evidence: `bs.traf` advances (displacement table above) with zero Python
position integration. `tests/test_bluesky_state_provenance.py` reads `bs.traf`
directly.

### Q2 — Does the orchestrator only step / command / collect state?

**Yes.** The orchestrator's air-side responsibilities are: queue commands
(`bs.stack.stack`, via `fly_to`/`park`/`command`), call `bs.step()`, and collect
state via `bs.state()`. No kinematics code exists in the orchestrator.

### Q3 — Is there any Python-Hub position-stepping code?

**No.** A grep for position mutation across `orchestrator/`
(`lat =` / `lon =` / `position` / `velocity` / `.lat =` / `.lon =`) finds only:

- `registry.py:50-51` — initial construction of `Aircraft(lat, lon)` (initial placement).
- `orchestrator.py:121`, `fleet.py:62` — `origin_latlon(config, site)` (initial placement from config).
- `orchestrator.py:284` — registry **mirror** from `st` (= `bs.traf`).
- `orchestrator.py:289` — `haversine` for arrival detection.

No `position += velocity * dt` or equivalent exists.

## Verdict

**PASS** — BlueSky runtime is the authoritative source of UAV trajectory state;
the orchestrator only steps/commands/collects and never self-advances positions.
