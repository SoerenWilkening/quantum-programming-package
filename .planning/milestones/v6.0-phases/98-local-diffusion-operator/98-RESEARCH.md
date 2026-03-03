# Phase 98: Local Diffusion Operator - Research

**Researched:** 2026-03-02
**Domain:** Quantum walk local diffusion operator (Montanaro 2015 backtracking)
**Confidence:** HIGH

## Summary

Phase 98 implements the local diffusion operator D_x for quantum backtracking walk trees. The operator D_x is a reflection about the state |psi_x> that mixes a parent node with its children in superposition. For uniform branching degree d, the parent/child amplitudes are each 1/sqrt(d+1). The root node uses a different formula with an additional depth-dependent weighting factor sqrt(n) on child amplitudes.

The implementation follows the locked decision of Ry rotation approach with a controlled-Ry cascade. The key angle is phi = 2*arctan(sqrt(d)), which produces exactly the 1/sqrt(d+1) amplitude split. The root uses phi_root = 2*arctan(sqrt(n*d)). D_x is implemented as the reflection pattern U_dagger * S_0 * U, reusing the existing Grover S_0 reflection from `diffusion.py`. The controlled-Ry cascade for d-way equal child superposition uses angles theta_k = 2*arctan(sqrt(1/(d-1-k))) for k = 0..d-2.

**Primary recommendation:** Implement in walk.py as `QWalkTree.local_diffusion(depth=k)` with eager angle precomputation in `_setup_diffusion()`, height-controlled dispatch via qbool wrapping individual height register qubits, and the S_0 reflection sandwich pattern U_dag-S_0-U for the reflection.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Ry rotation approach: use Ry(phi) where phi = 2*arctan(sqrt(d)) to split parent/children amplitude
- Controlled-Ry cascade for exact child amplitude distribution (supports arbitrary d, not just power-of-2)
- D_x implemented as reflection: U_dagger(map |psi_x> to |0>), then S_0 reflection, then U
- Reuse existing Grover S_0 reflection from `diffusion.py` (`ql.diffusion()` X-MCZ-X pattern) for the reflection step
- Support all uniform branching degrees from the start (d=2,3,4,5... not restricted to power-of-2)
- D_x acts on height register + branch register together: transitions h[k] -> h[k-1] and superimposes across branch register at that level
- Use @ql.compile controlled infrastructure for the controlled-Ry cascade (framework auto-derives controlled variants)
- Explicit depth parameter: `tree.local_diffusion(depth=k)` where h[k]=|1> means node at depth k
- D_x internally controlled on height qubit h[k] -- calling at wrong depth is a no-op (safe for walk operator loops)
- Root special case handled inside the same local_diffusion() method (not a separate function): detects depth=max_depth and applies Montanaro's exact root reflection formula
- Paper's exact root formula: D_root = 2|psi_root><psi_root| - I where |psi_root> is uniform over children only
- All-depths single pass: walk operators (Phase 99) call local_diffusion(depth=k) for each k in a loop; h[k] control makes irrelevant calls no-ops
- Explicit skip at depth 0 (leaf nodes): return immediately, no gates emitted
- Branch register mapping: D_x(depth=k) operates on `branch_registers[max_depth - k]`
- Per-level branching supported: branching[i] determines angles for that tree level
- All diffusion rotation angles precomputed eagerly at QWalkTree construction time
- Per-depth angle arrays stored privately on QWalkTree (one set of angles per depth level)
- Computation happens in `_setup_diffusion()` private helper called from `__init__`
- Method on QWalkTree: `tree.local_diffusion(depth=k)` -- not a standalone function
- Private angle storage with debug accessor: `tree.diffusion_info(depth)` returns angles and formula for inspection
- No top-level ql namespace export -- method-only access via tree instance
- Runtime depth validation: raises ValueError for out-of-bounds depth with clear error message

