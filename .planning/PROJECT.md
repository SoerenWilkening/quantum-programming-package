# Quantum Assembly

## What This Is

A quantum programming framework that enables writing quantum algorithms using standard programming constructs — operator overloading on variable-width quantum integers (qint, 1-64 bits) and quantum booleans (qbool), with Python's `with` statement implementing quantum conditionals. Operations compile to optimized quantum circuits via a C backend with Cython bindings. Supports dual arithmetic backends: QFT-based (phase rotations) and Toffoli-based (fault-tolerant, Clifford+T decomposable) with CDKM ripple-carry and Brent-Kung carry look-ahead adders. Includes `@ql.compile` for function-level compilation with gate capture/replay/optimization, Grover's search with `ql.grover()` (lambda predicate oracles, adaptive BBHT search), iterative quantum amplitude estimation via `ql.amplitude_estimate()`, circuit optimization, pixel-art circuit visualization scaling to 200+ qubits, T-count reporting, statistics, OpenQASM 3.0 export, and Qiskit-based verification.

## Core Value

Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## Requirements

### Validated

- ✓ Basic arithmetic (+, - for variable-width integers) — v1.0
- ✓ Multiplication (variable integer size, 1-64 bits) — v1.0
- ✓ Division and modulo operations — v1.0
- ✓ Modular arithmetic (add/sub/mul mod N) — v1.0
- ✓ Comparisons (<=, ==, >=, <, >, !=) for variable-width integers — v1.0
- ✓ Bitwise operations (AND, OR, XOR, NOT) for qint — v1.0
- ✓ Python operator overloading for all qint/qbool operations — v1.0
- ✓ Quantum conditionals via `with` statement — v1.0
- ✓ Circuit generation and OpenQASM output — v1.0
- ✓ Circuit optimization (gate merging, inverse cancellation) — v1.0
- ✓ Circuit statistics (depth, gate count, qubit usage) — v1.0
- ✓ Clean C layer with centralized memory management — v1.0
- ✓ Comprehensive documentation (Python docstrings, C headers, README) — v1.0
- ✓ Test infrastructure (pytest, pre-commit, characterization tests) — v1.0
- ✓ Performance benchmarks (QFT up to 2000 variables) — existing
- ✓ Remove QPU_state global dependency (R0-R3 registers) — v1.1
- ✓ Refactor equality comparison with CQ_equal_width/cCQ_equal_width — v1.1
- ✓ Implement qint == qint as (qint - qint) == 0 — v1.1
- ✓ Refactor >= and <= to use in-place subtraction/addition — v1.1
- ✓ Classical qint initialization via X gates — v1.1
- ✓ Dependency tracking for qbool expressions (parent-child relationships) — v1.2
- ✓ Reverse gate generation (adjoints) for all gate types — v1.2
- ✓ Automatic uncomputation on scope exit with LIFO cascade — v1.2
- ✓ Context manager integration (`with` block cleanup) — v1.2
- ✓ Uncomputation modes (lazy vs eager, `ql.option("qubit_saving")`) — v1.2
- ✓ User control methods (`.uncompute()`, `.keep()`, clear error messages) — v1.2
- ✓ Proper Python package structure with `__init__.py` files — v1.3
- ✓ ql.array class for homogeneous quantum arrays (qint or qbool) — v1.3
- ✓ Array reductions with optimal depth (`&A`, `|A`, `^A`, `sum(A)`) — v1.3
- ✓ Element-wise operators between arrays (arithmetic, bitwise, comparison) — v1.3
- ✓ Python integration for arrays (`len()`, iteration, indexing, slicing) — v1.3
- ✓ Production-quality C-level OpenQASM 3.0 export (all gate types, large_control, proper error handling) — v1.4
- ✓ `ql.to_openqasm()` Python API returning QASM string (in-memory, no file I/O) — v1.4
- ✓ Standalone verification script with built-in test cases (classical init -> export -> Qiskit simulate -> check outcomes) — v1.4

