# Phase 97: Tree Encoding & Predicate Interface - Research

**Researched:** 2026-03-02
**Domain:** Quantum backtracking tree data structures (Montanaro 2015)
**Confidence:** HIGH

## Summary

Phase 97 implements the foundational data structures for quantum backtracking walks: a `QWalkTree` class with one-hot height register, per-level branch registers (as `qarray`), root state preparation, predicate validation, and simulation-time resource enforcement. This is a pure Python module (`walk.py`) built on top of existing `quantum_language` primitives (`qint`, `qbool`, `qarray`, `@ql.compile`, `emit_x`, circuit management). No new C code or Cython extensions are needed.

The encoding follows Montanaro 2015: each tree node is represented by a one-hot height register (`max_depth + 1` qubits, where root = `max_depth`, leaves = 0) plus a branch quantum array storing the path from root to the current node (one entry per depth level, each entry `ceil(log2(branching_degree))` qubits wide). Root state preparation sets the appropriate height qubit to |1> via an X gate and leaves all branch registers at |0>.

The predicate interface accepts a callable returning `(is_accept, is_reject)` as two `qbool` values. Mutual exclusion is validated at construction time by running the predicate on a test state and checking that both qbools cannot simultaneously be |1>. Predicate uncomputation leverages the existing `@ql.compile` inverse pattern or raw allocation below LIFO scope tracking.

**Primary recommendation:** Implement `QWalkTree` as a pure Python class in `src/quantum_language/walk.py`, using `qint`/`qbool`/`qarray` for register allocation, `emit_x` for root state preparation, and the existing `@ql.compile` inverse mechanism for predicate uncomputation. The 17-qubit limit is simulation-only (enforced when converting to QASM/simulating, not at construction).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All-in-one constructor: `QWalkTree(max_depth, branching, predicate=my_fn)`
- `max_depth` is number of levels (inclusive): depth=3 means 4 levels (0,1,2,3) matching Montanaro's notation
- `branching` accepts int (uniform, shorthand for `[d]*max_depth`) or list (per-level specification, length = max_depth)
- Eager qubit allocation at construction time
- Root state preparation happens automatically during construction (no separate `prepare_root()` call)
- Registers exposed as named attributes: `tree.height_register`, `tree.branch_registers[i]` for debugging/inspection
- Predicate is a constructor parameter (not a separate method call)
- Callable receives a `TreeNode` state object with `.depth`, `.branch_values` attributes
- Returns tuple of two qbools: `(is_accept, is_reject)`
- Mutual exclusion validation happens at construction time (fail fast)
- Supports both raw callables and @ql.compile-decorated functions; compiled predicates get auto-inverse for uncomputation
- 17-qubit limit is a simulation constraint, NOT a circuit construction constraint
- Constructor allows any size tree to be created regardless of qubit count
- Simulation enforcement only: error raised when user tries to simulate a tree exceeding the qubit budget
- `max_qubits` is a configurable parameter (default 17) for future hardware targets
- No separate `num_qubits` property or static estimator -- users inspect register attributes if needed
- Lives inside `quantum_lib/walk.py` -- single file for now (can refactor to sub-package in later phases)
- Main class: `QWalkTree`
- Node state object: `TreeNode`

