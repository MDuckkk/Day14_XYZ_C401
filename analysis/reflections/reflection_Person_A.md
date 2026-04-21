# Reflection - Person A

## Contributions
- Built and validated the golden dataset in `data/golden_set.jsonl`.
- Implemented retrieval evaluation and failure clustering outputs.
- Helped verify that report metrics stay aligned with benchmark results.

## What Worked Well
- Ground-truth document IDs made retrieval debugging much faster.
- The benchmark structure exposed weak spots in retrieval versus reasoning clearly.

## Challenges
- Some retrieval metrics were easy to misread when cases had no ground-truth docs.
- Failure thresholds needed to stay consistent across reports and release-gate logic.

## Next Improvements
- Add more ambiguous and comparison cases to stress-test routing.
- Extend retrieval reporting with per-case diagnostics for missed supporting docs.
