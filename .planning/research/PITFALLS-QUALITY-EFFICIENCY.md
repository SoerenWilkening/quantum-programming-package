# Pitfalls Research: Quality & Efficiency Improvements (v4.1)

**Domain:** Bug fixes, tech debt cleanup, security hardening, performance optimization, binary size reduction, and test coverage for a large quantum circuit framework (C/Cython/Python, ~1.06M LOC)
**Researched:** 2026-02-22
**Confidence:** HIGH (based on codebase analysis + domain research + project history)

## Critical Pitfalls

### Pitfall 1: Quantum Arithmetic Bug Fixes Introducing New Correctness Regressions

**What goes wrong:**
Fixing one quantum arithmetic bug (e.g., BUG-WIDTH-ADD, BUG-QFT-DIV) silently breaks a previously-working operation at a different width or under a different control context. This is the most dangerous pitfall in v4.1 because the 7 carry-forward bugs all touch shared code paths in the C backend (IntegerAddition.c, IntegerComparison.c, ToffoliAdditionCDKM.c). A fix to QFT rotation angles for mixed-width addition could break same-width addition. A fix to division's MSB comparison leak could break the comparison operator used by Grover oracles. The project history confirms this pattern: v1.5 fixed subtraction underflow but the fix required changes that triggered BUG-CMP-01 (eq/ne inversion) found in v1.6. The v1.8 uncomputation regression was caused by a seemingly unrelated change to layer tracking.

**Why it happens:**
Quantum arithmetic operations compose: addition is used inside multiplication, multiplication inside division, comparisons inside conditionals. The C backend's `sequence_t` cache means a fix to `CQ_add` affects every operation that internally calls `CQ_add`. The qubit index mapping (`qubits[64 - width]` offset pattern) creates a non-obvious coupling between the Python layer's right-aligned addressing and the C backend's MSB-first processing. Additionally, controlled variants (cQQ, cCQ) share code with uncontrolled variants (QQ, CQ) via a control qubit parameter, so a fix targeting the uncontrolled path can break the controlled path if the fix assumptions differ.

**How to avoid:**
1. Fix one bug at a time, never batch arithmetic bug fixes into a single commit.
2. Run the full exhaustive verification suite (`tests/test_add.py`, `test_sub.py`, `test_mul.py`, `test_div.py`, `test_mod.py`, `test_compare.py`, `test_bitwise.py`) after each fix -- not just the tests for the operation being fixed.
3. Run cross-backend verification (`tests/python/test_cross_backend.py`) to confirm Toffoli/QFT equivalence is preserved.
4. For each bug fix, write the regression test BEFORE writing the fix (test must fail before, pass after).
5. Check all four variants (QQ, CQ, cQQ, cCQ) whenever modifying addition/subtraction code, even if the bug is only in one variant.

**Warning signs:**
- New xfail markers appearing in test runs that were not there before the fix.
- A fix that changes rotation angle formulas, qubit index calculations, or layer count constants.
- Test suite passes but total gate count or circuit depth changes unexpectedly for unrelated operations (monitor via `ql.stats()`).

**Phase to address:**
Bug fix phase (should be the first phase of v4.1). Each bug fix should be its own sub-phase with a verification gate.

---

### Pitfall 2: Dead Code Removal Breaking the Build or Silently Removing Live Code

**What goes wrong:**
Removing "dead" C files like `QPU.c`/`QPU.h`, unused stub functions in `IntegerComparison.c`, or Kogge-Stone CLA stubs from `ToffoliAdditionCLA.c` breaks compilation because another file has a transitive `#include` dependency. Worse: removing a function that appears unused but is actually called via function pointer, conditional compilation, or is a Cython `cdef extern` declaration causes a linker error or runtime crash. In this codebase, the risk is amplified because `setup.py` links ALL C sources into EVERY Cython extension module (each `.pyx` gets all ~120 C files). Removing a C file from `c_sources` in `setup.py` breaks all 7 extension modules simultaneously.

