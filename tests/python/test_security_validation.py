"""Phase 84: Security Validation Tests

Tests for SEC-01 (NULL pointer rejection) and SEC-02 (buffer bounds checking).
Verifies that invalid circuit state raises clear Python exceptions instead of
causing segfaults, and that qubit_array buffer overflow is detected.
"""

import pytest

from quantum_language import circuit, qint
from quantum_language._core import (
    _set_circuit_initialized,
    circuit_stats,
    get_current_layer,
    option,
    validate_circuit,
    validate_qubit_slots,
)


class TestNullCircuitPointerRejection:
    """SEC-01: Passing NULL/uninitialized circuit pointer raises ValueError."""

    def setup_method(self):
        """Ensure circuit is initialized before each test."""
        self.c = circuit()

    def test_validate_circuit_passes_when_initialized(self):
        """validate_circuit() does not raise when circuit is properly initialized."""
        validate_circuit()  # Should not raise

    def test_validate_circuit_raises_when_uninitialized(self):
        """validate_circuit() raises ValueError with [Validation] prefix when circuit is NULL."""
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                validate_circuit()
        finally:
            # Restore circuit state so teardown doesn't segfault
            _set_circuit_initialized(True)
            circuit()

    def test_gate_count_raises_when_uninitialized(self):
        """circuit.gate_count raises ValueError when circuit pointer is NULL."""
        c = circuit()
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                _ = c.gate_count
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_depth_raises_when_uninitialized(self):
        """circuit.depth raises ValueError when circuit pointer is NULL."""
        c = circuit()
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                _ = c.depth
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_qubit_count_raises_when_uninitialized(self):
        """circuit.qubit_count raises ValueError when circuit pointer is NULL."""
        c = circuit()
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                _ = c.qubit_count
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_gate_counts_raises_when_uninitialized(self):
        """circuit.gate_counts raises ValueError when circuit pointer is NULL."""
        c = circuit()
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                _ = c.gate_counts
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_draw_data_raises_when_uninitialized(self):
        """circuit.draw_data() raises ValueError when circuit pointer is NULL."""
        c = circuit()
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                c.draw_data()
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_can_optimize_raises_when_uninitialized(self):
        """circuit.can_optimize() raises ValueError when circuit pointer is NULL."""
        c = circuit()
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                c.can_optimize()
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_circuit_stats_raises_when_uninitialized(self):
        """circuit_stats() raises ValueError when circuit pointer is NULL."""
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                circuit_stats()
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_get_current_layer_raises_when_uninitialized(self):
        """get_current_layer() raises ValueError when circuit pointer is NULL."""
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                get_current_layer()
        finally:
            _set_circuit_initialized(True)
            circuit()

    def test_option_fault_tolerant_raises_when_uninitialized(self):
        """option('fault_tolerant') raises ValueError when circuit pointer is NULL."""
        _set_circuit_initialized(False)
        try:
            with pytest.raises(ValueError, match=r"\[Validation\]"):
                option("fault_tolerant")
        finally:
            _set_circuit_initialized(True)
            circuit()


class TestBufferOverflowRejection:
    """SEC-02: Buffer overflow attempt raises OverflowError."""

    def setup_method(self):
        """Ensure circuit is initialized before each test."""
        self.c = circuit()

    def test_validate_qubit_slots_at_limit(self):
        """validate_qubit_slots(384) does not raise (exact limit)."""
        validate_qubit_slots(384, "test_func")  # Should not raise

    def test_validate_qubit_slots_below_limit(self):
        """validate_qubit_slots(100) does not raise (well below limit)."""
        validate_qubit_slots(100, "test_func")  # Should not raise

    def test_validate_qubit_slots_zero(self):
        """validate_qubit_slots(0) does not raise."""
        validate_qubit_slots(0, "test_func")  # Should not raise

    def test_validate_qubit_slots_exceeds_limit(self):
        """validate_qubit_slots(385) raises OverflowError."""
        with pytest.raises(OverflowError, match="slot count exceeded, max 384"):
            validate_qubit_slots(385, "test_func")

    def test_validate_qubit_slots_large_value(self):
        """validate_qubit_slots with very large value raises OverflowError."""
        with pytest.raises(OverflowError, match="slot count exceeded, max 384"):
            validate_qubit_slots(10000, "test_func")

    def test_validate_qubit_slots_error_includes_function_name(self):
        """OverflowError message includes the function name."""
        with pytest.raises(OverflowError, match="my_operation"):
            validate_qubit_slots(500, "my_operation")


