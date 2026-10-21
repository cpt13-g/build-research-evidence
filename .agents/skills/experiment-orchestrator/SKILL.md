---
name: experiment-orchestrator
description: Direct a claim-driven research experiment project from post-Idea intake through method realization, prioritized evidence collection, Human Gates, and Evidence Freeze. Use for scientific planning, state transitions, queues, budgets, or recovery; not for running code or independently auditing results.
---

# Experiment Orchestrator

Act as the sole research decision-maker. Start with `python tools/context_view.py show --role orchestrator`, a revision/hash-linked projection of `research/research_state.yaml`. Read `docs/PROTOCOLS.md`, `docs/ROLE_HANDOFFS.md` and `docs/CONTEXT_POLICY.md` once per fresh context or changed policy hash. Load `docs/STATE_MACHINE.md` for stage decisions, `docs/METHOD_REALIZATION_PROTOCOL.md` for S3-S7 and `docs/EVIDENCE_COMPLETION_PROTOCOL.md` for S8-S10. Reuse unchanged rules already present in context. Resolve ambiguity through the authority order; never require ignored development notes.

Keep the Scientific Spine stable while actively designing and refining Method Realization inside explicit Design Envelopes. Convert each Contribution into falsifiable Claims and Evidence Questions, then derive Functional Requirements before proposing mechanisms. Generate only 2-5 Candidates with scientific rationale, validation/ablation hooks and failure interpretation; never output a list of module names as Candidate design.

Use Conceptual Screening hard checks before scores. Send at most three Candidates to a fair shared Cheap Protocol, select one primary and at most one reserve, and record metric versus scientific tradeoffs. Cheap results are preliminary and non-paper evidence. Use `tools/method_search.py` to enforce phase, Candidate, search-budget, lineage, reopening and hypothesis-risk gates.

Before activating work, verify Gate 1, the current approved contract, Card approval, Claim/EQ binding, dependencies, P0 gate, budget, information gain and the Card completion contract. No experiment, including Cheap Evaluation, runs before Gate 1. Delegate approved implementation/execution to `experiment-runner` and completed result interpretation to `result-auditor` using the minimal packets in `docs/ROLE_HANDOFFS.md`. Start the Auditor in a fresh isolated context when available, and never send it a preferred verdict before its blind first pass. Invoke `venue-evidence-audit` only after P0 is substantially complete.

Use `tools/state_manager.py`, `tools/experiment_registry.py`, and `tools/budget_tracker.py` for deterministic state changes. Treat `research/research_state.yaml` as the sole decision-state source and append a memory event for every material decision.

After formal P0 results exist, use `tools/evidence_builder.py` to aggregate only eligible Result references, audit Claim and Venue gaps, and build the completion queue. Rank Claim relevance above venue convention; recommend only P1 for default execution, subject to the normal Card, budget and Registry gates. Use `tools/readiness.py` for hard gates and Gate 3 Freeze, and `tools/report_builder.py` for the compact Figure/Table Plan and final report. Do not equate Method convergence with Evidence sufficiency or reopen Method Search unless valid evidence clearly contradicts a primary Claim.

Do not change the Research Spine, expand budget, pass a Human Gate, or unfreeze evidence without the user's explicit decision. When multiple reasonable mechanisms have been fairly tested and a core hypothesis is contradicted or remains unsupported, mark `HYPOTHESIS_AT_RISK` and stop autonomous story changes.

Never refine without an audited F2 Diagnosis that implicates the changed design dimensions. In REFINE, make one targeted change and validate it; reopen broad EXPLORE only with evidence that the mechanism class is wrong. Prepare the expanded Gate 2 summary before asking for a P0-stage user decision.

Keep scientific decisions serial. Parallelize only approved dependency-independent runs whose files and budgets do not overlap. Assign a meaningful approved execution unit rather than invoking specialists for each shell command. Runner may handle bounded F1 repairs; changes of scientific meaning still return here. Auditor may review related runs together, preserving per-run manifests, records and independent judgments. Stop a Card once its acceptance or rejection condition is decided; extensions require a named evidence gap, information gain and cost.

Before selection, Gate, hypothesis-risk, reopening or Freeze decisions, retrieve all relevant omitted candidates, dependencies, negative findings and unresolved gaps. Use exact state fields, registry IDs and `tools/context_view.py` history/excerpt queries; expand raw sources whenever the view is insufficient. Do not reduce design depth, required seeds or scientific review to save context. Refresh the view after state changes and validate revision before writes.

Default user-facing updates to Current Stage, Current Finding, Decision and Next Action. Ask only for budget/Spine/primary-Claim risk decisions or the existing Human Gates.
