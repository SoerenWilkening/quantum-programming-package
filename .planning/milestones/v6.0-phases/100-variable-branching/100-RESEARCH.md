# Phase 100: Variable Branching - Research

**Researched:** 2026-03-02
**Domain:** Quantum walk local diffusion with variable branching degree
**Confidence:** HIGH

## Summary

Phase 100 extends the existing uniform-branching local diffusion operator to support variable branching, where different nodes in the backtracking tree may have different numbers of valid children based on predicate evaluation. The core mechanism evaluates the predicate on each potential child, stores validity results in ancilla qbools, and dispatches angle-conditional Ry rotations based on the count of valid children d(x).

The implementation builds directly on the Phase 98 local_diffusion() infrastructure. The key addition is a pre-diffusion predicate evaluation loop that marks which children are valid, followed by conditional rotation blocks that select the correct phi = 2*arctan(sqrt(d(x))) angle based on the validity pattern. When no predicate is provided or all children are valid, the existing uniform fast-path fires with zero overhead.

**Primary recommendation:** Modify `local_diffusion()` in walk.py to add predicate evaluation before the existing U * S_0 * U_dagger pattern, with per-d(x) conditional angle dispatch controlled on validity ancilla patterns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Reuse existing `predicate(node) -> (accept, reject)` interface -- no new callback needed
- Framework internally navigates to child states by temporarily setting branch registers for the next depth to each child index (0..d-1), advancing the height register, calling the predicate, then reversing
- User's predicate sees a complete node state -- all navigation is internal to the framework
- Allocate one dedicated ancilla qbool per potential child to store validity (reject) results
- Evaluate predicate once per child, store results, use for counting and cascade
- Uncompute validity ancillae at end of diffusion using the existing LIFO/@ql.compile inverse pattern
- Classical enumeration: iterate over all possible d(x) values (1..d_max) and emit conditional rotation blocks for each
- No quantum popcount register needed -- pattern matching on validity ancillae controls which block fires
- Emit rotation per bit pattern (e.g., for d=2 with d_max=3: patterns 110, 101, 011 each get their own controlled rotation)
- No OR ancilla -- emit rotation conditioned directly on each matching pattern
- Skip diffusion entirely when d(x) = 0 (all children rejected -- node is effectively a leaf)
- Support up to ternary branching (d_max = 3) for test cases within 17-qubit budget
- Variable branching replaces uniform branching entirely -- uniform becomes a special case where d(x) = d_max
- Auto-detect fast-path: when no predicate is provided (or predicate never rejects children), use existing precomputed uniform angles directly -- zero overhead regression
- All existing Phase 97-99 tests must pass unchanged -- backward compatible
- Trees without predicates behave identically to current uniform branching
- Conditional blocks per d value: for each possible d (1..d_max), emit rotation block conditioned on "exactly d validity ancillae are |1>"
- Per-d cascade blocks compiled separately (cached via @ql.compile with d-value as cache key)
- S_0 reflection stays fixed on all branch register qubits + parent height qubit
- All angles for d=1..d_max precomputed at QWalkTree construction time
- When d(x) = d_max (all children valid), still go through conditional block machinery (no special-case bypass within variable branching path)

### Claude's Discretion
- Per-d cascade vs single adaptive cascade implementation choice
- Exact gate decomposition for multi-controlled rotations conditioned on validity patterns
- Ancilla allocation and cleanup ordering details
- Test tree structures (within ternary/17-qubit constraints)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DIFF-04 | Variable branching support -- count valid children per node via predicate evaluation, controlled Ry rotation based on child count d(x) | Core implementation: predicate evaluation loop, validity ancillae, conditional angle dispatch, fast-path auto-detection |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (walk.py) | current | QWalkTree, local_diffusion, cascade ops | Project framework |
| quantum_language._gates | current | emit_ry, emit_x, emit_mcz, emit_h | Low-level gate emission |
| quantum_language.qbool | current | Validity ancilla allocation | Framework primitive |
| quantum_language.compile | current | @ql.compile for cascade caching | Compilation infrastructure |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit-aer | installed | AerSimulator for statevector tests | All verification tests |
| numpy | installed | Statevector analysis, amplitude comparison | Test assertions |
| pytest | installed | Test framework | All tests |

### Alternatives Considered
None -- all locked to existing framework patterns.

## Architecture Patterns

### Pattern 1: Child Navigation for Predicate Evaluation
**What:** To evaluate the predicate on child i of a node at depth d, the framework must temporarily move to the child state: set branch_registers[level_idx+1] to child index i and flip height register from h[depth] to h[depth-1], call predicate, store reject result in validity ancilla, then reverse the navigation.

**When to use:** During variable branching diffusion, before the U * S_0 * U_dagger pattern.

