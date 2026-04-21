import json
from pathlib import Path
from typing import Dict, List

from eval.consensus import ConsensusEngine

PASS_THRESHOLD = 0.7


class RootCauseAnalyzer:
    def __init__(self, benchmark_results_path: str, golden_set_path: str):
        self.benchmark_results_path = Path(benchmark_results_path)
        self.golden_set_path = Path(golden_set_path)
        self.results = self._load_results()
        self.golden_cases = self._load_golden_cases()

    def _load_results(self) -> List[Dict]:
        if not self.benchmark_results_path.exists():
            return []
        with self.benchmark_results_path.open(encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("results", payload if isinstance(payload, list) else [])

    def _load_golden_cases(self) -> Dict[str, Dict]:
        if not self.golden_set_path.exists():
            return {}

        rows: Dict[str, Dict] = {}
        with self.golden_set_path.open(encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                case_id = str(row.get("id") or row.get("case_id") or f"case_{idx:03d}")
                rows[case_id] = row
        return rows

    def _cluster_failure(self, row: Dict) -> str:
        judge_modes = {item.get("mode") for item in row.get("judge_scores", [])}
        if judge_modes and judge_modes == {"heuristic_fallback"}:
            return "EVAL_INFRA_FAILURE"
        if row.get("ground_truth_doc_ids") and not (set(row.get("ground_truth_doc_ids", [])) & set(row.get("retrieved_doc_ids", []))):
            return "RETRIEVAL_FAILURE"
        if row.get("judge_agreement", 1.0) < 0.7:
            return "JUDGE_CONFLICT"
        answer = (row.get("agent_answer") or "").lower()
        if "khong" in answer or "không" in answer or "do not know" in answer:
            return "HALLUCINATION_OR_REFUSAL"
        return "REASONING_FAILURE"

    def get_top_failures(self, n: int = 5) -> List[Dict]:
        failed = [r for r in self.results if r.get("judge_score", 1.0) < PASS_THRESHOLD]
        failed.sort(key=lambda x: x.get("judge_score", 1.0))
        return [
            {
                "case_id": row.get("case_id"),
                "question": row.get("question"),
                "score": row.get("judge_score", 0.0),
                "cluster": self._cluster_failure(row),
            }
            for row in failed[:n]
        ]

    def _analyze_retrieval_vs_reasoning(self, result: Dict, golden: Dict) -> str:
        judge_modes = {item.get("mode") for item in result.get("judge_scores", [])}
        if judge_modes and judge_modes == {"heuristic_fallback"}:
            return "Judge API calls failed and scoring fell back to heuristics, so this run mixes agent behavior with evaluation infrastructure failure."
        retrieved = set(result.get("retrieved_doc_ids", []))
        expected = set(result.get("ground_truth_doc_ids") or golden.get("ground_truth_doc_ids", []))
        if expected and not (retrieved & expected):
            return "Retrieval likely failed: expected supporting docs were not retrieved."
        return "Reasoning likely failed: retrieval appears acceptable, but final answer remains weak."

    def _determine_root_cause(self, result: Dict, golden: Dict) -> str:
        cluster = self._cluster_failure(result)
        if cluster == "EVAL_INFRA_FAILURE":
            return "OpenAI judge connectivity failed, forcing heuristic fallback and making quality conclusions less reliable."
        if cluster == "RETRIEVAL_FAILURE":
            return "Chunking/retrieval configuration is not surfacing relevant evidence."
        if cluster == "JUDGE_CONFLICT":
            return "Rubric alignment across judges is weak; clarification-style prompts need stricter calibration."
        if cluster == "HALLUCINATION_OR_REFUSAL":
            return "Prompt constraints or confidence policy cause unsupported or over-conservative outputs."
        return "Reasoning prompt and answer synthesis strategy are insufficient for this case type."

    def _generate_recommendations(self, cluster_type: str) -> List[str]:
        mapping = {
            "EVAL_INFRA_FAILURE": [
                "Stabilize OpenAI API connectivity before trusting the benchmark scores.",
                "Log request failures separately from model-quality failures.",
                "Rerun the full benchmark only after judge API calls succeed in live mode.",
            ],
            "RETRIEVAL_FAILURE": [
                "Adopt hybrid retrieval (keyword + vector).",
                "Tune chunk size and overlap to preserve key facts.",
                "Add query rewrite for ambiguous user questions.",
            ],
            "JUDGE_CONFLICT": [
                "Tighten judge prompt rubric and scoring bands for clarification questions.",
                "Add a tiebreak judge for large score divergence.",
                "Track judge drift by case type each run.",
            ],
            "HALLUCINATION_OR_REFUSAL": [
                "Strengthen grounded-answer policy in system prompt.",
                "Add refusal threshold only when evidence is missing.",
                "Require citations from retrieved snippets.",
            ],
            "REASONING_FAILURE": [
                "Add decomposition steps for multi-hop questions.",
                "Use answer plan then final response format.",
                "Include hard-case exemplars in prompt instructions.",
            ],
        }
        return mapping.get(cluster_type, [])

    def _build_failure_summary(self) -> Dict:
        failed = [r for r in self.results if r.get("judge_score", 1.0) < PASS_THRESHOLD]
        clusters: Dict[str, int] = {}
        for row in failed:
            cluster = self._cluster_failure(row)
            clusters[cluster] = clusters.get(cluster, 0) + 1
        return {
            "total_cases": len(self.results),
            "failed_cases": len(failed),
            "passed_cases": len(self.results) - len(failed),
            "failure_rate": (len(failed) / len(self.results)) if self.results else 0.0,
            "clusters": clusters,
        }

    def _build_judge_summary(self) -> Dict:
        if not self.results:
            return {
                "avg_score": 0.0,
                "avg_agreement": 0.0,
                "num_conflicts": 0,
                "cohens_kappa": 1.0,
                "fallback_cases": 0,
            }

        avg_score = sum(float(r.get("judge_score", 0.0)) for r in self.results) / len(self.results)
        avg_agreement = sum(float(r.get("judge_agreement", 0.0)) for r in self.results) / len(self.results)
        num_conflicts = sum(1 for r in self.results if float(r.get("judge_agreement", 0.0)) < 0.7)

        judge_a_scores: List[float] = []
        judge_b_scores: List[float] = []
        for row in self.results:
            raw_scores = [float(item.get("score", 0.0)) for item in row.get("judge_scores", [])]
            if len(raw_scores) >= 1:
                judge_a_scores.append(raw_scores[0])
            if len(raw_scores) >= 2:
                judge_b_scores.append(raw_scores[1])

        overlap = min(len(judge_a_scores), len(judge_b_scores))
        kappa = (
            ConsensusEngine.calculate_cohens_kappa(judge_a_scores[:overlap], judge_b_scores[:overlap])
            if overlap >= 2
            else 1.0
        )
        fallback_cases = sum(
            1
            for row in self.results
            if row.get("judge_scores") and {item.get("mode") for item in row.get("judge_scores", [])} == {"heuristic_fallback"}
        )

        return {
            "avg_score": avg_score,
            "avg_agreement": avg_agreement,
            "num_conflicts": num_conflicts,
            "cohens_kappa": kappa,
            "fallback_cases": fallback_cases,
        }

    def analyze_failure_5whys(self, failure: Dict) -> Dict:
        case_id = str(failure["case_id"])
        result = next((r for r in self.results if str(r.get("case_id")) == case_id), None)
        golden = self.golden_cases.get(case_id, {})
        if not result:
            return {}

        whys = {
            "why_1": {
                "question": "Why did the agent answer score low?",
                "observation": f"Score={result.get('judge_score', 0.0):.3f}",
                "answer": "The response diverges from the expected answer content.",
            },
            "why_2": {
                "question": "Why does the response diverge from expectation?",
                "observation": "Compare retrieved evidence and expected support.",
                "answer": self._analyze_retrieval_vs_reasoning(result, golden),
            },
            "why_3": {
                "question": "Why did retrieval/reasoning fail in this stage?",
                "observation": f"Case type={result.get('case_type')}, difficulty={result.get('difficulty')}",
                "answer": "Current prompt/retrieval settings are not specialized by case type.",
            },
            "why_4": {
                "question": "Why are settings not specialized enough?",
                "observation": "One-size-fits-all defaults across heterogeneous cases.",
                "answer": "No adaptive strategy or dynamic routing exists for hard/adversarial questions.",
            },
            "why_5": {
                "question": "What is the root cause?",
                "observation": "System-level behavior pattern from repeated low-score cases.",
                "answer": self._determine_root_cause(result, golden),
            },
        }

        return {
            "case_id": case_id,
            "cluster": failure["cluster"],
            "score": failure["score"],
            "question": failure["question"],
            "five_whys": whys,
            "recommendations": self._generate_recommendations(failure["cluster"]),
        }

    def generate_full_report(self, top_n: int = 5) -> str:
        top_failures = self.get_top_failures(n=top_n)
        failure_summary = self._build_failure_summary()
        judge_summary = self._build_judge_summary()

        lines = [
            "# Failure Analysis Report",
            "",
            "## Executive Summary",
            f"- Total cases: {failure_summary['total_cases']}",
            f"- Pass/Fail: {failure_summary['passed_cases']}/{failure_summary['failed_cases']}",
            f"- Failure rate: {failure_summary['failure_rate']:.1%}",
            f"- Average judge score: {judge_summary['avg_score']:.4f} / 1.0",
            f"- Average judge agreement: {judge_summary['avg_agreement']:.2%}",
            f"- Judge conflicts: {judge_summary['num_conflicts']}",
            f"- Cohen's kappa: {judge_summary['cohens_kappa']:.4f}",
            f"- Judge fallback cases: {judge_summary['fallback_cases']}",
            "",
            "## Failure Clusters",
        ]

        if not failure_summary["clusters"]:
            lines.append("- No failing cases were detected.")
        else:
            for name, count in sorted(failure_summary["clusters"].items()):
                percentage = (count / failure_summary["failed_cases"] * 100) if failure_summary["failed_cases"] else 0.0
                lines.append(f"- {name}: {count} case(s) ({percentage:.1f}%)")

        lines.extend(["", "## Top Failure Deep Dive"])
        if judge_summary["fallback_cases"]:
            lines.extend(
                [
                    "## Infra Warning",
                    "- All judge calls in this run fell back to heuristic scoring because the OpenAI judge requests returned connection errors.",
                    "- Treat the reported score collapse as a mix of generation regression and evaluation-infrastructure instability.",
                    "",
                ]
            )
        if not top_failures:
            lines.append("No failing cases found (all judge_score >= 0.7).")
            return "\n".join(lines)

        for idx, failure in enumerate(top_failures, start=1):
            analysis = self.analyze_failure_5whys(failure)
            lines.append(f"### Failure #{idx}: {analysis['case_id']}")
            lines.append(f"- Cluster: {analysis['cluster']}")
            lines.append(f"- Score: {analysis['score']:.3f}")
            lines.append(f"- Question: {analysis['question']}")
            lines.append("")
            for key, payload in analysis["five_whys"].items():
                lines.append(f"#### {key.upper()}: {payload['question']}")
                lines.append(f"- Observation: {payload['observation']}")
                lines.append(f"- Answer: {payload['answer']}")
                lines.append("")
            lines.append("Recommendations:")
            for rec in analysis["recommendations"]:
                lines.append(f"- {rec}")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    analyzer = RootCauseAnalyzer("reports/benchmark_results.json", "data/golden_set.jsonl")
    report = analyzer.generate_full_report(top_n=5)
    output_path = Path("analysis/failure_analysis.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print("Root cause analysis generated at analysis/failure_analysis.md")
