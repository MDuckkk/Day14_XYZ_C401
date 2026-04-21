import asyncio
import json
from pathlib import Path

from analysis.regression_gate import RegressionReleaseGate
from analysis.root_cause import RootCauseAnalyzer
from eval.async_runner import AsyncBenchmarkRunner
from eval.consensus import ConsensusEngine


async def main() -> None:
    print("=" * 70)
    print("STARTING AI EVALUATION FACTORY BENCHMARK")
    print("=" * 70)

    golden_path = Path("data/golden_set.jsonl")
    if not golden_path.exists():
        print("golden_set.jsonl is missing. Run: python data/synthetic_gen.py")
        return

    print("[1/5] Running async benchmark with multi-judge...")
    runner = AsyncBenchmarkRunner(str(golden_path))
    results = await runner.run_benchmark(max_concurrent=5)
    runner.save_results("reports/benchmark_results.json")

    print("[2/5] Building benchmark summary...")
    summary = runner.build_summary(version="Agent_V2_Optimized")
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[3/5] Computing judge consensus metrics...")
    consensus_input = [
        {
            "final_score": r.get("judge_score", 0.0),
            "individual_scores": r.get("judge_scores", []),
        }
        for r in results
    ]
    consensus_report = ConsensusEngine.generate_consensus_report(consensus_input)
    Path("metrics").mkdir(parents=True, exist_ok=True)
    Path("metrics/judge_consensus.json").write_text(
        json.dumps(consensus_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[4/5] Running regression release gate...")
    gate = RegressionReleaseGate("reports/benchmark_results.json")
    gate_report = gate.generate_gate_report()
    Path("reports/release_gate_decision.json").write_text(
        json.dumps(gate_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[5/5] Generating 5 Whys failure analysis...")
    analyzer = RootCauseAnalyzer("reports/benchmark_results.json", "data/golden_set.jsonl")
    failure_report = analyzer.generate_full_report(top_n=5)
    Path("analysis/failure_analysis.md").write_text(failure_report, encoding="utf-8")

    print("=" * 70)
    print("DONE")
    print(f"Total cases evaluated: {len(results)}")
    print(f"Average score: {summary['metrics']['avg_score']:.4f}")
    print(f"Agreement rate: {summary['metrics']['agreement_rate']:.4f}")
    print(f"Release decision: {gate_report['release_gate']['decision']}")
    print("Generated files:")
    print("- reports/benchmark_results.json")
    print("- reports/summary.json")
    print("- metrics/judge_consensus.json")
    print("- reports/release_gate_decision.json")
    print("- analysis/failure_analysis.md")


if __name__ == "__main__":
    asyncio.run(main())
