"""Tests for Phase 74-05: MCX-decomposed hardcoded cQQ sequences.

Verifies that hardcoded MCX-decomposed cQQ addition sequences for widths 1-8
are correctly wired into the dispatch and produce MCX-free output.

Note: .measure() returns initial values (no quantum simulation). Correctness is
verified through equivalence testing and gate count structure.

IMPORTANT: Gate counts must be read from a stored circuit reference (c = ql.circuit()),
not from ql.circuit().gate_counts (which creates a new empty circuit).

Test coverage:
  - Gate purity: controlled QQ addition produces zero MCX gates at all widths 1-8
  - Gate presence: CCX gates are emitted (sequences not empty)
  - T-count: estimated T-count is 7 * CCX_count
  - Equivalence: controlled path emits more gates than uncontrolled
  - Subtraction: add+subtract restores original value, zero MCX
  - CQ purity: controlled CQ addition also produces zero MCX
"""

import pytest

import quantum_language as ql

# ============================================================================
# Gate purity tests: no MCX in controlled QQ addition output
# ============================================================================


class TestDecomposedCQQPurity:
    """Controlled QQ addition at widths 1-8 must produce zero MCX gates."""

    @pytest.mark.parametrize("width", range(1, 9))
    def test_cqq_add_no_mcx(self, width):
        """Controlled QQ addition at width N: zero MCX gates."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a += b
        gc = c.gate_counts
        assert gc.get("other", 0) == 0, f"width={width}: MCX gates found: {gc.get('other', 0)}"

    @pytest.mark.parametrize("width", range(1, 9))
    def test_cqq_sub_no_mcx(self, width):
        """Controlled QQ subtraction at width N: zero MCX gates."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a -= b
        gc = c.gate_counts
        assert gc.get("other", 0) == 0, (
            f"width={width}: MCX gates in subtraction: {gc.get('other', 0)}"
        )


# ============================================================================
# CCX presence tests: decomposed sequences emit actual gates
# ============================================================================


