# Root Cause Analysis (5 Whys)

## Failure #1: RETRIEVAL_FAILURE
Case: case_001 | Score: 0.45
Question: Câu hỏi mẫu từ tài liệu?

### WHY_1: Why did the agent answer score low?
- Observation: Score=0.45
- Answer: The response diverges from the expected answer content.

### WHY_2: Why does the response diverge from expectation?
- Observation: Compare retrieved evidence and expected support.
- Answer: Reasoning likely failed: retrieval appears acceptable, but final answer remains weak.

### WHY_3: Why did retrieval/reasoning fail in this stage?
- Observation: Case type=fact-check, difficulty=easy
- Answer: Current prompt/retrieval settings are not specialized by case type.

### WHY_4: Why are settings not specialized enough?
- Observation: One-size-fits-all defaults across heterogeneous cases.
- Answer: No adaptive strategy or dynamic routing exists for hard/adversarial questions.

### WHY_5: What is the root cause?
- Observation: System-level behavior pattern from repeated low-score cases.
- Answer: Chunking/retrieval configuration is not surfacing relevant evidence.

Recommendations:
- Adopt hybrid retrieval (keyword + vector).
- Tune chunk size and overlap to preserve key facts.
- Add query rewrite for ambiguous user questions.

---
