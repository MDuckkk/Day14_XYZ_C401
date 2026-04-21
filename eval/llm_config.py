import os
from dotenv import load_dotenv

load_dotenv()


class JudgeConfig:
    """Configuration for the multi-judge evaluation pipeline."""

    JUDGE_MODELS = [
        {
            "name": "gpt4",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": 0.0,
            "max_tokens": 200,
        },
        {
            "name": "gpt54nano",
            "provider": "openai",
            "model": "gpt-5.4-nano",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": 0.0,
            "max_tokens": 200,
        },
    ]

    JUDGE_PROMPT_TEMPLATE = """
Evaluate the following agent answer against the expected answer.

Question: {question}
Expected Answer: {expected_answer}
Agent Answer: {agent_answer}
Retrieved Context: {context}

Score the agent answer on a scale of 0 to 1.
Return strict JSON format:
{{"score": 0.8, "reasoning": "brief explanation"}}
""".strip()

    BASELINE_METRICS = {
        "avg_score": 0.75,
        "retrieval_hit_rate": 0.80,
        "cost_per_eval": 0.45,
        "judge_agreement": 0.75,
        "latency_avg": 1.5,
    }

    RELEASE_GATE = {
        "min_accuracy": 0.80,
        "max_cost_per_eval": 0.50,
        "max_latency_sec": 2.0,
        "min_judge_agreement": 0.80,
    }
