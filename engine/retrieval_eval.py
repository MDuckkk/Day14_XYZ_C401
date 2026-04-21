import json
import math
from datetime import datetime
from typing import Dict, List


class RetrievalEvaluator:
    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids:
            return 1.0
        top_retrieved = retrieved_ids[:top_k]
        return 1.0 if any(doc_id in top_retrieved for doc_id in expected_ids) else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids:
            return 1.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    def calculate_ndcg(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 5) -> float:
        if not expected_ids:
            return 1.0
        dcg = 0.0
        for rank, doc_id in enumerate(retrieved_ids[:top_k], start=1):
            relevance = 1.0 if doc_id in expected_ids else 0.0
            dcg += relevance / math.log2(rank + 1)
        ideal_hits = min(len(expected_ids), top_k)
        idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
        return dcg / idcg if idcg else 0.0

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        if not dataset:
            return {
                "hit_rate@3": 0.0,
                "hit_rate@5": 0.0,
                "mrr": 0.0,
                "ndcg@5": 0.0,
                "total_cases": 0,
                "timestamp": datetime.now().isoformat(),
            }

        hit3_scores = []
        hit5_scores = []
        mrr_scores = []
        ndcg_scores = []
        for case in dataset:
            expected_ids = case.get("ground_truth_doc_ids") or case.get("expected_retrieval_ids") or []
            retrieved_ids = case.get("retrieved_doc_ids", [])
            hit3_scores.append(self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=3))
            hit5_scores.append(self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=5))
            mrr_scores.append(self.calculate_mrr(expected_ids, retrieved_ids))
            ndcg_scores.append(self.calculate_ndcg(expected_ids, retrieved_ids, top_k=5))

        total = len(dataset)
        return {
            "hit_rate@3": sum(hit3_scores) / total,
            "hit_rate@5": sum(hit5_scores) / total,
            "mrr": sum(mrr_scores) / total,
            "ndcg@5": sum(ndcg_scores) / total,
            "total_cases": total,
            "timestamp": datetime.now().isoformat(),
        }


def load_golden_set(path: str) -> Dict[str, Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return {item["id"]: item for item in (json.loads(line) for line in f if line.strip())}


async def compute_metrics_from_results(benchmark_results_path: str, golden_set_path: str) -> Dict:
    with open(benchmark_results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    golden_set = load_golden_set(golden_set_path)
    merged_rows = []
    for result in results:
        case = golden_set.get(result["case_id"], {})
        merged_rows.append(
            {
                "ground_truth_doc_ids": case.get("ground_truth_doc_ids", []),
                "expected_retrieval_ids": case.get("expected_retrieval_ids", []),
                "retrieved_doc_ids": result.get("retrieved_doc_ids", []),
            }
        )
    evaluator = RetrievalEvaluator()
    return await evaluator.evaluate_batch(merged_rows)
