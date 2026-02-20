"""VADV-03: Array operation verification through full pipeline.

Verifies ql.array operations (reductions and element-wise) produce correct
results through the full pipeline: Python API -> C backend -> OpenQASM 3.0 ->
Qiskit simulation -> result extraction.

BUG-ARRAY-INIT was fixed in v1.6 Phase 34. The constructor now correctly
passes value and width parameters to qint():
  - ql.array([1, 2], width=3) creates two 3-bit qints with values 1 and 2
  - Element widths match the specified width parameter
  - All array operations produce correct quantum circuits

Coverage:
- Sum reduction: 2-element, 1-element (identity), overflow
- AND reduction (.all()): 2-element, 1-element (identity)
- OR reduction (.any()): 2-element, 1-element (identity)
- Element-wise: array + scalar, array - scalar
- Calibration: verifies constructor fix works correctly
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

# Suppress cosmetic warnings for values >= 2^(width-1) in unsigned interpretation
warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# Helper: run pipeline and return (actual_int, full_bitstring)
# ---------------------------------------------------------------------------


def _run_pipeline(circuit_builder, result_width):
    """Run full verification pipeline and extract result.

    Args:
        circuit_builder: Callable returning (expected, keepalive_refs).
        result_width: Bit width of result register (leftmost in bitstring).

    Returns:
        (actual, expected) tuple.
    """
    gc.collect()
    ql.circuit()

    result = circuit_builder()
    if isinstance(result, tuple):
        expected, _keepalive = result
    else:
        expected = result
        _keepalive = None

    qasm_str = ql.to_openqasm()
    _keepalive = None  # safe to release after export

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    actual = int(bitstring[:result_width], 2)
    return actual, expected


# ===========================================================================
# Calibration: document BUG-ARRAY-INIT empirically
# ===========================================================================


class TestArrayCalibration:
    """Calibration tests documenting BUG-ARRAY-INIT behavior."""

    def test_array_calibration_constructor(self):
        """Verify: ql.array([1,2], width=3) produces correct QASM.

        BUG-ARRAY-INIT was fixed in v1.6 Phase 34. Now constructor correctly
        creates qint(value, width=width) instead of qint(width).

        Both array and manual construction should use 6 qubits (2 * 3-bit).
        """
        gc.collect()
        ql.circuit()
        _arr = ql.array([1, 2], width=3)
        qasm_arr = ql.to_openqasm()

        gc.collect()
        ql.circuit()
        a = ql.qint(1, width=3)
        b = ql.qint(2, width=3)
        _keepalive = [a, b]
        qasm_manual = ql.to_openqasm()
        _keepalive = None

        # Both should have 6 qubits (2 * 3-bit)
        arr_qubits = None
        manual_qubits = None
        for line in qasm_arr.splitlines():
            if "qubit[" in line:
                arr_qubits = int(line.split("[")[1].split("]")[0])
        for line in qasm_manual.splitlines():
            if "qubit[" in line:
                manual_qubits = int(line.split("[")[1].split("]")[0])

        # Verify the fix: array now uses same qubits as manual construction
        assert manual_qubits == 6, "Manual construction should use 6 qubits"
        assert arr_qubits == manual_qubits, (
            "Array constructor should match manual construction "
            f"(arr={arr_qubits}, manual={manual_qubits})"
        )

    def test_array_qint_wrapping_limitation(self):
        """Document: ql.array cannot wrap existing qint objects when width is not explicit.

        qint.value is a cdef attribute not accessible from Python, so the
        width inference code (lines 290-295) fails when trying to access v.value.

        This is a known limitation: wrapping qints only works if explicit width
        is provided to bypass the inference logic, but that path also tries to
        access v.value for validation. This is separate from BUG-ARRAY-INIT.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(1, width=3)
        b = ql.qint(2, width=3)
        # Fails due to .value access in width inference/validation
        with pytest.raises(AttributeError, match="value"):
            ql.array([a, b])


# ===========================================================================
# Sum reduction tests
# ===========================================================================


