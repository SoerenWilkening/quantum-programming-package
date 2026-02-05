# Phase 38: Modular Reduction Fix - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix `_reduce_mod` in `qint_mod.pyx` so that modular arithmetic operations (add_mod, sub_mod, mul_mod) produce correct reduced values without corrupting the result register. The bug involves comparison ancilla entanglement with result qubits during iterative conditional subtraction. All BUG-MOD-REDUCE xfail markers must be removed.

</domain>

<decisions>
## Implementation Decisions

### Fix strategy
- Repair existing compare-and-subtract logic (do NOT rewrite algorithm)
- Investigate both ancilla uncomputation and result register tracking holistically — the root cause may involve both
- Minimize additional qubit overhead — try to fix without extra ancilla, but accept them if truly necessary
- Optimize iteration count if provably safe (e.g., ceil(log2(max_value/modulus)) instead of N iterations)

### Reduction correctness scope
- Prioritize add_mod and mul_mod; sub_mod has additional extraction instability but should still pass
- Both result=0 cases AND multi-iteration reduction cases must work correctly
- Focus on small moduli that fit comfortably in register width (mod 3, 5, 7 for 4-bit) — match existing test coverage
- Modulus >= 2 only; modulus=1 is out of scope

### Interaction with division
- Align fix approach with Phase 37 patterns where applicable — examine division fix for reusable ancilla management patterns
- Researcher should examine Phase 37 fix for comparison/subtraction patterns that may transfer
- Re-verify division tests after _reduce_mod fix to catch shared-code regressions
- Only regression-test basic qint arithmetic if shared code (in qint, not just qint_mod) is modified

### Test validation
- All modular tests must pass — zero BUG-MOD-REDUCE xfails remaining after this phase
- Remove xfail markers from test_modular.py as part of this phase (don't defer to Phase 41)
- Regression scope: modular + division tests (full suite deferred to Phase 41)

### Claude's Discretion
- Whether to make result extraction predictable (no calibration needed) or keep calibration-based approach — decide based on what the fix changes about qubit layout
- Exact iteration count optimization formula
- Internal ancilla allocation strategy

</decisions>

<specifics>
## Specific Ideas

- Phase 37 research noted _reduce_mod is "NOT affected by the same bug" (no shifting overflow), but the comparison/subtraction pattern is similar — look for transferable patterns in ancilla lifecycle management
- Root cause from Phase 30 analysis: comparison allocates qbool that entangles with result register; when subtraction brings value to 0, comparison/subtraction interaction corrupts result bits with residual state from comparison ancilla
- ~196/212 failures in test_modular.py, additional xfails in test_mod.py

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 38-modular-reduction-fix*
*Context gathered: 2026-02-02*
