# Phase 101: Detection & Demo - Research

**Researched:** 2026-03-03
**Domain:** Quantum walk detection algorithm (Montanaro 2015 Algorithm 1)
**Confidence:** HIGH

## Summary

Phase 101 implements the iterative power-method detection algorithm from Montanaro's backtracking framework (Algorithm 1 from arXiv:1509.02374). The algorithm applies the walk step U raised to increasing powers (1, 2, 4, 8, ...), measuring root-state overlap after each power level. If any measurement finds the root overlap probability below the 3/8 threshold, a solution exists in the tree. The implementation is a classical loop around quantum circuits -- each power level is a separate circuit execution within the 17-qubit budget.

All foundational infrastructure exists from Phases 97-100: QWalkTree class with register allocation, local_diffusion with variable branching, R_A/R_B walk operators, compiled walk_step via @ql.compile, and statevector simulation patterns. Phase 101 adds a `detect()` method to QWalkTree and demonstrates it on a small SAT instance.

**Primary recommendation:** Implement detect() as a method on QWalkTree that runs a classical loop of circuit constructions, applying walk_step k times per iteration (k doubling each round), measuring root overlap via statevector, and checking the 3/8 threshold. Demo uses a 3-variable binary SAT instance (depth 3, 7 tree qubits + predicate ancillae, well within 17-qubit budget).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fixed power schedule: apply walk step 1, 2, 4, 8, ... times (doubling), measure after each power level
- Root state overlap measurement: after walk step powers, measure overlap with initial root state |r>; if overlap drops below threshold, solution exists
- Threshold: probability > 3/8 per Montanaro Algorithm 1
- Classical loop execution: each power level is a separate circuit execution; classical code checks threshold between runs
- Maximum iterations computed from Montanaro's O(sqrt(T/n)) formula based on tree size parameters
- 3-variable binary SAT instance (binary tree depth 3, 8 leaves)
- Hardcoded clause check predicate: predicate encodes specific clauses directly
- Both satisfiable and unsatisfiable instances demonstrated
- Demo delivered as BOTH a standalone script in examples/ for users to run AND pytest test fixtures for CI verification
- Method on QWalkTree: `tree.detect(max_iterations=None)` -- consistent with tree.walk_step(), tree.R_A(), tree.R_B()
- Returns simple bool: True if solution detected, False otherwise
- Optional `max_iterations` parameter: auto-computed from tree size by default, user override for testing
- Silent execution: no print output
- Statevector probability tolerance: 1e-6
- All DET requirements tested: DET-01, DET-02, DET-03
- Test intermediate walk step states AND final detection result
- Explicit qubit budget verification test: confirms 3-variable SAT demo stays within 17 qubits

### Claude's Discretion
- Exact clause formulas for the satisfiable and unsatisfiable SAT instances
- Predicate implementation details (how branch register values map to variable assignments)
- Measurement circuit construction (how to compute root state overlap from statevector)
- Internal iteration loop structure and convergence check implementation
- Test helper organization and fixture design
- Demo script formatting and output presentation

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DET-01 | Iterative power-method detection algorithm (apply walk step powers, measure, threshold probability > 3/8) | Algorithm 1 implementation: classical loop constructs fresh circuit per power level, applies walk_step k times, computes root overlap via statevector, checks threshold |
| DET-02 | Demo on small SAT instance (binary tree depth 2-3, within 17-qubit budget) | 3-variable binary SAT with depth=3: 7 tree qubits + predicate ancillae fits within 17 qubits. Hardcoded clause predicate for SAT/UNSAT cases |
| DET-03 | Qiskit statevector verification confirming detection probability on known-solution and no-solution instances | Statevector simulation with _simulate_statevector pattern; measure root overlap probability; verify above/below 3/8 threshold |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language | current | Framework under development | Project core |
| qiskit | installed | QASM3 parsing and transpilation | Already used in all walk tests |
| qiskit-aer | installed | Statevector simulation | Already used in all walk tests |
| numpy | installed | Statevector array manipulation | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | installed | Test framework | Test execution |
| math | stdlib | Angle calculations, sqrt, log | Max iterations formula |

### Alternatives Considered
None -- this phase uses only existing project infrastructure.

## Architecture Patterns

### Detection Algorithm Structure

The detection algorithm (Montanaro Algorithm 1) follows this pattern:

```python
def detect(self, max_iterations=None):
    """Detect whether a solution exists in the backtracking tree."""
    if max_iterations is None:
        # T = total tree nodes, n = depth
        # max_iter ~ O(sqrt(T/n))
        T = self._tree_size()
        max_iterations = max(1, int(math.ceil(math.sqrt(T / self.max_depth))))

    # Power schedule: 1, 2, 4, 8, ... up to max_iterations
    power = 1
    while power <= max_iterations:
        root_prob = self._measure_root_overlap(power)
        if root_prob < 3.0 / 8.0:
            return True  # Solution detected
        power *= 2

    return False  # No solution detected
```

