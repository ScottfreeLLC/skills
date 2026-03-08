# Context Engineering

Source: Anthropic "Effective Context Engineering for AI Agents" (2025), LangChain context
engineering blog (2025), Google ADK architecture (Dec 2025), 12-Factor Agent framework,
Chroma context rot research (July 2025)

---

## Why Context Engineering Exists

Prompt engineering asks: "What words should I use?"
Context engineering asks: "What is the entire system that assembles the right information
for this LLM call?"

As agents run longer and handle more complex tasks, the amount of information they need
to track — chat history, tool outputs, retrieved documents, intermediate reasoning —
explodes. The naive solution (bigger context windows) fails under three pressures:

1. **Cost and latency spirals**: Token cost and time-to-first-token grow with context size
2. **Signal degradation ("lost in the middle")**: Irrelevant logs and stale outputs distract
   the model, causing it to fixate on noise rather than the instruction
3. **Context poisoning**: Hallucinations or errors that enter context persist and compound

A focused 300-token context often outperforms an unfocused 100k-token context. The goal
is not maximum context — it's *optimal* context.

---

## Components of Agent Context

Every LLM call receives some combination of:

- **System prompt**: Role, tone, boundaries, instructions
- **User input**: The current request from the user or orchestrating agent
- **Conversation history**: Running record of the dialogue
- **Retrieved knowledge**: Text or structured data from vector stores, databases, web search
- **Tool descriptions**: Definitions of available actions and when to use them
- **Tool outputs**: Results from previous tool calls
- **Task metadata**: User attributes, file types, performance constraints
- **Examples**: Few-shot examples showing desired input/output patterns
- **Memory**: Long-term facts, preferences, or procedures from previous sessions

Context engineering is the art and science of deciding which of these to include,
in what form, at what point, and under what rules.

---

## The Four Strategies

### 1. Write — Persist Outside the Context Window

Don't force the model to remember everything. Save information externally where it
can be reliably accessed when needed.

**Scratchpads / Notepads**

The most intuitive pattern. Agents write notes to an external document, just like
a human jotting things down while solving a complex problem.

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    scratchpad: str          # agent reads/writes working notes here
    final_answer: str | None

# The scratchpad is part of state but NOT necessarily part of the LLM prompt.
# You choose what to expose at each step.
```

**Long-term memory stores**

Three memory types that agents can write to:
- **Semantic memory**: Facts ("User prefers JSON output")
- **Episodic memory**: Past experiences ("Last time query X, approach Y worked")
- **Procedural memory**: Instructions/rules ("Always check cache before querying API")

```python
# Writing memory after a successful interaction
memory_store.save({
    "type": "episodic",
    "content": "User asked about Q3 revenue. Best approach: query financial DB first, then summarize.",
    "embedding": embed(content),
    "timestamp": datetime.now(),
    "tags": ["finance", "query-strategy"],
})
```

### 2. Select — Pull Relevant Information In

Not all available information belongs in every call. Select what's relevant.

**RAG retrieval** is the most common selection mechanism — covered in detail in
`building-semantic-search.md`.

**Memory retrieval** is the complement for agent-specific context:

```python
# Select relevant memories for the current task
relevant_memories = memory_store.search(
    query=current_task_description,
    memory_types=["procedural", "episodic"],  # skip semantic if not needed
    top_k=3,
    min_relevance=0.7,
)

# Inject into system prompt, not into conversation history
system_prompt += "\n\nRelevant past experience:\n" + format_memories(relevant_memories)
```

**Few-shot selection**: Don't use the same examples every time. Select examples
similar to the current query.

```python
# Dynamic few-shot: pick examples closest to current input
from langchain_core.example_selectors import SemanticSimilarityExampleSelector

selector = SemanticSimilarityExampleSelector.from_examples(
    examples=all_examples,
    embeddings=embedding_model,
    vectorstore_cls=Chroma,
    k=3,
)
selected = selector.select_examples({"input": user_query})
```

**Tool description selection**: For agents with many tools, dynamically select
which tool descriptions to include based on the current task, rather than
stuffing all of them into every call.

### 3. Compress — Retain Only Required Tokens

Two main techniques: summarization (LLM-based) and trimming (heuristic-based).

**Conversation compaction**

When conversation history grows too long, summarize older turns:

```python
async def compact_history(
    messages: list,
    llm,
    max_tokens: int = 4000,
    keep_recent: int = 6,
) -> list:
    """Compact conversation history when it exceeds token budget.

    Keeps the most recent messages intact and summarizes older ones.
    The summary replaces the old messages, preserving key decisions and facts.
    """
    if estimate_tokens(messages) <= max_tokens:
        return messages

    recent = messages[-keep_recent:]
    older = messages[:-keep_recent]

    summary = await llm.ainvoke(
        f"Summarize the key facts, decisions, and open questions from this "
        f"conversation history. Be concise but preserve anything the agent "
        f"needs to continue the task:\n\n{format_messages(older)}"
    )

    return [SystemMessage(content=f"[Summary of earlier conversation]\n{summary.content}")] + recent
```

**Tool output compression**

Tool calls (especially search, code execution, API responses) often return far more
data than the agent needs. Compress before injecting:

```python
# ❌ Dump raw API response into context
state["messages"].append(ToolMessage(content=raw_api_response))  # could be 10k+ tokens

