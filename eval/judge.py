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
    def __init__(self) -> None:
        self.model_cfg = JudgeConfig.JUDGE_MODELS[0]

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
                response = await client.chat.completions.create(
                    model=self.model_cfg["model"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.model_cfg["temperature"],
                    max_tokens=self.model_cfg["max_tokens"],
                )
                parsed = _safe_json_parse(response.choices[0].message.content or "")
                score = float(parsed.get("score", 0.0))
                reasoning = parsed.get("reasoning", "No reasoning returned")
                tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0
                return {
                    "score": max(0.0, min(1.0, score)),
                    "reasoning": reasoning,
                    "model": "gpt4",
                    "tokens_used": int(tokens),
                    "mode": "live_api",
                }
            except Exception as exc:
                fallback_score = _heuristic_score(expected_answer, agent_answer, context)
                return {
                    "score": fallback_score,
                    "reasoning": f"OpenAI fallback due to error: {exc}",
                    "model": "gpt4",
                    "tokens_used": 0,
                    "mode": "heuristic_fallback",
                }

        fallback_score = _heuristic_score(expected_answer, agent_answer, context)
        return {
            "score": fallback_score,
            "reasoning": "OpenAI API key missing; heuristic fallback used",
            "model": "gpt4",
            "tokens_used": 0,
            "mode": "heuristic_fallback",
        }


class AnthropicJudge(JudgeClient):
    def __init__(self) -> None:
        self.model_cfg = JudgeConfig.JUDGE_MODELS[1]

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
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=api_key)
                response = await client.messages.create(
                    model=self.model_cfg["model"],
                    max_tokens=self.model_cfg["max_tokens"],
                    temperature=self.model_cfg["temperature"],
                    messages=[{"role": "user", "content": prompt}],
                )
                content_text = ""
                if response.content and getattr(response.content[0], "text", None):
                    content_text = response.content[0].text

                parsed = _safe_json_parse(content_text)
                score = float(parsed.get("score", 0.0))
                reasoning = parsed.get("reasoning", "No reasoning returned")
                usage = getattr(response, "usage", None)
                tokens = 0
                if usage:
                    tokens = int(getattr(usage, "input_tokens", 0)) + int(getattr(usage, "output_tokens", 0))

                return {
                    "score": max(0.0, min(1.0, score)),
                    "reasoning": reasoning,
                    "model": "claude",
                    "tokens_used": tokens,
                    "mode": "live_api",
                }
            except Exception as exc:
                fallback_base = _heuristic_score(expected_answer, agent_answer, context)
                fallback_score = max(0.0, min(1.0, round(fallback_base * 0.98 + 0.01, 2)))
                return {
                    "score": fallback_score,
                    "reasoning": f"Anthropic fallback due to error: {exc}",
                    "model": "claude",
                    "tokens_used": 0,
                    "mode": "heuristic_fallback",
                }

        fallback_base = _heuristic_score(expected_answer, agent_answer, context)
        fallback_score = max(0.0, min(1.0, round(fallback_base * 0.98 + 0.01, 2)))
        return {
            "score": fallback_score,
            "reasoning": "Anthropic API key missing; heuristic fallback used",
            "model": "claude",
            "tokens_used": 0,
            "mode": "heuristic_fallback",
        }


class MultiJudge:
    def __init__(self) -> None:
        self.judges = {
            "gpt4": OpenAIJudge(),
            "claude": AnthropicJudge(),
        }

    async def judge_case(
        self,
        case_id: str,
        question: str,
        expected_answer: str,
        agent_answer: str,
        context: str,
    ) -> Dict[str, Any]:
        tasks = [
            self.judges["gpt4"].judge(question, expected_answer, agent_answer, context),
            self.judges["claude"].judge(question, expected_answer, agent_answer, context),
        ]
        results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        return {
            "case_id": case_id,
            "judge_scores": results,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
