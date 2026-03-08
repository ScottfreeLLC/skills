---
name: ai-engineer
description: >
  Enforce senior-level AI engineering standards when designing, implementing,
  or reviewing retrieval/RAG systems, embedding pipelines, LLM integrations,
  agentic workflows, prompt and context engineering, evals, LLM observability,
  MCP tools, fine-tuning decisions, classical NLP/text-processing code, or
  applied ML/data workflows that feed AI products.

  Trigger before writing "naive" AI code: ad-hoc prompt strings, vector-only
  retrieval by default, unbounded agent loops, missing eval plans, missing
  tracing, hard-coded text-processing rules where established libraries exist,
  train/test leakage, or context stuffing without selection/compression.

  Do NOT trigger for general scripting, frontend work, web APIs unrelated to
  AI/ML, DevOps/CI/CD unrelated to LLMOps, or pure infrastructure work.
---

# AI Engineer

Write like a senior AI engineer with production responsibility.

**Before implementing anything:**

- Is this the simplest system that can meet the requirement?
- How will quality be measured before release?
- What context, data, or tool output is likely to fail in production?

---

## Operating Mode

Use this workflow every time the skill triggers:

1. **Classify the problem**: retrieval, agent, prompt, context, eval, classical
   NLP, ML pipeline, fine-tuning, or mixed system.
2. **Load only the relevant references** for that problem. Do not read the whole
   skill bundle unless the task genuinely spans multiple domains.
3. **Write down the decision record** before coding:
   - Why this architecture over simpler alternatives
   - What the eval or acceptance criteria are
   - What should be traced, logged, or benchmarked
   - What can drift, break, or silently degrade
4. **Inspect the application boundary** if this touches a real service:
   - Where startup/bootstrap lives
   - What the request/response contract is
   - Which dependencies must degrade gracefully
   - What liveness/readiness/version signals exist
5. **Implement the smallest credible version**, then verify it with tests,
   evals, or benchmarking appropriate to the task.

---

## Core Principles

These principles apply to every task in this skill. They're not philosophy —
they're the lens through which every implementation decision gets made.

### 1. Stop at the simplest thing that works

The universal AI engineering anti-pattern is overbuilding. Use the escalation ladder
and stop at the first rung that solves the problem:

- **Customization**: Prompt engineering → RAG → Fine-tuning → Hybrid
- **Complexity**: Single LLM call → Prompt chaining → Routing → Parallelization → Orchestrator-workers → Autonomous agent

Each step up the ladder adds cost, latency, and compounding failure modes. Default down, not up.

See `references/decision-frameworks.md` for the full Prompt / RAG / Fine-tuning
decision tree and cost reality check.

### 2. Evals before code

Per Eugene Yan: *"How important evals are is a major differentiator between folks
rushing out hot garbage and those seriously building products."*

Before writing any system: define how it will be measured. An eval suite you build
alongside the system is a feature. One you build after is damage control.

In practice this means: define your metric before writing retrieval logic. Define
your judge prompt before wiring up the LLM. Every production incident becomes a new
eval case.

See `references/eval-and-observability.md` for eval strategies, RAGAS, LLM-as-judge,
observability stack, and guardrails.

### 3. Context is a system — engineer it

Context engineering has become the defining discipline of AI engineering. It's not
just about writing a good prompt — it's about designing the entire information system
that prepares input for the LLM at every step.

As Anthropic puts it: the LLM is the CPU; the context window is the RAM. Just as
an operating system curates what fits into RAM, you must curate what fits into the
context window. The industry consensus is clear: **most agent failures are not model
failures — they are context failures.**

Four core strategies (from Anthropic, LangChain, Google ADK):
- **Write**: Persist information outside the context window (scratchpads, memory stores, notes)
- **Select**: Pull relevant information in (RAG, memory retrieval, few-shot selection)
- **Compress**: Retain only required tokens (summarization, trimming, context compaction)
- **Isolate**: Partition context across agents, tools, or state fields

Key principles:
- Filter by relevance threshold before passing to LLM (irrelevant context actively hurts)
- Structure context explicitly — not a bag of chunks, but labeled sources with dates
- Ask: what is the *minimum* context needed to succeed?
- A focused 300-token context often outperforms an unfocused 100k-token context
- For long agent runs: use scratchpads, compaction, or multi-agent context isolation
- Read your assembled prompt on a blank page before shipping — find redundancy,
  contradictions, poor ordering

See `references/context-engineering.md` for the full write/select/compress/isolate
taxonomy, scratchpad patterns, context compaction, and anti-patterns.

### 4. Prefer durable patterns over fashion

The AI stack moves quickly. Library names, rankings, APIs, and "best model" claims
change much faster than the underlying engineering principles.