- ✓ Fix subtraction underflow bug (3-7 wraps correctly) — v1.5
- ✓ Fix less-or-equal comparison bug (5<=5 returns 1) — v1.5
- ✓ Fix multiplication segfaults at certain widths — v1.5
- ✓ Fix QFT addition bug (both nonzero operands) — v1.5
- ✓ Reusable Qiskit-based verification test framework — v1.5
- ✓ Exhaustive verification of all arithmetic operations — v1.5
- ✓ Exhaustive verification of all comparison operations — v1.5
- ✓ Exhaustive verification of bitwise operations — v1.5
- ✓ Verification of modular arithmetic operations — v1.5
- ✓ Verification of automatic uncomputation — v1.5
- ✓ Verification of quantum conditionals — v1.5
- ✓ Verification of ql.array operations — v1.5

- ✓ Fix array constructor value initialization (BUG-ARRAY-INIT) — v1.6
- ✓ Fix array element-wise arithmetic producing wrong circuits — v1.6
- ✓ Fix array in-place operations with width mismatches — v1.6
- ✓ Fix eq/ne comparison inversion (BUG-CMP-01, 488 tests) — v1.6
- ✓ Fix ordering comparison errors at MSB boundary (BUG-CMP-02) — v1.6
- ✓ Confirm circuit size for gt/le is linear, not exponential (BUG-CMP-03) — v1.6

- ✓ Fix division overflow for divisor >= 2^(w-1) (BUG-DIV-01) — v1.7
- ✓ Array element-wise arithmetic with classical values uses CQ_* directly (no temp qint) — v1.7
- ✓ Array element-wise bitwise ops with classical values uses CQ_* directly (no temp qint) — v1.7

- ✓ Fix automatic uncomputation regression (layer tracking on all operations) — v1.8
- ✓ CNOT-based quantum state copy for qint (copy()/copy_onto()) — v1.8
- ✓ Binary operations use quantum copy instead of classical value reinitialization — v1.8
- ✓ qarray binary ops produce quantum-copied elements — v1.8
- ✓ In-place qarray element mutation via augmented assignment (all 9 operators) — v1.8
- ✓ Multi-dimensional qarray indexing for in-place ops — v1.8
- ✓ New qint operations: neg, rsub, lshift, rshift, ilshift, irshift, ifloordiv — v1.8
- ✓ New qarray operations: floordiv, mod, invert, neg, lshift, rshift, ilshift, irshift, ifloordiv — v1.8

- ✓ Pixel-art circuit renderer with NumPy bulk rendering and 10 color-coded gate types — v1.9
- ✓ Multi-qubit gate visualization with control lines and control dots — v1.9
- ✓ Two zoom levels: overview (3px cells, 200+ qubits) and detail (12px cells, text labels) — v1.9
- ✓ Auto-zoom selection based on circuit size with user override — v1.9
- ✓ `ql.draw_circuit()` Python API returning PIL Image with save-to-PNG and lazy Pillow import — v1.9

- ✓ `@ql.compile` decorator captures gate sequences and replays with qubit remapping — v2.0
- ✓ Gate list optimizer cancels inverse pairs and merges adjacent gates before caching — v2.0
- ✓ Compiled functions work inside `with` blocks via controlled variant derivation — v2.0
- ✓ `.inverse()` on compiled functions produces adjoint of compiled sequence — v2.0
- ✓ Debug mode with operation counts, optimization stats, cache hit/miss reporting — v2.0
- ✓ Nested compilation (compiled functions calling other compiled functions) — v2.0
- ✓ Comprehensive test suite (62 tests) covering all compilation scenarios — v2.0
- ✓ Ancilla tracking with forward call registry for compiled functions — v2.1
- ✓ `f.inverse(x)` uncomputes exact physical ancillas from prior forward call and deallocates — v2.1
- ✓ `f.adjoint(x)` standalone adjoint generation without forward tracking — v2.1
- ✓ Auto-uncompute of temp ancillas in qubit_saving mode (preserves return qubits) — v2.1
- ✓ `ql.qarray` support as `@ql.compile` arguments with correct capture, caching, and replay — v2.1
- ✓ 106 compilation tests covering all INV and ARR requirements — v2.1

- ✓ Profiling infrastructure: cProfile, memray, Cython annotations, py-spy, pytest-benchmark — v2.2
- ✓ Forward/adjoint depth equality verified with regression tests — v2.2
- ✓ Cython hot paths: static typing, compiler directives, memory views — v2.2
- ✓ Hardcoded gate sequences for all 4 addition variants, widths 1-16 (~80K lines generated C) — v2.2
- ✓ Top 3 hot paths (mul, add, xor) migrated to C with nogil — 27.7% aggregate improvement — v2.2
- ✓ Memory leaks eliminated, 59-93% allocation reduction via stack allocation — v2.2

