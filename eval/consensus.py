import math
from datetime import datetime
from typing import Dict, List


class ConsensusEngine:
    """Compute agreement metrics and resolve score conflicts."""

    @staticmethod
    def calculate_agreement_rate(scores: List[float], tolerance: float = 0.2) -> float:
        if len(scores) < 2:
            return 1.0

        agreement_count = 0
        total_pairs = 0
        for i in range(len(scores)):
            for j in range(i + 1, len(scores)):
                total_pairs += 1
                if abs(scores[i] - scores[j]) <= tolerance:
                    agreement_count += 1

        return agreement_count / total_pairs if total_pairs else 1.0

    @staticmethod
    def calculate_cohens_kappa(scores1: List[float], scores2: List[float]) -> float:
        if len(scores1) != len(scores2) or len(scores1) < 2:
            return 1.0

        bins = [0.2, 0.4, 0.6, 0.8, 1.01]

        def _bucket(score: float) -> int:
            for idx, upper in enumerate(bins):
                if score <= upper:
                    return idx
            return len(bins) - 1

        n = len(scores1)
        k = len(bins)
        matrix = [[0 for _ in range(k)] for _ in range(k)]
        for a, b in zip(scores1, scores2):
            matrix[_bucket(a)][_bucket(b)] += 1

        po = sum(matrix[i][i] for i in range(k)) / n
        row_marginals = [sum(matrix[i]) / n for i in range(k)]
        col_marginals = [sum(matrix[r][c] for r in range(k)) / n for c in range(k)]
        pe = sum(row_marginals[i] * col_marginals[i] for i in range(k))

        if math.isclose(1 - pe, 0.0):
            return 1.0
        return (po - pe) / (1 - pe)

    @staticmethod
    def resolve_conflict(judge_scores: List[Dict]) -> Dict:
        scores = [float(j.get("score", 0.0)) for j in judge_scores]
        if not scores:
            return {
                "final_score": 0.0,
                "individual_scores": [],
                "resolution_method": "empty",
                "agreement": 1.0,
            }

        avg_score = sum(scores) / len(scores)
        spread = max(scores) - min(scores)

        if spread > 0.3:
            sorted_scores = sorted(scores)
            mid = len(sorted_scores) // 2
            if len(sorted_scores) % 2 == 1:
                final_score = sorted_scores[mid]
            else:
                final_score = (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
            resolution_method = "median"
        else:
            final_score = avg_score
            resolution_method = "average"

        return {
            "final_score": round(max(0.0, min(1.0, final_score)), 4),
            "individual_scores": judge_scores,
            "resolution_method": resolution_method,
            "agreement": round(ConsensusEngine.calculate_agreement_rate(scores), 4),
        }

    @staticmethod
    def generate_consensus_report(all_case_results: List[Dict]) -> Dict:
        if not all_case_results:
            return {
                "total_cases": 0,
                "avg_agreement_rate": 0.0,
                "avg_score": 0.0,
                "num_conflicts": 0,
                "cohens_kappa": 1.0,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        agreement_rates: List[float] = []
        final_scores: List[float] = []
        judge_a_scores: List[float] = []
        judge_b_scores: List[float] = []

        for row in all_case_results:
            final_scores.append(float(row.get("final_score", 0.0)))
            judge_rows = row.get("individual_scores", [])
            raw_scores = [float(j.get("score", 0.0)) for j in judge_rows]
            agreement_rates.append(ConsensusEngine.calculate_agreement_rate(raw_scores))
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

        return {
            "total_cases": len(all_case_results),
            "avg_agreement_rate": round(sum(agreement_rates) / len(agreement_rates), 4),
            "avg_score": round(sum(final_scores) / len(final_scores), 4),
            "num_conflicts": int(sum(1 for ar in agreement_rates if ar < 0.7)),
            "cohens_kappa": round(kappa, 4),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