**Why it happens:**
- The C backend has no dependency graph enforcement -- `circuit.h` is a mega-include that pulls in everything.
- Cython `.pxd` files declare `cdef extern` for C functions. If a C function is removed but the `.pxd` declaration remains, the Cython module compiles but fails to link.
- The `qint_preprocessed.pyx` dual-maintenance problem means dead code in `qint.pyx` might still be "alive" in the preprocessed version, or vice versa.
- Stubs that return NULL (like KS CLA stubs) are intentionally called by dispatch functions that fall through to RCA on NULL -- removing the stub makes the dispatch function call a missing symbol.

**How to avoid:**
1. Before removing any C function, `grep` across all `.pxd`, `.pyx`, `.c`, `.h`, and `setup.py` files for references. The search must include both the function name and any aliased `cdef extern` declarations.
2. Remove one function or file at a time, rebuild (`python setup.py build_ext --inplace`), and run `pytest tests/python/ -v` before removing the next item.
3. For QPU.c/QPU.h removal: first verify that `QPU.h` is not included by any file other than `QPU.c` itself. Currently `optimizer.c` includes `QPU.h` (line 12), so `QPU.h` references must be replaced with `circuit.h` first.
4. For KS CLA stubs: do NOT remove them. They are intentionally called by the dispatch layer (`ToffoliAdditionCLA.c` lines 395-409) and must return NULL for the fallback to RCA to work.
5. Automate the `build_preprocessor.py` run as part of any dead code removal to ensure `qint_preprocessed.pyx` stays in sync.

**Warning signs:**
- Linker errors mentioning `undefined symbol` after removing a function.
- Import errors (`ImportError: ... undefined symbol`) at Python `import quantum_language` time.
- Build succeeds but `import quantum_language` crashes immediately (function pointer to removed function).

**Phase to address:**
Tech debt cleanup phase. Must come AFTER bug fixes (which may touch the same files) and BEFORE binary size reduction (which depends on knowing what is truly dead).

---

### Pitfall 3: Bounds Checking at the C/Cython Boundary Masking Real Bugs or Degrading Hot Paths

**What goes wrong:**
Adding bounds checks to `qubit_array` access (the 384-element scratch buffer in `_core.pyx`) and `circuit_t` pointer validation slows down the critical hot path: every `add_gate()` call goes through `run_instruction()` which indexes into `qubit_array`. If bounds checks are added naively (Python-level `if` checks in Cython), the overhead compounds across thousands of gates. Alternatively, adding C-level `assert()` statements provides zero protection in release builds (`-O3` strips asserts) and false safety in debug builds. The existing `@cython.boundscheck(False)` and `@cython.wraparound(False)` decorators on hot-path functions (qint_arithmetic.pxi lines 5-6, qint_bitwise.pxi lines 5-6) were intentionally disabled for performance -- re-enabling them globally would regress the 27.7% performance improvement achieved in v2.2.

**Why it happens:**
- The `qubit_array` buffer size (4*64 + NUMANCILLY = 384) is computed at module init and never validated against actual usage. It is theoretically possible for deeply nested operations on wide qints to exceed 384 slots.
- Circuit pointer validation is skipped on many paths because `_get_circuit()` returns an `unsigned long long` that is cast to `circuit_t*` without NULL check.
- The temptation is to add checks everywhere "just in case," but in a circuit builder that adds millions of gates, even a 1% overhead per gate compounds into significant regression.

**How to avoid:**
1. Add bounds validation ONLY at entry points (Python API surface), not in inner loops. Validate `qubit_array` slot count when preparing arguments in the Cython wrapper (e.g., `addition_inplace`), before entering the `with nogil:` block. This is a one-time check per operation, not per gate.
2. For circuit pointer validation: add a single check in `_get_circuit()` that raises `RuntimeError("No active circuit -- call ql.circuit() first")` if `_circuit_initialized` is False. This is called once per operation and already has a function-call overhead.
3. Do NOT re-enable `@cython.boundscheck(True)` on hot-path functions. Instead, use the `CYTHON_DEBUG=1` environment variable (already supported in `setup.py`) for debug builds that enable all checks.
4. For the `qubit_array` buffer: compute the maximum slot index needed before writing, and raise `ValueError` if it exceeds 384. This is an O(1) comparison, not O(n) bounds checking.
5. Use AddressSanitizer (`make asan-test`) for development-time detection of buffer overflows rather than runtime bounds checks in production.