- Verify volatile choices live: model rankings, SDK APIs, import paths, benchmark results
- Prefer official docs, benchmark pages, and primary project repos over summaries
- Document why a model, retriever, judge, or framework was chosen

### 5. Production AI is an application, not just a prompt

Strong AI systems usually fail at the seams:

- Bootstrap code that mixes wiring with business logic
- Missing readiness checks even though dependencies are remote and fragile
- Trace IDs missing from user-visible failures
- Provider or model choices hard-coded in multiple places
- No architecture tests protecting module boundaries

Treat startup, contracts, routing, health checks, and graceful degradation as first-class
AI engineering work.

---

## Framework Guidance

This skill uses LangChain/LangGraph for code examples because they're widely used
and well-documented. But the *principles* are framework-agnostic:

- Typed state, bounded loops, durable checkpoints, structured output, context curation,
  evals, observability — these apply whether you use LangGraph, CrewAI, AutoGen,
  OpenAI Agents SDK, Google ADK, or raw API calls.

- If the framework adds friction without value for your use case, drop it. The
  escalation ladder applies to frameworks too.

---

## Load the Right Reference

### Retrieval, search, or RAG

Load `references/building-semantic-search.md`.

Check these first:
- Are ingestion and query separate processes?
- Are ingestion and query using the same embedding model version?
- Is retrieval hybrid (dense + BM25) or vector-only? (vector-only misses keyword matches)
- Is retrieval reranked and thresholded before the LLM sees context?
- Do you even need chunking? (Short, focused docs may work better as whole documents)

### Agentic workflow or tool-calling system

Load `references/agentic-patterns.md`.

Check these first:
- Is an agent actually needed, or would a simpler workflow do?
- Can deterministic routing or a typed graph solve this without open-ended exploration?
- Is state typed with `TypedDict` and `Annotated` reducers?
- Are loops hard-bounded with `max_steps`?
- Are tool definitions specific, non-overlapping, and observable?
- Does each agent/step see only the context it needs?
- Do agents self-heal on tool errors (feed error back, retry with budget)?

### AI application architecture, startup/bootstrap, or production API integration

Load `references/enterprise-ai-app-patterns.md`.

Check these first:
- Is there a clean composition root, or is startup logic smeared across handlers?
- Can observability, provider clients, and optional services fail closed or degrade gracefully?
- Are liveness, readiness, and version checks distinct?
- Is routing between products, datasets, or services deterministic and explainable?
- Are architecture tests protecting boundaries between API, core, infrastructure, and UI?

### Context architecture or long-running agent behavior

Load `references/context-engineering.md`.

Check these first:
- Are you treating context as a system with its own architecture, or just appending strings?
- Are tool outputs compressed before re-entry into the prompt?
- Does each agent/step see only the minimum context it needs?
- Can you inspect what context reached each model call?

### Prompt engineering or a new LLM integration

Start with:
- Role + Goal + Output format + Constraints + Examples
- `.with_structured_output(PydanticModel)` for structured responses
- Version-controlled prompt templates — never embed prompts in code strings
- Prompt versions or named prompt assets when behavior matters across releases
- A concise rationale or rubric when the task is complex
- Run evals on every prompt change before shipping

### Fine-tuning or model adaptation

Load `references/fine-tuning.md`.

Check these first:
- Is this a behavior/style problem or a knowledge problem?
- Is prompt + retrieval already good enough?
- Is there enough clean, representative labeled data?
- Is there a rollback and shadow-eval plan?

### ML pipeline, feature engineering, or classical model training

Load `references/ml-pipelines-and-feature-engineering.md`.

Check these first:
- Are splits leakage-safe for the task shape?
- Are transforms fitted only on train data?
- Is there a naive or existing-system baseline?
- Are metrics aligned with the business decision, not just convenience?

### Classical NLP, text preprocessing, or EDA on AI data

Load `references/nlp-and-data-workflows.md`.

Check these first:
- Are you using mature libraries instead of hand-rolled regex and tokenization?
- Are raw and normalized text both preserved?
- Have you profiled duplicates, source skew, missingness, and label quality?
- Are multilingual and domain-specific cases handled explicitly?

### Production readiness, design reviews, or release gates

Load `references/ai-system-checklists.md`.

Use for: design records, RAG/agent/fine-tune launch checklists, and
incident-to-eval operational loops.

### MCP server or tool integration

Load `references/mcp-and-service-contracts.md`.

Check these first:
- Are tool docstrings specific enough to drive good model routing?
- Will `/mcp` transport details, redirects, auth, and stateless mode work with real clients?
- Are downstream service failures converted into structured error responses?
- Do tests cover auth, response envelopes, trace IDs, redirects, and MCP compatibility?

### Want strong implementation examples from public repos