### Claude's Discretion
- Exact controlled-Ry cascade decomposition (how to split d-way amplitude with Ry chain)
- Internal angle storage data structure (dict vs list of tuples)
- `_setup_diffusion()` implementation details
- `diffusion_info()` return format
- How S_0 reflection from diffusion.py is invoked within D_x circuit
- Gate ordering within the reflection pattern
- Error message wording

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DIFF-01 | D_x local diffusion operator for uniform branching with correct amplitude angle phi = 2*arctan(sqrt(d)) | Verified: phi = 2*arctan(sqrt(d)) produces parent and per-child amplitudes of exactly 1/sqrt(d+1). Controlled-Ry cascade angles theta_k = 2*arctan(sqrt(1/(d-1-k))) produce equal d-way superposition. |
| DIFF-02 | Root node diffusion with separate phi_root formula (different amplitude weighting per Montanaro section 2) | Verified: phi_root = 2*arctan(sqrt(n*d)) where n=max_depth, d=root branching. Root amplitude = 1/sqrt(1+n*d), per-child = sqrt(n)/sqrt(1+n*d). Root has children only (no parent edge). |
| DIFF-03 | Statevector tests verifying |psi_x> amplitudes match 1/sqrt(d(x)+1) tolerance | Existing `_simulate_statevector()` pattern from test_walk_tree.py, Qiskit AerSimulator statevector method with max_parallel_threads=4. Tests verify D_x squared = I (reflection property) and amplitude matching. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (ql) | Current | All circuit operations, gate emission, compile decorator | Project's own framework |
| quantum_language._gates | Current | emit_ry, emit_x, emit_h, emit_z, emit_mcz primitives | Low-level gate API |
| quantum_language.diffusion | Current | S_0 reflection (X-MCZ-X pattern) for Grover diffusion | Reused for D_x reflection step |
| quantum_language.compile | Current | @ql.compile for controlled variant auto-derivation | Height-controlled dispatch |
| quantum_language.walk | Current | QWalkTree, TreeNode classes from Phase 97 | Extension target |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| math | stdlib | arctan, sqrt, ceil, log2 for angle precomputation | Angle computation in _setup_diffusion() |
| qiskit-aer | Installed | AerSimulator for statevector verification in tests | Test verification only |
| qiskit.qasm3 | Installed | QASM3 parsing for Qiskit simulation | Test pipeline |
| numpy | Installed | Array operations for statevector comparison in tests | Test assertions |

### Alternatives Considered
None -- all decisions locked in CONTEXT.md. Stack is the project's existing framework.

## Architecture Patterns

### Module Structure
```
src/quantum_language/
  walk.py              # QWalkTree class -- add _setup_diffusion(), local_diffusion(), diffusion_info()
  diffusion.py         # Existing Grover S_0 -- reused, not modified
  _gates.pyx           # emit_ry, emit_x, etc. -- used as-is
  compile.py           # @ql.compile -- used as-is for controlled variants

tests/python/
  test_walk_diffusion.py  # New: DIFF-01, DIFF-02, DIFF-03 tests
```

### Pattern 1: Height-Controlled Dispatch via qbool Wrapper
**What:** Create a qbool backed by a specific height register qubit to use as a controlled context for height-based gate dispatch.
**When to use:** Every time local_diffusion(depth=k) emits gates that should only apply when h[k]=|1>.
**Example:**
```python
# Access physical qubit index for height bit k
# Height register stores qubits right-aligned: bit k is at qubits[64 - (max_depth+1) + k]
height_qubit_idx = self.height_register.qubits[64 - (self.max_depth + 1) + depth]

# Create qbool wrapper pointing to existing height qubit (no allocation)
from .qbool import qbool
h_control = qbool(create_new=False, bit_list=[height_qubit_idx])

# All gates inside this block are controlled on h[depth]=|1>
with h_control:
    # ... emit Ry rotations, S_0 reflection, etc.
```

**Critical detail:** The qbool wrapper must use `create_new=False` with a `bit_list` containing the existing height qubit. This does NOT allocate a new qubit -- it creates a view onto the existing one. The `with` context manager activates the controlled gate context.

