import json
import os
import time
from typing import Dict, List


def generate_summary_report(
    benchmark_results: List[Dict],
    retrieval_metrics: Dict,
    failure_summary: Dict,
    agent_version: str,
    judge_consensus: Dict = None,
    release_gate: Dict = None,
) -> Dict:
    total = len(benchmark_results)
    avg_score = (
        sum(item.get("judge", {}).get("final_score", item.get("judge_score", 0.0)) for item in benchmark_results) / total
        if total
        else 0.0
    )
    agreement_rate = (
        sum(item.get("judge", {}).get("agreement_rate", item.get("judge_agreement", 0.0)) for item in benchmark_results) / total
        if total
        else 0.0
    )
    avg_latency = sum(item.get("latency", item.get("latency_sec", 0.0)) for item in benchmark_results) / total if total else 0.0
    avg_tokens = sum(item.get("tokens_used", 0) for item in benchmark_results) / total if total else 0.0
    judge_consensus = judge_consensus or {}
    release_gate = release_gate or {}

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": avg_score,
            "hit_rate": retrieval_metrics.get("hit_rate@5", 0.0),
            "agreement_rate": judge_consensus.get("avg_agreement_rate", agreement_rate),
            "mrr": retrieval_metrics.get("mrr", 0.0),
            "ndcg@5": retrieval_metrics.get("ndcg@5", 0.0),
            "avg_latency_sec": avg_latency,
            "avg_tokens_used": avg_tokens,
            "failure_rate": failure_summary.get("failure_rate", 0.0),
        },
        "retrieval_metrics": retrieval_metrics,
        "judge_metrics": judge_consensus,
        "failure_analysis": {
            "total_failures": failure_summary.get("total_failures", 0),
            "cluster_counts": failure_summary.get("cluster_counts", {}),
        },
        "release_gate": release_gate,
    }


def save_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
