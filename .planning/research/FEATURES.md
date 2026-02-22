# Feature Research: v4.1 Quality & Efficiency

**Domain:** Quantum circuit framework -- bug fixes, tech debt cleanup, performance optimization, binary size reduction, test coverage hardening
**Researched:** 2026-02-22
**Confidence:** HIGH (existing codebase analysis + domain literature)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that an open-source quantum computing framework must have working correctly. Missing these erodes trust in the library's correctness claims.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Correct modular arithmetic for all operand ranges | Modular arithmetic is the foundation of Shor's algorithm and post-quantum crypto circuits; incorrect results make the library unusable for its most important use case | HIGH | BUG-MOD-REDUCE: `_reduce_mod` result corruption. Requires fundamentally different circuit structure -- Beauregard-style reduction uses controlled subtraction + comparison + conditional re-addition, not simple repeated subtraction. Current approach hits duplicate qubit issues at larger moduli. Depends on: correct controlled QQ addition (BUG-CQQ-QFT) |
| Correct QFT-based controlled addition | Controlled operations are used in every non-trivial quantum algorithm (Grover oracles, phase estimation, modular exponentiation). If `with flag: a += b` generates wrong circuits, all algorithms built on top fail | HIGH | BUG-CQQ-QFT: QFT controlled QQ addition emits incorrect CCP (doubly-controlled phase) rotations at width 2+. Root cause is likely in the phase rotation angle calculation or qubit index mapping when adding the control qubit. Toffoli backend works correctly -- this is QFT-specific. Fix requires auditing the CCP gate emission in `IntegerAddition.c` against the Draper QFT adder specification |
| Correct QFT division and modulo | Division/modulo are core arithmetic operations. QFT division being "pervasively broken" (BUG-QFT-DIV) means 50% of the arithmetic backend is non-functional for these operations | HIGH | BUG-QFT-DIV: Pervasive failures at all tested widths. Likely cascading from BUG-CQQ-QFT since restoring division uses controlled addition/subtraction internally. Fix BUG-CQQ-QFT first, then re-verify division. If division still fails, the QFT subtraction-in-loop structure has independent bugs |
| Mixed-width addition correctness | Users naturally mix qint widths (e.g., 4-bit + 8-bit). Off-by-one errors break the fundamental promise of variable-width integers | MEDIUM | BUG-WIDTH-ADD: Off-by-one in mixed-width QFT addition. The phase rotation target qubit formula `64 - width + i_bit` may have an edge case when operand widths differ. Fix is surgical: audit the loop bounds in `IntegerAddition.c` for the mixed-width case |
| Controlled multiplication producing correct results | Multiplication inside conditionals is used in modular exponentiation for Shor's. The current workaround (scope-depth hack) is fragile | HIGH | BUG-COND-MUL-01: Controlled multiplication corrupts the result register. Root cause is that out-of-place multiplication results created inside a `with` scope get auto-uncomputed on scope exit, zeroing the result. Standard fix in quantum computing: the multiplication result must be explicitly moved/swapped out of the ancilla register before scope exit, or the multiplication circuit must be restructured to be in-place using the Beauregard swap trick |
| No segfaults at valid widths | A framework that segfaults at 32-bit multiplication is not production-ready | MEDIUM | 32-bit multiplication buffer overflow in C backend. The `sequence_t` or `qubit_array` buffer is undersized for 32x32 multiplication which produces a 64-bit result requiring 64+32=96 qubits worth of addressing. Fix: audit buffer sizes in `IntegerMultiplication.c` and ensure `qubit_array` in `_core.pyx` is large enough |
| MSB comparison correctness in division | Division silently producing wrong results for certain operand values is a correctness bug | MEDIUM | BUG-DIV-02: MSB comparison leak. 9 cases per div/mod test file fail due to the comparison qubit not being properly uncomputed after the restore step in restoring division. Fix: add explicit uncomputation of the MSB comparison ancilla after each division loop iteration |
| qiskit-aer declared as dependency | Users who install via pip and call `ql.grover()` get a bare `ModuleNotFoundError` | LOW | Add `qiskit-aer>=0.14` to `[project.optional-dependencies].verification` in `pyproject.toml`. Add a try/except wrapper with friendly error message |
| qarray in-place multiply without segfault | `arr[i] *= scalar` crashes -- a basic array operation should not crash the process | MEDIUM | C-layer segfault when `__imul__` is called on a qarray element. Root cause needs investigation but likely related to how the qint reference is held during in-place mutation vs. what the C backend expects for buffer ownership |

