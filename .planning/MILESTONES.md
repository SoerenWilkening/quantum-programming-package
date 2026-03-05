# Project Milestones: Quantum Assembly

## v6.1 Quantum Chess Demo (Shipped: 2026-03-05)

**Delivered:** Complete manual quantum walk on a chess game tree using raw quantum_language primitives -- board encoding with legal move generation, compiled move oracles, walk register scaffolding, Montanaro diffusion operators, and compiled walk step U = R_B * R_A, with side-by-side QWalkTree comparison demonstrating framework expressiveness.

**Phases completed:** 103-106 (8 plans total)

**Key accomplishments:**

- Chess board encoding module with knight/king attack patterns, legal move filtering, and deterministic sorted move enumeration (43 tests)
- Compiled move oracle via `@ql.compile(inverse=True)` with factory pattern for quantum state manipulation
- Walk register scaffolding: one-hot height register, per-level branch registers, forward/reverse oracle replay for board state derivation
- Local diffusion D_x with Montanaro angles (phi = 2*arctan(sqrt(d))) and variable branching with cascade fallback
- Full walk operators R_A/R_B with height-controlled diffusion cascade and compiled walk step U = R_B * R_A
- Demo scripts: manual quantum walk with circuit stats and QWalkTree comparison showing side-by-side circuit metrics

**Stats:**

- 52 commits, 8 files changed (+3,000 / -110 lines)
- 4 phases, 8 plans
- 3 days (2026-03-03 to 2026-03-05)
- 122+ tests across 4 test files, all passing

**Git range:** `f255d1b`..`6da8cc3`

**What's next:** TBD -- next milestone planning via `/gsd:new-milestone`

---

## v6.0 Quantum Walk Primitives (Shipped: 2026-03-03)

**Delivered:** Predicate-aware quantum walk operators based on Montanaro 2015 backtracking speedup — tree encoding with one-hot height registers, local diffusion with correct amplitude angles, compiled walk operators R_A/R_B, variable branching with dynamic child counting, and iterative power-method detection with SAT demo verified within 17-qubit budget.

**Phases completed:** 97-102 (11 plans total)

**Key accomplishments:**

- QWalkTree class with one-hot height register, per-level branch registers, predicate interface with mutual exclusion validation
- D_x local diffusion with Ry cascade and correct amplitude angles (phi = 2*arctan(sqrt(d))) per Montanaro 2015, statevector-verified for d=2..5
- Walk operators R_A/R_B with compiled walk step U = R_B * R_A, qubit disjointness verification, and @ql.compile wrapping for controlled variant derivation
- Variable branching with predicate-driven child counting, conditional Ry rotation based on d(x), multi-controlled V-gate decomposition
- Iterative power-method detection algorithm (detect()) with 3/8 threshold on root state overlap
- SAT detection demo within 17-qubit budget, Qiskit statevector verification for known-solution and no-solution instances
- Full requirements closure: 18/18 satisfied, all verified with 130 walk tests

**Stats:**

- 31 commits, 30 files changed (+6,688 / -52 lines)
- 6 phases, 11 plans
- 2 days (2026-03-02 → 2026-03-03)
- Walk module: 4,278 LOC (1,497 walk.py + 2,579 tests + 202 demo)

**Known gaps (tech debt, non-blocking):**
- Raw predicate qubit allocation: each predicate call allocates new qbools, making full SAT demos infeasible at depth >= 2 without compiled predicates (future work)
- Framework limitation: `with qbool:` cannot nest — worked around via V-gate CCRy decomposition and inline gate emission
- 14-15 pre-existing test failures in test_compile.py (unrelated to v6.0)

**Git range:** `edc069e`..`61d1206`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v5.0 Advanced Arithmetic & Compilation (Shipped: 2026-02-26)

**Delivered:** Fixed all deferred arithmetic bugs (division, modular reduction) with C-level restoring divmod, added Beauregard modular Toffoli arithmetic for Shor's building blocks, parametric compilation for compile-once-replay-many, automatic depth/ancilla tradeoff policy, and quantum counting API.

**Phases completed:** 90-96 (19 plans total)

**Key accomplishments:**

