# Exemplar Repos

Use this file when you want strong public implementation references instead of copying
patterns from isolated blog posts.

Verify current stars, maintenance status, and API direction live before treating
"popularity" as evidence.

---

## Core Frameworks and Agent Orchestration

| Repo | Study it for |
|---|---|
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | Broad LLM application abstractions and ecosystem conventions |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Durable state, graph workflows, checkpoints, and interrupts |
| [microsoft/autogen](https://github.com/microsoft/autogen) | Multi-agent orchestration and runtime design ideas |
| [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | Role-based orchestration and task decomposition ergonomics |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | Typed agents and validation-first design |

### What to steal

- How state is represented
- Where retries, checkpoints, and interrupts live
- How tools are typed and documented
- Whether examples are toy demos or production-shaped

---

## Retrieval, RAG, and Document Systems

| Repo | Study it for |
|---|---|
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | RAG pipelines, indexing abstractions, and document workflows |
| [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | Search-oriented architecture and retrieval pipeline design |
| [openai/openai-cookbook](https://github.com/openai/openai-cookbook) | Practical retrieval, structured output, and eval examples |

### What to steal

- How ingestion is separated from query serving
- How retrieval is benchmarked and evaluated
- How examples communicate tradeoffs, not just happy paths

---

## Serving, Routing, and Infra Adapters

| Repo | Study it for |
|---|---|
| [vllm-project/vllm](https://github.com/vllm-project/vllm) | High-throughput serving and inference systems thinking |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | Provider routing, gateways, fallback strategy, and policy controls |

### What to steal

- How operational concerns are exposed in code and docs
- How provider abstraction is handled without hiding too much
- How config and runtime concerns are separated

---

## Prompting, Optimization, and Structured Output

| Repo | Study it for |
|---|---|
| [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | Eval-driven prompt improvement and optimizer-style LM programming |
| [567-labs/instructor](https://github.com/567-labs/instructor) | Structured outputs and typed extraction ergonomics |

### What to steal

- How schemas are enforced
- How prompts are made inspectable
- How evaluation integrates with generation logic

---

## Observability and Evaluation

| Repo | Study it for |
|---|---|
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | Tracing, prompt management, datasets, and observation-level evaluation |
| [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | LLM observability, telemetry, and evaluation workflows |

### What to steal

- What they log by default
- How traces connect prompts, retrieval, tools, and outputs
- How evaluation results are attached back to production data

---

## How to Use This Reference

When choosing a repo to learn from, ask:

- Does this repo solve the same class of problem?
- Is the example production-shaped or just onboarding material?
- Does the project expose tradeoffs, failure modes, and monitoring?
- Is the popularity driven by substance or by trend heat?

Use exemplar repos to sharpen implementation taste, not to outsource architecture.
