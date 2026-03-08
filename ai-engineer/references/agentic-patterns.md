# Agentic Patterns (LangChain / LangGraph)

Source: Anthropic "Building Effective Agents" (Dec 2024), Anthropic "Effective Context
Engineering for AI Agents" (2025), LangGraph production docs, 12-Factor Agent framework

---

## LangGraph Production Checklist

A resilient LangGraph app has:
- **State**: small, typed, validated; reducers used sparingly
- **Flow**: simple edges at decision points; bounded cycles with hard stops
- **Memory**: `PostgresSaver` (production) or `SqliteSaver` (dev) — not `MemorySaver`
- **Streaming**: deliberate choice of mode (`messages` / `updates` / `values` / `custom`)
- **Errors**: node + graph + app-level handlers; self-healing on tool failures
- **HITL**: precise interrupt points and deterministic resume paths
- **Context**: scoped per agent/step; compressed at boundaries (see `context-engineering.md`)
- **Ops**: full tracing via LangSmith or Langfuse; cost monitoring
- **Evals**: agent-specific metrics (step success rate, tool accuracy, completion rate)

---

## Typed State (Required)

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # reducer accumulates
    context: str
    iteration: int                            # for bounding loops
    final_answer: str | None
    # Don't dump transient values here — pass through function scope
```

---

## LCEL (Always Prefer Over Legacy)

```python
# ❌ Legacy — never use for new code
chain = LLMChain(llm=llm, prompt=prompt)

# ✅ LCEL
chain = prompt | llm | StrOutputParser()

# ✅ With fallback
chain = (prompt | llm | StrOutputParser()).with_fallbacks([backup_chain])

# ✅ Async streaming (for user-facing output)
async for chunk in chain.astream({"input": user_query}):
    print(chunk, end="", flush=True)
```

---

## Tool Definition

The docstring IS the tool spec. The LLM reads it to decide when and how to use the tool.
This is the single most important thing to get right in tool-calling agents.

```python
from langchain_core.tools import tool

@tool
def search_knowledge_base(
    query: str,
    top_k: int = 5,
    min_score: float = 0.7,
) -> list[dict]:
    """Search the internal knowledge base for relevant documents.

    Use this when you need factual information about products, policies, or history.
    Do NOT use for general world knowledge the model already knows.

    Args:
        query: Natural language search query.
        top_k: Maximum number of results to return.
        min_score: Minimum relevance score (0-1). Lower = more permissive.

    Returns:
        List of dicts with 'content', 'source', and 'score' keys.
    """
    ...

# Bind tools to model before graph compilation
llm_with_tools = llm.bind_tools(tools)
```

### Tool set design principles

- **Minimal and non-overlapping**: If a human can't definitively say which tool to
  use in a given situation, neither can the agent. Ambiguous tools cause misrouting.
- **Self-contained**: Each tool handles its own errors and returns informative messages
- **Clear boundaries**: "Use this when X. Do NOT use for Y."
- **Typed inputs**: Descriptive parameter names that play to the model's strengths
- **Selective exposure**: For agents with many tools, dynamically select which tool
  descriptions to include based on the current task (see `context-engineering.md`)

---

## MCP (Model Context Protocol) Tools

MCP is the emerging standard for exposing tools to LLM agents over a network protocol.
When building MCP servers:

```python
# MCP tool definitions follow the same principles as LangChain tools:
# Clear docstrings, typed parameters, informative error messages.
# The difference is transport: MCP exposes tools over HTTP/SSE instead
# of in-process function calls.

# Key considerations:
# - Tool docstrings are even more critical — they're the only documentation
#   the consuming agent has
# - Error messages should be self-explanatory (the agent can't inspect your code)
# - Consider a CLI wrapper that strengthens your MCP offering (hybrid approach)
# - Multi-tenancy: handle client entitlements at the server level
```

---

## Checkpointing

```python
# Development/testing only
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# Production — durable, survives restarts, enables time-travel debugging
# Package: langgraph-checkpoint-postgres
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(os.environ["POSTGRES_URI"])

graph = builder.compile(checkpointer=checkpointer)

# Thread-scoped persistence (each user/session gets its own thread)
result = graph.invoke(
    input_state,
    config={"configurable": {"thread_id": f"user-{user_id}-session-{session_id}"}}
)
```

---

## Bounding Agent Loops

Unbounded loops are a production anti-pattern. Always add hard stops.

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    iteration: int
    MAX_ITERATIONS: int  # or use a constant

def should_continue(state: AgentState) -> str:
    if state["iteration"] >= state["MAX_ITERATIONS"]:
        return "force_end"
    if state.get("final_answer"):
        return "end"
    return "continue"
```

---

## Self-Healing on Tool Errors

One of the simplest and highest-impact patterns: when a tool call fails, feed the
error back into context and let the agent retry with a budget.

```python
MAX_RETRIES = 3

async def execute_tool_with_healing(state: AgentState) -> dict:
    """Execute tool call with self-healing on failure."""
    tool_call = state["messages"][-1].tool_calls[0]
    retries = state.get("tool_retries", 0)

    try:
        result = await execute_tool(tool_call)
        return {
            "messages": [ToolMessage(content=result, tool_call_id=tool_call["id"])],
            "tool_retries": 0,  # reset on success
        }
    except Exception as e:
        if retries >= MAX_RETRIES:
            # Escalate: return error as final tool result, let agent decide next step
            return {
                "messages": [ToolMessage(
                    content=f"Tool failed after {MAX_RETRIES} retries: {str(e)}. "
                            f"Please try a different approach.",
                    tool_call_id=tool_call["id"],
                )],
                "tool_retries": 0,
            }
        # Feed error back into context — LLMs are good at reading errors and adjusting
        return {
            "messages": [ToolMessage(
                content=f"Error: {str(e)}. Please adjust parameters and retry.",
                tool_call_id=tool_call["id"],
            )],
            "tool_retries": retries + 1,
        }
```