# ✅ Extract what matters
extracted = await llm.ainvoke(
    f"Extract only the fields relevant to the user's question from this API response. "
    f"Question: {user_question}\n\nResponse:\n{raw_api_response}"
)
state["messages"].append(ToolMessage(content=extracted.content))
```

**Heuristic trimming**

Not everything needs an LLM to compress. Simple rules work for many cases:

```python
def trim_tool_outputs(messages: list, max_output_tokens: int = 500) -> list:
    """Truncate oversized tool outputs with a note."""
    trimmed = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and estimate_tokens(msg.content) > max_output_tokens:
            trimmed.append(ToolMessage(
                content=msg.content[:max_output_tokens * 4] + "\n\n[Output truncated]",
                tool_call_id=msg.tool_call_id,
            ))
        else:
            trimmed.append(msg)
    return trimmed
```

### 4. Isolate — Partition Context Across Boundaries

Different tasks need different information. Don't cram everything into one window.

**Multi-agent context isolation**

Each specialist agent gets only the context relevant to its role:

```python
# ❌ Every agent sees everything
def research_agent(state):
    # sees all messages, all tool outputs, all intermediate reasoning
    return llm.invoke(state["messages"])

# ✅ Each agent gets scoped context
def research_agent(state):
    # only sees the research question and its own tool outputs
    scoped_messages = [
        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
        HumanMessage(content=state["research_question"]),
    ] + state.get("research_tool_outputs", [])
    return llm.invoke(scoped_messages)
```

**State field isolation**

Use typed state to isolate context into fields that are selectively exposed:

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # exposed to LLM
    research_notes: str                        # written by research agent, read by synthesis agent
    tool_results_raw: list[dict]               # stored but NOT exposed to LLM
    tool_results_summary: str                  # compressed version exposed to LLM
    iteration: int                             # control flow only, never in prompt
```

**Agent-agent boundary summarization**

When one agent hands off to another, summarize rather than passing raw history.
Cognition (Devin) uses fine-tuned summarization models for this step — it's
that important for long-running multi-agent tasks.

```python
def handoff_to_next_agent(state: AgentState) -> dict:
    """Summarize findings before handing to the next agent."""
    summary = llm.invoke(
        f"Summarize the key findings and open questions for the next step:\n"
        f"{state['research_notes']}"
    )
    return {"handoff_summary": summary.content}
```

---

## Context Rot

Research (Chroma, July 2025) tested 18 frontier models and found that retrieval
performance degrades as context length increases, even on straightforward tasks.
This is called **context rot** — the model's ability to accurately recall information
from context decreases as the number of tokens increases.

Implications:
- "Just use a bigger context window" is not a strategy
- More tokens in = lower attention per token on average
- Information near the start and end of context gets more attention;
  middle content gets "lost in the middle"
- Most relevant chunks should go first and last; less relevant in the middle

**Mitigation:**
1. Keep context lean — compress and trim aggressively
2. Structure context with explicit labels and delimiters
3. Put critical information at the start and end of context
4. Measure recall@k on your actual queries as context grows
5. Set hard token budgets per context component

---

## Context Poisoning

When incorrect or hallucinated information enters the context (via tool outputs,
previous agent responses, or corrupted memory), it persists and compounds.
The model treats everything in its context as potentially true.

**Prevention:**
- Validate tool outputs before writing to memory or scratchpad
- Use CRAG-style relevance checks before injecting retrieved context
- Periodically re-validate stored memories against ground truth
- Include a "confidence" field in memory entries and prefer high-confidence items
- For critical decisions, retrieve fresh data rather than relying on cached context

---

## The 12-Factor Agent (Relevant Factors)

The 12-Factor Agent framework (inspired by the original 12-Factor App) codifies
context engineering principles. Key factors:

1. **Own Your Prompts**: Control every token in your prompts — no framework magic
2. **Own Your Context Window**: Curate and optimize the information fed to the LLM
3. **Tools Are Just Structured Outputs**: LLM "tool use" is the model producing
   structured data for deterministic code execution
4. **Unify Execution State and Business State**: Don't split agent operational
   status from the real-world data it's working with
5. **Own Your Control Flow**: Don't let the LLM decide everything — use
   deterministic routing where possible

---

## Anti-Patterns

| ❌ Anti-pattern | ✅ Fix |
|---|---|
| Append all messages forever | Compact older messages; keep recent N intact |
| Raw tool output in context | Summarize or extract relevant fields before injecting |
| Same context for all agents | Scope context per agent role; isolate by design |
| No token budget per component | Set explicit limits: system prompt ≤ X, history ≤ Y, retrieved ≤ Z |
| "Bigger window = better" | Context rot is real; focused context outperforms padded context |
| Hallucination enters scratchpad | Validate before writing; include confidence scores |
| No observability on context | Log what goes into each LLM call — token counts per component |
| Static few-shot examples | Dynamic selection based on similarity to current input |
| All tool descriptions every call | Select tools relevant to current task; hide irrelevant ones |
| No hand-off summarization | Summarize at agent-agent boundaries to reduce token transfer |

---

## Observability for Context

You can't optimize what you can't measure. Instrument your context pipeline:

```python
from dataclasses import dataclass

@dataclass
class ContextTrace:
    """Log the composition of every LLM call's context."""
    call_id: str
    system_prompt_tokens: int
    conversation_history_tokens: int
    retrieved_context_tokens: int
    tool_descriptions_tokens: int
    tool_output_tokens: int
    few_shot_tokens: int
    total_tokens: int
    # Quality signals
    compaction_applied: bool = False
    tools_filtered: bool = False
    below_budget: bool = True
```

**Alert thresholds:**

| Metric | Alert if... | Likely cause |
|---|---|---|
| Total context tokens | Exceeds 80% of model limit | Missing compaction or trimming |
| Tool output tokens | > 50% of total context | Raw outputs not being compressed |
| Compaction frequency | Every turn | History growing too fast; review what's being appended |
| Context composition ratio | Retrieved context < 10% | RAG not contributing; check retrieval quality |
