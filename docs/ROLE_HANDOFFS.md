# Role handoffs and execution policy

This is the compact authority and collaboration contract for the four Skills. Keep one persistent Orchestrator; invoke specialists only at meaningful boundaries.

## Authority

| Role | Decides | May recommend | Must not change |
|---|---|---|---|
| Orchestrator | stage, Claim/EQ, Envelope, Card, priority, budget, Gate proposal, stop/freeze | research actions | user-only Gate approval, budget expansion, Spine change, unfreeze |
| Runner | bounded engineering choices inside an approved Card | feasibility/debug facts | scientific scope, priority, budget, stop condition, verdict |
| Result Auditor | signs an independent result verdict and Diagnosis | finite next action | code, method, queue, stage, Claim status |
| Venue Audit | signs venue-gap observations | evidence-completion candidates | Spine, Claim, method, queue |

When instructions conflict, apply this order: user Gate decision -> `Research Spine.md` -> `research/research_state.yaml` decision state -> approved contract/Card -> `AGENTS.md` -> shared protocols -> role Skill. A lower layer reports a conflict instead of repairing a higher layer.

## Minimal packets

- Orchestrator -> Runner: state revision, approved Card path/hash, contract path/version, allowed files/dimensions, budget reservation, completion contract.
- Runner -> Auditor: Card and contract references, immutable run-manifest path, raw metrics/log/artifact references, execution exceptions. Start a fresh isolated context when the runtime supports it, and do not include a desired scientific verdict.
- Auditor -> Orchestrator: signed result path, validity/fairness, result type, Claim impact, confidence, unresolved confounds, failure class, one finite recommendation.
- Venue Audit -> Orchestrator: dated source set, inclusion logic, stable gap matrix, uncertainty, ranked recommendations.

## Blind-first audit

The Auditor fixes its first verdict before reading the Orchestrator's interpretation or preferred story. It records whether planner expectations were withheld, which raw inputs were inspected, and which deterministic checks passed. If isolation is impossible, record an exception reason and classify the audit as a full-context exception; it remains outside formal Claim Evidence until replaced by a blind or independently reviewed record.

## Parallelism

Parallelize only approved, dependency-independent execution units such as seeds, datasets, or separate Cards whose shared writes do not overlap. Keep stage, Claim, priority, budget, Gate, method-selection and stopping decisions serial under the Orchestrator. Each worker writes to its own run directory; shared state updates use expected revisions and are serialized.

## Interaction and stopping

Routine ambiguity inside an approved Card is resolved with a documented conservative assumption. Ask the user only at existing Human Gates, budget/Spine/primary-Claim risk, or when an assumption would alter scientific meaning. Do not add tests or runs after the Card acceptance or rejection condition is decided unless the Orchestrator names the remaining evidence gap and approves the cost.
