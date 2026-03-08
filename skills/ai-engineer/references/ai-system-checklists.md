# AI System Checklists

Use this file for short design reviews, launch gates, and incident follow-up loops.

---

## One-Page Design Record

Write these fields before implementation:

- Problem statement
- User-facing success condition
- Simplest architecture that might work
- Why more complex alternatives were rejected
- Evaluation plan
- Observability plan
- Known failure modes
- Rollback or fallback plan

If this cannot fit on one page, the design is probably still blurry.

---

## RAG Launch Checklist

- Corpus, freshness, and ownership are defined
- Ingestion and query paths are separate
- Embedding model choice is documented
- Retrieval quality is benchmarked, not assumed
- Reranking and relevance threshold policy are defined
- Citations and provenance are preserved
- Retrieval and answer quality are both evaluated
- Context assembly is inspectable in traces
- Incident cases flow back into the eval set

---

## Agent Launch Checklist

- A simpler workflow was considered first
- Tool boundaries are explicit and non-overlapping
- Loops have max-step and retry limits
- Checkpointing fits the deployment environment
- Human intervention points are clear where needed
- Each agent or step gets scoped context
- Step-level metrics are defined
- Failure budgets and escalation paths are documented
- Production tracing captures trajectories and tool errors

---

## Fine-Tune Release Checklist

- The task is a behavior problem, not a knowledge problem
- Dataset sources and splits are documented
- The tuned model beats prompt-only and retrieval baselines
- Safety and refusal behavior were evaluated
- Shadow or canary rollout is ready
- The previous model or prompt path remains available
- Dataset version, training config, and model revision are recorded

---

## Prompt Change Checklist

- The prompt change has a stated purpose
- Structured output requirements are explicit
- Prompt assets are version-controlled
- Relevant eval cases were re-run
- The prompt does not duplicate context better supplied elsewhere
- Reasoning instructions are concise and justified by the task

---

## Incident-to-Eval Loop

For every meaningful production failure:

1. Capture the raw request, context, and output
2. Classify the failure: retrieval, prompt, tool, orchestration, policy, or data
3. Add a minimized repro case to the eval set
4. Add monitoring if the failure was previously invisible
5. Verify the fix against the new case before closing the incident

Treat incidents as dataset creation opportunities.
