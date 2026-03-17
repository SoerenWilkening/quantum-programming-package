"""Tests for blocker insertion on source operand usage.

Validates that every time a qint is used as a source operand (RHS of
an operation), a blocker is added to its history graph referencing the
result/destination qint.

Step 6.2: Blocker insertion on source operand usage [Quantum_Assembly-4q7.2].
"""

import quantum_language as ql

# ---------------------------------------------------------------------------
# add_creates_blocker
# ---------------------------------------------------------------------------


class TestAddCreatesBlocker:
    """Out-of-place addition adds blockers on both source operands."""

    def test_add_blockers_on_sources(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        c = a + b

        # Both a and b should have a blocker referencing c
        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert len(a_blockers) >= 1
        assert len(b_blockers) >= 1
        assert any(bl.dependent is c for bl in a_blockers)
        assert any(bl.dependent is c for bl in b_blockers)

    def test_add_classical_only_self_blocked(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = a + 1

        # Only a should have a blocker (classical int has no history)
        a_blockers = a.history.active_blockers_after(0)
        assert len(a_blockers) >= 1
        assert any(bl.dependent is c for bl in a_blockers)


# ---------------------------------------------------------------------------
# iadd_creates_blocker
# ---------------------------------------------------------------------------


class TestIaddCreatesBlocker:
    """In-place addition adds a blocker on the source (other) operand."""

    def test_iadd_blocker_on_other(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        a += b

        # b should have a blocker referencing a (the destination)
        b_blockers = b.history.active_blockers_after(0)
        assert len(b_blockers) >= 1
        assert any(bl.dependent is a for bl in b_blockers)

    def test_isub_blocker_on_other(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(2, width=4)
        a -= b

        # b should have a blocker referencing a
        b_blockers = b.history.active_blockers_after(0)
        assert len(b_blockers) >= 1
        assert any(bl.dependent is a for bl in b_blockers)


# ---------------------------------------------------------------------------
# comparison_creates_blocker
# ---------------------------------------------------------------------------


class TestComparisonCreatesBlocker:
    """Comparisons add blockers on source operands."""

    def test_eq_int_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        result = a == 3

        a_blockers = a.history.active_blockers_after(0)
        assert len(a_blockers) >= 1
        assert any(bl.dependent is result for bl in a_blockers)

    def test_eq_qint_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(3, width=4)
        result = a == b

        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert any(bl.dependent is result for bl in a_blockers)
        assert any(bl.dependent is result for bl in b_blockers)

    def test_lt_qint_blocker(self):
        ql.circuit()
        a = ql.qint(2, width=4)
        b = ql.qint(5, width=4)
        result = a < b

        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert any(bl.dependent is result for bl in a_blockers)
        assert any(bl.dependent is result for bl in b_blockers)

    def test_gt_qint_blocker(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(2, width=4)
        result = a > b

        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert any(bl.dependent is result for bl in a_blockers)
        assert any(bl.dependent is result for bl in b_blockers)


# ---------------------------------------------------------------------------
# xor_creates_blocker
# ---------------------------------------------------------------------------


class TestXorCreatesBlocker:
    """XOR operations add blockers on source operands."""

    def test_xor_blocker(self):
        ql.circuit()
        a = ql.qint(0b1100, width=5)
        b = ql.qint(0b0110, width=5)
        c = a ^ b

        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)
        assert any(bl.dependent is c for bl in b_blockers)

    def test_ixor_blocker_on_other(self):
        ql.circuit()
        a = ql.qint(0b1100, width=5)
        b = ql.qint(0b0110, width=5)
        a ^= b

        # b should have a blocker referencing a
        b_blockers = b.history.active_blockers_after(0)
        assert len(b_blockers) >= 1
        assert any(bl.dependent is a for bl in b_blockers)


# ---------------------------------------------------------------------------
# no_self_blocker
# ---------------------------------------------------------------------------


class TestNoSelfBlocker:
    """In-place operations on self (a += a, a ^= a) must not add blockers."""

    def test_iadd_self_no_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        blockers_before = len(a.history.blockers)
        a += a
        blockers_after = len(a.history.blockers)
        # Should not have added a self-blocker
        assert blockers_after == blockers_before

    def test_isub_self_no_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        blockers_before = len(a.history.blockers)
        a -= a
        blockers_after = len(a.history.blockers)
        assert blockers_after == blockers_before

    def test_ixor_self_no_blocker(self):
        ql.circuit()
        a = ql.qint(0b1010, width=5)
        blockers_before = len(a.history.blockers)
        a ^= a
        blockers_after = len(a.history.blockers)
        assert blockers_after == blockers_before


# ---------------------------------------------------------------------------
# Additional: other operations
# ---------------------------------------------------------------------------


class TestOtherOperationsCreateBlockers:
    """Other arithmetic/bitwise operations also insert blockers."""

    def test_sub_blocker(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(2, width=4)
        c = a - b

        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)
        assert any(bl.dependent is c for bl in b_blockers)

    def test_mul_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=4)
        c = a * 2

        a_blockers = a.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)

    def test_and_blocker(self):
        ql.circuit()
        a = ql.qint(0b1100, width=5)
        b = ql.qint(0b1010, width=5)
        c = a & b

        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)
        assert any(bl.dependent is c for bl in b_blockers)

    def test_or_blocker(self):
        ql.circuit()
        a = ql.qint(0b1100, width=5)
        b = ql.qint(0b0011, width=5)
        c = a | b

        a_blockers = a.history.active_blockers_after(0)
        b_blockers = b.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)
        assert any(bl.dependent is c for bl in b_blockers)

    def test_neg_blocker(self):
        ql.circuit()
        a = ql.qint(5, width=4)
        c = -a

        a_blockers = a.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)

    def test_lshift_blocker(self):
        ql.circuit()
        a = ql.qint(3, width=8)
        c = a << 2

        a_blockers = a.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)

    def test_rshift_blocker(self):
        ql.circuit()
        a = ql.qint(12, width=8)
        c = a >> 2

        a_blockers = a.history.active_blockers_after(0)
        assert any(bl.dependent is c for bl in a_blockers)
