# Evidence Completion protocol

Use the role views and source expansion rules in `docs/CONTEXT_POLICY.md`. Evidence aggregation and Freeze must inspect all required results and unresolved gaps, including counter-evidence; a bounded navigation view or successful hash check does not establish sufficiency. Keep existing eligibility, independent-audit and readiness gates intact.

Read this protocol after the Method is converged and P0 formal results exist.

## Artifact chain

```text
Formal Result Records
-> Claim-Evidence Matrix
-> Claim gaps + Venue gaps
-> Evidence Completion Queue
-> approved P1 / selected P2 Cards
-> Readiness
-> Gate 3
-> Evidence Freeze
-> Final Experiment Report
```

`research/research_state.yaml` stores only paths and the current Method, Claim, Evidence and Submission states. Full evidence remains in `experiments/` and `evidence/`.

## Formal evidence eligibility

Only a registered scientific Card with `paper_evidence_eligible: true`, a complete run manifest, and a blind-first persisted Result Record labeled `FORMAL_CLAIM_EVIDENCE` may enter the matrix. Cheap Evaluation and Tuning remain design history only. Never copy or relabel a preliminary result to bypass this rule.

## Sufficiency

Assess each Claim on Directness, Validity, Consistency and Confound Control. Do not average them. Missing primary evidence, invalid evaluation, unfair baseline, or missing explicitly required evidence makes the Claim `INSUFFICIENT`. Method convergence never implies Claim support or submission readiness.

## Completion queue

Rank a gap using only Claim relevance, reviewer risk, expected information gain and estimated cost. Claim relevance dominates venue commonality. P1 is the default execution recommendation, but still requires an approved Experiment Card, budget and Registry activation. P2 is conditional on ROI/budget. P3 and SKIP never auto-execute.

Supporting evidence does not reopen Method Search. Reopening is recommended only when valid formal evidence clearly contradicts a primary Claim; the existing Method Search reopen and user-risk rules still apply.

## Venue audit

Audit 5-10 recent highly relevant papers and stop once core expectations, material gaps and high-ROI actions are stable. Record sources, inclusion/relevance and uncertainty. Venue evidence may change supporting evaluation or presentation, but never the Research Spine, Primary Claim or Method.

## Readiness and Freeze

Hard gates are: primary evidence exists, evaluation is valid, baselines are fair and results are reproducible. Any failure yields `NOT_READY`. Otherwise report A/B/C/D diagnostically, without an aggregate score.

Evidence Freeze requires Gate 3 user approval, readiness A/B, and no unresolved P1 execution recommendation. Freeze stops ordinary experiment activation. Evidence already sufficient for the declared Claims is itself a stopping reason; optional novelty exploration remains backlog rather than delaying Freeze. Unfreezing remains an explicit user decision with a reason.

## Interaction format

Default progress messages are concise:

```text
Current Stage
Current Finding
Decision
Next Action
```
