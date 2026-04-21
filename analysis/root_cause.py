import json
from pathlib import Path
from typing import Dict, List


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
        if row.get("retrieval_hit_rate", 0.0) <= 0.0:
            return "RETRIEVAL_FAILURE"
        if row.get("judge_agreement", 1.0) < 0.7:
            return "JUDGE_CONFLICT"
        answer = (row.get("agent_answer") or "").lower()
        if "khong" in answer or "không" in answer:
            return "HALLUCINATION_OR_REFUSAL"
        return "REASONING_FAILURE"

    def get_top_failures(self, n: int = 5) -> List[Dict]:
        failed = [r for r in self.results if r.get("judge_score", 1.0) < 0.7]
        failed.sort(key=lambda x: x.get("judge_score", 1.0))
        top = failed[:n]

        out = []
        for row in top:
            out.append(
                {
                    "case_id": row.get("case_id"),
                    "question": row.get("question"),
                    "score": row.get("judge_score", 0.0),
                    "cluster": self._cluster_failure(row),
                }
            )
        return out

    def _analyze_retrieval_vs_reasoning(self, result: Dict, golden: Dict) -> str:
        retrieved = set(result.get("retrieved_doc_ids", []))
        expected = set(result.get("ground_truth_doc_ids") or golden.get("ground_truth_doc_ids", []))
        if expected and not (retrieved & expected):
            return "Retrieval likely failed: expected supporting docs were not retrieved."
        return "Reasoning likely failed: retrieval appears acceptable, but final answer remains weak."

    def _determine_root_cause(self, result: Dict, golden: Dict) -> str:
        cluster = self._cluster_failure(result)
        if cluster == "RETRIEVAL_FAILURE":
            return "Chunking/retrieval configuration is not surfacing relevant evidence."
        if cluster == "JUDGE_CONFLICT":
            return "Rubric alignment across judges is weak; scoring criteria need stricter calibration."
        if cluster == "HALLUCINATION_OR_REFUSAL":
            return "Prompt constraints or confidence policy cause unsupported or over-conservative outputs."
        return "Reasoning prompt and answer synthesis strategy are insufficient for this case type."

    def _generate_recommendations(self, cluster_type: str) -> List[str]:
        mapping = {
            "RETRIEVAL_FAILURE": [
                "Adopt hybrid retrieval (keyword + vector).",
                "Tune chunk size and overlap to preserve key facts.",
                "Add query rewrite for ambiguous user questions.",
            ],
            "JUDGE_CONFLICT": [
                "Tighten judge prompt rubric and scoring bands.",
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

    def analyze_failure_5whys(self, failure: Dict) -> Dict:
        case_id = str(failure["case_id"])
        result = next((r for r in self.results if str(r.get("case_id")) == case_id), None)
        golden = self.golden_cases.get(case_id, {})
        if not result:
            return {}

        whys = {
            "why_1": {
                "question": "Why did the agent answer score low?",
                "observation": f"Score={result.get('judge_score', 0.0):.2f}",
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
        lines = ["# Root Cause Analysis (5 Whys)", ""]

        if not top_failures:
            lines.append("No failing cases found (all judge_score >= 0.7).")
            return "\n".join(lines)

        for idx, failure in enumerate(top_failures, start=1):
            analysis = self.analyze_failure_5whys(failure)
            lines.append(f"## Failure #{idx}: {analysis['cluster']}")
            lines.append(f"Case: {analysis['case_id']} | Score: {analysis['score']:.2f}")
            lines.append(f"Question: {analysis['question']}")
            lines.append("")
            for key, payload in analysis["five_whys"].items():
                lines.append(f"### {key.upper()}: {payload['question']}")
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
