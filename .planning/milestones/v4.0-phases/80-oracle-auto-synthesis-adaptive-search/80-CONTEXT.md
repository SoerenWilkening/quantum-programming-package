# Phase 80: Oracle Auto-Synthesis & Adaptive Search - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can specify oracles as Python predicates (lambdas or named functions) instead of writing decorated oracle functions, and Grover search works when the solution count M is unknown via adaptive backoff. This phase adds predicate-to-oracle synthesis and BBHT adaptive search on top of the existing @ql.grover_oracle + ql.grover() infrastructure from Phases 77-79.

</domain>

<decisions>
## Implementation Decisions

### Lambda API Design
- Accept **any callable predicate** — lambdas, named functions, methods — not just lambda expressions
- Support **both** register passing styles: explicit register (`ql.grover(lambda x: x > 5, x)`) and width kwarg (`ql.grover(lambda x: x > 5, width=3)`)
- Support **multi-register predicates** (`lambda x, y: x + y == 10`) — each parameter maps to a separate search register
- Support **closures capturing classical values** — captured Python ints/floats become classical constants in the oracle circuit (`threshold = 5; lambda x: x > threshold`)
- Conversion uses **tracing approach** — call predicate with real qint objects, let existing qint operators capture gates. Reuses @ql.compile machinery, no AST parsing.
- Errors surface at circuit-build time (natural consequence of tracing approach)
- **Cache lambda oracles** same as decorated oracles — per source hash, width, arithmetic mode

### Compound Predicates
- Use **bitwise operators** for composition: `&` (AND), `|` (OR), `~` (NOT)
- Support **arbitrary nesting depth**: `((x > 5) & (x < 20)) | (x == 0)` — full expression tree from qbool operations
- Support **arithmetic in conditions**: `x * 2 > 10`, `x + y == 15` — leverages existing qint arithmetic operators
- Support **cross-register comparisons**: `x > y`, `x + y == 10` — full interaction between search registers
- **NOT/negation** supported via `~` operator on qbool
- qbool gets `__and__`, `__or__`, `__invert__` operators that return new qbool — enables bitwise syntax naturally
- **Ancilla management fully automatic** — auto-allocate and uncompute temporaries, user never sees them
- **Soft warning** (not hard error) when predicate + search register approaches qubit budget — user might target hardware, not simulator

### Adaptive Search Behavior
- Uses **BBHT algorithm** (Boyer-Brassard-Hoyer-Tapp) — each attempt picks random k in [1, 2^j], theoretically optimal
- **Return None** when search exhausts all attempts without finding a solution
- User can set **max_attempts= parameter** with sensible default (e.g., log2(N) attempts)
- **Always verify** found results — run predicate classically on measured value, retry if not a valid solution

### API Surface & Defaults
- **Single entry point**: `ql.grover()` handles everything — lambdas, decorated oracles, adaptive or exact
- **Default to adaptive search** when m= is omitted — most user-friendly, just works without knowing M
- **Opt out of adaptive** by passing `m=N` explicitly — providing m= disables adaptive and uses exact iteration count
- **Same return format**: `(value, iterations)` regardless of adaptive or not — iterations = total across all attempts
- Backwards compatible: existing `ql.grover(oracle, width=3, m=1)` calls continue to work unchanged

### Claude's Discretion
- Exact BBHT implementation details (random seed handling, growth factor)
- Default value for max_attempts
- Internal structure of the predicate-to-oracle wrapper
- How classical verification callback is derived from the predicate
- Cache eviction strategy for lambda oracles

</decisions>

<specifics>
## Specific Ideas

- Lambda predicates should feel like writing a Python `if` condition — `lambda x: x > 5` should "just work"
- The BBHT algorithm (random k in [1, 2^j]) was specifically chosen over simple exponential doubling
- Classical verification after measurement ensures correctness — never return a non-solution

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 80-oracle-auto-synthesis-adaptive-search*
*Context gathered: 2026-02-22*
