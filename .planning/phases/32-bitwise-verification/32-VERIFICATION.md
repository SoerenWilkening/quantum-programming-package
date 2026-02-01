---
phase: 32-bitwise-verification
verified: 2026-02-01T11:45:00Z
status: gaps_found
score: 3/5 must-haves verified
gaps:
  - truth: "AND, OR, XOR return correct results for all exhaustive input pairs at widths 1-4 (CQ variant)"
    status: failed
    reason: "BUG-BIT-01: CQ bitwise operations produce incorrect result register layout when classical operand has fewer set bits than operand width"
    artifacts:
      - path: "tests/test_bitwise.py"
        issue: "754/2418 CQ tests xfailed due to C backend bug in CQ_and, CQ_or, CQ_xor functions"
    missing:
      - "Fix C backend LogicOperations.c: CQ_and(), CQ_or(), CQ_xor() to allocate full-width result register regardless of popcount(classical_value)"
      - "Result register must always be operand width, not popcount(b)"
  - truth: "Mixed-width AND, OR, XOR produce correct results for adjacent width pairs (1,2), (2,3), (3,4), (4,5), (5,6)"
    status: failed
    reason: "BUG-BIT-01: Mixed-width bitwise operations completely broken - both qubit allocation overflow (~32K qubits) and incorrect circuit logic"
    artifacts:
      - path: "tests/test_bitwise_mixed.py"
        issue: "1260/1608 mixed-width tests xfailed due to C backend width-extension bugs"
    missing:
      - "Fix C backend LogicOperations.c width-extension code to correctly zero-extend narrower operand to max(width_a, width_b)"
      - "Fix result register allocation to use max width, not cause qubit explosion"
      - "Fix circuit logic to produce correct results for operands of different widths"
---

# Phase 32: Bitwise Verification Report

**Phase Goal:** All bitwise operations (AND, OR, XOR, NOT) are verified including variable-width operand combinations.

**Verified:** 2026-02-01T11:45:00Z

**Status:** gaps_found

**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AND, OR, XOR return correct results for all exhaustive input pairs at widths 1-4 (QQ variant) | ✓ VERIFIED | 1020/1020 QQ exhaustive tests pass (widths 1-4, all ops) |
| 2 | AND, OR, XOR return correct results for all exhaustive input pairs at widths 1-4 (CQ variant) | ✗ FAILED | 754/1020 CQ tests xfailed due to BUG-BIT-01 (incorrect result register layout) |
| 3 | NOT returns correct bitwise complement for all values at widths 1-4 | ✓ VERIFIED | 30/30 NOT exhaustive tests pass (widths 1-4) |
| 4 | Sampled tests at widths 5-6 pass for all ops and variants (QQ, NOT) | ✓ VERIFIED | 198 QQ sampled + 42 NOT sampled = 240 tests pass (widths 5-6) |
| 5 | Mixed-width bitwise operations produce correct results for adjacent width pairs | ✗ FAILED | 1260/1260 mixed-width tests xfailed due to BUG-BIT-01 (qubit overflow + wrong logic) |

**Score:** 3/5 truths verified

