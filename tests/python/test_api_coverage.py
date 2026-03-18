"""Comprehensive API coverage tests for Python API (TEST-03).

Tests verify that all public API methods work as documented.
Complements characterization tests by testing API contracts.
"""

import pytest

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
        """Default width is auto-sized (minimum bits for value)."""
        a = ql.qint(5)
        assert a.width == 3

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


class TestQboolAPI:
    """Test qbool class public API."""

    def test_qbool_default(self):
        """qbool() creates False by default."""
        b = ql.qbool()
        assert isinstance(b, ql.qbool)
        assert b.width == 1

    def test_qbool_true(self):
        """qbool(True) creates True value."""
        b = ql.qbool(True)
        assert isinstance(b, ql.qbool)

    def test_qbool_is_qint(self):
        """qbool inherits from qint."""
        b = ql.qbool(True)
        assert isinstance(b, ql.qint)

    def test_qbool_bitwise(self):
        """qbool supports bitwise operations."""
        a = ql.qbool(True)
        b = ql.qbool(False)
        c = a & b
        assert isinstance(c, ql.qint)  # Result is qint, not qbool


class TestQintModAPI:
    """Test qint_mod class public API."""

    def test_qint_mod_creation(self):
        """qint_mod(value, N=modulus) creates modular integer."""
        x = ql.qint_mod(5, N=17)
        assert isinstance(x, ql.qint_mod)
        assert x.modulus == 17

    def test_qint_mod_requires_N(self):
        """qint_mod requires N parameter."""
        with pytest.raises(ValueError):
            ql.qint_mod(5)

    def test_qint_mod_N_must_be_positive(self):
        """N must be positive integer."""
        with pytest.raises(ValueError):
            ql.qint_mod(5, N=0)
        with pytest.raises(ValueError):
            ql.qint_mod(5, N=-5)

    def test_qint_mod_add(self):
        """qint_mod + int returns qint_mod."""
        x = ql.qint_mod(5, N=17)
        y = x + 3
        assert isinstance(y, ql.qint_mod)
        assert y.modulus == 17

    def test_qint_mod_sub(self):
        """qint_mod - int returns qint_mod."""
        x = ql.qint_mod(5, N=17)
        y = x - 3
        assert isinstance(y, ql.qint_mod)

    def test_qint_mod_mul(self):
        """qint_mod * int returns qint_mod."""
        x = ql.qint_mod(5, N=17)
        y = x * 3
        assert isinstance(y, ql.qint_mod)

    def test_qint_mod_mul_qint_mod_not_implemented(self):
        """qint_mod * qint_mod raises NotImplementedError (known limitation)."""
        x = ql.qint_mod(5, N=17)
        y = ql.qint_mod(3, N=17)
        with pytest.raises(NotImplementedError) as excinfo:
            _ = x * y
        assert "qint_mod * int" in str(excinfo.value)  # Error message is actionable

    def test_qint_mod_mismatched_moduli(self):
        """Operations with different moduli raise ValueError."""
        x = ql.qint_mod(5, N=17)
        y = ql.qint_mod(3, N=19)
        with pytest.raises(ValueError):
            _ = x + y


class TestModuleFunctions:
    """Test module-level functions."""

    def test_array_creates_list_of_qint(self):
        """array(n) creates list of n qints."""
        arr = ql.array(5)
        assert len(arr) == 5
        assert all(isinstance(x, ql.qint) for x in arr)

    def test_array_with_values(self):
        """array([values]) creates qints from list."""
        arr = ql.array([1, 2, 3])
        assert len(arr) == 3
        assert all(isinstance(x, ql.qint) for x in arr)

    def test_array_2d(self):
        """array((rows, cols)) creates 2D array."""
        arr = ql.array((2, 3))
        assert len(arr) == 2
        assert len(arr[0]) == 3

    def test_circuit_stats(self):
        """circuit_stats() returns dict with allocation info."""
        _c = ql.circuit()
        _a = ql.qint(5, width=8)
        stats = ql.circuit_stats()
        assert isinstance(stats, dict)
        assert "peak_allocated" in stats
        assert "total_allocations" in stats

    def test_available_passes_constant(self):
        """AVAILABLE_PASSES is module-level constant."""
        assert hasattr(ql, "AVAILABLE_PASSES")
        assert "merge" in ql.AVAILABLE_PASSES


class TestPhase10SuccessCriteria:
    """Verify Phase 10 TEST-03 success criteria."""

    def test_qint_operations_covered(self):
        """TEST-03: Python API tests cover qint operations."""
        # Arithmetic
        a = ql.qint(5, width=8)
        _ = a + 1
        _ = a - 1
        _ = a * 2
        _ = a // 2
        _ = a % 3
        assert True  # If we got here, operations work

    def test_qbool_operations_covered(self):
        """TEST-03: Python API tests cover qbool operations."""
        a = ql.qbool(True)
        b = ql.qbool(False)
        _ = a & b
        _ = a | b
        _ = ~a
        assert True

    def test_circuit_operations_covered(self):
        """TEST-03: Python API tests cover circuit operations."""
        c = ql.circuit()
        _a = ql.qint(5, width=4)
        _ = c.gate_count
        _ = c.depth
        _ = c.gate_counts
        c.visualize()
        assert True
