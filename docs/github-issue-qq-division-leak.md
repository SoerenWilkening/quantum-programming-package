# GitHub Issue: QQ Division Ancilla Leak

Use this content to create a GitHub issue on `SoerenWilkening/speed-oriented-quantum-circuit-backend`.

**Title:** QQ division: comparison ancilla leak in repeated-subtraction path

**Labels:** bug, known-limitation

**Body:**

## Description

`toffoli_divmod_qq` in `c_backend/src/ToffoliDivision.c` leaks 2^n comparison ancillae per call (n = dividend width). The comparison ancillae allocated during the repeated-subtraction loop become entangled with the computation state and cannot be efficiently uncomputed.

## Affected Functions

- `toffoli_divmod_qq` (line 470 in `c_backend/src/ToffoliDivision.c`)
- `toffoli_cdivmod_qq` (controlled variant, same issue)

## Impact

- QQ division is unreliable for widths > 2
- Known test failures documented in `KNOWN_TOFFOLI_QDIV_FAILURES` (`tests/test_toffoli_division.py`)
- CQ division (classical divisor) is NOT affected

## Workaround

Use CQ division when the divisor is classically known.

## Potential Fixes

1. Full Bennett's trick at iteration level (doubles circuit size)
2. Alternative QQ division algorithms (Newton-Raphson, etc.)
3. Logarithmic-depth reversible comparison
4. Accept leak for small widths (current approach)

## References

- Detailed inline analysis: `ToffoliDivision.c` lines 605-828
- Known issues doc: `docs/KNOWN-ISSUES.md`
- Test xfails: `tests/test_toffoli_division.py` lines 43-56
