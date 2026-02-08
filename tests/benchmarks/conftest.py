"""Pytest fixtures for benchmark tests.

These fixtures integrate with pytest-benchmark for reproducible
performance testing of quantum circuit generation.
"""

# Check if pytest-benchmark is available
import importlib.util

import pytest

HAS_BENCHMARK = importlib.util.find_spec("pytest_benchmark") is not None


@pytest.fixture
def clean_circuit():
    """Setup clean circuit state for benchmarking.

    Creates a fresh circuit before each benchmark iteration.
    This ensures consistent starting conditions.

    Yields
    ------
    circuit
        Fresh circuit instance.
    """
    import quantum_language as ql

    c = ql.circuit()
    yield c
    # Cleanup happens automatically via GC


@pytest.fixture
def qint_pair_8bit(clean_circuit):
    """Create pair of 8-bit qints for binary operations.

    Parameters
    ----------
    clean_circuit : circuit
        Clean circuit fixture (dependency).

    Returns
    -------
    tuple
        (qint(5, 8), qint(3, 8)) pair.
    """
    import quantum_language as ql

    return ql.qint(5, width=8), ql.qint(3, width=8)


@pytest.fixture
def qint_pair_16bit(clean_circuit):
    """Create pair of 16-bit qints for binary operations.

    Returns
    -------
    tuple
        (qint(12345, 16), qint(6789, 16)) pair.
    """
    import quantum_language as ql

    return ql.qint(12345, width=16), ql.qint(6789, width=16)


@pytest.fixture(params=[4, 8, 16, 32])
def qint_width(request):
    """Parametrize over common bit widths.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Pytest fixture request.

    Yields
    ------
    int
        Bit width value.
    """
    return request.param
