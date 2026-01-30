# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.5 Bug Fixes & Exhaustive Verification -- Phase 28: Verification Framework & Init

## Current Position

Phase: 29 of 33 (C Backend Bug Fixes)
Plan: 01 of 04 (BUG-01 & BUG-02 Investigation)
Status: In progress
Last activity: 2026-01-30 -- Completed 29-01 investigation (bugs deferred to C backend work)

Progress: [██░░░░░░░░] 16%

## Performance Metrics

**Velocity:**
- Total plans completed: 88 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 2)
- Average duration: ~8 min/plan
- Total execution time: ~11.8 hours

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

### Pending Todos

None.

### Blockers/Concerns

**Known C backend bugs (v1.5 targets):**
- **BUG-04 (CRITICAL):** QFT addition fails with both nonzero operands - blocks BUG-01 and BUG-02 fixes
- BUG-01: Subtraction underflow (3-7 returns 7 instead of 12) - blocked by BUG-04, test files created
- BUG-02: Less-or-equal comparison (5<=5 returns 0) - blocked by BUG-04, test files created
- BUG-03: Multiplication segfaults at certain widths
- BUG-05: circuit() does not properly reset state - gates accumulate across calls (discovered in 28-02)

**Known pre-existing issues (not v1.5 scope):**
- Nested quantum conditionals require quantum-quantum AND
- Build system: pip install -e . fails with absolute path error
- Some tests/python/ tests cause segfaults during execution (discovered in 28-02, pre-existing)

## Session Continuity

Last session: 2026-01-30
Stopped at: Completed Phase 29-01 investigation (BUG-01 and BUG-02 deferred to C backend work)
Resume file: None
Resume action: Continue with Phase 29-02 (BUG-03 & BUG-04) - BUG-04 is high priority

---
*State updated: 2026-01-30 after completing Phase 29-01*
