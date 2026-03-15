# Quantum Assembly — Project Specification

## 1. Overview

This document captures the specification for ongoing development of the Quantum Assembly framework.

The framework compiles high-level Python code (arithmetic, comparisons, `with` blocks) into quantum circuits. Users never interact with gates directly.

---

## 2. Task Areas

| Task | Area | Priority | Status |
|------|------|----------|--------|
| 1 | Code maintenance (speed, memory, stability, file sizes) | Normal | Not started |
| 2 | Codebase cleanup | Normal | Not started |
| 4 | Circuit compilation improvements | Normal | Phase 0 complete |

### Dependencies

- Tasks 1 and 2 are independent of each other and of Task 4.

---

## 3. Task 1: Code Maintenance

Improve the existing codebase in terms of:

- **Speed**: Optimize hot paths, reduce overhead in gate emission and circuit construction.
- **Memory**: Reduce memory footprint of circuit representation.
- **Stability**: Fix edge cases, improve error handling at system boundaries.
- **File sizes**: Reduce bloat (e.g., the 100+ generated sequence files in `c_backend/src/sequences/`).
- **Functionality**: Extend supported operations where gaps exist.

No detailed specification yet — to be refined based on profiling and usage patterns.

---

## 4. Task 2: Codebase Cleanup

General cleanup of the codebase:

- Remove dead code and unused modules.
- Consolidate duplicated logic.
- Improve module organization.
- Clean up the `.planning/` directory (large number of deleted planning files in git status).
- Standardize naming conventions across Python and C layers.

No detailed specification yet.

---

## 5. Task 4: Circuit Compilation Improvements

### 5.1 Problem

Currently, full quantum circuits are stored in memory. For large algorithms, this is prohibitive. Gates are meant to be applied to a QPU, not stored.

### 5.2 Direction

- Use **call graphs** to store instructions at a higher level of abstraction, rather than storing every individual gate.
- The `@ql.compile` decorator and `CallGraphDAG` are partial implementations of this idea.
- Optimization flags (`opt=0`, `opt=1`, `opt=2`) exist but are incomplete.

### 5.3 Completed (Phase 0)

- Execution-order edges (replace overlap edges with qubit-aware sequential edges)
- Flat operation DAG (remove wrapper/function nodes)
- Graph immutability after capture
- Gate counts stored on `sequence_t`, including hardcoded sequences
- Gate counts wired through `_record_operation` → `DAGNode`

### 5.4 Remaining

- Complete and working optimization flags (`opt=0`, `opt=1`, `opt=2`).
- Streaming gate application (gates applied to QPU without full circuit storage).
