# Project Research Summary

**Project:** Quantum Assembly
**Domain:** Quantum programming framework with C backend and Python bindings
**Researched:** 2026-01-25
**Confidence:** HIGH

## Executive Summary

Quantum Assembly is a quantum circuit generation framework that differentiates itself through high-level quantum data types (qint, qbool) with operator overloading, providing a significantly better developer experience than gate-level frameworks like Qiskit or Cirq. The current architecture follows the industry-standard pattern of C/C++ backend for performance with Python bindings for usability, matching the approach used by major frameworks. However, the codebase exhibits several critical architectural anti-patterns common in early-stage quantum frameworks: heavy reliance on global state, unclear memory ownership between C and Python layers, and hardcoded integer sizes that prevent variable-width arithmetic.

The recommended approach prioritizes architectural cleanup over feature additions. Research reveals that the framework's core differentiation (high-level types with natural syntax) is already present and working, but critical memory management issues and global state dependencies create a fragile foundation. The path forward involves incremental refactoring following proven patterns from the scientific Python ecosystem: eliminating global state through context objects, establishing clear ownership semantics between layers, and separating concerns into focused modules. This cleanup enables the planned feature additions (variable-width integers, extended arithmetic operations, bit operations) without accumulating technical debt.

Key risks center on the complexity of C/Python memory management and the temptation to attempt "big bang" refactoring. Mitigation requires establishing comprehensive characterization tests before any refactoring, using Valgrind and AddressSanitizer systematically, and enforcing incremental changes with frequent integration. The quantum-specific risks (ancilla leakage, circuit depth explosion) are manageable through established patterns from the quantum computing literature, but require careful implementation during arithmetic operations expansion.

## Key Findings

### Recommended Stack

The current technology stack is solid and aligns with 2025-2026 scientific Python best practices. The C backend compiled with GCC and Cython 3.2.4 for bindings matches exactly how mature projects like NumPy and SciPy are built. No major stack changes are needed, but the development tooling should be enhanced with modern quality assurance tools.

**Core technologies:**
- **Cython 3.2.4**: C/Python binding layer — industry standard for scientific computing, used by NumPy/SciPy/scikit-learn, production-stable release from January 2026
- **setuptools + cythonize**: Build system — current setup works correctly, don't change unless complexity increases 10x
- **pytest 9.0.2 + pytest-cython**: Testing framework — latest stable with 1300+ plugins, pytest-cython enables testing Cython .pyx code
- **Valgrind 3.26.0 + AddressSanitizer**: Memory debugging — Valgrind for comprehensive weekly checks, ASan for fast daily development with `-fsanitize=address`
- **Ruff 0.14.14**: Code quality — replaces Black/Flake8/isort in one tool, 10-100x faster, used by FastAPI/Pandas/PyTorch
- **Sphinx 9.1.0 + numpydoc**: Documentation — standard for scientific Python, NumPy-style docstrings

**Development enhancements needed:**
- Add pre-commit hooks for automatic linting (Ruff, mypy)
- Enable ASan builds via environment variable for daily memory testing
- Set up GitHub Actions CI matrix for Python 3.10-3.13 and multiple platforms
- Add Scalene profiler for performance optimization work

### Expected Features

The quantum programming framework landscape has clear table stakes and differentiators. Quantum Assembly already possesses its key competitive advantages but is missing some expected baseline features.

**Must have (table stakes):**
- Universal gate set (H, CNOT, Rx, Ry, Rz) — likely present, verify completeness
- OpenQASM 3.0 export — critical gap, industry moving from 2.0 to 3.0 with mid-circuit measurement and real-time conditionals
- Circuit visualization — essential for debugging, status unknown
- Complete arithmetic operations — addition/subtraction present, multiplication/comparison partial, need modular arithmetic
- Automatic circuit optimization — gate merging and dead code elimination are becoming table stakes
- Clear error messages — need to audit compilation error quality

**Should have (competitive differentiators):**
- High-level data types (qint/qbool) — **ALREADY PRESENT, major differentiator**, Qiskit/Cirq don't have this
- Operator overloading (+, -, *, etc.) — **ALREADY PRESENT**, significantly better DX than competitors
- Variable-width integers — planned, enables memory efficiency and flexibility
- Bit operations for qint — planned, required for many algorithms (shifts, rotates, bitwise AND/OR/XOR)
- QFT-based arithmetic — more efficient than ripple-carry, consider after basic arithmetic complete
- Circuit templates library — pre-built QFT, Grover components, phase estimation algorithms

