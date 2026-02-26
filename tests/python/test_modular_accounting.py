"""Qubit accounting tests for modular arithmetic operations.

Phase 96: Verifies that modular operations (qint_mod) do not leak ancilla
qubits by checking circuit_stats()['current_in_use'] before and after each
operation. This provides regression detection for ancilla leaks in the
Beauregard modular arithmetic pipeline.

Pattern: measure current_in_use before operation, measure after, assert
increase equals the result register width (no leaked ancillae).
"""

import gc
import warnings

import quantum_language as ql

# Suppress "Value X exceeds N-bit range" warnings from qint
warnings.filterwarnings("ignore", message="Value .* exceeds")


class TestModularQubitAccounting:
    """Verify modular operations do not leak ancilla qubits.

    Uses circuit_stats()['current_in_use'] to detect allocator leaks.
    Pattern: measure before op, measure after op, assert increase == result.width.
    """

    def test_modular_add_cq_no_leak(self):
        """CQ modular addition does not leak qubits."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)

        a = ql.qint_mod(3, N=7)
        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        result = a + 5

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        increase = in_use_after - in_use_before
        assert increase == result.width, (
            f"CQ mod add: expected current_in_use increase of {result.width} "
            f"(result register), got {increase}. Possible ancilla leak."
        )

    def test_modular_add_qq_no_leak(self):
        """QQ modular addition does not leak qubits."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)

        a = ql.qint_mod(3, N=7)
        b = ql.qint_mod(2, N=7)
        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        result = a + b

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        increase = in_use_after - in_use_before
        assert increase == result.width, (
            f"QQ mod add: expected current_in_use increase of {result.width} "
            f"(result register), got {increase}. Possible ancilla leak."
        )

    def test_modular_sub_cq_no_leak(self):
        """CQ modular subtraction does not leak qubits."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)

        a = ql.qint_mod(5, N=7)
        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        result = a - 2

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        increase = in_use_after - in_use_before
        assert increase == result.width, (
            f"CQ mod sub: expected current_in_use increase of {result.width} "
            f"(result register), got {increase}. Possible ancilla leak."
        )

    def test_modular_sub_qq_no_leak(self):
        """QQ modular subtraction does not leak qubits."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)

        a = ql.qint_mod(5, N=7)
        b = ql.qint_mod(2, N=7)
        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        result = a - b

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        increase = in_use_after - in_use_before
        assert increase == result.width, (
            f"QQ mod sub: expected current_in_use increase of {result.width} "
            f"(result register), got {increase}. Possible ancilla leak."
        )

    def test_modular_mul_cq_no_leak(self):
        """CQ modular multiplication does not leak qubits."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)

        a = ql.qint_mod(3, N=7)
        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        result = a * 2

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        increase = in_use_after - in_use_before
        assert increase == result.width, (
            f"CQ mod mul: expected current_in_use increase of {result.width} "
            f"(result register), got {increase}. Possible ancilla leak."
        )

    def test_modular_neg_no_leak(self):
        """Modular negation does not leak qubits."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)

        a = ql.qint_mod(3, N=7)
        stats_before = ql.circuit_stats()
        in_use_before = stats_before["current_in_use"]

        result = -a

        stats_after = ql.circuit_stats()
        in_use_after = stats_after["current_in_use"]

        increase = in_use_after - in_use_before
        assert increase == result.width, (
            f"Mod neg: expected current_in_use increase of {result.width} "
            f"(result register), got {increase}. Possible ancilla leak."
        )
