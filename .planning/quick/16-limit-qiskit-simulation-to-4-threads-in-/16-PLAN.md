---
phase: 16-limit-qiskit-threads
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_bitwise_mixed.py
  - tests/test_modular.py
  - tests/test_cla_addition.py
  - tests/test_copy.py
  - tests/test_toffoli_division.py
  - tests/test_mul_addsub.py
  - tests/test_hardcoded_sequences.py
  - tests/test_copy_binops.py
  - tests/test_compare_preservation.py
  - tests/test_toffoli_cq_reduction.py
  - tests/test_toffoli_addition.py
  - tests/test_toffoli_multiplication.py
  - tests/test_div.py
  - tests/test_array_verify.py
  - tests/test_uncomputation.py
  - tests/test_toffoli_hardcoded.py
  - tests/test_mod.py
  - tests/python/test_cross_backend.py
  - tests/python/test_oracle.py
  - tests/python/test_cla_verification.py
  - tests/python/test_branch_superposition.py
  - tests/python/test_cla_bk_algorithm.py
  - tests/python/test_diffusion.py
  - scripts/verify_circuit.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Every AerSimulator instantiation uses at most 4 threads"
    - "All existing tests still pass with the thread limit applied"
  artifacts:
    - path: "tests/conftest.py"
      provides: "Thread-limited AerSimulator in verify_circuit fixture"
      contains: "max_parallel_threads=4"
    - path: "scripts/verify_circuit.py"
      provides: "Thread-limited AerSimulator in verification script"
      contains: "max_parallel_threads=4"
  key_links:
    - from: "all test files"
      to: "AerSimulator()"
      via: "max_parallel_threads=4 kwarg"
      pattern: "AerSimulator\\(.*max_parallel_threads=4"
---

<objective>
Limit all Qiskit AerSimulator instantiations to 4 threads across the entire codebase.

Purpose: Prevent Qiskit simulations from consuming all available CPU threads, which can slow down the system and cause resource contention during test runs and CI.

