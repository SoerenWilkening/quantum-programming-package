# Codebase Concerns

**Analysis Date:** 2026-02-22

---

## Tech Debt

**Duplicate source file: `qint_preprocessed.pyx`:**
- Issue: `src/quantum_language/qint_preprocessed.pyx` is a fully inlined copy of `src/quantum_language/qint.pyx` — the canonical source uses `.pxi` includes, the preprocessed copy has them expanded inline. Both files are 907 and 3282 lines respectively. Any change to the `.pxi` files must also be reflected in the preprocessed variant, and vice versa.
- Files: `src/quantum_language/qint.pyx`, `src/quantum_language/qint_preprocessed.pyx`, `src/quantum_language/qint_arithmetic.pxi`, `src/quantum_language/qint_bitwise.pxi`, `src/quantum_language/qint_comparison.pxi`, `src/quantum_language/qint_division.pxi`
- Impact: Dual-maintenance burden; bugs fixed in one file may not be fixed in the other. The preprocessed variant is the one Cython compiles directly for PyPI-style distribution.
- Fix approach: Automate generation of `qint_preprocessed.pyx` from `qint.pyx` + `.pxi` files via `build_preprocessor.py` (already referenced in comments) as part of the build/CI step, never hand-editing the preprocessed output.

**`QPU.c` / `QPU.h` kept as backward compat stubs:**
- Issue: `c_backend/src/QPU.c` and `c_backend/include/QPU.h` are empty compatibility wrappers with no active code. They add build surface area without functionality.
- Files: `c_backend/src/QPU.c`, `c_backend/include/QPU.h`
- Impact: Confusion for new contributors; slight build overhead.
- Fix approach: Remove files and update all include paths to reference `circuit.h` directly.

**Optimizer uses linear scan where binary search is noted as the improvement:**
- Issue: `c_backend/src/optimizer.c` `smallest_layer_below_comp()` iterates linearly over all occupied layer indices per qubit (marked `// TODO: improve with binary search`).
- Files: `c_backend/src/optimizer.c` line 27
- Impact: Performance degrades on deep circuits with many layers per qubit. The occupied-layer list is kept sorted, so binary search is directly applicable.
- Fix approach: Replace the loop with `bsearch()` or a manual binary search on `circ->occupied_layers_of_qubit[qubit]`.

**105 hardcoded sequence `.c` files in `c_backend/src/sequences/`:**
- Issue: Gate sequences for operations at each integer width (1–16 bits) are pre-generated and stored as individual C files rather than generated at runtime. Adding or modifying sequences requires regenerating and committing new C files.
- Files: `c_backend/src/sequences/` (105 files)
- Impact: Large codebase surface area, regeneration process is manual and undocumented in the repository, risk of drift between generator and stored sequences.
- Fix approach: Document the sequence generator script and add a CI check that regenerated sequences match committed ones.

**`_optimize_gate_list()` in Python with fixed `max_passes=10` limit:**
- Issue: `src/quantum_language/compile.py` `_optimize_gate_list()` runs a Python-level multi-pass optimizer capped at 10 passes with adjacent-only cancellation. It misses non-adjacent cancellations common in deeply nested compiled functions.
- Files: `src/quantum_language/compile.py` lines 150–177
- Impact: Suboptimal gate counts in `@ql.compile`-cached sequences; the C-level `circuit_optimizer` handles full circuit optimization, but compiled replay uses only this Python optimizer.
- Fix approach: Either increase passes dynamically until convergence (no hard cap needed when the list is short) or offload replay optimization to the C-level `run_optimization_pass` path.

**Nested `with`-block control combining is a TODO:**
- Issue: In `qint.__enter__`, when entering a second nested `with` block while already controlled, the comment says `# TODO: and operation of self and qint._control_bool`. The current implementation performs `_control_bool &= self` which creates a new intermediate qint but does not properly uncompute it via `_exit__`.
- Files: `src/quantum_language/qint.pyx` lines 811–814, `src/quantum_language/qint_preprocessed.pyx` lines 811–814
- Impact: Nested conditional `with` blocks (doubly-controlled operations) may leak ancilla qubits and leave `_list_of_controls` in a partially restored state.
- Fix approach: Implement proper `AND`-combination of the two control qubits (using `Q_and`) and ensure the combined qubit is uncomputed in `__exit__` when popping from `_list_of_controls`.

---

## Known Bugs