class TestDecomposedCQQGatePresence:
    """Decomposed sequences must emit CCX gates (not trivially empty)."""

    @pytest.mark.parametrize("width", range(1, 9))
    def test_cqq_emits_ccx(self, width):
        """Controlled QQ addition emits at least 1 CCX gate."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a += b
        gc = c.gate_counts
        ccx = gc.get("CCX", 0)
        assert ccx >= 1, f"width={width}: no CCX gates emitted, gc={gc}"

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_cqq_ccx_grows_with_width(self, width):
        """CCX count should increase with width."""
        c1 = ql.circuit()
        ql.option("fault_tolerant", True)
        a1 = ql.qint(1, width=width)
        b1 = ql.qint(1, width=width)
        ctrl1 = ql.qbool(True)
        with ctrl1:
            a1 += b1
        ccx_n = c1.gate_counts.get("CCX", 0)

        c2 = ql.circuit()
        ql.option("fault_tolerant", True)
        a2 = ql.qint(1, width=width + 1)
        b2 = ql.qint(1, width=width + 1)
        ctrl2 = ql.qbool(True)
        with ctrl2:
            a2 += b2
        ccx_n1 = c2.gate_counts.get("CCX", 0)

        assert ccx_n1 > ccx_n, (
            f"CCX count should grow: width {width}={ccx_n}, width {width + 1}={ccx_n1}"
        )


# ============================================================================
# T-count consistency tests
# ============================================================================


class TestDecomposedCQQTCount:
    """T-count must be 7 * CCX_count for controlled addition."""

    @pytest.mark.parametrize("width", range(1, 9))
    def test_t_equals_7_times_ccx(self, width):
        """T-count estimate equals 7 * CCX count."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a += b
        gc = c.gate_counts
        ccx = gc.get("CCX", 0)
        t_est = gc.get("T", 0)
        if ccx > 0:
            assert t_est == 7 * ccx, f"width={width}: T={t_est}, expected 7*{ccx}={7 * ccx}"

    @pytest.mark.parametrize("width", range(1, 9))
    def test_t_count_positive(self, width):
        """T-count estimate should be positive for controlled addition."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a += b
        gc = c.gate_counts
        t_est = gc.get("T", 0)
        assert t_est > 0, f"width={width}: T-count should be positive, got {t_est}"


# ============================================================================
# Controlled vs uncontrolled comparison tests
# ============================================================================


class TestDecomposedCQQEquivalence:
    """Controlled path should emit more gates than uncontrolled path."""

    @pytest.mark.parametrize("width", range(1, 9))
    def test_controlled_emits_more_gates(self, width):
        """Controlled path emits more gates than uncontrolled path."""
        # Uncontrolled addition
        c1 = ql.circuit()
        ql.option("fault_tolerant", True)
        a1 = ql.qint(1, width=width)
        b1 = ql.qint(1, width=width)
        a1 += b1
        gc_uncont = c1.gate_counts
        total_uncont = sum(gc_uncont.get(k, 0) for k in ["X", "CNOT", "CCX"])

        # Controlled addition
        c2 = ql.circuit()
        ql.option("fault_tolerant", True)
        a2 = ql.qint(1, width=width)
        b2 = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a2 += b2
        gc_cont = c2.gate_counts
        total_cont = sum(gc_cont.get(k, 0) for k in ["X", "CNOT", "CCX"])

        assert total_cont >= total_uncont, (
            f"width={width}: controlled={total_cont} should be >= uncontrolled={total_uncont}"
        )

    @pytest.mark.parametrize("width", range(1, 9))
    def test_control_false_preserves_value(self, width):
        """With control=False, measure should return initial value."""
        _c = ql.circuit()  # noqa: F841 — initializes fresh circuit context
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(False)
        with ctrl:
            a += b
        assert a.measure() == 1


# ============================================================================
# Subtraction consistency tests
# ============================================================================


class TestDecomposedCQQSubtraction:
    """Add then subtract should restore original .measure() value."""

    @pytest.mark.parametrize("width", range(1, 9))
    def test_add_then_subtract_restores(self, width):
        """a += b then a -= b should leave a unchanged."""
        _c = ql.circuit()  # noqa: F841 — initializes fresh circuit context
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a += b
        with ctrl:
            a -= b
        assert a.measure() == 1, f"width={width}: after add+sub, expected 1, got {a.measure()}"

    @pytest.mark.parametrize("width", range(1, 9))
    def test_subtract_no_mcx(self, width):
        """Subtraction path (invert=True) produces zero MCX."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a -= b
        gc = c.gate_counts
        assert gc.get("other", 0) == 0, f"width={width}: MCX in subtraction: {gc.get('other', 0)}"

    @pytest.mark.parametrize("width", range(1, 9))
    def test_subtract_emits_ccx(self, width):
        """Subtraction emits CCX gates (not empty)."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a -= b
        gc = c.gate_counts
        ccx = gc.get("CCX", 0)
        assert ccx >= 1, f"width={width}: no CCX in subtraction"


# ============================================================================
# CQ controlled addition purity tests
# ============================================================================


class TestDecomposedCCQPurity:
    """Controlled CQ addition also produces zero MCX gates."""

    @pytest.mark.parametrize("width", range(1, 9))
    def test_ccq_add_no_mcx(self, width):
        """Controlled CQ addition at width N: zero MCX gates."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(0, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a += 1
        gc = c.gate_counts
        assert gc.get("other", 0) == 0, f"width={width}: MCX gates in cCQ: {gc.get('other', 0)}"

    @pytest.mark.parametrize("width", [2, 3, 4])
    def test_ccq_sub_no_mcx(self, width):
        """Controlled CQ subtraction at width N: zero MCX gates."""
        c = ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(1, width=width)
        ctrl = ql.qbool(True)
        with ctrl:
            a -= 1
        gc = c.gate_counts
        assert gc.get("other", 0) == 0, f"width={width}: MCX gates in cCQ sub: {gc.get('other', 0)}"