### Circuit-per-Power-Level Pattern

Each power level requires a fresh circuit because the framework accumulates gates globally:

```python
def _measure_root_overlap(self, num_steps):
    """Build circuit with num_steps walk steps and measure root overlap."""
    import quantum_language as ql

    ql.circuit()  # Fresh circuit
    tree = QWalkTree(max_depth=self.max_depth, branching=self.branching,
                     predicate=self._predicate, max_qubits=self.max_qubits)

    for _ in range(num_steps):
        tree.walk_step()

    # Get statevector and compute root overlap
    qasm_str = ql.to_openqasm()
    sv = _simulate_statevector(qasm_str)
    root_idx = _root_state_index(tree)
    return abs(sv[root_idx]) ** 2
```

**Key insight:** The detect() method cannot reuse `self` for inner circuits because `ql.circuit()` resets state. It must recreate the tree with the same parameters for each power level. This means detect() stores the tree construction parameters and rebuilds internally.

### Root State Index Computation

The root state in the tree encoding has h[max_depth]=|1> and all other qubits=|0>. Using Qiskit's little-endian convention:

```python
def _root_state_index(tree):
    """Compute statevector index for the root state |r>."""
    h_root_qubit = tree._height_qubit(tree.max_depth)
    return 1 << h_root_qubit
```

### SAT Predicate Pattern

For a 3-variable SAT instance, the tree has depth=3 with binary branching. Variables x1, x2, x3 correspond to branch choices at depths 2, 1, 0 (from root downward). The predicate evaluates clauses on the branch register values:

```python
def sat_predicate(node):
    """Predicate for (x1 OR NOT x2) AND (x2 OR x3)."""
    is_accept = ql.qbool()
    is_reject = ql.qbool()

    # At leaf level (depth=0), evaluate all clauses
    # Branch values encode variable assignments
    # Use CNOT/Toffoli gates to compute clause satisfaction
    # Set is_accept if all clauses satisfied
    # Set is_reject if any clause violated at current partial assignment

    return (is_accept, is_reject)
```

### Anti-Patterns to Avoid
- **Nested circuit reuse:** Do NOT try to reuse the outer tree's walk_step inside detect(). Each power level needs a fresh circuit.
- **Sampling-based measurement:** Do NOT use shot-based measurement. Use statevector directly for exact probabilities.
- **Global state leakage:** detect() must not modify the caller's circuit state. It creates and discards its own circuits internally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Statevector simulation | Custom matrix multiplication | qiskit-aer AerSimulator(method="statevector") | Already proven in 30+ walk tests |
| QASM generation | Manual QASM string construction | ql.to_openqasm() | Framework handles gate-to-QASM compilation |
| Walk step compilation | Manual gate sequence replay | tree.walk_step() with @ql.compile | Handles caching and optimization |
| Controlled walk step | Manual control qubit threading | `with qbool:` pattern on walk_step | Framework propagates controls |

## Common Pitfalls

### Pitfall 1: Circuit State Accumulation
**What goes wrong:** Calling walk_step() multiple times on the same circuit builds up gates correctly, but detect() needs separate circuits for each power level (to re-prepare the root state each time).
**Why it happens:** The framework's ql.circuit() is global state. There's no way to "reset" mid-circuit.
**How to avoid:** detect() creates a fresh ql.circuit() + QWalkTree for each power level. Store construction parameters (max_depth, branching, predicate, max_qubits) and rebuild.
**Warning signs:** Getting nonsense probabilities because the walk is applied on top of a previous power level's walk.

### Pitfall 2: Qubit Budget with Predicates
**What goes wrong:** Predicate evaluation allocates ancilla qubits (accept/reject qbools + internal computation qubits). Total qubits can exceed 17.
**Why it happens:** Raw predicates allocate new qubits per call. With multiple walk steps, each calling local_diffusion which calls the predicate, the qubit count balloons.
**How to avoid:** Use compiled predicates or very simple predicates. For the demo, the clause-check predicate must be minimal. Count qubits carefully. Consider using @ql.compile on the predicate for qubit reuse.
**Warning signs:** ValueError from _check_qubit_budget or Qiskit simulator running out of memory.

### Pitfall 3: Threshold Direction
**What goes wrong:** Checking root_prob > 3/8 instead of root_prob < 3/8 (or vice versa).
**Why it happens:** Montanaro's Algorithm 1 states that if a marked vertex exists, the overlap with the root state *decreases*. The walk moves amplitude away from the root toward marked vertices.
**How to avoid:** The threshold check is: if root_prob < 3/8, solution detected (True). If root_prob >= 3/8 for all power levels, no solution (False).
**Warning signs:** False positives on no-solution trees or false negatives on solution trees.