**Defer (v2+):**
- ML framework integration (PennyLane-style) — requires stable API first, complex integration
- Multiple hardware backends beyond OpenQASM — export handles most cases
- Real-time debugging (CircInspect-style) — complex infrastructure requirement
- Formal verification and type safety — nice-to-have, not critical yet
- GUI interface — programmatic API and CLI sufficient for now

**Anti-features to avoid:**
- Direct quantum state access (violates no-cloning theorem)
- Automatic qubit cloning (physically impossible, causes subtle bugs)
- Unbounded quantum resources (unrealistic for real hardware)
- Over-abstraction hiding circuit details (need both high and low level APIs)

### Architecture Approach

The current three-layer architecture (C backend → Cython bindings → Python API) follows industry best practice, but the implementation has critical flaws that prevent it from scaling. The research identifies five key architectural patterns used by mature frameworks: opaque handle/context objects instead of global state, strict separation of concerns with single-responsibility modules, RAII-style resource management with clear ownership, intermediate representation as DAG for optimization, and layered API design supporting both low and high-level usage.

**Major architectural issues requiring remediation:**
1. **Global state dependency** — `extern circuit_t *circuit` and `QPU_state` prevent multiple circuits, break thread safety, make testing impossible
2. **Mixed concerns** — QPU.c does allocation, optimization, insertion, and state management in 187 lines
3. **Unclear ownership** — quantum_int_t allocates struct but circuit owns qubits, creating memory leak risk
4. **Leaky abstractions** — Python layer directly accesses C memory layout and constants like INTEGERSIZE
5. **Hardcoded sizes** — INTEGERSIZE=8 constant baked into operations prevents variable-width integers

**Recommended component structure:**
1. **Core Data Structures** — circuit_t, gate_t, qubit_allocator_t type definitions
2. **Circuit Builder** — circuit_create(), circuit_add_gate(), circuit_free() with explicit context
3. **Circuit Optimizer** — layer assignment and gate merging as separate module
4. **Gate Library** — gate construction primitives (X, Y, Z, H, CNOT, etc.)
5. **Quantum Operations** — high-level arithmetic and logic built on circuit builder
6. **Compiler** — OpenQASM and other format export
7. **Binding Layer** — Cython wrappers with proper lifetime management
8. **Python Frontend** — user-facing QuantumCircuit, QInt, QBool classes

### Critical Pitfalls

Research identified 20+ pitfalls, with these five being most critical for the project:

1. **Mixing C and Python memory allocators** — Memory allocated in C (malloc) freed by Python GC or vice versa causes segfaults and corruption. Prevention: document ownership clearly, use PyCapsule destructors, never use C functions on Python objects. This must be addressed in Phase 1 before any feature work.

2. **Global state in C library with multiple Python contexts** — Global `circuit`, `QPU_state`, `R0-R3` registers shared across all Python objects, breaking thread safety and testability. Prevention: pass circuit_t* context to all functions, use opaque handles. Critical for Phases 2-4.

3. **Incorrect sizeof() usage with pointer types** — Current code uses `sizeof(integer)` where `integer` is pointer, allocating 8 bytes instead of full struct size (Integer.c lines 31, 37). Causes memory corruption. Prevention: always use `sizeof(type_name)` or `sizeof(*ptr)`. Must fix in Phase 1.

4. **Hardcoded integer sizes breaking variable-width operations** — INTEGERSIZE=8 constant prevents the planned variable-width feature. Prevention: parameterize all functions with width from day one, dynamic allocation based on runtime width. Blocks Phase 2 implementation.

5. **Big bang refactoring instead of incremental** — Attempting to fix all issues simultaneously creates unmergeable branches and regression bugs. Prevention: strangler pattern, feature flags, time-box changes to 1 week maximum, merge at least weekly. Critical discipline for ALL phases.

