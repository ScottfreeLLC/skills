# Decision Frameworks

Use this file when deciding whether to stay in prompting, add retrieval, train a
specialized model, or escalate toward agents.

---

## Prompting vs. RAG vs. Fine-Tuning

Start with the smallest intervention that can plausibly solve the problem.
**LLMs are reasoning engines, not databases.** Knowledge gaps → RAG.
Behavior gaps → fine-tuning. Most teams jump to fine-tuning when RAG would have been
faster, cheaper, and more maintainable.

### First question: what kind of gap is this?

```
Is the failure mostly missing or stale knowledge?
  YES → Retrieval or better context
    Does it change frequently (weekly+)?
      YES → RAG with live index
      NO → RAG with periodic re-index, or large context prompting
  NO → Is the failure mostly behavior, style, structure, or task policy?
    YES → Prompting, schemas, examples, or fine-tuning
      Do you have 500+ high-quality labeled examples?
        NO → Prompt engineering + few-shot first
        YES → Consider fine-tuning (see references/fine-tuning.md)
    NO → Is the real issue orchestration, tool use, or control flow?
      YES → Workflow design or agents
      NO → Re-check the requirement and eval definition
```

### Use prompting first when

- The task is mostly instruction following
- Knowledge is already in-model or small enough to pass directly
- Fast iteration matters more than peak consistency
- The system can tolerate some variation in output style

### Use RAG when

- Facts must be current, proprietary, or citable
- The system depends on external documents or records
- Knowledge changes faster than you want to retrain
- 60%+ of enterprise production GenAI uses RAG over fine-tuning

### Use fine-tuning when

- The task is stable and repeatedly exercised at high volume
- You need consistent behavior the prompt cannot reliably enforce
- You have 500+ clean, representative labeled examples
- The value of consistency outweighs dataset, training, and rollout cost
- See `references/fine-tuning.md` for the full lifecycle

### Use hybrid systems when

- Retrieval is needed for knowledge and tuning is needed for behavior
- Quality goals justify the extra operational burden
- You can measure each layer independently

### Practical decision notes

- Knowledge gaps usually want retrieval, not training
- Behavior gaps usually want prompting or fine-tuning, not a larger document corpus
- If a simple prompt with the right context already works, do not add a larger system
- If you cannot define an eval target, you are not ready to choose the architecture

### Cost reality check (illustrative — varies widely by scale, provider, and use case)

| Approach | Upfront | Ongoing monthly spend | Ops burden | Typical reason to choose |
|---|---|---|---|---|
| Prompt only | $0–2k | $500–5k | Low | Fastest path to a useful baseline |
| RAG | $2k–10k | $1k–8k | Medium | Need fresh or private knowledge |
| Fine-tune | $1k–5k | $300–3k | High | Need durable behavior/style consistency |
| Hybrid | $5k–15k | $2k–12k | Highest | Need both strong grounding and strong behavior control |

These are rough order-of-magnitude estimates across API usage, infrastructure, and
engineering time. The relative ordering is more reliable than the exact numbers.
If exact pricing affects the decision, verify it live with your providers.

---

## Agent Escalation Ladder

Stop at the first level that solves the problem. Each level adds latency, cost, and
potential for error compounding.

1. **Single LLM call + good prompt + context**
   Handles most tasks. Optimize this before escalating. If you're reaching for an agent,
   ask: "Would a well-crafted prompt with the right context solve this?"

2. **Prompt chaining** — output of one call feeds the next
   Use when: task has fixed sequential subtasks; each LLM call benefits from focus.

3. **Routing** — classify input, dispatch to specialized handler
   Use when: distinct input types are better handled separately; classification is reliable.

4. **Parallelization** — multiple calls run concurrently
   - *Sectioning*: independent subtasks in parallel
   - *Voting*: same task N times, aggregate (e.g., content moderation)

5. **Orchestrator-workers** — central LLM dynamically delegates to workers
   Use when: subtasks can't be predicted upfront (e.g., coding agents, research).

6. **Full autonomous agent** — LLM directs its own tool use in a loop
   Use when: open-ended problem, unpredictable steps, and you can afford the cost/latency.
   Requires: sandboxed testing, stopping conditions, human-in-the-loop checkpoints.

### Escalation rule

For every step up the ladder, be able to answer:

- What failure mode does this extra complexity solve?
- How will we detect whether it helped?
- What new failure mode does it introduce?

If you cannot answer those three questions, do not escalate.

---

## Context Discipline at Every Level

Context engineering matters at every rung:

- **Levels 1-2**: Mostly prompt engineering. Curate what goes into the prompt.
- **Levels 3-4**: Route context along with the query. Each branch may need different context.
- **Levels 5-6**: Context becomes a system: scratchpads, memory stores, compaction, isolation
  across agents. See `context-engineering.md` for the full taxonomy.

Teams often misdiagnose context failures as model failures. Fix the information flow
before assuming the model needs replacement or the architecture needs more layers.
