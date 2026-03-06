# Phase 110: Merge Verification & Regression - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove that merged circuits (opt=2) produce correct results via Qiskit statevector simulation, and verify the full compile test suite passes at all optimization levels (opt=1, opt=2, opt=3). Covers requirement MERGE-04.

</domain>

<decisions>
## Implementation Decisions

### Equivalence test workloads
- Verify add, mul, and grover oracle workloads (matches success criteria exactly)
- Exhaustive testing at small widths (1-4) for add and mul, all input pairs within 17-qubit budget
- Grover oracle uses lambda predicate (e.g., `x == target`) to test full compile+merge pipeline
- Compare opt=2 output against opt=3 (full expansion) -- proves merge doesn't change behavior
- No need to compute expected results independently since opt=3 is already verified

### Statevector comparison method
- Use statevector simulation for exact equivalence (no shot-based noise)
- Compare full state vectors (all qubit amplitudes, not just output qubits) to catch any corruption including ancilla state
- Ignore global phase differences -- normalize by aligning phase of first non-zero amplitude (physically equivalent circuits can differ by global phase)
- Tolerance: np.allclose with atol=1e-10 for floating-point accumulation in deep circuits

### Multi-opt regression strategy
- Parametrize all compile tests (test_compile.py, test_merge.py) with pytest fixture to run at opt=1, opt=2, opt=3
- All ~106 existing compile tests run at each opt level (~320 test runs total)
- Pre-existing 14-15 xfail tests remain xfail at all opt levels -- no new failures = pass
- Non-compile tests (arithmetic, comparison, etc.) not parametrized -- they don't use @ql.compile so opt level is irrelevant

### Parametric + opt level interaction
- Explicit tests for all three paths:
  - parametric=True + opt=1: should work with DAG (verify with 3-4 classical parameter values)
  - parametric=True + opt=3: should work, backward compat (verify with 3-4 classical parameter values)
  - parametric=True + opt=2: should raise ValueError (Phase 109 decision)
- Parametric verification confirms output correctness only -- topology may legitimately differ between opt levels

### Claude's Discretion
- How to implement the opt-level pytest fixture (conftest parametrize vs per-test decorator)
- Statevector extraction approach (Qiskit Statevector class vs AerSimulator statevector method)
- How to structure the equivalence test file (single file vs split by workload)
- Which specific grover oracle predicate and search space size to use within 17-qubit budget

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sim_backend.py` (`src/quantum_language/sim_backend.py`): `load_qasm()` + `simulate()` with AerSimulator, lazy imports, max_parallel_threads=4
- `test_cross_backend.py`: Established pattern for exhaustive verification with `generate_exhaustive_pairs()` / `generate_sampled_pairs()` from `verify_helpers`
- `test_merge.py`: 29 existing merge tests covering merge_groups, _merge_and_optimize, opt=2 integration
- `test_compile.py`: 106+ compile tests -- target for opt-level parametrization

### Established Patterns
- Cross-backend testing: exhaustive small widths, sampled large widths
- AerSimulator with `max_parallel_threads=4` and max 17 qubits
- xfail markers for known pre-existing failures
- `ql.option('fault_tolerant', True/False)` for backend switching

### Integration Points
- `@ql.compile(opt=N)` parameter controls optimization level
- `ql.to_openqasm()` for QASM export -> Qiskit simulation
- `sim_backend.load_qasm()` + `sim_backend.simulate()` for simulation pipeline

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 110-merge-verification-regression*
*Context gathered: 2026-03-06*