**Additional high-risk pitfalls:**
- **Uninitialized structure fields** — sequence_t allocated but pointers not initialized (IntegerAddition.c lines 230-250)
- **Missing memory allocation failure checks** — no NULL checks after malloc/calloc throughout codebase
- **Ancilla qubit leakage** — temporary qubits not uncomputed, leaving entanglement (test.py lines 66-68 has increment instead of decrement)
- **Refactoring without characterization tests** — changing code without tests that document current behavior risks silent regressions

## Implications for Roadmap

Based on research, the project requires foundational cleanup before feature additions. The existing differentiation (high-level types) is already working, but architectural issues create a fragile base for expansion.

### Phase 1: Foundation Cleanup (C Layer Architecture)
**Rationale:** Must eliminate global state and fix memory bugs before building features. Attempting to add variable-width integers or extended arithmetic on the current foundation will compound technical debt and create cascading failures.

**Delivers:**
- All C functions take explicit circuit_t* context parameter (no globals)
- Memory ownership documented at every allocation
- sizeof() bugs fixed (Integer.c corrected)
- Uninitialized structure bugs fixed (IntegerAddition.c, IntegerComparison.c)
- malloc NULL checks added throughout
- Characterization test suite capturing current behavior

**Addresses:** None of the user-facing features yet — this is pure architectural cleanup

**Avoids:**
- Pitfall 1 (C/Python memory mixing) — clear ownership established
- Pitfall 2 (sizeof bugs) — all instances corrected
- Pitfall 4 (global state) — context object pattern implemented
- Pitfall 19 (refactoring without tests) — characterization tests written first

**Stack usage:** pytest + pytest-cython for testing, Valgrind + ASan for memory validation, Ruff for code quality

**Time estimate:** 2-3 weeks (high risk, touches everything)

**Research flag:** LOW — patterns well-documented in opaque pointer literature and scientific Python ecosystem

---

### Phase 2: Memory Architecture (Ownership and Allocation)
**Rationale:** With global state eliminated, establish clear memory ownership model between circuit and quantum types. Required before variable-width integers which need dynamic allocation.

**Delivers:**
- Qubit allocator module (qubit_allocator.c/h) centralizing lifecycle management
- qint_create() takes circuit_t* context and width parameter
- qint_free() returns qubits to pool
- quantum_int_t borrows qubits from circuit (documented ownership)
- Ancilla allocation explicit and trackable

**Addresses:**
- Variable-width integers foundation (removes INTEGERSIZE hardcoding)
- Must-have feature: proper memory management for stability

**Avoids:**
- Pitfall 3 (unclear ownership) — ownership model documented and implemented
- Pitfall 5 (hardcoded sizes) — width parameterized throughout
- Pitfall 6 (missing allocation checks) — centralized allocator validates
- Pitfall 16 (ancilla leakage) — explicit ancilla lifecycle tracking

**Stack usage:** Valgrind/ASan for validation, pytest for allocator unit tests

**Time estimate:** 1-2 weeks (moderate risk, changes type creation)

**Research flag:** LOW — RAII patterns and arena allocation well-documented

---

### Phase 3: Module Separation (Code Organization)
**Rationale:** With clean architecture foundation, separate QPU.c god object into focused modules. This is low-risk internal refactoring that improves maintainability without changing APIs.

**Delivers:**
- circuit_builder.c — create/destroy/add gates
- circuit_optimizer.c — layer assignment and gate merging (extracted from QPU.c)
- circuit_allocator.c — memory management helpers
- operations/arithmetic.c, operations/comparison.c, operations/logic.c — extracted from Integer*.c
- Clear dependency graph between modules

**Addresses:** Internal code quality, no user-facing features

**Avoids:**
- Pitfall anti-pattern "god object" — QPU.c responsibilities separated
- Future maintenance burden — changes localized to specific modules

**Stack usage:** Existing test suite, no new tools needed

**Time estimate:** 1-2 weeks (low risk, internal refactoring)

**Research flag:** NONE — straightforward code organization, skip research

---

### Phase 4: Variable-Width Integer Support
**Rationale:** First major feature addition, enabled by Phase 2 memory work. This is a table-stakes feature that unblocks bit operations and extended arithmetic.

**Delivers:**
- QInt(width=N) constructor for arbitrary bit-width quantum integers
- Dynamic allocation based on width parameter
- Width validation in arithmetic operations (compatible widths)
- Tests with mixed-width integers (8-bit + 32-bit cases)
- Update Python API to expose width parameter

