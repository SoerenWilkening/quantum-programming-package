# Codebase Concerns

**Analysis Date:** 2026-02-22

## Tech Debt

**Backward compatibility tracking in free_element() is broken by design:**
- Issue: `free_element()` decrements `circ->ancilla` and `circ->used_qubit_indices` by 1 regardless of the qubit width being freed. A comment explicitly acknowledges this is a width-incorrect decrement maintained to avoid behavioral changes during migration.
- Files: `c_backend/src/Integer.c` lines 137-143
- Impact: Legacy `circ->ancilla` and `circ->used_qubit_indices` fields drift incorrect for any multi-qubit free. These fields are legacy (see `c_backend/include/circuit.h` line 85), but any code still reading them gets wrong values.
- Fix approach: Remove the `circ->ancilla` / `circ->used_qubit_indices` fields entirely (already marked `TODO(Phase 5 follow-up)` in `c_backend/src/Integer.c:141`). Replace all callsites with `allocator_get_stats()`.

**INT() and BOOL() classical constructors silently discard their argument:**
- Issue: `INT(int64_t intg)` and `BOOL(bool intg)` both cast the argument with `(void)intg` and include a comment "classical value handling TBD". The classical value passed is never stored.
- Files: `c_backend/src/Integer.c` lines 62-83
- Impact: Any C-layer code that calls `INT(x)` expecting the classical value to be accessible will silently get a zero-value struct. No Python-layer functionality appears to call these directly, but the API surface is misleading.
- Fix approach: Either store the classical value in the struct (requires a union field) or remove the functions and document that classical integers are handled purely at the Python layer.

**Duplicate legacy globals for precompiled sequences:**
- Issue: Both INTEGERSIZE-fixed globals (`precompiled_QQ_add`, `precompiled_cQQ_add`, etc.) and width-parameterized arrays (`precompiled_QQ_add_width[65]`, `precompiled_cQQ_add_width[65]`) co-exist. Legacy globals are documented as "point to INTEGERSIZE versions" but require manual sync.
- Files: `c_backend/src/IntegerAddition.c` lines 8-16, `c_backend/src/IntegerMultiplication.c` lines 6-12, `c_backend/include/arithmetic_ops.h` lines 122-130
- Impact: Memory overhead, confusion about which to use, potential divergence if only one is updated. Code paths that use the legacy globals may silently run the wrong width.
- Fix approach: Remove legacy globals and update all consumers to use `_width[bits]` arrays directly.

**optimizer.c `smallest_layer_below_comp` loop direction is wrong:**
- Issue: The loop `for (int i = last_index; i > 0; ++i)` increments `i` while the condition is `i > 0`. If `last_index > 0`, `i` will grow unboundedly (since incrementing keeps `i > 0`), making this a potential infinite loop. The function also has a `TODO: improve with binary search` comment.
- Files: `c_backend/src/optimizer.c` lines 26-38
- Impact: Potential infinite loop if `smallest_layer_below_comp` is called with a qubit that has occupation history and a `compar` value below the top entry. Currently the gate placement algorithm may short-circuit before reaching this path in common cases.
- Fix approach: Change to `for (int i = last_index - 1; i >= 0; --i)` to scan the occupation list in reverse order as intended, then optionally upgrade to binary search.

**QPU.h/QPU.c kept as dead backward compat shims:**
- Issue: `c_backend/src/QPU.c` contains only comments explaining that global state was removed. `c_backend/include/QPU.h` is described as "backward compatibility header". Both are included by nearly every C source file via `#include "QPU.h"`.
- Files: `c_backend/src/QPU.c`, `c_backend/include/QPU.h`
- Impact: Every compilation unit pays the include cost and risk of future confusion about what QPU.h provides. The files add no functionality.
- Fix approach: Inline any remaining useful content from `QPU.h` into `circuit.h` and delete `QPU.h`/`QPU.c`, updating all includes.

**`@ql.compile` optimizer limited to adjacent gate cancellation only:**
- Issue: `_optimize_gate_list()` in `src/quantum_language/compile.py` only cancels/merges adjacent gates (left-to-right single pass, repeated up to 10 times). Non-adjacent inverse pairs separated by commuting gates are never cancelled.
- Files: `src/quantum_language/compile.py` lines 150-177
- Impact: Compiled function cache stores suboptimal gate counts for circuits with interleaved commuting operations. The `max_passes=10` cap is an arbitrary safety limit.
- Fix approach: Implement commutation-aware optimization (track qubit dependencies to determine commutativity before attempting reorder). Medium priority since the C-layer optimizer already handles adjacent cancellation at the circuit level.

## Known Bugs

