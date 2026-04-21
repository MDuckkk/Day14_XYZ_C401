# Failure Analysis Report

## Executive Summary
- Total cases: 50
- Failures: 14 (28.0%)
- Main issue cluster: retrieval_failure

## Cluster Breakdown
- reasoning_or_generation_failure: 5 cases (35.7%)
- retrieval_failure: 8 cases (57.1%)
- instruction_following_failure: 1 cases (7.1%)

## Top 5 Failure Deep Dive
### Failure #1: case_003
- Question: Which retrieval metrics are explicitly required?
- Cluster: reasoning_or_generation_failure
- Judge score: 2.25 / 5.0
- Retrieval hit: yes
- Ground truth docs: doc_retrieval
- Retrieved docs: doc_retrieval
- Suggested fix: improve retrieval if the gold doc was missed, otherwise tighten answer generation and instruction handling.

### Failure #2: case_004
- Question: Why do test cases need ground truth document IDs?
- Cluster: reasoning_or_generation_failure
- Judge score: 2.25 / 5.0
- Retrieval hit: yes
- Ground truth docs: doc_retrieval
- Retrieved docs: doc_retrieval, doc_performance, doc_adversarial_policy
- Suggested fix: improve retrieval if the gold doc was missed, otherwise tighten answer generation and instruction handling.

### Failure #3: case_007
- Question: Which three dimensions should the release gate consider?
- Cluster: reasoning_or_generation_failure
- Judge score: 2.25 / 5.0
- Retrieval hit: yes
- Ground truth docs: doc_regression
- Retrieved docs: doc_regression, doc_judge, doc_performance
- Suggested fix: improve retrieval if the gold doc was missed, otherwise tighten answer generation and instruction handling.

### Failure #4: case_023
- Question: How are release decisions linked to benchmarking metrics?
- Cluster: reasoning_or_generation_failure
- Judge score: 2.25 / 5.0
- Retrieval hit: yes
- Ground truth docs: doc_regression, doc_performance
- Retrieved docs: doc_retrieval, doc_regression
- Suggested fix: improve retrieval if the gold doc was missed, otherwise tighten answer generation and instruction handling.

### Failure #5: case_026
- Question: Compare Hit Rate and MRR in one sentence.
- Cluster: reasoning_or_generation_failure
- Judge score: 2.25 / 5.0
- Retrieval hit: yes
- Ground truth docs: doc_retrieval
- Retrieved docs: doc_retrieval, doc_judge, doc_conflict_a
- Suggested fix: improve retrieval if the gold doc was missed, otherwise tighten answer generation and instruction handling.

## Recommendations
- Expand retrieval coverage for multi-document and comparison questions.
- Strengthen refusal and clarification behavior for adversarial and ambiguous cases.
- Review prompts and answer formatting when retrieval succeeds but judge scores remain low.