- Quantum counting API (`ql.count_solutions()`) wrapping IQAE for exact solution count estimation with CountResult int-like wrapper
- Fixed BUG-DIV-02/BUG-QFT-DIV/BUG-MOD-REDUCE: C-level restoring divmod replacing broken QFT division, Beauregard modular reduction replacing orphan-qubit `_reduce_mod`
- Beauregard modular Toffoli arithmetic (add/sub/mul mod N) — 12 C functions for Shor's algorithm building blocks, exhaustively verified widths 2-8
- Depth/ancilla tradeoff via `ql.option('tradeoff', 'auto'|'min_depth'|'min_qubits')` with runtime CLA/CDKM dispatch replacing compile-time threshold
- Parametric compilation (`@ql.compile(parametric=True)`) — probe/detect/replay lifecycle with topology-safe per-value fallback for Toffoli CQ
- Full requirements closure: 20/20 satisfied, milestone audit PASSED with zero integration gaps

**Stats:**

- 80 commits, 106 files changed (+22,357 / -2,388 lines)
- 7 phases, 19 plans
- 3 days (2026-02-24 → 2026-02-26)

**Known gaps (tech debt, non-blocking):**
- QQ division persistent ancilla leak (fundamental algorithmic limitation, documented in KNOWN-ISSUES.md)
- 13 xfailed QQ division tests (a >= b cases)
- 14-15 pre-existing test failures in test_compile.py (unrelated to v5.0)
- Dead C function bodies kept intentionally (Cython refs removed)

**Git range:** v4.1..HEAD (80 commits)

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v4.1 Quality & Efficiency (Shipped: 2026-02-24)

**Delivered:** Comprehensive quality and efficiency improvements — fixed critical 32-bit multiplication segfault and QFT arithmetic bugs, hardened C backend security with pointer validation and static analysis, optimized binary size by 56.6%, improved test coverage from 48.2% to 56%, and eliminated dead code and tech debt.

**Phases completed:** 82-89 (22 plans total)

**Key accomplishments:**

- Fixed 32-bit multiplication segfault by increasing MAXLAYERINSEQUENCE from 10K to 300K
- Resolved mixed-width QFT addition and controlled QQ addition rotation bugs (BUG-WIDTH-ADD, BUG-CQQ-QFT)
- Security hardening: NULL pointer validation at Cython boundary, buffer bounds checking, cppcheck/clang-tidy with 45+ real fixes
- Binary size reduced 56.6% (64.4MB to 27.9MB) via section GC, symbol stripping, and -Os optimization
- Test coverage improved 48.2% to 56% (+7.8%); compile.py coverage from 18% to 63%
- Eliminated tech debt: dead QPU stubs removed, automated preprocessor drift detection, vulture scan clean

**Stats:**

- 24 commits, 181 files changed (+22,198 / -2,512 lines)
- 8 phases, 22 plans, ~34 tasks
- 3 days (2026-02-22 → 2026-02-24)

**Known gaps (deferred):**
- BUG-06 (MSB comparison leak in division) — requires uncomputation architecture redesign
- BUG-08 (QFT division/modulo failures) — depends on BUG-06
- BUG-09 (_reduce_mod corruption) — requires Beauregard-style algorithm redesign

**Git range:** `5ec5a39` → `18c2cdb`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v4.0 Grover's Algorithm (Shipped: 2026-02-22)

**Delivered:** Complete Grover's search implementation — gate primitives (Ry rotation, MCZ), oracle infrastructure with compute-phase-uncompute validation, zero-ancilla diffusion operator, end-to-end `ql.grover()` API, lambda predicate oracle auto-synthesis with BBHT adaptive search, and Iterative Quantum Amplitude Estimation with configurable precision.

**Phases completed:** 76-81 (18 plans total)

**Key accomplishments:**

- Ry rotation gate primitives with `branch(prob)` for creating superposition on qint/qbool
- Oracle infrastructure with `@ql.grover_oracle` decorator enforcing compute-phase-uncompute ordering and ancilla validation
- Zero-ancilla diffusion operator (X-MCZ-X pattern) and `x.phase += theta` phase syntax
- End-to-end `ql.grover()` API with auto iteration count for known and unknown solution counts
- Lambda predicate oracle auto-synthesis via tracing and BBHT adaptive search for unknown M
- Iterative Quantum Amplitude Estimation (`ql.amplitude_estimate()`) with Clopper-Pearson CIs

**Stats:**

- 83 commits, 104 files changed (+16,181 lines)
- 6 phases, 18 plans, ~27 tasks
- 4 days (2026-02-19 → 2026-02-22)
- 157 new tests (31 branch + 37 oracle + 22 diffusion + 21 grover + 22 predicate + 24 IQAE)

