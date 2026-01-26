# Roadmap: Quantum Assembly

## Overview

This roadmap transforms Quantum Assembly from a mid-restructuring prototype into a production-ready quantum programming framework. The journey follows a bottom-up approach: first establishing a solid C foundation by eliminating architectural anti-patterns (global state, memory bugs), then building variable-width integer support and complete arithmetic operations, and finally polishing the Python API with comprehensive documentation. Each phase delivers verifiable capabilities that build toward the core value: writing quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Testing Foundation** - Establish characterization tests before any refactoring
- [x] **Phase 2: C Layer Cleanup** - Eliminate global state and fix critical memory bugs
- [ ] **Phase 3: Memory Architecture** - Centralize qubit allocation and establish ownership model
- [ ] **Phase 4: Module Separation** - Split QPU.c god object into focused modules
- [ ] **Phase 5: Variable-Width Integers** - Enable arbitrary bit-width quantum integers
- [ ] **Phase 6: Bit Operations** - Add bitwise operations for quantum integers
- [ ] **Phase 7: Extended Arithmetic** - Complete multiplication, add division and modular operations
- [ ] **Phase 8: Circuit Optimization** - Add gate merging, visualization, and statistics
- [ ] **Phase 9: Code Organization** - Reorganize operations into category-based modules
- [ ] **Phase 10: Documentation and API Polish** - Comprehensive docs and Python API stabilization

## Phase Details

### Phase 1: Testing Foundation
**Goal**: Capture current behavior with comprehensive characterization tests before any refactoring begins
**Depends on**: Nothing (first phase)
**Requirements**: TEST-01, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. Characterization test suite passes and captures current behavior of all existing operations
  2. Valgrind and ASan are integrated into development workflow with automated runs
  3. Pre-commit hooks enforce code quality (Ruff linting) on every commit
  4. Developer can run memory tests locally without manual setup
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md - Test infrastructure setup (pytest + pre-commit hooks)
- [x] 01-02-PLAN.md - Python characterization tests (qint/qbool operations)
- [x] 01-03-PLAN.md - Memory testing integration (Makefile with Valgrind/ASan)

### Phase 2: C Layer Cleanup
**Goal**: Eliminate global state and fix critical memory bugs in C backend
**Depends on**: Phase 1
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05
**Success Criteria** (what must be TRUE):
  1. All C functions accept explicit circuit_t* context parameter (no global circuit variable)
  2. Memory ownership is documented at every allocation point with clear comments
  3. All sizeof() usage is corrected (use sizeof(type) not sizeof(pointer))
  4. All structure fields are initialized before use (no uninitialized memory reads)
  5. NULL checks exist after all malloc/calloc operations with proper error handling
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md - Fix sizeof() bugs and uninitialized sequence structures
- [x] 02-02-PLAN.md - Add NULL checks after all malloc/calloc operations
- [x] 02-03-PLAN.md - Eliminate global state and document memory ownership

### Phase 3: Memory Architecture
**Goal**: Centralize qubit lifecycle management and establish clear ownership between circuit and quantum types
**Depends on**: Phase 2
**Requirements**: FOUND-06, FOUND-07, FOUND-08
**Success Criteria** (what must be TRUE):
  1. Qubit allocator module centralizes all qubit allocation and deallocation
  2. qint and qbool types borrow qubits from circuit with tracked ownership
  3. Ancilla qubit allocation is explicit and trackable without significant performance overhead
  4. Memory leaks from qubit allocation are eliminated (verified by Valgrind)
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md - Create qubit allocator module with core API and statistics
- [ ] 03-02-PLAN.md - Update C QINT/QBOOL to use allocator with ownership tracking
- [ ] 03-03-PLAN.md - Update Python bindings to use allocator and expose statistics

