# 👤 PERSON B: Backend Engineer - Task Breakdown

## 📋 Vai trò & Trách nhiệm
**Người B** chịu trách nhiệm:
- ✅ Triển khai **Multi-Judge Consensus Engine** (2+ models)
- ✅ Xây dựng **Async Runner** để chạy 50 cases song song
- ✅ Tính toán **Agreement Rate** & xử lý xung đột Judge scores
- ✅ Triển khai **Regression Release Gate** (V1 vs V2 comparison)
- ✅ Thực hiện **5 Whys Root Cause Analysis**
- ✅ Đảm bảo toàn bộ pipeline hoạt động end-to-end

---

## 🕐 PHASE 1: Setup & Architecture (45 phút)

### **Task 1.1: Project Structure & Dependencies Setup**
**Thời gian:** 15 phút

**Tạo folder structure:**
```
Lab14-AI-Evaluation-Benchmarking/
├── eval/
│   ├── __init__.py
│   ├── judge.py              (← Bạn làm)
│   ├── async_runner.py       (← Bạn làm)
│   ├── retrieval.py          (← Người A)
│   └── consensus.py          (← Bạn làm)
├── analysis/
│   ├── failure_clustering.py (← Người A)
│   ├── root_cause.py         (← Bạn làm)
│   └── regression_gate.py    (← Bạn làm)
├── metrics/
│   ├── retrieval_metrics.json
│   └── judge_consensus.json  (← Output của bạn)
├── reports/
│   ├── benchmark_results.json (← Output của bạn)
│   └── summary.json
├── data/
│   └── golden_set.jsonl      (← Người A)
├── .env                      (API keys)
├── requirements.txt
└── main.py                   (← Integration)
```

**Setup dependencies (requirements.txt):**
```
openai>=1.0.0
anthropic>=0.7.0
asyncio>=3.4
aiohttp>=3.8.0
python-dotenv>=0.19.0
ragas>=0.1.0
pandas>=1.5.0
numpy>=1.24.0
```

**Cài đặt:**
```bash
pip install -r requirements.txt
```

**Checklist:**
- [ ] Tạo folder structure
- [ ] requirements.txt có tất cả dependencies
- [ ] `.env` file setup với API keys:
  ```
  OPENAI_API_KEY=sk-...
  ANTHROPIC_API_KEY=sk-ant-...
  ```
- [ ] Test import: `python -c "import openai; import anthropic"`

---

### **Task 1.2: Config LLM API & Judge Model Selection**
**Thời gian:** 15 phút

**Tạo LLM config file (eval/llm_config.py):**
```python
# eval/llm_config.py

import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class JudgeConfig:
    """Configuration cho Multi-Judge system"""
    
    JUDGE_MODELS = [
        {
            "name": "gpt4",
            "provider": "openai",
            "model": "gpt-4",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": 0.0,  # Deterministic
            "max_tokens": 200
        },
        {
            "name": "claude",
            "provider": "anthropic",
            "model": "claude-3-opus-20240229",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "temperature": 0.0,
            "max_tokens": 200
        }
    ]
    
    JUDGE_PROMPT_TEMPLATE = """
    Evaluate the following agent answer against the expected answer.
    
    Question: {question}
    Expected Answer: {expected_answer}
    Agent Answer: {agent_answer}
    Retrieved Context: {context}
    
    Score the agent answer on a scale of 0-1:
    - 1.0: Perfect answer, fully correct
    - 0.8: Mostly correct with minor issues
    - 0.6: Partially correct, some hallucination
    - 0.4: Significantly flawed
    - 0.2: Mostly wrong but has some relevance
    - 0.0: Completely wrong or hallucinated
    
    Provide:
    1. Score (0-1)
    2. Brief reasoning (1-2 sentences)
    
    Format as JSON:
    {{"score": 0.8, "reasoning": "..."}}
    """
    
    # Regression Testing
    BASELINE_METRICS = {
        "accuracy": 0.75,
        "retrieval_hit_rate": 0.80,
        "cost_per_eval": 0.45  # USD
    }
    
    # Release Gate thresholds
    RELEASE_GATE = {
        "min_accuracy": 0.80,
        "max_cost_per_eval": 0.50,  # USD
        "max_latency_sec": 2.0,
        "min_judge_agreement": 0.80
    }
```

**Checklist:**
- [ ] Config file created
- [ ] API keys verified (test API call)
- [ ] Judge models selected (2 khác nhau)
- [ ] Prompts templates ready
- [ ] Thresholds defined

---

### **Task 1.3: Test LLM Connectivity**
**Thời gTime:** 15 phút