- ✓ Benchmark infrastructure measuring import time, first-call generation, and cached dispatch overhead — v2.3
- ✓ Data-driven decision to keep all addition widths 1-16 hardcoded (2-6x dispatch speedup) — v2.3
- ✓ Shared QFT/IQFT factoring reducing generated C by 32.9% (79,867 to 53,598 lines) — v2.3
- ✓ 11.1% binary size reduction (17.2MB to 15.3MB) from shared arrays — v2.3
- ✓ Evaluation: multiplication "investigate", bitwise "skip", division "skip" for hardcoding — v2.3
- ✓ Zero regression verified — 60-94% first-call improvement for addition operations — v2.3

- ✓ Toffoli-based CDKM ripple-carry adder (QQ/CQ/cQQ/cCQ) with 1-ancilla lifecycle — v3.0
- ✓ Toffoli-based schoolbook multiplication (QQ/CQ/cQQ/cCQ) via shift-and-add — v3.0
- ✓ Restoring division/modulo with Toffoli add/sub underneath — v3.0
- ✓ Brent-Kung Carry Look-Ahead Adder with O(log n) depth (~50% depth reduction) — v3.0
- ✓ `ql.option('fault_tolerant')` backend dispatch — Toffoli default, QFT opt-in — v3.0
- ✓ Cross-backend verification: Toffoli/QFT equivalence for add (1-8), mul (1-6), div (2-6) — v3.0
- ✓ Hardcoded Toffoli sequences for widths 1-8 (QQ/cQQ/CQ-inc/cCQ-inc) — v3.0
- ✓ Inline CQ/cCQ generators with classical-bit gate simplification — v3.0
- ✓ MCX auto-decomposition (AND-ancilla pattern, zero MCX in output) — v3.0
- ✓ CCX->Clifford+T decomposition via `ql.option('toffoli_decompose', True)` — v3.0
- ✓ T_GATE/TDG_GATE enum, exact T-count reporting, QASM T/Tdg export — v3.0
- ✓ ~120 Clifford+T hardcoded sequence C files for CDKM and BK CLA (widths 1-8) — v3.0

- ✓ Ry rotation gate primitives with `branch(prob)` on qint/qbool — v4.0
- ✓ `@ql.grover_oracle` decorator with compute-phase-uncompute validation and ancilla delta check — v4.0
- ✓ Bit-flip oracle auto-wrapping with phase kickback pattern — v4.0
- ✓ Zero-ancilla diffusion operator (X-MCZ-X) and `x.phase += theta` syntax — v4.0
- ✓ `ql.grover(oracle, search_space)` API with auto iteration count — v4.0
- ✓ Lambda predicate oracle auto-synthesis via tracing — v4.0
- ✓ BBHT adaptive search for unknown solution count — v4.0
- ✓ `ql.amplitude_estimate()` with IQAE, configurable epsilon and confidence — v4.0

### Active

**Deferred bugs (carry forward):**
- Fix _reduce_mod result corruption (BUG-MOD-REDUCE) — needs fundamentally different circuit structure
- Fix controlled multiplication scope uncomputation (BUG-COND-MUL-01) — root-caused in Phase 69-02, workaround active
- Fix MSB comparison leak in division (BUG-DIV-02) — 9 cases per div/mod test file
- Fix mixed-width QFT addition off-by-one (BUG-WIDTH-ADD) — discovered in Phase 43
- Fix 32-bit multiplication segfault (buffer overflow in C backend) — discovered in Phase 61
- Fix QFT controlled QQ addition CCP rotation errors (BUG-CQQ-QFT) — discovered in Phase 70-01
- Fix QFT division/modulo pervasive failures (BUG-QFT-DIV) — discovered in Phase 70-02

