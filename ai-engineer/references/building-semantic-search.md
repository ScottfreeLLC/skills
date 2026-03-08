# Building Semantic Search: Prototype to Production

RAG is an information retrieval problem with 60 years of IR history behind it.
Most failures come from ignoring that history, not from wrong model choices.

This file covers the complete picture: model selection → chunking → ingestion →
retrieval → ranking → caching → advanced patterns → production operations.
Read it end to end once, then use sections as reference.

---

## System Architecture

Two pipelines. Never one. Ingestion and query have incompatible resource profiles —
they compete for CPU/GPU if you run them together, and ingestion latency bleeds into
query SLAs.

```
╔══════════════════════════════════════════════════════════╗
║           OFFLINE: INGESTION PIPELINE                    ║
║  Trigger: new/updated documents (batch, CDC, or queue)   ║
║                                                          ║
║  Source (DB / S3 / API)                                  ║
║       │                                                  ║
║       ▼                                                  ║
║  Document Processor                                      ║
║  · Extract text (PDF, HTML, DOCX, etc.)                  ║
║  · Normalize (strip boilerplate, fix encoding)           ║
║  · Detect language / content type                        ║
║       │                                                  ║
║       ▼                                                  ║
║  Chunker                                                 ║
║  · RecursiveCharacterTextSplitter (default)              ║
║  · SemanticChunker (better recall, slower)               ║
║  · HierarchicalChunker (parent/child, best balance)      ║
║  · Or skip chunking entirely for short docs              ║
║  · Attach metadata: doc_id, chunk_id, source, date       ║
║       │                                                  ║
║       ▼                                                  ║
║  Embedding Service  [batched, async, idempotent]         ║
║  · hash(text) → skip if already indexed                  ║
║  · Batch size 64–256; retry with exponential backoff     ║
║  · DLQ for failures — don't silently drop documents      ║
║       │                                                  ║
║       ▼                                                  ║
║  Vector Store Writer                                     ║
║  · Upsert vectors + full metadata                        ║
║  · Record content_hash → avoid re-embedding on re-runs   ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║           ONLINE: QUERY PIPELINE                         ║
║  Trigger: user request; SLA target <200ms                ║
║                                                          ║
║  User Query                                              ║
║       │                                                  ║
║       ▼                                                  ║
║  Semantic Cache  [check before embedding]                ║
║  · Redis vector search, cosine sim ≥ 0.92                ║
║  · Hit → return immediately (<2ms)                       ║
║  · Miss → continue pipeline                              ║
║       │ miss                                             ║
║       ▼                                                  ║
║  Query Embedder  [same model as ingestion — always]      ║
║  · Async, non-blocking                                   ║
║  · LRU-cache query embeddings (TTL 1h)                   ║
║       │                                                  ║
║       ▼                                                  ║
║  Hybrid Retriever                                        ║
║  · Dense: ANN (HNSW) over vector store                   ║
║  · Sparse: BM25 over inverted index                      ║
║  · Fuse via Reciprocal Rank Fusion (RRF)                 ║
║  · Apply metadata pre-filters (date, category, tenant)   ║
║  · Retrieve k=20 candidates (not 5)                      ║
║       │                                                  ║
║       ▼                                                  ║
║  Cross-Encoder Reranker                                  ║
║  · Score full query-document pairs (not bi-encoder)      ║
║  · Drop results below relevance threshold (0.7)          ║
║  · Return top-5 to caller                                ║
║       │                                                  ║
║       ▼                                                  ║
║  Results + Citations                                     ║
║  · Chunk text + source metadata                          ║
║  · Write result to semantic cache                        ║
╚══════════════════════════════════════════════════════════╝

CROSS-CUTTING: trace every request end-to-end
latency per stage | recall@k | cache hit rate | embedding cost | rerank drop rate
```

