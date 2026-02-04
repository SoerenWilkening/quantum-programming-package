# Quantum Assembly

## What This Is

A quantum programming framework that enables writing quantum algorithms using standard programming constructs — operator overloading on variable-width quantum integers (qint, 1-64 bits) and quantum booleans (qbool), with Python's `with` statement implementing quantum conditionals. Operations compile to optimized quantum circuits via a C backend with Cython bindings. Includes circuit optimization, pixel-art circuit visualization scaling to 200+ qubits, statistics, OpenQASM 3.0 export, and Qiskit-based verification.

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

### Active

**Current Milestone: v2.0 — Function Compilation**

- [ ] `@ql.compile` decorator captures all gate sequences within a decorated function
- [ ] Merged sequences are optimized (gate merging, inverse cancellation) as a single unit
- [ ] Compiled functions execute the pre-optimized sequence on subsequent calls
- [ ] Classical parameters are parametric (compile once, not per-value)
- [ ] Compiled functions work inside `with` blocks (controlled execution)
- [ ] Compiled functions return quantum values (qint/qbool) usable in further operations

**Deferred bugs (carry forward):**
- Fix _reduce_mod result corruption (BUG-MOD-REDUCE) — needs fundamentally different circuit structure
- Fix controlled multiplication corruption (BUG-COND-MUL-01) — not yet investigated
- Fix MSB comparison leak in division (BUG-DIV-02) — 9 cases per div/mod test file
- Fix mixed-width QFT addition off-by-one (BUG-WIDTH-ADD) — discovered in Phase 43

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

**Current state:** v1.9 shipped — pixel-art circuit visualization complete. C-level data extraction with qubit compaction, NumPy pixel-art renderer with 10 gate colors, multi-qubit control lines/dots, two zoom levels (overview 3px + detail 12px with text labels), auto-zoom selection, and `ql.draw_circuit()` public API with lazy Pillow import. 47 visualization tests. Exhaustive verification suite with 8,365+ tests covering every operation category through the full pipeline (Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check). Clean modular C backend with types.h, circuit.h, arithmetic_ops.h, comparison_ops.h, bitwise_ops.h, circuit_output.h. Centralized qubit allocator with ownership tracking. Variable-width quantum integers (1-64 bits) with complete arithmetic, comparison, and initialization operations. Automatic uncomputation with dependency tracking, mode control (lazy/eager), and user override methods. Proper package structure with ql.array supporting multi-dimensional arrays, reductions, element-wise operations, and in-place element mutation. CNOT-based quantum copy for binary operations. Memory-safe Python-to-C bridge with Cython try-finally cleanup.

**Codebase:**
- ~221,387 lines of code (Python, Cython, C)
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
| Pure Python (PIL) renderer first | Simpler to build, optimize to C only if needed | ✓ Good — renders 200+ qubits in <5s |
| Pixel-art over ASCII for large circuits | ASCII unusable beyond ~20 qubits; pixel art scales to 200+ | ✓ Good — 200 qubits / 10K gates verified |
| NumPy bulk rendering over per-pixel ImageDraw | Performance at scale (10K+ gates) | ✓ Good — 54MB image in <5s |
| 3x3 pixel cells for overview mode | 2px gate + 1px gap gives clean pixel art | ✓ Good — compact and readable |
| 12px cells with text labels for detail mode | Accommodates 2-char labels (Rx, Ry) | ✓ Good — readable gate labels |
| Auto-zoom with AND logic (both thresholds) | Keep detail for circuits large in only one dimension | ✓ Good — sensible default behavior |

---
*Last updated: 2026-02-04 after v2.0 milestone start*
