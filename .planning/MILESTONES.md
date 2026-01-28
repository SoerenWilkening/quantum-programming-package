# Project Milestones: Quantum Assembly

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
- 1 day (v1.0 → v1.1)

**Git range:** `feat(11-01)` → `docs(15)`

**What's next:** v1.2 — bit shift operations, OpenQASM 3.0 export, advanced features

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

**Git range:** `feat(01-01)` → `feat(10-04)`

**What's next:** v1.1 (TBD) — bit shifts, OpenQASM 3.0, advanced features

---
