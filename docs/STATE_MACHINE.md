# State machine transition contract

This file is the normative runtime contract for stage meaning, transition guards and cross-stage flags. Runtime behavior must depend only on version-controlled project files; internal implementation plans, local notes and ignored files are never required to operate the agent.

| Stage | Purpose | Required exit condition |
|---|---|---|
| `S0_INTAKE_RECOVERY` | Recover persisted state and identify missing research input without rebuilding decisions from chat history. | State is readable and blocking inputs are explicit. |
| `S1_RESEARCH_VENUE_CONTRACT` | Draft the Scientific Spine, venue target and resource boundary. | Research objective, venue status and budget proposal are explicit. |
| `S2_CLAIM_FORMALIZATION` | Convert contributions into falsifiable Claims and Evidence Questions. | Primary Claims and their evidence questions are testable. |
| `S3_METHOD_REALIZATION` | Derive Functional Requirements and search inside an approved Design Envelope. | A bounded candidate set and screening plan exist. |
| `S4_EXPERIMENTAL_PROTOCOL` | Define fair comparison, completion contracts and initial budget. | Gate 1 approves the contract and budget. |
| `S5_INFRASTRUCTURE_BASELINE` | Validate data, splits, metrics, baselines and candidate feasibility. | Infrastructure checks pass and a primary candidate is selected. |
| `S6_P0_MAIN_EXPERIMENTS` | Execute the minimum core experiments that decide whether the paper's main Claim can stand. | P0 runs are complete, auditable and ready for scientific review. |
| `S7_CLAIM_AUDIT_REFINEMENT` | Audit P0 evidence and permit only diagnosis-linked refinement. | Claim impact and the next bounded action are explicit; Gate 2 decides whether supporting work may start. |
| `S8_SUPPORTING_EXPERIMENTS` | Fill approved Claim-relevant evidence gaps in dependency and value order. | Required P1 evidence is resolved or explicitly waived by the user. |
| `S9_VENUE_EVIDENCE_AUDIT` | Compare existing evidence with current venue expectations without redefining the research problem. | A dated, ranked gap assessment is available. |
| `S10_EVIDENCE_FREEZE_REPORT` | Check readiness, freeze evidence and produce the final experiment handoff. | Gate 3 approves Evidence Freeze and final artifacts are generated. |

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

## Transition guards

- Only the Orchestrator may change the stage or cross-stage flags, using the current state revision and the deterministic state tools.
- S1-S4 form the Gate 1 drafting region. No experiment, including Cheap Evaluation, may run before Gate 1 approves the experiment contract and initial budget.
- Before Gate 2, only P0 work and work explicitly required to unblock P0 may be activated. P1-P3 remain in Backlog.
- A failed run does not itself authorize a stage change or method change. Execution validity is established first; scientific interpretation then comes from a blind-first Result Audit.
- A transition requiring a Human Gate, budget expansion, Scientific Spine change or evidence unfreeze stops until the user explicitly decides.
- Every transition records its reason and expected revision in `research/research_state.yaml` and appends the corresponding memory event.

## Ambiguity resolution

Use current role views according to `docs/CONTEXT_POLICY.md`; omitted history is not a completed stage condition. Gate, refinement, risk and Freeze decisions still require all relevant evidence and guards below.

Apply the authority order in `docs/ROLE_HANDOFFS.md`. A routine implementation ambiguity inside an approved Card may use a documented conservative assumption only when it preserves the Card's scientific meaning, controlled variables, budget and completion contract. If an assumption would change any of those, affect a primary Claim, cross a Human Gate or expand scope, stop and request the owning decision instead of searching for an internal planning document or silently inventing policy.
