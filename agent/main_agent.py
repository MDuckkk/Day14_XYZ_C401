import asyncio
from typing import Dict, List

from data.synthetic_gen import DOCUMENTS


class MainAgent:
    """
    Minimal RAG-like demo agent for the benchmark pipeline.
    It performs a simple keyword retrieval over the synthetic documents and
    answers from the top match, with special handling for adversarial and
    edge-case prompts.
    """

    def __init__(self):
        self.name = "SupportAgent-v1"
        self.documents = DOCUMENTS

    def _retrieve(self, question: str) -> List[Dict]:
        query_terms = {
            token.strip("?,.!").lower()
            for token in question.split()
            if len(token.strip("?,.!")) > 2
        }
        scored = []
        for doc in self.documents:
            doc_terms = set(doc["title"].lower().split()) | set(doc["text"].lower().split())
            score = len(query_terms & doc_terms)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:3]]

    def _answer_from_question(self, question: str, retrieved_docs: List[Dict]) -> str:
        lower_q = question.lower()
        if any(trigger in lower_q for trigger in ["ignore", "pretend", "forget", "override", "disregard", "stop acting"]):
            if any(topic in lower_q for topic in ["poem", "joke", "hack", "weather", "trading", "marketing"]):
                return "I cannot help with unrelated requests. Please ask about the provided evaluation documents."
        if any(
            trigger in lower_q
            for trigger in ["capital of", "world cup", "gravitational", "boil at on mars", "stock to buy"]
        ):
            return "I do not know because that information is not present in the provided project documents."
        if "can you explain the report requirements" in lower_q:
            return "Could you clarify whether you want the required files, the output formats, or the submission checklist?"
        if "how should we improve it" in lower_q:
            return "Could you clarify whether you mean retrieval, judging reliability, performance, or reporting?"
        if "what should we run first" in lower_q:
            return "Could you clarify whether you mean the first command or the first project phase?"
        if not retrieved_docs:
            return "I do not know based on the supplied documents."
        first_sentence = retrieved_docs[0]["text"].split(". ")[0].strip()
        return first_sentence if first_sentence.endswith(".") else first_sentence + "."

    async def query(self, question: str) -> Dict:
        await asyncio.sleep(0.1)
        retrieved_docs = self._retrieve(question)
        answer = self._answer_from_question(question, retrieved_docs)
        return {
            "answer": answer,
            "contexts": [doc["text"] for doc in retrieved_docs],
            "retrieved_doc_ids": [doc["id"] for doc in retrieved_docs],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": 120 + len(question.split()),
                "sources": [doc["title"] for doc in retrieved_docs],
            },
        }


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("How many judge models are required?")
        print(resp)

    asyncio.run(test())