### Pattern 2: D_x Reflection via U-S0-U_dagger Sandwich
**What:** Implement D_x = U * S_0 * U_dagger where U maps |psi_x> to |0...0>.
**When to use:** For every non-root, non-leaf diffusion operation.
**Circuit structure:**
```
D_x(depth=k, controlled on h[k]):
  1. U_dagger: Undo the state preparation (inverse of Ry cascade + height transition)
  2. S_0: Grover reflection on |0...0> (X-all, MCZ, X-all) via ql.diffusion()
  3. U: Re-apply state preparation (Ry cascade + height transition)
```

**Key insight:** U is the unitary that prepares |psi_x> from |0>, so U_dagger * |psi_x> = |0>. Then S_0 flips phase on |0>, and U rotates back. This gives the reflection 2|psi_x><psi_x| - I (up to global phase from S_0 convention).

### Pattern 3: Controlled-Ry Cascade for d-way Equal Superposition
**What:** Create equal superposition over d basis states using a cascade of Ry rotations.
**When to use:** Within the U (state preparation) step of D_x, to distribute amplitude equally across d children in the branch register.
**Algorithm:**
```python
# For d children, cascade on ceil(log2(d)) qubits of branch register
# Step k (k=0 to d-2): Apply Ry(theta_k) to qubit handling the k-th split
# theta_k = 2 * arctan(sqrt(1/(d-1-k)))
# Each step peels off exactly 1/d of the remaining amplitude

# Equivalently: sin^2(theta_k / 2) = 1/(d-k)
# This means each rotation extracts one child's share from the remaining amplitude

# For d=2: one Ry rotation, theta = pi/2 (Hadamard equivalent)
# For d=3: two rotations on 2 qubits
# For d=4: two Ry rotations (balanced binary split)
# For d=5+: cascade on ceil(log2(d)) qubits with conditional splits
```

**Important:** For d > 2, the cascade requires controlled rotations. Qubit k+1's rotation must be controlled on qubit k's state to correctly partition the remaining amplitude. Use `with qbool:` context on each cascade qubit.

### Pattern 4: Eager Angle Precomputation in __init__
**What:** Compute all diffusion angles at QWalkTree construction time.
**When to use:** In `_setup_diffusion()` called from `__init__`.
**Example:**
```python
def _setup_diffusion(self):
    """Precompute diffusion angles for all depth levels."""
    import math
    self._diffusion_angles = []  # List indexed by level_idx (0..max_depth-1)

    for level_idx in range(self.max_depth):
        d = self.branching[level_idx]
        depth = self.max_depth - level_idx  # depth in tree (root=max_depth)

        # Parent-children split angle
        phi = 2 * math.atan(math.sqrt(d))

        # Child cascade angles (for d-way equal superposition)
        cascade_angles = []
        for k in range(d - 1):
            theta_k = 2 * math.atan(math.sqrt(1.0 / (d - 1 - k)))
            cascade_angles.append(theta_k)

        self._diffusion_angles.append({
            'phi': phi,
            'cascade': cascade_angles,
            'd': d,
            'depth': depth,
        })

    # Root angle (uses separate formula)
    d_root = self.branching[0]  # branching at level 0 (root's children)
    n = self.max_depth
    self._root_phi = 2 * math.atan(math.sqrt(n * d_root))
```

### Pattern 5: Root Diffusion (Special Case)
**What:** Root node has no parent edge, only children. |psi_root> = (1/sqrt(1+n*d)) * (|r> + sqrt(n) * sum_children |y>).
**When to use:** When local_diffusion(depth=max_depth) is called.
**Key difference from non-root:**
- Non-root |psi_x>: amplitude 1/sqrt(d+1) for parent AND each child
- Root |psi_r>: amplitude 1/sqrt(1+n*d) for root, sqrt(n)/sqrt(1+n*d) for each child
- phi_root = 2*arctan(sqrt(n*d)) where n=max_depth

