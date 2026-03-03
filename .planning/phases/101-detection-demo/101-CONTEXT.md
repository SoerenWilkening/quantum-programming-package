# Phase 101: Detection & Demo - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Iterative power-method detection algorithm that applies walk step powers, measures root state overlap, and determines solution existence by threshold comparison (probability > 3/8). Includes end-to-end demo on a small 3-variable SAT instance within the 17-qubit simulator budget, with both satisfiable and unsatisfiable cases. Solution finding (Algorithm 2) and public API exports are future phases.

</domain>

<decisions>
## Implementation Decisions

### Detection Algorithm
- Fixed power schedule: apply walk step 1, 2, 4, 8, ... times (doubling), measure after each power level
- Root state overlap measurement: after walk step powers, measure overlap with initial root state |r>; if overlap drops below threshold, solution exists
- Threshold: probability > 3/8 per Montanaro Algorithm 1
- Classical loop execution: each power level is a separate circuit execution; classical code checks threshold between runs
- Maximum iterations computed from Montanaro's O(sqrt(T/n)) formula based on tree size parameters

### SAT Demo Design
- 3-variable binary SAT instance (binary tree depth 3, 8 leaves)
- Hardcoded clause check predicate: predicate encodes specific clauses directly (e.g., x1 OR NOT x2) for clarity and readability
- Both satisfiable and unsatisfiable instances demonstrated: one SAT instance with a known solution (detect returns True) and one with no satisfying assignment (detect returns False)
- Demo delivered as BOTH a standalone script in examples/ for users to run AND pytest test fixtures for CI verification

### API Surface
- Method on QWalkTree: `tree.detect(max_iterations=None)` — consistent with tree.walk_step(), tree.R_A(), tree.R_B()
- Returns simple bool: True if solution detected, False otherwise
- Optional `max_iterations` parameter: auto-computed from tree size by default, user override for testing or constrained scenarios
- Silent execution: no print output, consistent with walk_step(), local_diffusion(), grover()

### Verification Scope
- Statevector probability tolerance: 1e-6 (matching existing walk tests)
- All DET requirements tested: DET-01 (power-method converges), DET-02 (SAT demo within 17 qubits), DET-03 (statevector on solution/no-solution), false positive rejection
- Test intermediate walk step states AND final detection result (catches pipeline bugs early)
- Explicit qubit budget verification test: confirms 3-variable SAT demo stays within 17 qubits

### Claude's Discretion
- Exact clause formulas for the satisfiable and unsatisfiable SAT instances
- Predicate implementation details (how branch register values map to variable assignments)
- Measurement circuit construction (how to compute root state overlap from statevector)
- Internal iteration loop structure and convergence check implementation
- Test helper organization and fixture design
- Demo script formatting and output presentation

</decisions>

<specifics>
## Specific Ideas

- Montanaro Algorithm 1 is the reference: iterative doubling of walk step powers with root overlap measurement
- The classical loop pattern keeps each circuit small enough for the 17-qubit constraint
- 3-variable SAT (depth 3) is more interesting than 2-variable while still fitting budget
- Hardcoded clause predicates make the demo readable and self-contained — no CNF parser needed
- The satisfiable/unsatisfiable pair validates both detection directions (no false positives or false negatives)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `QWalkTree.walk_step()`: Compiled walk step U = R_B * R_A, callable via `with qbool:` for controlled variant
- `_all_qubits_register()`: Bundles all tree qubits into single qint for @ql.compile compatibility
- `_simulate_statevector()` test helper: Qiskit statevector simulation pattern used in all walk test files
- `QWalkTree.__init__` with `predicate` parameter: accepts callable returning (accept, reject) qbools
- Variable branching (`_variable_diffusion`): evaluates predicate per child, applies conditional rotations
- `verify_disjointness()`: structural validation already in place

### Established Patterns
- One-hot height register for depth control (h[depth]=|1> means node at depth)
- Height-controlled dispatch: all diffusion gates controlled on h[depth]
- V-gate CCRy decomposition for doubly-controlled gates (avoids nested `with` blocks)
- Lazy compilation: walk_step compiled on first call, not at construction
- Test organization: separate test files per concern (test_walk_tree, test_walk_diffusion, test_walk_operators, test_walk_variable)
- Predicate uncomputation via @ql.compile .adjoint() pattern

### Integration Points
- `walk.py`: detect() method added to QWalkTree class
- `tests/python/test_walk_detection.py`: new test file for DET-01, DET-02, DET-03
- `examples/`: new standalone demo script for SAT detection
- Predicate pattern: reuse existing `predicate(node) -> (accept, reject)` interface from Phase 97

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 101-detection-demo*
*Context gathered: 2026-03-03*
