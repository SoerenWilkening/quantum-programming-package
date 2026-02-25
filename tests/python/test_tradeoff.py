"""Phase 93: Depth/Ancilla Tradeoff Tests.

Tests for the ql.option('tradeoff', ...) API covering:
- TRD-01: Option API (get/set, validation, set-once enforcement, circuit reset)
- TRD-02: Dispatch modes (auto threshold, min_depth CLA, min_qubits RCA)
- TRD-03: Modular arithmetic always uses RCA regardless of tradeoff
"""

import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

# Suppress value-exceeds-width warnings
warnings.filterwarnings("ignore", message="Value .* exceeds")

# Max qubits for simulation per project constraints
MAX_SIM_QUBITS = 17


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_num_qubits_from_qasm(qasm_str):
    """Extract qubit count from OpenQASM qubit[N] declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate QASM and extract result register value."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(method="statevector", max_parallel_threads=4)
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Qiskit bitstring: position i = qubit (N-1-i)
    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _simulate_addition(a_val, b_val, width, tradeoff="auto", invert=False):
    """Create circuit, perform addition/subtraction, return result via simulation."""
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("tradeoff", tradeoff)

    a = ql.qint(a_val, width=width)
    b = ql.qint(b_val, width=width)

    if invert:
        a -= b
    else:
        a += b

    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)

    if num_qubits > MAX_SIM_QUBITS:
        pytest.skip(f"Circuit requires {num_qubits} qubits (max {MAX_SIM_QUBITS})")

    # a is registered at qubit 0..width-1
    return _simulate_and_extract(qasm_str, num_qubits, 0, width)


def _get_circuit_qubit_count(a_val, b_val, width, tradeoff="auto"):
    """Get peak allocated qubit count for an addition circuit."""
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("tradeoff", tradeoff)

    a = ql.qint(a_val, width=width)
    b = ql.qint(b_val, width=width)
    a += b

    stats = ql.circuit_stats()
    return stats["peak_allocated"]


def _get_circuit_depth(a_val, b_val, width, tradeoff="auto"):
    """Get circuit depth for an addition."""
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("tradeoff", tradeoff)

    a = ql.qint(a_val, width=width)
    b = ql.qint(b_val, width=width)
    a += b

    stats = ql.circuit_stats()
    return stats.get("depth", 0)


# ============================================================================
# TRD-01: Tradeoff Option API Tests
# ============================================================================


class TestTradeoffOption:
    """Test basic option get/set behavior."""

    def test_default_is_auto(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        assert ql.option("tradeoff") == "auto"

    def test_set_min_depth(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_depth")
        assert ql.option("tradeoff") == "min_depth"

    def test_set_min_qubits(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_qubits")
        assert ql.option("tradeoff") == "min_qubits"

    def test_set_auto_explicit(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_depth")
        ql.option("tradeoff", "auto")
        assert ql.option("tradeoff") == "auto"

    def test_invalid_value_raises(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        with pytest.raises(ValueError, match="Invalid tradeoff value"):
            ql.option("tradeoff", "fast")

    def test_invalid_type_raises(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        with pytest.raises(ValueError, match="Invalid tradeoff value"):
            ql.option("tradeoff", True)

    def test_reset_on_new_circuit(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_depth")
        assert ql.option("tradeoff") == "min_depth"
        # Create new circuit
        ql.circuit()
        ql.option("fault_tolerant", True)
        assert ql.option("tradeoff") == "auto"


class TestTradeoffFrozen:
    """Test set-once enforcement after arithmetic operations."""

    def test_frozen_after_addition(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_depth")
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        a += b
        with pytest.raises(RuntimeError, match="Cannot change tradeoff"):
            ql.option("tradeoff", "min_qubits")

    def test_frozen_after_subtraction(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "auto")
        a = ql.qint(5, width=4)
        b = ql.qint(2, width=4)
        a -= b
        with pytest.raises(RuntimeError, match="Cannot change tradeoff"):
            ql.option("tradeoff", "min_depth")

    def test_not_frozen_before_ops(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_depth")
        ql.option("tradeoff", "min_qubits")
        # No error -- no arithmetic ops performed yet
        assert ql.option("tradeoff") == "min_qubits"

    def test_frozen_reset_on_new_circuit(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_depth")
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        a += b
        # Frozen now
        with pytest.raises(RuntimeError):
            ql.option("tradeoff", "auto")
        # New circuit resets frozen state
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("tradeoff", "min_qubits")  # Should not raise
        assert ql.option("tradeoff") == "min_qubits"


# ============================================================================
# TRD-02: Auto Mode Tests
# ============================================================================


class TestAutoMode:
    """Test auto mode CLA/CDKM dispatch based on width threshold."""

    def test_auto_uses_cla_for_large_width(self):
        """Auto mode should use CLA (more qubits) for width >= threshold (4)."""
        auto_qubits = _get_circuit_qubit_count(3, 5, 8, tradeoff="auto")
        min_qubits_qubits = _get_circuit_qubit_count(3, 5, 8, tradeoff="min_qubits")
        # CLA uses more ancilla qubits than CDKM
        assert auto_qubits > min_qubits_qubits, (
            f"Auto mode at width=8 should use CLA (more qubits), "
            f"got auto={auto_qubits}, min_qubits={min_qubits_qubits}"
        )

    def test_auto_uses_cdkm_for_small_width(self):
        """Auto mode should use CDKM for width < threshold (3 < 4)."""
        auto_qubits = _get_circuit_qubit_count(1, 2, 3, tradeoff="auto")
        min_qubits_qubits = _get_circuit_qubit_count(1, 2, 3, tradeoff="min_qubits")
        # At small widths, auto mode should behave like min_qubits (both use CDKM)
        assert auto_qubits == min_qubits_qubits, (
            f"Auto mode at width=3 should use CDKM (same qubits as min_qubits), "
            f"got auto={auto_qubits}, min_qubits={min_qubits_qubits}"
        )

    def test_auto_correctness(self):
        """Verify a + b produces correct results in auto mode for various widths."""
        for width in range(2, 7):
            mask = (1 << width) - 1
            test_pairs = [(1, 1), (0, 1), (mask, 1)]
            for a_val, b_val in test_pairs:
                expected = (a_val + b_val) & mask
                result = _simulate_addition(a_val, b_val, width, tradeoff="auto")
                assert result == expected, (
                    f"auto mode: {a_val} + {b_val} (width={width}) = {result}, expected {expected}"
                )


class TestMinDepthMode:
    """Test min_depth mode uses CLA for all widths >= 2."""

    def test_min_depth_uses_cla_at_small_width(self):
        """min_depth should use CLA even at width=3 (more qubits than min_qubits)."""
        min_depth_qubits = _get_circuit_qubit_count(1, 2, 3, tradeoff="min_depth")
        min_qubits_qubits = _get_circuit_qubit_count(1, 2, 3, tradeoff="min_qubits")
        # CLA at width 3 uses more qubits than CDKM
        assert min_depth_qubits > min_qubits_qubits, (
            f"min_depth at width=3 should use CLA (more qubits), "
            f"got min_depth={min_depth_qubits}, min_qubits={min_qubits_qubits}"
        )

    def test_min_depth_addition_correct(self):
        """Verify a + b produces correct results in min_depth mode."""
        for width in range(2, 7):
            mask = (1 << width) - 1
            test_pairs = [(1, 1), (0, 1), (mask, 1), (2, 3)]
            for a_val, b_val in test_pairs:
                a_val = a_val & mask
                b_val = b_val & mask
                expected = (a_val + b_val) & mask
                result = _simulate_addition(a_val, b_val, width, tradeoff="min_depth")
                assert result == expected, (
                    f"min_depth mode: {a_val} + {b_val} (width={width}) = {result}, "
                    f"expected {expected}"
                )


class TestMinQubitsMode:
    """Test min_qubits mode forces CDKM/RCA for all widths."""

    def test_min_qubits_forces_rca(self):
        """min_qubits at width=8 should use minimal qubits (CDKM)."""
        min_qubits_qubits = _get_circuit_qubit_count(3, 5, 8, tradeoff="min_qubits")
        min_depth_qubits = _get_circuit_qubit_count(3, 5, 8, tradeoff="min_depth")
        # CDKM uses fewer qubits than CLA
        assert min_qubits_qubits < min_depth_qubits, (
            f"min_qubits should use fewer qubits than min_depth at width=8, "
            f"got min_qubits={min_qubits_qubits}, min_depth={min_depth_qubits}"
        )

    def test_min_qubits_addition_correct(self):
        """Verify a + b produces correct results in min_qubits mode."""
        for width in range(2, 7):
            mask = (1 << width) - 1
            test_pairs = [(1, 1), (0, 1), (mask, 1)]
            for a_val, b_val in test_pairs:
                expected = (a_val + b_val) & mask
                result = _simulate_addition(a_val, b_val, width, tradeoff="min_qubits")
                assert result == expected, (
                    f"min_qubits mode: {a_val} + {b_val} (width={width}) = {result}, "
                    f"expected {expected}"
                )

    def test_min_qubits_subtraction_correct(self):
        """Verify a - b produces correct results in min_qubits mode."""
        for width in range(2, 7):
            mask = (1 << width) - 1
            test_pairs = [(3, 1), (5, 2), (0, 1)]
            for a_val, b_val in test_pairs:
                a_val = a_val & mask
                b_val = b_val & mask
                expected = (a_val - b_val) & mask
                result = _simulate_addition(a_val, b_val, width, tradeoff="min_qubits", invert=True)
                assert result == expected, (
                    f"min_qubits mode: {a_val} - {b_val} (width={width}) = {result}, "
                    f"expected {expected}"
                )


# ============================================================================
# TRD-03: Modular Arithmetic RCA Forcing Tests
# ============================================================================


class TestModularForceRCA:
    """Test that modular arithmetic always uses RCA regardless of tradeoff."""

    def test_modular_add_same_result_all_modes(self):
        """All tradeoff modes should produce identical QASM for modular ops."""
        qasm_outputs = {}
        for mode in ("auto", "min_depth", "min_qubits"):
            ql.circuit()
            ql.option("fault_tolerant", True)
            ql.option("tradeoff", mode)
            from quantum_language import qint_mod

            a = qint_mod(2, N=5, width=3)
            b = qint_mod(3, N=5, width=3)
            a += b
            qasm_outputs[mode] = ql.to_openqasm()

        # All three should produce exactly the same QASM
        assert qasm_outputs["auto"] == qasm_outputs["min_depth"], (
            "Modular arithmetic QASM differs between auto and min_depth"
        )
        assert qasm_outputs["auto"] == qasm_outputs["min_qubits"], (
            "Modular arithmetic QASM differs between auto and min_qubits"
        )

    def test_modular_add_qubit_count_same_all_modes(self):
        """All tradeoff modes should use same qubit count for modular ops (no CLA)."""
        qubit_counts = {}
        for mode in ("auto", "min_depth", "min_qubits"):
            ql.circuit()
            ql.option("fault_tolerant", True)
            ql.option("tradeoff", mode)
            from quantum_language import qint_mod

            a = qint_mod(2, N=5, width=3)
            b = qint_mod(3, N=5, width=3)
            a += b
            stats = ql.circuit_stats()
            qubit_counts[mode] = stats["peak_allocated"]

        # All three should use exactly the same peak allocation (no CLA for modular)
        assert qubit_counts["auto"] == qubit_counts["min_depth"], (
            f"Modular qubit count differs: auto={qubit_counts['auto']}, "
            f"min_depth={qubit_counts['min_depth']}"
        )
        assert qubit_counts["auto"] == qubit_counts["min_qubits"], (
            f"Modular qubit count differs: auto={qubit_counts['auto']}, "
            f"min_qubits={qubit_counts['min_qubits']}"
        )