**`qint_mod * qint_mod` causes C-layer segfault:**
- Symptoms: Multiplying two `qint_mod` instances crashes the Python process with a segfault.
- Files: `src/quantum_language/qint_mod.pyx` lines 262–267
- Trigger: `x = ql.qint_mod(5, N=17); y = ql.qint_mod(3, N=17); z = x * y`
- Workaround: The code raises `NotImplementedError` before reaching the C layer as a guard. Do not remove the guard without fixing the underlying C issue.

**`qarray` element `*=` (in-place multiplication) causes C backend segfault:**
- Symptoms: `arr[i] *= scalar` on a `qarray` crashes the process.
- Files: `tests/test_qarray_mutability.py` line 115 (`pytest.skip` in place)
- Trigger: Calling `__imul__` on a `qarray` element (not a standalone `qint`).
- Workaround: Test is explicitly skipped. Use `arr[i] = arr[i] * scalar` (non-in-place) if possible, but this creates a new qint rather than mutating.

**`qint.measure()` is a simulation placeholder:**
- Symptoms: `qint.measure()` always returns `self.value` (the initialization value), regardless of circuit operations performed on the qint.
- Files: `src/quantum_language/qint.pyx` lines 881–901 (docstring says "Currently returns initialization value (simulation placeholder)")
- Trigger: Calling `.measure()` directly instead of using `ql.grover()` or `to_openqasm()` + Qiskit simulation.
- Workaround: Use `to_openqasm()` followed by Qiskit `AerSimulator` for correct measurement results.

---

## Security Considerations

**`qiskit_aer` is an undeclared runtime dependency:**
- Risk: `grover.py` and `amplitude_estimation.py` do `from qiskit_aer import AerSimulator` at call time, but `qiskit-aer` is not listed in `pyproject.toml` dependencies. Only `qiskit>=1.0` appears under `[project.optional-dependencies].verification`, and `qiskit-aer` is a separate package.
- Files: `src/quantum_language/grover.py` line 260, `src/quantum_language/amplitude_estimation.py` line 184, `pyproject.toml`
- Current mitigation: Import is deferred (inside functions), so installation without `qiskit-aer` only fails at call time.
- Recommendations: Add `qiskit-aer` to the `verification` optional dependency group in `pyproject.toml`. Consider a cleaner `ImportError` with install instructions if the import fails.

**No input validation on circuit pointer casts:**
- Risk: Multiple functions in `src/quantum_language/_core.pyx` cast the circuit pointer via `<circuit_t*><unsigned long long>_get_circuit()`. If `_get_circuit_initialized()` check is bypassed or the pointer is corrupted (e.g., after manual `free_circuit` call), this is an exploitable unsafe cast.
- Files: `src/quantum_language/_core.pyx` (multiple locations), `src/quantum_language/qint.pyx` line 485
- Current mitigation: `_circuit_initialized` guard is present in most but not all paths.
- Recommendations: Audit all sites where the circuit pointer is dereferenced without an initialized check.

---

## Performance Bottlenecks

**O(n) linear scan in `smallest_layer_below_comp` (optimizer hot path):**
- Problem: Every `add_gate()` call (the innermost loop of circuit building) calls `smallest_layer_below_comp` which iterates `O(L)` over layers per qubit where `L` is the number of occupied layers.
- Files: `c_backend/src/optimizer.c` lines 26–38
- Cause: Sequential scan over a sorted array; binary search is noted but not implemented.
- Improvement path: Replace with binary search — the `occupied_layers_of_qubit` array is monotonically sorted, making `bsearch()` a direct drop-in.

**Full circuit rebuild per Grover attempt (BBHT and IQAE):**
- Problem: Each BBHT attempt and each IQAE round calls `circuit()` to create a completely fresh circuit and re-runs the oracle construction from scratch. For oracles with complex compilation, this dominates runtime.
- Files: `src/quantum_language/grover.py` line 329, `src/quantum_language/amplitude_estimation.py` line 369
- Cause: Circuit state is global and non-resettable; circuit objects cannot be rewound, only recreated. Comment: "Fresh circuit for each attempt (required: circuit state not resettable)".
- Improvement path: Add a circuit snapshot/restore mechanism or make `circuit()` reset state without full reallocation. Alternatively, cache the compiled QASM string across iterations and only vary the shot count.

