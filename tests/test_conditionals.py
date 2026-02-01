"""Verification tests for quantum conditionals (VADV-02).

Tests that `with qbool:` blocks correctly gate operations:
- When condition is True, the gated operation executes
- When condition is False, the gated operation is skipped

Condition sources tested: CQ comparisons (gt, lt, eq, ne) and QQ comparisons (gt).
Gated operations tested: addition (+= 1), subtraction (-= 1), multiplication (*= 2).

Known bugs affecting conditionals:
- BUG-CMP-01: eq/ne return inverted results at comparison level, but
  empirically conditional gating still works correctly -- the qbool
  controls the with-block as expected despite the comparison inversion.
- BUG-CMP-02: Ordering comparisons fail when operands span MSB boundary.
  All tests use values in [0,3] for width=3 to avoid this.
- BUG-COND-MUL-01 (NEW): Controlled multiplication (cCQ_mul) corrupts
  the result register, returning 0 regardless of condition or operands.
"""

import warnings

import pytest

import quantum_language as ql

# Suppress cosmetic warnings for values near width boundary
warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# CQ Greater-than conditional (gt) -- no known bugs for safe values
# ---------------------------------------------------------------------------


class TestCondGt:
    """CQ greater-than as condition source."""

    def test_cond_gt_true(self, verify_circuit):
        """a=3 > 1 is True, so result += 1 should execute. Expected: 1."""

        def build():
            a = ql.qint(3, width=3)
            cond = a > 1
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (1, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_cond_gt_false(self, verify_circuit):
        """a=0 > 1 is False, so result += 1 should be skipped. Expected: 0."""

        def build():
            a = ql.qint(0, width=3)
            cond = a > 1
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (0, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# CQ Less-than conditional (lt) -- no known bugs for safe values
# ---------------------------------------------------------------------------


class TestCondLt:
    """CQ less-than as condition source."""

    def test_cond_lt_true(self, verify_circuit):
        """a=1 < 3 is True, so result += 1 should execute. Expected: 1."""

        def build():
            a = ql.qint(1, width=3)
            cond = a < 3
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (1, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_cond_lt_false(self, verify_circuit):
        """a=3 < 3 is False, so result += 1 should be skipped. Expected: 0."""

        def build():
            a = ql.qint(3, width=3)
            cond = a < 3
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (0, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# QQ Greater-than conditional -- no known bugs for safe values
# ---------------------------------------------------------------------------


class TestCondQQGt:
    """QQ greater-than (both operands quantum) as condition source."""

    def test_cond_qq_gt_true(self, verify_circuit):
        """a=3 > b=1 is True, so result += 1 should execute. Expected: 1."""

        def build():
            a = ql.qint(3, width=3)
            b = ql.qint(1, width=3)
            cond = a > b
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (1, [a, b, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_cond_qq_gt_false(self, verify_circuit):
        """a=1 > b=3 is False, so result += 1 should be skipped. Expected: 0."""

        def build():
            a = ql.qint(1, width=3)
            b = ql.qint(3, width=3)
            cond = a > b
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (0, [a, b, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# CQ Equality conditional (eq) -- BUG-CMP-01: eq is inverted
# ---------------------------------------------------------------------------


class TestCondEq:
    """CQ equality as condition source.

    Note: BUG-CMP-01 inverts eq results at the comparison level, but
    empirically the conditional gating still works correctly. The qbool
    produced by eq correctly controls the with-block despite the comparison
    inversion bug. Tests run without xfail.
    """

    def test_cond_eq_true(self, verify_circuit):
        """a=2 == 2 is True, so result += 1 should execute. Expected: 1."""

        def build():
            a = ql.qint(2, width=3)
            cond = a == 2
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (1, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_cond_eq_false(self, verify_circuit):
        """a=3 == 2 is False, so result += 1 should be skipped. Expected: 0."""

        def build():
            a = ql.qint(3, width=3)
            cond = a == 2
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (0, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# CQ Not-equal conditional (ne) -- BUG-CMP-01: ne is inverted
# ---------------------------------------------------------------------------


class TestCondNe:
    """CQ not-equal as condition source.

    Note: BUG-CMP-01 inverts ne results at the comparison level, but
    empirically the conditional gating still works correctly. The qbool
    produced by ne correctly controls the with-block despite the comparison
    inversion bug. Tests run without xfail.
    """

    def test_cond_ne_true(self, verify_circuit):
        """a=3 != 2 is True, so result += 1 should execute. Expected: 1."""

        def build():
            a = ql.qint(3, width=3)
            cond = a != 2
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (1, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_cond_ne_false(self, verify_circuit):
        """a=2 != 2 is False, so result += 1 should be skipped. Expected: 0."""

        def build():
            a = ql.qint(2, width=3)
            cond = a != 2
            result = ql.qint(0, width=3)
            with cond:
                result += 1
            return (0, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# Conditional subtraction -- gated -= 1
# ---------------------------------------------------------------------------


class TestCondSub:
    """Conditional subtraction: result starts at 3, gated -= 1."""

    def test_cond_sub_true(self, verify_circuit):
        """a=3 > 1 is True, so result -= 1 should execute. result: 3 -> 2."""

        def build():
            a = ql.qint(3, width=3)
            cond = a > 1
            result = ql.qint(3, width=3)
            with cond:
                result -= 1
            return (2, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_cond_sub_false(self, verify_circuit):
        """a=0 > 1 is False, so result -= 1 should be skipped. result stays 3."""

        def build():
            a = ql.qint(0, width=3)
            cond = a > 1
            result = ql.qint(3, width=3)
            with cond:
                result -= 1
            return (3, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# Conditional multiplication -- gated *= 2 (untested cCQ_mul)
# ---------------------------------------------------------------------------


class TestCondMul:
    """Conditional multiplication: result starts at 1, gated *= 2.

    BUG-COND-MUL-01: Controlled multiplication (cCQ_mul) produces 0 for both
    True and False branches, corrupting the result register entirely.
    The controlled variant exists in the C backend but is non-functional.
    """

    @pytest.mark.xfail(
        reason="BUG-COND-MUL-01: cCQ_mul corrupts result register (returns 0)",
        strict=False,
    )
    def test_cond_mul_true(self, verify_circuit):
        """a=3 > 1 is True, so result *= 2 should execute. result: 1 -> 2."""

        def build():
            a = ql.qint(3, width=3)
            cond = a > 1
            result = ql.qint(1, width=3)
            with cond:
                result *= 2
            return (2, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    @pytest.mark.xfail(
        reason="BUG-COND-MUL-01: cCQ_mul corrupts result register (returns 0)",
        strict=False,
    )
    def test_cond_mul_false(self, verify_circuit):
        """a=0 > 1 is False, so result *= 2 should be skipped. result stays 1."""

        def build():
            a = ql.qint(0, width=3)
            cond = a > 1
            result = ql.qint(1, width=3)
            with cond:
                result *= 2
            return (1, [a, cond, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"
