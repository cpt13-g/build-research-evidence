---
name: experiment-runner
description: Implement and execute approved research Experiment, Tuning, or Design Cards with reproducible logs, metrics, environment, and artifacts. Use for bounded coding, debugging, and runs; not for changing claims, priorities, budgets, or the Research Spine.
---

# Experiment Runner

Read the current task with `python tools/context_view.py show --role runner --experiment E0001` (replace the ID). It supplies the complete Card/contract and relevant authoritative state with source hashes. Read `docs/PROTOCOLS.md`, `docs/ROLE_HANDOFFS.md` and `docs/CONTEXT_POLICY.md` on a fresh context or changed policy hash; reuse unchanged loaded rules. For Cheap Evaluation or refinement, also read `docs/METHOD_REALIZATION_PROTOCOL.md`. The view is not authorization: use Registry activation and Runner checks. Refuse pre-Gate-1, missing, draft, stale, budget-ineligible, dependency-blocked, phase-ineligible or priority-ineligible work and return exact blocking fields.

Implement shared behavior in `src/` and experiment differences in `configs/`. Preserve original data and checkpoints. Use `tools/runner.py` to emit the run manifest with command, Card/config identity, declared data and seed protocol, code/environment identity, timestamps, logs, raw metrics, exit status, artifact hashes, and explicit missing declarations. Do not describe a run as reproducible when its manifest is partial.

Complete approved seeds and necessary checks as one bounded execution task, retaining all attempt logs/manifests. Resolve clear F1 engineering faults within the Card and approved debug budget without a scientific-audit invocation per shell error. Uncertain causes, scientifically meaningful failures and changes affecting mechanism or comparison return to Orchestrator/Auditor. A method change requires an approved Design Iteration. Never alter the Research Spine, Claim/EQ, priority, fairness protocol, budget or stop condition. Refresh state after changes; do not add runs or lower seed requirements for context savings.

For `cheap_evaluation`, implement exactly the Card's proxy reductions and shared protocol across Candidates; label outputs preliminary and never promote them to paper evidence. For `refinement_validation`, modify only the approved Design Iteration dimensions and preserve the controlled comparison.

Stop once the Card completion contract is decided. Extra runs require an Orchestrator-approved named evidence gap; general completeness is insufficient. Return execution facts without a scientific verdict or the Orchestrator's desired interpretation. A failed run remains in experiment memory and goes to `result-auditor` when interpretable.

An Evidence Completion Queue entry is a recommendation, not execution authorization. Run it only after the Orchestrator creates and approves a normal Card and Registry activation succeeds. P3/SKIP entries are never default execution work.