**Warning signs:**
- Benchmark regression >15% on circuit generation for QFT addition (the established regression threshold from v2.3).
- `_get_circuit()` being called inside tight loops (should be hoisted outside loops).
- New `if` statements inside `with nogil:` blocks (illegal in Cython -- would cause a compilation error, but the attempt indicates misplaced validation).

**Phase to address:**
Security/fragility hardening phase. Should run after bug fixes and after performance optimization (to avoid undermining the optimizer improvements).

---

### Pitfall 4: Circuit Optimizer Refactoring Breaking Gate Ordering Semantics

**What goes wrong:**
Replacing the linear scan in `smallest_layer_below_comp()` with binary search changes the layer assignment for gates in edge cases where multiple layers have the same occupancy. The current O(n) scan returns the LAST valid layer (scanning from `last_index` downward), while a naive binary search might return ANY valid layer. If the replacement changes which layer a gate is assigned to, it alters circuit depth, which changes gate ordering, which changes the quantum circuit's behavior for operations that are not commutative. Additionally, the Python-level `_optimize_gate_list()` in `compile.py` (max_passes=10) might interact differently with a circuit whose layer structure has changed.

**Why it happens:**
- The optimizer is the most-called C function in the entire codebase (one call per gate). Any behavioral change propagates to every circuit.
- The comment says `// TODO: improve with binary search // maybe not necessary` -- the original author was uncertain whether this optimization matters.
- `smallest_layer_below_comp` has a subtle bug: the loop `for (int i = last_index; i > 0; ++i)` (optimizer.c line 32) increments `i` when it should decrement. This appears to be an off-by-one or direction error that happens to work because `last_index` is typically small. A "correct" binary search would expose this latent bug.

**How to avoid:**
1. Before refactoring, capture golden-master circuit snapshots for representative operations (add, mul, div at widths 2, 4, 8). Compare gate-by-gate output after the refactoring.
2. Implement the binary search as a SEPARATE function alongside the linear scan. Run both and assert identical results across the full test suite before replacing the old one.
3. If the existing loop has a bug (the `++i` vs `--i` issue), fix that bug FIRST in a separate commit with its own test, THEN optimize for binary search.
4. Benchmark the change with `pytest-benchmark` on the `tests/benchmarks/` infrastructure before and after, specifically measuring circuit generation time for operations at widths 8, 16, and 32.

**Warning signs:**
- Circuit depth changes for the same operation (e.g., 4-bit QFT addition was depth 12, now depth 13).
- Characterization tests in `test_qint_operations.py` fail even though correctness tests pass (different gate ordering, same final unitary but different layout).
- Optimizer binary search "improvement" actually makes things slower because the occupied-layer lists are small (typically <20 entries) and linear scan with branch prediction is faster.

**Phase to address:**
Performance optimization phase. Should be preceded by a measurement phase that profiles whether the optimizer scan is actually a bottleneck for the current workload.

---

### Pitfall 5: Binary Size Reduction Breaking Hardcoded Sequence Dispatch

**What goes wrong:**
The 15.3MB `.so` file includes ~120 hardcoded sequence C files. Removing sequence files to reduce binary size breaks the dispatch functions (`add_seq_dispatch.c`, `toffoli_add_seq_dispatch.c`, `toffoli_clifft_cdkm_dispatch.c`, etc.) which use width-indexed function calls like `get_hardcoded_QQ_add(bits)`. If a width's sequence file is removed but the dispatch still references it, linking fails. If the dispatch is updated to return NULL for removed widths, the fallback to runtime generation may have different behavior (different gate ordering, different circuit depth, or even different correctness due to the bugs being fixed). This happened implicitly during v2.3: the QFT/IQFT sharing optimization reduced source by 32.9% but required careful verification that shared arrays produced identical circuits.

