# Phase 97: Tree Encoding & Predicate Interface - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Foundational data structures for quantum backtracking walks (Montanaro 2015). Deliver QWalkTree class with register layout, root state preparation, predicate validation, and resource awareness. Local diffusion, walk operators, variable branching, and detection belong in later phases (98-101).

</domain>

<decisions>
## Implementation Decisions

### Tree Constructor API
- All-in-one constructor: `QWalkTree(max_depth, branching, predicate=my_fn)`
- `max_depth` is number of levels (inclusive): depth=3 means 4 levels (0,1,2,3) matching Montanaro's notation
- `branching` accepts int (uniform, shorthand for `[d]*max_depth`) or list (per-level specification, length = max_depth)
- Eager qubit allocation at construction time
- Root state preparation happens automatically during construction (no separate `prepare_root()` call)
- Registers exposed as named attributes: `tree.height_register`, `tree.branch_registers[i]` for debugging/inspection

### Predicate Interface
- Predicate is a constructor parameter (not a separate method call)
- Callable receives a `TreeNode` state object with `.depth`, `.branch_values` attributes
- Returns tuple of two qbools: `(is_accept, is_reject)`
- Mutual exclusion validation happens at construction time (fail fast)
- Supports both raw callables and @ql.compile-decorated functions; compiled predicates get auto-inverse for uncomputation

### Resource Estimation
- 17-qubit limit is a simulation constraint, NOT a circuit construction constraint
- Constructor allows any size tree to be created regardless of qubit count
- Simulation enforcement only: error raised when user tries to simulate a tree exceeding the qubit budget
- `max_qubits` is a configurable parameter (default 17) for future hardware targets
- No separate `num_qubits` property or static estimator — users inspect register attributes if needed

### Module & Naming
- Lives inside `quantum_lib/walk.py` — single file for now (can refactor to sub-package in later phases)
- Main class: `QWalkTree`
- Node state object: `TreeNode`

### Claude's Discretion
- Internal register allocation order and qubit mapping
- TreeNode implementation details (what additional attributes beyond depth/branch_values)
- Predicate validation strategy (how to test mutual exclusion at construction)
- Error message wording for validation failures
- Root state preparation circuit implementation

</decisions>

<specifics>
## Specific Ideas

- Per-level branching list allows different widths at each tree level: `branching=[2,3,2]` means root has 2 children, level-1 has 3 children each, level-2 has 2 children each
- One-hot height register uses max_depth+1 qubits per Montanaro's encoding
- Branch registers are QuantumArrays, one per depth level

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 97-tree-encoding-predicate-interface*
*Context gathered: 2026-02-26*