The root diffusion operates only on the branch register at the root level (branch_registers[0]) plus the height qubit h[max_depth]. The root has no parent transition to a higher height qubit.

### Anti-Patterns to Avoid
- **Allocating new qubits for height control:** Never allocate fresh qubits for the controlled context. Always wrap existing height register qubits via `qbool(create_new=False, bit_list=...)`.
- **Hardcoding d=2 only:** The controlled-Ry cascade must support arbitrary d from the start. The cascade generalizes naturally.
- **Separate root diffusion function:** Per CONTEXT, root handling is inside `local_diffusion()`, not a separate method.
- **Applying diffusion to leaf nodes (depth=0):** Leaf nodes have no children. `local_diffusion(depth=0)` must return immediately with no gates.
- **Forgetting branch register mapping inversion:** Depth k uses `branch_registers[max_depth - k]`, NOT `branch_registers[k]`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| S_0 reflection | Custom X-MCZ-X pattern | `ql.diffusion(*registers)` from diffusion.py | Already handles qubit collection, edge cases, and is @ql.compile-cached |
| Controlled gate variants | Manual CRy emission | `with qbool:` context + standard emit_ry | emit_ry auto-detects controlled context and emits CRy |
| Qubit index extraction | Manual qubits array slicing | `_collect_qubits()` from diffusion.py | Handles qint, qbool, qarray flattening correctly |
| Inverse gate sequence | Manual reverse-angle computation | @ql.compile adjoint | Auto-derives U_dagger from U |

**Key insight:** The existing infrastructure (emit_ry with auto-CRy, `with qbool:` for control, `ql.diffusion()` for S_0) does most of the heavy lifting. The new code mainly orchestrates the correct sequence and angles.

## Common Pitfalls

### Pitfall 1: Qubit Indexing Off-by-One in Height Register
**What goes wrong:** Accessing the wrong physical qubit for height bit k, causing controlled gates to be controlled on the wrong depth level.
**Why it happens:** The height register uses right-aligned storage. Bit k is at `qubits[64 - (max_depth+1) + k]`, NOT `qubits[k]`.
**How to avoid:** Use a helper method like `_height_qubit(k)` that returns the correct physical index. Add assertions in tests that verify the physical qubit mapping.
**Warning signs:** Diffusion applies at the wrong tree level; statevector shows amplitude at unexpected basis states.

### Pitfall 2: Branch Register Mapping Inversion
**What goes wrong:** Using `branch_registers[k]` instead of `branch_registers[max_depth - k]` for depth k, applying the diffusion to the wrong branch register.
**Why it happens:** The height register encodes root at h[max_depth] (top), but branch registers are ordered from root level (index 0) to leaves.
**How to avoid:** The mapping is `level_idx = max_depth - depth`, then `branch_registers[level_idx]`. Use a helper or document clearly.
**Warning signs:** Diffusion modifies the wrong register's qubits.

### Pitfall 3: qbool Wrapper Allocating New Qubits
**What goes wrong:** Creating `qbool(True)` instead of `qbool(create_new=False, bit_list=...)` allocates a NEW qubit instead of wrapping an existing one.
**Why it happens:** Default qbool constructor allocates fresh qubits.
**How to avoid:** Always pass `create_new=False` and `bit_list` when wrapping height register qubits.
**Warning signs:** Total qubit count increases unexpectedly; controlled gates control on wrong qubit.

### Pitfall 4: Controlled-Ry Cascade Qubit Ordering
**What goes wrong:** The cascade rotations apply to the wrong qubits within the branch register, producing non-uniform amplitudes.
**Why it happens:** Branch register qubits are right-aligned (LSB at rightmost position). For d-way split, the cascade must operate on the correct subset of qubits.
**How to avoid:** For d <= 2^w (where w is the branch register width), the cascade operates on the w qubits of the branch register. Access them via `qubits[64 - w + i]` for bit i.
**Warning signs:** Statevector amplitudes are not equal across children; some children have zero amplitude.

