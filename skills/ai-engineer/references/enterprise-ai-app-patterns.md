# Enterprise AI App Patterns

Use this file when the task is not just "call an LLM," but "ship and run an AI
application" with APIs, startup logic, external dependencies, routing, and support burden.

---

## Composition Root First

Keep dependency wiring in one place.

Good homes:

- FastAPI `lifespan`
- Flask app factory
- Dedicated bootstrap module
- CLI startup command

That layer should:

- Load config and secrets before imports that depend on them
- Create provider clients, caches, and tracing wrappers once
- Register routes, middleware, and health checks
- Flush telemetry and close clients on shutdown

Keep business logic out of bootstrap code. Route handlers should consume already-wired
services, not construct them.

### Review questions

- Which module is the composition root?
- What happens if one dependency is missing at startup?
- Does startup fail fast when it should, and degrade gracefully when it can?

---

## Graceful Degradation for Optional Dependencies

Observability, analytics, and secondary providers should not force the whole service down.

Prefer a thin wrapper with a no-op fallback:

```python
class NoOpSpan:
    def update(self, **kwargs): ...
    def end(self, **kwargs): ...

@contextmanager
def traced_span(name: str, enabled: bool):
    if not enabled:
        yield NoOpSpan()
        return
    with provider.start_span(name) as span:
        yield span
```

Use this pattern for:

- tracing clients
- cost tracking
- optional caches
- fallback model providers

Do not leak tracing setup details into every business function.

---

## Health Signals: Liveness, Readiness, Version

One `/health` endpoint is usually not enough.

- **Liveness**: process is up and event loop is healthy
- **Readiness**: required dependencies are reachable enough to serve traffic
- **Version**: build or package version matches what you think is running

Good readiness checks are dependency-aware but cheap:

- S3 head object
- DB `SELECT 1`
- downstream auth token fetch
- model gateway ping

Bad readiness checks:

- expensive full workflow runs on every probe
- "returns 200 as long as Python started"

Startup automation is part of the same story. Scripts that validate auth, connectivity,
and version drift before a developer starts working can save more time than another prompt tweak.

---

## Response Contracts and Support Metadata

If an AI service has users, support, or downstream clients, define a stable envelope.

Recommended contract shape:

```json
{
  "response": {
    "content": "...",
    "format": "text"
  },
  "metadata": {
    "status": "success",
    "status_code": 200,
    "trace_id": "abc123",
    "timings": {"total_ms": 412},
    "sources": [],
    "model": {"provider": "openai", "id": "model-name"},
    "extensions": {}
  }
}
```

Include:

- `trace_id` for support correlation
- stage timings
- provider/model identifiers when relevant
- source provenance for grounded answers
- explicit redirect or unresolved states in `extensions`

Do not make clients reverse-engineer behavior from free-form strings.

---

## Deterministic Routing Beats Vague Prompt Routing

If a request must be routed between products, datasets, or execution paths, start with
deterministic logic or a tightly-scoped classifier.

Good routing systems:

- have explicit defaults
- return reasons
- log routing decisions
- are testable independently from generation

Use LLM routing when semantics genuinely matter, but still constrain the output and
define safe defaults.

Examples:

- product routing across multiple AI backends
- query complexity routing for retrieval fan-out
- redirecting menu questions away from report search

Do not bury critical routing decisions inside a giant answer prompt.

---

## Architecture Tests

Production AI codebases drift toward accidental coupling. Add tests that enforce boundaries.

Common checks:

- API modules must not import UI/frontend modules
- core/business logic must not import web framework details
- infrastructure must not import frontend or deleted legacy packages
- prompt modules must not reach into request objects

AST-based tests are cheap and high leverage:

```python
def test_api_does_not_import_frontend():
    for file_path in get_python_files("app/api"):
        imports = get_imports_from_file(file_path)
        assert not any(name.startswith("app.ui") for name in imports)
```

This is much cheaper than discovering the coupling during a refactor.

---

## Prompt and Model Configuration Discipline

AI application code rots when prompt text and model IDs are duplicated in handlers.

Prefer:

- prompt assets or prompt modules with explicit versions
- config-driven model selection
- documented fallback order
- one place to change provider/model defaults

Good:

- `SYSTEM_PROMPT_VERSION=v2`
- `PRIMARY_LLM_PROVIDER=openai`
- `FALLBACK_LLM_PROVIDER=bedrock`

Bad:

- hard-coded embedding or model IDs spread across services
- silent provider changes with no eval or rollout note

---

## Startup and Runtime Checklist

- Can the app start without optional observability?
- Are required dependencies validated before serving traffic?
- Are shutdown flushes bounded by timeout?
- Is the request contract documented and tested?
- Are routing decisions inspectable?
- Are model and prompt choices centralized?
- Are architecture boundaries enforced by tests?

---

## Anti-Patterns

| Naive | Professional |
|---|---|
| Import-time network calls everywhere | Explicit startup phase with failure policy |
| Route handler creates clients on every request | Prewired services with clear lifetime |
| Trace setup mixed into domain logic | Wrapper/decorator with no-op fallback |
| One health endpoint for everything | Liveness, readiness, and version treated separately |
| Free-form success/error payloads | Stable response envelope with metadata |
| Routing hidden in one giant prompt | Deterministic router or constrained classifier |
| No boundary enforcement | Architecture tests in CI |