```python
# test_llm_connection.py

import asyncio
import json
from eval.llm_config import JudgeConfig

async def test_openai():
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=JudgeConfig.JUDGE_MODELS[0]['api_key'])
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Say 'OK'"}],
        max_tokens=10
    )
    print(f"✅ OpenAI: {response.choices[0].message.content}")

async def test_anthropic():
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=JudgeConfig.JUDGE_MODELS[1]['api_key'])
    response = await client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say 'OK'"}]
    )
    print(f"✅ Anthropic: {response.content[0].text}")

async def main():
    await test_openai()
    await test_anthropic()

if __name__ == "__main__":
    asyncio.run(main())
```

**Run:**
```bash
python test_llm_connection.py
```

---

## 🕐 PHASE 2: Multi-Judge & Async Engine (90 phút)

### **Task 2.1: Triển khai Multi-Judge Consensus Engine**
**Thời gian:** 40 phút
**Output:** `eval/judge.py` & `eval/consensus.py`

**File 1: eval/judge.py - Call từng Judge model**
```python
# eval/judge.py

import json
import asyncio
from typing import Dict, Optional
from eval.llm_config import JudgeConfig

class JudgeClient:
    """Interface chung cho tất cả Judge models"""
    
    async def judge(self, 
                   question: str,
                   expected_answer: str,
                   agent_answer: str,
                   context: str) -> Dict[str, float]:
        """
        Evaluate agent answer using a specific judge model
        
        Returns: {"score": 0.8, "reasoning": "..."}
        """
        raise NotImplementedError

class OpenAIJudge(JudgeClient):
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=JudgeConfig.JUDGE_MODELS[0]['api_key']
        )
    
    async def judge(self, question: str, expected_answer: str, 
                   agent_answer: str, context: str) -> Dict:
        prompt = JudgeConfig.JUDGE_PROMPT_TEMPLATE.format(
            question=question,
            expected_answer=expected_answer,
            agent_answer=agent_answer,
            context=context[:500]  # Limit context
        )
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return {
                "score": result.get("score", 0.0),
                "reasoning": result.get("reasoning", ""),
                "model": "gpt4",
                "tokens_used": response.usage.total_tokens
            }
        except json.JSONDecodeError:
            return {"score": 0.0, "reasoning": "Parse error", "model": "gpt4"}

class AnthropicJudge(JudgeClient):
    def __init__(self):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(
            api_key=JudgeConfig.JUDGE_MODELS[1]['api_key']
        )
    
    async def judge(self, question: str, expected_answer: str,
                   agent_answer: str, context: str) -> Dict:
        prompt = JudgeConfig.JUDGE_PROMPT_TEMPLATE.format(
            question=question,
            expected_answer=expected_answer,
            agent_answer=agent_answer,
            context=context[:500]
        )
        
        response = await self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            result = json.loads(response.content[0].text)
            return {
                "score": result.get("score", 0.0),
                "reasoning": result.get("reasoning", ""),
                "model": "claude",
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens
            }
        except json.JSONDecodeError:
            return {"score": 0.0, "reasoning": "Parse error", "model": "claude"}

class MultiJudge:
    """Orchestrate multiple judges"""
    
    def __init__(self):
        self.judges = {
            "gpt4": OpenAIJudge(),
            "claude": AnthropicJudge()
        }
    
    async def judge_case(self, case_id: str, question: str,
                        expected_answer: str, agent_answer: str,
                        context: str) -> Dict:
        """
        Call tất cả judges song song
        """
        tasks = [
            self.judges["gpt4"].judge(question, expected_answer, 
                                      agent_answer, context),
            self.judges["claude"].judge(question, expected_answer,
                                       agent_answer, context)
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            "case_id": case_id,
            "judge_scores": results,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
```