### Differentiators (Competitive Advantage)

Features that set this framework apart from Qiskit, Cirq, PennyLane. Not required for correctness, but valuable for the framework's positioning as a high-performance circuit compiler.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| DAG-based circuit optimizer (beyond linear scan) | Current `add_gate()` uses O(L) linear scan in `smallest_layer_below_comp()`. Qiskit uses DAGCircuit with CommutativeCancellation (recently unified into CommutativeOptimization in v2.3). VOQC uses propagate-and-cancel with commutation rules achieving 17.7% gate reduction. Upgrading to binary search on the sorted occupancy array is the minimum; building a commutation-aware optimizer would be a major differentiator | MEDIUM (binary search) / HIGH (full DAG optimizer) | Binary search on `occupied_layers_of_qubit` is a drop-in since the array is monotonically sorted. This is the "easy win." Full commutation analysis would require tracking gate commutativity rules (rotations on different qubits commute, CX and single-qubit gates may commute under specific conditions). Depends on: existing `optimizer.c` architecture |
| Rotation merging in `_optimize_gate_list` | The Python-level optimizer in `compile.py` only does adjacent cancellation (max 10 passes). VOQC's rotation merging combines non-adjacent same-axis rotations via commutation propagation. Adding this would reduce gate counts for compiled QFT-heavy functions by 10-20% | MEDIUM | Extend `_optimize_gate_list` to propagate rotations through commuting gates (single-qubit rotations commute with CX on other qubits). Also: remove the arbitrary `max_passes=10` cap -- converge until stable. The gate list is typically short (cached per-function), so unbounded iteration is safe |
| Binary size reduction via LTO and sequence right-sizing | At 15.3MB, the `.so` is large for a pip package. Competitors like Qiskit distribute pre-compiled wheels but their core library is pure Python. Having a compact native extension is a distribution advantage | MEDIUM | Three approaches: (1) `-ffunction-sections` + `--gc-sections` for dead code elimination in the 105 sequence files (~344K lines of C); (2) Link-Time Optimization (`-flto`) for cross-module inlining and dead code removal -- literature shows 4-21% reduction; (3) Strip debug symbols; (4) Right-size Clifford+T sequences -- the ~120 files for widths 1-8 may have redundant patterns that can share common subsequences. Depends on: `setup.py` build configuration |
| Automated preprocessor for `qint_preprocessed.pyx` | Eliminates the dual-maintenance burden. The canonical `.pyx` + `.pxi` include pattern stays as the editable source; `build_preprocessor.py` generates the flat file as a build step. CI verifies generated matches committed | LOW | `build_preprocessor.py` already exists and is referenced in comments. Wire it into the build pipeline properly and add a CI check |
| Circuit pointer validation and bounds checking | Security hardening: prevent use-after-free on stale circuit pointers, validate `qubit_array` bounds before C calls. Not a feature users see, but prevents mysterious crashes that drive users to competitors | MEDIUM | Audit all `<circuit_t*><unsigned long long>_get_circuit()` cast sites in `_core.pyx`. Add `_circuit_initialized` check to every path. Add bounds checking on `qubit_array` (4*64 + NUMANCILLY = 384 elements) before writes. Depends on: understanding all C-Python bridge call sites |
| C tests integrated into pytest | Having C-level allocator tests run in CI prevents regressions in the foundation layer that would otherwise be invisible | LOW | Write a pytest plugin or conftest fixture that compiles and runs `tests/c/Makefile` targets, capturing stdout and asserting exit code 0. Alternatively, use `subprocess.run()` in a pytest test |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like they belong in a quality/efficiency milestone but would create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full DAG-based intermediate representation rewrite | "Qiskit has DAGCircuit, we should too" | The existing layer-based circuit representation is deeply embedded in the C backend, Cython bridge, optimizer, and all 105 sequence files. A full DAG rewrite would touch every layer of the stack and regress performance in the short term. This is a v5.0+ effort, not a quality milestone task | Binary search in the existing occupancy array gives most of the performance benefit. Add commutation rules as a separate post-construction pass without changing the core IR |
| Comprehensive mutation testing | "Mutation testing finds more bugs than coverage" | Mutation testing on a quantum circuit library requires simulation for every mutant, making it computationally prohibitive (8,365 tests x hundreds of mutants = millions of simulation runs). The existing exhaustive verification approach with Qiskit is already more thorough than mutation testing | Focus on property-based testing for new code paths and differential testing between QFT and Toffoli backends (which already exists in `test_cross_backend.py`) |
| Coverage target enforcement (e.g., 90% line coverage) | "Industry standard is 80%+ coverage" | Line coverage is misleading for quantum circuit libraries. The critical correctness property is not "was this line executed" but "does this circuit produce the correct unitary." The existing requirement-tracing approach (test docstrings reference requirement IDs) plus exhaustive value verification is superior to line coverage metrics | Continue the requirement-tracing pattern. Add property-based tests for boundary conditions. Use the cross-backend differential testing pattern for new features |
| PyPy compatibility | "Support alternative Python runtimes" | The `__del__`-based uncomputation relies on CPython reference-counting GC ordering. PyPy's GC has different finalization semantics. Supporting PyPy would require rewriting the entire uncomputation system to use explicit context managers exclusively | Document "CPython only" as a constraint. The `with` block pattern already works correctly -- encourage users to use explicit scope management |
| Rewriting the C backend in Rust | "Memory safety without manual auditing" | The C backend is 604K lines, performance-optimized with stack allocation and cache-friendly layouts. A Rust rewrite would take months and lose the hand-tuned performance characteristics. The C code has already been hardened through ASAN testing and memory leak elimination in v2.2 | Continue targeted hardening: bounds checks at the Cython boundary, ASAN in CI, valgrind for new C code |
| Runtime-generated sequences replacing all hardcoded files | "Reduce the 344K lines of generated C" | v2.3 data showed hardcoded sequences provide 2-6x dispatch speedup for addition. Removing them would regress the framework's core performance advantage. The binary size concern is real but addressable through LTO and dead code elimination, not by removing the sequences | Use LTO, `-ffunction-sections` + `--gc-sections`, and strip debug symbols to reduce binary size while keeping the performance benefit |