**`free_element()` width-incorrect legacy counter decrement:**
- Symptoms: `circ->ancilla` and `circ->used_qubit_indices` become negative or undercount when freeing multi-qubit integers.
- Files: `c_backend/src/Integer.c` lines 137-143
- Trigger: Calling `free_element(circ, el)` on any `quantum_int_t` with `width > 1`.
- Workaround: Use `allocator_get_stats(circ->allocator)` for authoritative qubit counts; do not rely on legacy fields.

**`smallest_layer_below_comp` loop is an infinite loop for qubits with occupation history:**
- Symptoms: Process hangs during gate placement for circuits where qubit occupation history is non-empty and `compar` is not the maximum layer.
- Files: `c_backend/src/optimizer.c` lines 32-36
- Trigger: Gate added to a circuit where the target/control qubit has been used in a prior layer and a lower-bound search is performed (e.g., circuit with gate merge/cancellation activity).
- Workaround: The function currently appears to mostly short-circuit before this path in practice. The safest mitigation is to apply the loop direction fix immediately.

**BUG-03 fixed but fix comments remain as noise:**
- Symptoms: Four `// FIX BUG-03: Control qubit reversal` comments remain in production code, making intent of the current code ambiguous to auditors.
- Files: `c_backend/src/IntegerMultiplication.c` lines 33, 50, 60, 130, 356
- Trigger: Code review or auditing.
- Workaround: Comments are purely cosmetic; the logic is now correct.

## Security Considerations

**No input validation on Qiskit simulation qubit counts:**
- Risk: `_simulate_single_shot()` and `_simulate_multi_shot()` run whatever QASM is passed without checking that the total qubit count stays under the known 17-qubit hardware constraint before submitting to `AerSimulator`.
- Files: `src/quantum_language/grover.py` lines 260-269, `src/quantum_language/amplitude_estimation.py` lines 184-191
- Current mitigation: Tests are manually constrained to small widths; the project memory documents the limit (`max qubits for Qiskit simulation: 17`). No runtime guard exists.
- Recommendations: Add a pre-flight qubit count check in `_simulate_single_shot` and `_simulate_multi_shot` that raises a clear `ValueError` if the circuit exceeds 17 qubits.

**No bounds check before `qubit_indices[MAXQUBITS]` array access:**
- Risk: `circuit_t` contains a fixed-size legacy array `qubit_t qubit_indices[MAXQUBITS]` (8000 elements) and a pointer `ancilla = &qubit_indices[0]`. Any write through the pointer above index 7999 is a buffer overflow.
- Files: `c_backend/include/circuit.h` line 86, `c_backend/src/circuit_allocations.c` lines 187-191
- Current mitigation: The new `qubit_allocator_t` enforces `ALLOCATOR_MAX_QUBITS=8192` with an explicit check. The legacy array is only initialized at `init_circuit()` and not written to afterwards in primary code paths.
- Recommendations: Remove the `qubit_indices[MAXQUBITS]` field and the `ancilla` pointer entirely as part of the legacy cleanup.

## Performance Bottlenecks

**`smallest_layer_below_comp` uses linear scan, documented as needing binary search:**
- Problem: Layer placement for every gate requires a linear scan of all occupied layers for each qubit touched by the gate. For circuits with many layers this is O(N) per qubit per gate addition.
- Files: `c_backend/src/optimizer.c` lines 26-38
- Cause: Occupied layers are stored as a sorted array but searched linearly. The `TODO: improve with binary search` comment is present.
- Improvement path: Replace linear scan with manual binary search. The array is already sorted ascending so binary search directly applies once the loop direction bug is fixed.

**Massive generated sequence files (~353k lines of C) compiled from scratch:**
- Problem: The `c_backend/src/sequences/` directory contains over 100 hand-generated C files, the largest being `toffoli_clifft_cla_cqq_8.c` at 23,631 lines. These are compiled as part of the main build.
- Files: `c_backend/src/sequences/` (entire directory, ~353,841 lines total across all sequence files)
- Cause: Gate sequences for each integer width (1-8) and operation variant are pre-expanded into static C arrays. This is intentional for runtime speed but causes very long compile times.
- Improvement path: Compile sequences as a separate static library that is cached and only rebuilt when scripts in `scripts/` regenerate them.

**Qiskit simulation is the only execution backend; no lightweight alternative:**
- Problem: `ql.grover()` and `ql.amplitude_estimate()` require Qiskit as the simulation backend. Every end-to-end test requires spawning an `AerSimulator` instance including Qiskit's full import chain.
- Files: `src/quantum_language/grover.py` lines 258-269, `src/quantum_language/amplitude_estimation.py` lines 182-191, `pyproject.toml` line 24
- Cause: Simulation is listed as an optional dependency (`verification = ["qiskit>=1.0"]`) but without it the main user-facing APIs cannot produce results.
- Improvement path: Integrate a lightweight numpy-based statevector simulator for small circuits to allow testing without the full Qiskit stack.