**Query latency budget** (target <200ms total):
```
Semantic cache check:   <2ms    cache hit → done
Query embedding:        10–30ms API; <1ms local model
Hybrid ANN + BM25:      10–50ms
Cross-encoder rerank:   20–80ms Cohere API; 5–20ms local
─────────────────────────────────
Total (cache miss):     40–160ms  ✓
Total (cache hit):      <5ms      ✓
```

---

## Step 1: Embedding Model Selection

Use current retrieval benchmarks and official model docs before selecting an embedder.
The [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) is a good
starting point, but rankings change and different task families reward different models.

Do not optimize for "top overall" if your task is clearly multilingual, code-heavy,
latency-constrained, or domain-specific.

### Candidate model families to benchmark first

| Use case | Candidate families | What to verify |
|---|---|---|
| General proprietary retrieval | Provider flagship embedding models | Retrieval scores, latency, ecosystem fit |
| Enterprise/private deployment | Provider enterprise SKUs or VPC options | Data residency, throughput, auth model |
| Open-source multilingual | Qwen, BGE, Jina, E5 families | Language coverage, hardware cost, license |
| Lightweight local deployment | Smaller BGE or Nomic-class models | Recall loss vs. latency gain |
| Long documents | Long-context embedding families | Whether long-context really beats chunking for your corpus |
| Code retrieval | Code-specialized embeddings | Language support and benchmark relevance |
| Domain-specific retrieval | Fine-tuned or domain-adapted embedders | Domain lift vs. maintenance burden |

**Always comment the choice**: `# Selected for multilingual retrieval, local deployment, and acceptable recall on our benchmark set`

**Hard rule**: ingestion and query must use the same model at the same version. Cosine
similarity is meaningless across different embedding spaces. Pin the model version in
config; a silent model upgrade breaks retrieval without any error.

**Embedding model choice matters as much as chunking strategy** — Superlinked's HotpotQA
tests showed model selection can dominate chunking strategy in retrieval accuracy.

---

## Step 2: Chunking

### Do you need chunking at all?

This is the first question. For short, single-purpose documents (FAQs, product
descriptions, support tickets), document-level embedding often outperforms chunking.
Chunking can actually *hurt* retrieval accuracy when documents are already focused
and aligned with likely queries.

**When to chunk**: Long, multi-topic documents (manuals, policies, reports, PDFs).
Chunking is essential when documents exceed the embedding model's context window
or when different sections would match different queries.

**When to skip**: Short documents (<512 tokens) that are already self-contained.

### Strategy selection

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
import hashlib

embedding_model = build_embedding_model(model="your-embedding-model")

# Default for most text — fast, predictable, validated as best general-purpose default
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,     # tokens; tune per task (see table below)
    chunk_overlap=64,   # 10–15% of chunk_size; see overlap note below
    separators=["\n\n", "\n", ". ", " "],  # paragraph → sentence → word
)

# For topic-boundary-aware chunking — slower but better recall on mixed-topic docs
# Caution: can produce very small fragments on some corpora
semantic_splitter = SemanticChunker(
    embedding_model,
    breakpoint_threshold_type="percentile",  # splits where meaning shifts
    breakpoint_threshold_amount=95,
)
```

### Hierarchical chunking (production recommendation)

Use parent chunks for context, child chunks for retrieval precision:

```python
# Parent chunks: 1000–1500 tokens (provide context to LLM)
# Child chunks: 256–300 tokens (used for retrieval)
# When a child chunk matches, return the parent chunk to the LLM

parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=60)

