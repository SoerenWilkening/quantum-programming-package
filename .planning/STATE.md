# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v4.0 Grover's Algorithm -- Phase 80 COMPLETE (3/3 plans), ready for Phase 81

## Current Position

Phase: 80 of 81 (Oracle Auto-Synthesis & Adaptive Search)
Plan: 3 of 3 complete
Status: Phase Complete
Last activity: 2026-02-22 - Completed 80-03-PLAN.md (BUG-CMP-MSB fix + inequality predicate tests)

Progress: [#########################░░░░░░░░░░░░░░░░░░░░░░░░░] 5/6 phases (v4.0)

## Performance Metrics

**Velocity:**
- Total plans completed: 231 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 22, v2.3: 4, v3.0: 35, v4.0: 15)
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
| Phase 78 P03 | 10min | 2 tasks | 3 files |
| Phase 79 P01 | 12min | 2 tasks | 2 files |
| Phase 79 P02 | 33min | 2 tasks | 3 files |
| Phase 80 P01 | 31min | 2 tasks | 2 files |
| Phase 80 P02 | 19min | 2 tasks | 2 files |
| Phase 80 P03 | 25min | 2 tasks | 2 files |

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
- [Phase 78-03]: emit_p_raw bypasses _get_controlled() to prevent double-control bug in _PhaseProxy.__iadd__
- [Phase 78-03]: Layer floor save/restore in __iadd__ keeps P gate outside comparison layer range during compute-P-uncompute
- [Phase 78-03]: Manual S_0 path now produces observable P gate in QASM and correct statevector reflection
- [Phase 79]: emit_h for H-sandwich in Grover iterations (not branch(0.5)) because H^2=I while Ry(pi/2)^2!=I
- [Phase 79]: branch(0.5) only for initial superposition on |0> (Ry(pi/2)|0> = H|0>)
- [Phase 79]: fault_tolerant=True set by default inside grover() for oracle comparison support
- [Phase 79]: width/widths keyword args for register width (qint annotations lack width info)
- [Phase 79-02]: Oracle phase marking requires `with flag: x.phase += math.pi` (not `pass` which is no-op after compile optimization)
- [Phase 79-02]: GroverOracle cache replay must allocate ancilla qubits for virtual indices beyond search register
- [Phase 79-02]: Auto-wrapped oracles in grover() use validate=False (P gate targets comparison ancilla, not search register)
- [Phase 80]: Tracing approach for predicate-to-oracle synthesis (not AST parsing) -- call predicate with real qint objects
- [Phase 80]: validate=False on synthesized predicate oracles (P gate targets comparison ancilla)
- [Phase 80]: m=None defaults to m=1 in Plan 01 (backwards-compatible placeholder for Plan 02 BBHT)
- [Phase 80]: Closure variable values in lambda cache key to distinguish closures with different captured values
- [Phase 80]: Decorated oracles without predicate fall back to m=1 when m=None (BBHT needs classical verification)
- [Phase 80]: BBHT growth factor LAMBDA=6/5, default max_attempts=ceil(2*log2(N))
- [Phase 80]: _run_grover_attempt refactors circuit building for reuse in adaptive and exact paths
- [Phase 80]: BUG-CMP-MSB discovered: inequality operators (<,>,<=,>=) access qubit 63 for MSB (pre-existing)
- [Phase 80-03]: BUG-CMP-MSB FIXED: temp_self[63] -> temp_self[comp_width - 1] in __lt__, temp_other[63] -> temp_other[comp_width - 1] in __gt__
- [Phase 80-03]: Adaptive path for compound inequality Grover tests (BBHT auto-selects iterations for complex predicates)

### Research Flags

- Phase 77: Interaction between oracle scoping and existing dependency tracking needs design review
- Phase 80: Compound predicate oracle synthesis RESOLVED -- tracing approach reuses existing qbool operators

### Blockers/Concerns

**Carry forward:**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication scope auto-uncomputation (workaround active)
- BUG-CQQ-QFT: QFT controlled QQ in-place addition incorrect at width 2+
- BUG-QFT-DIV: QFT division/modulo pervasively broken at all tested widths
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one
- 32-bit multiplication segfault (buffer overflow in C backend)
- ~~BUG-CMP-MSB~~: FIXED in 80-03 (b53bc44) -- inequality operators now use comp_width-1 MSB indexing

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 16 | Limit qiskit simulation to 4 threads in all simulation scripts | 2026-02-20 | 6961944 | [16-limit-qiskit-simulation-to-4-threads-in-](./quick/16-limit-qiskit-simulation-to-4-threads-in-/) |

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 80-03-PLAN.md (BUG-CMP-MSB fix + inequality predicate tests)
Resume action: Plan Phase 81 or next milestone task

---
*State updated: 2026-02-22 -- Phase 80 complete (3/3 plans: predicate synthesis, BBHT adaptive search, BUG-CMP-MSB fix + inequality tests)*
