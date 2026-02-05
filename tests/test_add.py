"""Verification tests for qint addition operations.

Tests that addition (QQ and CQ variants) produces correct results
through the full pipeline: Python API -> C backend -> OpenQASM -> Qiskit simulation.

Coverage:
- Exhaustive: All input pairs for widths 1-4 bits (QQ and CQ)
- Sampled: Representative pairs for widths 5-8 bits (QQ and CQ)
"""

import warnings

import pytest
from verify_helpers import (
    format_failure_message,
    generate_exhaustive_pairs,
    generate_sampled_pairs,
)

import quantum_language as ql

# Suppress cosmetic warnings for values >= 2^(width-1) in unsigned interpretation
warnings.filterwarnings("ignore", message="Value .* exceeds")


# --- Module-level test data generation ---


def _exhaustive_cases():
    """Generate (width, a, b) tuples for exhaustive testing (widths 1-4)."""
    cases = []
    for width in [1, 2, 3, 4]:
        for a, b in generate_exhaustive_pairs(width):
            cases.append((width, a, b))
    return cases


def _sampled_cases():
    """Generate (width, a, b) tuples for sampled testing (widths 5-8)."""
    cases = []
    for width in [5, 6, 7, 8]:
        max_val = (1 << width) - 1
        boundary_pairs = [(0, 0), (0, max_val), (max_val, 0), (max_val, max_val)]
        sampled = generate_sampled_pairs(width, sample_size=10)
        # Merge boundary pairs with sampled pairs, deduplicated
        all_pairs = sorted(set(sampled) | set(boundary_pairs))
        for a, b in all_pairs:
            cases.append((width, a, b))
    return cases


EXHAUSTIVE_QQ_ADD = _exhaustive_cases()
SAMPLED_QQ_ADD = _sampled_cases()
EXHAUSTIVE_CQ_ADD = _exhaustive_cases()
SAMPLED_CQ_ADD = _sampled_cases()


# --- QQ Addition Tests ---


@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_QQ_ADD)
def test_qq_add_exhaustive(verify_circuit, width, a, b):
    """QQ addition: qint(a) + qint(b) at widths 1-4 bits.

    Exhaustive coverage of all input pairs ensures correctness for
    fundamental bit widths. Total: 4 + 16 + 64 + 256 = 340 test cases.
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _r = qa + qb
        return (a + b) % (1 << w)

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("qq_add", [a, b], width, expected, actual)


@pytest.mark.parametrize("width,a,b", SAMPLED_QQ_ADD)
def test_qq_add_sampled(verify_circuit, width, a, b):
    """QQ addition: qint(a) + qint(b) at widths 5-8 bits.

    Sampled coverage includes boundary values and random pairs for
    representative testing at larger bit widths.
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _r = qa + qb
        return (a + b) % (1 << w)

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("qq_add", [a, b], width, expected, actual)


# --- CQ Addition Tests ---


@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_CQ_ADD)
def test_cq_add_exhaustive(verify_circuit, width, a, b):
    """CQ addition: qint(a) += int(b) at widths 1-4 bits.

    Exhaustive coverage of all input pairs for the classical-quantum
    addition variant (in-place addition with classical operand).
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qa += b
        return (a + b) % (1 << w)

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("cq_add", [a, b], width, expected, actual)


@pytest.mark.parametrize("width,a,b", SAMPLED_CQ_ADD)
def test_cq_add_sampled(verify_circuit, width, a, b):
    """CQ addition: qint(a) += int(b) at widths 5-8 bits.

    Sampled coverage for the classical-quantum addition variant
    at larger bit widths.
    """

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qa += b
        return (a + b) % (1 << w)

    actual, expected = verify_circuit(circuit_builder, width)
    assert actual == expected, format_failure_message("cq_add", [a, b], width, expected, actual)
