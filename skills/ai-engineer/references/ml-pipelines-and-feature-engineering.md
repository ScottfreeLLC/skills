# ML Pipelines and Feature Engineering

Use this file for classical ML pipelines, tabular models, feature stores, or
prediction services that feed AI products.

---

## Baselines First

Always start with the cheapest baseline that can falsify the need for something
more complex.

Examples:

- Majority class or historical average
- Simple logistic regression or linear model
- Existing heuristic or business rule
- Current production model

If the advanced system does not clearly beat the baseline, stop.

---

## Split Discipline

Bad splits create fake progress.

### Choose the split that matches deployment

- Random split for IID tasks
- Group split when entities repeat across rows
- Time-based split when future data should never influence the past
- Stratified split when class balance matters

### Leakage rules

- Fit encoders, scalers, imputers, and selectors on train only
- Never aggregate future information into current features
- Avoid entity leakage through IDs, timestamps, or duplicated text
- Keep target-derived features out of training unless they are truly available online

Use pipeline abstractions so leakage prevention is enforced by construction.

---

## Feature Engineering Rules

### Prefer stable, explainable features first

- Aggregations with clear business meaning
- Time-window features aligned to what is available at prediction time
- Explicit missingness indicators when useful
- Encodings that can be reproduced online

### Be careful with

- High-cardinality categoricals with weak signal
- Hand-built text features when embeddings may dominate
- Leakage from post-event data
- Features that are expensive to compute in the serving path

### For feature selection

- Start with domain reasoning and ablations
- Use importance and SHAP carefully; they are diagnostics, not ground truth
- Drop features that create operational fragility unless they buy meaningful lift

---

## Metrics and Decision Alignment

Pick metrics that match the actual decision.

Examples:

- Precision / recall / F1 when class balance matters
- PR-AUC when positives are rare
- Calibration when downstream decisions use scores as probabilities
- Ranking metrics when only top-N results matter
- Cost-sensitive metrics when false positives and false negatives have different prices

Do not report accuracy alone on imbalanced problems.

---

## Reproducibility

Every training run should be replayable.

Record:

- Dataset version
- Feature definitions
- Split seed or split logic
- Model config and hyperparameters
- Code revision
- Eval outputs

If you cannot reproduce the run, you cannot debug the gain.

---

## Serving Concerns

Design feature pipelines with online reality in mind.

- Can every feature be computed within the latency budget?
- Are online and offline feature definitions identical?
- Is there a fallback when a data source is missing?
- Can you detect stale features or delayed joins?

Feature quality problems often look like model regressions in production.

---

## Monitoring

After launch, track:

- Feature drift
- Prediction distribution drift
- Calibration drift
- Slice failures
- Data freshness and join completeness
- Business outcome lagging indicators

Turn recurring production misses into new eval slices.

---

## Anti-Patterns

| Naive | Professional |
|---|---|
| Fit transforms on full data | Fit on train only |
| One metric for every task | Choose metrics that match the decision |
| Hand-run notebooks only | Package reproducible training pipelines |
| Ignore online feature availability | Design features for serving reality |
| No monitoring after launch | Track drift, calibration, and slices |
