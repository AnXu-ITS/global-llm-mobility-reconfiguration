# Conference manuscript revision: 16 October 2026

Paper: **A Ground-Low-Altitude Mobility Manager for Service Reconfiguration under Disruptions**.

This companion archive supports the revised eight-page main manuscript. Supplementary material is hosted here because the conference submission does not provide a separate supplementary-file field. The submitted manuscript contains the essential method, experimental definitions, quantitative results and limitations; this archive provides extended evidence rather than a substitute for those elements.

## Changes to the main manuscript

1. Figure 1 now combines a service-level ground/air choice, a real archived candidate example and the shared selection/revalidation loop. The example uses Suzhou, seed 20240601, a decision at 300 s and a deadline at 600 s. Ground ETA is 228.617 s, while air ETA is 212.823 s; only air displaces an incumbent.
2. Figure 3 restores the E1 matched first-decision comparison previously relegated to Supplementary Figure S7. Among states where air is faster and preemptive but ground remains timely, air-selection counts for B1/B2/B4b are 20/20, 0/20, 12/20 at A; 60/60, 60/60, 57/60 at B; and 20/20 for all three at C. These are descriptive counts, not independently sampled states or real-world frequencies.
3. The methods distinguish aircraft endurance margin from mission deadline margin, retain the original B2 objective, and clarify that the injected execution wait is not added to B2's fixed ranking formula.
4. Current-state revalidation, active-command versions, identical-command due-time preservation, supersession and independent local contingencies are explained in the main text.
5. E3 and E4C are shortened to make room for the interface and decision evidence. E2/E4 emergency windows, E2 fault contexts, fixed-panel seed-block inference and final-state incumbent-damage definitions remain explicit.
6. The main text retains the ETA-timer abstraction, missing physical payload transfers and the limits of reconstructing historical trajectories. The language model is not presented as consistently superior to the heuristic.

## Evidence and version scope

No new SUMO, BlueSky or language-model cohort was executed for this manuscript revision. The statistical estimands and historical experiment results were not changed. New figure layouts reorganize existing evidence. Figure 2 uses the exact numerical values in the supplied `itsac/figures/e1_results_data.json`; the candidate example and selection matrix are retained from the archived manuscript and decision-regime evidence.

The 20-page [supplement PDF](ITSAC_Supplement.pdf) is unchanged from the author's submission package:

- Size: 1,792,875 bytes.
- SHA-256: `c4f65ae9d2a06d90cb530e1f9c9000960ba82070ff5b81b4920b2d250a6a98b3`.
- Git blob: `eb17732a42e78f8f1b75736cdcbf88dff64e57e7`.

Its figure numbering remains S1-S9 and table numbering remains S1-S20. In particular, revised main Figure 3 draws on Supplementary Figure S7; revised main Figure 1 is not the archived conceptual overview in S4.

## Which manuscript is current?

The author-facing revised deliverables are `ITSAC_LNEE_8pages_Revised.docx` and `ITSAC_LNEE_8pages_Revised.pdf`. Their editable source and figure assets are supplied in the revised submission ZIP. The older `../ITSAC_LNEE_8pages.docx` and `../ITSAC_LNEE_8pages.pdf` in this repository are the preceding compression draft and have not been replaced by this supplement update. Use the manuscript submitted through the conference system as the authoritative main paper.

The `main` branch is a later research direction and was not changed. This paper uses only the `itsac-restored-20261016` branch.

## Reproducibility boundary

The archive provides 11,140 per-run metric records, restored implementation/configuration files and an offline numerical verifier. Full historical `runs/` and `outputs/` directories are not recovered. Recomputing statistics from saved metrics is not equivalent to reconstructing raw trajectories or rerunning the original language-model service. The existing verification report records the previous 879 numerical checks; those checks are not newly claimed as executed by the manuscript-formatting revision.
