# Phase 100: Variable Branching - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Walk operators support trees where different nodes have different numbers of valid children, with amplitude angles computed dynamically from predicate evaluation. Variable branching replaces the existing uniform branching (which becomes a fast-path special case). Detection and demo are separate phases (Phase 101).

</domain>

<decisions>
## Implementation Decisions

### Predicate API Design
- Reuse the existing `predicate(node) -> (accept, reject)` interface — no new callback needed
- Framework internally navigates to child states by temporarily setting branch registers for the next depth to each child index (0..d-1), advancing the height register, calling the predicate, then reversing
- User's predicate sees a complete node state — all navigation is internal to the framework
- Allocate one dedicated ancilla qbool per potential child to store validity (reject) results
- Evaluate predicate once per child, store results, use for counting and cascade
- Uncompute validity ancillae at end of diffusion using the existing LIFO/@ql.compile inverse pattern

### Child Count Mechanism
- Classical enumeration: iterate over all possible d(x) values (1..d_max) and emit conditional rotation blocks for each
- No quantum popcount register needed — pattern matching on validity ancillae controls which block fires
- Emit rotation per bit pattern (e.g., for d=2 with d_max=3: patterns 110, 101, 011 each get their own controlled rotation)
- No OR ancilla — emit rotation conditioned directly on each matching pattern
- Skip diffusion entirely when d(x) = 0 (all children rejected — node is effectively a leaf)
- Support up to ternary branching (d_max = 3) for test cases within 17-qubit budget

### Uniform/Variable Mode
- Variable branching replaces uniform branching entirely — uniform becomes a special case where d(x) = d_max
- Auto-detect fast-path: when no predicate is provided (or predicate never rejects children), use the existing precomputed uniform angles directly — zero overhead regression
- All existing Phase 97-99 tests must pass unchanged — backward compatible
- Trees without predicates behave identically to current uniform branching

### Angle Dispatch Strategy
- Conditional blocks per d value: for each possible d (1..d_max), emit a rotation block conditioned on "exactly d validity ancillae are |1>"
- Per-d cascade blocks compiled separately (cached via @ql.compile with d-value as cache key)
- S_0 reflection stays fixed on all branch register qubits + parent height qubit (state preparation ensures zero amplitude on invalid children, so full-space S_0 is equivalent)
- All angles for d=1..d_max precomputed at QWalkTree construction time (consistent with existing _setup_diffusion() pattern)
- When d(x) = d_max (all children valid), still go through conditional block machinery (no special-case bypass within variable branching path)

### Claude's Discretion
- Per-d cascade vs single adaptive cascade implementation choice
- Exact gate decomposition for multi-controlled rotations conditioned on validity patterns
- Ancilla allocation and cleanup ordering details
- Test tree structures (within ternary/17-qubit constraints)

</decisions>

<specifics>
## Specific Ideas

- Binary SAT tree is the primary use case — variable branching prunes invalid assignments
- Ternary (d_max=3) should be supported for generality but binary is the focus
- The fast-path auto-detection should be invisible to the user — no flags, no mode switches
- Pattern matching for d_max=3 is manageable: 1 pattern for d=3 (111), 3 patterns for d=2 (110, 101, 011), 3 patterns for d=1 (100, 010, 001)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `QWalkTree` class (`walk.py`): Tree encoding with height registers, branch registers, predicate interface
- `_plan_cascade_ops(d, w)`: Precomputes cascade operations for equal superposition — reusable per d value
- `_emit_cascade_h_controlled()`: Height-controlled gate emission with V-gate decomposition
- `_setup_diffusion()`: Angle precomputation pattern — extend for d=1..d_max table
- `diffusion.py`: `_collect_qubits()` and `_make_qbool_wrapper()` utilities

### Established Patterns
- One-hot height register for depth control — unchanged
- Height-controlled dispatch (gates only fire when h[depth]=|1>) — unchanged
- V-gate decomposition for doubly-controlled gates — reuse for validity-conditioned rotations
- @ql.compile with key parameter for caching — use d value as cache key for per-d blocks

### Integration Points
- `local_diffusion(depth)` is the primary modification target — add predicate evaluation and conditional angle dispatch
- `R_A()` and `R_B()` call `local_diffusion()` — no changes needed at operator level
- `walk_step()` composition unchanged — variable branching is encapsulated within diffusion

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 100-variable-branching*
*Context gathered: 2026-03-02*