**Interpretation:** Same-width QQ operations and NOT are fully verified. CQ operations and ALL mixed-width operations have systemic C backend bugs documented as BUG-BIT-01.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_bitwise.py` | All same-width bitwise correctness verification tests | ✓ VERIFIED | EXISTS (296 lines), SUBSTANTIVE (6 parametrized test functions, 2418 tests collected), WIRED (imported by pytest, uses verify_circuit fixture) |
| `tests/test_bitwise_mixed.py` | Mixed-width, NOT compositions, preservation tests | ✓ VERIFIED | EXISTS (335 lines), SUBSTANTIVE (4 test functions, 1608 tests collected), WIRED (imported by pytest, uses custom pipeline + verify_circuit) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| tests/test_bitwise.py | tests/conftest.py | verify_circuit fixture | WIRED | verify_circuit fixture used in all 6 test functions |
| tests/test_bitwise.py | tests/verify_helpers.py | generate_exhaustive_pairs, generate_sampled_pairs, format_failure_message | WIRED | Helper imports present, used in data generation and assertions |
| tests/test_bitwise.py | quantum_language | qint(), circuit(), bitwise operators | WIRED | ql.qint() used to create operands, &|^~ operators tested |
| tests/test_bitwise_mixed.py | tests/conftest.py | verify_circuit fixture | WIRED | verify_circuit used in test_not_composition |
| tests/test_bitwise_mixed.py | qiskit | loads(), AerSimulator | WIRED | Custom pipeline for preservation tests uses Qiskit directly |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| VBIT-01: Verify AND, OR, XOR, NOT operations | ⚠️ PARTIAL | QQ variants fully verified. CQ variants fail due to BUG-BIT-01 (result register layout bug in C backend). |
| VBIT-02: Verify bitwise operations with variable-width operands | ✗ BLOCKED | ALL mixed-width operations fail due to BUG-BIT-01 (width-extension code broken, causes qubit overflow or wrong results). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tests/test_bitwise.py | 83-87 | 754 xfail markers on CQ tests | ⚠️ Warning | Documents known BUG-BIT-01; tests exist but don't verify correctness |
| tests/test_bitwise_mixed.py | 67-71 | 1260 xfail markers on mixed-width tests | 🛑 Blocker | ALL mixed-width tests fail; prevents VBIT-02 verification |
| tests/test_bitwise_mixed.py | 16-25 | BUG-BIT-01 documented in module docstring | ℹ️ Info | Clear documentation of bug manifestations |

**Blocker Count:** 1 (mixed-width complete failure blocks VBIT-02)
**Warning Count:** 1 (CQ partial failure)

### Human Verification Required

No human verification needed — all issues are deterministically detectable through automated tests.

### Gaps Summary

**Gap 1: CQ bitwise operations fail due to result register layout bug**

The C backend's `CQ_and()`, `CQ_or()`, and `CQ_xor()` functions in LogicOperations.c allocate result qubits only for bits that are SET in the classical operand, rather than always allocating a full-width result register. This causes:
- When `popcount(classical_value) < width`, fewer result qubits allocated
- Standard extraction `bitstring[:width]` reads wrong bits
- 754/1020 CQ tests fail (74% failure rate)
- Only passes when `b == 2^width - 1` (all bits set) or coincidentally

**Impact on goal:** Success criterion 1 is PARTIALLY met for AND/OR/XOR — QQ variants verified, but CQ variants fail systematically. VBIT-01 requirement is partially satisfied.

**Gap 2: Mixed-width bitwise operations completely broken**

ALL mixed-width bitwise operations (1260/1260 tests) fail due to C backend width-extension code bugs:
- **Manifestation A:** Qubit allocation overflow (~32K qubits) for QQ AND, CQ AND, QQ OR with width pairs (1,2), (4,5), (5,6) — makes circuits unsimulatable
- **Manifestation B:** Incorrect circuit logic for all other combinations — OR and XOR wrong for all tested pairs; AND fails for ~44% of inputs at (2,3) and (3,4)

**Impact on goal:** Success criterion 2 is NOT met. VBIT-02 requirement is completely blocked.

**What works:**
- Same-width QQ operations (AND, OR, XOR): 1020/1020 pass ✓
- NOT operation (all widths): 72/72 pass ✓
- NOT compositions (NOT-AND, NOT-OR, NOT-XOR): 300/300 pass ✓
- Operand preservation: 44/48 pass (4 skip for degenerate circuits) ✓

**What's broken:**
- CQ operations: 754/1020 fail (74%) ✗
- ALL mixed-width operations: 1260/1260 fail (100%) ✗

---

**Conclusion:** Phase goal is NOT achieved. While tests exist and execute through the full pipeline, documenting behavior with xfail markers, the phase goal states operations must be "verified" — interpreted as producing correct results. Same-width QQ operations are verified. CQ operations and all mixed-width operations are documented but not verified correct.

The gap is in the C backend implementation (LogicOperations.c), not in the test infrastructure. The verification framework works correctly — it successfully detected the bugs.

---

_Verified: 2026-02-01T11:45:00Z_
_Verifier: Claude (gsd-verifier)_