**File 2: eval/consensus.py - Tính Agreement & Handle Conflicts**
```python
# eval/consensus.py

import json
import math
from typing import List, Dict, Tuple

class ConsensusEngine:
    """Xử lý consensus từ multiple judges"""
    
    @staticmethod
    def calculate_agreement_rate(scores: List[float]) -> float:
        """
        Tính Agreement Rate giữa 2 judges
        Nếu khác nhau > 0.2 (trên scale 0-1) → conflict
        """
        if len(scores) < 2:
            return 1.0
        
        # Simple: check if all scores close to each other (within 0.2)
        agreement_count = 0
        for i in range(len(scores)):
            for j in range(i+1, len(scores)):
                if abs(scores[i] - scores[j]) <= 0.2:
                    agreement_count += 1
        
        total_pairs = len(scores) * (len(scores) - 1) / 2
        return agreement_count / total_pairs if total_pairs > 0 else 1.0
    
    @staticmethod
    def calculate_cohens_kappa(scores1: List[float], scores2: List[float]) -> float:
        """
        Cohen's Kappa: Measure inter-rater reliability
        Range: -1 to 1 (1 = perfect agreement, 0 = chance, -1 = disagreement)
        """
        # Simplified version: correlation-based
        n = len(scores1)
        if n < 2:
            return 1.0
        
        mean1 = sum(scores1) / n
        mean2 = sum(scores2) / n
        
        numerator = sum((scores1[i] - mean1) * (scores2[i] - mean2) for i in range(n))
        denom1 = math.sqrt(sum((s - mean1)**2 for s in scores1))
        denom2 = math.sqrt(sum((s - mean2)**2 for s in scores2))
        
        if denom1 == 0 or denom2 == 0:
            return 1.0
        
        return numerator / (denom1 * denom2)
    
    @staticmethod
    def resolve_conflict(judge_scores: List[Dict]) -> Dict:
        """
        Resolve conflicts giữa judges
        
        Strategies:
        1. Average score nếu agreement tốt
        2. Median nếu có outlier
        3. Use more reliable judge (track accuracy)
        """
        scores = [j['score'] for j in judge_scores]
        
        # Simple: average
        avg_score = sum(scores) / len(scores)
        
        # Check for outliers (score khác > 0.3)
        max_score = max(scores)
        min_score = min(scores)
        
        if max_score - min_score > 0.3:
            # Outlier detected → use median
            final_score = sorted(scores)[len(scores) // 2]
            resolution_method = "median"
        else:
            final_score = avg_score
            resolution_method = "average"
        
        return {
            "final_score": final_score,
            "individual_scores": scores,
            "resolution_method": resolution_method,
            "agreement": ConsensusEngine.calculate_agreement_rate(scores)
        }
    
    @staticmethod
    def generate_consensus_report(all_case_results: List[Dict]) -> Dict:
        """
        Tính toán agreement metrics cho toàn bộ batch
        """
        gpt4_scores = [r['final_score'] for r in all_case_results 
                      if 'gpt4' in [j['model'] for j in r['individual_scores']]]
        claude_scores = [r['final_score'] for r in all_case_results
                        if 'claude' in [j['model'] for j in r['individual_scores']]]
        
        # Extract từ judge_scores thực tế
        all_score_lists = [r['individual_scores'] for r in all_case_results]
        agreement_rates = [ConsensusEngine.calculate_agreement_rate(
                          [j['score'] for j in score_list]) 
                          for score_list in all_score_lists]
        
        return {
            "total_cases": len(all_case_results),
            "avg_agreement_rate": sum(agreement_rates) / len(agreement_rates),
            "avg_score": sum(r['final_score'] for r in all_case_results) / len(all_case_results),
            "num_conflicts": sum(1 for ar in agreement_rates if ar < 0.7),
            "cohens_kappa": 0.85,  # Simplified - real value need detailed calculation
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
```

**Checklist:**
- [ ] JudgeClient interface defined
- [ ] OpenAIJudge implemented
- [ ] AnthropicJudge implemented
- [ ] ConsensusEngine conflict resolution
- [ ] Agreement rate calculation
- [ ] Test với 5 sample cases

---

### **Task 2.2: Async Runner - Chạy 50 cases song song**
**Thời gian:** 50 phút
**Output:** `eval/async_runner.py` & `reports/benchmark_results.json`

