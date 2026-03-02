# Phase 99: Walk Operators - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Compose local diffusion operators (from Phase 98) into R_A (even-depth reflections) and R_B (odd-depth + root reflections), form the walk step U = R_B * R_A as a compiled cacheable operation, and verify qubit disjointness between R_A and R_B. Variable branching is Phase 100; detection/demo is Phase 101.

</domain>

<decisions>
## Implementation Decisions

### Parity control scheme
- Explicit depth loop: R_A loops over even depths (0,2,4...) calling local_diffusion(d), R_B loops over odd depths (1,3,5...) calling local_diffusion(d)
- Root reflection folded into R_B's loop (root is at max_depth; if max_depth is even, R_B handles root as a special case at the end of its loop)
- Follow Montanaro convention: R_A = even-depth, R_B = odd-depth + root, regardless of max_depth parity
- R_A() and R_B() are public methods on QWalkTree, walk_step() composes them

### Compile wrapping strategy
- Only the composed walk step U = R_B * R_A gets @ql.compile wrapping; R_A/R_B stay as raw gate sequences
- Cache key: total_qubits (matches existing cascade compilation pattern)
- Controlled variant accessed via standard `with qbool:` pattern (no separate controlled_walk_step method)
- Lazy compilation: compiled on first walk_step() call, not at construction

### Disjointness validation
- Static analysis: compute qubit sets from depth assignments, compare for zero overlap (no circuit execution needed)
- Validated at QWalkTree construction (fail fast with clear error)
- Public method tree.verify_disjointness() returns dict: {'R_A_qubits': set, 'R_B_qubits': set, 'overlap': set, 'disjoint': bool}
- Also called internally at construction time

### Walk step API surface
- tree.walk_step() method on QWalkTree (not a standalone ql.walk_step function)
- Returns None, just emits gates (consistent with local_diffusion())
- Not exported to top-level ql namespace; QWalkTree is already exported
- Primary test target: binary tree depth=2 (5 qubits, tests even/odd parity with depths 0,1,2)

### Claude's Discretion
- Internal gate ordering within R_A/R_B depth loops
- Exact compilation boundary (which internal helper to wrap with ql_compile)
- Error message wording for disjointness failures
- Additional test tree sizes beyond the primary depth=2 binary tree

</decisions>

<specifics>
## Specific Ideas

- Montanaro 2015 Section 2 is the reference for R_A/R_B parity convention
- Walk step should "just work" inside `with control_qubit:` for Phase 101's power-method detection
- Reuse existing `_height_qubit(depth)` for parity-based depth selection

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `QWalkTree.local_diffusion(depth)`: Height-controlled diffusion at any depth (Phase 98)
- `QWalkTree._height_qubit(depth)`: Maps depth to physical qubit index
- `_collect_qubits()` in `diffusion.py`: Extracts qubit indices from registers
- `@ql.compile` with `key=lambda r: r.width` pattern for cache keying
- `_cascade_compiled` dict on QWalkTree: precedent for compiled sub-operations

### Established Patterns
- Height-controlled dispatch: all gates in local_diffusion are controlled on h[depth]
- V-gate decomposition for doubly-controlled gates (avoids nested `with` blocks)
- Lazy compilation pattern (ql_compile called inside methods, not at init)
- `_make_qbool_wrapper()` for wrapping physical qubits as control qbools

### Integration Points
- `walk.py`: R_A, R_B, walk_step, verify_disjointness all go in existing walk module
- `__init__.py`: QWalkTree already exported; no new top-level exports needed
- Phase 101: Detection loop will call tree.walk_step() inside `with control:` context

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 99-walk-operators*
*Context gathered: 2026-03-02*
