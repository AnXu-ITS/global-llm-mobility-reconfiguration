"""Validate historical hashes including one exactly reconstructible metric fix."""
import hashlib,json

NEW = '''            # FIX (review 20260908 P0-5): an unfinished mission that is already past
            # its deadline must count as a violation, not be silently marked on-time.
            "critical_mission_deadline_violation": bool(
                crit and crit.deadline_s is not None and (comp_t is None or comp_t > crit.deadline_s)),'''
OLD = '''            "critical_mission_deadline_violation": bool(comp_t and crit and comp_t > crit.deadline_s),'''

def check_manifest(root,manifest):
    bad=[];transitions=[]
    for name,want in manifest.items():
        p=root/name
        if not p.exists():bad.append(name);continue
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual==want:continue
        text=p.read_text(encoding='utf-8')
        if name=='orchestrator/experiment1_runner.py' and text.count(NEW)==1:
            reconstructed=hashlib.sha256(text.replace(NEW,OLD).encode()).hexdigest()
            if reconstructed==want:
                transitions.append({'path':name,'historical_sha256':want,'current_sha256':actual,
                    'reconstructed_historical_sha256':reconstructed,
                    'change':'Only deadline reporting for missing completion; no executor/scheduler changes.',
                    'provenance':'reports/REVIEW_20260908_ANALYSIS.md section 8; exact reverse patch verified'})
                continue
        bad.append(name)
    return bad,transitions
