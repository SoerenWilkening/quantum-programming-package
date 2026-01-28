# Project Research Summary

**Project:** Quantum Assembly v1.2 - Automatic Uncomputation with Dependency Tracking
**Domain:** Quantum programming language compiler with automatic memory management
**Researched:** 2026-01-28
**Confidence:** HIGH

## Executive Summary

Automatic uncomputation requires tracking which intermediate qubits depend on which operations, then automatically generating inverse gate sequences when those intermediates go out of scope. Research confirms that the recommended approach is **Python-level dependency tracking with C-level reverse gate generation**, avoiding the complexity of retrofitting object lifecycle management into the existing stateless C backend while maintaining performance-critical circuit generation in C.

The existing three-layer architecture (Python frontend with Cython bindings to stateless C backend) naturally supports this pattern. Python already manages qint/qbool object lifetimes through garbage collection, so extending `__del__` to trigger uncomputation cascades aligns with the existing design. The key architectural decision is using `weakref.finalize` callbacks instead of `__del__` directly for reliability, and storing creation sequences at the Python level to enable C-level adjoint generation.

The primary risk is **incorrect uncomputation positioning** in the circuit, which can silently corrupt quantum states. Prevention requires layer-aware dependency graph analysis, validation that qubits needed for uncomputation haven't been modified, and comprehensive testing with conditional (`with` statement) contexts. Secondary risks include circular reference memory leaks (mitigated by single-ownership model), exponential cost blowup in nested expressions (requires immediate uncomputation mode), and incorrect reversal of multi-controlled gates (requires gate-type-specific inversion logic).

## Key Findings

### Recommended Stack

The core technology pattern is **Python dependency graph + weakref lifecycle management + C adjoint generation**, avoiding external dependencies and leveraging existing infrastructure.

**Core technologies:**
- **Python dict/list (native)**: Dependency storage — O(1) lookups, no external dependency, sufficient for parent→child relationships
- **weakref.finalize (PEP 442)**: Lifetime management — Reliable cleanup without `__del__` pitfalls, can be triggered manually for tests
- **weakref.ref**: Reference tracking — Track dependencies without preventing garbage collection, prevents circular reference issues
- **C reverse_gate_generator (new)**: Adjoint generation — Generate inverse sequences (X→X, P(θ)→P(-θ), reverse order), reuses existing gate types

**Why Python-level tracking:**
- Existing C backend is stateless by design (circuit_t is just gate storage, no object lifecycle)
- Python already manages qint/qbool object lifetimes through garbage collection
- Dependency graph mutations are infrequent (creation-time only, no runtime updates)
- Avoids duplicating Python's garbage collector in C

**Why NOT C-level tracking:**
- C has no weak reference equivalent (would require manual reference counting)
- Retrofitting object lifecycle into stateless C backend breaks existing architecture
- Cython bindings would need complex memory ownership logic
- Python's GC and weak reference support already solve this problem

**Rejected alternatives:**
- NetworkX/graphlib: Overkill for simple parent→child edges (native collections sufficient)
- Context managers for scoping: Awkward API for automatic feature (valid for mode switching only)
- C-level dependency tracking: Duplicates Python's GC, error-prone, high complexity

### Expected Features