**Git range:** `2eca659` → `a8f56fa`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v3.0 Fault-Tolerant Arithmetic (Shipped: 2026-02-18)

**Delivered:** Complete Toffoli-based fault-tolerant arithmetic backend — CDKM ripple-carry adder, Brent-Kung carry look-ahead adder, schoolbook multiplication, restoring division, all with controlled variants and Clifford+T gate decomposition. Toffoli arithmetic is the default mode with QFT available via opt-out.

**Phases completed:** 65-75 (35 plans total)

**Key accomplishments:**

- CDKM ripple-carry adder (QQ/CQ/cQQ/cCQ) with MAJ/UMA chains and 1-ancilla lifecycle management
- Brent-Kung Carry Look-Ahead Adder with O(log n) depth (~50% depth reduction vs RCA at width 8)
- Toffoli schoolbook multiplication and restoring division completing full arithmetic surface
- Toffoli-default mode via `ql.option('fault_tolerant')` with seamless QFT fallback
- Cross-backend verification proving Toffoli/QFT equivalence for addition (widths 1-8), multiplication (widths 1-6), division (widths 2-6)
- Clifford+T gate decomposition with ~120 hardcoded sequence C files eliminating runtime decomposition overhead

**Stats:**

- 40 feat commits, 232 files changed (+330,063 lines)
- ~1,059K total LOC (604K C, 395K Python, 60K Cython)
- 11 phases, 35 plans
- 4 days (2026-02-14 → 2026-02-18)

**Git range:** `11fb70d` → `aaa5865`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v2.3 Hardcoding Right-Sizing (Shipped: 2026-02-08)

**Delivered:** Data-driven evaluation and right-sizing of hardcoded gate sequences — benchmarked all 9 operation types, kept addition widths 1-16 with shared QFT/IQFT factoring (32.9% source reduction, 11.1% binary size reduction), confirmed zero regression.

**Phases completed:** 62-64 (4 plans total)

**Key accomplishments:**

- Comprehensive benchmark infrastructure measuring import time (192ms), first-call generation (9 ops x 16 widths), and cached dispatch overhead
- Data-driven decision to keep all addition widths 1-16 hardcoded (2-6x dispatch speedup)
- Shared QFT/IQFT factoring reducing generated C from 79,867 to 53,598 lines (32.9% reduction)
- 11.1% binary size reduction (17.2MB to 15.3MB) from shared arrays
- Evaluation: multiplication "investigate", bitwise "skip", division "skip" for hardcoding
- Zero performance regression — 60-94% first-call improvement for addition operations

**Stats:**

- 21 commits
- 3 phases, 4 plans, 9 tasks
- 1 day (2026-02-08)

**Git range:** `d819159` → `ca5a4df`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v2.2 Performance Optimization (Shipped: 2026-02-08)

**Delivered:** Profiling-driven performance optimization achieving 27.7% aggregate throughput improvement via C hot path migration, 59-93% memory allocation reduction, hardcoded gate sequences for widths 1-16, and Cython hot path typing.

**Phases completed:** 55-61 (22 plans total)

**Key accomplishments:**

- Profiling infrastructure with cProfile, memray, Cython annotations, py-spy, and pytest-benchmark
- Forward/adjoint depth equality verified and regression-tested (no fix needed)
- Cython hot paths optimized with static typing, compiler directives, and memory views
- Hardcoded gate sequences for all 4 addition variants, widths 1-16 (~80K lines generated C)
- Top 3 hot paths (mul, add, xor) migrated to C with nogil — 27.7% aggregate throughput improvement
- Memory leaks eliminated, 59-93% allocation reduction via stack allocation

**Stats:**

- 68 commits
- 7 phases, 22 plans
- 4 days (2026-02-05 → 2026-02-08)

**Git range:** `16ff5cd` → `681f8a1`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v2.1 Compile Enhancements (Shipped: 2026-02-05)

**Delivered:** Ancilla qubit reuse in compiled function inverses (track, uncompute, deallocate), auto-uncompute in qubit_saving mode, and `ql.qarray` support as `@ql.compile` arguments.

**Phases completed:** 52-54 (6 plans total)

**Key accomplishments:**