### Pitfall 5: Root Formula Confusion
**What goes wrong:** Using phi = 2*arctan(sqrt(d)) for root instead of phi_root = 2*arctan(sqrt(n*d)).
**Why it happens:** Root formula includes the depth factor n that non-root nodes don't have.
**How to avoid:** Explicitly check `if depth == self.max_depth` and use the precomputed `_root_phi`.
**Warning signs:** Root statevector amplitudes don't match Montanaro's formula; walk operator convergence fails.

### Pitfall 6: S_0 Reflection Qubit Scope
**What goes wrong:** Passing too many or too few qubits to `ql.diffusion()` for the S_0 reflection step.
**Why it happens:** S_0 must reflect on all qubits involved in the local state |psi_x>, which includes the branch register at this level AND the height transition qubit(s).
**How to avoid:** Carefully identify which qubits define the local Hilbert space for D_x. For a non-root node at depth k, this is the branch register at level (max_depth - k) and possibly the height qubits h[k] and h[k-1].
**Warning signs:** D_x is not a proper reflection (D_x^2 != I on the relevant subspace).

### Pitfall 7: Qiskit Statevector Qubit Ordering
**What goes wrong:** Test assertions fail because of Qiskit's little-endian qubit ordering vs the project's qubit indexing.
**Why it happens:** In Qiskit's statevector, qubit 0 is the LSB of the state index. Physical qubit k being |1> means bit k of the index is 1.
**How to avoid:** Use `1 << physical_qubit_index` to compute the basis state index for a single qubit being |1>. Combine with OR for multiple qubits.
**Warning signs:** Amplitudes appear at wrong indices; tests pass for d=2 but fail for d=3.

## Code Examples

### Height Qubit Access Helper
```python
def _height_qubit(self, depth):
    """Get physical qubit index for height register bit at given depth.

    In one-hot encoding, h[depth] = |1> means the node is at depth `depth`.
    Root is at depth=max_depth, leaves at depth=0.

    Returns the physical qubit index for h[depth].
    """
    # Height register is qint with width = max_depth + 1
    # Right-aligned: bit k is at qubits[64 - width + k]
    width = self.max_depth + 1
    return int(self.height_register.qubits[64 - width + depth])
```

### Controlled-Ry Cascade for d-way Superposition
```python
def _ry_cascade(self, branch_reg, d, cascade_angles):
    """Apply Ry cascade to create equal superposition over d states.

    Uses sequential conditional rotations:
    theta_k = 2*arctan(sqrt(1/(d-1-k))) for k = 0..d-2

    For d=2: single Ry(pi/2) = Hadamard-equivalent on first qubit
    For d=3: Ry(theta_0) on q0, then controlled-Ry(pi/2) on q1 conditioned on q0=|1>
    For d=4: Ry(pi/2) on q1, then Ry(pi/2) on q0 for each half (balanced split)
    """
    from ._gates import emit_ry
    from .qbool import qbool

    w = branch_reg.width

    if d <= 1:
        return  # No children or single child -- no rotation needed

    if d == 2:
        # Simple case: Ry(pi/2) on the first qubit = Hadamard equivalent
        # This creates |0> -> (|0> + |1>)/sqrt(2)
        qubit = int(branch_reg.qubits[64 - w])  # LSB
        emit_ry(qubit, cascade_angles[0])
        return

    # General d > 2: cascade of conditional rotations
    # Step 0: Ry(theta_0) on qubit 0 (unconditional)
    # Step k>0: Ry(theta_k) on qubit handling state k, controlled on previous splits
    # ... (exact decomposition depends on branch register bit encoding)
```

