# Phase 99: Walk Operators - Research

**Researched:** 2026-03-02
**Domain:** Quantum walk operator composition (Montanaro 2015 backtracking)
**Confidence:** HIGH

## Summary

Phase 99 composes the local diffusion operators (Phase 98) into walk operators R_A and R_B, then forms the walk step U = R_B * R_A. The core challenge is parity-controlled depth looping: R_A loops over even-depth nodes calling `local_diffusion(d)`, R_B loops over odd-depth nodes plus the root node. Since each `local_diffusion` call is already height-controlled (only activates when `h[depth] = |1>`), the parity loops can safely iterate over all relevant depths -- non-matching depths are no-ops.

The secondary deliverables are: (1) static qubit disjointness validation between R_A and R_B, confirmed by extracting the physical qubit sets each operator touches, and (2) `@ql.compile` wrapping of the composed walk step for caching and controlled variant derivation.

**Primary recommendation:** Implement R_A, R_B, walk_step, and verify_disjointness as methods on QWalkTree in `walk.py`, following the established pattern of `local_diffusion`. Wrap only the composed walk_step with `@ql.compile` (not individual R_A/R_B). Validate disjointness at construction time.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Explicit depth loop: R_A loops over even depths (0,2,4...) calling local_diffusion(d), R_B loops over odd depths (1,3,5...) calling local_diffusion(d)
- Root reflection folded into R_B's loop (root is at max_depth; if max_depth is even, R_B handles root as a special case at the end of its loop)
- Follow Montanaro convention: R_A = even-depth, R_B = odd-depth + root, regardless of max_depth parity
- R_A() and R_B() are public methods on QWalkTree, walk_step() composes them
- Only the composed walk step U = R_B * R_A gets @ql.compile wrapping; R_A/R_B stay as raw gate sequences
- Cache key: total_qubits (matches existing cascade compilation pattern)
- Controlled variant accessed via standard `with qbool:` pattern (no separate controlled_walk_step method)
- Lazy compilation: compiled on first walk_step() call, not at construction
- Static analysis: compute qubit sets from depth assignments, compare for zero overlap (no circuit execution needed)
- Validated at QWalkTree construction (fail fast with clear error)
- Public method tree.verify_disjointness() returns dict: {'R_A_qubits': set, 'R_B_qubits': set, 'overlap': set, 'disjoint': bool}
- Also called internally at construction time
- tree.walk_step() method on QWalkTree (not a standalone ql.walk_step function)
- Returns None, just emits gates (consistent with local_diffusion())
- Not exported to top-level ql namespace; QWalkTree is already exported
- Primary test target: binary tree depth=2 (5 qubits, tests even/odd parity with depths 0,1,2)

### Claude's Discretion
- Internal gate ordering within R_A/R_B depth loops
- Exact compilation boundary (which internal helper to wrap with ql_compile)
- Error message wording for disjointness failures
- Additional test tree sizes beyond the primary depth=2 binary tree

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WALK-01 | R_A operator applying local diffusions at even-depth nodes via height-parity control | R_A iterates even depths calling local_diffusion(); height-controlled dispatch already handles selectivity |
| WALK-02 | R_B operator applying local diffusions at odd-depth nodes (plus root reflection) via height-parity control | R_B iterates odd depths + handles root as special case after loop; root_phi already precomputed |
| WALK-03 | Walk step U = R_B * R_A composed as single operation | walk_step() calls R_A() then R_B() sequentially |
| WALK-04 | Walk step wrapped in @ql.compile for caching and controlled variant derivation | @ql.compile wrapper with key=lambda self: self.total_qubits; lazy compilation on first call |
| WALK-05 | Qubit disjointness test confirming R_A and R_B have zero qubit-index overlap | Static analysis of depth->qubit mappings; verified at construction |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language | project | Host framework (QWalkTree, gates, compile) | This IS the project |
| qiskit-aer | existing | Statevector simulation for test verification | Already used in Phase 98 tests |
| pytest | existing | Test framework | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | existing | Statevector analysis in tests | Amplitude comparison |
| math | stdlib | Angle computation | arctan, sqrt for expected values |

### Alternatives Considered
None -- all dependencies are already in use from Phase 97-98.

## Architecture Patterns

### Recommended Implementation Structure

All new code goes in existing files:

```
src/quantum_language/
  walk.py           # Add R_A(), R_B(), walk_step(), verify_disjointness() to QWalkTree
tests/python/
  test_walk_operators.py  # New test file for Phase 99
```

### Pattern 1: Parity-Controlled Depth Loop

**What:** R_A loops over even depths, R_B over odd depths. Each call to `local_diffusion(depth)` is already height-controlled -- it only activates when the node's height qubit matches.

**When to use:** Building R_A and R_B methods.

**Example:**
```python
def R_A(self):
    """Apply R_A: local diffusions at even-depth nodes."""
    for depth in range(0, self.max_depth + 1, 2):  # 0, 2, 4, ...
        self.local_diffusion(depth)

def R_B(self):
    """Apply R_B: local diffusions at odd-depth nodes + root."""
    for depth in range(1, self.max_depth + 1, 2):  # 1, 3, 5, ...
        self.local_diffusion(depth)
    # Root: always apply at max_depth if not already covered by odd loop
    if self.max_depth % 2 == 0:  # max_depth is even => not in odd loop
        self.local_diffusion(self.max_depth)
```

**Key insight:** The Montanaro convention assigns root to R_B regardless of parity. If `max_depth` is even, the root (at max_depth) is NOT in the odd-depth loop (1,3,5...) and must be added explicitly. If `max_depth` is odd, the root IS already in the odd-depth loop. The CONTEXT.md says "R_B handles root as a special case at the end of its loop" -- this means R_B always calls `local_diffusion(max_depth)` for root, but we must avoid double-application when max_depth is odd. The simplest approach: track which depths R_B covers and add root only if not already covered.

### Pattern 2: Lazy @ql.compile Wrapping

**What:** Walk step is compiled on first invocation, cached by total_qubits.

**When to use:** walk_step() method.

**Example:**
```python
def walk_step(self):
    """Apply walk step U = R_B * R_A."""
    if not hasattr(self, '_walk_compiled'):
        from .compile import compile as ql_compile

        def _walk_body(tree):
            tree.R_A()
            tree.R_B()

        self._walk_compiled = ql_compile(key=lambda t: t.total_qubits)(_walk_body)

    self._walk_compiled(self)
```

**Important:** The `@ql.compile` wrapper captures the gate sequence on first call and replays it on subsequent calls with the same key. The controlled variant is automatically available via `with qbool:` context when calling `walk_step()` inside a control block.

### Pattern 3: Static Disjointness Analysis

**What:** Compute physical qubit sets for R_A and R_B without running a circuit.

**When to use:** verify_disjointness() and construction-time validation.

**Example:**
```python
def verify_disjointness(self):
    """Return disjointness analysis for R_A and R_B."""
    r_a_qubits = set()
    r_b_qubits = set()

    for depth in range(0, self.max_depth + 1, 2):  # R_A depths
        r_a_qubits.update(self._qubits_for_depth(depth))

    for depth in range(1, self.max_depth + 1, 2):  # R_B depths
        r_b_qubits.update(self._qubits_for_depth(depth))
    # Root always in R_B
    if self.max_depth % 2 == 0:
        r_b_qubits.update(self._qubits_for_depth(self.max_depth))

    overlap = r_a_qubits & r_b_qubits
    return {
        'R_A_qubits': r_a_qubits,
        'R_B_qubits': r_b_qubits,
        'overlap': overlap,
        'disjoint': len(overlap) == 0,
    }
```

**Critical detail:** Each `local_diffusion(depth)` touches:
1. Height qubit `h[depth]` (the control qubit)
2. Height qubit `h[depth-1]` (the child height qubit for Ry rotation)
3. Branch register at `level_idx = max_depth - depth`