# Index child chunks for retrieval; store parent-child mapping
# On match: retrieve child, expand to parent for LLM context
```

### Sizing by task

| Task | chunk_size | chunk_overlap |
|---|---|---|
| Semantic retrieval (most RAG) | 256–512 tok | 32–64 tok |
| Dense QA, longer passages | 512–1024 tok | 64–128 tok |
| Summarization context | 1024–2048 tok | 128–256 tok |
| Code | Function / class boundary | 0–32 tok |
| Hierarchical (child) | 256–300 tok | 30–60 tok |
| Hierarchical (parent) | 1000–1500 tok | 100–200 tok |

Smaller chunks improve retrieval recall. Larger chunks give the LLM more context once
retrieved. The sweet spot for most RAG is 512 tokens with recursive splitting.

**Note on overlap**: Common wisdom recommends 10–15% overlap. However, a January 2026
systematic analysis using SPLADE retrieval found overlap provided no measurable benefit
and only increased indexing cost. Test what works for your data and retrieval model —
don't assume overlap is always worth the storage trade-off.

### Always attach metadata

```python
def chunk_document(doc_text: str, metadata: dict) -> list:
    """Chunk a document and attach full provenance metadata to every chunk."""
    chunks = splitter.create_documents(texts=[doc_text], metadatas=[metadata])
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "chunk_id": i,
            "total_chunks": len(chunks),
            # content hash enables idempotent ingestion — skip if already indexed
            "content_hash": hashlib.md5(chunk.page_content.encode()).hexdigest(),
        })
    return chunks
```

Every chunk must carry: `doc_id`, `chunk_id`, `source`, `section` (if available), `date`.
Without metadata, you can't filter, you can't cite sources, and you can't debug retrievals.

### Contextual headers

Prepend document-level context to each chunk to reduce ambiguity during retrieval:

```python
def add_contextual_header(chunk, doc_title: str, section_title: str) -> str:
    """Prepend document context to chunk for better retrieval."""
    header = f"Document: {doc_title}\nSection: {section_title}\n\n"
    return header + chunk.page_content
```

This is a low-effort, high-impact improvement — chunks like "The policy applies to
all employees" become retrievable when prefixed with the document and section they
came from.

---

## Step 3: Ingestion Pipeline

### Idempotent async worker

```python
import hashlib
from celery import Celery
from redis import Redis
from tenacity import retry, stop_after_attempt, wait_exponential

app = Celery("ingestion", broker="redis://localhost:6379/0")
redis_client = Redis()
INGESTED_PREFIX = "ingested:"

@app.task(bind=True, max_retries=3, acks_late=True)
def ingest_document(self, doc_id: str, text: str, metadata: dict):
    """
    Idempotent ingestion: skips unchanged documents.
    acks_late=True — task only ACKed after success, not on receipt.
    Failed tasks go back to queue; exhausted retries go to DLQ.
    """
    content_hash = hashlib.md5(text.encode()).hexdigest()
    state_key = f"{INGESTED_PREFIX}{doc_id}"

    stored_hash = redis_client.get(state_key)
    if stored_hash and stored_hash.decode() == content_hash:
        return {"status": "skipped", "doc_id": doc_id}  # nothing changed

    try:
        chunks = chunk_document(text, metadata)
        texts = [c.page_content for c in chunks]
        embeddings = embedding_service.embed_documents(texts)  # batched

        vector_store.upsert([
            {
                "id": f"{doc_id}_{c.metadata['chunk_id']}",
                "values": emb,
                "metadata": c.metadata,
                "text": c.page_content,
            }
            for c, emb in zip(chunks, embeddings)
        ])

        redis_client.set(state_key, content_hash)
        return {"status": "ingested", "doc_id": doc_id, "chunks": len(chunks)}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### Batched embedding service

Embedding is almost always the throughput bottleneck in ingestion. Batch aggressively.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class EmbeddingService:
    def __init__(self, model: str, batch_size: int = 128):
        self.embedder = build_embedding_model(model=model)
        self.batch_size = batch_size

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        for i in range(0, len(texts), self.batch_size):
            results.extend(self._embed_batch(texts[i : i + self.batch_size]))
        return results

    def embed_query(self, query: str) -> list[float]:
        return self.embedder.embed_query(query)