Output: Every `AerSimulator(...)` call in all test files and scripts includes `max_parallel_threads=4`.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@tests/conftest.py
@scripts/verify_circuit.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add max_parallel_threads=4 to all AerSimulator instantiations</name>
  <files>
    tests/conftest.py
    tests/test_bitwise_mixed.py
    tests/test_modular.py
    tests/test_cla_addition.py
    tests/test_copy.py
    tests/test_toffoli_division.py
    tests/test_mul_addsub.py
    tests/test_hardcoded_sequences.py
    tests/test_copy_binops.py
    tests/test_compare_preservation.py
    tests/test_toffoli_cq_reduction.py
    tests/test_toffoli_addition.py
    tests/test_toffoli_multiplication.py
    tests/test_div.py
    tests/test_array_verify.py
    tests/test_uncomputation.py
    tests/test_toffoli_hardcoded.py
    tests/test_mod.py
    tests/python/test_cross_backend.py
    tests/python/test_oracle.py
    tests/python/test_cla_verification.py
    tests/python/test_branch_superposition.py
    tests/python/test_cla_bk_algorithm.py
    tests/python/test_diffusion.py
    scripts/verify_circuit.py
  </files>
  <action>
    Find every `AerSimulator(...)` call in the codebase and add `max_parallel_threads=4` as a keyword argument. There are three patterns to handle:

    1. **No arguments:** `AerSimulator()` becomes `AerSimulator(max_parallel_threads=4)`

    2. **With method argument:** `AerSimulator(method="statevector")` becomes `AerSimulator(method="statevector", max_parallel_threads=4)` (same for `method="matrix_product_state"`)

    3. **String-template AerSimulator in scripts/verify_circuit.py:** The `run_test_in_subprocess` function at line ~684 constructs `AerSimulator(method='statevector')` as a Python string literal inside `script_suffix`. Update that string to include `max_parallel_threads=4`.

    Complete list of files and line references (use grep to verify exact lines before editing):

    - `tests/conftest.py` line 106: `AerSimulator(method="statevector")`
    - `tests/test_bitwise_mixed.py` line 255: `AerSimulator(method="statevector")`
    - `tests/test_modular.py` line 47: `AerSimulator(method="statevector")`
    - `tests/test_cla_addition.py` line 39: `AerSimulator(method="statevector")`
    - `tests/test_copy.py` line 177: `AerSimulator(method="statevector")`
    - `tests/test_toffoli_division.py` line 132: `AerSimulator(method="matrix_product_state")`
    - `tests/test_mul_addsub.py` line 39: `AerSimulator(method="statevector")`
    - `tests/test_hardcoded_sequences.py` line 383: `AerSimulator(method="statevector")`
    - `tests/test_copy_binops.py` lines 195, 234: `AerSimulator(method="statevector")`
    - `tests/test_compare_preservation.py` line 73: `AerSimulator(method="statevector")`
    - `tests/test_toffoli_cq_reduction.py` line 46: `AerSimulator(method="statevector")`
    - `tests/test_toffoli_addition.py` line 47: `AerSimulator(method="statevector")`
    - `tests/test_toffoli_multiplication.py` line 63: `AerSimulator(method="statevector")`
    - `tests/test_div.py` line 60: `AerSimulator(method="matrix_product_state")`
    - `tests/test_array_verify.py` line 66: `AerSimulator(method="statevector")`
    - `tests/test_uncomputation.py` line 67: `AerSimulator(method="statevector")`
    - `tests/test_toffoli_hardcoded.py` line 40: `AerSimulator(method="statevector")`
    - `tests/test_mod.py` line 60: `AerSimulator(method="matrix_product_state")`
    - `tests/python/test_cross_backend.py` lines 181, 183: `AerSimulator(method="matrix_product_state")` and `AerSimulator(method="statevector")`
    - `tests/python/test_oracle.py` lines 31, 810: `AerSimulator()`
    - `tests/python/test_cla_verification.py` lines 66, 575, 644, 792: `AerSimulator(method="statevector")`
    - `tests/python/test_branch_superposition.py` line 40: `AerSimulator()`
    - `tests/python/test_cla_bk_algorithm.py` lines 56, 72, 459, 519: various `AerSimulator(method=...)` and inline `.run()` chains
    - `tests/python/test_diffusion.py` lines 31, 40: `AerSimulator(method="statevector")` and `AerSimulator()`
    - `scripts/verify_circuit.py` line 684: string template containing `AerSimulator(method='statevector')`

    Do NOT modify any files in `.planning/`, `circuit-gen-results/`, or other non-source directories. Only modify actual Python source/test/script files.
  </action>
  <verify>
    Run: `grep -rn "AerSimulator(" tests/ scripts/verify_circuit.py --include="*.py" | grep -v "max_parallel_threads"` -- should return zero results (every AerSimulator call has the thread limit).
    Then run: `grep -rn "max_parallel_threads=4" tests/ scripts/verify_circuit.py --include="*.py" | wc -l` -- should return 34 (matching total AerSimulator instances).
    Then run: `pytest tests/python/ -v --timeout=120` to confirm tests still pass.
  </verify>
  <done>Every AerSimulator instantiation in tests/ and scripts/verify_circuit.py includes max_parallel_threads=4. No AerSimulator call exists without the thread limit. Tests pass.</done>
</task>

</tasks>

<verification>
1. `grep -rn "AerSimulator(" tests/ scripts/ --include="*.py" | grep -v max_parallel_threads` returns empty (no ungated instances)
2. `grep -rn "max_parallel_threads=4" tests/ scripts/ --include="*.py"` shows all 34 instances
3. `pytest tests/python/ -v` passes
</verification>

<success_criteria>
- Zero AerSimulator instantiations without max_parallel_threads=4 in tests/ and scripts/
- All existing tests pass with the thread limit
</success_criteria>

<output>
After completion, create `.planning/quick/16-limit-qiskit-simulation-to-4-threads-in-/16-SUMMARY.md`
</output>