**Python-level `extract_gate_range` / `inject_remapped_gates` for replay:**
- Problem: `compile.py` replay path iterates over Python dictionaries for every gate, performing Python-level qubit remapping. For large compiled functions this is O(G) Python object overhead per replay call.
- Files: `src/quantum_language/_core.pyx` lines 690–838, `src/quantum_language/compile.py` lines 952–1000
- Cause: Gate representation was chosen as `list[dict]` for flexibility; C-level batch injection via `inject_remapped_gates` helps but the Python dict overhead remains.
- Improvement path: Store captured gates as a C `sequence_t` and implement a C-level remap+inject that accepts a qubit mapping array.

---

## Fragile Areas

**Global module-level state in `_core.pyx`:**
- Files: `src/quantum_language/_core.pyx` lines 25–47
- Why fragile: All quantum state (`_circuit`, `_controlled`, `_control_bool`, `_list_of_controls`, `_scope_stack`, `_global_creation_counter`) is module-level Cython global state. Any code that creates a `circuit()` object resets all of this state, invalidating existing `qint` objects that hold qubit indices into the old (freed) circuit. This makes concurrent use or multiple active circuits impossible.
- Safe modification: Always call `circuit()` before creating any `qint`/`qbool` objects. Never hold `qint` references across a `circuit()` call.
- Test coverage: Integration tests assume single-circuit execution; no tests for multi-circuit or re-entrant scenarios.

**`__del__`-based uncomputation (GC-dependent ordering):**
- Files: `src/quantum_language/qint.pyx` lines 727–775
- Why fragile: Automatic uncomputation relies on Python's garbage collector invoking `__del__` in a specific order (LIFO by creation for intermediates). CPython's reference-counting GC usually achieves this, but it is not guaranteed. In PyPy or alternative Python implementations the order may differ, producing incorrect circuit gate sequences.
- Safe modification: Prefer explicit `.uncompute()` calls or `qubit_saving=True` (eager mode) for correctness-critical paths. Test under PyPy before any PyPy support claim.
- Test coverage: Tests run CPython only; GC ordering is not mocked or verified.

**`qint` width hard-limited to 64 bits:**
- Files: `src/quantum_language/qint.pyx` line 197 (`ValueError` if width > 64), `src/quantum_language/qint_preprocessed.pyx` line 256, `c_backend/include/circuit.h` line 103 (`q_address[64]`)
- Why fragile: The 64-element `q_address` array is statically sized in the C struct. Exceeding it would be a buffer overflow; the Python layer enforces the limit but the C layer has no bounds check.
- Safe modification: Do not attempt to increase the width limit without expanding `q_address` and auditing all C code that uses the 64-element assumption (e.g., `qubits[64 - width]` offset pattern throughout `qint.pyx`).

**`qubit_array` global buffer fixed at `4 * 64 + NUMANCILLY` elements:**
- Files: `src/quantum_language/_core.pyx` line 244
- Why fragile: This NumPy array is used as a scratch buffer for multi-argument C backend calls. If any operation requires more than 256 + 128 = 384 qubit slots simultaneously (e.g., deeply nested binary operations on wide qints), it would silently overrun.
- Safe modification: Validate the required slot count before writing into `qubit_array` in the Cython wrappers.

---

## Scaling Limits

**Qiskit simulation hard cap at 17 qubits:**
- Current capacity: Verified working up to 17 total qubits (search register + ancilla overhead).
- Limit: Memory doubles per additional qubit (statevector simulation). At 17 qubits the statevector is 2^17 = 131,072 complex amplitudes ≈ 2 MB; at 20 it would be 16 MB, at 30 it would be 16 GB.
- Scaling path: The grover and IQAE paths warn (but do not enforce) when `total_register_width > 14`. Real hardware or a sparse/tensor-network simulator would be required for larger problems. The project memory notes maximum 17 qubits.

**Thread limit fixed at 4 in `AerSimulator`:**
- Files: `src/quantum_language/grover.py` line 265, `src/quantum_language/amplitude_estimation.py` line 189
- Current: `AerSimulator(max_parallel_threads=4)` is hardcoded in both simulation call sites.
- Limit: Cannot leverage more than 4 CPU threads for simulation even on machines with more cores.
- Scaling path: Make thread count configurable via `ql.option()` or an environment variable.

---

## Dependencies at Risk