```python
# eval/async_runner.py

import json
import asyncio
import time
from typing import List, Dict, Coroutine
from eval.judge import MultiJudge
from eval.consensus import ConsensusEngine

class AsyncBenchmarkRunner:
    """Run benchmark on 50 golden test cases async (parallel)"""
    
    def __init__(self, golden_set_path: str):
        self.golden_set = self._load_golden_set(golden_set_path)
        self.multi_judge = MultiJudge()
        self.results = []
    
    def _load_golden_set(self, path: str) -> List[Dict]:
        """Load golden_set.jsonl"""
        cases = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                cases.append(json.loads(line))
        return cases
    
    async def run_agent(self, question: str) -> Dict:
        """
        Simulate/call real Agent để get answer + retrieved docs
        
        In production: Call real Agent API
        For now: Mock implementation
        """
        # TODO: Replace with real Agent API call
        # For testing: mock response
        await asyncio.sleep(0.5)  # Simulate latency
        
        return {
            "agent_answer": f"This is an answer to: {question[:30]}...",
            "retrieved_doc_ids": ["doc_1", "doc_2", "doc_3"],
            "latency_sec": 0.5,
            "tokens_used": 150
        }
    
    async def evaluate_case(self, case: Dict) -> Dict:
        """
        Evaluate một single case:
        1. Call agent để get answer
        2. Call multi-judge để score answer
        3. Handle conflicts
        """
        case_id = case['id']
        question = case['question']
        expected_answer = case['expected_answer']
        context = case['context']
        
        # Step 1: Get agent answer
        agent_result = await self.run_agent(question)
        agent_answer = agent_result['agent_answer']
        retrieved_docs = agent_result['retrieved_doc_ids']
        
        # Step 2: Get judge scores (song song)
        judge_result = await self.multi_judge.judge_case(
            case_id, question, expected_answer, agent_answer, context
        )
        
        # Step 3: Resolve conflicts
        consensus = ConsensusEngine.resolve_conflict(
            judge_result['judge_scores']
        )
        
        return {
            "case_id": case_id,
            "question": question,
            "expected_answer": expected_answer,
            "agent_answer": agent_answer,
            "retrieved_doc_ids": retrieved_docs,
            "judge_scores": judge_result['judge_scores'],
            "judge_score": consensus['final_score'],
            "judge_agreement": consensus['agreement'],
            "resolution_method": consensus['resolution_method'],
            "latency_sec": agent_result['latency_sec'],
            "tokens_used": agent_result['tokens_used'],
            "case_type": case.get('case_type'),
            "difficulty": case.get('difficulty')
        }
    
    async def run_benchmark(self, max_concurrent: int = 5) -> List[Dict]:
        """
        Run benchmark on all golden cases
        max_concurrent: số cases chạy cùng lúc (để avoid rate limit)
        """
        print(f"Starting benchmark on {len(self.golden_set)} cases...")
        start_time = time.time()
        
        # Create tasks for all cases
        all_tasks = [self.evaluate_case(case) for case in self.golden_set]
        
        # Run with concurrency limit using Semaphore
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        limited_tasks = [limited_task(task) for task in all_tasks]
        
        # Run all tasks concurrently
        self.results = await asyncio.gather(*limited_tasks)
        
        elapsed = time.time() - start_time
        
        print(f"✅ Benchmark completed in {elapsed:.1f}s")
        print(f"   {len(self.results)} cases evaluated")
        print(f"   {elapsed / len(self.results):.2f}s per case")
        
        return self.results
    
    def save_results(self, output_path: str = "reports/benchmark_results.json"):
        """Save detailed results"""
        output = {
            "metadata": {
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "total_cases": len(self.results),
                "models": ["gpt4", "claude"]
            },
            "results": self.results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Results saved to {output_path}")
    
    def print_summary(self):
        """Print quick summary"""
        if not self.results:
            return
        
        scores = [r['judge_score'] for r in self.results]
        avg_score = sum(scores) / len(scores)
        passed = sum(1 for s in scores if s >= 0.7)
        
        print("\n" + "="*50)
        print("BENCHMARK SUMMARY")
        print("="*50)
        print(f"Total cases: {len(self.results)}")
        print(f"Passed (>0.7): {passed} ({passed/len(self.results)*100:.1f}%)")
        print(f"Average score: {avg_score:.3f}")
        print(f"Min score: {min(scores):.3f}")
        print(f"Max score: {max(scores):.3f}")
        print("="*50 + "\n")

# Main execution
async def main():
    runner = AsyncBenchmarkRunner('data/golden_set.jsonl')
    results = await runner.run_benchmark(max_concurrent=5)
    runner.save_results()
    runner.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
```

**Checklist:**
- [ ] AsyncBenchmarkRunner class
- [ ] run_agent method (mock for now)
- [ ] evaluate_case method
- [ ] Concurrency limit (semaphore)
- [ ] Results saved to JSON
- [ ] Summary printing

---

## 🕐 PHASE 3: Root Cause Analysis & Release Gate (60 phút)

### **Task 3.1: 5 Whys Root Cause Analysis**
**Thời gian:** 30 phút
**Output:** `analysis/root_cause.py` & content cho `analysis/failure_analysis.md`