## Feature Dependencies

```
BUG-CQQ-QFT (QFT controlled addition fix)
    |
    +---> BUG-QFT-DIV (QFT division depends on controlled add/sub)
    |         |
    |         +---> BUG-MOD-REDUCE (modular reduction uses division-like structure)
    |
    +---> BUG-COND-MUL-01 (controlled multiplication uses controlled addition)

BUG-WIDTH-ADD (mixed-width addition)
    |
    +---> (independent, can be fixed in parallel with other QFT fixes)

32-bit segfault (buffer overflow)
    |
    +---> (independent, C-level buffer sizing issue)

BUG-DIV-02 (MSB comparison in division)
    |
    +---> (independent, uncomputation issue in division loop)

Optimizer binary search
    |
    +---> Rotation merging (benefits from faster layer lookup)
    |
    +---> compile.py optimizer improvements (complementary to C-level optimizer)

Binary size reduction
    |
    +---> setup.py build flags (LTO, function sections)
    |
    +---> Sequence right-sizing (Clifford+T shared patterns)

Tech debt cleanup
    |
    +---> qint_preprocessed.pyx automation (independent)
    +---> QPU stubs removal (independent)
    +---> Nested with-blocks (depends on understanding _list_of_controls)

Test coverage gaps
    |
    +---> Nested with-blocks tests (depends on fix or characterization)
    +---> Circuit reset tests (independent)
    +---> qiskit-aer import tests (independent, quick)
    +---> C tests in pytest (independent, quick)
```

### Dependency Notes

- **BUG-QFT-DIV requires BUG-CQQ-QFT:** QFT division internally uses controlled QFT addition/subtraction. If the controlled addition is broken, division cannot work. Fix controlled addition first, then re-test division to see how many failures remain.
- **BUG-MOD-REDUCE requires correct division:** Modular reduction is essentially division-based. Cannot be fixed until the prerequisite arithmetic operations are correct.
- **BUG-COND-MUL-01 is partially independent:** The core issue is auto-uncomputation of scope-created results, not the arithmetic itself. However, testing the fix requires correct controlled addition.
- **Binary size and optimizer improvements are independent of bug fixes:** Can be parallelized with bug fix work.
- **Tech debt items are all independent:** Can be addressed in any order.

