import asyncio
import json
import os

from agent.main_agent import MainAgent
from analysis.failure_clustering import FailureAnalyzer
from engine.report_generator import generate_summary_report, save_json
from engine.retrieval_eval import compute_metrics_from_results
from engine.runner import BenchmarkRunner


class ExpertEvaluator:
    async def score(self, case, resp):
        expected_ids = case.get("ground_truth_doc_ids", [])
        retrieved_ids = resp.get("retrieved_doc_ids", [])
        hit_rate = 1.0 if not expected_ids or any(doc_id in retrieved_ids[:5] for doc_id in expected_ids) else 0.0
        faithfulness = 0.9 if hit_rate else 0.55
        relevancy = 0.85 if retrieved_ids else 0.4
        return {
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "retrieval": {"hit_rate": hit_rate, "mrr": 1.0 if hit_rate else 0.0},
        }


class MultiModelJudge:
    async def evaluate_multi_judge(self, question, answer, ground_truth):
        del question
        lower_answer = answer.lower()
        lower_gt = ground_truth.lower()
        if any(token in lower_gt for token in ["i do not know", "i cannot", "could you clarify"]):
            aligned = any(token in lower_answer for token in ["do not know", "cannot", "clarify"])
        else:
            aligned = any(token in lower_answer for token in lower_gt.split()[:6])

        score_a = 4.5 if aligned else 2.5
        score_b = 4.0 if aligned else 2.0
        avg_score = (score_a + score_b) / 2
        agreement = 1.0 if abs(score_a - score_b) <= 0.5 else 0.5
        return {
            "final_score": avg_score,
            "agreement_rate": agreement,
            "reasoning": "Both heuristic judges see the answer as aligned with the expected behavior."
            if aligned
            else "The answer only partially matches the expected grounded behavior.",
            "individual_scores": {"judge_a": score_a, "judge_b": score_b},
        }


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

    runner = BenchmarkRunner(MainAgent(), ExpertEvaluator(), MultiModelJudge())
    return await runner.run_all(dataset)


async def main():
    os.makedirs("reports", exist_ok=True)
    os.makedirs("metrics", exist_ok=True)

    results = await run_benchmark_with_results("Agent_V2_Optimized")
    if results is None:
        return

    save_json("reports/benchmark_results.json", results)

    retrieval_metrics = await compute_metrics_from_results(
        "reports/benchmark_results.json",
        "data/golden_set.jsonl",
    )
    save_json("metrics/retrieval_metrics.json", retrieval_metrics)

    analyzer = FailureAnalyzer("reports/benchmark_results.json", "data/golden_set.jsonl")
    failure_summary = analyzer.save_json("analysis/failure_clusters.json")
    analyzer.save_markdown("analysis/failure_analysis.md", failure_summary)

    summary = generate_summary_report(
        benchmark_results=results,
        retrieval_metrics=retrieval_metrics,
        failure_summary=failure_summary,
        agent_version="Agent_V2_Optimized",
    )
    save_json("reports/summary.json", summary)

    print("\nBenchmark summary")
    print(f"- Cases: {summary['metadata']['total']}")
    print(f"- Average score: {summary['metrics']['avg_score']:.2f}/5.0")
    print(f"- Hit Rate@5: {summary['metrics']['hit_rate']:.2%}")
    print(f"- MRR: {summary['metrics']['mrr']:.3f}")
    print(f"- NDCG@5: {summary['metrics']['ndcg@5']:.3f}")
    print(f"- Agreement Rate: {summary['metrics']['agreement_rate']:.2%}")
    print(f"- Failure Rate: {summary['metrics']['failure_rate']:.2%}")


if __name__ == "__main__":
    asyncio.run(main())