class TestArraySum:
    """Sum reduction: arr.sum() should return element sum."""

    def test_array_sum_2elem(self, verify_circuit):
        """Sum of [1, 2] (width=3) should equal 3."""

        def build():
            arr = ql.array([1, 2], width=3)
            _result = arr.sum()
            return ((1 + 2) % (1 << 3), [arr, _result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_array_sum_1elem(self, verify_circuit):
        """Sum of [3] (width=3) should equal 3 (identity)."""

        def build():
            arr = ql.array([3], width=3)
            _result = arr.sum()
            # Single element: sum() returns the element itself
            return (3, [arr])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_array_sum_overflow(self, verify_circuit):
        """Sum of [3, 3] (width=2) should equal (3+3)%4 = 2 (overflow wrapping)."""

        def build():
            arr = ql.array([3, 3], width=2)
            _result = arr.sum()
            return ((3 + 3) % (1 << 2), [arr, _result])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ===========================================================================
# AND reduction tests
# ===========================================================================


class TestArrayAND:
    """AND reduction: arr.all() should return bitwise AND of all elements."""

    def test_array_and_2elem(self, verify_circuit):
        """AND of [3, 1] (width=2) should equal 3 & 1 = 1."""

        def build():
            arr = ql.array([3, 1], width=2)
            _result = arr.all()
            return (3 & 1, [arr, _result])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_array_and_1elem(self, verify_circuit):
        """AND of [3] (width=2) should equal 3 (identity)."""

        def build():
            arr = ql.array([3], width=2)
            _result = arr.all()
            # Single element: all() returns the element itself
            return (3, [arr])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ===========================================================================
# OR reduction tests
# ===========================================================================


class TestArrayOR:
    """OR reduction: arr.any() should return bitwise OR of all elements."""

    def test_array_or_2elem(self, verify_circuit):
        """OR of [1, 2] (width=2) should equal 1 | 2 = 3."""

        def build():
            arr = ql.array([1, 2], width=2)
            _result = arr.any()
            return (1 | 2, [arr, _result])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_array_or_1elem(self, verify_circuit):
        """OR of [2] (width=2) should equal 2 (identity)."""

        def build():
            arr = ql.array([2], width=2)
            _result = arr.any()
            # Single element: any() returns the element itself
            return (2, [arr])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ===========================================================================
# Element-wise operation tests
# ===========================================================================


class TestArrayElementwise:
    """Element-wise operations: array +/- scalar."""

    def test_array_add_scalar(self, verify_circuit):
        """[1, 2] + 1 should give [2, 3]. Last element = 3."""

        def build():
            arr = ql.array([1, 2], width=3)
            result_arr = arr + 1
            # Result array's last element is the last-allocated register
            # so it should be at bitstring[:3]
            return (3, [arr, result_arr])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_array_sub_scalar(self, verify_circuit):
        """[3, 2] - 1 should give [2, 1]. Last element = 1."""

        def build():
            arr = ql.array([3, 2], width=3)
            result_arr = arr - 1
            return (1, [arr, result_arr])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"


# ===========================================================================
# Sanity: manual qint operations (no array bug) to confirm pipeline works
# ===========================================================================


class TestManualSanity:
    """Sanity checks using manual qint construction (no BUG-ARRAY-INIT).

    These tests confirm the underlying operations (addition, AND, OR) work
    correctly through the pipeline when array constructor bug is bypassed.
    """

    def test_manual_sum(self, verify_circuit):
        """Manual qint(1,w=3) + qint(2,w=3) = 3 through pipeline."""

        def build():
            a = ql.qint(1, width=3)
            b = ql.qint(2, width=3)
            result = a + b
            return (3, [a, b, result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_manual_and(self, verify_circuit):
        """Manual qint(3,w=2) & qint(1,w=2) = 1 through pipeline."""

        def build():
            a = ql.qint(3, width=2)
            b = ql.qint(1, width=2)
            result = a & b
            return (1, [a, b, result])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_manual_or(self, verify_circuit):
        """Manual qint(1,w=2) | qint(2,w=2) = 3 through pipeline."""

        def build():
            a = ql.qint(1, width=2)
            b = ql.qint(2, width=2)
            result = a | b
            return (3, [a, b, result])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"
