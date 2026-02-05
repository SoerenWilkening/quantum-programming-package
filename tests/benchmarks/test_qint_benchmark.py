"""Benchmark tests for qint operations.

Run with: pytest tests/benchmarks/ -v --benchmark-only
Or skip benchmarks: pytest tests/benchmarks/ --benchmark-skip

These tests measure circuit generation performance,
not quantum execution performance.
"""

import pytest

# Skip entire module if pytest-benchmark not installed
pytest.importorskip("pytest_benchmark")

import quantum_language as ql


class TestQintAddition:
    """Benchmark qint addition operations."""

    def test_add_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit qint addition."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        def do_add():
            return a + b

        benchmark(do_add)
        # Benchmark handles iterations automatically

    def test_add_16bit(self, benchmark, clean_circuit):
        """Benchmark 16-bit qint addition."""
        a = ql.qint(12345, width=16)
        b = ql.qint(6789, width=16)

        def do_add():
            return a + b

        benchmark(do_add)

    @pytest.mark.parametrize("width", [4, 8, 16, 32])
    def test_add_scaling(self, benchmark, width):
        """Benchmark addition scaling with bit width."""
        ql.circuit()
        a = ql.qint(1, width=width)
        b = ql.qint(1, width=width)

        benchmark(lambda: a + b)

    def test_iadd_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit in-place addition."""
        a = ql.qint(5, width=8)

        def do_iadd():
            nonlocal a
            a += 3
            return a

        benchmark(do_iadd)

    def test_iadd_quantum_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit in-place quantum addition."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        def do_iadd():
            nonlocal a
            a += b
            return a

        benchmark(do_iadd)


class TestQintMultiplication:
    """Benchmark qint multiplication operations."""

    def test_mul_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit qint multiplication."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        benchmark(lambda: a * b)

    def test_mul_classical(self, benchmark, clean_circuit):
        """Benchmark qint * classical multiplication."""
        a = ql.qint(5, width=8)

        benchmark(lambda: a * 3)


class TestQintBitwise:
    """Benchmark qint bitwise operations."""

    def test_xor_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit qint XOR."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        benchmark(lambda: a ^ b)

    def test_and_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit qint AND."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        benchmark(lambda: a & b)

    def test_or_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit qint OR."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        benchmark(lambda: a | b)


class TestQintComparison:
    """Benchmark qint comparison operations."""

    def test_eq_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit qint equality comparison."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        benchmark(lambda: a == b)

    def test_lt_8bit(self, benchmark, clean_circuit):
        """Benchmark 8-bit qint less-than comparison."""
        a = ql.qint(5, width=8)
        b = ql.qint(3, width=8)

        benchmark(lambda: a < b)


class TestCircuitCreation:
    """Benchmark circuit setup overhead."""

    def test_circuit_creation(self, benchmark):
        """Benchmark circuit() call overhead."""
        benchmark(ql.circuit)

    def test_qint_creation_8bit(self, benchmark, clean_circuit):
        """Benchmark qint creation."""
        benchmark(lambda: ql.qint(5, width=8))

    def test_qint_creation_16bit(self, benchmark, clean_circuit):
        """Benchmark 16-bit qint creation."""
        benchmark(lambda: ql.qint(12345, width=16))
