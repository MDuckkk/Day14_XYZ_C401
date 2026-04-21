# Failure Analysis Report

## Executive Summary
- Total cases: 50
- Pass/Fail: 47/3
- Failure rate: 6.0%
- Average judge score: 0.8560 / 1.0
- Average judge agreement: 100.00%
- Judge conflicts: 0
- Cohen's kappa: 0.8551
- Judge fallback cases: 0

## Failure Clusters
- HALLUCINATION_OR_REFUSAL: 2 case(s) (66.7%)
- RETRIEVAL_FAILURE: 1 case(s) (33.3%)

## Top Failure Deep Dive
### Failure #1: case_027
- Cluster: HALLUCINATION_OR_REFUSAL
- Score: 0.200
- Question: Compare prompt injection and goal hijacking.

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.200
- Answer: The response diverges from the expected answer content.

#### WHY_2: Why does the response diverge from expectation?
- Observation: Compare retrieved evidence and expected support.
- Answer: Reasoning likely failed: retrieval appears acceptable, but final answer remains weak.

#### WHY_3: Why did retrieval/reasoning fail in this stage?
- Observation: Case type=comparison, difficulty=medium
- Answer: Current prompt/retrieval settings are not specialized by case type.

#### WHY_4: Why are settings not specialized enough?
- Observation: One-size-fits-all defaults across heterogeneous cases.
- Answer: No adaptive strategy or dynamic routing exists for hard/adversarial questions.

#### WHY_5: What is the root cause?
- Observation: System-level behavior pattern from repeated low-score cases.
- Answer: Prompt constraints or confidence policy cause unsupported or over-conservative outputs.

Recommendations:
- Strengthen grounded-answer policy in system prompt.
- Add refusal threshold only when evidence is missing.
- Require citations from retrieved snippets.

---

### Failure #2: case_047
- Cluster: HALLUCINATION_OR_REFUSAL
- Score: 0.400
- Question: How should we improve it?

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.400
- Answer: The response diverges from the expected answer content.

#### WHY_2: Why does the response diverge from expectation?
- Observation: Compare retrieved evidence and expected support.
- Answer: Reasoning likely failed: retrieval appears acceptable, but final answer remains weak.

#### WHY_3: Why did retrieval/reasoning fail in this stage?
- Observation: Case type=edge-case, difficulty=medium
- Answer: Current prompt/retrieval settings are not specialized by case type.

#### WHY_4: Why are settings not specialized enough?
- Observation: One-size-fits-all defaults across heterogeneous cases.
- Answer: No adaptive strategy or dynamic routing exists for hard/adversarial questions.

#### WHY_5: What is the root cause?
- Observation: System-level behavior pattern from repeated low-score cases.
- Answer: Prompt constraints or confidence policy cause unsupported or over-conservative outputs.

Recommendations:
- Strengthen grounded-answer policy in system prompt.
- Add refusal threshold only when evidence is missing.
- Require citations from retrieved snippets.

---

### Failure #3: case_048
- Cluster: RETRIEVAL_FAILURE
- Score: 0.400
- Question: What should we run first?

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.400
- Answer: The response diverges from the expected answer content.

#### WHY_2: Why does the response diverge from expectation?
- Observation: Compare retrieved evidence and expected support.
- Answer: Retrieval likely failed: expected supporting docs were not retrieved.

#### WHY_3: Why did retrieval/reasoning fail in this stage?
- Observation: Case type=edge-case, difficulty=medium
- Answer: Current prompt/retrieval settings are not specialized by case type.

#### WHY_4: Why are settings not specialized enough?
- Observation: One-size-fits-all defaults across heterogeneous cases.
- Answer: No adaptive strategy or dynamic routing exists for hard/adversarial questions.

#### WHY_5: What is the root cause?
- Observation: System-level behavior pattern from repeated low-score cases.
- Answer: Chunking/retrieval configuration is not surfacing relevant evidence.

Recommendations:
- Adopt hybrid retrieval (keyword + vector).
- Tune chunk size and overlap to preserve key facts.
- Add query rewrite for ambiguous user questions.

---