- Forward call registry tracks ancilla qubits allocated during compiled function execution
- `f.inverse(x)` uncomputes exact physical ancillas from prior `f(x)` and deallocates them
- `f.adjoint(x)` provides standalone adjoint without forward call tracking
- Auto-uncompute of temp ancillas when `qubit_saving` mode is active (preserves return qubits)
- `ql.qarray` support in `@ql.compile` with correct capture, cache keying by length, and replay
- 106 compilation tests (100% pass rate) covering all INV and ARR requirements

**Stats:**

- 22 files created/modified (+5,334 / -104 lines)
- 345,901 total LOC (Python, Cython, C)
- 3 phases, 6 plans, ~12 tasks
- 1 day (2026-02-04 → 2026-02-05)

**Git range:** `feat(52-01) 2098d6f` → `docs(54) 54c18ec`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v2.0 Function Compilation (Shipped: 2026-02-04)

**Delivered:** `@ql.compile` decorator that captures gate sequences on first call, optimizes them, and replays with qubit remapping on subsequent calls — supporting controlled contexts, inverse generation, nesting, and debug introspection.

**Phases completed:** 48-51 (8 plans total)

**Key accomplishments:**

- `@ql.compile` decorator with gate capture, caching, and replay with virtual-to-real qubit remapping
- Gate list optimizer canceling inverse pairs and merging adjacent gates before caching
- Compiled functions work inside `with` blocks via controlled variant derivation with separate cache entries
- Inverse generation (`.inverse()`) producing adjoint of compiled sequences with reversed gate order
- Debug introspection mode showing operation counts, optimization stats, and cache hit/miss reporting
- Nested compilation support — compiled functions can call other compiled functions

**Stats:**

- 40 files created/modified (+8,252 lines)
- Key files: compile.py (920 LOC) + test_compile.py (1,794 LOC)
- 4 phases, 8 plans, 62 tests (100% pass rate)
- 1 day (2026-02-04)

**Git range:** `docs(48) 67196d0` → `test(51) c803676`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v1.9 Pixel-Art Circuit Visualization (Shipped: 2026-02-03)

**Delivered:** Added compact pixel-art circuit visualization with two zoom levels (overview for 200+ qubits, detail with text labels), auto-zoom selection, and a clean `ql.draw_circuit()` public API with lazy Pillow import.

**Phases completed:** 45-47 (7 plans total)

**Key accomplishments:**

- C-level circuit data extraction with qubit compaction (sparse-to-dense index remapping)
- NumPy-based pixel-art renderer with 10 color-coded gate types and measurement checkerboard
- Multi-qubit gate visualization with control lines and control dots
- Scale-tested at 200+ qubits and 10,000+ gates (54MB, <5s render time)
- Detail mode with 12px cells, text gate labels, qubit labels, and wire termination
- Public `ql.draw_circuit()` API with auto-zoom, mode override, save parameter, and lazy Pillow import

**Stats:**

- 9 files created/modified (+1,466 lines)
- ~221,387 total LOC (Python, Cython, C)
- 3 phases, 7 plans, 47 tests
- 1 day (2026-02-03)

**Git range:** `feat(45-01) aaa258d` -> `docs(47) 8dc87d8`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v1.8 Quantum Copy, Array Mutability & Uncomputation Fix (Shipped: 2026-02-03)

**Delivered:** Fixed uncomputation regression, implemented CNOT-based quantum state copying for qint/qarray binary operations, and enabled in-place element mutation on qarrays via all augmented assignment operators.

**Phases completed:** 41-44 (7 plans total)

**Key accomplishments:**

- Fixed uncomputation regression by adding layer tracking to all qint operations
- Implemented CNOT-based quantum state copy (qint.copy()/copy_onto()) verified by 70 Qiskit tests
- Replaced classical value reinitialization with quantum copy in all binary operations
- Added 10 missing qint operations (neg, rsub, lshift, rshift, ilshift, irshift, ifloordiv + copy/copy_onto)
- Added 9 missing qarray operations (floordiv, mod, invert, neg, lshift, rshift, ilshift, irshift, ifloordiv)
- Enabled in-place qarray element mutation via __setitem__ and all 9 augmented assignment operators

**Stats:**

- 37 files created/modified (+5,488 / -2,131 lines)
- ~219,921 total LOC (Python, Cython, C)
- 4 phases, 7 plans, ~15 tasks
- 2 days (2026-02-02 → 2026-02-03)

**Git range:** `feat(41-01) 3551193` → `docs(44) 83914dd`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v1.7 Bug Fixes & Array Optimization (Shipped: 2026-02-02)