class TestNormalOperationsStillWork:
    """Verify that validation does not break normal operations."""

    def setup_method(self):
        """Ensure circuit is initialized before each test."""
        self.c = circuit()

    def test_circuit_properties_work(self):
        """Circuit properties return valid results on initialized circuits."""
        c = circuit()
        assert isinstance(c.gate_count, int)
        assert isinstance(c.depth, int)
        assert isinstance(c.qubit_count, int)
        assert isinstance(c.gate_counts, dict)

    def test_arithmetic_addition_works(self):
        """Quantum addition still works correctly after adding validation."""
        circuit()  # Initialize circuit (side effect)
        a = qint(5, width=4)
        b = qint(3, width=4)
        result = a + b
        assert result.width == 4

    def test_arithmetic_subtraction_works(self):
        """Quantum subtraction still works correctly after adding validation."""
        circuit()  # Initialize circuit (side effect)
        a = qint(5, width=4)
        b = qint(3, width=4)
        result = a - b
        assert result.width == 4

    def test_arithmetic_multiplication_works(self):
        """Quantum multiplication still works correctly after adding validation."""
        circuit()  # Initialize circuit (side effect)
        a = qint(3, width=4)
        result = a * 2
        assert result.width == 4

    def test_bitwise_and_works(self):
        """Quantum AND still works correctly after adding validation."""
        circuit()  # Initialize circuit (side effect)
        a = qint(0b1101, width=4)
        b = qint(0b1011, width=4)
        result = a & b
        assert result.width == 4

    def test_bitwise_or_works(self):
        """Quantum OR still works correctly after adding validation."""
        circuit()  # Initialize circuit (side effect)
        a = qint(0b1100, width=4)
        b = qint(0b0011, width=4)
        result = a | b
        assert result.width == 4

    def test_bitwise_xor_works(self):
        """Quantum XOR still works correctly after adding validation."""
        circuit()  # Initialize circuit (side effect)
        a = qint(0b1100, width=4)
        b = qint(0b0110, width=4)
        result = a ^ b
        assert result.width == 4

    def test_comparison_eq_works(self):
        """Quantum equality comparison still works correctly."""
        circuit()  # Initialize circuit (side effect)
        a = qint(5, width=4)
        result = a == 5
        assert result.width == 1

    def test_circuit_stats_works(self):
        """circuit_stats returns valid data on initialized circuit."""
        circuit()  # Initialize circuit (side effect)
        qint(5, width=4)  # Allocate some qubits
        stats = circuit_stats()
        assert stats is not None
        assert "peak_allocated" in stats
        assert "current_in_use" in stats

    def test_get_current_layer_works(self):
        """get_current_layer returns valid layer count."""
        circuit()  # Initialize circuit (side effect)
        layer = get_current_layer()
        assert isinstance(layer, int)
        assert layer >= 0

    def test_option_get_set_works(self):
        """option() get/set works correctly."""
        circuit()  # Initialize circuit (side effect)
        # Test qubit_saving (Python-level)
        qs = option("qubit_saving")
        assert isinstance(qs, bool)
        # Test fault_tolerant (C-level)
        ft = option("fault_tolerant")
        assert isinstance(ft, bool)

    def test_draw_data_works(self):
        """draw_data() returns valid structure."""
        c = circuit()
        qint(5, width=4)  # Add some gates
        data = c.draw_data()
        assert "num_layers" in data
        assert "num_qubits" in data
        assert "gates" in data
