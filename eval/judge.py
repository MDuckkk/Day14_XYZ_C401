import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

from eval.llm_config import JudgeConfig


class JudgeClient:
    async def judge(
        self,
        question: str,
        expected_answer: str,
        agent_answer: str,
        context: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError


def _heuristic_score(expected_answer: str, agent_answer: str, context: str) -> float:
    expected_tokens = {t.lower() for t in expected_answer.split() if len(t) > 2}
    answer_tokens = {t.lower() for t in agent_answer.split() if len(t) > 2}
    context_tokens = {t.lower() for t in context.split() if len(t) > 2}

    if not expected_tokens:
        return 0.5

    overlap_expected = len(expected_tokens & answer_tokens) / max(len(expected_tokens), 1)
    overlap_context = len(answer_tokens & context_tokens) / max(len(answer_tokens), 1) if answer_tokens else 0.0
    raw = (0.75 * overlap_expected) + (0.25 * overlap_context)
    return max(0.0, min(1.0, round(raw, 2)))


def _safe_json_parse(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


class OpenAIJudge(JudgeClient):
    def __init__(self, model_cfg: Dict[str, Any]) -> None:
        self.model_cfg = model_cfg
        self.model_name = model_cfg.get("name", "openai_judge")

    async def judge(
        self,
        question: str,
        expected_answer: str,
        agent_answer: str,
        context: str,
    ) -> Dict[str, Any]:
        prompt = JudgeConfig.JUDGE_PROMPT_TEMPLATE.format(
            question=question,
            expected_answer=expected_answer,
            agent_answer=agent_answer,
            context=(context or "")[:500],
        )

        api_key = self.model_cfg.get("api_key")
        if api_key:
            try:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=api_key)
                request_kwargs: Dict[str, Any] = {
                    "model": self.model_cfg["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.model_cfg["temperature"],
                }
                if str(self.model_cfg["model"]).startswith("gpt-5"):
                    request_kwargs["max_completion_tokens"] = self.model_cfg["max_tokens"]
                else:
                    request_kwargs["max_tokens"] = self.model_cfg["max_tokens"]

                response = await client.chat.completions.create(**request_kwargs)
                parsed = _safe_json_parse(response.choices[0].message.content or "")
                score = float(parsed.get("score", 0.0))
                reasoning = parsed.get("reasoning", "No reasoning returned")
                tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0
                return {
                    "score": max(0.0, min(1.0, score)),
                    "reasoning": reasoning,
                    "model": self.model_name,
                    "tokens_used": int(tokens),
                    "mode": "live_api",
                }
            except Exception as exc:
                fallback_score = _heuristic_score(expected_answer, agent_answer, context)
                return {
                    "score": fallback_score,
                    "reasoning": f"OpenAI fallback due to error: {exc}",
                    "model": self.model_name,
                    "tokens_used": 0,
                    "mode": "heuristic_fallback",
                }

        fallback_score = _heuristic_score(expected_answer, agent_answer, context)
        return {
            "score": fallback_score,
            "reasoning": "OpenAI API key missing; heuristic fallback used",
            "model": self.model_name,
            "tokens_used": 0,
            "mode": "heuristic_fallback",
        }


class MultiJudge:
    def __init__(self) -> None:
        self.judges = [OpenAIJudge(model_cfg) for model_cfg in JudgeConfig.JUDGE_MODELS]

    async def judge_case(
        self,
        case_id: str,
        question: str,
        expected_answer: str,
        agent_answer: str,
        context: str,
    ) -> Dict[str, Any]:
        tasks = [judge.judge(question, expected_answer, agent_answer, context) for judge in self.judges]
        results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        return {
            "case_id": case_id,
            "judge_scores": results,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
