# Phase 15: Classical Initialization - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Initialize qint with classical value by setting qubits to |1⟩ based on binary representation. Users can create qint with an initial value (e.g., `qint(5)` creates auto-width qint initialized to 5). Superposition initialization is out of scope.

</domain>

<decisions>
## Implementation Decisions

### API signature
- Constructor argument: `qint(width, value=0)` — width first, value optional with default 0
- Auto-width mode: `qint(5)` creates auto-width qint initialized to 5 (breaking change from current behavior)
- Negative values supported via two's complement representation
- When only value provided, width auto-determined from minimum bits needed

### Overflow handling
- Truncate/mask: value masked to fit bit width (take lower bits only)
- Emit Python warning when truncation occurs
- Auto-width minimum: 1 bit (even for value=0)
- Negative auto-width: minimum bits for two's complement representation (e.g., -3 needs 3 bits)

### Validation behavior
- Accept int-like values: anything with `__int__` (numpy integers, etc.)
- Breaking change: `qint(5)` now means auto-width initialized to 5, not 5-bit zero
- Use `qint(width=5)` or `qint(5, 0)` for explicit 5-bit zero
- No deprecation period — clean break in v1.1

### Initialization timing
- X gates applied at construction immediately
- No distinction from regular X gates (optimizer can merge freely)
- No re-initialization after creation — immutable initial state
- Classical initialization only — no superposition init

### Claude's Discretion
- Exact auto-width calculation implementation
- Warning message text for truncation
- Internal helper function organization

</decisions>

<specifics>
## Specific Ideas

- API follows pattern: `qint(5)` reads as "quantum int initialized to 5"
- Two's complement for negative values consistent with how comparisons already work
- Truncation warning helps catch bugs without hard errors

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-classical-initialization*
*Context gathered: 2026-01-27*