**Key insight:** The height register navigation (h[depth] -> h[depth-1]) can be done via controlled-X gates. The branch register navigation requires encoding child index i into the appropriate branch register. For binary branching (d=2), child 0 is |0> and child 1 is |1> on a single qubit. For ternary (d=3), children 0,1,2 use 2-qubit encoding.

**Implementation approach:**
```python
# For each child i in range(d_max):
#   1. Navigate to child: set branch_reg[next_level] = i
#   2. Flip height: X on h[depth], X on h[depth-1]
#   3. Call predicate -> get (accept, reject) qbools
#   4. Store reject result into validity_ancilla[i]
#   5. Reverse: uncompute predicate, undo height flip, undo branch set
```

The branch register "set to i" step uses X gates on specific qubits of the next-level branch register to encode the binary representation of i. The height flip is two X gates on the one-hot register.

### Pattern 2: Validity Pattern Matching for Conditional Dispatch
**What:** For d_max children with validity ancillae v[0..d_max-1], each possible child count d(x) corresponds to specific bit patterns. The rotation block for count=k fires when exactly k validity ancillae are |1>.

**When to use:** After predicate evaluation, before S_0 reflection.

**Key insight:** For d_max=2, patterns are: d=0 (00, skip), d=1 (01, 10), d=2 (11). For d_max=3: d=0 (000), d=1 (001, 010, 100), d=2 (011, 101, 110), d=3 (111).

Each pattern can be matched using multi-controlled gates with appropriate X-gate sandwiches:
- To match v[0]=0, v[1]=1: X on v[0], then control on both v[0] and v[1], then X on v[0]
- Each pattern emits its own conditional Ry rotation on the parent-child split qubit

### Pattern 3: Fast-Path Detection
**What:** When no predicate is provided, skip all variable branching machinery and use existing uniform angles directly.

**When to use:** QWalkTree construction and local_diffusion() dispatch.

**Implementation:**
```python
if self._predicate is None:
    # Use existing uniform diffusion path -- zero overhead
    # (existing code path from Phase 98)
else:
    # Variable branching path with predicate evaluation
```

### Anti-Patterns to Avoid
- **Nested `with qbool:` blocks**: The framework cannot nest quantum-quantum AND. All multi-controlled operations must use V-gate decomposition (established in Phase 98).
- **Quantum popcount register**: Don't build a separate register counting valid children. Pattern matching on validity ancillae directly is simpler and uses fewer qubits.
- **Modifying S_0 reflection basis**: S_0 operates on the full branch register + height qubit space. Invalid children get zero amplitude from the conditional rotation, so the full-space S_0 is equivalent to the valid-subspace reflection.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-controlled Ry | Custom decomposition | V-gate CCRy pattern from _emit_cascade_h_controlled | Already debugged in Phase 98 |
| Cascade state prep | New cascade logic | _plan_cascade_ops() with d parameter | Existing binary-splitting cascade handles arbitrary d |
| Compiled caching | Manual cache | @ql.compile with key=d | Framework handles replay/inverse |

## Common Pitfalls

### Pitfall 1: Qubit Budget Explosion
**What goes wrong:** Validity ancillae + child navigation qubits push total beyond 17.
**Why it happens:** Each child needs one validity ancilla, navigation uses branch register at next level.
**How to avoid:** Carefully budget: for d_max=2 at depth 2 on binary tree: 5 tree qubits + 2 validity ancillae = 7 qubits. For d_max=3 at depth 2 on ternary tree: 7 tree qubits + 3 validity ancillae = 10 qubits. Tests must verify <= 17.
**Warning signs:** Test failures with "qubit budget" errors.

### Pitfall 2: Uncomputation of Validity Ancillae
**What goes wrong:** Validity ancillae left entangled with tree state, corrupting subsequent operations.
**Why it happens:** Predicate evaluation entangles ancillae with tree registers; must be fully uncomputed.
**How to avoid:** Use symmetric evaluate-then-uncompute pattern. The CONTEXT.md locks the LIFO/@ql.compile inverse approach. Evaluate all children, store results, do all the diffusion work, then uncompute in reverse order.
**Warning signs:** D_x^2 != I (reflection property violated).

### Pitfall 3: Incorrect Pattern Matching for d=0 Case
**What goes wrong:** When all children are rejected (d=0), the diffusion still fires.
**Why it happens:** No explicit skip for d=0 pattern (all validity ancillae |0>).
**How to avoid:** The d=0 case naturally produces zero rotation angle -- but the S_0 reflection may still fire on the wrong subspace. Explicitly skip the entire diffusion when d=0 is detected, or ensure that the conditional rotation for d=0 produces identity.
**Warning signs:** Statevector has non-zero amplitude on invalid child states.