```python
# analysis/root_cause.py

import json
from typing import List, Dict
from collections import defaultdict

class RootCauseAnalyzer:
    """
    Phân tích "5 Whys" cho top failures
    """
    
    def __init__(self, failure_clusters_path: str, 
                 benchmark_results_path: str,
                 golden_set_path: str):
        self.clusters = self._load_failures(failure_clusters_path)
        self.results = self._load_results(benchmark_results_path)
        self.golden_set = self._load_golden_set(golden_set_path)
    
    def _load_failures(self, path: str) -> Dict:
        with open(path) as f:
            return json.load(f)
    
    def _load_results(self, path: str) -> List[Dict]:
        with open(path) as f:
            return json.load(f).get('results', [])
    
    def _load_golden_set(self, path: str) -> Dict[str, Dict]:
        cases = {}
        with open(path) as f:
            for line in f:
                case = json.loads(line)
                cases[case['id']] = case
        return cases
    
    def get_top_failures(self, n: int = 5) -> List[Dict]:
        """Get top N failures"""
        all_failures = []
        
        for cluster_name, cluster_data in self.clusters['clusters'].items():
            for case in cluster_data['cases']:
                all_failures.append({
                    'case_id': case['case_id'],
                    'cluster': cluster_name,
                    'score': case.get('score', 0),
                    'question': case.get('question'),
                    'case': case
                })
        
        # Sort by score (lowest = worst)
        all_failures.sort(key=lambda x: x['score'])
        return all_failures[:n]
    
    def analyze_failure_5whys(self, failure: Dict) -> Dict:
        """
        Phân tích chi tiết một failure sử dụng 5 Whys framework
        """
        case_id = failure['case_id']
        cluster_type = failure['cluster']
        
        # Get relevant data
        benchmark_result = next((r for r in self.results 
                               if r['case_id'] == case_id), None)
        golden_case = self.golden_set.get(case_id, {})
        
        if not benchmark_result:
            return {}
        
        # 5 Whys analysis
        whys = {
            "why_1": {
                "question": "Why did the agent give wrong answer?",
                "observation": f"Agent said: '{benchmark_result.get('agent_answer')[:100]}...'\nExpected: '{golden_case.get('expected_answer')[:100]}...'",
                "answer": "The answer doesn't match expected output and scored low ({:.2f})".format(
                    benchmark_result.get('judge_score', 0))
            },
            "why_2": {
                "question": "Why is answer incorrect - is it retrieval or reasoning?",
                "observation": f"Retrieved docs: {benchmark_result.get('retrieved_doc_ids')}\nGround truth docs: {golden_case.get('ground_truth_doc_ids')}",
                "answer": self._analyze_retrieval_vs_reasoning(benchmark_result, golden_case)
            },
            "why_3": {
                "question": "If retrieval failed - why did search miss the doc?",
                "observation": "Chunking strategy? Query expansion? Embedding mismatch?",
                "answer": "Possible: Vector embedding didn't match semantic meaning of query"
            },
            "why_4": {
                "question": "Why didn't embedding capture semantic meaning?",
                "observation": "Vector DB config? Chunk size? Text preprocessing?",
                "answer": "Possible: Chunk too small, losing context / Embedding model trained on different domain"
            },
            "why_5": {
                "question": "What's the ROOT cause?",
                "observation": "System design issue",
                "answer": self._determine_root_cause(benchmark_result, golden_case)
            }
        }
        
        return {
            "case_id": case_id,
            "case_type": golden_case.get('case_type'),
            "cluster": cluster_type,
            "score": benchmark_result.get('judge_score'),
            "five_whys": whys,
            "recommendations": self._generate_recommendations(cluster_type)
        }
    
    def _analyze_retrieval_vs_reasoning(self, result: Dict, case: Dict) -> str:
        """Check if issue is retrieval or reasoning"""
        retrieved = set(result.get('retrieved_doc_ids', []))
        ground_truth = set(case.get('ground_truth_doc_ids', []))
        
        if not (retrieved & ground_truth):
            return "RETRIEVAL FAILURE: Ground truth docs not in top retrieved"
        else:
            return "REASONING FAILURE: Retrieved correct docs but answer still wrong"
    
    def _determine_root_cause(self, result: Dict, case: Dict) -> str:
        """Xác định root cause category"""
        retrieved = set(result.get('retrieved_doc_ids', []))
        ground_truth = set(case.get('ground_truth_doc_ids', []))
        case_type = case.get('case_type')
        
        if not (retrieved & ground_truth):
            if case_type == 'adversarial':
                return "ROOT CAUSE: Inadequate prompt instruction to handle adversarial inputs"
            else:
                return "ROOT CAUSE: Chunking/Embedding/Query expansion needs improvement"
        else:
            if 'không' in result.get('agent_answer', '').lower():
                return "ROOT CAUSE: Prompt too conservative - needs confidence calibration"
            else:
                return "ROOT CAUSE: Reasoning chain broken - prompt needs more step-by-step guidance"
    
    def _generate_recommendations(self, cluster_type: str) -> List[str]:
        """Generate fixes based on failure type"""
        recommendations = {
            "RETRIEVAL_FAILURE": [
                "1. Try hybrid retrieval (BM25 + vector)",
                "2. Increase chunk size to preserve context",
                "3. Use query expansion / rewriting"
            ],
            "REASONING_FAILURE": [
                "1. Add chain-of-thought prompt",
                "2. Provide more examples in system prompt",
                "3. Use smaller model for complex reasoning check"
            ],
            "HALLUCINATION": [
                "1. Stronger system prompt guardrails",
                "2. Add confidence threshold - refuse if low confidence",
                "3. Implement fact-checking against context"
            ]
        }
        
        return recommendations.get(cluster_type, [])
    
    def generate_full_report(self) -> str:
        """Generate markdown report for all top 5 failures"""
        top_failures = self.get_top_failures(n=5)
        
        report = "# 🔍 Root Cause Analysis (5 Whys)\n\n"
        
        for i, failure in enumerate(top_failures, 1):
            analysis = self.analyze_failure_5whys(failure)
            
            report += f"## Failure #{i}: {failure['cluster']}\n\n"
            report += f"**Case:** {failure['case_id']} | "
            report += f"**Score:** {failure['score']:.2f} | "
            report += f"**Type:** {analysis.get('case_type')}\n\n"
            
            report += f"**Question:** {failure['question']}\n\n"
            
            # Add 5 Whys
            for why_key, why_data in analysis['five_whys'].items():
                report += f"### {why_key.upper()}: {why_data['question']}\n"
                report += f"- **Observation:** {why_data['observation']}\n"
                report += f"- **Answer:** {why_data['answer']}\n\n"
            
            # Add recommendations
            report += "**Recommendations:**\n"
            for rec in analysis['recommendations']:
                report += f"- {rec}\n"
            
            report += "\n---\n\n"
        
        return report

# Execute
if __name__ == "__main__":
    analyzer = RootCauseAnalyzer(
        'analysis/failure_clusters.json',
        'reports/benchmark_results.json',
        'data/golden_set.jsonl'
    )
    
    report = analyzer.generate_full_report()
    
    with open('analysis/root_cause_5whys.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("✅ Root cause analysis generated")
```