**Why it happens:**
- The dispatch functions are generated by scripts in `scripts/generate_*.py` but the dispatch and sequence files are committed separately. If sequence files are removed without regenerating the dispatch, you get stale references.
- Toffoli Clifford+T sequences (widths 1-8) and QFT sequences (widths 1-16) serve DIFFERENT purposes: Toffoli is the default arithmetic mode. Removing Toffoli sequences forces fallback to runtime CCX decomposition which is orders of magnitude slower.
- The binary size is dominated by ~107 sequence files that are essentially large `const` arrays. Removing a few files saves negligible space; meaningful reduction requires a structural change (e.g., runtime generation, compression, or lazy loading).

**How to avoid:**
1. Start with measurement: use `nm --print-size --size-sort` on the `.so` file to identify which sequence files contribute the most to binary size. Focus effort on the top contributors.
2. Never remove Toffoli CDKM sequences (widths 1-8) or Clifford+T sequences -- these are the default arithmetic mode and have no runtime fallback.
3. For QFT sequences (widths 1-16): the v2.3 data showed widths 1-16 provide 2-6x dispatch speedup. Reducing to widths 1-8 would save space but regress performance for widths 9-16. Only consider this if the size budget is firm.
4. If using LTO (`-flto`), test thoroughly -- the project disabled LTO due to a GCC LTO bug (setup.py line 77). Verify with both GCC and Clang before enabling.
5. Strip debug symbols (`strip --strip-unneeded`) as a safe first step -- this alone can reduce size by 10-30% with zero functional impact.

**Warning signs:**
- Linker errors mentioning `get_hardcoded_*` functions.
- Runtime fallback silently engaged (circuit generation 10-100x slower for affected widths without any error).
- Import time regression >200ms (current baseline is 192ms, per v2.3 measurements).

**Phase to address:**
Binary size reduction phase. Should be the LAST phase in v4.1 because it depends on all bug fixes and tech debt cleanup being complete first. Bug fixes may modify sequences, tech debt cleanup may remove or consolidate files.

---

### Pitfall 6: Test Coverage Expansion Creating False Confidence

**What goes wrong:**
Adding tests that increase coverage numbers without testing meaningful quantum behavior. This codebase has a specific trap: tests that create circuits and verify they complete without error (characterization tests) provide no confidence that the circuits are quantum-mechanically correct. A test like `assert ql.qint(5, width=4) is not None` passes even if the X gates are applied to wrong qubits. The 8,365+ existing tests include ~91 xfail markers across 13 files and ~968 xfail-marked test cases for known bugs. Adding coverage by converting xfails to skips (or worse, removing them) hides regressions. Testing nested `with`-blocks by checking that the code does not crash, without verifying the generated circuit applies the correct controlled operations, would be false coverage.

**Why it happens:**
- The Qiskit verification pipeline (QASM export -> AerSimulator -> bitstring extraction) is slow (seconds per test) and limited to 17 qubits. Teams naturally gravitate toward faster, non-simulated tests.
- Cython extension code (`_core.pyx`, `qint.pyx`) is harder to cover with standard Python coverage tools because Cython-generated C is opaque to `pytest-cov`.
- The C tests (`tests/c/`) are not integrated into `pytest` and are easy to forget.
- The project's existing pattern of requirement-tracing (`GROV-01`, `INIT-01` IDs in docstrings) creates an illusion of completeness -- requirement coverage is not the same as behavioral coverage.

