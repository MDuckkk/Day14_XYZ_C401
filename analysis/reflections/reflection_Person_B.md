# Reflection - Person B

## Contributions
- Implemented `eval/async_runner.py`: async benchmark runner with semaphore-limited concurrency (max 5 parallel cases).
- Built `eval/judge.py` (OpenAIJudge, MultiJudge) and `eval/consensus.py` (ConsensusEngine) for multi-judge scoring and conflict resolution.
- Integrated the two-version comparison pipeline in `main.py`: runs V1 (gpt-4.1-nano) as baseline, then V2 (gpt-4o-mini) as candidate, and feeds V1 actual results into the regression gate.
- Configured and managed `eval/llm_config.py`: judge models (`gpt-4.1-mini`, `gpt-4.1-nano`), release gate thresholds, and baseline metrics.
- Generated all final outputs: `reports/benchmark_results.json`, `reports/summary.json`, `reports/release_gate_decision.json`, `metrics/judge_consensus.json`.
- Diagnosed and fixed the `gpt-5.4-nano` invalid model bug (replaced with `gpt-4.1-nano`) that caused all judges to fall back to heuristic scoring.

## Final Results (V2 — gpt-4o-mini)
| Metric | Value |
|--------|-------|
| Avg Score | 0.791 |
| Avg Latency | 1.920s |
| Total Tokens | 16,763 |
| Estimated Cost | $0.168 |
| Agreement Rate | 72.0% |
| Judge Conflicts | 13 |
| Cohen's Kappa | ~0.31 |
| Release Decision | CONDITIONAL_RELEASE |

## What Worked Well
- Async execution with `asyncio.gather` and a semaphore kept the full 50-case V2 benchmark under 2 minutes, well within the performance target.
- The two-version pipeline (V1 → V2) produces a real data-driven baseline instead of a hardcoded one, making regression detection meaningful.
- Multi-judge scoring with two models immediately revealed the judge calibration gap on adversarial cases — this would have been hidden with a single judge.
- Cost per evaluation was very low ($0.003/case for V2), demonstrating that GPT-4o-mini is cost-efficient for this benchmark scale.
- V2 outperformed V1 on avg_score (0.791 vs 0.782) and latency was acceptable at 1.92s, confirming quality_ok, latency_ok, and no_major_regression all passed.

## Challenges
- `gpt-4.1-mini` and `gpt-4.1-nano` disagree frequently on adversarial refusal cases: the agent gives correct behavior but phrased differently from expected, and the two judges score it inconsistently. This is the sole reason for CONDITIONAL_RELEASE instead of RELEASE.
- Agreement rate of 72% (vs 80% threshold) is driven by 13 judge conflicts — almost all on adversarial and edge-case types. Factual and reasoning cases reached near-100% agreement.
- Removing the `asyncio.sleep(0.1)` from the agent reduced latency from ~2.4s to 1.92s, but some API response variance remains; a few cases still exceed 3s individually.
- Calibrating the release gate thresholds required balancing between what's achievable with real API latency and what was originally specified for heuristic-only mode.

## Next Improvements
- Add an adversarial-specific rubric dimension to the judge prompt: award 0.8–1.0 for any semantically correct refusal, regardless of phrasing match.
- Implement a tiebreak judge (e.g. gpt-4o-mini) that activates automatically when the two primary judges diverge by more than 0.3.
- Track agreement rate broken down by case type (fact-check, reasoning, adversarial, edge-case) each run to detect judge drift by category.
- Cache judge client instances across cases to reduce overhead from repeated `AsyncOpenAI` initialisation.
- Once agreement_ok passes, promote V2 metrics as the new V1 baseline in `eval/llm_config.py`.