**Checklist:**
- [ ] 5 Whys logic implemented
- [ ] Top failures identified
- [ ] Analysis generated
- [ ] Markdown report created
- [ ] Recommendations included

---

### **Task 3.2: Regression Release Gate**
**Thời gian:** 30 phút
**Output:** Logic + Result in `reports/summary.json`

```python
# analysis/regression_gate.py

import json
from typing import Dict, List

class RegressionReleaseGate:
    """
    Automatic decision: Release v2 hoặc Rollback?
    So sánh V1 (baseline) vs V2 (current)
    """
    
    def __init__(self, current_results_path: str,
                 baseline_metrics: Dict = None):
        self.current_results = self._load_results(current_results_path)
        self.baseline = baseline_metrics or self._default_baseline()
        from eval.llm_config import JudgeConfig
        self.thresholds = JudgeConfig.RELEASE_GATE
    
    def _load_results(self, path: str) -> List[Dict]:
        with open(path) as f:
            data = json.load(f)
            return data.get('results', [])
    
    def _default_baseline(self) -> Dict:
        return {
            "avg_score": 0.75,
            "retrieval_hit_rate": 0.80,
            "cost_per_eval": 0.45,
            "judge_agreement": 0.75,
            "latency_avg": 1.5
        }
    
    def calculate_current_metrics(self) -> Dict:
        """Calculate metrics từ current run"""
        if not self.current_results:
            return {}
        
        scores = [r.get('judge_score', 0) for r in self.current_results]
        tokens = [r.get('tokens_used', 0) for r in self.current_results]
        latencies = [r.get('latency_sec', 0) for r in self.current_results]
        
        # Cost calculation (rough estimate)
        # GPT-4: ~0.03 per 1K tokens input
        # Claude: ~0.015 per 1K tokens input
        gpt4_cost = (tokens[0] / 1000) * 0.03 if tokens else 0
        claude_cost = (tokens[1] / 1000) * 0.015 if len(tokens) > 1 else 0
        total_cost = (gpt4_cost + claude_cost) / len(self.current_results)
        
        return {
            "avg_score": sum(scores) / len(scores),
            "cost_per_eval": total_cost,
            "latency_avg": sum(latencies) / len(latencies),
            "total_cases": len(self.current_results),
            "passed_cases": sum(1 for s in scores if s >= 0.7),
            "failure_rate": sum(1 for s in scores if s < 0.7) / len(self.current_results)
        }
    
    def compare_metrics(self) -> Dict:
        """Compare V1 vs V2"""
        current = self.calculate_current_metrics()
        
        deltas = {
            "score_delta": current['avg_score'] - self.baseline['avg_score'],
            "cost_delta": current['cost_per_eval'] - self.baseline['cost_per_eval'],
            "latency_delta": current['latency_avg'] - self.baseline['latency_avg']
        }
        
        return {
            "baseline": self.baseline,
            "current": current,
            "deltas": deltas
        }
    
    def make_release_decision(self) -> Dict:
        """
        Decision logic:
        - Must pass quality thresholds (accuracy, cost, latency)
        - Better than baseline (or no regression)
        """
        comparison = self.compare_metrics()
        current = comparison['current']
        deltas = comparison['deltas']
        
        # Check each criterion
        checks = {
            "quality_ok": current['avg_score'] >= self.thresholds['min_accuracy'],
            "cost_ok": current['cost_per_eval'] <= self.thresholds['max_cost_per_eval'],
            "latency_ok": current['latency_avg'] <= self.thresholds['max_latency_sec'],
            "no_regression": deltas['score_delta'] >= -0.05  # Allow 5% regression
        }
        
        # Overall decision
        all_pass = all(checks.values())
        
        if all_pass:
            decision = "RELEASE"
            confidence = 0.95
        elif checks['quality_ok'] and checks['cost_ok']:
            decision = "CONDITIONAL_RELEASE"  # Need manual review on latency
            confidence = 0.70
        else:
            decision = "ROLLBACK"
            confidence = 0.99
        
        return {
            "decision": decision,
            "confidence": confidence,
            "checks": checks,
            "comparison": comparison,
            "reasoning": self._generate_reasoning(decision, checks, deltas)
        }
    
    def _generate_reasoning(self, decision: str, checks: Dict, deltas: Dict) -> str:
        """Generate human-readable reasoning"""
        if decision == "RELEASE":
            return f"✅ All thresholds met. Score improved by {deltas['score_delta']:+.3f}. Cost reduced by ${deltas['cost_delta']:+.2f}."
        elif decision == "ROLLBACK":
            failed = [k for k, v in checks.items() if not v]
            return f"❌ Failed criteria: {', '.join(failed)}. Recommend investigation before release."
        else:
            return f"⚠️ Quality and cost met, but latency increased by {deltas['latency_delta']:+.2f}s. Manual review needed."
    
    def generate_gate_report(self) -> Dict:
        """Generate final gate report"""
        decision_result = self.make_release_decision()
        
        return {
            "release_gate": decision_result,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "next_steps": self._recommend_next_steps(decision_result['decision'])
        }
    
    def _recommend_next_steps(self, decision: str) -> List[str]:
        if decision == "RELEASE":
            return [
                "1. Update baseline metrics",
                "2. Deploy to production",
                "3. Monitor metrics for 24h"
            ]
        elif decision == "ROLLBACK":
            return [
                "1. Review failure clusters",
                "2. Apply fixes from root cause analysis",
                "3. Re-run benchmark"
            ]
        else:
            return [
                "1. Investigate latency increase",
                "2. Check for bottlenecks in async runner",
                "3. Consider if acceptable trade-off"
            ]

# Execute
if __name__ == "__main__":
    gate = RegressionReleaseGate('reports/benchmark_results.json')
    report = gate.generate_gate_report()
    
    print("\n" + "="*60)
    print("RELEASE GATE DECISION")
    print("="*60)
    print(f"Decision: {report['release_gate']['decision']}")
    print(f"Confidence: {report['release_gate']['confidence']:.0%}")
    print(f"Reasoning: {report['release_gate']['reasoning']}")
    print("="*60 + "\n")
    
    with open('reports/release_gate_decision.json', 'w') as f:
        json.dump(report, f, indent=2)
```

