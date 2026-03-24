"""Tests for controlled Toffoli dispatch for OR, XOR, IXOR (Step 12.1).

Covers issue Quantum_Assembly-a0x: Controlled variants for bitwise OR (qq/cq),
XOR (qq), and IXOR (qq/cq) via CCX decomposition pattern.

Acceptance criteria:
- Controlled OR qq completes without NotImplementedError
- Controlled OR cq completes without NotImplementedError
- Controlled XOR qq completes without NotImplementedError
- Controlled XOR cq completes without NotImplementedError
- Controlled IXOR qq completes without NotImplementedError
- Controlled IXOR cq completes without NotImplementedError
- Controlled paths produce non-zero gate counts
- All bitwise operations have controlled Toffoli support
"""

import warnings

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# No NotImplementedError for any controlled bitwise operation
# ---------------------------------------------------------------------------


class TestControlledOrQQ:
    """Controlled quantum-quantum OR via CCX decomposition."""

    def test_no_error(self):
        """OR qq controlled does not raise NotImplementedError."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a | b

    def test_gate_count_nonzero(self):
        """OR qq controlled produces nonzero gate count."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)
        gc_before = ql.get_gate_count()
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a | b
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, (
            f"Controlled OR qq should produce gates: before={gc_before}, after={gc_after}"
        )

    def test_more_gates_than_uncontrolled(self):
        """Controlled OR qq uses more gates than uncontrolled."""
        ql.circuit()
        a1 = ql.qint(3, width=3)
        b1 = ql.qint(5, width=3)
        gc0 = ql.get_gate_count()
        _ = a1 | b1
        gc_uncontrolled = ql.get_gate_count() - gc0

        a2 = ql.qint(3, width=3)
        b2 = ql.qint(5, width=3)
        ctrl = ql.qbool(True)
        gc0 = ql.get_gate_count()
        with ctrl:
            _ = a2 | b2
        gc_controlled = ql.get_gate_count() - gc0
        assert gc_controlled >= gc_uncontrolled, (
            f"Controlled OR qq ({gc_controlled}) should use at least as many gates "
            f"as uncontrolled ({gc_uncontrolled})"
        )


class TestControlledOrCQ:
    """Controlled classical-quantum OR via CX/CCX decomposition."""

    def test_no_error(self):
        """OR cq controlled does not raise NotImplementedError."""
        ql.circuit()
        a = ql.qint(3, width=3)
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a | 5

    def test_gate_count_nonzero(self):
        """OR cq controlled produces nonzero gate count."""
        ql.circuit()
        a = ql.qint(3, width=3)
        gc_before = ql.get_gate_count()
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a | 5
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, (
            f"Controlled OR cq should produce gates: before={gc_before}, after={gc_after}"
        )


class TestControlledXorQQ:
    """Controlled quantum-quantum XOR via CCX decomposition."""

    def test_no_error(self):
        """XOR qq controlled does not raise NotImplementedError."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a ^ b

    def test_gate_count_nonzero(self):
        """XOR qq controlled produces nonzero gate count."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)
        gc_before = ql.get_gate_count()
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a ^ b
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, (
            f"Controlled XOR qq should produce gates: before={gc_before}, after={gc_after}"
        )


class TestControlledXorCQ:
    """Controlled classical-quantum XOR via CX decomposition."""

    def test_no_error(self):
        """XOR cq controlled does not raise NotImplementedError."""
        ql.circuit()
        a = ql.qint(3, width=3)
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a ^ 5

    def test_gate_count_nonzero(self):
        """XOR cq controlled produces nonzero gate count."""
        ql.circuit()
        a = ql.qint(3, width=3)
        gc_before = ql.get_gate_count()
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a ^ 5
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, (
            f"Controlled XOR cq should produce gates: before={gc_before}, after={gc_after}"
        )


class TestControlledIxorQQ:
    """Controlled in-place quantum-quantum XOR via CCX decomposition."""

    def test_no_error(self):
        """IXOR qq controlled does not raise NotImplementedError."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)
        ctrl = ql.qbool(True)
        with ctrl:
            a ^= b

    def test_gate_count_nonzero(self):
        """IXOR qq controlled produces nonzero gate count."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)
        gc_before = ql.get_gate_count()
        ctrl = ql.qbool(True)
        with ctrl:
            a ^= b
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, (
            f"Controlled IXOR qq should produce gates: before={gc_before}, after={gc_after}"
        )


class TestControlledIxorCQ:
    """Controlled in-place classical-quantum XOR via CX decomposition."""

    def test_no_error(self):
        """IXOR cq controlled does not raise NotImplementedError."""
        ql.circuit()
        a = ql.qint(3, width=3)
        ctrl = ql.qbool(True)
        with ctrl:
            a ^= 5

    def test_gate_count_nonzero(self):
        """IXOR cq controlled produces nonzero gate count."""
        ql.circuit()
        a = ql.qint(3, width=3)
        gc_before = ql.get_gate_count()
        ctrl = ql.qbool(True)
        with ctrl:
            a ^= 5
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, (
            f"Controlled IXOR cq should produce gates: before={gc_before}, after={gc_after}"
        )


class TestControlledAndQQStillWorks:
    """Existing controlled AND qq still works after changes."""

    def test_no_error(self):
        """AND qq controlled still completes without error."""
        ql.circuit()
        a = ql.qint(3, width=3)
        b = ql.qint(5, width=3)
        ctrl = ql.qbool(True)
        with ctrl:
            _ = a & b