### Claude's Discretion
- Internal register allocation order and qubit mapping
- TreeNode implementation details (what additional attributes beyond depth/branch_values)
- Predicate validation strategy (how to test mutual exclusion at construction)
- Error message wording for validation failures
- Root state preparation circuit implementation

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TREE-01 | QuantumBacktrackingTree class with one-hot height register (max_depth+1 qubits) and QuantumArray branch registers (one entry per depth level) | One-hot encoding per Montanaro 2015 (root=max_depth, leaf=0). Branch registers are `qarray` of `qint` elements, one per depth level. Width per entry = `ceil(log2(branching_degree_at_level))`. Register allocation uses existing `qint`/`qarray` constructors with eager allocation at construction time. |
| TREE-02 | Resource estimator that computes exact qubit count for given tree parameters and fails fast before circuit construction | Per CONTEXT.md: no static estimator or separate `num_qubits` property. The 17-qubit limit is simulation-only. Qubit count = `(max_depth + 1) + sum(ceil(log2(branching[i])) for i in range(max_depth))`. Enforcement happens at simulation time (in a `simulate()` method or when exporting to QASM), not construction. |
| TREE-03 | Node initialization (root state preparation with correct height qubit) | Root = height qubit `h[max_depth]` set to |1> (via `emit_x`), all branch registers at |0> (default). Happens automatically in constructor per CONTEXT.md. Verified via statevector showing only the root-height qubit is |1>. |
| PRED-01 | Accept/reject predicate interface -- user provides callable returning two qbools (is_accept, is_reject) for a given tree state | Predicate receives a `TreeNode` state object with `.depth` (qint from height register) and `.branch_values` (list of qint from branch registers). Returns `(is_accept, is_reject)` tuple of qbool. Supports both raw callables and `@ql.compile`-decorated functions. |
| PRED-02 | Predicate mutual exclusion validation (accept and reject cannot both be true) | Construction-time validation: invoke predicate on the initialized root state, check that `is_accept & is_reject` is classically False (or circuit-level: AND the two qbools and verify the result is |0>). Fail fast with clear error message. |
| PRED-03 | Predicate uncomputation managed below LIFO scope tracking (raw allocation or @ql.compile inverse pattern) | Predicate qbools allocated outside LIFO scope stack (scope depth 0 or via `@ql.compile`). For compiled predicates, `pred.inverse(node)` uncomputes. For raw callables, the predicate's temporary qbools must be manually managed or allocated with `create_new=True` at scope 0 to avoid interference with the LIFO cascade. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (this project) | 0.1.0 | All quantum primitives: qint, qbool, qarray, circuit, @ql.compile, emit_x, emit_ry, to_openqasm | The project's own framework -- all new code builds on existing primitives |
| Python | 3.11+ | Pure Python module (walk.py) | No C/Cython needed -- tree encoding is compositional, not computational at bit-width scale |
| math | stdlib | `ceil`, `log2` for branch register width calculation | Standard library |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit + qiskit-aer | existing | Statevector simulation for verification tests | Test-time only, via existing `sim_backend.py` pattern |
| numpy | existing | Qubit array storage (qint internal) | Already used by qint for qubit index arrays |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure Python class | Cython extension | Python is sufficient -- tree class is a thin wrapper around qint/qarray allocations, no hot loops |
| qarray for branch registers | Raw qint list | qarray provides shape metadata and iteration protocol; matches CONTEXT.md "QuantumArray branch registers" |
| emit_x for root prep | qint(1, width=max_depth+1) | emit_x on allocated qubit is cleaner -- root prep is a single X gate on one specific qubit, not initializing a whole integer to a value |

**No new dependencies needed.** Everything builds on existing project infrastructure.

## Architecture Patterns

### Recommended Module Structure
```
src/quantum_language/
    walk.py              # NEW: QWalkTree, TreeNode classes
    __init__.py          # ADD: export QWalkTree
tests/python/
    test_walk_tree.py    # NEW: tree encoding tests
    test_walk_predicate.py # NEW: predicate interface tests
```

**Note:** CONTEXT.md says `quantum_lib/walk.py` but the actual package is `quantum_language` (in `src/quantum_language/`). The module MUST be placed in `src/quantum_language/walk.py` to be importable as `quantum_language.walk` or `ql.QWalkTree`.

### Pattern 1: Register Allocation via Existing Primitives
**What:** Use `qint` and `qarray` constructors for qubit allocation; the circuit's allocator handles physical qubit mapping automatically.
**When to use:** All register allocation in QWalkTree.
**Example:**
```python
import quantum_language as ql
from quantum_language._gates import emit_x

# Height register: one-hot encoding, max_depth+1 qubits
# Each qubit represents one level (qubit i = 1 means "at depth i")
height_register = ql.qint(0, width=max_depth + 1)

# Branch registers: one qint per depth level
# Width per register = ceil(log2(branching_degree_at_that_level))
branch_registers = []
for level in range(max_depth):
    width = math.ceil(math.log2(branching[level])) if branching[level] > 1 else 1
    branch_registers.append(ql.qint(0, width=width))

# Root state: set h[max_depth] = |1> via X gate
# Height register is right-aligned: qubit for level max_depth is at index 64-width+max_depth
height_offset = 64 - (max_depth + 1)
emit_x(height_register.qubits[height_offset + max_depth])
```

### Pattern 2: TreeNode as Lightweight State Wrapper
**What:** `TreeNode` wraps existing register references so the predicate callable has a clean interface.
**When to use:** Passed to the user's predicate function.
**Example:**
```python
class TreeNode:
    """Represents the current quantum state of a tree node for predicate evaluation."""

    def __init__(self, height_register, branch_registers, max_depth):
        self._height_register = height_register
        self._branch_registers = branch_registers
        self._max_depth = max_depth

    @property
    def depth(self):
        """The one-hot height register as a qint (max_depth+1 qubits)."""
        return self._height_register

    @property
    def branch_values(self):
        """List of qint branch registers, one per depth level."""
        return list(self._branch_registers)
```

