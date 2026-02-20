# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v4.0 Grover's Algorithm -- Phase 78 (Diffusion Operator)

## Current Position

Phase: 78 of 81 (Diffusion Operator) -- COMPLETE
Plan: 2 of 2 complete
Status: Phase Complete
Last activity: 2026-02-20 -- Completed 78-02-PLAN.md (diffusion operator tests)

Progress: [################░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 3/6 phases (v4.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 225 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 22, v2.3: 4, v3.0: 35, v4.0: 9)
- Average duration: ~13 min/plan
- Total execution time: ~34.0 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | 16 | Complete (2026-01-29) |
| v1.4 OpenQASM Export | 25-27 | 6 | Complete (2026-01-30) |
| v1.5 Bug Fixes & Verification | 28-33 | 33 | Complete (2026-02-01) |
| v1.6 Array & Comparison Fixes | 34-36 | 5 | Complete (2026-02-02) |
| v1.7 Bug Fixes & Array Optimization | 37, 40 | 2 | Complete (2026-02-02) |
| v1.8 Copy, Mutability & Uncomp Fix | 41-44 | 7 | Complete (2026-02-03) |
| v1.9 Pixel-Art Circuit Visualization | 45-47 | 7 | Complete (2026-02-03) |
| v2.0 Function Compilation | 48-51 | 8 | Complete (2026-02-04) |
| v2.1 Compile Enhancements | 52-54 | 6 | Complete (2026-02-05) |
| v2.2 Performance Optimization | 55-61 | 22 | Complete (2026-02-08) |
| v2.3 Hardcoding Right-Sizing | 62-64 | 4 | Complete (2026-02-08) |
| v3.0 Fault-Tolerant Arithmetic | 65-75 | 35 | Complete (2026-02-18) |
| v4.0 Grover's Algorithm | 76-81 | TBD | In Progress |
| Phase 76 P05 | 1min | 2 tasks | 2 files |
| Phase 76 P06 | 2min | 2 tasks | 0 files |
| Phase 77 P01 | 34min | 2 tasks | 3 files |
| Phase 77 P02 | 14min | 2 tasks | 1 files |
| Phase 78 P01 | 17min | 2 tasks | 6 files |
| Phase 78 P02 | 18min | 1 tasks | 1 files |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.
v4.0: `branch(theta)` = Ry rotation (not Hadamard), IQAE preferred for amplitude estimation (no QFT), X-MCZ-X diffusion pattern (zero ancilla).
76-05: Bounds check added to __getitem__ for clear IndexError on invalid qubit indices. Qiskit little-endian convention: ctrl=q[0] is rightmost bit in bitstrings.
76-04: Task 1 gate.c fix pre-existing from plan 01 (4bae694). Layer accumulation uses 0/0 sentinel for first-call detection.
- [Phase 76]: Bounds check added to __getitem__ for clear IndexError on invalid qubit indices
- [Phase 76]: Qiskit little-endian convention: ctrl=q[0] is rightmost bit in bitstrings
- [Phase 76]: Rotation gate inverse: Ry(theta)^-1 = Ry(-theta), same for Rx, Rz, P
- [Phase 76]: Multi-call layer tracking: min/max accumulation instead of overwrite
- [Phase 76]: All 31 tests passing after rebuild -- 3 UAT gaps fully closed (indexed branch, controlled CRY, double accumulation)
- [Phase 77]: Oracle validation at circuit generation time (first call), not decoration time
- [Phase 77]: validate=False bypasses ALL checks (ancilla delta + compute-phase-uncompute)
- [Phase 77]: Phase gate detection: only Z-type gates targeting param qubits count as phase marking
- [Phase 77]: Direct (non-compiled) oracle tests for QASM-visible phase verification; compiled oracles tested via allocator stats
- [Phase 77]: bit_flip=True mismatch is expected for standard comparison oracles (ancilla independence)
- [Phase 78]: _PhaseProxy class for x.phase += theta syntax (plain Python class in qint.pyx, no-op setter for += desugaring)
- [Phase 78]: emit_p targets control qubit in controlled context (register-agnostic global phase)
- [Phase 78]: Width-based compile cache key for diffusion (variable-arity register support)
- [Phase 78]: Statevector sign verification for S_0 reflection (|0...0> opposite sign from others)
- [Phase 78]: Manual S_0 gates invisible in QASM due to auto-uncomputation -- verified via equivalence to X-MCZ-X
- [Phase 78]: CP duplicate-qubit QASM (cp q[n], q[n]) valid quantum semantics but Qiskit rejects

### Research Flags

- Phase 77: Interaction between oracle scoping and existing dependency tracking needs design review
- Phase 80: Compound predicate oracle synthesis may need /gsd:research-phase

### Blockers/Concerns

**Carry forward:**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication scope auto-uncomputation (workaround active)
- BUG-CQQ-QFT: QFT controlled QQ in-place addition incorrect at width 2+
- BUG-QFT-DIV: QFT division/modulo pervasively broken at all tested widths
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one
- 32-bit multiplication segfault (buffer overflow in C backend)

## Session Continuity

Last session: 2026-02-20
Stopped at: Completed 78-02-PLAN.md (diffusion operator tests)
Resume action: Begin Phase 79 (Grover iteration)

---
*State updated: 2026-02-20 -- Phase 78 complete (ql.diffusion + _PhaseProxy + tests, GROV-03/GROV-05 verified)*