**How to avoid:**
1. Every new test for quantum operations MUST include Qiskit simulation verification (the `verify_circuit` fixture), not just "runs without error" assertions.
2. Do NOT convert existing xfail markers to skip or remove them. xfail markers are the project's bug backlog and must be converted to passing tests only when the corresponding bug is fixed.
3. For nested `with`-block testing: the test must verify that the generated QASM contains the correct controlled gate type (e.g., doubly-controlled X for nested conditionals), not just that the circuit was created.
4. For C test integration: wrap C test executables in pytest via `subprocess.run()` and assert exit code 0. This takes 5 minutes to implement and permanently closes the gap.
5. Track MUTATION testing effectiveness, not line coverage. A test suite that catches injected bugs (e.g., changing `+` to `-` in rotation angle calculations) provides real confidence. Line coverage does not.

**Warning signs:**
- New tests that never call `verify_circuit`, `to_openqasm()`, or Qiskit simulation.
- Coverage numbers increase but xfail count stays the same (covering new paths without fixing bugs).
- Tests that assert `isinstance(result, qint)` instead of asserting the actual quantum result.
- C allocator tests still not in pytest after the "test coverage" phase is marked complete.

**Phase to address:**
Test coverage phase. Should come AFTER all bug fixes (so xfail conversions are meaningful) and AFTER security hardening (so the new bounds checks are tested).

---

### Pitfall 7: qint_preprocessed.pyx Synchronization Drift During Refactoring

**What goes wrong:**
Any modification to `qint.pyx` or its `.pxi` includes (`qint_arithmetic.pxi`, `qint_bitwise.pxi`, `qint_comparison.pxi`, `qint_division.pxi`) must be reflected in `qint_preprocessed.pyx`. During a quality milestone that touches arithmetic operations (bug fixes), bitwise operations (dead code), and comparison operations (bug fixes), the preprocessed file drifts out of sync. The build still succeeds because `setup.py` runs `build_preprocessor.py` to regenerate it -- but if someone edits `qint_preprocessed.pyx` directly (treating it as the canonical source), those edits are overwritten on the next build. Conversely, if `build_preprocessor.py` is not run after editing `.pxi` files, tests pass locally (using the stale `.so`) but fail on a fresh build.

**Why it happens:**
- The project has TWO canonical sources for qint: `qint.pyx` (with includes) and `qint_preprocessed.pyx` (monolithic). Both are checked into git.
- `build_preprocessor.py` regenerates the preprocessed file, but there is no CI check that committed preprocessed files match regenerated output.
- Bug fixes often require editing `.pxi` files directly (e.g., fixing a comparison bug in `qint_comparison.pxi`), but the developer may forget to rebuild and re-commit the preprocessed variant.

**How to avoid:**
1. Establish the rule: NEVER edit `qint_preprocessed.pyx` directly. Always edit `qint.pyx` or its `.pxi` includes.
2. Add `build_preprocessor.py --check` as a pre-commit hook or CI step that fails if the preprocessed output differs from what is committed.
3. During the v4.1 milestone, run `python build_preprocessor.py` after every commit that touches any `.pyx` or `.pxi` file and commit the regenerated output.
4. Long-term: consider removing `qint_preprocessed.pyx` from git tracking entirely and generating it only at build time. This eliminates the synchronization problem permanently.

**Warning signs:**
- `git diff` shows changes in `qint_preprocessed.pyx` that you did not make manually (it was regenerated).
- Tests pass locally but fail in a fresh clone (`python setup.py build_ext --inplace` uses stale preprocessed).
- Bug fix confirmed in `.pxi` file but still failing because the preprocessed file still has old code.

**Phase to address:**
Tech debt cleanup phase. Should be one of the first items addressed because it affects all subsequent bug fix and refactoring work.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Editing `qint_preprocessed.pyx` directly instead of `.pxi` sources | Faster edit cycle, no rebuild step | Edits overwritten on next build, dual-maintenance burden grows | Never -- always edit the canonical `.pxi` sources |
| Leaving KS CLA stubs as NULL-returning functions | No work needed, dispatch fallback works | Confuses contributors, code suggests KS is "almost implemented" when it is not | Acceptable for v4.1 if stubs are clearly documented as intentional |
| Keeping QPU.c/QPU.h backward compat wrappers | No breakage risk | Build surface area, includes propagate to every module | Remove in v4.1 -- the wrapper has been empty since v1.1 |
| Using xfail instead of fixing known bugs | Unblocks test runs, documents bugs | 91 xfail instances across 13 files create noise, mask new regressions | Acceptable only until the corresponding bug is actively being fixed in the current milestone |
| Skipping C tests in pytest | Faster test runs, no C compilation step | C allocator regressions invisible in CI, false confidence in test pass rate | Never for a project with 604K lines of C |