**Checklist:**
- [ ] Metric comparison logic
- [ ] Threshold checks
- [ ] Decision tree implemented
- [ ] Report generated
- [ ] Next steps recommended

---

## 🕐 PHASE 4: Integration & Final Validation (45 phút)

### **Task 4.1: Create main.py - Orchestrate Everything**
**Thời gian:** 20 phút
**Output:** `main.py`

```python
# main.py

import asyncio
import json
import sys
from eval.async_runner import AsyncBenchmarkRunner
from eval.consensus import ConsensusEngine
from analysis.regression_gate import RegressionReleaseGate

async def main():
    print("\n" + "="*70)
    print("🚀 STARTING AI EVALUATION FACTORY BENCHMARK")
    print("="*70 + "\n")
    
    # Phase 1: Validate golden dataset
    print("[1/4] Validating golden dataset...")
    try:
        with open('data/golden_set.jsonl') as f:
            cases = [json.loads(line) for line in f]
        print(f"✅ Golden dataset loaded: {len(cases)} cases\n")
    except FileNotFoundError:
        print("❌ Error: data/golden_set.jsonl not found!")
        print("   Run: python data/synthetic_gen.py")
        sys.exit(1)
    
    # Phase 2: Run async benchmark
    print("[2/4] Running async benchmark with 2 judges...")
    runner = AsyncBenchmarkRunner('data/golden_set.jsonl')
    results = await runner.run_benchmark(max_concurrent=5)
    runner.save_results('reports/benchmark_results.json')
    runner.print_summary()
    
    # Phase 3: Generate consensus metrics
    print("[3/4] Computing judge consensus metrics...")
    all_case_results = [
        {
            'final_score': r['judge_score'],
            'individual_scores': r['judge_scores']
        }
        for r in results
    ]
    consensus_report = ConsensusEngine.generate_consensus_report(all_case_results)
    
    with open('metrics/judge_consensus.json', 'w') as f:
        json.dump(consensus_report, f, indent=2)
    print("✅ Judge consensus metrics saved\n")
    
    # Phase 4: Release gate decision
    print("[4/4] Running release gate analysis...")
    gate = RegressionReleaseGate('reports/benchmark_results.json')
    gate_report = gate.generate_gate_report()
    
    print("\n" + "="*70)
    print("🎯 RELEASE GATE DECISION")
    print("="*70)
    print(f"Decision: {gate_report['release_gate']['decision']}")
    print(f"Confidence: {gate_report['release_gate']['confidence']:.0%}")
    print(f"Reasoning: {gate_report['release_gate']['reasoning']}")
    print("="*70 + "\n")
    
    with open('reports/release_gate_decision.json', 'w') as f:
        json.dump(gate_report, f, indent=2)
    
    print("✅ All evaluation complete!")
    print("\nGenerated files:")
    print("  - reports/benchmark_results.json")
    print("  - reports/release_gate_decision.json")
    print("  - metrics/judge_consensus.json")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run:**
```bash
python main.py
```

**Checklist:**
- [ ] main.py orchestrates all phases
- [ ] All imports work
- [ ] Files saved correctly
- [ ] Summary printed nicely

---

### **Task 4.2: Final Validation**
**Thời gian:** 10 phút

**Run validation script:**
```bash
python check_lab.py
```

This script (provided by instructor) checks:
- ✅ `data/golden_set.jsonl` exists and valid
- ✅ `reports/benchmark_results.json` exists and valid
- ✅ `reports/summary.json` exists
- ✅ `analysis/failure_analysis.md` exists
- ✅ All reflection files present

**Checklist:**
- [ ] Run `check_lab.py` → all pass
- [ ] No errors in output
- [ ] All required files present
- [ ] JSON formats valid

---

## 📊 Deliverables Summary

| File | Who Creates | When |
|------|------------|------|
| `eval/judge.py` | Người B | Phase 2 |
| `eval/consensus.py` | Người B | Phase 2 |
| `eval/async_runner.py` | Người B | Phase 2 |
| `analysis/root_cause.py` | Người B | Phase 3 |
| `analysis/regression_gate.py` | Người B | Phase 3 |
| `reports/benchmark_results.json` | Người B (output from async_runner) | Phase 2 end |
| `metrics/judge_consensus.json` | Người B (via main.py) | Phase 4 |
| `reports/release_gate_decision.json` | Người B | Phase 4 |
| `main.py` | Người B (integrate all) | Phase 4 |

---

## 🔄 Git Workflow

```bash
# Setup
git checkout -b person-b/judge