## MVP Definition (v4.1 Minimum)

### Must Fix (Critical Bugs)

These bugs prevent users from using core functionality correctly.

- [ ] BUG-CQQ-QFT -- QFT controlled addition is broken at width 2+; blocks all controlled QFT arithmetic
- [ ] BUG-QFT-DIV -- QFT division pervasively broken; depends on CQQ fix
- [ ] BUG-COND-MUL-01 -- Controlled multiplication corrupts results; blocks oracle-based algorithms
- [ ] 32-bit multiplication segfault -- Buffer overflow causes process crash
- [ ] qarray `*=` segfault -- Core array operation crashes

### Should Fix (Correctness Issues)

Important but with known workarounds (use Toffoli backend, avoid edge cases).

- [ ] BUG-WIDTH-ADD -- Mixed-width QFT addition off-by-one
- [ ] BUG-DIV-02 -- MSB comparison leak in division (9 cases per test file)
- [ ] BUG-MOD-REDUCE -- Modular reduction result corruption (fundamentally different circuit needed)
- [ ] qiskit-aer dependency declaration and import error handling

### Should Address (Tech Debt & Hardening)

Reduce maintenance burden and improve reliability.

- [ ] Automate `qint_preprocessed.pyx` generation in build pipeline
- [ ] Remove dead QPU stubs (`QPU.c`/`QPU.h`)
- [ ] Circuit pointer validation audit
- [ ] `qubit_array` bounds checking
- [ ] Integrate C tests into pytest

### Should Improve (Performance & Efficiency)

Measurable improvements to framework quality.

- [ ] Optimizer binary search in `smallest_layer_below_comp`
- [ ] Remove `max_passes=10` cap in `_optimize_gate_list` (converge until stable)
- [ ] Binary size reduction (LTO, function sections, strip)
- [ ] compile.py replay overhead reduction

### Defer (v4.2+ or v5.0)

Features that are out of scope for a quality milestone.