### Pitfall 4: Max Iterations Too Small
**What goes wrong:** The power schedule doesn't go high enough, missing the solution.
**Why it happens:** max_iterations derived from wrong tree size estimate.
**How to avoid:** For the demo, the tree is small (8 leaves, depth 3). The formula gives max_iter ~ sqrt(8/3) ~ 2. But to be safe, use a generous upper bound for small trees (e.g., max(4, computed_value)).
**Warning signs:** Detection returns False on a known-satisfiable instance.

### Pitfall 5: Predicate Qubit Overhead
**What goes wrong:** Each walk step with variable branching evaluates the predicate at every non-leaf depth, allocating ancillae each time.
**Why it happens:** The current _variable_diffusion implementation calls the raw predicate, which allocates new qbools.
**How to avoid:** For the demo SAT instance, keep the predicate extremely simple (CNOT-based, minimal ancillae). Alternatively, test whether the tree works without variable branching (uniform branching with a leaf-level-only predicate).
**Warning signs:** Qubit count exceeds 17 after just one walk step.

## Code Examples

### Existing _simulate_statevector pattern (from test_walk_operators.py)
```python
def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector as numpy array."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return np.asarray(result.get_statevector())
```

### Existing QWalkTree construction pattern
```python
ql.circuit()
tree = QWalkTree(max_depth=2, branching=2)
tree.walk_step()  # Applies U = R_B * R_A
sv = _simulate_statevector(ql.to_openqasm())
```

### Root state index computation
```python
h_root = tree._height_qubit(tree.max_depth)
root_idx = 1 << h_root  # Little-endian: qubit k set = bit k of index
root_prob = abs(sv[root_idx]) ** 2
```

### Multiple walk steps on same circuit
```python
ql.circuit()
tree = QWalkTree(max_depth=3, branching=2)
for _ in range(4):
    tree.walk_step()  # Applies U^4
sv = _simulate_statevector(ql.to_openqasm())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase estimation detection | Iterative power-method (Algorithm 1) | Montanaro 2015 | Simpler, fewer ancilla qubits |
| Amplitude estimation | Direct threshold check | Context decision | Avoids IQAE complexity |

## Open Questions

1. **Predicate qubit count for SAT demo**
   - What we know: Raw predicates allocate new qbools per call. The tree has 7 qubits. Predicate adds 2 (accept/reject) + clause computation ancillae per evaluation.
   - What's unclear: Exact qubit count after walk_step with variable branching predicate. May need to prototype to confirm fits within 17.
   - Recommendation: Start with uniform branching (no predicate, pure detection test), then add SAT predicate separately. If qubit budget is tight, consider a depth-2 tree (5 qubits) for the SAT demo or a simpler predicate that only checks at leaf level.

2. **Predicate at leaf level only vs all levels**
   - What we know: In Montanaro's framework, the predicate evaluates accept/reject at every node. For SAT, leaf nodes have complete assignments (accept if satisfying), internal nodes may have partial assignment checks (reject if already violated).
   - What's unclear: Whether the demo predicate should evaluate at all levels or only leaves.
   - Recommendation: For simplicity, implement a predicate that only sets accept at leaves (complete assignment check). Internal nodes have is_accept=False, is_reject=False (neither accepted nor rejected, which means "continue exploring"). This minimizes predicate complexity while demonstrating the algorithm.

3. **detect() encapsulation**
   - What we know: detect() needs fresh circuits per power level, but must use the same tree parameters.
   - What's unclear: Best way to encapsulate the "rebuild tree" pattern.
   - Recommendation: detect() stores construction parameters and creates a helper _build_and_walk(num_steps) method that returns root overlap probability. This keeps the public API clean.

## Sources

### Primary (HIGH confidence)
- Existing codebase: walk.py (QWalkTree, walk_step, R_A, R_B, local_diffusion)
- Existing test files: test_walk_operators.py, test_walk_variable.py, test_walk_diffusion.py, test_walk_tree.py
- CONTEXT.md: Phase 101 locked decisions
- REQUIREMENTS.md: DET-01, DET-02, DET-03 definitions

### Secondary (MEDIUM confidence)
- Montanaro arXiv:1509.02374 Algorithm 1 (referenced in codebase docstrings, consistent with CONTEXT.md decisions)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use
- Architecture: HIGH -- clear algorithm definition, existing patterns to follow
- Pitfalls: HIGH -- based on direct codebase analysis of qubit allocation patterns

**Research date:** 2026-03-03
**Valid until:** 2026-04-03