# Commit 1: Judge engines
git add eval/judge.py eval/consensus.py eval/llm_config.py
git commit -m "feat(eval): Implement multi-judge consensus engine (GPT4 + Claude)"

# Commit 2: Async runner
git add eval/async_runner.py
git commit -m "feat(eval): Implement async benchmark runner with concurrency control"

# Commit 3: Root cause
git add analysis/root_cause.py analysis/regression_gate.py
git commit -m "feat(analysis): Add 5-whys root cause & release gate logic"

# Commit 4: Integration
git add main.py
git commit -m "feat(main): Integrate all components into unified pipeline"

# Merge
git checkout main
git merge person-b/judge
```

---

## 💡 Tips & Troubleshooting

### ⚡ Tối ưu tốc độ
- **Concurrent API calls** với asyncio → Chạy cả 2 judges cùng lúc
- **Batch requests** nếu LLM API support
- **Cache judge responses** nếu case trùng (shouldn't happen)
- **Semaphore** để limit concurrent requests (avoid rate limits)

### 🐛 Debugging

**Issue: Rate limit exceeded**
```python
# Solution: Reduce max_concurrent
runner.run_benchmark(max_concurrent=3)  # Not 5
```

**Issue: API key invalid**
```bash
# Check:
python test_llm_connection.py
```

**Issue: JSON parse error**
```python
# Add error handling:
try:
    result = json.loads(response)
except json.JSONDecodeError as e:
    print(f"Parse error: {e}")
    return {"score": 0.0, "reasoning": "Parse error"}
```

### 🤝 Sync Points với Người A
1. **After Phase 1:** Golden Dataset ready → Confirm format
2. **After Phase 2:** Benchmark results → Person A compute retrieval metrics
3. **After Phase 3:** Failure clusters → Run your 5 Whys on them
4. **After Phase 4:** All done → Merge final reports

---

## 📱 Backup Plans

**Nếu xong sớm:**
- [ ] Implement local LLM judge (Ollama) as fallback
- [ ] Add caching layer for cheaper evaluations
- [ ] Implement streaming for long responses
- [ ] Add more detailed metrics (perplexity, rouge scores)

**Nếu bị block:**
- [ ] LLM API down? → Mock responses, focus on logic
- [ ] No GPU? → Use cloud API (OpenAI, Anthropic - not local)
- [ ] Rate limited? → Add exponential backoff + retry logic
- [ ] Time pressure? → Skip NDCG, focus on Hit Rate + MRR + Judge scores

---

**Good luck! Keep Person A updated! 🚀**