**Delivered:** Fixed division overflow bug (BUG-DIV-01) and eliminated temporary qint allocations in qarray classical element-wise operations, with two bug fixes (modular reduction, controlled multiplication) deferred due to scaling issues.

**Phases completed:** 37, 40 (2 plans total)

**Key accomplishments:**

- Fixed division overflow (BUG-DIV-01) with safe loop bounds preventing divisor<<bit_pos overflow
- Identified and documented MSB comparison leak as separate bug (BUG-DIV-02)
- Eliminated temporary qint allocations in all 6 qarray in-place operators for classical operands
- Switched division test simulator to matrix_product_state for 44+ qubit circuits

**Stats:**

- 20 files created/modified (+2,460 / -95 lines)
- ~257,678 total LOC (Python, Cython, C)
- 2 phases, 2 plans, ~4 tasks
- 1 day (2026-02-02)

**Git range:** `docs(37) 82b7245` → `docs(40) 3058528`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v1.6 Array & Comparison Fixes (Shipped: 2026-02-02)

**Delivered:** Fixed array constructor parameter swap and three comparison operator bugs (equality inversion, ordering MSB boundary errors, circuit explosion investigation), with full verification confirming 1529 comparison tests pass and zero regressions.

**Phases completed:** 34-36 (5 plans total)

**Key accomplishments:**

- Fixed array constructor to create elements with correct values and widths (BUG-ARRAY-INIT)
- Fixed dual-bug in equality operators: GC gate reversal + bit-order reversal (BUG-CMP-01, 488 tests)
- Fixed ordering comparison MSB boundary errors with LSB-aligned CNOT bit copies (BUG-CMP-02)
- Confirmed circuit size explosion is non-issue — linear growth verified (BUG-CMP-03)
- Cleaned test suite: removed 324 lines of xfail logic, 1529 comparison tests pass cleanly
- Zero regressions across entire test suite

**Stats:**

- 25 files created/modified
- +3,766 / -537 lines (166,585 total LOC)
- 3 phases, 5 plans, ~9 tasks
- 2 days (2026-02-01 → 2026-02-02)

**Git range:** `docs(34) 442681a` → `test(36) 2990b29`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v1.5 Bug Fixes & Exhaustive Verification (Shipped: 2026-02-01)

**Delivered:** Fixed all 4 known C backend bugs and exhaustively verified every operation category (arithmetic, comparison, bitwise, advanced features) through the full pipeline, creating 8,365 tests with 7,410 passing and 968 xfail documenting newly discovered bugs.

**Phases completed:** 28-33 (33 plans total)

**Key accomplishments:**

- Reusable parameterized verification framework (build circuit -> OpenQASM -> Qiskit simulate -> check)
- Fixed 4 critical C backend bugs: subtraction underflow, comparison operators, multiplication segfault, QFT addition
- Exhaustive arithmetic verification: 2,048 passing tests for add/sub/mul across all small bit widths
- Exhaustive comparison verification: 1,095 passing tests across all 6 operators, QQ and CQ variants
- Exhaustive bitwise verification: 3,048 passing tests for AND/OR/XOR/NOT including mixed-width
- Advanced feature verification: uncomputation, quantum conditionals, and array operations validated

**Stats:**

- 123 files created/modified
- +20,426 lines (166,585 total LOC)
- 6 phases, 33 plans
- 3 days (2026-01-30 -> 2026-02-01)

**Git range:** `docs(28) ec76341` -> `docs(33) 9dbb49c`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v1.4 OpenQASM Export & Verification (Shipped: 2026-01-30)

**Delivered:** Production-quality OpenQASM 3.0 export from C backend with Python API and standalone Qiskit-based verification script validating the full pipeline.

**Phases completed:** 25-27 (5 plans total)

**Key accomplishments:**

- Production-quality `circuit_to_qasm_string()` C function with all 10 gate types, multi-controlled gates, and dynamic buffer management
- Backward-compatible file export via delegation pattern fixing all 14 legacy bugs in `circuit_to_opanqasm()`
- Memory-safe Python API (`ql.to_openqasm()`) with Cython try-finally cleanup
- Standalone verification script with subprocess isolation running 18 deterministic test cases
- Full pipeline validated: Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulation -> result verification

**Stats:**

- 36 files created/modified
- +6,185 lines (161,445 total LOC)
- 3 phases, 5 plans, ~7 tasks
- 1 day (2026-01-30)

**Git range:** `docs(25) af77763` -> `docs(27) ddfdaf3`

