# Phase 77: Oracle Infrastructure - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can create quantum oracles with correct phase-marking semantics that integrate with @ql.compile. Includes @ql.grover_oracle decorator with compute-phase-uncompute enforcement, ancilla validation, bit-flip auto-wrapping, and oracle caching. Grover search API, diffusion operator, and adaptive search are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Decorator API design
- @ql.grover_oracle layers on top of @ql.compile — user writes both decorators, oracle adds validation/wrapping
- Decorator accepts optional parameters (e.g., bit_flip=True, validate=False)
- Oracle function signature takes search register only: `def my_oracle(x: qint)`
- No explicit target qubit parameter — system handles ancilla internally when needed

### Validation & error behavior
- Non-zero ancilla delta is always a hard error — no warnings, no repair mode
- Compute-phase-uncompute ordering violations produce minimal error messages (short, user reads docs)
- @ql.grover_oracle(validate=False) allows advanced users to bypass validation checks
- Validation timing is Claude's discretion based on compilation pipeline

### Phase kickback auto-wrapping
- User explicitly declares bit-flip oracles via @ql.grover_oracle(bit_flip=True)
- Default is bit_flip=False — phase oracle assumed unless declared
- When bit_flip=True, system auto-allocates ancilla target qubit initialized to |-> internally
- If bit_flip=True but no bit-flip detected in the oracle circuit, hard error (mismatch)

### Caching semantics
- Oracle caching is purely internal — no user-facing API surface
- Cache key includes: oracle function, arithmetic_mode (QFT vs Toffoli), and search register width
- Cache is global/persistent across @ql.compile sessions within the same Python process
- Cache key includes hash of function source code — redefining an oracle auto-invalidates the cache

### Claude's Discretion
- Validation timing (decoration time vs circuit generation time)
- Compute-phase-uncompute enforcement strategy (post-hoc analysis vs syntax enforcement)
- Exact error message wording
- Ancilla target qubit lifecycle management for bit-flip wrapping
- Cache data structure and eviction policy

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 77-oracle-infrastructure*
*Context gathered: 2026-02-20*
