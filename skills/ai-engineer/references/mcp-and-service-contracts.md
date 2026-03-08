# MCP and Service Contracts

Use this file when building or reviewing MCP servers, tool surfaces, or internal AI
APIs that tools call behind the scenes.

---

## Tool Surface Design

Treat tool descriptions as routing infrastructure.

Good tool definitions:

- describe the authority and scope of the tool
- include specific examples of when to call it
- avoid overlapping tools that compete for the same query
- use descriptive parameter names and constraints

Bad tool definitions:

- "Get data"
- multiple tools that can all answer roughly the same question
- parameters that hide domain meaning behind abbreviations

If the model cannot tell which tool is correct, it will guess.

---

## Transport and Compatibility

Real MCP deployments fail on details, not the happy path.

Check:

- trailing slash behavior on `/mcp` vs `/mcp/`
- redirect behavior for POST requests
- stateless HTTP mode if clients expect it
- auth middleware order
- rate limiting before expensive execution
- docs/openapi exposure policy in production

Compatibility bugs are part of product quality. If a client breaks on a 307 redirect,
fix the server behavior instead of calling it "someone else's problem."

---

## Structured Errors and Response Envelopes

If an MCP tool calls a downstream AI service, do not return opaque blobs.

Recommended error fields:

- `status`
- `status_code`
- `error.code`
- `error.message`
- `trace_id`
- `timings`

Recommended success metadata:

- provider/model
- retrieval stats when retrieval happened
- sources/citations
- contract version if the payload evolves

Clients and support teams need a consistent envelope to debug failures quickly.

---

## MCP Evaluation Rubric

Score the server on these dimensions:

| Dimension | What to check |
|---|---|
| Tools | Clear descriptions, good examples, focused scope, strong parameter naming |
| Security | Auth, rate limiting, credential handling, constant-time comparisons where relevant |
| Performance | Caching, timeouts, bounded retries, compatibility with client transport |
| Documentation | Setup, config, tool examples, failure modes, environment variables |
| Testing | Auth, payload validation, response contract, redirects, compatibility, latency-sensitive paths |
| Error handling | Structured responses, clear codes, graceful degradation |
| Compliance | Tool/resource/prompt behavior matches MCP expectations |

Use the rubric to compare changes over time, not just to write one report.

---

## Minimal Test Matrix

Every serious MCP server should have tests for:

- missing/invalid auth
- malformed requests
- valid tool invocation
- downstream service failure mapping
- redirect behavior and path normalization
- response envelope shape
- trace/header propagation
- rate limiting behavior if enabled

If tools can redirect users to another system, test the redirect payload explicitly.

---

## Contract-Driven Review Questions

- Could two tools plausibly answer the same query?
- Are tool descriptions specific enough for an LLM, not just a human engineer?
- What exact payload does a client receive on auth failure? On timeout? On partial success?
- Can support correlate an issue with a `trace_id`?
- Are transport quirks tested with real client assumptions in mind?

---

## Anti-Patterns

| Naive | Professional |
|---|---|
| Tool names/descriptions written for humans only | Tool specs optimized for model routing and client expectations |
| Many overlapping tools | Minimal, clearly differentiated tool set |
| Redirects left to framework defaults | Path normalization and compatibility tested explicitly |
| String-only error responses | Structured error envelope with codes and metadata |
| No downstream timing visibility | Stage timings and trace IDs surfaced |
| Manual spot checks only | Contract tests in CI |
