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


async def run_benchmark_with_results(agent_version: str, agent_model: str, results_path: str):
    print(f"\nStarting benchmark for {agent_version} (model: {agent_model})...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("Missing data/golden_set.jsonl. Run 'python data/synthetic_gen.py' first.")
        return None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("The golden dataset is empty. Generate at least one test case first.")
        return None

    runner = AsyncBenchmarkRunner("data/golden_set.jsonl", agent_model=agent_model)
    results = await runner.run_benchmark(max_concurrent=5)
    runner.save_results(results_path)
    return results


def extract_baseline_from_results(results_path: str) -> dict:
    with open(results_path, encoding="utf-8") as f:
        payload = json.load(f)
    rows = payload.get("results", [])
    if not rows:
        return {}
    total = len(rows)
    scores = [float(r.get("judge_score", 0.0)) for r in rows]
    agreements = [float(r.get("judge_agreement", 0.0)) for r in rows]
    latencies = [float(r.get("latency_sec", 0.0)) for r in rows]
    total_tokens = sum(int(r.get("tokens_used", 0)) for r in rows)
    retrieval_rows = [r for r in rows if r.get("ground_truth_doc_ids")]
    if retrieval_rows:
        hits = [
            1.0 if set(r.get("ground_truth_doc_ids", [])) & set(r.get("retrieved_doc_ids", [])[:5]) else 0.0
            for r in retrieval_rows
        ]
        hit_rate = round(sum(hits) / len(hits), 4)
    else:
        hit_rate = 0.0
    return {
        "avg_score": round(sum(scores) / total, 4),
        "retrieval_hit_rate": hit_rate,
        "cost_per_eval": round((total_tokens / 1000.0 * 0.01) / total, 4),
        "judge_agreement": round(sum(agreements) / total, 4),
        "latency_avg": round(sum(latencies) / total, 4),
    }


async def main():
    os.makedirs("reports", exist_ok=True)
    os.makedirs("metrics", exist_ok=True)

    # --- Run V1: gpt-4.1-nano ---
    v1_results = await run_benchmark_with_results(
        agent_version="Agent_V1",
        agent_model="gpt-4.1-nano",
        results_path="reports/benchmark_results_v1.json",
    )
    if v1_results is None:
        return

    v1_baseline = extract_baseline_from_results("reports/benchmark_results_v1.json")
    print(f"  V1 avg_score={v1_baseline['avg_score']:.3f}  latency={v1_baseline['latency_avg']:.2f}s")

    # --- Run V2: gpt-4o-mini ---
    v2_results = await run_benchmark_with_results(
        agent_version="Agent_V2_Optimized",
        agent_model="gpt-4o-mini",
        results_path="reports/benchmark_results.json",
    )
    if v2_results is None:
        return

    # --- Metrics & analysis for V2 ---
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
        for row in v2_results
    ]
    judge_consensus = ConsensusEngine.generate_consensus_report(consensus_rows)
    save_json("metrics/judge_consensus.json", judge_consensus)

    analyzer = FailureAnalyzer("reports/benchmark_results.json", "data/golden_set.jsonl")
    failure_summary = analyzer.save_json("analysis/failure_clusters.json")

    root_cause = RootCauseAnalyzer("reports/benchmark_results.json", "data/golden_set.jsonl")
    with open("analysis/failure_analysis.md", "w", encoding="utf-8") as f:
        f.write(root_cause.generate_full_report(top_n=5))

    # Regression gate: compare V2 against actual V1 results
    release_gate = RegressionReleaseGate(
        "reports/benchmark_results.json",
        baseline_metrics=v1_baseline,
    ).generate_gate_report()
    save_json("reports/release_gate_decision.json", release_gate)

    summary = generate_summary_report(
        benchmark_results=v2_results,
        retrieval_metrics=retrieval_metrics,
        failure_summary=failure_summary,
        agent_version="Agent_V2_Optimized",
        judge_consensus=judge_consensus,
        release_gate=release_gate,
    )
    save_json("reports/summary.json", summary)

    print("\n========== Benchmark Summary ==========")
    print(f"  V1 (gpt-4.1-nano)  avg_score={v1_baseline['avg_score']:.3f}  latency={v1_baseline['latency_avg']:.2f}s")
    print(f"  V2 (gpt-4o-mini)   avg_score={summary['metrics']['avg_score']:.3f}  latency={summary['metrics'].get('avg_latency_sec', 0):.2f}s")
    print(f"  Hit Rate@5:      {summary['metrics']['hit_rate@5']:.2%}")
    print(f"  MRR:             {summary['metrics']['mrr']:.3f}")
    print(f"  NDCG@5:          {summary['metrics']['ndcg@5']:.3f}")
    print(f"  Agreement Rate:  {summary['metrics']['agreement_rate']:.2%}")
    print(f"  Failure Rate:    {summary['metrics']['failure_rate']:.2%}")
    print(f"  Release Decision: {summary['release_gate']['release_gate']['decision']}")


if __name__ == "__main__":
    asyncio.run(main())