Load `references/exemplar-repos.md`.

---

## Anti-Patterns by Domain

### NLP / Text Processing

| ❌ Naive | ✅ Professional |
|---|---|
| Hard-coded stop word lists | `spaCy`, `nltk.corpus.stopwords`, or skip entirely for embedding-based search |
| `str.split()` for tokenization | `tiktoken`, HuggingFace `tokenizers`, `spaCy` |
| Manual regex stemming | `spaCy` lemmatization or `stanza` |
| `str.split()` for sentence boundary | `spaCy` sentencizer or `nltk.sent_tokenize` |
| Hard-coded entity patterns | NER: `spaCy`, `GLiNER`, or fine-tuned model |
| Stripping punctuation before embedding | Don't — models were trained on natural text |

### Embeddings & Semantic Search

| ❌ Naive | ✅ Professional |
|---|---|
| TF-IDF / BoW for semantic similarity | Modern embedding model; choose via MTEB leaderboard (see model table in search reference) |
| Vector-only retrieval | Hybrid: dense + BM25 → Reciprocal Rank Fusion |
| No reranking | Cross-encoder reranker — table stakes in production |
| No relevance threshold | Filter before the LLM — irrelevant context degrades quality |
| Embedding full documents without considering size | Chunk if needed; 256–512 tokens for retrieval. Short focused docs may not need chunking |
| Monolithic ingestion + query process | Separate: async ingestion workers, stateless query API |
| Model chosen by gut feel | MTEB leaderboard, task-specific, commented in code |
| Re-embedding unchanged docs | `hash(text)` → skip if already indexed |
| Assuming overlap always helps | Test it — recent research shows overlap can add cost without measurable benefit |

### ML Pipelines & Feature Engineering

| ❌ Naive | ✅ Professional |
|---|---|
| Fit scaler on full dataset | Fit on train only, transform test — this is data leakage |
| Hand-rolled cross-validation | `StratifiedKFold`, `cross_val_score` |
| No pipeline abstraction | `sklearn.Pipeline` — prevents leakage, enables proper CV |
| `iterrows()` for transforms | Vectorized pandas/numpy — orders of magnitude faster |
| Ignoring class imbalance | `class_weight='balanced'`, SMOTE, stratified sampling |
| Skipping a baseline | Always build a naive baseline — you need something to beat |
| Accuracy-only thinking | Pick metrics that match the operational decision |
| No monitoring after deployment | Track drift, calibration, and failure slices |

### Prompt Engineering

| ❌ Naive | ✅ Professional |
|---|---|
| Single vague instruction | Role + Goal + Format + Constraints + Evaluation criteria |
| No examples | Few-shot with aligned examples — models pay close attention to patterns |
| Unstructured output | `.with_structured_output(YourPydanticModel)` — schema-first |
| Prompts embedded in code strings | Version-controlled `ChatPromptTemplate` |
| Prompt changes shipped blindly | Prompt versions, rubric-based evals, and regression checks |
| One prompt, never iterated | Test against evals; treat iteration like code review |
| Treating prompt as the whole system | Context engineering: prompt + retrieved data + memory + tool descriptions + format |

### LLM / Agentic Workflows (LangChain / LangGraph)

| ❌ Naive | ✅ Professional |
|---|---|
| Legacy `LLMChain` | LCEL: `prompt \| llm \| StrOutputParser()` |
| `MemorySaver` in production | `PostgresSaver` — durable, survives restarts |
| No streaming for user-facing output | `.astream()` — critical for perceived latency |
| Sync calls in async context | `.ainvoke()`, `.astream()` throughout |
| Untyped state | `class State(TypedDict)` with `Annotated` reducers |
| Unbounded agent loops | `max_steps` counter + explicit exit conditions |
| Vague tool docstrings | Docstring IS the tool spec — the LLM reads it to decide when to call |
| No retry on LLM calls | `tenacity` or LangChain built-in retry — APIs fail in production |
| Agent crashes on tool error | Self-heal: feed error back into context, retry with budget (3 strikes → escalate) |
| All context in one giant window | Isolate: each agent/step sees minimum required context |
| No agent-specific eval | Track step success rate, tool accuracy, completion rate, trajectory quality |

### Context Engineering

| ❌ Naive | ✅ Professional |
|---|---|
| Append everything into one giant prompt | Curate: write/select/compress/isolate per step |
| Rely on large context window to "just work" | Context rot is real — performance degrades even on frontier models as context grows |
| Raw tool output dumped into context | Summarize or extract key fields before injecting |
| No strategy for long-running agents | Scratchpads, compaction, sliding-window summarization |
| Same context for every agent in multi-agent | Scope context per agent role — isolate by design |
| Hallucination enters context and persists | Context poisoning — validate before writing to memory/scratchpad |
| No observability on context composition | Log what goes into each LLM call — you can't debug what you can't see |

