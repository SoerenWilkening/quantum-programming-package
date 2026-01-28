# Quantum Assembly

## What This Is

A quantum programming framework that enables writing quantum algorithms using standard programming constructs — operator overloading on variable-width quantum integers (qint, 1-64 bits) and quantum booleans (qbool), with Python's `with` statement implementing quantum conditionals. Operations compile to optimized quantum circuits via a C backend with Cython bindings. Includes circuit optimization, visualization, and statistics.

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

### Active

**Milestone v1.2: TBD**

(Requirements to be defined in `/gsd:new-milestone`)

### Out of Scope

- Direct/immediate execution mode — future direction, keep circuit compilation approach
- Hardware integration — OpenQASM export handles most cases
- ML framework integration — requires stable API first, complex integration
- Real-time debugging — complex infrastructure requirement
- GUI interface — programmatic API sufficient
- Direct quantum state access — violates no-cloning theorem
- Automatic qubit cloning — physically impossible

## Context

**Architecture:** Three-layer stateless design — C backend (gate primitives, circuit management, integer operations) → Cython bindings → Python frontend (qint/qbool classes, operator overloading). All functions take explicit parameters; no global state.

**Current state:** v1.1 shipped. Clean modular C backend with types.h, circuit.h, arithmetic_ops.h, comparison_ops.h, bitwise_ops.h. Centralized qubit allocator with ownership tracking. Variable-width quantum integers (1-64 bits) with complete arithmetic, comparison, and initialization operations.

**Codebase:**
- ~70,900 lines of code (Python, Cython, C)
- Version 0.1.0
- Tech stack: Python 3.11+, Cython, C backend

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
- Multiplication tests segfault at certain widths (C backend issue, pre-existing)

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
| MAXLAYERINSEQUENCE for QQ_mul | Original formula underestimated layer needs | ⚠️ Revisit — may need optimization |
| Single README format | GitHub-rendered, accessible without build | ✓ Good — easy to maintain |
| Stateless C backend | Global state eliminated for cleaner architecture | ✓ Good — v1.1 complete |
| Multi-controlled gates via large_control | Supports n-controlled X without ancilla qubits | ✓ Good — efficient for comparisons |
| In-place comparison pattern | Subtract-add-back preserves operands without temp allocation | ✓ Good — memory efficient |
| Auto-width qint initialization | qint(5) calculates minimum bits automatically | ✓ Good — user-friendly API |

---
*Last updated: 2026-01-28 after v1.1 milestone*