**Addresses:**
- Must-have feature: variable-width integers for memory efficiency
- Foundation for Phase 5 (bit operations) and Phase 6 (extended arithmetic)

**Avoids:**
- Pitfall 5 (hardcoded sizes) — now fully parameterized
- Pitfall 8 (cache invalidation) — precompiled sequence cache updated with width in key

**Stack usage:** pytest for mixed-width test cases, ASan to catch buffer overflows

**Time estimate:** 2 weeks (moderate complexity, needs careful testing)

**Research flag:** MEDIUM — need to research optimal gate sequences for variable-width arithmetic, may benefit from literature review

---

### Phase 5: Bit Operations for qint
**Rationale:** With variable-width integers working, add bit-level operations required by many quantum algorithms. Complements arithmetic operations.

**Delivers:**
- Bit shifts (left/right logical and arithmetic)
- Bit rotations (left/right)
- Bitwise operations (AND, OR, XOR, NOT) on quantum integers
- Python operator overloading (<<, >>, &, |, ^, ~)
- Gate sequence optimization for bit operations

**Addresses:**
- Should-have feature: bit operations needed for algorithm implementations
- Differentiator: natural Python syntax for quantum bit operations

**Avoids:**
- Pitfall 10 (depth explosion) — use efficient quantum bit operation circuits from literature

**Stack usage:** pytest-benchmark for performance testing, Scalene for profiling

**Time estimate:** 2 weeks (medium complexity, patterns available in literature)

**Research flag:** MEDIUM — research optimal quantum bit shift/rotate circuits before implementing

---

### Phase 6: Extended Arithmetic Operations
**Rationale:** Complete the arithmetic operation set. Builds on variable-width and bit operation foundations.

**Delivers:**
- Complete multiplication (currently partial)
- Division and modular division
- Modular arithmetic (add/sub/mul mod N)
- Exponentiation (classical and quantum exponents)
- Enhanced comparison (>=, <=, not just >, <, ==)
- Circuit optimization specific to arithmetic (QFT-based alternatives)

**Addresses:**
- Must-have feature: complete arithmetic for algorithm implementations
- Should-have feature: QFT-based arithmetic for efficiency gains

**Avoids:**
- Pitfall 10 (circuit depth explosion) — research optimal algorithms first
- Pitfall 17 (ignoring error rates) — consider error-aware optimization

**Stack usage:** pytest-benchmark for depth comparison, literature from PennyLane quantum arithmetic

**Time estimate:** 3-4 weeks (high complexity, multiple operations)

**Research flag:** HIGH — should run `/gsd:research-phase` for QFT arithmetic and modular operations to identify optimal implementations

---

### Phase 7: Circuit Optimization and Compilation
**Rationale:** With complete feature set, optimize generated circuits and upgrade output format. This addresses table-stakes expectations.

**Delivers:**
- Automatic gate merging (identity elimination, inverse cancellation)
- Commutation-based reordering
- OpenQASM 3.0 export (upgrade from 2.0, adds mid-circuit measurement)
- Circuit statistics (depth, gate count, qubit usage)
- Visualization output (text-based circuit diagrams)

**Addresses:**
- Must-have feature: OpenQASM 3.0 (industry standard as of 2026)
- Must-have feature: circuit optimization (increasingly table stakes)
- Must-have feature: visualization for debugging

**Avoids:**
- Feature gap compared to competitors who have automatic optimization

**Stack usage:** OpenQASM 3.0 specification, Sphinx for documenting optimization passes

**Time estimate:** 2-3 weeks (medium complexity, optimization is well-documented)

**Research flag:** LOW — DAG optimization patterns well-established, OpenQASM 3.0 spec is public

---

### Phase 8: Python API Stabilization and Documentation
**Rationale:** Final phase before potential open source release. Polish user-facing API and create comprehensive documentation.

**Delivers:**
- Updated Python bindings reflecting all C API changes (Phases 1-3)
- QuantumCircuit context manager (proper resource cleanup)
- Comprehensive docstrings (NumPy style with numpydoc)
- Sphinx documentation with examples
- API reference auto-generated from docstrings
- Tutorial notebooks demonstrating features
- Pre-commit hooks installed (Ruff, mypy)