```

**Scaling ingestion throughput:**
1. Batch size 128–256 per API call
2. Multiple concurrent workers (Celery concurrency or async tasks)
3. Local model on GPU (`bge-base`, `nomic-embed-text`) — removes API latency and per-token cost
4. Content hash deduplication — never re-embed unchanged documents

---

## Step 4: Hybrid Retrieval

Vector-only retrieval misses exact keyword matches. Hybrid search — dense + sparse — consistently
outperforms either alone on real-world queries. The improvement is most pronounced on queries
containing proper nouns, product names, IDs, or technical terms.

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever

def build_retriever(
    vector_store,
    documents: list,
    dense_k: int = 20,       # retrieve wide; reranker narrows
    sparse_k: int = 20,
    rerank_top_n: int = 5,
    min_relevance_score: float = 0.7,
) -> ContextualCompressionRetriever:
    """
    Production retriever: dense ANN + BM25 → RRF fusion → cross-encoder reranking.

    Retrieve k=20, rerank to top 5. The ANN index uses bi-encoder similarity (fast,
    approximate). The reranker scores full query-document pairs (slower, precise).
    These two steps are complementary — don't skip either.
    """
    dense = vector_store.as_retriever(search_kwargs={"k": dense_k})
    sparse = BM25Retriever.from_documents(documents, k=sparse_k)

    # weights=[sparse, dense] — tune on your eval set, start here
    hybrid = EnsembleRetriever(retrievers=[sparse, dense], weights=[0.4, 0.6])

    # Cross-encoder reranker — pick the provider/model that fits your stack
    reranker = build_reranker(model="your-reranker-model", top_n=rerank_top_n)

    return ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=hybrid,
    )
```

### Relevance threshold — always filter before the LLM sees results

```python
results = retriever.invoke(query)
relevant = [r for r in results if r.metadata.get("relevance_score", 1.0) >= 0.7]

if not relevant:
    return "I don't have enough information to answer this question."
    # Don't hallucinate an answer — irrelevant context actively hurts LLM quality
```

### Query expansion — when recall matters more than latency

```python
# Multi-query: generate N rephrasings of the query, retrieve for each, merge
from langchain.retrievers.multi_query import MultiQueryRetriever
retriever = MultiQueryRetriever.from_llm(retriever=base_retriever, llm=llm)

# HyDE: generate a hypothetical answer, embed it, retrieve on that embedding
# Good when queries are short/vague and documents are long/detailed

# Self-query: LLM parses metadata filters from natural language query
# e.g., "recent articles about pricing" → filter(date >= last_month) + "pricing"
from langchain.retrievers.self_query.base import SelfQueryRetriever
```

### Context construction

Don't just concatenate chunks. Structure context so the LLM can navigate it.

```python
system = """Answer using ONLY the provided context. Cite sources as [doc_id].
If the context doesn't contain the answer, say so explicitly — do not invent."""

# Lost-in-the-middle: LLMs attend poorly to middle context.
# Put most relevant chunks first and last; less relevant in the middle.
context_str = "\n\n".join([
    f"[{i}] Source: {doc.metadata['source']} | Date: {doc.metadata.get('date', 'unknown')}\n{doc.page_content}"
    for i, doc in enumerate(relevant_docs)
])
```

---

## Step 5: Semantic Cache

Cache retrieval results for semantically similar queries. In production, 60–80% of queries
cluster around the same topics and hit the cache — this is the single highest-leverage
latency and cost optimization available.

```python
from langchain.cache import RedisSemanticCache
from langchain.globals import set_llm_cache
import redis, hashlib, json

# Semantic cache: returns cached results for cosine-similar queries
# score_threshold 0.90–0.95 — higher = stricter matching, fewer false hits
semantic_cache = RedisSemanticCache(
    redis_url="redis://localhost:6379",
    embedding=build_embedding_model(model="your-embedding-model"),
    score_threshold=0.92,
)
set_llm_cache(semantic_cache)

# For retrieval result caching (not just LLM output):
def cached_retrieve(query: str, retriever, ttl_seconds: int = 3600) -> list:
    key = f"retrieve:{hashlib.md5(query.encode()).hexdigest()}"
    hit = redis_client.get(key)
    if hit:
        return json.loads(hit)
    results = retriever.invoke(query)
    redis_client.setex(key, ttl_seconds, json.dumps([r.dict() for r in results]))
    return results
```

