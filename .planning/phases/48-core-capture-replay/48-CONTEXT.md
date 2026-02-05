# Phase 48: Core Capture-Replay - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

`@ql.compile` decorator that captures gate sequences on first call and replays them with qubit remapping on subsequent calls. Covers decorator API, capture mechanism, replay with remapping, caching, and return value handling. Optimization (Phase 49), controlled context (Phase 50), inverse/debug/nesting polish (Phase 51) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Decorator API surface
- Support both `@ql.compile` and `@ql.compile()` forms (standard Python decorator pattern)
- Cache key formed automatically from (function identity + classical arg values + qint widths)
- Optional `key=...` parameter for user-supplied cache key override in advanced cases
- Quantum vs classical arguments distinguished by type inspection at call time (qint/qbool = quantum, everything else = classical)
- Both positional and keyword arguments supported (standard Python calling convention)

### Return value handling
- In-place modification of input quantum arguments is allowed
- Functions can allocate new qubits internally (ancillas); replay allocates fresh ancillas each time
- Returned qints are backed by real, newly-allocated qubits on replay -- fully usable for subsequent operations
- Multi-return semantics: Claude's discretion based on what the capture system handles cleanly

### Cache behavior
- Global cache keyed by (function + args), single place to manage
- `ql.circuit()` clears all caches (silent by default, logged when `debug=True`)
- Configurable cache size limit via `@ql.compile(max_cache=N)` with sensible default; evicts oldest entries
- Per-function `my_func.clear_cache()` method for selective invalidation

### Error behavior
- TypeError raised immediately if non-quantum argument passed where quantum expected (fail fast, clear message)
- Partial captures discarded on exception -- next call retries capture from scratch
- `@ql.compile(verify=True)` mode runs both capture and replay, compares gate sequences for correctness checking
- Classical side effects (print, measurement, file I/O) silently ignored -- only gate operations captured and replayed

### Claude's Discretion
- Single vs tuple return implementation details
- Internal data structures for gate sequence storage
- Exact cache eviction strategy (LRU vs FIFO)
- How qubit remapping is represented internally
- Global state snapshot/restore mechanism during capture

</decisions>

<specifics>
## Specific Ideas

- Decorator should feel like standard Python -- both bare and parens forms, kwargs supported
- `verify=True` mode is for development/testing, not production use
- `clear_cache()` on individual functions is useful for testing workflows

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 48-core-capture-replay*
*Context gathered: 2026-02-04*