**Addresses:**
- Must-have feature: clear error messages and good documentation
- Developer experience polish

**Avoids:**
- Pitfall 18 (breaking changes frustrate users) — semantic versioning, deprecation warnings
- Pitfall 20 (removing "dead" code) — deprecation period before any removals

**Stack usage:** Sphinx 9.1.0, numpydoc 1.11.0, Ruff 0.14.14, mypy, Furo theme

**Time estimate:** 2-3 weeks (writing and polish)

**Research flag:** NONE — documentation tools and patterns well-established

---

### Phase Ordering Rationale

**Critical path:** Phases 1 → 2 → 4 → 6 → 8
- Phase 1 (Foundation) unblocks all other work by eliminating architectural blockers
- Phase 2 (Memory) enables Phase 4 (variable-width integers)
- Phase 4 enables Phase 5 (bit operations) and Phase 6 (arithmetic)
- Phase 8 (API/docs) comes last when features are stable

**Parallel opportunities:**
- Phases 3 (Module Separation) and 2 (Memory Architecture) can proceed in parallel after Phase 1
- Phases 5 (Bit Operations) and 6 (Extended Arithmetic) can proceed in parallel after Phase 4
- Phase 7 (Optimization) can proceed in parallel with Phase 6 (uses same circuits)

**Dependency logic:**
- Arithmetic operations depend on variable-width integers (Phase 4 before 6)
- Variable-width depends on clean memory model (Phase 2 before 4)
- Clean memory model depends on eliminating global state (Phase 1 before 2)
- Documentation depends on stable API (Phases 1-7 before 8)

**Risk mitigation sequencing:**
- Highest-risk architectural changes (Phase 1) come first when codebase is smallest
- Incremental feature additions (Phases 4-6) come after foundation is solid
- Each phase has clear deliverables and can be validated independently
- No phase exceeds 4 weeks (enforcing incremental approach)

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 4 (Variable-Width Integers):** Research optimal gate sequences for variable-width addition/subtraction, review PennyLane and Qiskit implementations
- **Phase 5 (Bit Operations):** Research quantum bit shift/rotate circuits, limited literature on quantum bitwise operations
- **Phase 6 (Extended Arithmetic):** HIGH priority for `/gsd:research-phase` — QFT-based arithmetic, modular operations, and exponentiation have complex design space

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation Cleanup):** Opaque pointer pattern well-documented, context objects standard practice
- **Phase 2 (Memory Architecture):** RAII and arena allocation patterns well-known
- **Phase 3 (Module Separation):** Straightforward code organization
- **Phase 7 (Optimization):** DAG optimization and OpenQASM 3.0 well-documented
- **Phase 8 (Documentation):** Sphinx and scientific Python documentation practices established

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Cython, pytest, Sphinx versions verified via PyPI (Jan 2026). Current setup already correct. No changes needed beyond tooling additions. |
| Features | MEDIUM-HIGH | Table stakes and differentiators clear from framework comparisons. OpenQASM 3.0 and optimization increasingly expected. Quantum-specific feature complexity assessed via PennyLane research. |
| Architecture | HIGH | Three-layer pattern standard in scientific Python. Anti-patterns identified via codebase audit. Opaque pointer and DAG patterns well-documented in industry literature. |
| Pitfalls | HIGH | C/Python memory issues documented in official Python docs. Memory bugs verified by static analysis. Quantum-specific pitfalls from recent 2025 research papers. Refactoring risks from legacy code literature. |

**Overall confidence:** HIGH

The recommended approach is grounded in established patterns from the scientific Python ecosystem (NumPy, SciPy, Qiskit architecture) and verified through authoritative sources. The main uncertainty lies in quantum algorithm implementation details (optimal circuits for specific operations), which can be resolved through focused research during relevant phases.

### Gaps to Address

**Quantum arithmetic implementation details:** While the high-level architecture is clear, optimal gate sequences for variable-width arithmetic operations need literature review during Phase 4 and 6. PennyLane demos provide starting points, but may need to survey academic papers for state-of-the-art approaches.

