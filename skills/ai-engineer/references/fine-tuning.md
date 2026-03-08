# Fine-Tuning

Use this file when deciding whether to fine-tune, preparing a dataset, or planning
rollout and rollback for a tuned model.

---

## Start with the Right Diagnosis

Do not fine-tune to compensate for poor problem framing.

### Usually not a fine-tuning problem

- Missing or stale facts
- Poor retrieval quality
- Weak prompt structure
- Missing tool definitions
- Broken context assembly
- No eval suite

### Often a fine-tuning problem

- Consistent style, format, or refusal behavior is required
- The task is narrow and repeated at high volume
- Prompting plus examples still produces too much variance
- You have enough clean supervised data to define the target behavior

Knowledge gaps usually want retrieval. Behavior gaps may justify tuning.

---

## Adaptation Ladder

Exhaust simpler interventions before training:

1. Prompt cleanup
2. Better schemas and structured output
3. Better examples or demonstration selection
4. Retrieval or better context construction
5. Workflow redesign
6. Supervised fine-tuning
7. Preference tuning or policy optimization

If a lower rung is not convincingly evaluated, do not jump up the ladder.

---

## Data Quality Rules

Data quality is the bottleneck more often than model choice.

### Minimum requirements

- The task is stable enough that examples will still be useful after deployment
- Labels reflect the exact behavior you want in production
- Prompts, inputs, and outputs are representative of real traffic
- The dataset has train, validation, and holdout test splits
- Duplicates and near-duplicates are removed across splits

### Data anti-patterns

- Synthetic-only data with no human review
- Prompt templates copied into every example with little diversity
- Eval examples leaking into the train set
- "Gold" outputs that are inconsistent in tone or policy
- Data collected from old prompts that taught the wrong behavior

### What to record for each dataset version

- Source and collection method
- Filtering and cleaning steps
- Labeling instructions
- Known bias or coverage gaps
- Split policy
- Intended use and non-goals

---

## Technique Selection

### Supervised Fine-Tuning (SFT)

Use when you want consistent structure, style, or response policy from labeled
input-output pairs.

Good for:

- Support workflows
- Extraction formats
- Classification with explanation style constraints
- Domain-specific assistant tone

### Preference Optimization

Use when you have pairwise or graded preferences and want to refine behavior
after a usable SFT baseline exists.

Good for:

- Helpfulness vs. verbosity tradeoffs
- Brand tone preference
- Better ranking of multiple acceptable responses

### Parameter-efficient tuning

Use LoRA/QLoRA-style approaches when iteration speed, cost, or private deployment
matters more than training a fully customized large model.

---

## Eval Plan Before Training

Define these before the first training run:

- Primary task metric
- Regression suite against the current prompt-only or retrieval baseline
- Safety and policy checks
- Slice-based evaluation for important cohorts or document types
- Latency and cost expectations at serving time

### Compare against the right baselines

Always measure the tuned model against:

- Best prompt-only baseline
- Best prompt + retrieval baseline if retrieval is relevant
- Current production system

If the tuned model is not clearly better on the intended metric, do not ship it.

---

## Rollout Discipline

Treat a tuned model like a new production dependency.

### Release pattern

1. Register the dataset version, training config, and base model
2. Run offline evals on holdout data
3. Shadow or canary in production where possible
4. Monitor task quality, policy adherence, latency, and cost
5. Keep an immediate rollback path to the previous model or prompt system

### Monitor after launch

- Quality regressions by slice
- Safety failures
- Drift in user traffic compared with the training distribution
- Prompt wrappers that may now be redundant or conflicting

---

## Fine-Tuning Review Checklist

- Is tuning solving a behavior problem, not a retrieval problem?
- Is there enough real data to justify training?
- Are splits leakage-safe?
- Is the holdout set truly untouched?
- Is there a prompt-only baseline to beat?
- Is rollback trivial?
- Are model cards, dataset notes, and known limitations documented?

---

## Anti-Patterns

| Naive | Professional |
|---|---|
| Fine-tune to inject facts | Use retrieval for dynamic knowledge |
| Train on convenience data | Train on representative data with explicit splits |
| Measure only training loss | Evaluate on task metrics and policy behavior |
| Ship directly from offline wins | Shadow or canary before full rollout |
| Lose track of datasets and configs | Version datasets, code, prompts, and base models together |