### Pattern 3: Predicate Mutual Exclusion Validation
**What:** At construction, validate that the predicate never returns `(True, True)`.
**When to use:** QWalkTree constructor, after register allocation and root prep.
**Example strategy (circuit-level):**
```python
# Run predicate on the current state
node = TreeNode(self.height_register, self.branch_registers, self.max_depth)
is_accept, is_reject = predicate(node)

# Check mutual exclusion: accept AND reject must be |0>
# Use existing qint/qbool AND operator
conflict = is_accept & is_reject

# For validation, we can check the classical value
# (at construction, root state is computational basis, so this is deterministic)
if conflict.value:
    raise ValueError(
        "Predicate mutual exclusion violated: accept and reject "
        "both returned True for the root state"
    )
```

### Pattern 4: Simulation-Time Qubit Budget Enforcement
**What:** Check qubit count against budget only when simulating, not at construction.
**When to use:** In a `simulate()` method, `to_qasm()` wrapper, or similar.
**Example:**
```python
def _check_qubit_budget(self, max_qubits=17):
    """Raise error if tree exceeds simulation qubit budget."""
    total = self.total_qubits  # computed from registers
    if total > max_qubits:
        raise ValueError(
            f"Tree requires {total} qubits but simulation budget is "
            f"{max_qubits}. Reduce tree parameters or increase max_qubits."
        )
```

### Anti-Patterns to Avoid
- **Binary height encoding instead of one-hot:** Montanaro's algorithm requires single-qubit control per depth level. Binary encoding would need multi-qubit decoding, adding ancillas and gates. One-hot is mandatory.
- **Allocating branch registers as a single flat qint:** Each depth level needs independent branch register for per-level controlled operations in later phases (diffusion, walk operators). Must be separate `qint` objects.
- **Validating mutual exclusion via full statevector search:** Overkill for construction-time validation. The root state is a computational basis state -- classical evaluation suffices.
- **Creating the module in a `quantum_lib/` directory:** The project package is `quantum_language` (in `src/quantum_language/`), not `quantum_lib`. Module must go in the correct package.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Qubit allocation | Custom allocator | `qint(0, width=N)` constructor | The circuit's built-in allocator handles physical qubit mapping, LIFO tracking, and deallocation |
| Gate emission | Direct C calls | `emit_x()`, `emit_ry()` from `_gates.pyx` | Handles controlled context automatically (inside `with qbool:` blocks) |
| Function inverse | Custom gate reversal | `@ql.compile` + `.inverse()` pattern | Existing compile infrastructure captures, optimizes, and inverts gate sequences |
| Circuit export | Custom QASM generation | `ql.to_openqasm()` | Existing C-level OpenQASM 3.0 export handles all gate types |
| Statevector simulation | Custom simulation | `sim_backend.simulate()` or Qiskit `AerSimulator` | Existing pattern with `max_parallel_threads=4` |
| Array of quantum registers | Manual list management | `ql.qarray` or Python list of `qint` | qarray provides shape metadata; for branch registers a Python list of qint is also acceptable |

**Key insight:** This phase is entirely compositional -- it combines existing primitives (qint, qbool, qarray, emit_x, @ql.compile) into a higher-level abstraction. No new low-level quantum operations are needed.

## Common Pitfalls

### Pitfall 1: Wrong Module Path
**What goes wrong:** CONTEXT.md says `quantum_lib/walk.py` but the actual package is `quantum_language` at `src/quantum_language/`.
**Why it happens:** Naming discrepancy between discussion and codebase.
**How to avoid:** Always use `src/quantum_language/walk.py`. Verify by checking `src/quantum_language/__init__.py` for the package name.
**Warning signs:** `ImportError: No module named 'quantum_lib'`.

### Pitfall 2: One-Hot vs Binary Height Encoding
**What goes wrong:** Using binary encoding for height loses the single-qubit-control property needed by diffusion operators in Phase 98.
**Why it happens:** Binary is more qubit-efficient but requires multi-qubit decoding.
**How to avoid:** Always use one-hot: `max_depth + 1` qubits for height register, where qubit `i` being |1> means "at depth i". This matches Montanaro 2015.
**Warning signs:** If height register width != max_depth + 1, encoding is wrong.

