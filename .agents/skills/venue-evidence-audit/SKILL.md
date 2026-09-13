---
name: venue-evidence-audit
description: Audit recent high-relevance papers from a target venue to identify claim-relevant experimental evidence gaps after core P0 results exist. Use for venue completeness and reviewer-risk analysis; not for redefining the research question or running experiments.
---

# Venue Evidence Audit

Run only when the Orchestrator authorizes the audit and P0 is substantially complete. Read `research/research_state.yaml`, the current Claim-Evidence status, `docs/PROTOCOLS.md`, `docs/ROLE_HANDOFFS.md`, and `docs/EVIDENCE_COMPLETION_PROTOCOL.md`.

Analyze 5-10 recent, highly relevant papers, prioritizing same task, research question, method class, venue and recency. Record search date, sources, relevance, inclusion/exclusion reasons and uncertainty. Stop once core expectations, material gaps and high-ROI actions are stable; do not expand into a systematic review. Compare datasets, baselines, metrics, seed/statistical practice, ablations, sensitivity, robustness, generalization, efficiency, complexity, qualitative analysis and figure/table conventions.

Produce an Evidence Gap Matrix with current status, venue frequency, Claim relevance, reviewer risk, estimated cost, information gain and recommended priority. Recommendations do not enter the queue automatically. A common but Claim-irrelevant experiment is P3/SKIP. Do not alter the Research Spine, Primary Claims or Method, and report any positioning concern only as risk.