## Integration Gotchas

Common mistakes when connecting the C/Cython/Python layers.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| C to Cython pointer passing | Casting `_get_circuit()` return as `<circuit_t*><unsigned long long>` without NULL check | Always check `_get_circuit_initialized()` before casting; add `if not _get_circuit_initialized(): raise RuntimeError(...)` |
| Cython `with nogil:` blocks | Accessing Python objects inside `with nogil:` (compile error) or forgetting to extract all needed C data before entering `nogil` | Extract all qubit arrays, control qubits, and ancillas into C-typed local variables BEFORE the `with nogil:` block |
| `qubit_array` scratch buffer | Assuming 384 elements is always sufficient | Compute required slots (2*width + NUMANCILLY) and validate against buffer size before writing |
| Sequence cache invalidation | Modifying a C sequence generation function without clearing the `precompiled_*` cache arrays | The caches are per-process static pointers. They are cleared on `ql.circuit()` call. Ensure test fixtures always call `ql.circuit()` first (the `clean_circuit` fixture does this) |
| build_preprocessor sync | Editing `.pxi` files but not running `build_preprocessor.py` | Add preprocessor run to the build step (already done in `setup.py`) and add `--check` to pre-commit |
| Cython `@cython.boundscheck(False)` | Applying globally to all functions for performance | Apply ONLY to verified hot-path functions where bounds are validated at the entry point. Keep enabled for non-hot-path utility functions |
| `qiskit-aer` import | Importing at module level (breaks `import ql` when aer not installed) | Defer import inside functions. Add `try/except ImportError` with install instructions |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Linear scan in `smallest_layer_below_comp` | Circuit generation slows for deep circuits (>1000 layers per qubit) | Binary search on sorted `occupied_layers_of_qubit` array | >1000 layers per qubit (wide multiplication, deep Grover iterations) |
| Python-level gate replay in `compile.py` | `@ql.compile` replay overhead grows linearly with gate count | Move replay to C-level `inject_remapped_gates` with C-level qubit mapping | >10,000 gates in compiled function |
| Full circuit rebuild per Grover/IQAE attempt | Each BBHT attempt or IQAE round allocates new circuit from scratch | Add circuit snapshot/restore or cache QASM across iterations | >10 Grover iterations or >20 IQAE rounds |
| `_optimize_gate_list()` fixed at 10 passes | May not converge for deeply nested compiled functions | Remove hard cap, iterate until stable (convergence guaranteed on finite lists) | Compiled functions with >5 nesting levels |
| Hardcoded `NUMANCILLY = 2 * 64 = 128` | Buffer overflow if operation needs >128 ancilla slots | Compute actual ancilla requirement per operation at dispatch time | Toffoli CLA at width >16 (needs >128 AND-ancilla qubits) |

## Security Mistakes

