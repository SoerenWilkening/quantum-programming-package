# Roadmap: Quantum Assembly v1.4

## Overview

This milestone adds production-quality OpenQASM 3.0 string export from the C backend and a standalone Qiskit-based verification script. The roadmap progresses bottom-up: fix and extend the C export function, add Cython/Python bindings, then build the verification script that exercises the full pipeline.

## Milestones

- v1.0 MVP - Phases 1-10 (shipped 2026-01-27)
- v1.1 QPU State - Phases 11-15 (shipped 2026-01-28)
- v1.2 Uncomputation - Phases 16-20 (shipped 2026-01-28)
- v1.3 Package Structure & ql.array - Phases 21-24 (shipped 2026-01-29)
- **v1.4 OpenQASM Export & Verification** - Phases 25-27 (shipped 2026-01-30)

## Phases

- [x] **Phase 25: C Backend OpenQASM Export** - Fix all gate exports, add string-return function, handle large_control and measurements
- [x] **Phase 26: Python API Bindings** - Cython wrapper with memory safety, module-level ql.to_openqasm(), optional deps
- [x] **Phase 27: Verification Script** - Standalone Qiskit-based verification with built-in test cases and pass/fail reporting

## Phase Details

### Phase 25: C Backend OpenQASM Export
**Goal**: Production-quality OpenQASM 3.0 string export from C backend with all gate types, multi-controlled gates, measurements, and error handling
**Depends on**: v1.3 completion (Phase 24)
**Requirements**: EXP-01, EXP-02, EXP-03, EXP-04, EXP-05, EXP-06, EXP-07, EXP-08
**Plans:** 2 plans
Plans:
- [x] 25-01-PLAN.md — Implement circuit_to_qasm_string() with all gate types, controls, measurements, error handling
- [x] 25-02-PLAN.md — Fix circuit_to_opanqasm() and add circuit_to_openqasm() file-based wrapper
**Success Criteria** (what must be TRUE):
  1. `circuit_to_qasm_string()` returns valid OpenQASM 3.0 for circuits with X, Y, Z, H, P, Rx, Ry, Rz gates
  2. Multi-controlled gates with >2 controls use `ctrl(n) @ gate` syntax reading from `large_control` array
  3. Measurement gates export as `c[i] = measure q[i];` with proper `bit[n] c;` declaration
  4. NULL circuit input returns NULL; malloc failure returns NULL
  5. Existing `circuit_to_opanqasm()` file-based export also fixed (fclose, all gates, large_control)

### Phase 26: Python API Bindings
**Goal**: Users can call `ql.to_openqasm()` to get an OpenQASM 3.0 string from their circuit
**Depends on**: Phase 25
**Requirements**: API-01, API-02, API-03
**Plans:** 2 plans
Plans:
- [x] 26-01-PLAN.md — Create openqasm.pxd/pyx Cython wrapper, update __init__.py and setup.py
- [x] 26-02-PLAN.md — Build package, create tests, verify full pipeline
**Success Criteria** (what must be TRUE):
  1. Cython `to_openqasm()` method returns Python string and frees C buffer in finally block
  2. `ql.to_openqasm()` module-level function returns QASM string for current circuit
  3. Optional verification dependencies available via `pip install quantum-assembly[verification]`

### Phase 27: Verification Script
**Goal**: Standalone script that exports circuits to OpenQASM, simulates via Qiskit, and verifies outcomes match expected values
**Depends on**: Phase 26
**Requirements**: VER-01, VER-02, VER-03, VER-04, VER-05, VER-06, VER-07
**Plans:** 1 plan
Plans:
- [x] 27-01-PLAN.md — Create verification script with framework, CLI, test cases, and end-to-end validation
**Success Criteria** (what must be TRUE):
  1. Running `python scripts/verify_circuit.py` executes all built-in test cases
  2. Arithmetic tests verify addition, subtraction, multiplication including overflow
  3. Comparison tests verify all six operators (<, <=, ==, >=, >, !=)
  4. Bitwise tests verify AND, OR, XOR, NOT
  5. Each test uses deterministic verification (classical init → 1 shot → exact match)
  6. Script prints pass/fail per test with summary, exits non-zero on any failure
  7. Failing tests show expected vs actual values

## Progress

**Execution Order:** 25 -> 26 -> 27

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 25. C Backend OpenQASM Export | v1.4 | 2/2 | Complete | 2026-01-30 |
| 26. Python API Bindings | v1.4 | 2/2 | Complete | 2026-01-30 |
| 27. Verification Script | v1.4 | 1/1 | Complete | 2026-01-30 |

---
*Roadmap created: 2026-01-30*
*Last updated: 2026-01-30 (Phase 27 complete — v1.4 milestone shipped)*