### Pitfall 3: Branch Register Width for Non-Power-of-Two Branching
**What goes wrong:** `ceil(log2(d))` gives wrong result when `d=1` (returns 0, but need 1 qubit minimum).
**Why it happens:** `log2(1) = 0`, so `ceil(0) = 0`.
**How to avoid:** Use `max(1, math.ceil(math.log2(d)))` or handle `d=1` as special case (1 qubit, value always 0).
**Warning signs:** Zero-width registers, allocation failures.

### Pitfall 4: LIFO Scope Interference with Predicate Qbools
**What goes wrong:** Predicate returns qbools that get auto-uncomputed by scope cleanup before the walk algorithm can use them.
**Why it happens:** If predicate is called inside a `with` block, qbools created at that scope depth get registered in `_scope_stack` and uncomputed on `__exit__`.
**How to avoid:** Two strategies: (1) Use `@ql.compile` for the predicate -- compiled functions manage their own ancillas. (2) Call predicate at scope depth 0 (top level, outside any `with` block). (3) Call `.keep()` on returned qbools to prevent auto-uncomputation.
**Warning signs:** Qbool `_is_uncomputed` becomes True unexpectedly; "already uncomputed" errors.

### Pitfall 5: Right-Aligned Qubit Storage in qint
**What goes wrong:** Accessing height register qubits by wrong index.
**Why it happens:** qint stores qubits right-aligned: bit 0 (LSB) at `qubits[64 - width]`, bit `width-1` (MSB) at `qubits[63]`. For a one-hot register, qubit for depth `d` is at `qubits[64 - (max_depth + 1) + d]`.
**How to avoid:** Always compute qubit offset as `64 - self.height_register.width + level_index`. Use the existing `_collect_qubits` pattern from `diffusion.py` as reference.
**Warning signs:** X gate applied to wrong qubit; statevector shows wrong height.

### Pitfall 6: Predicate Validation on Non-Root States
**What goes wrong:** Mutual exclusion validated only for root but predicate may violate it for other nodes.
**Why it happens:** Full tree traversal validation would require exponential states.
**How to avoid:** Validate on root at construction (fast, deterministic basis state). Document that mutual exclusion must hold for all nodes. Full validation is the user's responsibility. The construction-time check catches obvious errors (both always True).
**Warning signs:** Walk algorithm produces wrong results in later phases due to predicate violations.

### Pitfall 7: Circuit Not Initialized Before Register Allocation
**What goes wrong:** qint constructor fails because no circuit exists.
**Why it happens:** User creates QWalkTree before calling `ql.circuit()`.
**How to avoid:** QWalkTree constructor should either require an active circuit or automatically call `ql.circuit()` / check `_get_circuit_initialized()`. Follow grover.py's pattern of calling `circuit()` at the start.
**Warning signs:** `RuntimeError: Circuit allocator not initialized`.

## Code Examples

Verified patterns from the project codebase:

### Qubit Allocation (from qint.__init__)
```python
# Source: src/quantum_language/qint.pyx lines 262-310
# qint allocates through circuit's qubit allocator
# Right-aligned storage: qubits[64-width] through qubits[63]
x = ql.qint(0, width=4)
# x.qubits[60], x.qubits[61], x.qubits[62], x.qubits[63] are the physical qubits
# x.qubits[60] = bit 0 (LSB), x.qubits[63] = bit 3 (MSB)
```

### Gate Emission (from _gates.pyx)
```python
# Source: src/quantum_language/_gates.pyx lines 37-94
from quantum_language._gates import emit_x, emit_ry, emit_h

# emit_x automatically handles controlled context
emit_x(qubit_index)  # X gate on specific physical qubit

# emit_ry for rotation gates
emit_ry(qubit_index, angle)  # Ry(angle) on specific qubit
```

### Statevector Verification Pattern (from test_diffusion.py)
```python
# Source: tests/python/test_diffusion.py lines 27-33
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return result.get_statevector()
```

### Module Registration Pattern (from __init__.py)
```python
# Source: src/quantum_language/__init__.py
# To add QWalkTree to the public API:
from .walk import QWalkTree
# Add to __all__ list:
__all__ = [
    # ... existing exports ...
    "QWalkTree",
]
```

