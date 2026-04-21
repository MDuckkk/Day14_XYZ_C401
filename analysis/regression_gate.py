import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from eval.llm_config import JudgeConfig


class RegressionReleaseGate:
    """Automatic release decision by comparing current run vs baseline."""

    def __init__(self, current_results_path: str, baseline_metrics: Dict = None):
        self.current_results_path = Path(current_results_path)
        self.current_results = self._load_results(self.current_results_path)
        self.baseline = baseline_metrics or JudgeConfig.BASELINE_METRICS
        self.thresholds = JudgeConfig.RELEASE_GATE

    def _load_results(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("results", payload if isinstance(payload, list) else [])

    def calculate_current_metrics(self) -> Dict:
        if not self.current_results:
            return {
                "avg_score": 0.0,
                "retrieval_hit_rate": 0.0,
                "cost_per_eval": 0.0,
                "judge_agreement": 0.0,
                "latency_avg": 0.0,
                "total_cases": 0,
                "passed_cases": 0,
                "failure_rate": 0.0,
            }

        total = len(self.current_results)
        scores = [float(r.get("judge_score", 0.0)) for r in self.current_results]
        agreements = [float(r.get("judge_agreement", 0.0)) for r in self.current_results]
        retrieval_hits = [float(r.get("retrieval_hit_rate", 0.0)) for r in self.current_results]
        latencies = [float(r.get("latency_sec", 0.0)) for r in self.current_results]

        total_tokens = sum(int(r.get("tokens_used", 0)) for r in self.current_results)
        estimated_cost = (total_tokens / 1000.0) * 0.01

        return {
            "avg_score": round(sum(scores) / total, 4),
            "retrieval_hit_rate": round(sum(retrieval_hits) / total, 4),
            "cost_per_eval": round(estimated_cost / total, 4),
            "judge_agreement": round(sum(agreements) / total, 4),
            "latency_avg": round(sum(latencies) / total, 4),
            "total_cases": total,
            "passed_cases": sum(1 for s in scores if s >= 0.7),
            "failure_rate": round(sum(1 for s in scores if s < 0.7) / total, 4),
        }

    def compare_metrics(self) -> Dict:
        current = self.calculate_current_metrics()
        deltas = {
            "score_delta": round(current["avg_score"] - self.baseline["avg_score"], 4),
            "retrieval_delta": round(current["retrieval_hit_rate"] - self.baseline["retrieval_hit_rate"], 4),
            "cost_delta": round(current["cost_per_eval"] - self.baseline["cost_per_eval"], 4),
            "agreement_delta": round(current["judge_agreement"] - self.baseline["judge_agreement"], 4),
            "latency_delta": round(current["latency_avg"] - self.baseline["latency_avg"], 4),
        }
        return {"baseline": self.baseline, "current": current, "deltas": deltas}

    def make_release_decision(self) -> Dict:
        comparison = self.compare_metrics()
        current = comparison["current"]
        deltas = comparison["deltas"]

        checks = {
            "quality_ok": current["avg_score"] >= self.thresholds["min_accuracy"],
            "cost_ok": current["cost_per_eval"] <= self.thresholds["max_cost_per_eval"],
            "latency_ok": current["latency_avg"] <= self.thresholds["max_latency_sec"],
            "agreement_ok": current["judge_agreement"] >= self.thresholds["min_judge_agreement"],
            "no_major_regression": deltas["score_delta"] >= -0.05,
        }

        if all(checks.values()):
            decision = "RELEASE"
            confidence = 0.95
        elif checks["quality_ok"] and checks["cost_ok"] and checks["no_major_regression"]:
            decision = "CONDITIONAL_RELEASE"
            confidence = 0.70
        else:
            decision = "ROLLBACK"
            confidence = 0.99

        return {
            "decision": decision,
            "confidence": confidence,
            "checks": checks,
            "comparison": comparison,
            "reasoning": self._generate_reasoning(decision, checks, deltas),
        }

    @staticmethod
    def _generate_reasoning(decision: str, checks: Dict, deltas: Dict) -> str:
        if decision == "RELEASE":
            return (
                f"All checks passed. Score delta {deltas['score_delta']:+.3f}, "
                f"cost delta ${deltas['cost_delta']:+.3f}."
            )
        if decision == "CONDITIONAL_RELEASE":
            failed = [k for k, v in checks.items() if not v]
            return f"Core quality passed but needs review on: {', '.join(failed)}."
        failed = [k for k, v in checks.items() if not v]
        return f"Failed release checks: {', '.join(failed)}."

    def generate_gate_report(self) -> Dict:
        result = self.make_release_decision()
        return {
            "release_gate": result,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "next_steps": self._recommend_next_steps(result["decision"]),
        }

    @staticmethod
    def _recommend_next_steps(decision: str) -> List[str]:
        if decision == "RELEASE":
            return [
                "Promote current metrics as the new baseline.",
                "Deploy and monitor for at least 24 hours.",
                "Track drift by case type in production logs.",
            ]
        if decision == "CONDITIONAL_RELEASE":
            return [
                "Run targeted tests for failed checks.",
                "Apply low-risk optimizations, then re-benchmark.",
                "Require manual approval before production rollout.",
            ]
        return [
            "Review top failure cases and root causes.",
            "Apply fixes and rerun benchmark suite.",
            "Keep previous stable version in production.",
        ]


if __name__ == "__main__":
    gate = RegressionReleaseGate("reports/benchmark_results.json")
    report = gate.generate_gate_report()
    output = Path("reports/release_gate_decision.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Release gate decision saved to {output}")
