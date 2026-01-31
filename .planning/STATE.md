# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.5 Bug Fixes & Exhaustive Verification -- Phase 28: Verification Framework & Init

## Current Position

Phase: 29 of 33 (C Backend Bug Fixes)
Plan: 6 of 8 (gap closure in progress)
Status: Gap closure execution — QQ_add control reversal applied
Last activity: 2026-01-31 -- Completed 29-06-PLAN.md (QQ_add fix partial success)

Progress: [███░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 94 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 8)
- Average duration: ~10 min/plan
- Total execution time: ~15.7 hours

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
| 29-05 | Accept partial fix for BUG-03 multiplication | Investigation identified root cause but fix incomplete - document for future work |
| 29-05 | Disable GCC LTO due to compiler bug | GCC 15 -flto triggers internal error, disabled until toolchain fixed |
| 29-04 | BUG-04 fix scope limited to CQ_add only | QQ_add (qint+qint) uses different implementation, needs separate fix |
| 29-04 | BUG-01 and BUG-02 remain blocked by incomplete BUG-04 | Cannot test/fix until QQ_add bit-ordering corrected |
| 29-06 | Fixed QQ_add control qubit mapping: 2*bits-1-bit instead of bits+bit | Control bits were swapped - outer loop MSB-first but needs LSB-first qubit access |
| 29-06 | CQ_add analytically correct, test failures are BUG-05 interference | Plan 29-03 fix is mathematically sound, BUG-05 cache pollution causes wrong results |
| 29-06 | Accept partial verification due to BUG-05 blocking test suite | Simple tests pass (0+0, 1+0, 1+1), complex tests hit memory explosion from BUG-05 |

### Pending Todos

None.

### Blockers/Concerns

**Known C backend bugs (v1.5 targets):**
- **BUG-05 (CRITICAL BLOCKER):** circuit() does not properly reset state - causes memory explosion, blocks ALL verification of arithmetic fixes
- **BUG-04 (PARTIALLY FIXED):** CQ_add fixed (29-03), QQ_add control reversal applied (29-06) - partial success but BUG-05 prevents full verification
- **BUG-03 (INVESTIGATED):** Multiplication returns 0 - root cause identified but algorithm needs deeper redesign
- **BUG-01 (PARTIALLY UNBLOCKED):** Subtraction - QQ_add now has control fix (29-06), pending BUG-05 resolution for verification
- **BUG-02 (BLOCKED):** Less-or-equal comparison - transitively blocked by BUG-01 verification pending BUG-05 fix

**Known pre-existing issues (not v1.5 scope):**
- Nested quantum conditionals require quantum-quantum AND
- Build system: pip install -e . fails with absolute path error
- Some tests/python/ tests cause segfaults during execution (discovered in 28-02, pre-existing)

## Session Continuity

Last session: 2026-01-31
Stopped at: Completed 29-06-PLAN.md — QQ_add control reversal applied, partial test success
Resume file: None
Resume action: BUG-05 resolution is CRITICAL BLOCKER for all arithmetic verification - must fix circuit state reset before proceeding

---
*State updated: 2026-01-30 after Phase 29 execution + verification*
