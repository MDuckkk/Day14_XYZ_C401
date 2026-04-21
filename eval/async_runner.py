import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from agent.main_agent import MainAgent
from eval.consensus import ConsensusEngine
from eval.judge import MultiJudge
from eval.llm_config import JudgeConfig


class AsyncBenchmarkRunner:
    """Run benchmark cases asynchronously with multi-judge scoring."""

    def __init__(self, golden_set_path: str):
        self.golden_set_path = Path(golden_set_path)
        self.golden_set = self._load_golden_set(self.golden_set_path)
        self.agent = MainAgent()
        self.multi_judge = MultiJudge()
        self.results: List[Dict] = []

    def _load_golden_set(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []

        cases: List[Dict] = []
        with path.open(encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                case_id = str(row.get("id") or row.get("case_id") or f"case_{idx:03d}")
                context = row.get("context") or " ".join(row.get("contexts", []))
                metadata = row.get("metadata", {})
                case_type = row.get("case_type") or metadata.get("type") or "fact-check"
                difficulty = row.get("difficulty") or metadata.get("difficulty") or "medium"
                ground_truth_doc_ids = row.get("ground_truth_doc_ids") or metadata.get("ground_truth_doc_ids") or []

                cases.append(
                    {
                        "id": case_id,
                        "question": row.get("question", ""),
                        "expected_answer": row.get("expected_answer", ""),
                        "context": context,
                        "case_type": case_type,
                        "difficulty": difficulty,
                        "ground_truth_doc_ids": ground_truth_doc_ids,
                    }
                )
        return cases

    @staticmethod
    def _compute_hit_rate(expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids:
            return 0.0
        top_retrieved = retrieved_ids[:top_k]
        return 1.0 if any(item in top_retrieved for item in expected_ids) else 0.0

    @staticmethod
    def _compute_mrr(expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids:
            return 0.0
        for i, item in enumerate(retrieved_ids, start=1):
            if item in expected_ids:
                return 1.0 / i
        return 0.0

    async def run_agent(self, question: str) -> Dict:
        start = time.perf_counter()
        response = await self.agent.query(question)
        latency = time.perf_counter() - start

        retrieved_ids = response.get("retrieved_doc_ids") or response.get("metadata", {}).get("retrieved_doc_ids")
        if not retrieved_ids:
            retrieved_ids = response.get("metadata", {}).get("sources") or []

        contexts = response.get("contexts") or []

        return {
            "agent_answer": response.get("answer", ""),
            "retrieved_doc_ids": retrieved_ids,
            "retrieved_context": "\n".join(contexts),
            "latency_sec": round(latency, 4),
            "tokens_used": int(response.get("metadata", {}).get("tokens_used", 0)),
        }

    async def evaluate_case(self, case: Dict) -> Dict:
        case_id = case["id"]
        question = case["question"]
        expected_answer = case["expected_answer"]
        context = case["context"]

        agent_result = await self.run_agent(question)

        judge_result = await self.multi_judge.judge_case(
            case_id=case_id,
            question=question,
            expected_answer=expected_answer,
            agent_answer=agent_result["agent_answer"],
            context=context or agent_result.get("retrieved_context", ""),
        )

        consensus = ConsensusEngine.resolve_conflict(judge_result["judge_scores"])
        expected_doc_ids = case.get("ground_truth_doc_ids", [])
        retrieved_doc_ids = agent_result.get("retrieved_doc_ids", [])

        hit_rate = self._compute_hit_rate(expected_doc_ids, retrieved_doc_ids)
        mrr = self._compute_mrr(expected_doc_ids, retrieved_doc_ids)

        return {
            "case_id": case_id,
            "question": question,
            "expected_answer": expected_answer,
            "agent_answer": agent_result["agent_answer"],
            "retrieved_doc_ids": retrieved_doc_ids,
            "ground_truth_doc_ids": expected_doc_ids,
            "judge_scores": judge_result["judge_scores"],
            "judge_score": consensus["final_score"],
            "judge_agreement": consensus["agreement"],
            "resolution_method": consensus["resolution_method"],
            "retrieval_hit_rate": hit_rate,
            "retrieval_mrr": mrr,
            "latency_sec": agent_result["latency_sec"],
            "tokens_used": agent_result["tokens_used"],
            "case_type": case.get("case_type"),
            "difficulty": case.get("difficulty"),
        }

    async def run_benchmark(self, max_concurrent: int = 5) -> List[Dict]:
        if not self.golden_set:
            self.results = []
            return self.results

        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_limit(single_case: Dict) -> Dict:
            async with semaphore:
                return await self.evaluate_case(single_case)

        tasks = [run_with_limit(case) for case in self.golden_set]
        self.results = await asyncio.gather(*tasks)
        return self.results

    def save_results(self, output_path: str = "reports/benchmark_results.json") -> Dict:
        payload = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_cases": len(self.results),
                "models": [m["name"] for m in JudgeConfig.JUDGE_MODELS],
                "dataset_path": str(self.golden_set_path),
            },
            "results": self.results,
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return payload

    def build_summary(self, version: str) -> Dict:
        total = len(self.results)
        if total == 0:
            metrics = {
                "avg_score": 0.0,
                "hit_rate": 0.0,
                "mrr": 0.0,
                "agreement_rate": 0.0,
                "latency_avg": 0.0,
                "pass_rate": 0.0,
            }
        else:
            metrics = {
                "avg_score": round(sum(r["judge_score"] for r in self.results) / total, 4),
                "hit_rate": round(sum(r["retrieval_hit_rate"] for r in self.results) / total, 4),
                "mrr": round(sum(r["retrieval_mrr"] for r in self.results) / total, 4),
                "agreement_rate": round(sum(r["judge_agreement"] for r in self.results) / total, 4),
                "latency_avg": round(sum(r["latency_sec"] for r in self.results) / total, 4),
                "pass_rate": round(sum(1 for r in self.results if r["judge_score"] >= 0.7) / total, 4),
            }

        return {
            "metadata": {
                "version": version,
                "total": total,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
            "metrics": metrics,
        }
