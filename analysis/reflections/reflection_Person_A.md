# Reflection - Person A

## Contributions
- Designed and generated the golden dataset (`data/golden_set.jsonl`) with 50 test cases covering 5 types: fact-check, reasoning, comparison, adversarial, and edge-case.
- Implemented retrieval evaluation metrics: Hit Rate@5, MRR, NDCG@5 in `engine/retrieval_eval.py`.
- Built failure clustering logic in `analysis/failure_clustering.py` to group failing cases into root-cause categories.
- Produced `analysis/failure_clusters.json` and this failure analysis report with 5-Whys drill-down.
- Verified consistency between retrieval metrics, failure clusters, and the release gate summary.

## Final Results (V2 — gpt-4o-mini)
| Metric | Value |
|--------|-------|
| Hit Rate@5 | 94.87% |
| MRR | 0.885 |
| NDCG@5 | 0.865 |
| Avg Score | 0.791 |
| Failure Rate | 26.0% |
| Release Decision | CONDITIONAL_RELEASE |

## What Worked Well
- Including `ground_truth_doc_ids` in every golden case made retrieval debugging precise — we could immediately distinguish retrieval failures from generation failures.
- Distributing cases across 5 types (especially adversarial and edge-case) revealed judge calibration issues that a purely factual benchmark would have missed.
- The failure clustering pipeline correctly attributed 76.9% of failures to reasoning/generation rather than retrieval, which directed optimization effort to the right layer.
- V2 (gpt-4o-mini) scored higher than V1 (gpt-4.1-nano) on avg_score (0.791 vs 0.782), confirming the model upgrade delivers quality improvement.

## Challenges
- Adversarial cases are inherently hard to score automatically: the agent's refusal is semantically correct but phrased differently from the expected answer, causing judge disagreement and the failed `agreement_ok` check.
- Cases with no `ground_truth_doc_ids` (adversarial/out-of-scope) are excluded from retrieval scoring, which inflates the apparent Hit Rate. This needed explicit documentation so downstream analysis wasn't misleading.
- Ambiguous edge-case questions (e.g., "How should we improve it?") require clarification responses, but the agent's heuristic for ambiguity detection is unreliable for short underspecified prompts.

## Next Improvements
- Extend the golden dataset with targeted comparison cases for every document pair to stress-test retrieval boost coverage.
- Add per-case retrieval diagnostics (expected doc retrieved at rank N) to `analysis/failure_clusters.json`.
- Introduce a pre-generation ambiguity classifier so short/vague questions trigger clarification before attempting factual lookup.
- Align expected answers for adversarial cases more closely with the agent's actual refusal phrasing to reduce judge scoring variance.
