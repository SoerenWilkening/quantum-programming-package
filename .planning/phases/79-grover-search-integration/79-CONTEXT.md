# Phase 79: Grover Search Integration - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Single `ql.grover()` API that combines oracle + diffusion into a complete Grover search. Auto-calculates iteration count from search space size N and solution count M. Runs Qiskit simulation internally and returns measured Python value(s). Lambda/predicate oracles are Phase 80; amplitude estimation is Phase 81.

</domain>

<decisions>
## Implementation Decisions

### API signature
- Accepts any @ql.compile decorated function (not limited to @ql.grover_oracle) — auto-wraps with oracle semantics if needed
- Search register inferred from oracle function's type-annotated parameters — user does NOT pass register explicitly
- Supports multi-register oracles (e.g., oracle(x: qint, y: qint)) — diffusion applied to all search registers
- Auto-initializes equal superposition (H⊗n) on all search registers before iterations
- Solution count `m` is optional, defaults to 1
- Explicit `iterations=k` override parameter available to bypass auto-calculation
- Fully self-contained: creates circuit, initializes superposition, runs iterations, simulates, returns result

### Return value
- Returns a plain tuple: `(value, iterations)` for single-register oracles
- For multi-register oracles: `(x_val, y_val, ..., iterations)` — flat tuple, iterations always last
- Single shot simulation — value is sampled from probability distribution, not deterministic argmax

### Iteration count
- Auto-calculated using `floor(pi/4 * sqrt(N/M) - 0.5)` formula
- When M=0: run 0 iterations, return random measurement from initial superposition
- When M=N: skip iterations (0 iterations), measure immediately
- No maximum cap on iterations — trust the formula
- No validation that M <= N — let it run regardless

### Measurement & simulation
- ql.grover() runs Qiskit simulation internally — truly all-in-one black box
- True single-shot sampling from probability distribution (not statevector argmax)
- All registers measured (every qubit in every register passed to oracle)
- Circuit is internal — not exposed for inspection (no circuit in return value, no separate grover_circuit method)

### Claude's Discretion
- Internal circuit construction approach (how oracle/diffusion are composed)
- Error handling for invalid oracle functions
- How multi-register diffusion is applied (joint vs per-register)
- Qiskit backend selection and simulation details

</decisions>

<specifics>
## Specific Ideas

- "Simulation always uses only a single shot" — the framework is single-shot by design
- Oracle parameter inference means the simplest usage is just `ql.grover(oracle)` with no other arguments

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 79-grover-search-integration*
*Context gathered: 2026-02-21*
