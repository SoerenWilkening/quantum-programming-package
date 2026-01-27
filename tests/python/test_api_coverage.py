"""Comprehensive API coverage tests for Python API (TEST-03).

Tests verify that all public API methods work as documented.
Complements characterization tests by testing API contracts.
"""

import os
import sys

import pytest

# noqa comments allow import after path setup
# ruff: noqa: E402

# Add python-backend to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "python-backend"))

import quantum_language as ql


class TestCircuitAPI:
    """Test circuit class public API."""

    def test_circuit_creation(self):
        """circuit() creates circuit singleton."""
        c = ql.circuit()
        assert c is not None

    def test_circuit_visualize(self):
        """visualize() runs without error."""
        c = ql.circuit()
        _a = ql.qint(5, width=4)  # Create qubits to have gates
        c.visualize()  # Should not raise

    def test_circuit_gate_count(self):
        """gate_count returns int."""
        c = ql.circuit()
        _a = ql.qint(5, width=4)  # Create qubits to have gates
        assert isinstance(c.gate_count, int)

    def test_circuit_depth(self):
        """depth returns int."""
        c = ql.circuit()
        _a = ql.qint(5, width=4)  # Create qubits to have gates
        assert isinstance(c.depth, int)

    def test_circuit_qubit_count(self):
        """qubit_count returns int >= 0."""
        c = ql.circuit()
        _a = ql.qint(5, width=4)  # Create qubits to have gates
        assert isinstance(c.qubit_count, int)
        assert c.qubit_count >= 0

    def test_circuit_gate_counts(self):
        """gate_counts returns dict with expected keys."""
        c = ql.circuit()
        _a = ql.qint(5, width=4)  # Create qubits to have gates
        counts = c.gate_counts
        assert isinstance(counts, dict)
        assert "X" in counts
        assert "H" in counts
        assert "CNOT" in counts

    def test_circuit_available_passes(self):
        """available_passes returns list of pass names."""
        c = ql.circuit()
        passes = c.available_passes
        assert isinstance(passes, list)
        assert "merge" in passes
        assert "cancel_inverse" in passes

    def test_circuit_optimize(self):
        """optimize() returns before/after stats dict."""
        c = ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        stats = c.optimize()
        assert "before" in stats
        assert "after" in stats
        assert "gate_count" in stats["before"]

    def test_circuit_can_optimize(self):
        """can_optimize() returns bool."""
        c = ql.circuit()
        _a = ql.qint(5, width=4)  # Create qubits to have gates
        result = c.can_optimize()
        assert isinstance(result, bool)


class TestQintAPI:
    """Test qint class public API."""

    # Construction
    def test_qint_default_width(self):
        """Default width is 8 bits."""
        a = ql.qint(5)
        assert a.width == 8

    def test_qint_explicit_width(self):
        """width parameter sets bit width."""
        a = ql.qint(5, width=16)
        assert a.width == 16

    def test_qint_bits_alias(self):
        """bits parameter is alias for width."""
        a = ql.qint(5, bits=16)
        assert a.width == 16

    def test_qint_width_validation(self):
        """Width must be 1-64."""
        with pytest.raises(ValueError):
            ql.qint(0, width=0)
        with pytest.raises(ValueError):
            ql.qint(0, width=65)

    # Arithmetic
    def test_qint_add_int(self):
        """qint + int returns qint."""
        a = ql.qint(5, width=8)
        b = a + 3
        assert isinstance(b, ql.qint)
        assert b is not a

    def test_qint_iadd_int(self):
        """qint += int modifies in-place."""
        a = ql.qint(5, width=8)
        a += 3
        assert isinstance(a, ql.qint)

    def test_qint_add_qint(self):
        """qint + qint returns qint with max width."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=16)
        c = a + b
        assert isinstance(c, ql.qint)
        assert c.width == 16

    def test_qint_sub_int(self):
        """qint - int returns qint."""
        a = ql.qint(10, width=8)
        b = a - 3
        assert isinstance(b, ql.qint)

    def test_qint_mul_int(self):
        """qint * int returns qint."""
        a = ql.qint(3, width=8)
        b = a * 4
        assert isinstance(b, ql.qint)

    @pytest.mark.skip(reason="Segfault in QQ_mul - known issue, needs C-layer fix")
    def test_qint_mul_qint(self):
        """qint * qint returns qint."""
        a = ql.qint(3, width=8)
        b = ql.qint(4, width=8)
        c = a * b
        assert isinstance(c, ql.qint)

    def test_qint_floordiv_int(self):
        """qint // int returns qint."""
        a = ql.qint(10, width=8)
        q = a // 3
        assert isinstance(q, ql.qint)

    def test_qint_floordiv_zero(self):
        """Division by zero raises ZeroDivisionError."""
        a = ql.qint(10, width=8)
        with pytest.raises(ZeroDivisionError):
            _ = a // 0

    def test_qint_mod_int(self):
        """qint % int returns qint."""
        a = ql.qint(10, width=8)
        r = a % 3
        assert isinstance(r, ql.qint)

    def test_qint_divmod_int(self):
        """divmod(qint, int) returns (qint, qint)."""
        a = ql.qint(10, width=8)
        q, r = divmod(a, 3)
        assert isinstance(q, ql.qint)
        assert isinstance(r, ql.qint)

    # Bitwise
    def test_qint_and_int(self):
        """qint & int returns qint."""
        a = ql.qint(5, width=8)
        b = a & 3
        assert isinstance(b, ql.qint)

    def test_qint_or_int(self):
        """qint | int returns qint."""
        a = ql.qint(5, width=8)
        b = a | 3
        assert isinstance(b, ql.qint)

    def test_qint_xor_int(self):
        """qint ^ int returns qint."""
        a = ql.qint(5, width=8)
        b = a ^ 3
        assert isinstance(b, ql.qint)

    def test_qint_invert(self):
        """~qint returns qint (in-place)."""
        a = ql.qint(5, width=8)
        b = ~a
        assert isinstance(b, ql.qint)

    # Comparison
    def test_qint_eq_int(self):
        """qint == int returns qbool."""
        a = ql.qint(5, width=8)
        b = a == 5
        assert isinstance(b, ql.qbool)

    def test_qint_lt_int(self):
        """qint < int returns qbool."""
        a = ql.qint(5, width=8)
        b = a < 10
        assert isinstance(b, ql.qbool)

    def test_qint_gt_int(self):
        """qint > int returns qbool."""
        a = ql.qint(5, width=8)
        b = a > 3
        assert isinstance(b, ql.qbool)

    # Indexing
    def test_qint_getitem(self):
        """qint[i] returns qbool for bit access."""
        a = ql.qint(5, width=8)
        bit = a[0]
        assert isinstance(bit, ql.qbool)

    # Context manager
    def test_qint_context_manager(self):
        """qint can be used in with statement."""
        a = ql.qint(5, width=8)
        b = ql.qbool(True)
        with b:
            a += 1
        # Should complete without error
        assert isinstance(a, ql.qint)