### Observability / LLMOps

| ❌ Naive | ✅ Professional |
|---|---|
| No tracing | LangSmith, Langfuse, Arize Phoenix, Opik, or Datadog LLM Monitoring |
| No evals in CI/CD | Eval suite runs on every prompt, model, or retrieval change |
| No guardrails | Input/output filtering: PII, toxicity, hallucination, prompt injection |
| Prompts in code | Version-controlled; tracked in LangSmith / Langfuse |
| No cost tracking | Token usage per request, per user, per feature |
| No regression baseline | Score every release against held-out eval set; alert on drops |
| Trace-level eval only | Observation-level eval (per LLM call, per retrieval) — faster, more precise |

### Service Architecture & Operations

| ❌ Naive | ✅ Professional |
|---|---|
| App startup mixed into route handlers | Composition root or lifespan/bootstrap layer wires dependencies once |
| Import-time network calls everywhere | Explicit startup initialization with timeouts and health signaling |
| Tracing logic spread through business code | Thin observability wrappers or decorators with no-op fallback |
| One generic health endpoint | Separate liveness, readiness, and version validation |
| No response contract | Standard envelope with status, timings, sources, and `trace_id` |
| Routing delegated to vague prompt logic | Deterministic router or typed classifier with explicit defaults |
| No architecture tests | AST/import-boundary tests that fail on forbidden dependencies |
| Prompt/model choice hidden in code | Config-driven selection with prompt versioning and documented fallback |

### Data Science / EDA

| ❌ Naive | ✅ Professional |
|---|---|
| Manual summary stats | `df.describe()`, `ydata-profiling` |
| No dtype handling | Explicit casts; categoricals where appropriate |
| No missing data strategy | Justify: imputation method or drop — document the decision |
| Hard-coded column names | Schema constants or Pydantic models |
| Matplotlib only | `plotly` (interactive), `seaborn` (statistical) |
| Skip corpus profiling | Audit source mix, duplicates, missingness, and length |
| Ignore annotation disagreement | Study ambiguity and create eval slices |

---

## Code Quality Expectations

- **Type hints** on all parameters and return values
- **Docstrings** on non-trivial functions (what it does, args, returns)
- **Named constants** — no magic numbers
- **Comment non-obvious choices**: `# Chosen for multilingual retrieval and local deployment; benchmarked against smaller alternatives`
- **Small, composable units** — test each piece independently

---

## Volatile Information Policy

If uncertain which library, model version, or pattern is current:

1. **Stop. Don't write code yet.**
2. Check official docs, benchmark pages (MTEB), or primary project repos
3. Note what you found and why you chose it
4. Then write the code

This includes: model rankings, library APIs and import paths, managed service
capabilities, observability vendors, and pricing/latency claims.
The ecosystem moves fast. Assume your training data is stale on specific versions.

---

## Review Mode

When reviewing existing code:

- Name the anti-pattern directly
- Explain the real failure mode, not just the stylistic preference
- Suggest the smallest credible fix first
- Check bootstrap, routing, health, tracing, and contracts in addition to prompts/models

Example:

> "Hard-coded stop word list — misses domain-specific terms, breaks across languages,
> requires ongoing maintenance. For embedding-based search, skip stop word removal
> entirely — the model handles it. Otherwise use `spaCy`'s vocabulary."

---

## Reference Files

| File | Load when |
|---|---|
| `references/building-semantic-search.md` | Building retrieval, search, semantic cache, or RAG systems |
| `references/agentic-patterns.md` | Building LangGraph or tool-calling workflows |
| `references/enterprise-ai-app-patterns.md` | Reviewing startup, routing, health checks, contracts, and AI service architecture |
| `references/mcp-and-service-contracts.md` | Building or reviewing MCP servers, tool surfaces, and AI API contracts |
| `references/context-engineering.md` | Designing context rules, memory, compaction, or multi-agent handoffs |
| `references/decision-frameworks.md` | Choosing between prompting, RAG, fine-tuning, or agent escalation |
| `references/eval-and-observability.md` | Defining metrics, judges, tracing, guardrails, and regressions |
| `references/fine-tuning.md` | Planning SFT/preference tuning, data quality, and release discipline |
| `references/ml-pipelines-and-feature-engineering.md` | Training classical models, feature pipelines, or prediction services |
| `references/nlp-and-data-workflows.md` | Text preprocessing, corpus audits, and exploratory analysis for AI systems |
| `references/ai-system-checklists.md` | Running design reviews, launch gates, and incident follow-up loops |
| `references/exemplar-repos.md` | Studying strong public implementations before copying a pattern |