**`qiskit-aer` not pinned or declared in `pyproject.toml`:**
- Risk: `qiskit-aer` is imported at runtime but only `qiskit>=1.0` is listed under optional dependencies. A `qiskit-aer` version incompatible with the installed `qiskit` could silently break all simulation.
- Impact: `ql.grover()`, `ql.amplitude_estimate()`, and all end-to-end tests that call Qiskit fail with `ImportError` or runtime errors.
- Migration plan: Add `qiskit-aer>=0.14` to the `verification` optional group in `pyproject.toml`.

**Cython `>=3.0.11,<4.0` build dependency is pinned to a major version range:**
- Files: `pyproject.toml` line 3
- Risk: Cython 4.0 (when released) would break the build constraint. The generated `.c` files committed to the repo would need regeneration.
- Impact: Fresh installs from source fail once Cython 4.0 is released and `pip` selects it.
- Migration plan: Test against Cython 4.0 pre-releases and update the upper bound or pin to a specific known-good version.

---

## Missing Critical Features

**Controlled bitwise AND, OR, XOR not implemented:**
- Problem: Any code inside a `with flag:` block that uses `&`, `|`, `^`, `&=`, `|=`, or `^=` between two `qint` values (or a `qint` and an `int`) raises `NotImplementedError`.
- Files: `src/quantum_language/qint_bitwise.pxi` lines 112, 129, 269, 282, 421, 438, 494, 504
- Blocks: Writing oracle predicates that use bitwise logic inside controlled contexts; Grover oracles for problems requiring bitwise masking under a condition.

**Division with negative divisor not implemented:**
- Problem: `qint // negative_int` and related operations raise `NotImplementedError`.
- Files: `src/quantum_language/qint_division.pxi` lines 61, 187, 290

**`qint_mod * qint_mod` not implemented:**
- Problem: Modular multiplication between two quantum modular integers is blocked at the Python layer. The underlying C code segfaults.
- Files: `src/quantum_language/qint_mod.pyx` lines 262–267

**Multi-dimensional `qarray` assignment not implemented:**
- Problem: Assigning to a row or using slice-based assignment in a 2D `qarray` raises `NotImplementedError`.
- Files: `src/quantum_language/qarray.pyx` lines 255, 267

---

## Test Coverage Gaps

**No tests for nested `with` (doubly-controlled) operations:**
- What's not tested: Two consecutive `with` blocks where the inner block depends on a second condition qubit (the `_list_of_controls` path in `__enter__`).
- Files: `src/quantum_language/qint.pyx` lines 808–814
- Risk: The TODO comment indicates the `_list_of_controls` and `_control_bool &= self` path may not properly uncompute the combined control or restore state on `__exit__`.
- Priority: High — silently incorrect quantum circuits would be generated.

**No tests for qubit limit boundary conditions (width=64):**
- What's not tested: `qint(0, width=64)`, operations at maximum width, overflow behavior at boundary.
- Files: `src/quantum_language/qint.pyx`, `c_backend/include/circuit.h`
- Risk: Off-by-one in the `qubits[64 - width]` offset indexing at maximum width.
- Priority: Medium.

**No tests for circuit reset while live `qint` objects exist:**
- What's not tested: Calling `ql.circuit()` while holding references to existing `qint` objects, which would free the C circuit but leave Python objects with dangling qubit indices.
- Files: `src/quantum_language/_core.pyx` lines 302–323
- Risk: Use-after-free at the C level; Python crash or silent memory corruption.
- Priority: High — this is a likely user mistake with catastrophic consequences.

**No tests for `qiskit-aer` import failure path:**
- What's not tested: Behavior when `qiskit_aer` is not installed but `ql.grover()` or `ql.amplitude_estimate()` is called.
- Files: `src/quantum_language/grover.py` line 260, `src/quantum_language/amplitude_estimation.py` line 184
- Risk: Users get a bare `ModuleNotFoundError` with no guidance.
- Priority: Low — add a friendly `ImportError` wrapper with install instructions.

**C-level allocator tests are not integrated into `pytest`:**
- What's not tested: `tests/c/test_allocator_block.c`, `tests/c/test_reverse_circuit.c` are standalone C executables not invoked by `pytest tests/python/ -v`.
- Files: `tests/c/Makefile`, `tests/c/test_allocator_block.c`, `tests/c/test_reverse_circuit.c`
- Risk: C allocator regressions are invisible in the standard test run.
- Priority: Medium — add a `pytest` plugin step or CI job that compiles and runs `tests/c/Makefile`.

---

*Concerns audit: 2026-02-22*
