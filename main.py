import asyncio
import json
import os

from analysis.failure_clustering import FailureAnalyzer
from analysis.regression_gate import RegressionReleaseGate
from analysis.root_cause import RootCauseAnalyzer
from eval.async_runner import AsyncBenchmarkRunner
from eval.consensus import ConsensusEngine
from engine.report_generator import generate_summary_report, save_json
from engine.retrieval_eval import compute_metrics_from_results


async def run_benchmark_with_results(agent_version: str):
    print(f"Starting benchmark for {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("Missing data/golden_set.jsonl. Run 'python data/synthetic_gen.py' first.")
        return None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("The golden dataset is empty. Generate at least one test case first.")
        return None

    runner = AsyncBenchmarkRunner("data/golden_set.jsonl")
    results = await runner.run_benchmark(max_concurrent=5)
    runner.save_results("reports/benchmark_results.json")
    return results


async def main():
    os.makedirs("reports", exist_ok=True)
    os.makedirs("metrics", exist_ok=True)

    results = await run_benchmark_with_results("Agent_V2_Optimized")
    if results is None:
        return

    retrieval_metrics = await compute_metrics_from_results(
        "reports/benchmark_results.json",
        "data/golden_set.jsonl",
    )
    save_json("metrics/retrieval_metrics.json", retrieval_metrics)

    consensus_rows = [
        {
            "final_score": row.get("judge_score", 0.0),
            "individual_scores": row.get("judge_scores", []),
        }
        for row in results
    ]
    judge_consensus = ConsensusEngine.generate_consensus_report(consensus_rows)
    save_json("metrics/judge_consensus.json", judge_consensus)

    analyzer = FailureAnalyzer("reports/benchmark_results.json", "data/golden_set.jsonl")
    failure_summary = analyzer.save_json("analysis/failure_clusters.json")

    root_cause = RootCauseAnalyzer("reports/benchmark_results.json", "data/golden_set.jsonl")
    with open("analysis/failure_analysis.md", "w", encoding="utf-8") as f:
        f.write(root_cause.generate_full_report(top_n=5))

    release_gate = RegressionReleaseGate("reports/benchmark_results.json").generate_gate_report()
    save_json("reports/release_gate_decision.json", release_gate)

    summary = generate_summary_report(
        benchmark_results=results,
        retrieval_metrics=retrieval_metrics,
        failure_summary=failure_summary,
        agent_version="Agent_V2_Optimized",
        judge_consensus=judge_consensus,
        release_gate=release_gate,
    )
    save_json("reports/summary.json", summary)

    print("\nBenchmark summary")
    print(f"- Cases: {summary['metadata']['total']}")
    print(f"- Average score: {summary['metrics']['avg_score']:.3f}")
    print(f"- Hit Rate@5: {summary['metrics']['hit_rate@5']:.2%}")
    print(f"- MRR: {summary['metrics']['mrr']:.3f}")
    print(f"- NDCG@5: {summary['metrics']['ndcg@5']:.3f}")
    print(f"- Agreement Rate: {summary['metrics']['agreement_rate']:.2%}")
    print(f"- Failure Rate: {summary['metrics']['failure_rate']:.2%}")
    print(f"- Release Decision: {summary['release_gate']['release_gate']['decision']}")


if __name__ == "__main__":
    asyncio.run(main())
