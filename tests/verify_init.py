"""Verification tests for qint initialization.

Tests that qint(value, width) correctly initializes quantum integers
through the full pipeline: Python API -> C backend -> OpenQASM -> Qiskit simulation.

Coverage:
- Exhaustive: All values for widths 1-4 bits (30 total values)
- Sampled: Representative values for widths 5-8 bits (~50 values per width)
"""

import pytest
from verify_helpers import (
    format_failure_message,
    generate_exhaustive_values,
    generate_sampled_values,
)

import quantum_language as ql


# Module-level parametrize data generators
def _exhaustive_cases():
    """Generate (width, value) tuples for exhaustive testing (widths 1-4)."""
    cases = []
    for width in [1, 2, 3, 4]:
        for value in generate_exhaustive_values(width):
            cases.append((width, value))
    return cases


def _sampled_cases():
    """Generate (width, value) tuples for sampled testing (widths 5-8)."""
    cases = []
    for width in [5, 6, 7, 8]:
        for value in generate_sampled_values(width):
            cases.append((width, value))
    return cases


# Test data for parametrization
EXHAUSTIVE_CASES = _exhaustive_cases()
SAMPLED_CASES = _sampled_cases()


@pytest.mark.parametrize("width,value", EXHAUSTIVE_CASES)
def test_init_exhaustive(verify_circuit, width, value):
    """Test qint initialization with all values at widths 1-4 bits.

    Exhaustive coverage ensures every possible initialization value works correctly
    at these fundamental bit widths. Total: 2 + 4 + 8 + 16 = 30 test cases.

    Args:
        verify_circuit: Fixture providing verification pipeline
        width: Bit width (1, 2, 3, or 4)
        value: Initialization value (0 to 2^width - 1)
    """

    def circuit_builder(val=value, w=width):
        """Build circuit with qint initialization.

        Uses default argument binding to avoid closure capture issues.
        """
        ql.qint(val, width=w)
        return val

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("init", [value], width, expected, actual)


@pytest.mark.parametrize("width,value", SAMPLED_CASES)
def test_init_sampled(verify_circuit, width, value):
    """Test qint initialization with sampled values at widths 5-8 bits.

    Sampled coverage includes edge cases (0, 1, max, max-1) plus random samples
    to ensure correctness at larger bit widths without exhaustive runtime cost.

    Args:
        verify_circuit: Fixture providing verification pipeline
        width: Bit width (5, 6, 7, or 8)
        value: Initialization value (from sampled set)
    """

    def circuit_builder(val=value, w=width):
        """Build circuit with qint initialization.

        Uses default argument binding to avoid closure capture issues.
        """
        ql.qint(val, width=w)
        return val

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("init", [value], width, expected, actual)
