# Method Realization protocol

Read this protocol when the current task involves S3 Method Realization, Candidate Search, Cheap Evaluation, Result Diagnosis, Design Iteration, search reopening, or Gate 2 preparation.

Follow `docs/CONTEXT_POLICY.md` to reuse unchanged loaded rules and retrieve only relevant artifacts. Context limits never lower candidate-design quality, mandatory seeds or audit depth. Before selection or reopening, expand the complete relevant candidate set and positive/negative diagnoses; a shortened registry view cannot justify eliminating unseen candidates.

## Permission layers

- L1 Research Spine is stable: Research Question, context, core Hypothesis, Contribution directions, Claims, evaluation goals, task boundary, exclusions and target Venue. Changes require user review.
- L2 Method Realization is adaptive: architecture, modules, representation, fusion, attention, routing, constraints, Loss, decoder, optimization and training mechanisms may change inside an active Design Envelope.
- L3 Engineering is flexible: implementation, hyperparameters, optimizer, data loader, memory optimization, logging and approved parallel execution.

Do not treat L2 choices as part of the frozen Experiment Contract. The contract freezes what is tested and how fairness is maintained.

## Artifact chain

```text
Contribution
-> Functional Requirement
-> Design Envelope
-> 2-5 Candidate Mechanisms
-> Conceptual Screenings
-> fair Cheap Evaluation Cards
-> Candidate Decision
-> Full Evaluation Card
-> structured Diagnosis
-> Design Iteration
-> Refinement Validation
-> Converged Method
```

Full artifacts live below `research/method/`, `experiments/`, and `evidence/`. `research/research_state.yaml` stores only current phase, IDs, paths, counters, budgets and next action.

## Candidate generation and screening

Every Candidate must state the problem addressed, scientific rationale, operational architecture/algorithm, expected intermediate and task effects, controlled baseline difference, validation hook, ablation hook, failure interpretation, risks, complexity, cost, Claim alignment and affected design dimensions.

Generate 2-5 materially distinct Candidates according to uncertainty and budget; stop before five when additional Candidates repeat an existing mechanism class. Conceptual Screening uses hard checks before scores. Reject a Candidate when it conflicts with the Research Spine or Contribution, cannot be validated or compared fairly, exceeds approved budget, or primarily gains through scale. Scores cannot rescue a failed hard check. At most three Candidates enter Cheap Evaluation.

## Cheap Evaluation

Cheap Evaluation is `P0_SUPPORT`, uses an approved `E####` Card, and is always `PRELIMINARY_NON_PAPER`. The Card declares the proxy reduction and proxy risk. Every Candidate in the same decision set uses the same fair Cheap Protocol unless a documented task constraint makes a dimension inapplicable.

Cheap Evaluation runs only after Gate 1 approves the experiment contract and design-search budget. Conceptual generation and screening may occur before Gate 1; execution may not. Method Search may remain in `CHEAP_EVALUATE` while the project advances through S4 into S5.

## Candidate decision

Choose exactly one primary route and at most one reserve. Compare task performance, Claim alignment, scientific interpretability, evidence strength, stability, complexity, compute cost and implementation risk. Do not select by a simple average or final Metric alone; record metric and scientific tradeoffs explicitly.

## Diagnosis and failure classes

Audited results use one result type and a finite recommended action. Diagnose execution validity, convergence, baseline fairness, primary observation, Claim impact, scientific/performance value, confidence, causes and unresolved confounds.

- F1 Execution Failure -> `DEBUG` or `TUNE`; it is not scientific counter-evidence.
- F2 Method Failure -> reject the Candidate or refine inside the Envelope.
- F3 Hypothesis Risk -> only after multiple reasonable, valid and fair Candidates give consistent negative evidence with major confounds resolved. A single Candidate failure cannot trigger it.

## Targeted Refinement

`NO DIAGNOSIS -> NO METHOD CHANGE`.

A Design Iteration must link an audited F2 Diagnosis recommending `REFINE_METHOD`. Its affected design dimensions must be implicated by the Diagnosis, allowed by the active Envelope and included in approved scope. The refinement produces a new Method lineage node and requires a `P0_SUPPORT` refinement-validation Card.

## Convergence and reopening

```text
NOT_STARTED -> EXPLORE -> SCREEN -> CHEAP_EVALUATE
-> SELECT -> FULL_EVALUATE -> REFINE -> CONVERGED
```

REFINE does not permit broad Candidate generation. Reopen EXPLORE only when evidence shows the mechanism class—not merely one parameterization—is unsuitable. Record evidence, reason and budget use. Search/candidate/iteration/reopen counters are negotiable budgets: exhaustion writes a Budget Extension Recommendation and waits for user decision.

## Gate 2

Prepare a structured summary containing Current Method, Method Evolution, Primary Claim Evidence, Candidate Search Summary, selection rationale, remaining uncertainty, experiment and method-search budgets, and potential refinement ROI. The user chooses refinement, acceptance, supporting experiments, or Hypothesis-at-Risk review.
