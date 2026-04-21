import json
from collections import Counter, defaultdict
from typing import Dict, List


def load_golden_set(path: str) -> Dict[str, Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return {item["id"]: item for item in (json.loads(line) for line in f if line.strip())}


class FailureAnalyzer:
    def __init__(self, benchmark_results_path: str, golden_set_path: str):
        with open(benchmark_results_path, "r", encoding="utf-8") as f:
            self.results = json.load(f)
        self.golden_set = load_golden_set(golden_set_path)

    def identify_failures(self) -> List[Dict]:
        failures: List[Dict] = []
        for result in self.results:
            case = self.golden_set.get(result["case_id"], {})
            retrieved_ids = result.get("retrieved_doc_ids", [])
            ground_truth = case.get("ground_truth_doc_ids", [])
            hit = bool(set(retrieved_ids) & set(ground_truth)) if ground_truth else True
            judge_score = result.get("judge", {}).get("final_score", 0.0)
            if judge_score >= 3.0 and hit:
                continue
            failures.append(
                {
                    "case_id": result["case_id"],
                    "question": case.get("question", result.get("test_case")),
                    "expected_answer": case.get("expected_answer", ""),
                    "agent_answer": result.get("agent_response", ""),
                    "judge_score": judge_score,
                    "case_type": case.get("case_type", "unknown"),
                    "difficulty": case.get("difficulty", "unknown"),
                    "retrieved_doc_ids": retrieved_ids,
                    "ground_truth_doc_ids": ground_truth,
                    "retrieval_hit": hit,
                }
            )
        return failures

    def _cluster_failure(self, failure: Dict) -> str:
        actual = failure.get("agent_answer", "").lower()
        case_type = failure.get("case_type", "")
        if not failure.get("retrieval_hit") and failure.get("ground_truth_doc_ids"):
            return "retrieval_failure"
        if case_type == "adversarial" and "cannot" not in actual:
            return "instruction_following_failure"
        if case_type == "edge-case" and not any(token in actual for token in ["do not know", "clarify"]):
            return "edge_case_handling_failure"
        return "reasoning_or_generation_failure"

    def cluster_failures(self, failures: List[Dict]) -> Dict[str, List[Dict]]:
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for failure in failures:
            cluster = self._cluster_failure(failure)
            grouped[cluster].append({**failure, "cluster": cluster})
        return dict(grouped)

    def build_summary(self) -> Dict:
        failures = self.identify_failures()
        clusters = self.cluster_failures(failures)
        cluster_counts = Counter({name: len(items) for name, items in clusters.items()})
        total_cases = len(self.results)
        failure_rate = len(failures) / total_cases if total_cases else 0.0
        return {
            "total_cases": total_cases,
            "total_failures": len(failures),
            "failure_rate": failure_rate,
            "clusters": {
                name: {
                    "count": len(items),
                    "percentage": (len(items) / len(failures) * 100) if failures else 0.0,
                    "cases": items,
                }
                for name, items in clusters.items()
            },
            "cluster_counts": dict(cluster_counts),
        }

    def save_json(self, output_path: str) -> Dict:
        summary = self.build_summary()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return summary

    def save_markdown(self, output_path: str, summary: Dict = None) -> None:
        summary = summary or self.build_summary()
        lines = [
            "# Failure Analysis Report",
            "",
            "## Executive Summary",
            f"- Total cases: {summary['total_cases']}",
            f"- Failures: {summary['total_failures']} ({summary['failure_rate']:.1%})",
        ]
        if summary["cluster_counts"]:
            top_cluster = max(summary["cluster_counts"], key=summary["cluster_counts"].get)
            lines.append(f"- Main issue cluster: {top_cluster}")
        else:
            lines.append("- Main issue cluster: none")

        lines.extend(["", "## Cluster Breakdown"])
        if not summary["clusters"]:
            lines.append("- No failing cases were detected.")
        else:
            for name, payload in summary["clusters"].items():
                lines.append(f"- {name}: {payload['count']} cases ({payload['percentage']:.1f}%)")

        top_failures = sorted(
            [case for payload in summary["clusters"].values() for case in payload["cases"]],
            key=lambda item: item["judge_score"],
        )[:5]
        lines.extend(["", "## Top 5 Failure Deep Dive"])
        if not top_failures:
            lines.append("- No failures to analyze.")
        else:
            for idx, failure in enumerate(top_failures, start=1):
                lines.extend(
                    [
                        f"### Failure #{idx}: {failure['case_id']}",
                        f"- Question: {failure['question']}",
                        f"- Cluster: {failure['cluster']}",
                        f"- Judge score: {failure['judge_score']:.2f} / 5.0",
                        f"- Retrieval hit: {'yes' if failure['retrieval_hit'] else 'no'}",
                        f"- Ground truth docs: {', '.join(failure['ground_truth_doc_ids']) or 'none'}",
                        f"- Retrieved docs: {', '.join(failure['retrieved_doc_ids']) or 'none'}",
                        "- Suggested fix: improve retrieval if the gold doc was missed, otherwise tighten answer generation and instruction handling.",
                        "",
                    ]
                )

        lines.extend(
            [
                "## Recommendations",
                "- Expand retrieval coverage for multi-document and comparison questions.",
                "- Strengthen refusal and clarification behavior for adversarial and ambiguous cases.",
                "- Review prompts and answer formatting when retrieval succeeds but judge scores remain low.",
                "",
            ]
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