Domain-specific security issues for this quantum circuit framework.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No circuit pointer validation on all paths | Use-after-free crash if `ql.circuit()` is called while qint objects exist | Add `_circuit_initialized` check at every `_get_circuit()` call site; raise `RuntimeError` not segfault |
| `qubit_array` buffer without bounds | Buffer overwrite with 384-element fixed buffer; attacker-controlled width could trigger overflow | Validate `2 * width + NUMANCILLY <= len(qubit_array)` before any C call |
| Undeclared `qiskit-aer` dependency | Runtime `ModuleNotFoundError` with no guidance; users may install wrong version | Add `qiskit-aer>=0.14` to pyproject.toml `verification` extras; wrap import with `ImportError` message |
| `__del__`-based uncomputation order dependency | Incorrect quantum circuits under alternative GC implementations (PyPy) | Document CPython-only support; use explicit `.uncompute()` for security-critical paths |
| Committed `.so` files in repository | Stale compiled extensions used instead of freshly built ones; could mask bugs or carry old vulnerabilities | Add `.so` files to `.gitignore` or verify they match source on CI |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Bug fix "passes tests":** A fixed bug that passes its direct test but was not verified against the full exhaustive suite (test_add, test_mul, test_div, test_compare) -- regression may lurk in a different width or controlled variant
- [ ] **Dead code removal "builds clean":** QPU.c removed and `python setup.py build_ext --inplace` succeeds, but `import quantum_language` has not been tested (linker might succeed but runtime dlopen fails)
- [ ] **Bounds checking "added validation":** Validation added to Cython entry point but not tested with edge-case widths (width=1, width=64, width exceeding buffer) -- validates the happy path only
- [ ] **Optimizer refactoring "same results":** Binary search produces same layer assignments in unit test but not verified on full circuit generation (characterization tests) -- different gate ordering could produce same unitary but different optimization profile
- [ ] **Binary size reduced "stripped and smaller":** `strip` applied to `.so` file reducing size, but debug symbols needed for crash diagnostics are now permanently lost -- keep separate `.debug` file
- [ ] **Test coverage increased "85% coverage":** New tests added but they test circuit creation (constructors), not circuit correctness (simulation) -- coverage of lines executed without verification of quantum correctness
- [ ] **C tests integrated "in pytest now":** C test runner added to pytest but only checks exit code, not individual test assertions -- a C test binary that crashes before reaching the failing test still exits nonzero
- [ ] **Preprocessor sync "automated now":** `build_preprocessor.py` added to build step but no CI check verifies committed preprocessed files match generated output -- drift still possible between builds

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Arithmetic bug fix introduces regression | MEDIUM | `git bisect` to identify the breaking commit; the exhaustive test suite (8,365+ tests) makes bisection reliable. Revert the fix, add a regression test for the new failure, then re-attempt the fix with both tests. |
| Dead code removal breaks import | LOW | `git revert` the removal commit. Re-examine the dependency chain with `nm -u *.so` to find the undefined symbol. Restore only the needed function. |
| Bounds checking kills performance | LOW | Performance regression is detectable immediately via `pytest-benchmark`. Revert to `@cython.boundscheck(False)` on the hot path; move validation to the entry point instead. |
| Optimizer refactoring changes circuit layout | HIGH | If characterization tests were not captured before refactoring, recovery requires manual comparison of circuit output. Re-run the old code in a separate branch, capture golden masters, then debug the new code against them. |
| Binary size reduction breaks dispatch | MEDIUM | Linker error is immediate and obvious. Restore the removed sequence file and its dispatch entry. Regenerate dispatch files with `scripts/generate_*.py`. |
| False test coverage masks real bug | HIGH | Discovered only when a user reports a bug that tests "should" have caught. Requires auditing all tests added during the coverage phase for simulation verification. Add mutation testing to prevent recurrence. |
| Preprocessed file drift | LOW | Run `python build_preprocessor.py` and commit the output. If the stale preprocessed file caused a bug, `git diff` the regenerated output against the committed version to identify the exact drift. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Arithmetic regression (Pitfall 1) | Phase 1: Bug Fixes | Full exhaustive suite passes; xfail count decreases; no new xfails |
| Dead code removal breakage (Pitfall 2) | Phase 2: Tech Debt Cleanup | Clean build + `import quantum_language` succeeds; all 7 extension modules load |
| Bounds checking performance (Pitfall 3) | Phase 3: Security Hardening | Benchmark within 15% regression threshold; `CYTHON_DEBUG=1` build detects buffer overflows |
| Optimizer refactoring (Pitfall 4) | Phase 4: Performance Optimization | Golden-master circuit snapshots identical; benchmark shows measurable improvement |
| Binary size reduction (Pitfall 5) | Phase 5: Binary Size Reduction | `.so` file size decreased; `import quantum_language` baseline unchanged; dispatch fallback never triggered |
| False test coverage (Pitfall 6) | Phase 6: Test Coverage | Every new test includes Qiskit simulation verification; C tests in pytest; xfails converted to passes for fixed bugs |
| Preprocessed file drift (Pitfall 7) | Phase 2: Tech Debt Cleanup | `build_preprocessor.py --check` passes in CI; no manual edits to `qint_preprocessed.pyx` in git history |

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| BUG-MOD-REDUCE fix | Needs fundamentally different circuit structure; partial fixes will corrupt results for moduli > 2^(w-1) | Do NOT attempt incremental fix. Either redesign the modular reduction circuit from scratch or defer to a future milestone with proper research. |
| BUG-COND-MUL-01 fix | Controlled multiplication's scope uncomputation interacts with `_list_of_controls` global state | Must fix AFTER nested `with`-block cleanup (they share the `_list_of_controls` mechanism) |
| BUG-QFT-DIV fix | QFT division is "pervasively broken at all tested widths" per v3.0 discovery | This is likely a fundamental QFT rotation formula issue, not a simple bug. Consider whether QFT division is even needed given Toffoli division works correctly. May be better to mark QFT division as "not supported" and close the bug as "won't fix." |
| 32-bit multiplication segfault | Buffer overflow in C backend -- ASAN will find it but the fix may require expanding buffer sizes that affect binary size | Fix with ASAN first (`make asan-test`), then apply the minimal buffer expansion. Benchmark after. |
| Removing duplicate Cython files | `qint_preprocessed.pyx` removal changes the build path | Verify that `setup.py`'s preprocessor integration works on all platforms (macOS and Linux) before committing |
| Optimizer binary search | The existing loop has a `++i` where `--i` is likely intended (line 32) | Fix the loop direction bug BEFORE optimizing to binary search. These must be separate commits. |
| qiskit-aer dependency declaration | Adding to pyproject.toml may pin a version that conflicts with user's Qiskit | Use `qiskit-aer>=0.14` (floor only, no ceiling) in the optional `verification` group |

