# Project Milestones: Quantum Assembly

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
