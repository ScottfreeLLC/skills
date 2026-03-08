# NLP and Data Workflows

Use this file for classical NLP, text preprocessing, schema audits, and exploratory
analysis on data that will feed AI systems.

---

## Text Preprocessing Rules

Every text transformation is a modeling decision. Keep only the ones that help.

### Good defaults

- Preserve raw text alongside normalized text
- Normalize obvious encoding and whitespace issues
- Keep punctuation unless the model or feature pipeline clearly benefits from removal
- Record language and source metadata early

### Do not do this by habit

- Lowercase everything without checking whether case carries signal
- Strip punctuation before embeddings
- Remove stop words before transformer-based retrieval
- Hand-roll tokenization or sentence splitting when a mature library exists

---

## Library Choices

Pick libraries based on the task, not nostalgia.

### Useful categories

- Token counting: `tiktoken` or provider-specific tokenizers
- Classical tokenization and sentence segmentation: spaCy, Stanza, NLTK
- Language detection: fastText, lingua, or equivalent
- NER and labeling baselines: spaCy, GLiNER, task-specific models
- Fuzzy matching and dedupe: rapidfuzz, record-linkage style tools

If a library decision is current-version-sensitive, verify it live before implementation.

---

## Document and Corpus Audits

Before modeling on a text corpus, profile it.

Check:

- Document counts by source
- Language distribution
- Length distribution
- Duplicate and near-duplicate rate
- Empty or boilerplate-heavy documents
- Timestamp coverage and freshness
- Label quality if supervised tasks are involved

Many retrieval and classification problems are data-shape problems first.

---

## EDA for AI Datasets

EDA is not just charts. It is risk discovery.

### Minimum audit

- Column schema and dtype review
- Missingness map
- Cardinality and top values
- Target balance
- Outlier review
- Leakage candidates
- Join-key sanity checks

### Text-specific audit

- Which sources dominate volume?
- Are labels confounded by source or time?
- Do near-duplicate examples span train and eval?
- Are there multilingual, OCR, or formatting failure pockets?

---

## Label and Annotation Quality

If humans or heuristics produced labels, inspect disagreement.

- Sample false positives and false negatives manually
- Track annotation ambiguity, not just final labels
- Write label guidelines if multiple people annotate
- Separate hard cases into their own evaluation slice

Weak labels are acceptable only if their failure pattern is understood.

---

## Feature Extraction from Text

For classical pipelines:

- Start with simple, interpretable features when baselines matter
- Use embeddings when semantics matter more than exact token counts
- Keep provenance from raw text to derived feature
- Benchmark sparse, dense, and hybrid representations instead of assuming one wins

For retrieval and LLM systems, over-normalizing text often destroys useful signal.

---

## Anti-Patterns

| Naive | Professional |
|---|---|
| Regex for everything | Use mature NLP libraries and task-specific models |
| Clean once, lose the raw text | Preserve raw text and derived text separately |
| Skip corpus profiling | Audit source mix, duplicates, missingness, and length |
| Ignore annotation disagreement | Study ambiguity and create eval slices |
| Treat EDA as optional | Use EDA to shape data cleaning, splits, and evals |
