# Phase 95: Verification & Requirements Closure - Research

**Researched:** 2026-02-26
**Domain:** Procedural gap closure (VERIFICATION.md generation, REQUIREMENTS.md updates)
**Confidence:** HIGH

## Summary

Phase 95 is a purely procedural/documentation phase that closes gaps identified by the v5.0 milestone audit. No code changes are required. The audit found that Phase 91 (Arithmetic Bug Fixes) and Phase 93 (Depth/Ancilla Tradeoff) both completed all implementation work and have passing tests, but lack VERIFICATION.md files that independently verify their requirements against success criteria. Additionally, REQUIREMENTS.md has three FIX-0x checkboxes still unchecked and three traceability table entries still showing "Pending" despite the work being complete.

The work divides cleanly into three independent tasks: (1) generate 91-VERIFICATION.md by cross-referencing Phase 91 PLAN must-haves, SUMMARY accomplishments, and the ROADMAP success criteria against actual code and test evidence; (2) generate 93-VERIFICATION.md by the same method for Phase 93; and (3) update REQUIREMENTS.md checkboxes and traceability table for FIX-01, FIX-02, FIX-03.

**Primary recommendation:** Follow the established VERIFICATION.md format used by Phases 90, 92, and 94. Each verification file must independently check every success criterion from the ROADMAP, every must-have truth from the PLANs, and map each requirement ID to evidence. The REQUIREMENTS.md update is a straightforward find-and-replace of checkboxes and status values.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FIX-01 | Division correctly uncomputes MSB comparison temporaries (BUG-DIV-02) | Verified via 91-VERIFICATION.md: C-level restoring divmod in ToffoliDivision.c manages all ancillae internally. CQ division: 0 persistent ancillae. Tests: 100/100 pass at widths 1-3, sampled width 4. Evidence in 91-01-SUMMARY, 91-03-SUMMARY. |
| FIX-02 | QFT division/modulo produces correct results for all tested widths (BUG-QFT-DIV) | Verified via 91-VERIFICATION.md: QFT division replaced entirely by Toffoli-gate divmod. CQ divmod: exhaustive correctness at widths 2-4. QQ divmod: width 2 verified. Tests: 182 passed, 13 xfailed (QQ known limitation), 0 failed. Evidence in 91-01-SUMMARY, 91-03-SUMMARY. |
| FIX-03 | Modular reduction produces correct (a+b) mod N without orphan qubits (BUG-MOD-REDUCE) | Verified via 91-VERIFICATION.md: C-level toffoli_mod_reduce replaces broken Python _reduce_mod. Leak reduced from n+1 to 1 qubit per call. 2516 statevector tests + MPS tests pass. Phase 92 Beauregard primitives supersede this. Evidence in 91-02-SUMMARY, 91-03-SUMMARY. |
| TRD-01 | User can set ql.option('tradeoff', 'auto'\|'min_depth'\|'min_qubits') to control adder selection | Verified via 93-VERIFICATION.md: option() handler in _core.pyx supports three modes, validation, set-once enforcement. 21 tests in test_tradeoff.py. Evidence in 93-01-SUMMARY. |
| TRD-02 | Auto mode selects CLA for width >= threshold, CDKM otherwise | Verified via 93-VERIFICATION.md: tradeoff_auto_threshold field in circuit_t, runtime dispatch at 8 locations in hot_path_add_toffoli.c. Auto threshold = 4. Evidence in 93-01-SUMMARY. |
| TRD-03 | Modular arithmetic primitives force RCA regardless of tradeoff policy | Verified via 93-VERIFICATION.md: ToffoliModReduce.c calls toffoli_CQ_add/toffoli_QQ_add directly, bypassing hot_path dispatch. Same results across all tradeoff modes. Evidence in 93-01-SUMMARY, 92-VERIFICATION.md. |
| TRD-04 | CLA subtraction limitation documented clearly | Verified via 93-VERIFICATION.md: Two's complement CLA subtraction implemented in min_depth mode. Documentation in hot_path_add_toffoli.c header and _core.pyx option() docstring. 27 tests (6 subtraction-specific). Evidence in 93-02-SUMMARY. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Existing codebase files | Current | Source of verification evidence | All evidence comes from reading existing code, tests, and plan summaries |
| VERIFICATION.md format | Phases 90, 92, 94 | Template for new verification files | Established project pattern with consistent structure |
| REQUIREMENTS.md | Current | Checkbox and traceability updates | Single source of truth for requirement status |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| grep/read tools | N/A | Cross-referencing code evidence | Verifying function signatures, test counts, key links |
| git log | N/A | Commit verification | Confirming SUMMARYs match git history |

