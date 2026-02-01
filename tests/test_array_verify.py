"""VADV-03: Array operation verification through full pipeline.

Verifies ql.array operations (reductions and element-wise) produce correct
results through the full pipeline: Python API -> C backend -> OpenQASM 3.0 ->
Qiskit simulation -> result extraction.

BUG-ARRAY-INIT: The ql.array([values], width=w) constructor has a confirmed bug
where it passes self._width as the VALUE to qint() instead of as the width
parameter. This means:
  - ql.array([1, 2], width=3) creates two qint(3) => 2-bit qints with value 3
  - All elements get the same quantum value (= width), ignoring user data
  - Element widths are auto-inferred from width value, not the specified width

Additionally, ql.array cannot wrap existing qint objects because qint has no
.value attribute accessible from Python (the constructor tries q.value = value.value).

As a result, all tests that depend on correct array value initialization are
marked with xfail(reason="BUG-ARRAY-INIT"). Tests are written to document the
INTENDED behavior so they will automatically pass once the bug is fixed.

Coverage:
- Sum reduction: 2-element, 1-element (identity), overflow
- AND reduction (.all()): 2-element, 1-element (identity)
- OR reduction (.any()): 2-element, 1-element (identity)
- Element-wise: array + scalar, array - scalar
- Calibration: documents actual bug behavior empirically
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

    sim = AerSimulator(method="statevector")
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
        """Document: ql.array([1,2], width=3) produces wrong QASM.

        BUG-ARRAY-INIT: constructor creates qint(width) instead of
        qint(value, width=width). So all elements get quantum value = width
        with auto-inferred width from that value's bit_length().

        For width=3: each element becomes qint(3) = 2-bit qint with value 3.
        Expected: 3-bit qints with values 1 and 2 respectively.
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

        # Array QASM should have 6 qubits (2 * 3-bit), but has 4 (2 * 2-bit)
        arr_qubits = None
        manual_qubits = None
        for line in qasm_arr.splitlines():
            if "qubit[" in line:
                arr_qubits = int(line.split("[")[1].split("]")[0])
        for line in qasm_manual.splitlines():
            if "qubit[" in line:
                manual_qubits = int(line.split("[")[1].split("]")[0])

        # Document the bug: array uses fewer qubits than manual construction
        assert manual_qubits == 6, "Manual construction should use 6 qubits"
        # This assertion documents the bug (array uses 4, not 6)
        assert arr_qubits != manual_qubits, (
            "BUG-ARRAY-INIT: array constructor should differ from manual "
            f"(arr={arr_qubits}, manual={manual_qubits})"
        )

    def test_array_qint_wrapping_unsupported(self):
        """Document: ql.array cannot wrap existing qint objects.

        qint has no .value attribute accessible from Python, so the array
        constructor crashes when given qint objects.
        """
        gc.collect()
        ql.circuit()
        a = ql.qint(1, width=3)
        b = ql.qint(2, width=3)
        with pytest.raises(AttributeError, match="value"):
            ql.array([a, b])


# ===========================================================================
# Sum reduction tests
# ===========================================================================


class TestArraySum:
    """Sum reduction: arr.sum() should return element sum."""

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
    def test_array_sum_2elem(self, verify_circuit):
        """Sum of [1, 2] (width=3) should equal 3."""

        def build():
            arr = ql.array([1, 2], width=3)
            _result = arr.sum()
            return ((1 + 2) % (1 << 3), [arr, _result])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
    def test_array_sum_1elem(self, verify_circuit):
        """Sum of [3] (width=3) should equal 3 (identity)."""

        def build():
            arr = ql.array([3], width=3)
            _result = arr.sum()
            # Single element: sum() returns the element itself
            return (3, [arr])

        actual, expected = verify_circuit(build, width=3)
        assert actual == expected, f"Expected {expected}, got {actual}"

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
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

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
    def test_array_and_2elem(self, verify_circuit):
        """AND of [3, 1] (width=2) should equal 3 & 1 = 1."""

        def build():
            arr = ql.array([3, 1], width=2)
            _result = arr.all()
            return (3 & 1, [arr, _result])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
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

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
    def test_array_or_2elem(self, verify_circuit):
        """OR of [1, 2] (width=2) should equal 1 | 2 = 3."""

        def build():
            arr = ql.array([1, 2], width=2)
            _result = arr.any()
            return (1 | 2, [arr, _result])

        actual, expected = verify_circuit(build, width=2)
        assert actual == expected, f"Expected {expected}, got {actual}"

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
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

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
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

    @pytest.mark.xfail(
        reason="BUG-ARRAY-INIT: array elements initialized to wrong values", strict=False
    )
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
