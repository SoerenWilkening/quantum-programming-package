# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.5 Bug Fixes & Exhaustive Verification -- Phase 28: Verification Framework & Init

## Current Position

Phase: 29 of 33 (C Backend Bug Fixes)
Plan: 03 of 04 (BUG-04 Complete Fix)
Status: In progress
Last activity: 2026-01-30 -- Completed 29-03 (BUG-04 bit-ordering fix complete)

Progress: [██░░░░░░░░] 18%

## Performance Metrics

**Velocity:**
- Total plans completed: 89 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 3)
- Average duration: ~9 min/plan
- Total execution time: ~13.3 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | 16 | Complete (2026-01-29) |
| v1.4 OpenQASM Export | 25-27 | 6 | Complete (2026-01-30) |
| v1.5 Bug Fixes & Verification | 28-33 | TBD | In progress |

## Accumulated Context

### Decisions

Milestone decisions archived. See PROJECT.md Key Decisions table for full history.

**Recent (Phase 28-29):**

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 28-01 | Separate tests/conftest.py for verification tests vs tests/python/conftest.py for unit tests | Keep fixture namespaces distinct, avoid conflicts between test categories |
| 28-01 | verify_circuit returns (actual, expected) tuple instead of asserting directly | Gives tests flexibility in assertion style and failure message formatting |
| 28-01 | Exhaustive testing threshold at 4 bits, sampled testing for 5+ bits | Balance coverage (all 256 pairs at 4-bit) vs runtime (sampled edge cases + random at higher widths) |
| 28-01 | Deterministic sampling with random.seed(42) | Reproducible test cases across runs for debugging |
| 28-02 | Generate parametrize data at module level via helper functions | Clean test structure, avoids pytest collection overhead from dynamic generation |
| 28-02 | Use default argument binding in circuit_builder closures | Avoids Python closure variable capture issues in loops |
| 28-02 | Document C backend circuit() reset bug rather than attempting fix | C backend memory management fix is risky and time-consuming, beyond v1.5 scope |
| 29-01 | Defer BUG-01 and BUG-02 fixes, create test files only | Investigation revealed root cause is C backend QFT arithmetic (BUG-04), not Python operator logic |
| 29-01 | tests/bugfix/ directory for bug reproduction tests | Separate targeted bug tests from exhaustive verification tests |
| 29-02 | Use MAXLAYERINSEQUENCE for multiplication num_layer allocation | Conservative but safe - formula-based calculation was insufficient |
| 29-02 | Increase per-layer gate allocation to 10*bits | Progressive testing showed 2*bits, 3*bits, 4*bits all still segfaulted |
| 29-02 | Accept partial fixes for both BUG-03 and BUG-04 | Segfault fixed (primary goal), logic bugs documented for future work |
| 29-03 | Fix bit-ordering with bin[bits-1-bit_idx] reversal | two_complement() returns MSB-first, QFT formula needs LSB-first iteration |
| 29-03 | Fix cache update to use rotations[i] not rotations[bits-i-1] | Must match initial build path indexing for gate value consistency |
| 29-03 | Verify formula against Qiskit reference | Analytical verification when BUG-05 prevents reliable test execution |

### Pending Todos

None.

### Blockers/Concerns

**Known C backend bugs (v1.5 targets):**
- **BUG-05 (CRITICAL):** circuit() does not properly reset state - causes memory explosion, blocks exhaustive testing AND prevents verification of BUG-04 fix
- **BUG-03 (PARTIALLY FIXED):** Multiplication segfault fixed, but returns wrong results (logic bug remains)
- **BUG-04 (FIXED):** QFT addition bit-ordering corrected (29-03), verified against Qiskit reference - test verification blocked by BUG-05
- BUG-01: Subtraction underflow (3-7 returns 7 instead of 12) - root cause (BUG-04) fixed, needs testing after BUG-05 resolved
- BUG-02: Less-or-equal comparison (5<=5 returns 0) - root cause (BUG-04) fixed, needs testing after BUG-05 resolved

**Known pre-existing issues (not v1.5 scope):**
- Nested quantum conditionals require quantum-quantum AND
- Build system: pip install -e . fails with absolute path error
- Some tests/python/ tests cause segfaults during execution (discovered in 28-02, pre-existing)

## Session Continuity

Last session: 2026-01-30
Stopped at: Completed Phase 29-03 (BUG-04 bit-ordering fix complete)
Resume file: None
Resume action: Address BUG-05 (circuit reset) to enable verification, then continue with Phase 29 remaining plans

---
*State updated: 2026-01-30 after completing Phase 29-03*