## Sources

- Codebase analysis: `.planning/codebase/CONCERNS.md`, `ARCHITECTURE.md`, `TESTING.md`, `STRUCTURE.md`, `STACK.md` (project-internal, HIGH confidence)
- Project history: `.planning/PROJECT.md` key decisions and known bugs (project-internal, HIGH confidence)
- Source code: `c_backend/src/optimizer.c`, `c_backend/src/execution.c`, `c_backend/src/IntegerAddition.c`, `src/quantum_language/_core.pyx`, `src/quantum_language/qint_arithmetic.pxi`, `setup.py` (project-internal, HIGH confidence)
- [VOQC: A Verified Optimizer for Quantum Circuits](https://dl.acm.org/doi/10.1145/3604630) -- MEDIUM confidence, domain research on optimizer correctness
- [Bounds checking performance: 0.3% overhead](https://chandlerc.blog/posts/2024/11/story-time-bounds-checking/) -- MEDIUM confidence, general C/C++ bounds checking
- [Dead code risks (Knight Capital $440M loss)](https://vfunction.com/blog/dead-code/) -- MEDIUM confidence, general dead code removal
- [Cython memory safety limitations](https://pythonspeed.com/articles/cython-limitations/) -- MEDIUM confidence, Cython-specific pitfalls
- [Test coverage false confidence](https://hackernoon.com/misleading-test-coverage-and-how-to-avoid-false-confidence) -- MEDIUM confidence, general testing practices
- [D-Linker: Shared library debloating](https://dl.acm.org/doi/10.1109/TCAD.2024.3446712) -- LOW confidence, general binary reduction
- [Quantum circuit optimization survey](https://www.mdpi.com/2624-960X/7/1/2) -- MEDIUM confidence, quantum optimizer patterns

---
*Pitfalls research for: Quantum Assembly v4.1 Quality & Efficiency*
*Researched: 2026-02-22*
