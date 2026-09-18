"""Revision overlay: preserve the due time of an identical pending command.

Parent project source and original runs are read-only. Import this subclass
instead of Experiment4BRunner for revised E4B runs.
"""
from orchestrator.experiment4_runner import Experiment4BRunner

class DeduplicatedExperiment4BRunner(Experiment4BRunner):
    def _apply_valid_action(self,t,decision,raw_action,normalized_action):
        for pending in self.pending_actions:
            if pending['normalized_action'] == normalized_action:
                self._write_action_pipeline(t,decision['decision_id'],raw_action,
                                            normalized_action,None,'DUPLICATE_PENDING')
                self._record_action(t,normalized_action.get('type'),
                    normalized_action.get('aircraft_id'),normalized_action.get('mission_id'),
                    normalized_action.get('target_site'),normalized_action.get('route'),
                    'DUPLICATE_PENDING',decision['decision_id'])
                return
        return super()._apply_valid_action(t,decision,raw_action,normalized_action)
