# Evals & Observability

"Evals are the foundation. Without them, you're flying blind." — Eugene Yan

---

## Metric Selection by Task

Don't use BLEU/ROUGE for generative tasks — poor correlation with human judgment.

| Task | Metrics |
|---|---|
| RAG faithfulness | RAGAS `faithfulness`, FACTS score |
| RAG retrieval quality | MRR@K, NDCG@K, Hit@K, `context_recall` |
| Summarization | BERTScore, LLM-as-judge |
| Classification | Precision / Recall / F1 per class, AUC-ROC |
| Translation | COMET (not BLEU) |
| Dialogue / generation | LLM-as-judge, human eval |
| Hallucination | FActScore, RAGAS faithfulness |
| Agents | Step success rate, tool accuracy, completion rate, trajectory quality |

---

## LLM-as-Judge

Now the standard for evaluating LLM outputs at scale. Research shows strong LLM judges
achieve 80–90% agreement with human evaluators, comparable to inter-annotator agreement
between humans.

### Best practices (validated by research, 2024–2026)

1. **Start with binary pass/fail** before scaling to numeric scores.
   A pass/fail verdict forces you to define what "acceptable" means before worrying
   about what distinguishes a 3 from a 4. Add granularity later.

2. **Limit evaluation criteria to 3–5 dimensions per judge call.**
   Evaluating too many dimensions at once dilutes the judge's focus and reduces
   scoring quality. Run separate calls for separate concerns.

3. **Use separate judge calls for separate concerns.**
   Hallucination detection and tone evaluation are different skills. Specialized
   judge prompts produce better results than a single monolithic evaluation prompt.

4. **Include few-shot examples — but not too many.**
   One well-chosen example of a good and bad output consistently improves scoring.
   However, research on code evaluation found that adding more examples can actually
   degrade performance. Start with one shot.

5. **Calibrate against human labels.**
   Before trusting a judge in production, build a calibration set of 30–50 examples
   annotated by domain experts. If the judge disagrees more than 20% of the time on
   clear-cut cases, iterate on the prompt before deploying.

6. **Use a different model as judge than the one being evaluated.**
   Self-evaluation creates self-serving bias — models favor their own outputs. Also
   watch for verbosity bias (judges favor longer responses) and position bias.

7. **Consider dedicated judge models.**
   Dedicated evaluation models (see Judge Arena Leaderboard) increasingly outperform
   general-purpose models on judging tasks. The tradeoff: they may not generalize as
   well to novel tasks outside their training distribution.

8. **Ask for concise justification, not verbose hidden reasoning.**
   A short rubric-based rationale is usually enough to debug disagreements and is
   less brittle across models than relying on long reasoning traces.

### Implementation

```python
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

class EvalResult(BaseModel):
    faithfulness_score: int = Field(..., ge=1, le=5)
    faithfulness_reasoning: str
    relevance_score: int = Field(..., ge=1, le=5)
    relevance_reasoning: str

judge_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert QA evaluator. Score on a 1-5 scale. Be critical.
Give a concise justification for each score using the rubric. Do not add filler.

Example of a faithful answer (score 5):
Question: "What is our refund policy?"
Context: "Customers may request a refund within 30 days of purchase."
Answer: "You can request a refund within 30 days of your purchase."
Reasoning: The answer directly paraphrases the context with no added claims.

Example of an unfaithful answer (score 1):
Question: "What is our refund policy?"
Context: "Customers may request a refund within 30 days of purchase."
Answer: "We offer a 60-day money-back guarantee with free return shipping."
Reasoning: The answer contradicts the context (60 days vs 30) and adds unsupported claims."""),
    ("human", """
Question: {question}
Context: {context}
Answer: {answer}

Score FAITHFULNESS (1=contradicts context, 5=fully grounded in context).
Score RELEVANCE (1=doesn't address question, 5=directly answers it).
""")
])

# `judge_model` is any strong model or dedicated judge model that supports
# structured output in your stack. Avoid judging a model with itself.
judge_model = build_judge_model(model="your-judge-model")
judge = judge_prompt | judge_model.with_structured_output(EvalResult)
result = judge.invoke({"question": q, "context": ctx, "answer": ans})
```

### Layered evaluation strategy

Use the right tool for the job — not everything needs an LLM judge:

```python
# Layer 1: Deterministic checks (fast, cheap, reliable)
# - Format validation (is it valid JSON? Does it contain required fields?)
# - Length constraints (within min/max token limits?)
# - Regex patterns (contains legal disclaimer? No PII?)
assert is_valid_json(output)
assert MIN_TOKENS <= count_tokens(output) <= MAX_TOKENS

# Layer 2: LLM-as-judge (semantic quality)
# - Faithfulness, relevance, coherence, tone
# - Run per-observation for speed, or per-trace for holistic view
faithfulness = await judge.ainvoke({"question": q, "context": ctx, "answer": ans})

# Layer 3: Human review (calibration and edge cases)
# - Flagged cases from Layer 1 or Layer 2
# - Random sample (5-10%) for ongoing calibration
# - Every production failure → manual review → new eval case
```

---

## RAGAS (RAG Evaluation)

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,       # Is the answer grounded in context?
    answer_relevancy,   # Does it address the question?
    context_recall,     # Did retrieval find necessary info?
    context_precision,  # Is retrieved context actually relevant?
)

result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_recall])
print(result)  # Dict of metric -> score (0-1)

