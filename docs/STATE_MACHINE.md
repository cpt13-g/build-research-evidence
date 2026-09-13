# State machine transition contract

The normative state descriptions and consistency review are in `docs/IMPLEMENTATION_PLAN.md`. This file defines machine-facing transitions.

```text
S0_INTAKE_RECOVERY -> S1_RESEARCH_VENUE_CONTRACT
S1_RESEARCH_VENUE_CONTRACT -> S2_CLAIM_FORMALIZATION
S2_CLAIM_FORMALIZATION -> S3_METHOD_REALIZATION
S3_METHOD_REALIZATION -> S4_EXPERIMENTAL_PROTOCOL
S4_EXPERIMENTAL_PROTOCOL -> S5_INFRASTRUCTURE_BASELINE  [Gate 1 approved]
S5_INFRASTRUCTURE_BASELINE -> S6_P0_MAIN_EXPERIMENTS
S6_P0_MAIN_EXPERIMENTS -> S7_CLAIM_AUDIT_REFINEMENT
S7_CLAIM_AUDIT_REFINEMENT -> S3_METHOD_REALIZATION       [targeted redesign]
S7_CLAIM_AUDIT_REFINEMENT -> S6_P0_MAIN_EXPERIMENTS     [rerun/refinement]
S7_CLAIM_AUDIT_REFINEMENT -> S8_SUPPORTING_EXPERIMENTS  [Gate 2 approved]
S8_SUPPORTING_EXPERIMENTS -> S9_VENUE_EVIDENCE_AUDIT
S9_VENUE_EVIDENCE_AUDIT -> S8_SUPPORTING_EXPERIMENTS    [approved high-ROI gap]
S9_VENUE_EVIDENCE_AUDIT -> S10_EVIDENCE_FREEZE_REPORT   [Gate 3 approved]
```

Cross-stage flags are `BLOCKED_INPUT`, `BUDGET_EXTENSION_REQUIRED`, `HYPOTHESIS_AT_RISK`, and `EVIDENCE_FROZEN`. They are not additional stages. `EVIDENCE_FROZEN` prevents queue activation until the user approves a documented unfreeze reason.

S3 through S7 use a nested Method Search lifecycle. S3 permits conceptual design and screening; execution begins only after Gate 1, typically with Cheap Evaluation during S5:

```text
NOT_STARTED -> EXPLORE -> SCREEN -> CHEAP_EVALUATE
-> SELECT -> FULL_EVALUATE -> REFINE -> CONVERGED
```

Broad Candidate generation is legal only in EXPLORE. Returning from REFINE/FULL_EVALUATE/CONVERGED to EXPLORE requires evidence, a recorded reason and reopen-search budget.

At S8-S10, use the separate compact statuses `method_status`, `claim_status`, `evidence_status`, and `submission_readiness`. No status implies another. Gate 3 plus readiness A/B and resolution of P1 recommendations permits Evidence Freeze; `EVIDENCE_FROZEN` blocks ordinary Registry activation.
