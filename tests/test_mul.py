"""Verification tests for multiplication operations.

Tests that qint multiplication (QQ and CQ variants) produces correct results
through the full pipeline: Python API -> C backend -> OpenQASM -> Qiskit simulation.

Coverage:
- Exhaustive: All input pairs for widths 1-3 bits (84 pairs per variant)
- Sampled: Representative pairs for widths 4-5 bits (~30-40 pairs per variant)

Operations:
- QQ multiplication: qint(a) * qint(b)
- CQ multiplication: qint(a) *= int(b)
"""

import warnings

import pytest
from verify_helpers import (
    format_failure_message,
    generate_exhaustive_pairs,
    generate_sampled_pairs,
)

import quantum_language as ql

# Suppress warnings about values exceeding signed range
warnings.filterwarnings("ignore", message="Value .* exceeds")


# --- Module-level test data generators ---


def _exhaustive_qq_mul_cases():
    """Generate (width, a, b) tuples for exhaustive QQ multiplication (widths 1-3)."""
    cases = []
    for width in [1, 2, 3]:
        for a, b in generate_exhaustive_pairs(width):
            cases.append((width, a, b))
    return cases


def _sampled_qq_mul_cases():
    """Generate (width, a, b) tuples for sampled QQ multiplication (widths 4-5)."""
    cases = []
    for width in [4, 5]:
        for a, b in generate_sampled_pairs(width, sample_size=10):
            cases.append((width, a, b))
    return cases


def _exhaustive_cq_mul_cases():
    """Generate (width, a, b) tuples for exhaustive CQ multiplication (widths 1-3)."""
    cases = []
    for width in [1, 2, 3]:
        for a, b in generate_exhaustive_pairs(width):
            cases.append((width, a, b))
    return cases


def _sampled_cq_mul_cases():
    """Generate (width, a, b) tuples for sampled CQ multiplication (widths 4-5)."""
    cases = []
    for width in [4, 5]:
        for a, b in generate_sampled_pairs(width, sample_size=10):
            cases.append((width, a, b))
    return cases


# Test data for parametrization
EXHAUSTIVE_QQ_MUL = _exhaustive_qq_mul_cases()
SAMPLED_QQ_MUL = _sampled_qq_mul_cases()
EXHAUSTIVE_CQ_MUL = _exhaustive_cq_mul_cases()
SAMPLED_CQ_MUL = _sampled_cq_mul_cases()


# --- QQ Multiplication Tests ---


@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_QQ_MUL)
def test_qq_mul_exhaustive(verify_circuit, width, a, b):
    """QQ multiplication: qint(a) * qint(b) at widths 1-3 bits.

    Exhaustive coverage of all input pairs. Total: 4 + 16 + 64 = 84 test cases.
    Expected result: (a * b) % (2^width) -- unsigned wrap on overflow.
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _r = qa * qb
        return (a * b) % (1 << w)

    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("qq_mul", [a, b], width, exp, actual)


@pytest.mark.parametrize("width,a,b", SAMPLED_QQ_MUL)
def test_qq_mul_sampled(verify_circuit, width, a, b):
    """QQ multiplication: qint(a) * qint(b) at widths 4-5 bits.

    Representative pairs including boundary values and random samples.
    Expected result: (a * b) % (2^width) -- unsigned wrap on overflow.
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _r = qa * qb
        return (a * b) % (1 << w)

    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("qq_mul", [a, b], width, exp, actual)


# --- CQ Multiplication Tests ---


@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_CQ_MUL)
def test_cq_mul_exhaustive(verify_circuit, width, a, b):
    """CQ multiplication: qint(a) *= int(b) at widths 1-3 bits.

    Exhaustive coverage of all input pairs. Total: 4 + 16 + 64 = 84 test cases.
    Expected result: (a * b) % (2^width) -- unsigned wrap on overflow.
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qa *= b
        return (a * b) % (1 << w)

    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("cq_mul", [a, b], width, exp, actual)


@pytest.mark.parametrize("width,a,b", SAMPLED_CQ_MUL)
def test_cq_mul_sampled(verify_circuit, width, a, b):
    """CQ multiplication: qint(a) *= int(b) at widths 4-5 bits.

    Representative pairs including boundary values and random samples.
    Expected result: (a * b) % (2^width) -- unsigned wrap on overflow.
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qa *= b
        return (a * b) % (1 << w)

    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("cq_mul", [a, b], width, exp, actual)