Set TTL based on how often your data changes. For mostly-static corpora, TTL of hours
is fine. For live data, shorter TTL or cache invalidation on index writes.

---

## Step 6: Vector Store Selection

| Scenario | Recommended | Notes |
|---|---|---|
| Already on Postgres | `pgvector` | Aurora 0.8.0+: `relaxed_order` mode, 9x faster, 95–99% recall vs strict |
| AWS-native | OpenSearch k-NN | Separate ML nodes from data nodes for inference |
| Azure-native | Azure AI Search | Native semantic reranking, hybrid search built-in |
| Managed, no ops | Pinecone serverless | Auto-scales; ~150ms P90 at scale |
| Self-hosted, large scale | Qdrant or Milvus | Qdrant: simpler ops; Milvus: GPU acceleration, billion-scale |
| Multi-tenant SaaS | Qdrant | Namespace isolation per tenant |
| Prototype / local | Chroma, FAISS | Do not use in production |
| Semantic cache | Redis | Sub-millisecond latency; doubles as session state |

---

## Step 7: HNSW Index Tuning

Every vector store uses HNSW under the hood. Most teams never touch the defaults and
wonder why recall degrades as the corpus grows. Three parameters control the tradeoff:

| Parameter | When set | Effect | Start value |
|---|---|---|---|
| `M` | Index build | Edge density. Higher = better recall + more RAM | 16 |
| `ef_construction` | Index build | Graph quality. Higher = better recall + slower build | 200 |
| `ef_search` | Query time — **tunable live** | Search depth. Higher = better recall + more latency | 100 |

**Recall-latency table (10M vectors):**

| ef_search | Recall@10 | P95 Latency |
|---|---|---|
| 50 | ~85% | ~1ms |
| 100 | ~92% | ~3ms |
| 200 | ~96% | ~6ms |
| 400 | ~98% | ~12ms |

**Critical**: HNSW recall degrades silently as corpus grows. At 100k vectors, ef_search=100
gives ~96% recall. At 10M vectors, the same setting may give ~85% — the system looks
healthy by infrastructure metrics while the LLM receives worse context and hallucinates more.
Re-benchmark recall@k after each order-of-magnitude growth.

```python
# ef_search can be tuned live without rebuilding the index
# Qdrant:
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
client.update_collection("documents", hnsw_config={"ef": 200})

# pgvector:
# SET hnsw.ef_search = 200;  -- session-level, or set in connection pool config
```

---

## Step 8: Advanced RAG Patterns

Layer these on top of the core pipeline when basic hybrid retrieval isn't enough.
Each adds complexity — justify with evals before adopting.

### CRAG (Corrective RAG)

Check retrieval quality *before* generation. If context is weak, fall back to
broader search or admit ignorance rather than generating with bad context.

```python
async def corrective_rag(query: str, retriever, llm) -> dict:
    """CRAG: verify retrieval quality before generating."""
    results = retriever.invoke(query)

    # Grade retrieved documents for relevance
    grading_prompt = (
        f"Is this document relevant to the question: '{query}'?\n"
        f"Document: {{doc}}\nAnswer YES or NO."
    )
    relevant_docs = []
    for doc in results:
        grade = await llm.ainvoke(grading_prompt.format(doc=doc.page_content))
        if "YES" in grade.content.upper():
            relevant_docs.append(doc)

    if not relevant_docs:
        # Fallback: broader search, web search, or honest "I don't know"
        return {"answer": "I couldn't find relevant information.", "confidence": 0.0}

    return await generate_answer(query, relevant_docs)
```

### HyDE (Hypothetical Document Embeddings)

When queries are short or vague, generate a hypothetical answer, embed *that*,
and retrieve documents similar to the hypothesis. Bridges the gap between
query-style text and document-style text.