### Pitfall 4: Height Register Navigation During Child Evaluation
**What goes wrong:** The height flip (h[depth] <-> h[depth-1]) during child evaluation conflicts with the height-controlled dispatch of the diffusion.
**Why it happens:** local_diffusion is already height-controlled. Moving to child state changes the height register temporarily.
**How to avoid:** The predicate evaluation loop must happen BEFORE the height-controlled diffusion gates. Navigate to child, evaluate, store in ancilla, navigate back -- all before the U * S_0 * U_dagger pattern. The validity ancillae then persist through the diffusion and are uncomputed after.
**Warning signs:** Gates firing at wrong depth, incorrect statevectors.

### Pitfall 5: Backward Compatibility Regression
**What goes wrong:** Existing Phase 97-99 tests fail after variable branching changes.
**Why it happens:** Modifying local_diffusion() or _setup_diffusion() changes behavior for uniform branching.
**How to avoid:** Fast-path auto-detection: when no predicate is provided, use exactly the existing code path. The variable branching path only activates when a predicate is present.
**Warning signs:** Any test_walk_*.py test failure.

## Code Examples

### Validity Ancilla Allocation
```python
from quantum_language.qbool import qbool

# Allocate one validity ancilla per potential child
d_max = self.branching[level_idx]
validity = [qbool() for _ in range(d_max)]
```

### Child Navigation Pattern
```python
# Navigate to child i at next depth
branch_reg = self.branch_registers[next_level_idx]
w = branch_reg.width
# Encode child index i in branch register
for bit in range(w):
    if (i >> (w - 1 - bit)) & 1:
        emit_x(int(branch_reg.qubits[64 - w + bit]))

# Flip height: move from depth to depth-1
emit_x(self._height_qubit(depth))
emit_x(self._height_qubit(depth - 1))

# Evaluate predicate
node = self.node
accept, reject = self._predicate(node)
# Store reject result into validity ancilla (valid = not rejected)
# ... CNOT from reject to validity[i] ...

# Uncompute predicate
self.uncompute_predicate()

# Undo height flip
emit_x(self._height_qubit(depth - 1))
emit_x(self._height_qubit(depth))

# Undo branch register encoding
for bit in range(w):
    if (i >> (w - 1 - bit)) & 1:
        emit_x(int(branch_reg.qubits[64 - w + bit]))
```

### Conditional Rotation Per Pattern
```python
import itertools

# For each possible d value (1..d_max), find all bit patterns with exactly d ones
for d_val in range(1, d_max + 1):
    phi_d = 2.0 * math.atan(math.sqrt(d_val))
    # All bit patterns of length d_max with exactly d_val ones
    for pattern in itertools.combinations(range(d_max), d_val):
        # pattern is a tuple of indices that are |1> (valid children)
        # Emit controlled rotation: control on exactly this pattern
        # Use X gates to flip |0> ancillae to |1> for matching
        zeros = [i for i in range(d_max) if i not in pattern]
        for z in zeros:
            emit_x(validity[z].qubit_index)
        # Multi-controlled Ry on parent-child qubit, controlled on ALL validity ancillae
        # (all now |1> if pattern matches)
        # ... emit multi-controlled Ry ...
        for z in zeros:
            emit_x(validity[z].qubit_index)  # undo
```

## Open Questions

1. **Validity ancilla semantics: valid=|1> or reject=|1>?**
   - The predicate returns (accept, reject). The CONTEXT says "validity (reject) results".
   - Recommendation: Store the REJECT qubit value. valid child = reject is |0>, invalid child = reject is |1>. When counting valid children, count the number of reject ancillae that are |0>. This aligns with the predicate interface and avoids an extra NOT gate.
   - Alternative: Copy and negate so validity[i]=|1> means valid. This is clearer for pattern matching.
   - Decision: Claude's discretion per CONTEXT.md.

2. **Exact ancilla budget for test trees**
   - Binary tree depth 2 with predicate: 5 tree + 2 validity = 7 qubits. Well within 17.
   - Binary tree depth 3 with predicate: 7 tree + 2 validity = 9 qubits. Fine.
   - Ternary tree depth 2 with predicate: 7 tree + 3 validity = 10 qubits. Fine.
   - The predicate itself may allocate additional ancillae. Must budget carefully.
   - Recommendation: Test predicates should use minimal ancillae (simple reject logic on branch values).

## Sources

### Primary (HIGH confidence)
- walk.py source code -- current implementation of QWalkTree, local_diffusion, cascade ops
- diffusion.py source code -- _collect_qubits, S_0 reflection pattern
- CONTEXT.md -- locked decisions and design constraints
- Phase 98/99 summaries -- established patterns and known limitations

### Secondary (MEDIUM confidence)
- Montanaro 2015 (arXiv:1509.02374) -- theoretical basis for variable branching angles

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- using existing project infrastructure exclusively
- Architecture: HIGH -- patterns directly extend Phase 98 local_diffusion with well-understood mechanisms
- Pitfalls: HIGH -- based on concrete Phase 98/99 debugging experience (V-gate decomposition, nested control limitation)

**Research date:** 2026-03-02
**Valid until:** Indefinite (project-internal research)
