# Shared research protocols

This file is the shared interface contract for all four skills. Detailed field requirements are enforced by `schemas/`; YAML files in `templates/` are bootstrap examples.

Runtime context is governed by `docs/CONTEXT_POLICY.md`. Use source-linked role views from `tools/context_view.py`, reuse unchanged rules already loaded in the current context, and retrieve relevant raw evidence before scientific decisions. Views do not grant approval, replace independent audit or change the single authoritative state.

## Authority and ownership

| Object | Creates | Approves / mutates decision state | Consumes |
|---|---|---|---|
| Research state | Orchestrator | Orchestrator; user at Human Gates | all skills |
| Functional requirement / envelope / candidate | Orchestrator | Orchestrator | Runner, Auditor |
| Design iteration | Orchestrator drafts; Runner may report feasibility | Orchestrator | Runner, Auditor |
| Experiment/Tuning Card | Orchestrator | Orchestrator | Runner, Auditor |
| Raw run record | Runner | append-only after completion | Auditor, Orchestrator |
| Audit/result interpretation | Result Auditor | Auditor signs; Orchestrator applies decision | Orchestrator |
| Venue gap matrix | Venue Audit | Orchestrator selects recommendations | Orchestrator |
| Claim-Evidence / completion queue / readiness | Orchestrator aggregates; Auditor supplies Result interpretation | Orchestrator; user approves Gate 3 Freeze | all skills |

No skill may silently repair a decision owned by another role. It should return a structured blocking reason. `docs/ROLE_HANDOFFS.md` defines the minimal packet, context isolation, and parallelism rules for each handoff.

## Identifiers and lifecycle

- Scientific experiments: `E####`; tuning/engineering: `T####`; design iterations: `D####`; claims: `C#`; evidence questions: `EQ#` or `P0-EQ#`.
- Card lifecycle: `draft -> approved -> running -> completed|failed -> audited`.
- Contract lifecycle: `draft -> approved -> superseded`.
- State revisions are monotonic integers. A state-changing command should reject a stale expected revision.
- Method artifacts use `FR-*`, `DE-*`, `MC-*`, `CS-*`, `CD-*`, `D####`, and `M#`. Full objects remain outside the state file.

## Queue gate

Before activation, the Orchestrator must establish: Gate 1 approval, an approved current experiment contract, a valid approved Card, Claim/EQ binding for `E####`, dependency completion, priority eligibility, budget availability, and a completion contract. Before Gate 2, only `CORE_P0`, `P0_SUPPORT`, Debug and Tuning work can enter the active queue. There is no pre-Gate-1 execution exception.

## Result handoff

Runner records exit status, timestamps, command, code/config/data/environment identity, logs, raw metrics and artifact hashes or explicit missing declarations in a run manifest. It does not choose a Claim verdict. Auditor first performs a blind review from the Card, contract and raw execution packet without the Orchestrator's preferred interpretation; only after fixing the first verdict may it reconcile diagnoses. It assigns exactly one result type, records performance/scientific value separately, describes Claim impact and confidence, and recommends—not schedules—the next action.

Cheap Evaluation results can never become formal Claim Evidence. Result persistence cross-checks evidence classification against the registered Card.

## Method refinement gate

A design change is executable only when a `design_iteration` record includes an observed problem, diagnosis, proposed change, scientific reason, expected effect, evaluation measure, rejection condition and estimated cost. The change must stay within an active Design Envelope. An F1 execution failure is debugged before it is treated as method evidence.

## Completion contract

Every scientific Card declares the minimum required checks, acceptance condition, rejection condition, and that execution stops once the evidence question is decided. Additional runs require a named unresolved evidence gap, expected information gain, cost, and Orchestrator approval. “More completeness” alone is not a valid extension reason.

For the complete Method Search lifecycle and failure gates, read `docs/METHOD_REALIZATION_PROTOCOL.md`.

## Evidence completion

After P0, formal evidence aggregation, Venue gaps, completion ranking, Readiness and Freeze follow `docs/EVIDENCE_COMPLETION_PROTOCOL.md`. Cheap/Tuning results never enter formal evidence. P1 recommendations still require an approved Card and normal Registry activation; P3 is not an execution recommendation. Method convergence, Claim support, Evidence sufficiency and Submission readiness are separate states.

## Human Gates

- Gate 1 approves Research Spine, Venue, Claims/Evidence Questions, experiment contract and initial budget.
- Gate 2 reviews P0 evidence, Primary Claim status and whether to refine or enter supporting experiments.
- Gate 3 reviews completeness, Venue gaps, remaining high-ROI work and Evidence Freeze.

Only the user can approve a Gate, expand a depleted budget, accept a Research Spine change, or unfreeze evidence.