### Angle Precomputation
```python
def _setup_diffusion(self):
    """Precompute all diffusion rotation angles."""
    import math

    self._diffusion_data = []

    for level_idx in range(self.max_depth):
        d = self.branching[level_idx]
        depth = self.max_depth - level_idx

        # Parent-children split: phi = 2*arctan(sqrt(d))
        phi = 2.0 * math.atan(math.sqrt(d))

        # Child cascade angles: theta_k = 2*arctan(sqrt(1/(d-1-k)))
        cascade = []
        for k in range(max(0, d - 1)):
            remaining = d - 1 - k
            if remaining > 0:
                theta = 2.0 * math.atan(math.sqrt(1.0 / remaining))
            else:
                theta = 0.0
            cascade.append(theta)

        self._diffusion_data.append({
            'phi': phi,
            'cascade': cascade,
            'd': d,
            'depth': depth,
            'level_idx': level_idx,
        })

    # Root angle: phi_root = 2*arctan(sqrt(n*d_root))
    d_root = self.branching[0]  # root is at level_idx=0
    self._root_phi = 2.0 * math.atan(math.sqrt(self.max_depth * d_root))
```

### Statevector Test Pattern
```python
def test_diffusion_amplitude_d2(self):
    """D_x at depth=1 for d=2 tree produces 1/sqrt(3) amplitudes."""
    ql.circuit()
    tree = QWalkTree(max_depth=2, branching=2)

    # Move to depth 1 by applying X to h[1] and removing h[2]
    # (prepare a state at depth 1 for testing)
    # ... setup code ...

    tree.local_diffusion(depth=1)

    qasm_str = ql.to_openqasm()
    sv = _simulate_statevector(qasm_str)

    # Expected: parent (h[2]) amplitude = 1/sqrt(3)
    #           child 0 (h[0], branch=0) amplitude = 1/sqrt(3)
    #           child 1 (h[0], branch=1) amplitude = 1/sqrt(3)
    expected = 1.0 / math.sqrt(3)
    # ... verify statevector entries ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Explicit diffusion matrix construction | Ry-cascade + S_0 sandwich | Standard since Montanaro 2015 | Avoids exponential matrix, uses O(d) gates per D_x |
| Power-of-2 only branching | Arbitrary d via Ry cascade | Qrisp 2024 implementation | Supports d=3,5,7... without padding to power-of-2 |
| Separate root function | Unified method with depth check | Design decision (Phase 98 CONTEXT) | Cleaner API for walk operators |

## Mathematical Reference

### Non-Root Node Diffusion (DIFF-01)

For a non-root, non-leaf node x at depth k with branching degree d(x):

```
|psi_x> = (1/sqrt(d(x)+1)) * (|parent> + sum_{i=0}^{d(x)-1} |child_i>)
D_x = 2|psi_x><psi_x| - I  (on the local subspace)
```

Amplitude angle: phi = 2*arctan(sqrt(d(x)))
- cos(phi/2) = 1/sqrt(d(x)+1)  [parent amplitude]
- sin(phi/2) = sqrt(d(x))/sqrt(d(x)+1)  [total children amplitude]
- Per child: sin(phi/2)/sqrt(d(x)) = 1/sqrt(d(x)+1)

**Verified numerically** for d = 2, 3, 4, 5. All produce exact 1/sqrt(d+1) amplitudes.

### Root Node Diffusion (DIFF-02)

For root node r with branching degree d_r and tree max_depth n:

```
|psi_r> = (1/sqrt(1 + n*d_r)) * (|r> + sqrt(n) * sum_{i=0}^{d_r-1} |child_i>)
D_r = 2|psi_r><psi_r| - I
```

Root angle: phi_root = 2*arctan(sqrt(n*d_r))
- cos(phi_root/2) = 1/sqrt(1 + n*d_r)  [root amplitude]
- sin(phi_root/2) = sqrt(n*d_r)/sqrt(1 + n*d_r)  [total children amplitude]
- Per child: sqrt(n)/sqrt(1 + n*d_r)

**Verified numerically** for n=2,3,4 and d=2,3.

### Controlled-Ry Cascade for d-way Equal Superposition

To create (1/sqrt(d)) * sum_{i=0}^{d-1} |i> from |0...0>:

For k = 0, 1, ..., d-2:
```
theta_k = 2*arctan(sqrt(1/(d-1-k)))
Equivalently: sin^2(theta_k/2) = 1/(d-k)
```

Each step k peels off exactly 1/d of the total amplitude:
- Step 0: extracts amplitude 1/sqrt(d) for child 0, leaving sqrt((d-1)/d)
- Step 1: extracts amplitude 1/sqrt(d) for child 1, leaving sqrt((d-2)/d)
- ...
- Step d-2: splits remaining sqrt(2/d) into two equal parts of 1/sqrt(d)

**Verified numerically** for d = 3 and d = 5.

## Open Questions

1. **Exact circuit decomposition for d-way cascade on multi-qubit branch registers**
   - What we know: The cascade produces d equal amplitudes via sequential conditional rotations. The angles are verified.
   - What's unclear: For d not a power of 2 (e.g., d=3 on 2 qubits), the cascade must avoid creating amplitude on states >= d. This requires careful controlled-Ry targeting.
   - Recommendation: For d <= 2 (single qubit register), trivial. For d = 2^w (power of 2), balanced Hadamard tree. For d < 2^w (non-power-of-2), use the conditional cascade with careful state labeling. The implementation can start with the general cascade and optimize power-of-2 cases later if needed.

2. **S_0 reflection scope within D_x**
   - What we know: ql.diffusion() applies the S_0 reflection on arbitrary registers. D_x must reflect on the local subspace only.
   - What's unclear: The exact set of qubits to pass to ql.diffusion() within D_x. Should it include the height qubit(s) and the branch register, or just the branch register?
   - Recommendation: The local state |psi_x> spans the parent height qubit h[k], child height qubit h[k-1], and the branch register at level (max_depth - k). The S_0 reflection should operate on the branch register only (since after U_dagger maps |psi_x> -> |0...0> on the branch register, the height qubits are already in a product state). Validate with statevector tests.

3. **D_x acting as identity on marked (accepted) vertices**
   - What we know: Montanaro defines D_x = I for accepted vertices. In our implementation, accepted nodes are handled by the predicate interface.
   - What's unclear: Whether Phase 98 needs to check the accept flag, or if this is deferred to Phase 99 (walk operators).
   - Recommendation: Phase 98 implements the bare diffusion operator D_x without predicate checking. The walk operators in Phase 99 will combine D_x with the predicate. This keeps Phase 98 focused.

## Sources

### Primary (HIGH confidence)
- Montanaro 2015, "Quantum walk speedup of backtracking algorithms" (arXiv:1509.02374) - Section 2 definitions of |psi_x>, |psi_r>, D_x, R_A, R_B
- Numerical verification of all angle formulas (run locally with Python math library)
- Existing project code: walk.py, diffusion.py, _gates.pyx, compile.py, test_walk_tree.py

### Secondary (MEDIUM confidence)
- Qrisp implementation (eclipse-qrisp/Qrisp on GitHub, backtracking_tree.py) - Practical circuit decomposition for psi_prep, c_iswap_reduced pattern, root_phase formula
- Seidel et al. 2024, "Quantum Backtracking in Qrisp Applied to Sudoku Problems" (arXiv:2402.10060) - phi = 2*arctan(sqrt(deg)), root_phi = 2*arctan(sqrt(N*deg))

### Tertiary (LOW confidence)
- Martiel & Remaud 2019, "Practical implementation of a quantum backtracking algorithm" (arXiv:1908.11291) - Referenced but PDF not accessible for detailed verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing project framework, all components verified in Phase 97
- Architecture: HIGH - Reflection pattern (U-S0-U_dagger) is textbook, angle formulas numerically verified
- Pitfalls: HIGH - Identified through code analysis of existing qubit indexing patterns and common quantum circuit errors
- Mathematical formulas: HIGH - All independently verified with numerical computation

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable mathematical foundation, no library version dependencies)