# Note: RAGAS API has changed across releases. Verify import paths and metric names
# against the version you have installed. Pin the version in requirements.txt.
```

---

## Building an Eval Dataset

You need labeled examples to evaluate anything properly.

Bootstrap when you have no labels:
1. Run your system on 50-100 representative queries; label outputs manually
2. Scale with LLM-as-judge; spot-check 10% manually
3. Collect real user feedback (thumbs up/down) as implicit labels in production
4. Every production failure → add to eval dataset (turn incidents into guardrails)
5. Set up a closed loop: production logs → curated datasets → future evals

**Critical**: Your eval set must represent real production queries, not synthetic
cherry-picked examples. Include edge cases, ambiguous queries, and adversarial inputs.

---

## Regression Testing

Run your eval suite on every change to prompts, models, or retrieval.

```python
BASELINE_SCORE = 0.82  # from last release

current_score = run_eval_suite()
if current_score < BASELINE_SCORE - 0.02:  # 2% tolerance
    raise ValueError(f"Regression: {current_score:.3f} < baseline {BASELINE_SCORE:.3f}")
```

---

## Observability Stack

### Tracing (pick one)

| Tool | Best for |
|---|---|
| **LangSmith** | LangChain/LangGraph native; seamless integration; prompt hub |
| **Langfuse** | Open-source; self-hostable; great for data governance; native LLM-as-judge at observation level |
| **Arize Phoenix** | OpenTelemetry-native; framework-agnostic; ML + LLM |
| **Braintrust** | Eval-centric; traces → eval cases with one click; CI/CD integration |
| **Opik** | Open-source; observation-level eval; growing ecosystem |
| **Datadog LLM Monitoring** | Enterprise; integrates with existing Datadog stack |

```python
# LangSmith (set env vars: LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY=...)
from langsmith import traceable

@traceable(run_type="llm", name="rag-qa-pipeline")
def answer_question(question: str) -> str:
    ...

# Langfuse
from langfuse.callback import CallbackHandler
handler = CallbackHandler(public_key=..., secret_key=...)
chain.invoke(input, config={"callbacks": [handler]})
```

### Observation-level vs. Trace-level Evaluation

**Prefer observation-level eval in production.** Evaluating individual operations
(per LLM call, per retrieval, per tool call) is faster and more precise than
evaluating entire traces:

- Observation-level: completes in seconds, pinpoints exactly which step failed
- Trace-level: takes minutes, gives holistic view but harder to diagnose

**Production pattern**: Use observation-level eval for real-time monitoring.
Use trace-level eval during development for end-to-end validation.

### Guardrails

Implement input/output guardrails for production LLM systems.

```python
# Guardrails to implement (ordered by priority):
# 1. Prompt injection detection (security — highest priority)
# 2. PII detection (prevent data leakage)
# 3. Hallucination detection (faithfulness check on output)
# 4. Toxicity / hate speech filtering
# 5. Off-topic / out-of-scope detection
# 6. Competitor mention filtering (if required)

# Library selection:
# - guardrails-ai: flexible, good for custom validators
# - NeMo Guardrails: Nvidia; dialog-centric; programmable rails
# - Llama Guard: Meta; fast classification model; good for content safety
# - Custom LLM-as-judge: most flexible; use for domain-specific checks

from guardrails import Guard
from guardrails.hub import DetectPII, ToxicLanguage

guard = Guard().use_many(DetectPII(), ToxicLanguage(threshold=0.5))
validated_output = guard.validate(llm_output)
```

### What to Monitor in Production

- **Quality**: LLM-as-judge score on sampled traffic (async, not blocking)
- **Faithfulness**: RAGAS faithfulness on RAG responses
- **Latency**: p50/p95/p99 per pipeline stage
- **Token cost**: per request, per user, per feature — alert on anomalies
- **Error rate**: LLM failures, retrieval failures, tool call failures
- **Guardrail trigger rate**: how often inputs/outputs are being blocked
- **User feedback**: thumbs up/down, explicit ratings
- **Context composition**: tokens per component (see `context-engineering.md`)

```python
# Example: async quality eval on production traffic (sample 10%)
import random

async def log_with_quality_eval(question: str, answer: str, context: str):
    trace = langsmith_client.create_run(...)

    if random.random() < 0.10:  # sample 10%
        quality = await eval_faithfulness(question, answer, context)
        langsmith_client.update_run(trace.id, feedback=quality)
```

---

## Prompt Versioning

Prompts should be versioned like code.

```python
# ❌ Prompt buried in code string
response = llm.invoke("Summarize the following: " + text)

# ✅ Version-controlled, tested, tracked
from langsmith import Client

client = Client()
prompt = client.pull_prompt("rag-summarizer:v3")  # pinned version
chain = prompt | llm | StrOutputParser()

# Alternative: store prompts as files in version control
# prompts/rag_summarizer_v3.yaml → loaded at runtime
# Every change goes through PR review + eval suite
```

---

## Agent Evaluation

Agent evals are distinct from single-call LLM evals. See `agentic-patterns.md`
for the full agent eval metrics table (step success rate, tool accuracy,
completion rate, trajectory quality, token efficiency, self-healing rate).

Key principle: evaluate the *trajectory*, not just the final answer. An agent that
reaches the right answer through a wasteful 15-step loop is worse than one that
reaches it in 3 focused steps.

```python
# Trajectory-level LLM-as-judge
trajectory_judge_prompt = """
Evaluate this agent's trajectory for efficiency and correctness.

Task: {task}
Steps taken: {trajectory}
Final answer: {answer}

Score EFFICIENCY (1=wasteful loops, 5=direct path).
Score CORRECTNESS (1=wrong answer, 5=fully correct).
Score TOOL_USE (1=wrong tools or bad parameters, 5=optimal tool selection).
"""
```