## Fragile Areas

**`@ql.compile` cache keying and invalidation:**
- Files: `src/quantum_language/compile.py` (`CompiledBlock`, `_clear_all_caches`), `src/quantum_language/oracle.py` (`_predicate_oracle_cache`)
- Why fragile: Cache clearing is triggered by `ql.circuit()` via a global hook (`_register_cache_clear_hook`). The registry uses weak references, so if a `CompiledFunc` is garbage collected, its cache entry silently disappears. If the user reuses a `CompiledFunc` across circuits with different arithmetic modes without calling `ql.circuit()`, the wrong cached sequence may be replayed.
- Safe modification: Always call `ql.circuit()` between circuit builds; when adding new circuit-global options, update `_clear_all_caches` to reset them.
- Test coverage: `tests/python/test_cython_optimization.py` covers cache replay. Arithmetic-mode cache invalidation is verified in `tests/python/test_cross_backend.py`.

**Grover BBHT search does not enforce the 17-qubit limit at runtime:**
- Files: `src/quantum_language/grover.py` (`_bbht_search`, `_run_grover_attempt`)
- Why fragile: BBHT search builds circuits inside a retry loop. Each attempt calls `circuit()` (resetting state), clearing all caches. If an oracle causes qubit count to exceed 17, the Aer simulator will fail or OOM mid-loop rather than failing cleanly with a useful message.
- Safe modification: Add a qubit count assertion after `to_openqasm()` and before `_simulate_single_shot()` to surface this early.
- Test coverage: All Grover integration tests are manually constrained to small widths; no test exists for the over-budget case.

**`ancilla` field pointer in `circuit_t` aliases `qubit_indices` array:**
- Files: `c_backend/include/circuit.h` lines 85-88, `c_backend/src/circuit_allocations.c` line 191
- Why fragile: `circ->ancilla = &circ->qubit_indices[0]` creates an internal alias. Any code that writes through `circ->ancilla` modifies the `qubit_indices` array at potentially unbounded offsets. The `qubit_allocator_t` system does not know about this pointer.
- Safe modification: Do not use or pass `circ->ancilla` to new code. Only use `allocator_alloc()` / `allocator_free()`.
- Test coverage: `tests/c/test_allocator_block.c` covers the allocator but does not test the legacy pointer behavior.

**`execution.c run_instruction` ownership of `large_control` arrays relies on implicit convention:**
- Files: `c_backend/src/execution.c` lines 31-68, `c_backend/src/circuit_allocations.c` `free_circuit` lines 202-211
- Why fragile: When `run_instruction` maps an n-controlled gate, it `malloc`s a new `large_control` array. The comment says "The circuit takes ownership via memcpy in append_gate." However, `append_gate` does `memcpy(&circ->sequence[...][pos], g, sizeof(gate_t))` which copies the pointer value, not the pointed-to heap memory. If any caller mistakenly frees `g.large_control` before `free_circuit`, it creates a dangling pointer. The correctness constraint is invisible to future callers.
- Safe modification: Add explicit ownership documentation to `append_gate`. Consider a deep-copy helper that copies `large_control` data to avoid implicit ownership transfer.
- Test coverage: `tests/c/test_reverse_circuit.c` exercises this path for n-controlled gates.

**Oracle uncomputation validation is opt-in and bypassed for lambda oracles:**
- Files: `src/quantum_language/oracle.py` (`GroverOracle.__init__`, `_ensure_oracle`)
- Why fragile: `_ensure_oracle()` passes `validate=False` when auto-wrapping lambdas, disabling compute-phase-uncompute validation. User-written oracles wrapped via `grover_oracle(oracle, validate=False)` skip validation entirely, so ancilla leaks or incomplete uncomputation would not be caught.
- Safe modification: When possible, use `validate=True` and fix the false-positive root cause (distinguish oracle-internal phase gates from search-register phase marking at the gate-list analysis level).
- Test coverage: `tests/python/test_oracle.py` covers the validated path; lambda-wrapped paths are tested in `tests/python/test_grover_predicate.py`.

## Scaling Limits

**Hard qubit limit of 17 for Qiskit simulation enforced by convention only:**
- Current capacity: Up to 17 qubits produce tractable statevector simulation on the development machine (~8 GB RAM).
- Limit: Beyond 17 qubits the simulator requires >8 GB RAM and exceeds the thread constraint (`max_parallel_threads=4`).
- Scaling path: Use matrix product state (MPS) simulation for shallower circuits (already used in `tests/test_div.py` and `tests/test_toffoli_division.py`). Add runtime guard to warn or error above 17 qubits.