For disjointness, the key question is whether any height qubit or branch register qubit is used by both R_A and R_B. Since depth d and depth d+1 share the child height qubit h[d], adjacent depths share a qubit. R_A has even depths and R_B has odd depths -- so depth 0 (R_A) shares h[0] with depth 1 (R_B's use of h[depth-1]=h[0]).

**Wait -- this means R_A and R_B are NOT qubit-disjoint at the physical qubit level.** Depth 0 (R_A, leaf) is a no-op. But depth 2 (R_A) uses h[2] and h[1], while depth 1 (R_B) uses h[1] and h[0]. They share h[1]. However, depth 2 and depth 1 operate on different subspaces because the height qubit control means only the qubit state `h[depth]=|1>` activates the gates. **The disjointness is at the operator level (the operations don't interfere because of the height control), not necessarily at the physical qubit level.**

**Revised understanding:** The REQUIREMENTS say "qubit disjointness test confirms R_A and R_B operate on zero overlapping qubit indices." This likely means the qubits CONTROLLED by R_A vs R_B are disjoint -- i.e., the height qubits that serve as control qubits for even vs odd depths don't overlap. The even depth control qubits are h[0], h[2], h[4],... and the odd depth control qubits are h[1], h[3], h[5],... These are indeed disjoint. The root is controlled on h[max_depth], which is either even or odd.

**Resolution:** The disjointness verification should check that the height qubit INDICES used as primary controls for R_A depths vs R_B depths have no overlap. The shared child qubits (h[depth-1]) and branch registers are accessed under different height controls, so they don't interfere. The structural correctness is that R_A and R_B are "product of reflections" -- each reflection is controlled on a distinct height qubit, and no height qubit appears in both sets.

### Anti-Patterns to Avoid
- **Nested `with qbool:` blocks:** The framework does not support quantum-quantum AND. All doubly-controlled operations must use V-gate decomposition (already handled in `_emit_cascade_h_controlled`).
- **Allocating new qubits in walk operators:** R_A, R_B, and walk_step must NOT allocate any new quantum registers. They only operate on the existing tree registers.
- **Double root application in R_B:** When max_depth is odd, the root depth is already in the odd loop. Must not apply local_diffusion(max_depth) twice.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Height-controlled diffusion | Custom gate sequences per depth | `self.local_diffusion(depth)` | Already handles all V-gate decomposition, cascade ops, S_0 reflection |
| Compile wrapping | Manual gate recording/replay | `@ql.compile(key=...)` | Handles inverse, controlled variant, caching |
| Qubit extraction | Manual qubit index arithmetic | `self._height_qubit(depth)`, `_collect_qubits()` | Correct one-hot indexing |

## Common Pitfalls

### Pitfall 1: Root double-application in R_B
**What goes wrong:** If max_depth is odd, calling local_diffusion for all odd depths (1,3,5,...,max_depth) already includes the root. Adding root separately would apply it twice.
**Why it happens:** The CONTEXT.md says root is folded into R_B as a special case. Easy to interpret as "always add root at the end."
**How to avoid:** Only add root explicitly when max_depth is even (root not already in odd loop).
**Warning signs:** Walk step test fails D_x^2=I property for root when max_depth is odd.

### Pitfall 2: Assuming physical qubit disjointness
**What goes wrong:** R_A at depth 2 uses h[1] as the Ry target qubit; R_B at depth 1 also uses h[1] as the Ry target qubit. Physical qubits overlap.
**Why it happens:** Confusing "operator disjointness" with "physical qubit disjointness."
**How to avoid:** The disjointness check should verify that the HEIGHT CONTROL qubits (the qubits that activate each reflection) are disjoint between R_A and R_B. Even-depth heights = {h[0], h[2], h[4],...}, odd-depth heights = {h[1], h[3], h[5],...}. Root height h[max_depth] goes with R_B.
**Warning signs:** verify_disjointness() incorrectly reports overlap when using full qubit sets.

### Pitfall 3: Compile key collision
**What goes wrong:** If two different tree configurations have the same total_qubits, the compiled walk step from one might be replayed for the other.
**Why it happens:** Using total_qubits as the compile key doesn't distinguish tree structure.
**How to avoid:** Acceptable for now -- in practice, users create one tree per circuit. The compile cache is per-instance via `self._walk_compiled`, so different QWalkTree instances get separate compiled functions. The key lambda just needs to be consistent for the same instance.

### Pitfall 4: Leaf depth in R_A
**What goes wrong:** Depth 0 (leaf) is always in the even set. local_diffusion(0) is a no-op. Including it is harmless but wastes a function call.
**Why it happens:** Mechanical even-depth iteration includes 0.
**How to avoid:** Can start R_A loop at depth 2 (skip leaf). Or include depth 0 for simplicity (it's a no-op). Either is fine.

## Code Examples

### R_A Implementation
```python
def R_A(self):
    """Apply R_A: reflections at even-depth nodes.

    R_A = product of D_x for all x at even depths (0, 2, 4, ...).
    Leaf (depth=0) is a no-op. Root is NOT included (belongs to R_B).
    """
    for depth in range(0, self.max_depth + 1, 2):
        if depth == self.max_depth:
            continue  # Root belongs to R_B
        self.local_diffusion(depth)
```

Wait -- the Montanaro convention is: R_A = even depths, R_B = odd depths + root. So if max_depth is even, the root depth (even) is NOT in R_A -- it's explicitly moved to R_B. If max_depth is odd, root is already an odd depth and naturally in R_B.

**Corrected R_A:** Skip root even if max_depth is even.

```python
def R_A(self):
    """Apply R_A: reflections at even-depth nodes (excluding root)."""
    for depth in range(0, self.max_depth + 1, 2):
        if depth == self.max_depth:
            continue  # Root always belongs to R_B per Montanaro
        self.local_diffusion(depth)

def R_B(self):
    """Apply R_B: reflections at odd-depth nodes plus root."""
    for depth in range(1, self.max_depth + 1, 2):
        self.local_diffusion(depth)
    # Root always in R_B, add if not already covered (even max_depth)
    if self.max_depth % 2 == 0:
        self.local_diffusion(self.max_depth)
```

### verify_disjointness Implementation
```python
def verify_disjointness(self):
    """Verify R_A and R_B height controls are disjoint."""
    r_a_depths = set()
    r_b_depths = set()

    for depth in range(0, self.max_depth + 1, 2):
        if depth != self.max_depth:
            r_a_depths.add(depth)

    for depth in range(1, self.max_depth + 1, 2):
        r_b_depths.add(depth)
    if self.max_depth % 2 == 0:
        r_b_depths.add(self.max_depth)

    r_a_qubits = {self._height_qubit(d) for d in r_a_depths}
    r_b_qubits = {self._height_qubit(d) for d in r_b_depths}

    overlap = r_a_qubits & r_b_qubits
    return {
        'R_A_qubits': r_a_qubits,
        'R_B_qubits': r_b_qubits,
        'overlap': overlap,
        'disjoint': len(overlap) == 0,
    }
```

### walk_step with Lazy @ql.compile
```python
def walk_step(self):
    """Apply walk step U = R_B * R_A."""
    if self._walk_compiled is None:
        from .compile import compile as ql_compile

        def _walk_body(tree):
            tree.R_A()
            tree.R_B()

        self._walk_compiled = ql_compile(key=lambda t: t.total_qubits)(_walk_body)

    self._walk_compiled(self)
```

## Open Questions

1. **Compile key semantics with `self` argument**
   - What we know: `@ql.compile(key=...)` typically wraps functions that take qint/qarray arguments. The `key` lambda receives the same arguments as the function.
   - What's unclear: Passing `self` (a QWalkTree instance) to a compiled function may not work the same way as passing qint. The compile infrastructure may need the function to take quantum register arguments directly.
   - Recommendation: If passing `self` doesn't work, wrap the body to take the relevant registers as arguments and use `total_qubits` as an integer key. Test the compile wrapping first; adjust if needed.

2. **Disjointness definition precision**
   - What we know: WALK-05 says "zero overlapping qubit indices." R_A and R_B physically touch overlapping qubits (shared h[depth-1] child height qubits).
   - What's unclear: Whether the requirement means physical qubit disjointness or control-qubit disjointness.
   - Recommendation: Implement as control-qubit disjointness (height qubits used as primary controls). This is the mathematically meaningful notion -- the "product of reflections" structure requires each reflection to be controlled on a distinct qubit. Document this interpretation clearly.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/walk.py` -- QWalkTree, local_diffusion, _height_qubit, _make_qbool_wrapper, _emit_cascade_h_controlled
- `src/quantum_language/diffusion.py` -- _collect_qubits, @ql_compile pattern
- `src/quantum_language/compile.py` -- CompiledFunc, compile() decorator
- `tests/python/test_walk_diffusion.py` -- existing test patterns for statevector verification

### Secondary (MEDIUM confidence)
- Montanaro 2015 (arXiv:1509.02374) Section 2 -- R_A/R_B parity convention
- Phase 98 CONTEXT.md -- design decisions about height-controlled dispatch

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use from Phase 97-98
- Architecture: HIGH -- direct extension of established QWalkTree patterns
- Pitfalls: HIGH -- identified from code analysis of existing implementations

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (internal project, stable patterns)