### @ql.compile with Inverse (from compile.py)
```python
# Source: src/quantum_language/compile.py lines 1440-1461
# Compiled functions support .inverse() for uncomputation
@ql.compile
def my_predicate(node):
    is_accept = (node.depth == 0)  # leaf check
    is_reject = ql.qbool(False)
    return is_accept, is_reject

# Forward call
result = my_predicate(tree_node)
# Inverse (uncompute) call
my_predicate.inverse(tree_node)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Binary height encoding | One-hot height encoding | Montanaro 2015 | Single-qubit control per depth level; essential for efficient diffusion operators |
| Distance-from-root encoding | Height encoding (root=max_depth) | Qrisp implementation | Better generalization to subtree operations |
| Separate predicate method | Constructor parameter | CONTEXT.md decision | Fail-fast validation; predicate available for all operations |

**Reference implementations:**
- Qrisp (`QuantumBacktrackingTree`) uses one-hot height + QuantumArray branch path, matching Montanaro's formalization
- Martiel et al. (2019) practical implementation confirms one-hot encoding and provides gate count analysis

## Open Questions

1. **Predicate validation depth**
   - What we know: CONTEXT.md says validate mutual exclusion at construction. Root state is a computational basis state, making classical evaluation straightforward.
   - What's unclear: Should validation also test on non-root states? How exhaustive should it be?
   - Recommendation: Validate on root only at construction (fast, deterministic). Document that mutual exclusion must hold for all nodes. This matches Qrisp's approach.

2. **TreeNode `.depth` attribute semantics**
   - What we know: CONTEXT.md says TreeNode has `.depth` and `.branch_values`. The height register is one-hot encoded.
   - What's unclear: Is `.depth` the raw one-hot qint (user compares with `==`) or a decoded integer?
   - Recommendation: Expose `.depth` as the raw one-hot qint. Users write `node.depth == ql.qint(level, width=max_depth+1)` or we provide a convenience method. The one-hot encoding is the quantum state -- decoding would require ancillas.

3. **Branch register for single-child levels**
   - What we know: If `branching[i] = 1`, that level has only one child.
   - What's unclear: Should we still allocate a 1-qubit branch register (always |0>) or skip it?
   - Recommendation: Allocate 1-qubit register (always 0). Keeps indexing uniform and avoids special cases in later phases.

4. **Predicate return value ownership**
   - What we know: Predicate returns (is_accept, is_reject) as qbool. Walk operators (Phase 98-99) need these qbools.
   - What's unclear: Who owns the returned qbools? Who is responsible for uncomputation?
   - Recommendation: The QWalkTree stores references to the predicate-returned qbools. For `@ql.compile` predicates, the framework handles uncomputation via `.inverse()`. For raw callables, the user must ensure proper cleanup. Document this contract.

## Sources

### Primary (HIGH confidence)
- Project codebase: `src/quantum_language/qint.pyx`, `compile.py`, `_gates.pyx`, `qarray.pyx`, `qbool.pyx`, `sim_backend.py`, `grover.py`, `diffusion.py` -- directly examined for API patterns, qubit allocation, scope management, and gate emission
- Project CONTEXT.md: `97-CONTEXT.md` -- locked user decisions constraining implementation
- Project REQUIREMENTS.md: phase requirement definitions TREE-01 through PRED-03
- Project STATE.md: current project position and accumulated decisions

### Secondary (MEDIUM confidence)
- [Qrisp QuantumBacktrackingTree documentation](https://qrisp.eu/reference/Algorithms/QuantumBacktrackingTree.html) -- verified implementation of Montanaro's algorithm with one-hot height encoding and branch quantum array
- [Qrisp Sudoku tutorial](https://www.qrisp.eu/general/tutorial/Sudoku.html) -- practical example of predicate functions and tree construction
- [Montanaro 2015 paper (arXiv:1509.02374)](https://arxiv.org/abs/1509.02374) -- original algorithm definition
- [Martiel et al. 2019 practical implementation](https://arxiv.org/pdf/1908.11291) -- practical implementation with gate count analysis

### Tertiary (LOW confidence)
- [Quantum Backtracking in Qrisp Applied to Sudoku Problems (2024)](https://arxiv.org/abs/2402.10060) -- recent application confirming algorithm patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are existing project infrastructure, no external dependencies
- Architecture: HIGH -- one-hot encoding per Montanaro, verified against Qrisp reference implementation, patterns follow existing grover.py/diffusion.py module structure
- Pitfalls: HIGH -- identified from direct codebase analysis (right-aligned qubits, LIFO scope tracking, module path discrepancy)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable -- internal project, no external version drift)