Research across production quantum frameworks (Q#, Qrisp, Silq) and academic work (Unqomp, Qurts, SQUARE) shows two universal patterns: **scope-triggered cleanup** and **dual-mode strategy** (lazy vs eager uncomputation).

**Must have (table stakes):**
- **Scope-triggered cleanup**: Uncompute at scope exit (industry standard across Q#, Qrisp, Silq)
- **Dependency tracking**: Track intermediate allocations to know what can be safely uncomputed
- **Reverse-order uncomputation**: LIFO cleanup (mathematical requirement for U†VU pattern)
- **Nested expression support**: Handle `~a & b | ~c` tree of intermediates
- **Both qbool and qint comparisons**: Comparison results return qbool that need uncomputation
- **Safety verification**: Prevent uncomputation of values still in use (type system or runtime checks)

**Should have (competitive):**
- **Dual-mode strategy**: Lazy (default, minimize gates) vs eager (qubit-saving, minimize peak qubits)
- **Visual uncomputation markers**: Circuit output shows what gets cleaned up (OpenQASM comment annotations)
- **Statistics tracking**: Report qubits saved via uncomputation (extends existing circuit stats)
- **Zero-configuration default**: Works automatically without setup (most users shouldn't need options)

**Defer (v2+):**
- **Automatic strategy selection**: Smart defaults based on expression depth analysis
- **Recompute-on-demand**: Uncompute early, recompute if needed later (Qrisp's advanced feature)
- **Circuit optimizer integration**: Uncomputation + optimization synergy (U†U pattern simplification)

**Anti-features (explicitly avoid):**
- **Automatic cloning**: Violates no-cloning theorem
- **Measurement-based uncomputation**: Changes semantics (collapses superposition)
- **Global cleanup at circuit end**: Defeats purpose (memory already consumed)
- **Implicit uncomputation without tracking**: Can uncompute values still needed

### Architecture Approach

The architecture extends the existing three-layer system with minimal changes: Python adds DependencyManager and extends qbool lifecycle, C adds reverse gate generation, Cython exposes new functions.

**Major components:**

1. **DependencyManager (Python)** — Centralized dependency graph tracking parent→child relationships, provides topological sort for cascade uncomputation, stored in Python dict/weakref structures

2. **qbool.dependency_list (Python)** — Each qbool stores list of intermediates it depends on, populated at creation time during operator overloading, triggers cascade cleanup in `__del__`

3. **reverse_gate_generator.c (C)** — Generate adjoint sequences for uncomputation (reverse gate order, apply gate-specific adjoints like P(θ)→P(-θ)), reuses existing gate types

4. **uncomputation.c (C)** — Apply reversed sequences to circuit, integrates with existing add_gate() infrastructure, no new gate types needed

5. **weakref.finalize callbacks (Python)** — Register finalization callback at qbool creation, receives qubit indices and operation type, calls C backend to append inverse gates

**Integration points:**
- Extend qint/qbool operators (`__invert__`, `__and__`, comparisons) to register dependencies (~5 lines per operator)
- Modify `__del__` to call `uncompute()` before freeing qubits
- Extend `with` statement `__exit__` to uncompute context-local temporaries
- Qubit allocator (existing) continues handling qubit freeing (uncomputation circuit generation happens first)

**Data flow pattern:**
1. User writes `result = ~a & b`
2. Python creates intermediate for `~a`, records empty dependency list
3. Python creates result for `intermediate & b`, records `[intermediate, b]` as dependencies
4. Scope exit triggers `result.__del__()`
5. Cascade uncomputation: walk dependencies in reverse, generate and apply adjoint sequences
6. Free qubits to allocator

### Critical Pitfalls

Research identified five critical pitfalls that cause rewrites, incorrect quantum states, or exponential resource usage.

1. **Incorrect uncomputation position in circuit flow** — Uncomputing before value's last use or after qubits modified produces silent state corruption. Prevention: Layer-aware dependency graph, validate qubit availability before uncomputation, test with statevector simulation to verify ancilla return to |0⟩.

2. **Circular dependencies and memory leaks** — Bidirectional parent↔child references prevent garbage collection, memory grows unbounded. Prevention: Single ownership model (dependency graph in circuit_t), weak references for parent pointers, explicit cleanup protocol in topological order.

3. **Exponential cost blowup with nested uncomputation** — Naive uncomputation in nested contexts causes 2^ℓ gate multiplication for ℓ nesting levels. Prevention: Immediate uncomputation mode (qubit-saving), memoization to avoid duplicate uncomputation, flatten dependency graph to identify shared intermediates.

4. **Incorrect reversal of multi-controlled and conditional gates** — Multi-controlled gates, phase gates P(θ), and conditional contexts require gate-type-specific inversion logic. Prevention: Switch on gate type for custom inverse logic, test adjoint correctness (U†U = I), preserve gate metadata for inversion.

5. **Integration with `with` statement conditional scoping** — Global `_controlled` flag state creates scope mismatch when intermediates created inside `with` block are uncomputed outside. Prevention: Tag dependency nodes with conditional scope, uncomputation inherits control from creation context, trigger cleanup at `with` block exit.

## Implications for Roadmap

Based on research, suggested phase structure follows dependency order: core infrastructure (dependency tracking, gate reversal) → basic uncomputation → integration with existing features → advanced modes → testing/docs.

### Phase 1: Dependency Tracking Infrastructure
**Rationale:** Foundation for all uncomputation features. Research shows dependency graph must exist before any uncomputation logic to avoid incorrect positioning (Pitfall 1). Python-level tracking is the correct layer based on architecture analysis.

**Delivers:**
- DependencyManager class with parent→child tracking
- qbool.dependency_list attribute
- Operator overloading modifications to record dependencies
- Topological sort for cascade cleanup

**Addresses:**
- Dependency tracking (table stakes feature)
- Nested expression support (table stakes feature)

**Avoids:**
- Pitfall 2 (circular dependencies) via single-ownership model
- Pitfall 1 (incorrect positioning) by building graph before inserting gates

**Research needs:** Standard graph algorithms (topological sort), no deeper research needed.

### Phase 2: C Reverse Gate Generation
**Rationale:** Must exist before Python can trigger uncomputation. Pure C implementation, no Python dependencies, enables testing gate reversal correctness independently.

**Delivers:**
- reverse_gate_generator.c with reverse_sequence() and reverse_gate()
- Gate-type-specific adjoint logic (X→X, P(θ)→P(-θ), etc.)
- uncomputation.c with apply_uncomputation()
- Cython bindings for new C functions

**Addresses:**
- Reverse-order uncomputation (table stakes feature)

**Avoids:**
- Pitfall 4 (incorrect gate reversal) via gate-type-specific logic
- Pitfall 3 (exponential cost) by making reversal O(gates) not O(gates²)

**Research needs:** Standard quantum computing (adjoint circuits), no deeper research needed.

### Phase 3: Basic Uncomputation Integration
**Rationale:** Connects Phase 1 and 2 components. Extends qbool lifecycle to trigger uncomputation, validates end-to-end flow.

**Delivers:**
- qbool.uncompute() method with cascade logic
- Modified `__del__` to call uncompute() before freeing
- weakref.finalize integration
- Test suite for basic expressions (a & b, ~a, a > b)

**Addresses:**
- Scope-triggered cleanup (table stakes feature)
- Both qbool and qint comparisons (table stakes feature)
- Safety verification (table stakes, basic level)

**Avoids:**
- Pitfall 9 (type system mismatch) by handling qbool-from-comparison
- Pitfall 8 (qubit reuse) by coordinating with allocator

**Research needs:** Python lifecycle management patterns (already researched), no additional research.

### Phase 4: Context Manager Integration
**Rationale:** Critical for conditional correctness. The `with` statement creates quantum conditionals, so uncomputation must respect conditional scopes.

**Delivers:**
- Extended `__enter__` to track context temporaries
- Extended `__exit__` to uncompute context-local intermediates
- Scope-aware dependency tagging
- Test suite for nested `with` blocks

**Addresses:**
- Integration with existing conditional features

**Avoids:**
- Pitfall 5 (conditional scope leakage) via scope-aware tracking

**Research needs:** **YES** — complex interaction between global `_controlled` state and dependency tracking. May need `/gsd:research-phase` to investigate codebase patterns in quantum_language.pyx lines 26-29.

### Phase 5: Qubit-Saving Mode (Eager Uncomputation)
**Rationale:** Addresses different use cases (qubit-constrained hardware vs gate-count-constrained). Research shows both modes are industry standard.

**Delivers:**
- ql.option("uncomputation", "eager") configuration
- Immediate intermediate cleanup after use
- Reference counting to detect last use
- Documentation on lazy vs eager trade-offs

**Addresses:**
- Dual-mode strategy (competitive feature)
- Zero-configuration default (competitive feature, lazy is default)

**Avoids:**
- Pitfall 3 (exponential cost) by providing escape valve for nested expressions

**Research needs:** Standard pattern, no additional research needed.

### Phase 6: Visualization and Documentation
**Rationale:** Uncomputation is invisible to users without tooling. Research shows debugging difficulty is major usability issue.

**Delivers:**
- Visual uncomputation markers in circuit output (OpenQASM comments)
- Statistics tracking (qubits saved metric in get_statistics())
- Debug mode (ql.option("debug_uncomputation"))
- Comprehensive examples and API docs

**Addresses:**
- Visual markers (competitive feature)
- Statistics tracking (competitive feature)

**Avoids:**
- Pitfall 11 (debugging difficulty) via visualization
- Pitfall 12 (documentation mismatch) via examples-first docs

**Research needs:** Documentation best practices, no technical research needed.

### Phase Ordering Rationale

- **Phase 1 before 2:** Dependency graph must exist to know WHAT to uncompute before implementing HOW to uncompute
- **Phase 2 before 3:** C reverse gate generation must work independently before integrating with Python lifecycle
- **Phase 3 before 4:** Basic uncomputation must work for simple cases before tackling conditional complexity
- **Phase 4 before 5:** Scope correctness more critical than mode optimization (wrong scope = wrong result, wrong mode = inefficiency)
- **Phase 6 last:** Tooling enhances existing features, no dependencies

This ordering avoids the common mistake of implementing uncomputation without dependency analysis (causes Pitfall 1), and prevents the trap of optimizing before correctness is established.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 4 (Context Manager Integration):** Complex interaction between global `_controlled` state, `_list_of_controls`, and scope-based dependency tracking. Existing quantum_language.pyx uses global state that may conflict with scope-aware uncomputation. Recommend `/gsd:research-phase` to investigate:
  - How `with` statement modifies global state
  - When `_controlled` is set/reset
  - How nested `with` blocks interact
  - Where to inject uncomputation trigger in `__exit__`

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** Dependency graph and topological sort are standard computer science algorithms
- **Phase 2:** Quantum gate adjoints are well-documented (U†U = I) in quantum computing fundamentals
- **Phase 3:** Python object lifecycle management is standard Python pattern
- **Phase 5:** Eager vs lazy evaluation is standard programming language concept
- **Phase 6:** Documentation and visualization are standard development practices

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python weakref.finalize verified in official Python 3.14.2 docs (Jan 2026), C adjoint generation is standard quantum technique |
| Features | HIGH | Surveyed production frameworks (Q#, Qrisp, Silq) and academic research (Unqomp, Qurts, SQUARE 2024-2025), consistent patterns |
| Architecture | HIGH | Direct analysis of existing codebase (quantum_language.pyx, qubit_allocator.h, circuit.h), integration points identified |
| Pitfalls | HIGH | Recent academic papers (Qurts 2025, Modular Synthesis 2024, Reqomp 2024) document same pitfalls, validated by multiple sources |

**Overall confidence:** HIGH

Research is comprehensive and well-sourced. Python lifecycle management is proven technology (PEP 442). Quantum gate reversal is fundamental quantum computing. Dependency tracking is standard compiler technique. Architecture matches existing codebase patterns.

### Gaps to Address

Research identified four areas requiring validation during implementation:

- **Inverse operation availability:** Does every C operation support `invert` flag? Research assumes yes based on quantum theory, but C backend may not implement all adjoints. Resolution: Code audit during Phase 2 (reverse_gate_generator.c implementation).

- **Partial uncomputation policy:** What if only some intermediates can be safely uncomputed? Research suggests all-or-nothing for expressions, but user expectations unclear. Resolution: User study or design decision in Phase 3 (document behavior in API reference).

- **Sequence caching vs regeneration:** Should reversed sequences be cached (faster, more memory) or regenerated each time (slower, less memory)? Research doesn't provide clear guidance. Resolution: Performance testing during Phase 3, make configurable if significant impact.

- **Weak vs strong references in dependency list:** Should `dependency_list` use `weakref.ref` (allows earlier cleanup, more complex) or strong references (simpler, prevents premature GC)? Research suggests strong references for MVP, weak for optimization. Resolution: Start with strong references in Phase 1, add weak reference option in Phase 5 if memory profiling shows issues.

## Sources

### Primary (HIGH confidence)

**Quantum uncomputation research (2024-2026):**
- [Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime](https://arxiv.org/abs/2411.10835) - arXiv 2024, lifetime management patterns
- [Modular Synthesis of Efficient Quantum Uncomputation](https://dl.acm.org/doi/pdf/10.1145/3689785) - ACM 2024, exponential cost blowup documentation
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits](https://files.sri.inf.ethz.ch/website/papers/pldi21-unqomp.pdf) - PLDI 2021, dependency graph approach
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) - arXiv 2025, qubit reuse patterns
- [Rise of conditionally clean ancillae](https://quantum-journal.org/papers/q-2025-05-21-1752/pdf/) - Quantum Journal 2025, conditional uncomputation

**Python patterns:**
- [weakref — Weak references](https://docs.python.org/3/library/weakref.html) - Official Python 3.14.2 docs (Jan 26, 2026)
- [PEP 442 – Safe object finalization](https://peps.python.org/pep-0442/) - Python Enhancement Proposal
- [Python Weak References in 2025](https://medium.com/pythoneers/python-weak-references-in-2025-a-simpler-way-to-work-with-the-garbage-collector-26517aebde2e) - Medium 2025

**Framework documentation:**
- [Q# Conjugations](https://learn.microsoft.com/en-us/azure/quantum/user-guide/language/expressions/conjugations) - Microsoft official docs
- [Qrisp Uncomputation](https://qrisp.eu/reference/Core/Uncomputation.html) - Qrisp official docs
- [Silq Overview](https://silq.ethz.ch/overview) - ETH Zurich

### Secondary (MEDIUM confidence)

**Quantum circuit implementation:**
- [SQUARE: Strategic Quantum Ancilla Reuse](https://arxiv.org/abs/2004.08539) - arXiv 2020, eager vs lazy strategies
- [Reqomp: Space-constrained Uncomputation](https://quantum-journal.org/papers/q-2024-02-19-1258/) - Quantum 2024, partial uncomputation
- [CaQR: Compiler-Assisted Approach for Qubit Reuse](https://people.cs.rutgers.edu/zz124/assets/pdf/asplos23.pdf) - ASPLOS 2023

**Performance and optimization:**
- [Qubit-Reuse Compilation with Mid-Circuit Measurement and Reset](https://link.aps.org/doi/10.1103/PhysRevX.13.041057) - Physical Review X 2023, qubit saving modes
- [Integrated Qubit Reuse and Circuit Cutting](https://arxiv.org/html/2312.10298v1) - arXiv 2023

### Codebase-Specific (HIGH confidence)

**Existing architecture:**
- quantum_language.pyx — Python/Cython layer, global state management (_controlled, _list_of_controls lines 26-29)
- qubit_allocator.h — Centralized qubit allocation/deallocation, ownership tracking, successful single-ownership pattern
- circuit.h — Layer-based gate scheduling, circuit_t structure
- comparison_ops.h — qint → qbool conversion patterns (CQ_equal_width, etc.)
- bitwise_ops.c — Q_not, Q_and, Q_xor, Q_or return sequence_t*

---
*Research completed: 2026-01-28*
*Ready for roadmap: yes*
