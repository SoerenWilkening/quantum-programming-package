# Known Issues & Limitations

Known limitations in the Quantum Assembly framework. Each entry includes impact, workaround, and potential fix approaches.

## QQ Division Ancilla Leak

**Status:** Known limitation (since Phase 91)
**Tracking:** GitHub issue pending
**Affected:** `toffoli_divmod_qq` in `c_backend/src/ToffoliDivision.c`
**Impact:** QQ division leaks 2^n comparison ancillae per call (n = dividend width)
**Test coverage:** `KNOWN_TOFFOLI_QDIV_FAILURES` in `tests/test_toffoli_division.py`

### Description

The quantum-divisor variant of Toffoli division (`toffoli_divmod_qq`) uses repeated subtraction with 2^n iterations for an n-bit dividend. Each iteration allocates a comparison ancilla (`cmp_anc`) to determine whether the remainder is greater than or equal to the divisor. After the conditional subtraction and quotient increment, the comparison ancilla is entangled with the computation state (remainder + quotient registers) and cannot be efficiently uncomputed.

The fundamental problem: the comparison result depends on the quantum remainder state, which changes each iteration. Standard uncomputation (re-derive the comparison on the post-operation state) fails because the remainder may have been modified by the conditional subtraction. Full Bennett's trick (running the entire iteration backward) would double the circuit for each iteration.

CQ division (classical divisor) does NOT have this issue -- it uses bit-serial restoring division where the comparison is against a classical value, enabling proper Bennett's trick uncomputation at each bit position.

### Workaround

Use CQ division (classical divisor) whenever possible. CQ division uses bit-serial restoring division with proper Bennett's trick uncomputation and has zero ancilla leak.

When the divisor must be quantum, limit operand widths to 2-3 bits where the ancilla count (4-8) is manageable for simulation.

### Potential Fix Approaches

1. **Full Bennett's trick at iteration level** -- Run each iteration forward, copy the result, run backward to uncompute. Doubles circuit size per iteration, resulting in O(4^n) total gates.
2. **Alternative QQ division algorithms** -- Newton-Raphson quantum division or other algorithms that avoid the repeated-subtraction pattern.
3. **Logarithmic-depth comparison with reversible uncomputation** -- Replace the linear comparison chain with a reversible tree structure.
4. **Accept the leak for small widths** -- Current approach. Practical for widths 2-3.