```python
# 1. Generate hypothetical answer
hypothesis = llm.invoke(f"Write a short paragraph answering: {query}")
# 2. Embed the hypothesis (not the query)
hypo_embedding = embedder.embed_query(hypothesis.content)
# 3. Retrieve using hypothesis embedding
results = vector_store.similarity_search_by_vector(hypo_embedding, k=20)
# 4. Rerank against original query
final_results = reranker.rerank(query, results, top_k=5)
```

### Self-RAG

Train or prompt the model to decide *when* to retrieve (not every query needs it)
and to critique its own outputs for faithfulness. Improves factuality and citation
accuracy by making retrieval an active decision rather than automatic.

### Graph RAG / Knowledge Graphs

Structure entities and their relationships alongside vector retrieval. Particularly
valuable for queries involving relationships, multi-hop reasoning, or structured
data (org charts, product hierarchies, regulatory dependencies).

Tools: Neo4j + LangChain/LangGraph integration, LLM Graph Builder for auto-extraction.

### Contextual Headers

Covered in the chunking section above. Prepend document-level context (title, section,
date) to each chunk so retrieval doesn't lose track of what document a chunk came from.

### Parent Document Retrieval

Retrieve on small child chunks (high precision), but return the larger parent chunk
to the LLM (more context). Covered in the hierarchical chunking section above.

---

## Production Anti-Patterns

| ❌ Anti-pattern | ✅ Fix |
|---|---|
| Ingestion and query share a process | Separate async ingestion workers + stateless query API |
| Re-embedding unchanged docs on every run | `hash(text)` → skip if already indexed |
| Different embedding model for query vs ingestion | One model, pinned version. Mixing silently breaks cosine similarity |
| Vector-only search | Hybrid: dense + BM25 → RRF → cross-encoder reranker |
| No relevance threshold | Drop below-threshold results — bad context makes LLM worse, not better |
| top_k=5 directly from ANN | Retrieve k=20, rerank to 5. ANN is approximate; reranker is precise |
| ef_search at default forever | Benchmark recall@k on your corpus; re-benchmark after 10x growth |
| No semantic cache | 60–80% hit rates on repeat traffic; highest-ROI optimization available |
| Chunking without metadata | Every chunk needs doc_id, chunk_id, source, section, date |
| No DLQ for ingestion failures | Failed embeddings vanish silently; documents never get indexed |
| Relevance threshold tuned once, never revisited | Score distribution shifts as corpus and models change |
| Chunking everything without asking "do I need to?" | Short focused docs may work better as whole documents |
| No context quality check before generation | CRAG pattern: verify retrieval relevance before generating |
| No contextual headers on chunks | Chunks without document context are ambiguous during retrieval |

---

## Observability

Instrument every stage. Without per-stage latency and quality metrics, you cannot diagnose
whether a degraded response came from retrieval, reranking, or the LLM.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RetrievalTrace:
    query_id: str
    query: str
    cache_hit: bool = False
    embed_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    num_candidates: int = 0          # before reranking
    num_results: int = 0             # after threshold + reranking
    top_score: Optional[float] = None
    below_threshold_dropped: int = 0
    error: Optional[str] = None
```

**Alert thresholds:**

| Metric | Alert if... | Likely cause |
|---|---|---|
| P95 query latency | > 200ms | Cache miss rate high? Reranker slow? ef_search too high? |
| Recall@k (eval set) | Drops > 2% | HNSW degraded from corpus growth → increase ef_search |
| Cache hit rate | < 30% on repeat traffic | Threshold too strict, or TTL too short |
| `below_threshold_dropped` | > 50% of candidates | Wrong embedding model, or model mismatch |
| Ingestion queue depth | Growing unbounded | Worker capacity or embedding API rate limit |

**RAG quality metrics** (run async on sampled production traffic, not inline):

```python
from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
# faithfulness:     is the answer grounded in the retrieved context?
# context_recall:   did retrieval find the information needed to answer?
# context_precision: is the retrieved context actually relevant?
# answer_relevancy:  does the answer address the question asked?
#
# Note: verify import paths against current ragas version — API has changed across releases
```