**Circuit optimization trade-offs:** Phase 7 optimization work should research error-aware optimization (not just gate count/depth minimization). The balance between circuit depth and gate error rates for real hardware is evolving rapidly and may need current literature review in 2026.

**Cython 3.2.4 memory view behavior:** Some memory leak issues reported in older Cython versions. Phase 8 should validate that current Cython 3.2.4 has resolved memory view leaks, or implement workarounds from GitHub issue tracking.

**Cross-platform CI configuration:** GitHub Actions matrix for Python 3.10-3.13 and multiple OS (Ubuntu/macOS/Windows) needs setup during Phase 1. C compilation behavior differs across compilers (GCC vs Clang vs MSVC) — research CI configuration best practices from Scientific Python Development Guide.

## Sources

### Primary (HIGH confidence)

**Technology Stack:**
- [Cython PyPI](https://pypi.org/project/Cython/) — Version 3.2.4 confirmed (Jan 2026)
- [pytest PyPI](https://pypi.org/project/pytest/) — Version 9.0.2 confirmed (Dec 2025)
- [Sphinx PyPI](https://pypi.org/project/Sphinx/) — Version 9.1.0 confirmed (Dec 2025)
- [Ruff PyPI](https://pypi.org/project/ruff/) — Version 0.14.14 confirmed (Jan 2026)
- [Valgrind Documentation](https://valgrind.org/docs/manual/valgrind_manual.pdf) — Version 3.26.0 (Oct 2025)
- [Scientific Python Development Guide](https://scientific-python-cookie.readthedocs.io/en/latest/guides/docs/) — Documentation and CI patterns

**Quantum Framework Patterns:**
- [OpenQASM Live Specification](https://openqasm.com/) — Current standard
- [OpenQASM 3 Paper](https://arxiv.org/pdf/2104.14722) — Specification details
- [PennyLane Quantum Arithmetic Tutorial](https://pennylane.ai/qml/demos/tutorial_how_to_use_quantum_arithmetic_operators) — Implementation examples

**Architecture Patterns:**
- [Interrupt: Opaque Pointers in C](https://interrupt.memfault.com/blog/opaque-pointers) — Context object pattern
- [Circuit Transformations for Quantum Architectures](https://arxiv.org/pdf/1902.09102) — DAG-based optimization
- [Python Memory Management Documentation](https://docs.python.org/3/c-api/memory.html) — C/Python interop

**Pitfalls:**
- [Cython GitHub Issues](https://github.com/cython/cython/issues) — Memory leak tracking (#1638, #2828, #3046, #6850)
- [Memory Management Strategies for Quantum Simulators](https://www.mdpi.com/2624-960X/7/3/41) — Quantum-specific patterns
- [Scalable Memory Recycling for Quantum Programs](https://arxiv.org/abs/2503.00822) — Ancilla management

### Secondary (MEDIUM confidence)

**Framework Comparisons:**
- [Quantum Programming: Framework Comparison](https://postquantum.com/quantum-computing/quantum-programming/)
- [Top Quantum Programming Languages 2026](https://www.andhustechnologies.com/top-articles/top-quantum-programming-languages-you-should-learn-in-2026/)

**Legacy Code Refactoring:**
- [7 Techniques to Regain Control of Legacy Codebase](https://understandlegacycode.com/blog/7-techniques-to-regain-control-of-legacy/)
- [Legacy Code Refactoring: Best Practices](https://modlogix.com/blog/legacy-code-refactoring-tips-steps-and-best-practices/)

**Performance and Optimization:**
- [TDAG: Tree-based DAG Partitioning for Quantum Circuits](https://www.ornl.gov/publication/tdag-tree-based-directed-acyclic-graph-partitioning-quantum-circuits)
- [Quantum Circuit Design using Monte Carlo Tree Search](https://advanced.onlinelibrary.wiley.com/doi/10.1002/qute.202500093)

### Tertiary (LOW confidence)

**Emerging Practices:**
- [A Github Actions setup for Python projects in 2025](https://ber2.github.io/posts/2025_github_actions_python/) — CI configuration patterns
- [Quantum Error Correction: 2025 Trends](https://www.riverlane.com/blog/quantum-error-correction-our-2025-trends-and-2026-predictions) — Error-aware optimization context

---
*Research completed: 2026-01-25*
*Ready for roadmap: yes*