**Deferred features (carry forward):**
- Parametric compilation (compile once for all classical values) — PAR-01, PAR-02
- Resource estimation for compiled functions — ADV-01
- Serialization of compiled functions to disk — ADV-02
- Compiled function composition — ADV-03
- Hardcoded sequences for multiplication — ADV-OPT-01 (EVAL-01 recommends "investigate")
- SIMD vectorization for bulk gate operations — ADV-OPT-03
- Multi-threaded circuit building — ADV-OPT-04
- Automatic depth/ancilla tradeoff (RCA vs CLA selection) — OPT-01
- Modular arithmetic via Toffoli gates (for Shor's algorithm) — FTE-02
- Quantum counting (`ql.count_solutions`) for exact M estimation — ADV-01
- Fixed-point amplitude amplification — ADV-02
- Custom state preparation (non-uniform initial superposition) — ADV-03
- SAT/3-SAT oracle auto-generation from CNF formulas — SPEC-01
- Database search oracle from classical data structure — SPEC-02

### Out of Scope

- Direct/immediate execution mode — future direction, keep circuit compilation approach
- Hardware integration — OpenQASM export handles most cases
- ML framework integration — requires stable API first, complex integration
- Real-time debugging — complex infrastructure requirement
- GUI interface — programmatic API sufficient (pixel-art visualization is image output, not interactive GUI)
- Direct quantum state access — violates no-cloning theorem
- Automatic qubit cloning — physically impossible

## Context

**Architecture:** Three-layer stateless design — C backend (gate primitives, circuit management, integer operations) -> Cython bindings -> Python frontend (qint/qbool classes, operator overloading). All functions take explicit parameters; no global state.

**Current state:** v4.0 shipped — Grover's algorithm and amplitude estimation complete. Dual arithmetic backends: QFT (phase rotations) and Toffoli (CCX/CX/X only), with Toffoli as default. CDKM ripple-carry adder and Brent-Kung carry look-ahead adder for all 4 variants (QQ/CQ/cQQ/cCQ). Schoolbook multiplication and restoring division via Toffoli add/sub. MCX gates auto-decomposed via AND-ancilla pattern. CCX->Clifford+T decomposition with ~120 hardcoded sequence C files. T-count reporting (exact when Clifford+T active, 7*CCX estimate otherwise). Cross-backend verification suite proves Toffoli/QFT equivalence. `@ql.compile` supports ancilla tracking, inverse/adjoint generation, auto-uncompute, and `ql.qarray` arguments. `ql.grover()` with lambda predicate auto-synthesis, BBHT adaptive search, and `@ql.grover_oracle` decorator. `ql.amplitude_estimate()` with IQAE variant (no QFT). Pixel-art circuit visualization scaling to 200+ qubits. 157 new Grover/AE tests on top of exhaustive verification suite (8,365+ tests). Variable-width quantum integers (1-64 bits). Automatic uncomputation with dependency tracking. CNOT-based quantum copy. Memory-safe Python-to-C bridge.

**Codebase:**
- ~1,059,000 lines of code (604K C, 395K Python, 60K Cython)
- Version 0.1.0
- Tech stack: Python 3.11+, Cython, C backend, Qiskit (optional verification)

**Performance:** Benchmarks in `circuit-gen-results/` demonstrate speed and memory superiority over Qiskit, Cirq, PennyLane, and other backends for QFT circuits up to 2000 variables.

**Documentation:**
- README.md with Quick Start, API Reference, Examples
- NumPy-style Python docstrings
- Doxygen-style C header documentation
- Codebase analysis in `.planning/codebase/`

**Target audience:** Open source quantum computing community.

**Known limitations:**
- qint_mod * qint_mod raises NotImplementedError (by design)
- apply_merge() placeholder for future phase rotation merging
- Nested quantum conditionals require quantum-quantum AND implementation (future work)
- _reduce_mod result corruption (BUG-MOD-REDUCE) — needs different circuit structure for larger moduli
- Controlled multiplication corrupts result register (BUG-COND-MUL-01) — not yet investigated
- MSB comparison leak in division (BUG-DIV-02) — 9 cases per div/mod test file
- Dirty ancilla from widened comparisons (gt/le) — known limitation, not a correctness bug
- Mixed-width QFT addition off-by-one (BUG-WIDTH-ADD) — discovered in v1.8
- Layer-based uncomputation tracking unreliable when optimizer parallelizes gates — future: use instruction counter
- QFT controlled QQ addition CCP rotation errors at width 2+ (BUG-CQQ-QFT) — discovered in v3.0
- QFT division/modulo pervasively broken at all tested widths (BUG-QFT-DIV) — discovered in v3.0
- BK CLA subtraction falls back to RCA (carry-copy ancilla not uncomputed in reverse)
- Kogge-Stone CLA stubs return NULL (Brent-Kung only implementation)
- 32-bit multiplication segfault (buffer overflow in C backend) — discovered in v2.2

## Constraints

- **Architecture**: Keep `add_gate` circuit-building approach; direct execution is future work
- **Compatibility**: Maintain Python API compatibility in future versions
- **Performance**: Circuit generation must remain efficient for large circuits

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Bottom-up restructuring (C first) | Foundation must be solid before adding features | ✓ Good — clean modular C backend |
| Open source release target | Requires clean code, docs, tests | ✓ Good — v1.0 shipped |
| Keep circuit compilation model | Direct execution is future; current approach works | ✓ Good — works well |
| types.h as foundation module | Single source of truth for shared types | ✓ Good — clean dependencies |
| Right-aligned qubit array layout | Supports variable-width with minimal changes | ✓ Good — 1-64 bits work |
| MAXLAYERINSEQUENCE for QQ_mul | Original formula underestimated layer needs | Revisit — may need optimization |
| Single README format | GitHub-rendered, accessible without build | ✓ Good — easy to maintain |
| Stateless C backend | Global state eliminated for cleaner architecture | ✓ Good — v1.1 complete |
| Multi-controlled gates via large_control | Supports n-controlled X without ancilla qubits | ✓ Good — efficient for comparisons |
| In-place comparison pattern | Subtract-add-back preserves operands without temp allocation | ✓ Good — memory efficient |
| Auto-width qint initialization | qint(5) calculates minimum bits automatically | ✓ Good — user-friendly API |
| Weak references for dependencies | Prevents circular reference memory leaks | ✓ Good — enables safe GC |
| LIFO cascade uncomputation | Reverse creation order for correct quantum state | ✓ Good — verified correct |
| Mode capture at creation | Immutable per-qbool behavior, predictable | ✓ Good — no retroactive changes |
| Scope-based cleanup | Automatic uncomputation in `with` block exit | ✓ Good — Python-idiomatic |
| %.17g precision for angle export | Preserves full double precision in OpenQASM | ✓ Good — lossless rotation export |
| Delegation pattern for legacy API | Old circuit_to_opanqasm() delegates to new impl | ✓ Good — fixed 14 bugs, backward compatible |
| try-finally for C memory in Cython | Guaranteed free() even on exceptions | ✓ Good — no memory leaks |
| Subprocess isolation for verification | C backend doesn't deallocate qubits in-process | ✓ Good — 18/18 tests pass reliably |
| MSB-first bit extraction for Qiskit | Qiskit bitstrings have highest qubit index leftmost | ✓ Good — correct result extraction |
| Draper QFT qubit mapping fix | QQ_add target bits were offset incorrectly | ✓ Good — all addition tests pass |
| CCP decomposition for QQ_mul | Original multiplication algorithm was flawed | ✓ Good — 272/272 multiplication tests pass |
| xfail for discovered bugs | Document bugs without blocking test runs | ✓ Good — 968 xfail create future fix backlog |
| Separate result vs ancilla verification | gt/le leave ancilla dirty by design | ✓ Good — clear test expectations |
| Positional value + keyword width for qint in arrays | Fixes constructor parameter swap | ✓ Good — correct array initialization |
| Comparison results persist without auto-uncompute | Matches Phase 29-16 pattern, prevents GC gate reversal | ✓ Good — fixes equality inversion |
| MSB-first qubit ordering for C backend comparisons | C backend expects MSB-first, Python was passing LSB-first | ✓ Good — fixes bit-order reversal |
| LSB-aligned CNOT bit copies for widened comparisons | Zero-extension for proper unsigned semantics | ✓ Good — fixes MSB boundary errors |
| Target index formula: 64 - comp_width + i_bit | Correct LSB alignment for mixed-width operations | ✓ Good — all ordering tests pass |
| max_bit_pos = bits - divisor.bit_length() | Prevents divisor<<bit_pos overflow in restoring division | ✓ Good — BUG-DIV-01 fixed |
| matrix_product_state simulator for division tests | Statevector needs 137GB+ for 33+ qubit circuits | ✓ Good — handles 44+ qubits |
| Remove qint wrapping in qarray _inplace_binary_op | All 6 qint in-place operators handle int natively via CQ_* | ✓ Good — eliminates temp allocations |
| Defer BUG-MOD-REDUCE (scaling issues) | Beauregard approach hits duplicate qubit and memory issues | — Pending — needs different approach |
| Layer tracking on all qint operations | Required for correct scope-based uncomputation | ✓ Good — fixes uncomputation regression |
| Strict < for LAZY scope comparison | Prevents scope-0 top-level qints from auto-uncomputing | ✓ Good — fixes 975+ test failures |
| CNOT-based quantum copy via Q_xor | Faithful quantum state duplication preserving superposition | ✓ Good — 70 tests pass |
| XOR-into-zero copy pattern for binary ops | Replaces classical value init in add/sub/radd | ✓ Good — preserves quantum state |
| Shift=0 short-circuit in lshift/rshift | Avoids unnecessary mul/div circuits | ✓ Good — prevents memory explosion |
| qarray __setitem__ enables element mutation | Replaces TypeError with working assignment | ✓ Good — all 9 augmented operators work |

---
| Capture-replay over abstract tracing | Compatible with Cython layer, no operator rewrites | ✓ Good — works with existing architecture |
| Python-level gate list optimizer | Simpler than C-level, functionally equivalent | ✓ Good — cancels inverse pairs, merges adjacent |
| Controlled variant derivation | Correct quantum semantics vs post-hoc control | ✓ Good — both variants eagerly cached |
| Eager caching of controlled+uncontrolled | Avoids redundant re-capture | ✓ Good — separate cache entries |
| Pure Python (PIL) renderer first | Simpler to build, optimize to C only if needed | ✓ Good — renders 200+ qubits in <5s |
| Pixel-art over ASCII for large circuits | ASCII unusable beyond ~20 qubits; pixel art scales to 200+ | ✓ Good — 200 qubits / 10K gates verified |
| NumPy bulk rendering over per-pixel ImageDraw | Performance at scale (10K+ gates) | ✓ Good — 54MB image in <5s |
| 3x3 pixel cells for overview mode | 2px gate + 1px gap gives clean pixel art | ✓ Good — compact and readable |
| 12px cells with text labels for detail mode | Accommodates 2-char labels (Rx, Ry) | ✓ Good — readable gate labels |
| Auto-zoom with AND logic (both thresholds) | Keep detail for circuits large in only one dimension | ✓ Good — sensible default behavior |
| Only track forward calls when ancillas exist | In-place functions without ancillas don't need tracking | ✓ Good — avoids false double-forward errors |
| f.inverse as @property returning proxy | Enables f.inverse(x) call syntax | ✓ Good — clean API |
| f.adjoint as @property (standalone) | No forward tracking needed for pure adjoint | ✓ Good — separate use case |
| Auto-uncompute triggers in __call__ | After both replay and capture paths | ✓ Good — consistent behavior |
| Cache key includes qubit_saving mode | Mode change triggers recompilation | ✓ Good — correct semantics |
| Iteration protocol for qarray cdef access | _elements is cdef attribute; iteration uses __iter__ | ✓ Good — Python-accessible |
| Cache key uses ('arr', length) tuple | Distinguishes qarray from qint widths | ✓ Good — unambiguous caching |
| Profile before optimizing (v2.2 principle) | Avoid premature optimization — measure first | ✓ Good — all phases data-driven |
| Hardcoded sequences for widths 1-16 | Eliminate runtime QFT generation for common widths | ✓ Good — ~80K generated C |
| Unified generation script for all variants | Single source of truth for 4 addition variants | ✓ Good — reproducible |
| Two C entry points per hot path (QQ + CQ) | Clean API vs single function with NULL check | ✓ Good — type-safe |
| Stack-allocated gate_t in run_instruction | add_gate() copies via memcpy; safe for stack | ✓ Good — eliminates per-gate malloc |
| Arena allocator skipped | Remaining allocs are amortized realloc — not worth complexity | ✓ Good — evidence-based |
| Defer CYT-04 nogil to Phase 60 | Python call dependencies in Cython accessors | ✓ Good — applied with C migration |
| Keep all addition widths 1-16 hardcoded | Phase 62 data: 2-6x dispatch speedup, 192ms import justified | ✓ Good — data-driven |
| Segmented QFT/IQFT optimization | Independent segment optimization enables clean sharing | ✓ Good — 32.9% source reduction |
| Packed QFT layout for shared arrays | Fewer layers from _generate_qft_layers() packed layout | ✓ Good — const sharing works |
| Const vs mutable separation for sharing | Static const for QQ/cQQ, init helpers for CQ/cCQ | ✓ Good — type-safe sharing |
| Multiplication: "investigate" not "hardcode" | 48x addition cost but binary size impact needs study | — Pending — deferred to future |
| Bitwise: "skip" hardcoding | Max 288us generation, trivial cost | ✓ Good — definitively closed |
| Division: "skip" hardcoding | Python-level loop cost, not C sequence generation | ✓ Good — definitively closed |
| 15% regression tolerance | Accounts for ~8% stdev observed in benchmarks | ✓ Good — prevents false positives |

---
| Toffoli arithmetic as default mode | Fault-tolerant circuits should be default for error-correction readiness | ✓ Good — QFT available via opt-out |
| CDKM ripple-carry before CLA | Simpler algorithm, 1 ancilla, proven correct before optimizing depth | ✓ Good — solid foundation |
| CQ via temp-register QQ approach | Direct MAJ/UMA simplification was buggy; X-init temp + QQ adder + X-cleanup is provably correct | ✓ Good — BUG-CQ-TOFFOLI fixed |
| BK CLA compute-copy-uncompute pattern | In-place quantum CLA ancilla uncomputation impossible with single pass | ✓ Good — correct BK at ~50% depth reduction |
| AND-ancilla MCX decomposition | MCX(3)->3 CCX via AND-ancilla eliminates all 3+ control gates | ✓ Good — zero MCX in all Toffoli output |
| CCX->Clifford+T exact 15-gate sequence | 2H+4T+3Tdg+6CX per CCX, matches literature | ✓ Good — 4:3 T/Tdg ratio verified |
| Dual T-count formula | Exact when T gates present, 7*CCX estimate otherwise | ✓ Good — accurate for both modes |
| Inline CQ/cCQ classical-bit generators | Skip gates at zero-bit positions (7-14T per position saved) | ✓ Good — significant T-count reduction |
| Split ToffoliAddition.c by algorithm | CDKM/CLA/Helpers modules vs monolithic file | ✓ Good — maintainable at ~800 lines each |
| ~120 Clifford+T hardcoded C files | Pre-computed for CDKM + BK CLA, all 4 variants, widths 1-8 | ✓ Good — zero runtime decomposition overhead |
| Division via Python-level composition | Reuse existing restoring division with Toffoli add/sub underneath | ✓ Good — no new C division code needed |

---
| branch(prob) = Ry(2*arcsin(sqrt(prob))) | Probability-to-angle conversion for intuitive API | ✓ Good — branch(0.5) = H gate equivalent |
| Tracing approach for predicate-to-oracle | Call predicate with real qint objects, reuse existing operators | ✓ Good — no AST parsing needed |
| BBHT adaptive search with LAMBDA=6/5 | Standard exponential backoff for unknown M | ✓ Good — O(sqrt(N)) expected queries |
| IQAE over QPE-based amplitude estimation | No QFT circuit required, lower depth | ✓ Good — practical for NISQ |
| X-MCZ-X diffusion pattern | Zero ancilla, O(n) gates, reusable building block | ✓ Good — matches literature standard |
| emit_p_raw for manual S_0 path | Avoids double-control bug in PhaseProxy.__iadd__ | ✓ Good — both manual and API paths work |
| Oracle validation at circuit generation time | First call validates compute-phase-uncompute ordering | ✓ Good — fails fast with clear error |
| Clopper-Pearson CI for IQAE | Tighter than Chernoff-Hoeffding bounds | ✓ Good — accurate confidence intervals |
| H gate (emit_h) for Grover iterations | H^2=I exact self-inverse; Ry(pi/2)^2 != I | ✓ Good — correct interference pattern |
| BUG-CMP-MSB fix: comp_width-1 MSB indexing | Pre-existing bug — hardcoded qubit 63 for all widths | ✓ Good — inequality operators work for all widths |

---
*Last updated: 2026-02-22 after v4.0 milestone completion*
