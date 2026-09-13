# Project agent instructions

`Research Spine.md` is the highest-priority project design specification. Before making research decisions, read `research/research_state.yaml`; do not reconstruct state from chat history when the file exists.

## Invariants

- Keep L1 Scientific Spine stable. Method architecture is L2 and may change inside an approved Design Envelope.
- The Orchestrator is the only role allowed to change stage, queue priority, claims, envelopes, budget decisions, or Human Gate state.
- Do not run a scientific experiment without an `approved` `E####` Experiment Card. Do not present a `T####` tuning result as claim evidence.
- Do not activate any experiment, including Cheap Evaluation, before Gate 1 approves the experiment contract and initial budget.
- P0 blockers may run before P0 completion; P1–P3 remain in backlog until Gate 2 authorizes supporting work.
- Never modify a method without an observation, diagnosis, scientific reason, expected effect, rejection condition, and estimated cost.
- Derive a Functional Requirement and active Design Envelope before proposing Candidate Mechanisms. Broad Candidate generation is limited to EXPLORE.
- Cheap Evaluation is preliminary, uses a fair shared proxy protocol, and cannot enter formal paper evidence.
- Every scientific Card must define a completion contract. Stop when its acceptance or rejection condition is resolved; extensions require a named evidence gap and Orchestrator approval.
- Formal evidence requires a blind-first Result Audit. The first verdict must be formed from the Card, contract, run manifest, raw metrics, logs, and artifacts before seeing the Orchestrator's preferred interpretation.
- Preserve all meaningful positive, negative, null, boundary, confounded, failed, and debugging outcomes in experiment memory.
- Do not increase budget, change the research problem, or unfreeze evidence without explicit user approval.

## State and artifacts

- `research/research_state.yaml` is the sole mutable source of project decision state.
- `templates/research_state.yaml` is initialization material only.
- Raw logs, metrics, checkpoints, and artifacts are immutable evidence files referenced by the state/registry.
- Every run must emit a machine-readable manifest with code/config/data/environment identity and artifact hashes or explicit missing declarations.
- Use `tools/state_manager.py` and `tools/experiment_registry.py` for state changes. Direct edits are reserved for recovery and must be documented in memory.
- Use `tools/method_search.py` for Method Search phase, Candidate, Diagnosis-linked iteration, reopening, lineage and Hypothesis-risk gates.
- Shared research code belongs in `src/`; experiment differences belong in `configs/`. Do not copy the codebase per experiment.

## Skills

- Use `experiment-orchestrator` for project decisions and transitions.
- Use `experiment-runner` only for approved execution and implementation.
- Use `result-auditor` to validate and interpret completed runs.
- Use `venue-evidence-audit` only after P0 is substantially complete and the Orchestrator authorizes it.
- Follow `docs/ROLE_HANDOFFS.md` for authority, context isolation, parallelism, and handoff packets.

Run `python tools/validate_project.py` after changing protocols, templates, Skill references, or state tools.