- [ ] Full DAG-based circuit IR -- architectural change, not a bug fix
- [ ] Parametric compilation (PAR-01, PAR-02) -- feature addition, not quality
- [ ] Nested `with`-block proper AND combination -- requires `Q_and` implementation, new feature
- [ ] Toffoli modular arithmetic (for Shor's) -- new feature, depends on BUG-MOD-REDUCE fix

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Category |
|---------|------------|---------------------|----------|----------|
| BUG-CQQ-QFT fix | HIGH | HIGH | P1 | Bug fix |
| BUG-QFT-DIV fix | HIGH | MEDIUM (if CQQ fixed) | P1 | Bug fix |
| BUG-COND-MUL-01 fix | HIGH | HIGH | P1 | Bug fix |
| 32-bit mul segfault | HIGH | LOW | P1 | Bug fix |
| qarray `*=` segfault | MEDIUM | MEDIUM | P1 | Bug fix |
| BUG-WIDTH-ADD fix | MEDIUM | LOW | P2 | Bug fix |
| BUG-DIV-02 fix | MEDIUM | MEDIUM | P2 | Bug fix |
| BUG-MOD-REDUCE fix | HIGH | HIGH | P2 | Bug fix |
| qiskit-aer dependency | LOW | LOW | P2 | Hardening |
| Optimizer binary search | MEDIUM | LOW | P2 | Performance |
| `_optimize_gate_list` convergence | MEDIUM | LOW | P2 | Performance |
| Binary size reduction | MEDIUM | MEDIUM | P2 | Efficiency |
| qint_preprocessed automation | LOW | LOW | P2 | Tech debt |
| QPU stub removal | LOW | LOW | P3 | Tech debt |
| Circuit pointer validation | MEDIUM | MEDIUM | P2 | Security |
| qubit_array bounds checking | MEDIUM | LOW | P2 | Security |
| C tests in pytest | LOW | LOW | P3 | Testing |
| Nested with-block tests | MEDIUM | LOW | P2 | Testing |
| Circuit reset tests | MEDIUM | LOW | P2 | Testing |
| qiskit-aer import tests | LOW | LOW | P3 | Testing |
| compile.py replay overhead | LOW | HIGH | P3 | Performance |

**Priority key:**
- P1: Must have -- correctness bugs that produce wrong results or crash
- P2: Should have -- quality improvements that meaningfully reduce risk
- P3: Nice to have -- incremental improvements

## Competitor Feature Analysis

| Feature Area | Qiskit | Cirq | This Framework (Quantum Assembly) |
|-------------|--------|------|-----------------------------------|
| Circuit optimizer | DAGCircuit with CommutativeOptimization (v2.3), multiple passes, extensible pass manager | Moment-based optimizer with eject_z, eject_phased_paulis, merge_single_qubit_gates | Layer-based with inline merge during `add_gate()`. Post-construction `cancel_inverse` + `merge` passes. Python-level `_optimize_gate_list` for compiled functions. No commutation analysis |
| Arithmetic correctness testing | DraperQFTAdder verified via unit tests; VBEAdder for Toffoli-based; circuits are library components, not generated | No built-in arithmetic library; users build from primitives | Exhaustive verification (8,365+ tests) across all operations, cross-backend differential testing. Superior coverage but known bugs remain in edge cases |
| Modular arithmetic | `PhaseEstimation` + modular arithmetic in tutorials; no built-in modular multiplier | No built-in | Full `qint_mod` class with add/sub, but `*` not implemented; `_reduce_mod` has BUG-MOD-REDUCE |
| Binary size | Pure Python core; Rust transpiler (`qiskit-transpiler-service`); no large generated C | Pure Python | 15.3MB compiled .so with 344K lines of hardcoded C sequences; needs LTO/stripping |
| Test approach | pytest + property-based equivalence checks + CI; mutation testing explored in research | pytest + cirq-core test suite | pytest + exhaustive Qiskit simulation verification + cross-backend differential; 8,365+ tests. No property-based testing; no fuzz testing |

## Detailed Analysis by Bug Category

### 1. QFT Phase Rotation Bugs (BUG-CQQ-QFT, BUG-QFT-DIV, BUG-WIDTH-ADD)

**Standard approach in the literature:** The Draper QFT adder applies controlled phase rotations `P(pi/2^k)` where `k` depends on the relative qubit positions. Common bugs:

- **Off-by-one in qubit indexing:** The rotation angle `pi/2^(j-i)` depends on the distance between qubits `i` and `j`. If the framework uses a 64-qubit address space with right-aligned layout (`qubits[64 - width]` offset pattern), the index formula must correctly handle both the source and target register offsets. This is the most likely root cause of BUG-WIDTH-ADD.
- **Controlled phase becoming doubly-controlled:** When adding a control qubit to a QFT adder, each `CP` (controlled-phase) gate becomes a `CCP` (doubly-controlled-phase) gate. The CCP decomposition into standard gates must preserve the rotation angle exactly. If the decomposition introduces phase errors, they accumulate across all qubit positions. This is the likely root cause of BUG-CQQ-QFT.
- **QFT/IQFT placement relative to controlled block:** The QFT and IQFT must be applied to the target register, not the control. If the controlled block boundary includes the QFT/IQFT, they become controlled-QFT/IQFT which is incorrect.

**Fix strategy:** Audit `IntegerAddition.c` CCP gate emission against the Draper paper. Verify rotation angles `pi/2^k` use correct `k` values. Ensure QFT/IQFT are outside the controlled block. Test with width=2 first (simplest non-trivial case).

### 2. Controlled Multiplication Uncomputation (BUG-COND-MUL-01)

**Standard approach:** In quantum computing, controlled multiplication (as used in Shor's modular exponentiation) follows the pattern:

1. Compute `a * b` into an ancilla register (out-of-place)
2. SWAP the result into the target register
3. Reverse-compute (uncompute) the ancilla

The critical insight is that the ancilla must be uncomputed *within the controlled block*, not after it. If the framework's scope-based auto-uncomputation triggers on scope exit (which it does), and the multiplication result is a new qint created inside the scope, the result gets zeroed.

**Fix strategy:** Two options:
- **Option A (scope-aware):** Mark the multiplication result as "owned by caller" so scope exit does not uncompute it. This requires modifying the scope tracking to understand return values.
- **Option B (circuit restructure):** Use an in-place multiplication pattern (Beauregard's controlled swap trick) where the result overwrites the input, avoiding the ancilla ownership problem entirely.

Option A is more compatible with the existing architecture. The current workaround (setting `scope_depth=0` during multiplication) is a variant of this but fragile.

### 3. Modular Reduction (BUG-MOD-REDUCE)

**Standard approach (Beauregard 2002):** Modular addition `(a + b) mod N` is implemented as:
1. Add: `a + b`
2. Subtract modulus: `a + b - N`
3. Compare: is result negative? (check MSB)
4. Conditionally re-add N: if negative, add N back
5. Uncompute comparison: subtract `b`, check sign, re-add `b`

The key difficulty is step 5: uncomputing the comparison qubit requires reversing the addition of `b`, checking the sign again, and re-adding `b`. This creates a circular dependency if not carefully structured.

**Why this is HIGH complexity:** The current implementation uses `_reduce_mod` which hits "duplicate qubit" errors at larger moduli, suggesting the circuit is trying to use the same qubit as both source and target. The Beauregard approach requires a carefully ordered sequence of additions and comparisons with specific ancilla management.

### 4. Circuit Optimizer Beyond Linear Scan

**Standard approaches in quantum compilers:**

- **Binary search (minimum improvement):** Replace the O(L) scan in `smallest_layer_below_comp` with O(log L) binary search. The `occupied_layers_of_qubit` array is already sorted. This is a direct drop-in.
- **Commutation-aware cancellation:** Track which gate types commute (e.g., rotations on different qubits, CX on non-overlapping qubits). Propagate gates through commuting neighbors to find cancellation partners. VOQC achieves 17.7% gate count reduction this way.
- **Rotation merging:** Combine `Rz(a)` followed by (commuting gates) followed by `Rz(b)` into `Rz(a+b)`. Requires commutation tracking. Currently only adjacent merging is implemented in the Python `_optimize_gate_list`.
- **Template matching:** Replace known suboptimal patterns with more efficient equivalents (e.g., 3-CNOT to 2-CNOT for certain two-qubit unitaries). Higher complexity but significant gate reduction.

**Recommended for v4.1:** Binary search (LOW effort, measurable impact on deep circuits) + unbounded convergence in `_optimize_gate_list` (trivial change, better optimization results).

### 5. Binary Size Reduction

**Applicable techniques for this project:**

- **`-ffunction-sections` + `-Wl,--gc-sections`:** Place each function in its own ELF section; linker removes unreferenced sections. Effective for the 105 sequence files where not all widths may be used at runtime. Expected: 5-15% reduction.
- **Link-Time Optimization (`-flto`):** Cross-module inlining and dead code elimination. The 20+ C source files in the backend have many small functions that could be inlined. Expected: 4-10% additional reduction.
- **`strip -s`:** Remove all symbol table and debug info. Simple but effective. Expected: 5-10% reduction.
- **`-Os` instead of `-O3`:** Trade speed for size. NOT recommended -- the performance-critical hot paths would regress. Instead, use `-O3` for hot paths and `-Os` for cold paths (sequence files).
- **Shared Clifford+T subsequences:** The ~120 Clifford+T files contain the 15-gate CCX decomposition repeated thousands of times. Extracting the CCX->Clifford+T pattern as a callable function rather than inlining it would dramatically reduce code size. This was partially done for QFT sequences (32.9% reduction via shared QFT/IQFT factoring in v2.3).

### 6. Test Coverage Patterns

**What works for quantum circuit libraries (based on domain research):**

- **Exhaustive small-width verification:** Already implemented. Verify all 2^n x 2^n input pairs for small n (1-4), sample for larger n. This is the gold standard.
- **Cross-backend differential testing:** Already implemented in `test_cross_backend.py`. If QFT and Toffoli backends agree, the result is almost certainly correct. Extend to cover newly fixed operations.
- **Property-based testing:** Test algebraic properties rather than specific values. For example: `(a + b) - b == a` for all a, b. `(a * b) / b == a` for b != 0. This catches bugs that exhaustive testing at small widths might miss (e.g., BUG-WIDTH-ADD was found at width mismatches, not small exhaustive tests).
- **Boundary value testing:** Max width (64), width=1, mixed widths (1+64, 31+33), values at 2^(w-1) (sign bit boundary), 0, 2^w - 1 (max value). Focus on the boundaries that are most likely to expose bugs in the right-aligned qubit layout.
- **Regression tests for fixed bugs:** Every bug fix must add a test that would have caught the bug. These tests should be marked with the bug ID for traceability.
- **Fuzz testing (stretch goal):** QuteFuzz-style random circuit generation found 17 bugs across Qiskit/Pytket/Cirq. Generating random arithmetic expressions and comparing QFT vs Toffoli results would be high-value. However, this is better suited for CI automation than manual test writing.

**What to add for v4.1 specifically:**
- Nested `with`-block tests (characterize current behavior, then fix or document)
- Circuit reset with live qint objects (test for graceful failure, not segfault)
- `qiskit-aer` import failure (test for friendly error message)
- C allocator tests in pytest (subprocess wrapper)
- Property-based tests for fixed arithmetic operations

## Sources

### Quantum Arithmetic and Modular Circuits
- [Comprehensive Study of Quantum Arithmetic Circuits (2024)](https://arxiv.org/html/2406.03867v1)
- [Quantum Arithmetic with QFT - Ruiz-Perez & Garcia-Escartin (2017)](https://arxiv.org/pdf/1411.5949)
- [Constant-Optimized Quantum Circuits for Modular Multiplication - Markov & Saeedi](https://arxiv.org/abs/1202.6614)
- [High Performance Quantum Modular Multipliers - Rines & Chuang](https://apps.dtic.mil/sti/pdfs/AD1083851.pdf)
- [Measurement-based Uncomputation for Modular Arithmetic](https://arxiv.org/abs/2407.20167)
- [Measurement-based Uncomputation Applied to Controlled Modular Multiplication](https://arxiv.org/abs/2102.01453)

### Circuit Optimization
- [Qiskit CommutativeCancellation Pass](https://docs.quantum.ibm.com/api/qiskit/qiskit.transpiler.passes.CommutativeCancellation)
- [Qiskit v2.3 Release - CommutativeOptimization unification](https://www.ibm.com/quantum/blog/qiskit-2-3-release-summary)
- [VOQC: A Verified Optimizer for Quantum Circuits](https://www.cs.umd.edu/~mwh/papers/voqc.pdf)
- [Optimizing Quantum Circuits, Fast and Slow](https://arxiv.org/abs/2411.04104)
- [Truncated Phase-Based Quantum Arithmetic: Error Propagation](https://arxiv.org/html/2110.00217)

### Testing Quantum Programs
- [QUT: A Unit Testing Framework for Quantum Subroutines (2025)](https://arxiv.org/html/2509.17538)
- [Quantum Testing in the Wild: Qiskit Algorithms Case Study (2025)](https://arxiv.org/html/2501.06443v1)
- [Property-Based Testing of Quantum Programs in Q#](https://dl.acm.org/doi/10.1145/3387940.3391459)
- [Testing and Debugging Quantum Programs: Road to 2030](https://dl.acm.org/doi/full/10.1145/3715106)
- [QuteFuzz: Fuzzing Quantum Compilers (PLanQC 2025)](https://popl25.sigplan.org/details/planqc-2025-papers/12/QuteFuzz-Fuzzing-quantum-compilers-using-randomly-generated-circuits-with-control-fl)
- [QDiff: Differential Testing of Quantum Software Stacks](https://www.researchgate.net/publication/363137685_QDiff_Differential_Testing_of_Quantum_Software_Stacks)

### Binary Size Reduction
- [Code Size Optimization: GCC Compiler Flags](https://interrupt.memfault.com/blog/code-size-optimization-gcc-flags)
- [Cython Large Output Size Issue #2102](https://github.com/cython/cython/issues/2102)
- [Optimizing size of Cython .so (Pyodide #4289)](https://github.com/pyodide/pyodide/issues/4289)
- [Size Optimization Tricks - justine.lol](https://justine.lol/sizetricks/)
- [Shrinking the Kernel with Link-Time Optimization](https://lwn.net/Articles/744507/)

### QFT-Specific Issues
- [Systemic Errors of Banded Quantum Fourier Transformation](https://eprint.iacr.org/2024/454.pdf)
- [DraperQFTAdder - IBM Qiskit Documentation](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.DraperQFTAdder)
- [PennyLane Quantum Arithmetic Operators Demo](https://pennylane.ai/qml/demos/tutorial_how_to_use_quantum_arithmetic_operators)

---
*Feature research for: Quantum Assembly v4.1 Quality & Efficiency*
*Researched: 2026-02-22*