### Phase 4: Module Separation
**Goal**: Split QPU.c into focused modules with clear responsibilities
**Depends on**: Phase 3
**Requirements**: CODE-01, CODE-02, CODE-03, CODE-05
**Success Criteria** (what must be TRUE):
  1. Circuit builder module handles circuit creation, destruction, and gate addition
  2. Circuit optimizer module handles layer assignment and gate merging
  3. QPU.c responsibilities are separated into focused modules (no god object)
  4. Clear dependency graph exists between modules with minimal coupling
  5. Module interfaces are stable and well-documented
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Variable-Width Integers
**Goal**: Enable arbitrary bit-width quantum integers with dynamic allocation
**Depends on**: Phase 3
**Requirements**: VINT-01, VINT-02, VINT-03, VINT-04, ARTH-01, ARTH-02
**Success Criteria** (what must be TRUE):
  1. QInt constructor accepts width parameter for arbitrary bit sizes (8, 16, 32, 64, etc.)
  2. Quantum integers dynamically allocate qubits based on width parameter
  3. Arithmetic operations validate width compatibility and handle errors gracefully
  4. Mixed-width integer operations work correctly (e.g., 8-bit + 32-bit)
  5. Addition and subtraction operations work for all variable-width integers
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: Bit Operations
**Goal**: Add bitwise operations for quantum integers with Python operator overloading
**Depends on**: Phase 5
**Requirements**: BITOP-01, BITOP-02, BITOP-03, BITOP-04, BITOP-05
**Success Criteria** (what must be TRUE):
  1. Bitwise AND, OR, XOR, and NOT operations work on quantum integers
  2. Python operator overloading works for bitwise operations (&, |, ^, ~)
  3. Bit operations respect variable-width integers
  4. Generated circuits for bit operations have reasonable depth (verified by benchmarks)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Extended Arithmetic
**Goal**: Complete multiplication and add division, modulo, and modular arithmetic operations
**Depends on**: Phase 5
**Requirements**: ARTH-03, ARTH-04, ARTH-05, ARTH-06, ARTH-07
**Success Criteria** (what must be TRUE):
  1. Multiplication works for any integer size (not just fixed width)
  2. Comparison operations (>, <, ==, >=, <=) work for variable-width integers
  3. Division and modulo operations are implemented and work correctly
  4. Modular arithmetic operations (add/sub/mul mod N) are implemented
  5. All arithmetic operations generate optimized quantum circuits
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD
- [ ] 07-03: TBD

### Phase 8: Circuit Optimization
**Goal**: Add automatic circuit optimization, visualization, and statistics
**Depends on**: Phase 4
**Requirements**: CIRC-01, CIRC-02, CIRC-03, CIRC-04
**Success Criteria** (what must be TRUE):
  1. Text-based circuit visualization shows circuit structure for debugging
  2. Automatic gate merging optimization reduces circuit size
  3. Inverse gate cancellation eliminates redundant operations
  4. Circuit statistics (depth, gate count, qubit usage) are available programmatically
  5. Optimization passes can be enabled/disabled independently
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Code Organization
**Goal**: Reorganize arithmetic, comparison, and logic operations into category-based modules
**Depends on**: Phase 4
**Requirements**: CODE-04
**Success Criteria** (what must be TRUE):
  1. Arithmetic operations are organized in dedicated module (addition, subtraction, multiplication, etc.)
  2. Comparison operations are organized in dedicated module (>, <, ==, >=, <=)
  3. Logic operations are organized in dedicated module (AND, OR, XOR, NOT for qbool)
  4. Module structure follows consistent patterns across operation categories
**Plans**: TBD

Plans:
- [ ] 09-01: TBD

### Phase 10: Documentation and API Polish
**Goal**: Comprehensive documentation and stabilized Python API ready for release
**Depends on**: Phase 9
**Requirements**: TEST-02, TEST-03, DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. All public functions have comprehensive NumPy-style docstrings
  2. Sphinx documentation builds successfully with API reference and examples
  3. C backend has unit tests covering core functions
  4. Python API has unit tests covering all qint/qbool operations
  5. Tutorial examples demonstrate key features (arithmetic, conditionals, circuit generation)
  6. API reference is auto-generated from docstrings and navigable
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD
- [ ] 10-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Testing Foundation | 3/3 | Complete | 2026-01-26 |
| 2. C Layer Cleanup | 3/3 | Complete | 2026-01-26 |
| 3. Memory Architecture | 0/3 | Not started | - |
| 4. Module Separation | 0/0 | Not started | - |
| 5. Variable-Width Integers | 0/0 | Not started | - |
| 6. Bit Operations | 0/0 | Not started | - |
| 7. Extended Arithmetic | 0/0 | Not started | - |
| 8. Circuit Optimization | 0/0 | Not started | - |
| 9. Code Organization | 0/0 | Not started | - |
| 10. Documentation and API Polish | 0/0 | Not started | - |
