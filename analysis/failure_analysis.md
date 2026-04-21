# Failure Analysis Report

## Executive Summary
- Total cases: 50
- Pass/Fail: 43/7
- Failure rate: 14.0%
- Average judge score: 0.8825 / 1.0
- Average judge agreement: 88.00%
- Judge conflicts: 6
- Cohen's kappa: 0.1504

## Failure Clusters
- JUDGE_CONFLICT: 5 case(s) (71.4%)
- REASONING_FAILURE: 1 case(s) (14.3%)
- RETRIEVAL_FAILURE: 1 case(s) (14.3%)

## Top Failure Deep Dive
### Failure #1: case_002
- Cluster: REASONING_FAILURE
- Score: 0.300
- Question: What idea explains why evaluation matters in this lab?

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.300
- Answer: The response diverges from the expected answer content.

#### WHY_2: Why does the response diverge from expectation?
- Observation: Compare retrieved evidence and expected support.
- Answer: Reasoning likely failed: retrieval appears acceptable, but final answer remains weak.

#### WHY_3: Why did retrieval/reasoning fail in this stage?
- Observation: Case type=fact-check, difficulty=easy
- Answer: Current prompt/retrieval settings are not specialized by case type.

#### WHY_4: Why are settings not specialized enough?
- Observation: One-size-fits-all defaults across heterogeneous cases.
- Answer: No adaptive strategy or dynamic routing exists for hard/adversarial questions.

#### WHY_5: What is the root cause?
- Observation: System-level behavior pattern from repeated low-score cases.
- Answer: Reasoning prompt and answer synthesis strategy are insufficient for this case type.

Recommendations:
- Add decomposition steps for multi-hop questions.
- Use answer plan then final response format.
- Include hard-case exemplars in prompt instructions.

---

### Failure #2: case_021
- Cluster: JUDGE_CONFLICT
- Score: 0.425
- Question: Why does the failure analysis need to mention retrieval, chunking, or prompting?

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.425
- Answer: The response diverges from the expected answer content.

#### WHY_2: Why does the response diverge from expectation?
- Observation: Compare retrieved evidence and expected support.
- Answer: Reasoning likely failed: retrieval appears acceptable, but final answer remains weak.

#### WHY_3: Why did retrieval/reasoning fail in this stage?
- Observation: Case type=reasoning, difficulty=medium
- Answer: Current prompt/retrieval settings are not specialized by case type.

#### WHY_4: Why are settings not specialized enough?
- Observation: One-size-fits-all defaults across heterogeneous cases.
- Answer: No adaptive strategy or dynamic routing exists for hard/adversarial questions.

#### WHY_5: What is the root cause?
- Observation: System-level behavior pattern from repeated low-score cases.
- Answer: Rubric alignment across judges is weak; clarification-style prompts need stricter calibration.

Recommendations:
- Tighten judge prompt rubric and scoring bands for clarification questions.
- Add a tiebreak judge for large score divergence.
- Track judge drift by case type each run.

---

### Failure #3: case_046
- Cluster: JUDGE_CONFLICT
- Score: 0.500
- Question: Can you explain the report requirements?

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.500
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
- Answer: Rubric alignment across judges is weak; clarification-style prompts need stricter calibration.

Recommendations:
- Tighten judge prompt rubric and scoring bands for clarification questions.
- Add a tiebreak judge for large score divergence.
- Track judge drift by case type each run.

---

### Failure #4: case_048
- Cluster: RETRIEVAL_FAILURE
- Score: 0.550
- Question: What should we run first?

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.550
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

### Failure #5: case_016
- Cluster: JUDGE_CONFLICT
- Score: 0.675
- Question: Why must the team evaluate retrieval before evaluating answer generation?

#### WHY_1: Why did the agent answer score low?
- Observation: Score=0.675
- Answer: The response diverges from the expected answer content.

#### WHY_2: Why does the response diverge from expectation?
- Observation: Compare retrieved evidence and expected support.
- Answer: Reasoning likely failed: retrieval appears acceptable, but final answer remains weak.

#### WHY_3: Why did retrieval/reasoning fail in this stage?
- Observation: Case type=reasoning, difficulty=medium
- Answer: Current prompt/retrieval settings are not specialized by case type.

#### WHY_4: Why are settings not specialized enough?
- Observation: One-size-fits-all defaults across heterogeneous cases.
- Answer: No adaptive strategy or dynamic routing exists for hard/adversarial questions.

#### WHY_5: What is the root cause?
- Observation: System-level behavior pattern from repeated low-score cases.
- Answer: Rubric alignment across judges is weak; clarification-style prompts need stricter calibration.

Recommendations:
- Tighten judge prompt rubric and scoring bands for clarification questions.
- Add a tiebreak judge for large score divergence.
- Track judge drift by case type each run.

---