**`MAXLAYERINSEQUENCE = 10000` hard-codes maximum sequence depth:**
- Current capacity: Pre-computed sequences can have at most 10,000 layers (defined in `c_backend/include/types.h`).
- Limit: Larger width operations generating sequences programmatically could exceed this.
- Scaling path: Replace the constant with a dynamically grown array in `sequence_t` matching the dynamic growth pattern already used in `circuit_t`.

## Dependencies at Risk

**Qiskit is a verification-only optional dependency but required for all end-to-end results:**
- Risk: Qiskit's API (`qiskit.qasm3.loads`, `AerSimulator`) is external and subject to breaking changes. The project pins only `qiskit>=1.0` with no upper bound.
- Files: `pyproject.toml` line 24 (`verification = ["qiskit>=1.0"]`), `src/quantum_language/grover.py` lines 258-269, `src/quantum_language/amplitude_estimation.py` lines 182-191
- Impact: A Qiskit minor release breaking the QASM3 loader or `AerSimulator` interface would silently break all integration tests and end-to-end user workflows.
- Migration plan: Pin an upper bound (e.g., `qiskit>=1.0,<2.0`). Add an adapter layer that isolates Qiskit-specific API calls behind a thin interface.

## Missing Critical Features

**No runtime qubit budget guard before simulation:**
- Problem: There is no code path that checks total circuit qubit count before calling `AerSimulator`. Users who build circuits exceeding 17 qubits get an opaque simulator crash or memory exhaustion rather than a clear error.
- Blocks: Safe use of Grover / IQAE with larger registers without deep knowledge of the constraint documented only in project memory.

**`INT()` and `BOOL()` do not store the classical value:**
- Problem: C-layer classical integer/boolean constructors silently discard the value argument. Any future C-layer code that needs to use classical values in gate sequences has no mechanism to retrieve the classical value from the struct.
- Files: `c_backend/src/Integer.c` lines 62-83
- Blocks: Implementing C-layer classical-controlled operations that depend on the classical operand value.

## Test Coverage Gaps

**The `smallest_layer_below_comp` loop bug is not regression-tested:**
- What is not tested: The loop `for (int i = last_index; i > 0; ++i)` in `optimizer.c` increments rather than decrements `i`. There are no tests that exercise this function with a qubit that has occupation history and a `compar` value below the top entry (seeking the highest layer below a threshold).
- Files: `c_backend/src/optimizer.c` lines 26-38
- Risk: Infinite loop at runtime for complex circuits where this search function is actually needed.
- Priority: High — the loop direction is wrong and the function is part of the critical gate placement path.

**Legacy `circ->ancilla` / `circ->qubit_indices` pointer aliasing is not tested:**
- What is not tested: No test verifies that the pointer aliasing in `circuit_t` (`ancilla = &qubit_indices[0]`) does not corrupt data when used alongside the new `qubit_allocator_t`.
- Files: `c_backend/src/circuit_allocations.c` line 191, `c_backend/include/circuit.h` lines 85-88
- Risk: Silent memory corruption if any remaining code path writes through `circ->ancilla`.
- Priority: Medium — mitigated by the allocator being the sole allocation mechanism in new code.

**No test covers `amplitude_estimate()` with more than ~10 total qubits:**
- What is not tested: IQAE with wider registers (4-5 bits, requiring 10-17 qubits including ancilla). All existing integration tests use 2-3 bit registers.
- Files: `tests/python/test_amplitude_estimation.py`
- Risk: Precision-at-scale behavior is untested; algorithm may produce poor estimates or silently exceed qubit budget for wider inputs.
- Priority: Medium — bounded by the 17-qubit simulation constraint.

**C-level tests in `tests/c/` are not wired into the pytest suite:**
- What is not tested: `test_comparison.c`, `test_hot_path_add.c`, `test_hot_path_mul.c`, `test_hot_path_xor.c`, and `test_reverse_circuit.c` are compiled C executables not run by `pytest tests/python/ -v`.
- Files: `tests/c/test_comparison.c`, `tests/c/test_hot_path_add.c`, `tests/c/test_hot_path_mul.c`, `tests/c/test_hot_path_xor.c`, `tests/c/test_reverse_circuit.c`
- Risk: C-level regressions could go undetected if the C tests are not run manually as a separate step.
- Priority: Low — existing Python verification tests provide substantial coverage of the same operations via the Cython bindings.

---

*Concerns audit: 2026-02-22*