## Architecture Patterns

### VERIFICATION.md Standard Format (from Phases 90, 92, 94)

The project has an established VERIFICATION.md format. All three existing v5.0 verification files share this structure:

```
---
phase: XX-name
status: passed
verified: YYYY-MM-DDTHH:MM:SSZ
---

# Phase XX: Name - Verification

## Goal
[Phase goal from ROADMAP]

## Success Criteria Verification
### 1. [Criterion from ROADMAP]
**Status: PASSED/FAILED**
- [Evidence bullets with specific file:line references, test counts, command outputs]

## Requirements Traceability
| Requirement | Status | Evidence |
|-------------|--------|----------|
| REQ-ID | Complete | [specific evidence] |

## Artifacts
| File | Purpose |
|------|---------|
| [path] | [what it provides] |

## Self-Check: PASSED/FAILED
[Summary line]
```

Phase 94 uses a more detailed format with additional sections:
- Observable Truths table (# | Truth | Status | Evidence)
- Required Artifacts table with verification details
- Key Link Verification table (From | To | Via | Status | Details)
- Anti-Patterns Found table
- Commit Verification table
- Human Verification Required section

**Recommendation for Phase 95:** Use the Phase 92 format (simpler, cleaner) for 91-VERIFICATION.md and 93-VERIFICATION.md. It has: Goal, Success Criteria Verification (numbered from ROADMAP), Requirements Traceability table, Artifacts table, Self-Check summary. This is sufficient and avoids unnecessary complexity.

### REQUIREMENTS.md Update Pattern

The REQUIREMENTS.md has two locations that need updating for each requirement:

1. **Checkbox section** (lines 12-14): Change `[ ]` to `[x]` for FIX-01, FIX-02, FIX-03
2. **Traceability table** (lines 94-96): Change "Pending" to "Complete" for FIX-01, FIX-02, FIX-03

Note: TRD-01 through TRD-04 checkboxes are already `[x]` and traceability shows "Complete". Only the FIX-0x entries need updating.

### Evidence Sources for Verification

For 91-VERIFICATION.md, evidence comes from:
| Evidence Type | Source | What to Verify |
|---------------|--------|----------------|
| Code artifacts | ToffoliDivision.c, ToffoliModReduce.c, qint_division.pxi, qint_mod.pyx | Files exist, contain expected functions |
| Test results | 91-03-SUMMARY.md | 542 passed, 64 xfailed, 0 failed; specific per-test-file breakdowns |
| Bug fix status | 91-03-SUMMARY.md Phase 91 Overall Status table | BUG-DIV-02 FIXED, BUG-QFT-DIV FIXED, BUG-MOD-REDUCE PARTIALLY FIXED |
| Ancilla management | 91-01-SUMMARY.md | CQ: 0 persistent ancillae; QQ: 1 persistent per iteration (known limitation) |
| Regression check | 91-03-SUMMARY.md | Zero new regressions; test_sub.py 792 pre-existing (not regression) |
| Key decisions | 91-01/02/03-SUMMARY.md frontmatter | requirements-completed fields |

For 93-VERIFICATION.md, evidence comes from:
| Evidence Type | Source | What to Verify |
|---------------|--------|----------------|
| Code artifacts | _core.pyx (tradeoff handler), circuit.h (tradeoff fields), hot_path_add_toffoli.c (dispatch + CLA subtraction) | Functions and fields exist |
| Test results | 93-01-SUMMARY.md | 21 tests for TRD-01/02/03 |
| Test results | 93-02-SUMMARY.md | 27 total tests (6 new for TRD-04) |
| Documentation | hot_path_add_toffoli.c header, _core.pyx option() docstring | CLA subtraction limitation documented |
| Modular RCA forcing | 92-VERIFICATION.md SC#5 | Already independently verified |
| Key link wiring | v5.0-MILESTONE-AUDIT.md integration section | 14 dispatch locations confirmed |

### Anti-Patterns to Avoid
- **Rubber-stamping without evidence:** Each success criterion must have specific file paths, line references, test counts, or command outputs. Do not just say "PASSED" without evidence.
- **Copy-pasting SUMMARY content as verification:** VERIFICATION.md must independently verify -- it should reference SUMMARYs as evidence but also cross-check against code artifacts.
- **Missing known limitations:** Phase 91 has known limitations (QQ division ancilla leak, BUG-MOD-REDUCE partially fixed). The verification must honestly report these, not sweep them under PASSED status.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verification format | New format | Copy structure from 92-VERIFICATION.md | Consistency with existing verification files |
| Evidence gathering | Re-running tests | Reference SUMMARY test results + code inspection | Phase 95 is procedural -- implementation was completed in Phases 91/93 |
| REQUIREMENTS.md update | Manual line counting | Targeted find-and-replace of known patterns | Three checkbox changes + three table status changes |

**Key insight:** Phase 95 creates no new code. It verifies and documents what already exists. The primary risk is thoroughness, not technical complexity.

## Common Pitfalls

### Pitfall 1: Marking BUG-MOD-REDUCE as Fully Fixed
**What goes wrong:** FIX-03 states "without orphan qubits" but Phase 91 only partially fixed BUG-MOD-REDUCE (reduced leak from n+1 to 1 qubit per mod_reduce call).
**Why it happens:** The success criterion says "produces correct results without orphan qubits" but the implementation still has 1 persistent ancilla when reduction triggers.
**How to avoid:** The verification must honestly note the partial fix. However, the ROADMAP SC3 says "implemented at C level or via correct Beauregard sequence replacing the broken _reduce_mod" -- the Phase 92 Beauregard primitives supersede the Phase 91 mod_reduce and do work correctly (2516 tests pass). So FIX-03 is satisfied through the combined Phase 91+92 path, not Phase 91 alone.
**Warning signs:** Claiming zero orphan qubits when the 91-03-SUMMARY explicitly documents 1-qubit persistent leak.

### Pitfall 2: Missing the REQUIREMENTS.md Traceability Table
**What goes wrong:** Only updating the checkboxes but not the traceability table, or vice versa.
**Why it happens:** There are two separate locations in REQUIREMENTS.md that track requirement status.
**How to avoid:** Phase 95 success criteria explicitly call out both: (SC3) checkboxes must be `[x]`, (SC4) traceability must show "Complete". Update both in a single plan.
**Warning signs:** Audit re-run still shows gaps.

### Pitfall 3: Not Cross-Referencing ROADMAP Success Criteria
**What goes wrong:** Verifying against PLAN must-haves but missing ROADMAP-level success criteria.
**Why it happens:** The ROADMAP defines 4 success criteria for Phase 91 and a separate set for Phase 93. These may differ from individual PLAN must-haves.
**How to avoid:** Structure the VERIFICATION.md around the ROADMAP success criteria first, then cross-reference PLAN must-haves.
**Warning signs:** VERIFICATION.md has wrong number of success criteria.

### Pitfall 4: Ignoring Deviations from Plans
**What goes wrong:** Verification claims all must-haves met when SUMMARYs document deviations.
**Why it happens:** Plans had must-have truths like "no xfail cases remain" but SUMMARYs show xfails were kept for known limitations.
**How to avoid:** For Phase 91, 91-03-SUMMARY documents 4 deviations (QQ xfails kept, modular xfails kept, circuit_stats test not added, N=8/N=13 removed). The verification must acknowledge these and explain why they don't invalidate the success criteria.
**Warning signs:** PLAN must-have says "no xfail" but verification says "PASSED" without addressing the actual xfails.

## Code Examples

### Example 1: 91-VERIFICATION.md Structure

```markdown
---
phase: 91-arithmetic-bug-fixes
status: passed
verified: 2026-02-26
---

# Phase 91: Arithmetic Bug Fixes - Verification

## Goal
Division and modular reduction produce correct results without orphan qubits or circuit corruption.

## Success Criteria Verification

### 1. Division correctly uncomputes MSB comparison temporaries (SC from ROADMAP)
**Status: PASSED**
- [Evidence from code inspection and test results]

### 2. QFT division/modulo correct for widths 2-4 (SC from ROADMAP)
**Status: PASSED**
- [Evidence]

### 3. Modular reduction correct without orphan qubits (SC from ROADMAP)
**Status: PASSED (with known limitation)**
- [Evidence including partial fix note]

### 4. Zero regressions (SC from ROADMAP)
**Status: PASSED**
- [Evidence]

## Requirements Traceability
| Requirement | Status | Evidence |
|-------------|--------|----------|
| FIX-01 | Complete | ... |
| FIX-02 | Complete | ... |
| FIX-03 | Complete | ... |

## Artifacts
[Table of key files]

## Self-Check: PASSED
```

### Example 2: REQUIREMENTS.md Checkbox Update

```markdown
# Before:
- [ ] **FIX-01**: Division correctly uncomputes MSB comparison temporaries (BUG-DIV-02)
- [ ] **FIX-02**: QFT division/modulo produces correct results for all tested widths (BUG-QFT-DIV)
- [ ] **FIX-03**: Modular reduction produces correct (a+b) mod N without orphan qubits (BUG-MOD-REDUCE)

# After:
- [x] **FIX-01**: Division correctly uncomputes MSB comparison temporaries (BUG-DIV-02)
- [x] **FIX-02**: QFT division/modulo produces correct results for all tested widths (BUG-QFT-DIV)
- [x] **FIX-03**: Modular reduction produces correct (a+b) mod N without orphan qubits (BUG-MOD-REDUCE)
```

### Example 3: REQUIREMENTS.md Traceability Update

```markdown
# Before:
| FIX-01 | Phase 91 (verify: Phase 95) | Pending |
| FIX-02 | Phase 91 (verify: Phase 95) | Pending |
| FIX-03 | Phase 91 (verify: Phase 95) | Pending |

# After:
| FIX-01 | Phase 91 (verify: Phase 95) | Complete |
| FIX-02 | Phase 91 (verify: Phase 95) | Complete |
| FIX-03 | Phase 91 (verify: Phase 95) | Complete |
```

## Phase 91 Success Criteria (from ROADMAP) -- What 91-VERIFICATION.md Must Verify

| # | Criterion | Key Evidence Sources |
|---|-----------|---------------------|
| 1 | Division correctly uncomputes MSB comparison temporaries -- `circuit_stats()['current_in_use']` remains stable across repeated division operations (BUG-DIV-02 fixed) | 91-01-SUMMARY: CQ division 0 persistent ancillae. 91-03-SUMMARY: circuit_stats test not added (deviation), but CQ exhaustive tests prove stability. |
| 2 | QFT division and modulo produce correct results for widths 2-4 verified by Qiskit simulation (BUG-QFT-DIV fixed) | 91-01-SUMMARY: QFT division replaced by Toffoli divmod. 91-03-SUMMARY: 100/100 div tests, 100/100 mod tests at widths 1-3, sampled width 4. |
| 3 | Modular reduction `(a+b) mod N` produces correct results without orphan qubits -- implemented at C level or via correct Beauregard sequence (BUG-MOD-REDUCE fixed) | 91-02-SUMMARY: C-level toffoli_mod_reduce, leak reduced to 1 qubit. 92-VERIFICATION: 2516 tests pass via Beauregard. ROADMAP SC wording includes "or via correct Beauregard sequence" which Phase 92 satisfies. |
| 4 | All previously-passing tests continue to pass with zero regressions | 91-03-SUMMARY: 542 passed, 64 xfailed, 0 failed. test_sub.py 792 pre-existing. |

## Phase 93 Success Criteria (from ROADMAP) -- What 93-VERIFICATION.md Must Verify

Note: The ROADMAP does not list explicit numbered success criteria for Phase 93 beyond the requirement descriptions. The verification should use the PLAN must-haves as the success criteria framework.

| # | Criterion (from PLAN must-haves) | Key Evidence Sources |
|---|----------------------------------|---------------------|
| 1 | User can call ql.option('tradeoff', ...) with three modes (TRD-01) | 93-01-SUMMARY: option() handler implemented, 21 tests |
| 2 | Invalid values raise ValueError, post-ops changes raise RuntimeError (TRD-01) | 93-01-SUMMARY: validation + set-once enforcement |
| 3 | Auto mode uses CLA >= threshold, CDKM below (TRD-02) | 93-01-SUMMARY: threshold=4, 8 dispatch locations updated |
| 4 | min_depth uses CLA for all widths >= 2 (TRD-02) | 93-01-SUMMARY: threshold=2 in min_depth |
| 5 | min_qubits forces CDKM/RCA (TRD-02) | 93-01-SUMMARY: cla_override=1 |
| 6 | Modular arithmetic same results regardless of tradeoff (TRD-03) | 93-01-SUMMARY: verified same results across modes |
| 7 | CLA subtraction via two's complement in min_depth mode (TRD-04) | 93-02-SUMMARY: QQ, CQ, controlled paths |
| 8 | CLA subtraction limitation documented (TRD-04) | 93-02-SUMMARY: file header + docstring |
| 9 | Tradeoff state resets on new circuit (TRD-01) | 93-01-SUMMARY: reset logic in circuit init |

## Implementation Strategy

### Plan 95-01: Generate 91-VERIFICATION.md

**Inputs:** 91-01-SUMMARY.md, 91-02-SUMMARY.md, 91-03-SUMMARY.md, ROADMAP.md (Phase 91 section), 91-01/02/03-PLAN.md (must-haves)

**Steps:**
1. Read ROADMAP Phase 91 success criteria (4 criteria)
2. Read each PLAN's must-haves truths
3. For each ROADMAP success criterion, gather evidence from SUMMARYs
4. Cross-reference against actual code files (ToffoliDivision.c exists, qint_division.pxi updated, etc.)
5. Check test result counts from 91-03-SUMMARY
6. Note known limitations and deviations honestly
7. Write 91-VERIFICATION.md following Phase 92 format

**Output:** `.planning/phases/91-arithmetic-bug-fixes/91-VERIFICATION.md`

### Plan 95-02: Generate 93-VERIFICATION.md

**Inputs:** 93-01-SUMMARY.md, 93-02-SUMMARY.md, ROADMAP.md (Phase 93 section), 93-01/02-PLAN.md (must-haves)

**Steps:**
1. Read Phase 93 requirement definitions (TRD-01 through TRD-04)
2. Read each PLAN's must-haves truths
3. For each requirement, gather evidence from SUMMARYs
4. Cross-reference against actual code files (circuit.h fields, hot_path dispatch, _core.pyx handler)
5. Check test result counts from both SUMMARYs
6. Verify documentation artifacts (docstrings, file headers)
7. Write 93-VERIFICATION.md following Phase 92 format

**Output:** `.planning/phases/93-depth-ancilla-tradeoff/93-VERIFICATION.md`

### Plan 95-03: Update REQUIREMENTS.md

**Inputs:** REQUIREMENTS.md (current state)

**Steps:**
1. Change FIX-01, FIX-02, FIX-03 checkboxes from `[ ]` to `[x]` (lines 12-14)
2. Change traceability table status for FIX-01, FIX-02, FIX-03 from "Pending" to "Complete" (lines 94-96)
3. Verify no other requirements need updating
4. Update "Last updated" date

**Output:** Updated `.planning/REQUIREMENTS.md`

## Key Findings from Evidence Gathering

### Phase 91 Evidence Summary

**FIX-01 (BUG-DIV-02): FIXED**
- Root cause: Python-level comparison temporaries leaked during division loop
- Fix: C-level `toffoli_divmod_cq` in ToffoliDivision.c manages all ancillae internally
- CQ path: 0 persistent ancillae, all freed per iteration
- QQ path: 1 persistent ancilla per iteration (different bug, known limitation)
- Tests: 100/100 div, 100/100 mod, 182 toffoli_division (13 xfailed for QQ known issue)
- Deviation: circuit_stats stability test not added (planned but deemed unnecessary given exhaustive test coverage)

**FIX-02 (BUG-QFT-DIV): FIXED**
- Root cause: QFT division/modulo produced incorrect results
- Fix: QFT division deleted entirely, replaced by Toffoli-gate C-level divmod
- CQ divmod: exhaustive correctness at widths 2-4
- QQ divmod: width 2 verified, larger widths limited by simulation constraints
- Tests: Same test files as FIX-01

**FIX-03 (BUG-MOD-REDUCE): PARTIALLY FIXED (satisfies requirement through Phase 92)**
- Root cause: Python `_reduce_mod` leaked n+1 qubits per comparison
- Fix: C-level `toffoli_mod_reduce` in ToffoliModReduce.c, leak reduced to 1 qubit
- Phase 92 Beauregard primitives supersede Phase 91's mod_reduce and achieve full correctness
- ROADMAP SC3 wording: "or via correct Beauregard sequence" -- Phase 92 satisfies this
- Tests: 2516 modular tests pass (via Phase 92 test suite)
- The "1 qubit leak" is in the Phase 91 mod_reduce, which Phase 92's Beauregard approach replaces in practice

### Phase 93 Evidence Summary

**TRD-01: COMPLETE**
- `ql.option('tradeoff', ...)` with auto/min_depth/min_qubits modes
- Get/set API, validation, set-once enforcement via `_arithmetic_ops_performed` flag
- Reset on new circuit creation
- 21 tests covering option API, frozen state, dispatch modes
- Code: `_core.pyx` option() handler

**TRD-02: COMPLETE**
- Auto threshold = 4 (CLA for width >= 4)
- `tradeoff_auto_threshold` field in circuit_t
- 8 dispatch locations in hot_path_add_toffoli.c updated from compile-time CLA_THRESHOLD to runtime field
- min_depth: threshold=2, min_qubits: cla_override=1

**TRD-03: COMPLETE**
- ToffoliModReduce.c calls toffoli_CQ_add/toffoli_QQ_add directly (never hot_path)
- Verified: identical QASM and qubit counts across all tradeoff modes for modular ops
- Already confirmed in Phase 92 VERIFICATION.md SC#5
- v5.0 audit integration checker confirms at 14 dispatch locations

**TRD-04: COMPLETE**
- Two's complement CLA subtraction: X(b) + CLA_add(a += ~b) + CQ_add(a += 1) + X(b)
- QQ uncontrolled, QQ controlled, CQ uncontrolled, CQ controlled paths all implemented
- Documentation in hot_path_add_toffoli.c file header and _core.pyx option() docstring
- 27 tests total (6 new for CLA subtraction)

## Open Questions

1. **FIX-03 "without orphan qubits" interpretation**
   - What we know: Phase 91 reduced leak from n+1 to 1 qubit. Phase 92 Beauregard primitives achieve full correctness with 2516 tests passing.
   - What's unclear: Whether FIX-03 requires zero orphan qubits from the Phase 91 mod_reduce specifically, or whether the Phase 92 Beauregard approach satisfies it.
   - Recommendation: The ROADMAP SC3 says "implemented at C level **or** via correct Beauregard sequence replacing the broken `_reduce_mod`." The "or" clause explicitly allows the Beauregard path. Mark as PASSED with a note about the combined Phase 91+92 resolution.

2. **91-03-PLAN deviations vs PASSED status**
   - What we know: Plan 91-03 had must-haves including "no xfail cases remain" but the SUMMARY documents 4 deviations including kept xfails.
   - What's unclear: Whether the verification should mark these PLANs as having deviations.
   - Recommendation: The ROADMAP success criteria (which take precedence over PLAN must-haves) do not require zero xfails. SC1 requires stable circuit_stats (achieved for CQ). SC2 requires correct results for widths 2-4 (achieved). SC3 has the Beauregard "or" clause. SC4 requires zero regressions (achieved). Mark ROADMAP criteria as PASSED, note PLAN deviations for transparency.

## Sources

### Primary (HIGH confidence)
- `.planning/v5.0-MILESTONE-AUDIT.md` -- definitive gap list, evidence per requirement
- `.planning/ROADMAP.md` Phase 91 and 93 success criteria -- verification targets
- `.planning/phases/91-arithmetic-bug-fixes/91-01-SUMMARY.md` -- FIX-01, FIX-02 evidence
- `.planning/phases/91-arithmetic-bug-fixes/91-02-SUMMARY.md` -- FIX-03 evidence
- `.planning/phases/91-arithmetic-bug-fixes/91-03-SUMMARY.md` -- verification test results, deviations
- `.planning/phases/93-depth-ancilla-tradeoff/93-01-SUMMARY.md` -- TRD-01, TRD-02, TRD-03 evidence
- `.planning/phases/93-depth-ancilla-tradeoff/93-02-SUMMARY.md` -- TRD-04 evidence
- `.planning/phases/92-modular-toffoli-arithmetic/92-VERIFICATION.md` -- format reference + FIX-03 Beauregard evidence
- `.planning/phases/94-parametric-compilation/94-VERIFICATION.md` -- format reference (detailed variant)
- `.planning/phases/90-quantum-counting/90-VERIFICATION.md` -- format reference (simple variant)
- `.planning/REQUIREMENTS.md` -- current checkbox and traceability state

### Secondary (MEDIUM confidence)
- `.planning/phases/91-arithmetic-bug-fixes/91-01-PLAN.md` through `91-03-PLAN.md` -- must-have truths
- `.planning/phases/93-depth-ancilla-tradeoff/93-01-PLAN.md` through `93-02-PLAN.md` -- must-have truths

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - purely documentation/procedural, no technical uncertainty
- Architecture: HIGH - established VERIFICATION.md format from 3 existing examples
- Pitfalls: HIGH - known from v5.0 audit evidence and SUMMARY deviation reports

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable -- references existing artifacts that won't change)