This works because LLMs are surprisingly good at reading error messages and adjusting
their next move. The key is bounding retries (3 strikes) and eventually escalating
rather than looping forever.

---

## Multi-Agent Coordination Patterns

### Pipeline (Sequential Handoffs)

Each agent does its part and passes results to the next. Simplest multi-agent pattern.

```python
# research_agent → analysis_agent → writing_agent
# Each agent gets scoped context (not the full history of all agents)

def research_node(state: AgentState) -> dict:
    """Research agent: finds relevant information."""
    scoped = [SystemMessage(content=RESEARCH_PROMPT)] + extract_research_context(state)
    result = llm_with_tools.invoke(scoped)
    return {"research_findings": result.content}

def analysis_node(state: AgentState) -> dict:
    """Analysis agent: processes research into insights."""
    # Only sees research findings, not raw research tool outputs
    scoped = [
        SystemMessage(content=ANALYSIS_PROMPT),
        HumanMessage(content=state["research_findings"]),
    ]
    result = llm.invoke(scoped)
    return {"analysis": result.content}
```

### Hub-and-Spoke (Central Coordinator)

A coordinator agent dispatches tasks to specialist agents and synthesizes results.
Use when subtasks can't be predicted upfront.

```python
class CoordinatorState(TypedDict):
    messages: Annotated[list, add_messages]
    pending_tasks: list[dict]
    completed_results: list[dict]
    iteration: int

def coordinator_node(state: CoordinatorState) -> dict:
    """Central coordinator: decides what to do next and delegates."""
    prompt = (
        f"You are a coordinator. Based on the current results, decide:\n"
        f"1. Which specialist to call next (research, analysis, writing)\n"
        f"2. What specific task to give them\n"
        f"3. Or if we have enough to produce a final answer\n\n"
        f"Completed so far: {state['completed_results']}"
    )
    # Coordinator sees summaries, not raw specialist outputs
    ...
```

### Fan-Out / Fan-In (Parallel Specialists)

Multiple agents work on independent subtasks concurrently, then results converge.

```python
# LangGraph supports this with Send() for dynamic fan-out
from langgraph.types import Send

def route_to_specialists(state):
    """Fan out to multiple specialist agents in parallel."""
    tasks = state["pending_tasks"]
    return [Send(task["specialist"], {"task": task}) for task in tasks]
```

### Key principle for all multi-agent patterns

**Summarize at agent-agent boundaries.** Don't pass raw context between agents —
compress findings into what the next agent actually needs. Cognition (Devin) uses
fine-tuned summarization models for this step because it's that critical for
long-running tasks. See `context-engineering.md` for details.

---

## Streaming Modes

Choose deliberately based on your UX needs:

```python
# Stream token-by-token (best for chat UX)
async for chunk in graph.astream(input, config=config, stream_mode="messages"):
    if hasattr(chunk, "content"):
        print(chunk.content, end="", flush=True)

# Stream node-level updates (best for observability / step indicators)
async for update in graph.astream(input, config=config, stream_mode="updates"):
    print(f"Node completed: {list(update.keys())}")
```

---

## Human-in-the-Loop

```python
# Compile with interrupt
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["high_risk_action"]  # pause before this node
)

# Resume after human review
graph.invoke(None, config={"configurable": {"thread_id": thread_id}})
```

---

## Agent-Specific Evaluation

Agent evals are distinct from single-call LLM evals. Track these metrics:

| Metric | What it measures | How to compute |
|---|---|---|
| **Step success rate** | Did each intermediate step produce a valid result? | Grade each tool call and reasoning step |
| **Tool accuracy** | Did the agent pick the right tool with correct parameters? | Compare against gold-standard tool sequences |
| **Completion rate** | Did the agent finish the task? | Binary: reached final answer vs. timed out / gave up |
| **Trajectory quality** | Was the path efficient? (no unnecessary loops, no wrong turns) | LLM-as-judge on the full trajectory |
| **Token efficiency** | How many tokens to complete the task? | Total tokens / task complexity |
| **Self-healing rate** | How often did the agent recover from errors? | (recovered errors) / (total errors) |

```python
@dataclass
class AgentEvalTrace:
    task_id: str
    completed: bool
    total_steps: int
    tool_calls: int
    correct_tool_calls: int
    errors_encountered: int
    errors_recovered: int
    total_tokens: int
    latency_seconds: float
    trajectory_score: float | None  # from LLM-as-judge
```

---

## Common Gotchas

- `ChatPromptTemplate.from_messages` takes tuples `("role", "content")`, not dicts
- LangGraph nodes must return a dict matching state schema (partial updates OK)
- Avoid mutable defaults in state — use `Annotated` with reducers
- `invoke` is sync, `ainvoke` is async — never mix in async contexts
- Tool results arrive as `ToolMessage`, not `AIMessage` — reducers must handle both
- LangGraph `interrupt_before` requires a checkpointer — won't work without one
- `PostgresSaver` package is `langgraph-checkpoint-postgres` — verify import path against your version
- Multi-agent systems amplify complexity — monitor for loops, tool misuse, and cost blowups
- Don't let the LLM decide everything — use deterministic routing where possible (12-Factor Agent principle)
