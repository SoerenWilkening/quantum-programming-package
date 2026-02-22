# Phase 81: Amplitude Estimation (IQAE) - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement iterative quantum amplitude estimation (IQAE) as `ql.amplitude_estimate()`. Users can estimate the success probability of a quantum oracle with configurable precision and confidence. Uses QFT-free IQAE variant. No new oracle types or search strategies — reuses existing oracle and Grover infrastructure from Phases 79-80.

</domain>

<decisions>
## Implementation Decisions

### API surface
- Top-level export: `ql.amplitude_estimate(oracle, *registers, **kwargs)` — matches `ql.grover()` signature pattern
- Accepts same oracle types as grover(): @grover_oracle decorated functions AND lambda predicates
- Register passing mirrors grover() with `*registers` (not single register)
- Supports `width`/`widths` params like grover() for multi-register consistency
- Lives in its own module: `src/quantum_language/amplitude_estimation.py`
- Epsilon, confidence_level, max_iterations are keyword-only arguments

### Precision & confidence
- Default confidence level: 0.95 (95%)
- Default epsilon: Claude's discretion (pick sensible IQAE default from literature)
- Optional `max_iterations` parameter to cap oracle calls
- When max_iterations is hit before reaching precision: return best estimate + emit warning
- Warn (but allow) unreasonable precision requests that would require impractical iterations
- Shots per round determined by algorithm internally, no user-facing shots param
- Follow standard IQAE paper algorithm for everything not explicitly decided above

### Result format
- Returns a result object (class, not dict) with `.estimate` (float) and `.num_oracle_calls` (int)
- Result object behaves float-like: supports arithmetic, `float(result)` works (implement `__float__`, numeric dunder methods)
- Default Python repr (no custom pretty-printing)

### Integration with Grover
- Reuses existing oracle format — same @grover_oracle functions and lambda predicates
- Reuses grover() internal iteration machinery (oracle + diffusion) — no reimplementation
- Auto-synthesizes oracles from lambda predicates, same as grover()
- Supports adaptive mode (unknown M) using Phase 80's exponential backoff infrastructure
- grover() and amplitude_estimate() remain separate functions — no cross-linking return values
- Tests are standalone IQAE tests — not cross-validated against grover() results

### Claude's Discretion
- Default epsilon value
- Internal IQAE algorithm details (round scheduling, confidence interval narrowing)
- Warning message text for unreasonable precision / iteration cap
- Internal helper functions and code organization within the module

</decisions>

<specifics>
## Specific Ideas

- API should feel like a natural companion to `ql.grover()` — same oracle, same registers, different question (probability vs search)
- Lambda predicates should "just work": `ql.amplitude_estimate(lambda x: x > 5, x, epsilon=0.01)` with no extra setup

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 81-amplitude-estimation-iqae*
*Context gathered: 2026-02-22*
