"""Experiment-2 additive aircraft state transitions (E2-EXT-STATE-1).

The frozen registry state machine (`orchestrator/registry.py`) has no
AVAILABLE -> DEGRADED / AVAILABLE -> CONTINGENCY transition, but the F1 / F2
failure families can hit an IDLE aircraft (e.g. B0 never dispatched M-UAV-02,
so C2 Lost on M-UAV-02 must still move it to CONTINGENCY; a GNSS zone can
degrade the idle backup M-UAV-01).

This module implements ONLY those two additive transitions. The frozen state
machine is not modified. The transitions are applied exclusively by the
Experiment-2 failure injectors, are manager-agnostic, and are recorded with the
`E2-EXT-STATE-1` marker in the failure trace (EXPERIMENT2_PROTOCOL_EXTENSIONS.md).
"""
from __future__ import annotations

from typing import Any

# additive transitions allowed by E2-EXT-STATE-1 (source -> allowed new states)
E2_ADDITIVE_TRANSITIONS = {
    "AVAILABLE": {"DEGRADED", "CONTINGENCY"},
}

EXT_MARKER = "E2-EXT-STATE-1"


def apply_transition(aircraft: Any, new_status: str) -> str:
    """Apply a state transition, using the additive E2 table when needed.

    Returns "frozen" when the frozen transition() call succeeded, or
    EXT_MARKER when the additive table was used. Raises on anything else.
    """
    from orchestrator.registry import StateMachineError
    try:
        aircraft.transition(new_status)
        return "frozen"
    except StateMachineError:
        allowed = E2_ADDITIVE_TRANSITIONS.get(aircraft.status, set())
        if new_status in allowed:
            aircraft.status = new_status
            return EXT_MARKER
        raise
