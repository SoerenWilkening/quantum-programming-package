"""Bitwise operation verification: AND, OR, XOR, NOT through full pipeline.

Tests that all four bitwise operations produce correct results through the
full pipeline: Python API -> C backend circuit -> OpenQASM 3.0 -> Qiskit
simulation -> result extraction.

Coverage:
- Exhaustive: All input pairs for widths 1-4 bits (QQ and CQ for AND/OR/XOR)
- Exhaustive: All single values for widths 1-4 bits (NOT)
- Sampled: Representative pairs for widths 5-6 bits (QQ and CQ for AND/OR/XOR)
- Sampled: Representative values for widths 5-6 bits (NOT)

All bitwise operations return same-width results:
- AND, OR, XOR: result width = operand width (same-width operands)
- NOT: in-place operation, result width = input width

Note on NOT: The ~ operator is in-place -- it flips bits of the input qint
and returns the same object. The result sits on the same qubits as the input,
so standard extraction (bitstring[:width]) works correctly.

IMPORTANT: All circuit_builder functions return (expected, [qint_refs]) to keep
qint objects alive until after OpenQASM export. Without this, Python's garbage
collector may run qint destructors (which add uncomputation gates) before
to_openqasm() is called, corrupting the circuit. This is a known interaction
between the C backend's garbage collection (uncomputation) feature and Python's
reference counting.

Known bugs documented here:

BUG-BIT-01 (CQ Bitwise Result Layout): Classical-quantum bitwise operations
    (AND, OR, XOR with qint op int) produce incorrect result register layouts.
    The C backend allocates result qubits only for bits that are SET in the
    classical operand, rather than always allocating a full-width result
    register. This means:
    - When popcount(classical_value) < width, fewer result qubits are allocated
    - bitstring[:width] extracts the wrong bits
    - The failure pattern depends on both operands and the operation
    CQ tests are marked xfail(strict=False) since some cases pass
    coincidentally (e.g., when both operands are 0, or when all bits of the
    classical value are set).
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


# --- Oracle dictionaries ---

# Python native bitwise oracles (binary ops)
BINARY_OPS = {
    "and": lambda a, b, w: a & b,
    "or": lambda a, b, w: a | b,
    "xor": lambda a, b, w: a ^ b,
}

# Quantum-quantum operator callables
QL_OPS_QQ = {
    "and": lambda qa, qb: qa & qb,
    "or": lambda qa, qb: qa | qb,
    "xor": lambda qa, qb: qa ^ qb,
}

# Classical-quantum operator callables
QL_OPS_CQ = {
    "and": lambda qa, b: qa & b,
    "or": lambda qa, b: qa | b,
    "xor": lambda qa, b: qa ^ b,
}


# --- BUG-BIT-01 xfail marker ---
_XFAIL_CQ = pytest.mark.xfail(
    reason="BUG-BIT-01: CQ bitwise ops produce incorrect result register layout "
    "when classical operand has fewer set bits than operand width",
    strict=False,
)


# --- Module-level test data generation ---


def _exhaustive_binary_cases():
    """Generate (width, a, b, op_name) tuples for exhaustive testing (widths 1-4)."""
    cases = []
    for width in [1, 2, 3, 4]:
        for a, b in generate_exhaustive_pairs(width):
            for op_name in BINARY_OPS:
                cases.append((width, a, b, op_name))
    return cases


def _sampled_binary_cases():
    """Generate (width, a, b, op_name) tuples for sampled testing (widths 5-6)."""
    cases = []
    for width in [5, 6]:
        max_val = (1 << width) - 1
        boundary_pairs = [(0, 0), (0, max_val), (max_val, 0), (max_val, max_val)]
        sampled = generate_sampled_pairs(width, sample_size=10)
        # Merge boundary pairs with sampled pairs, deduplicated
        all_pairs = sorted(set(sampled) | set(boundary_pairs))
        for a, b in all_pairs:
            for op_name in BINARY_OPS:
                cases.append((width, a, b, op_name))
    return cases


def _exhaustive_not_cases():
    """Generate (width, a) tuples for exhaustive NOT testing (widths 1-4)."""
    cases = []
    for width in [1, 2, 3, 4]:
        for a in range(2**width):
            cases.append((width, a))
    return cases


def _sampled_not_cases():
    """Generate (width, a) tuples for sampled NOT testing (widths 5-6)."""
    cases = []
    for width in [5, 6]:
        max_val = (1 << width) - 1
        # Boundary values
        boundary = {0, 1, max_val - 1, max_val}
        # Extract unique a values from sampled pairs
        sampled_pairs = generate_sampled_pairs(width, sample_size=10)
        for a, b in sampled_pairs:
            boundary.add(a)
            boundary.add(b)
        for a in sorted(boundary):
            cases.append((width, a))
    return cases


def _mark_cq_cases(cases):
    """Apply BUG-BIT-01 xfail markers to CQ cases.

    CQ bitwise ops fail when popcount(classical_value) < width, but some
    cases pass coincidentally. Use non-strict xfail for all CQ cases since
    the failure pattern is hard to predict exactly.
    """
    marked = []
    for case in cases:
        width, a, b, op_name = case
        max_val = (1 << width) - 1
        # CQ passes reliably when classical value has all bits set
        if b == max_val:
            marked.append(case)
        else:
            marked.append(pytest.param(*case, marks=_XFAIL_CQ))
    return marked


EXHAUSTIVE_BINARY = _exhaustive_binary_cases()
SAMPLED_BINARY = _sampled_binary_cases()
EXHAUSTIVE_NOT = _exhaustive_not_cases()
SAMPLED_NOT = _sampled_not_cases()

EXHAUSTIVE_CQ = _mark_cq_cases(_exhaustive_binary_cases())
SAMPLED_CQ = _mark_cq_cases(_sampled_binary_cases())


# --- QQ Binary Exhaustive Tests ---


@pytest.mark.parametrize(
    "width,a,b,op_name",
    EXHAUSTIVE_BINARY,
    ids=lambda args: None,
)
def test_qq_bitwise_exhaustive(verify_circuit, width, a, b, op_name):
    """QQ bitwise: qint(a) op qint(b) at widths 1-4 bits.

    Exhaustive coverage of all input pairs x all 3 binary operators (AND, OR, XOR).
    Total: (4+16+64+256) pairs x 3 ops = 1020 test cases.
    """
    expected = BINARY_OPS[op_name](a, b, width)
    ql_op = QL_OPS_QQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = op(qa, qb)
        return (exp, [qa, qb, _result])

    actual, exp = verify_circuit(circuit_builder, width=width)
    assert actual == exp, format_failure_message(f"qq_{op_name}", [a, b], width, exp, actual)


# --- CQ Binary Exhaustive Tests ---


@pytest.mark.parametrize(
    "width,a,b,op_name",
    EXHAUSTIVE_CQ,
    ids=lambda args: None,
)
def test_cq_bitwise_exhaustive(verify_circuit, width, a, b, op_name):
    """CQ bitwise: qint(a) op int(b) at widths 1-4 bits.

    Exhaustive coverage of all input pairs x all 3 binary operators (AND, OR, XOR).
    Classical-quantum variant where second operand is a plain integer.

    Note: Most cases are xfail due to BUG-BIT-01 (CQ result register layout bug).
    Cases where classical value has all bits set pass correctly.
    """
    expected = BINARY_OPS[op_name](a, b, width)
    ql_op = QL_OPS_CQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        _result = op(qa, b)
        return (exp, [qa, _result])

    actual, exp = verify_circuit(circuit_builder, width=width)
    assert actual == exp, format_failure_message(f"cq_{op_name}", [a, b], width, exp, actual)


# --- NOT Exhaustive Tests ---


@pytest.mark.parametrize(
    "width,a",
    EXHAUSTIVE_NOT,
    ids=lambda args: None,
)
def test_not_exhaustive(verify_circuit, width, a):
    """NOT: ~qint(a) at widths 1-4 bits.

    Exhaustive coverage of all values. NOT is in-place: ~qa flips bits of qa
    and returns qa (same object). Result sits on the same qubits as input,
    so standard extraction (bitstring[:width]) works correctly.
    Total: 2+4+8+16 = 30 test cases.
    """
    expected = ((1 << width) - 1) ^ a  # bitwise complement within width

    def circuit_builder(a=a, w=width, exp=expected):
        qa = ql.qint(a, width=w)
        _result = ~qa
        return (exp, [qa, _result])

    actual, exp = verify_circuit(circuit_builder, width=width)
    assert actual == exp, format_failure_message("not", [a], width, exp, actual)


# --- QQ Binary Sampled Tests ---


@pytest.mark.parametrize(
    "width,a,b,op_name",
    SAMPLED_BINARY,
    ids=lambda args: None,
)
def test_qq_bitwise_sampled(verify_circuit, width, a, b, op_name):
    """QQ bitwise: qint(a) op qint(b) at widths 5-6 bits.

    Sampled coverage includes boundary values and random pairs for
    representative testing at larger bit widths.
    """
    expected = BINARY_OPS[op_name](a, b, width)
    ql_op = QL_OPS_QQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = op(qa, qb)
        return (exp, [qa, qb, _result])

    actual, exp = verify_circuit(circuit_builder, width=width)
    assert actual == exp, format_failure_message(f"qq_{op_name}", [a, b], width, exp, actual)


# --- CQ Binary Sampled Tests ---


@pytest.mark.parametrize(
    "width,a,b,op_name",
    SAMPLED_CQ,
    ids=lambda args: None,
)
def test_cq_bitwise_sampled(verify_circuit, width, a, b, op_name):
    """CQ bitwise: qint(a) op int(b) at widths 5-6 bits.

    Sampled coverage for the classical-quantum variant at larger bit widths.

    Note: Most cases are xfail due to BUG-BIT-01 (CQ result register layout bug).
    """
    expected = BINARY_OPS[op_name](a, b, width)
    ql_op = QL_OPS_CQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        _result = op(qa, b)
        return (exp, [qa, _result])

    actual, exp = verify_circuit(circuit_builder, width=width)
    assert actual == exp, format_failure_message(f"cq_{op_name}", [a, b], width, exp, actual)


# --- NOT Sampled Tests ---


@pytest.mark.parametrize(
    "width,a",
    SAMPLED_NOT,
    ids=lambda args: None,
)
def test_not_sampled(verify_circuit, width, a):
    """NOT: ~qint(a) at widths 5-6 bits.

    Sampled coverage with boundary values and values extracted from
    sampled pairs for representative testing at larger bit widths.
    """
    expected = ((1 << width) - 1) ^ a

    def circuit_builder(a=a, w=width, exp=expected):
        qa = ql.qint(a, width=w)
        _result = ~qa
        return (exp, [qa, _result])

    actual, exp = verify_circuit(circuit_builder, width=width)
    assert actual == exp, format_failure_message("not", [a], width, exp, actual)