**What's next:** TBD — next milestone planning via `/gsd:new-milestone`

---

## v1.3 Package Structure & ql.array (Shipped: 2026-01-29)

**Delivered:** Proper Python package structure with modular Cython files and a full-featured ql.array class supporting multi-dimensional quantum arrays with reductions and element-wise operations.

**Phases completed:** 21-24 (16 plans total)

**Key accomplishments:**

- Proper Python package structure with `__init__.py` files and src-layout
- Modular Cython bindings split across focused modules (~200-300 lines each)
- `ql.array` class for homogeneous quantum arrays (qint or qbool) with multi-dimensional support
- Array reductions with optimal O(log n) depth (`&A`, `|A`, `^A`, `sum(A)`)
- Element-wise operators between arrays (arithmetic, bitwise, comparison)
- Full Python integration (`len()`, iteration, NumPy-style indexing and slicing)

**Stats:**

- ~50 files created/modified
- ~80,000 total LOC after milestone
- 4 phases, 16 plans
- 1 day (2026-01-29)

**Git range:** `docs(21)` -> `docs(24)`

**What's next:** v1.4 — OpenQASM Export & Verification

---

## v1.2 Automatic Uncomputation (Shipped: 2026-01-28)

**Delivered:** Automatic uncomputation of intermediate qubits in boolean expressions with configurable modes and user control methods.

**Phases completed:** 16-20 (10 plans total)

**Key accomplishments:**

- Dependency tracking infrastructure for qbool expressions (weak references, creation order, single ownership)
- C backend reverse gate generation with correct adjoint handling for phase gates and multi-controlled gates
- Automatic uncomputation on scope exit with LIFO cascade through dependency graph
- Context manager integration for `with` blocks (automatic cleanup when block exits)
- Uncomputation modes (lazy vs eager) with per-circuit and per-qbool mode control
- User control methods: explicit `.uncompute()`, `.keep()` opt-out, clear error messages

**Stats:**

- 49 files modified
- +10,423 net lines (81,459 total LOC)
- 5 phases, 10 plans, 47 tests (100% pass rate)
- 1 day (v1.1 -> v1.2)

**Git range:** `feat(16-01)` -> `docs(phase-20)`

**What's next:** v1.3 — Package restructuring and ql.array

---

## v1.1 QPU State Removal & Comparison Refactoring (Shipped: 2026-01-28)

**Delivered:** Eliminated global state dependency and implemented efficient comparison operators with classical qint initialization.

**Phases completed:** 11-15 (13 plans total)

**Key accomplishments:**

- Removed QPU_state global dependency (R0-R3 registers, instruction_t type) — system now fully stateless
- Implemented multi-controlled X gates (mcx) for n-bit comparisons using large_control arrays (1-64 bits)
- Refactored equality comparison (qint == int, qint == qint) with operand-preserving subtract-add-back pattern
- Memory-efficient ordering operators (<, >, <=, >=) using in-place subtraction/addition (no temp allocation)
- Classical qint initialization via X gates with auto-width mode (qint(5) and qint(5, width=8))

**Stats:**

- 63 files modified
- +9,338 net lines (70,900 total LOC)
- 5 phases, 13 plans, 149 tests (100% pass rate)
- 1 day (v1.0 -> v1.1)

**Git range:** `feat(11-01)` -> `docs(15)`

**What's next:** v1.2 — Automatic uncomputation

---

## v1.0 Initial Release (Shipped: 2026-01-27)

**Delivered:** Production-ready quantum programming framework with variable-width integers, complete arithmetic, bitwise operations, circuit optimization, and comprehensive documentation.

**Phases completed:** 1-10 (41 plans total)

**Key accomplishments:**

- Clean C backend with centralized memory management and explicit ownership
- Variable-width quantum integers (1-64 bits) with dynamic allocation
- Complete arithmetic operations (add, sub, mul, div, mod, modular arithmetic)
- Bitwise operations with Python operator overloading (&, |, ^, ~)
- Circuit optimization (gate merging, inverse cancellation) and statistics
- Comprehensive documentation (NumPy docstrings, README, C header docs)

**Stats:**

- ~100 files created/modified
- ~67,600 lines of Python/Cython/C code
- 10 phases, 41 plans, ~150 tasks
- ~90 days from project start to ship

**Git range:** `feat(01-01)` -> `feat(10-04)`

**What's next:** v1.1 — QPU State Removal

---





