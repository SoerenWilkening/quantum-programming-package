"""Verification tests for qint comparison operations.

Tests that all 6 comparison operators (==, !=, <, >, <=, >=) produce correct
boolean results through the full pipeline: Python API -> C backend -> OpenQASM ->
Qiskit simulation.

Coverage:
- Exhaustive: All input pairs for widths 1-3 bits (QQ and CQ variants)
- Sampled: Representative pairs for widths 4-5 bits (QQ and CQ variants)
- BUG-02 regression: MSB index, GC gate reversal, unsigned overflow sub-cases

All comparisons return qbool (1-bit result): 1 = True, 0 = False.

Known bugs documented here (discovered during exhaustive verification):

BUG-CMP-01 (Equality Inversion): eq and ne operators return inverted results
    for ALL inputs at ALL widths. eq(a,b) returns 0 when a==b (should be 1),
    ne(a,b) returns 0 when a!=b (should be 1). Both QQ and CQ variants.
    Exception: CQ ne passes when b == max_val (all bits set) for a != max_val.

BUG-CMP-02 (Ordering Comparison Error): lt, gt, le, ge operators produce
    incorrect results for specific (a,b) pairs where the internal widened
    subtraction circuit does not correctly compute the sign of (b-a).
    Identical failure set for both QQ and CQ variants.

Note: Widths >= 6 are excluded because gt/le operators generate circuits
    that exceed available simulation memory (BUG-CMP-03).
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

# Python native comparison oracles
OPS = {
    "eq": lambda a, b: int(a == b),
    "ne": lambda a, b: int(a != b),
    "lt": lambda a, b: int(a < b),
    "gt": lambda a, b: int(a > b),
    "le": lambda a, b: int(a <= b),
    "ge": lambda a, b: int(a >= b),
}

# Quantum-quantum operator callables (qint op qint)
QL_OPS_QQ = {
    "eq": lambda qa, qb: qa == qb,
    "ne": lambda qa, qb: qa != qb,
    "lt": lambda qa, qb: qa < qb,
    "gt": lambda qa, qb: qa > qb,
    "le": lambda qa, qb: qa <= qb,
    "ge": lambda qa, qb: qa >= qb,
}

# Quantum-classical operator callables (qint op int)
QL_OPS_CQ = {
    "eq": lambda qa, b: qa == b,
    "ne": lambda qa, b: qa != b,
    "lt": lambda qa, b: qa < b,
    "gt": lambda qa, b: qa > b,
    "le": lambda qa, b: qa <= b,
    "ge": lambda qa, b: qa >= b,
}


# ---------------------------------------------------------------------------
# BUG-CMP-01/02 FIXED in v1.6 (Phase 35)
# ---------------------------------------------------------------------------
# All comparison bugs have been resolved:
# - BUG-CMP-01: Dual-bug fix (GC gate reversal + MSB-first bit ordering)
# - BUG-CMP-02: LSB-aligned CNOT copies for unsigned comparison semantics
# Historical failure sets preserved below for reference only.


# --- Module-level test data generation ---


def _exhaustive_cases():
    """Generate (width, a, b, op_name) tuples for exhaustive testing (widths 1-3)."""
    cases = []
    for width in [1, 2, 3]:
        for a, b in generate_exhaustive_pairs(width):
            for op_name in OPS:
                cases.append((width, a, b, op_name))
    return cases


def _sampled_cases():
    """Generate (width, a, b, op_name) tuples for sampled testing (widths 4-5)."""
    cases = []
    for width in [4, 5]:
        max_val = (1 << width) - 1
        boundary_pairs = [(0, 0), (0, max_val), (max_val, 0), (max_val, max_val)]
        sampled = generate_sampled_pairs(width, sample_size=5)
        # Merge boundary pairs with sampled pairs, deduplicated
        all_pairs = sorted(set(sampled) | set(boundary_pairs))
        for a, b in all_pairs:
            for op_name in OPS:
                cases.append((width, a, b, op_name))
    return cases


def _mark_qq_cases(cases):
    """All BUG-CMP-01/02 bugs fixed in v1.6 — no xfail needed."""
    return cases


def _mark_cq_cases(cases):
    """All BUG-CMP-01/02 bugs fixed in v1.6 — no xfail needed."""
    return cases


def _mark_sampled(cases, cq=False):
    """All BUG-CMP-01/02 bugs fixed in v1.6 — no xfail needed."""
    return cases


EXHAUSTIVE_QQ = _mark_qq_cases(_exhaustive_cases())
SAMPLED_QQ = _mark_sampled(_sampled_cases(), cq=False)
EXHAUSTIVE_CQ = _mark_cq_cases(_exhaustive_cases())
SAMPLED_CQ = _mark_sampled(_sampled_cases(), cq=True)


# --- QQ Comparison Tests ---


@pytest.mark.parametrize("width,a,b,op_name", EXHAUSTIVE_QQ)
def test_qq_cmp_exhaustive(verify_circuit, width, a, b, op_name):
    """QQ comparison: qint(a) op qint(b) at widths 1-4 bits.

    Exhaustive coverage of all input pairs x all 6 operators.
    """
    expected = OPS[op_name](a, b)
    ql_op = QL_OPS_QQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = op(qa, qb)
        return exp

    actual, exp = verify_circuit(circuit_builder, width=1)
    assert actual == exp, format_failure_message(f"qq_{op_name}", [a, b], width, exp, actual)


@pytest.mark.parametrize("width,a,b,op_name", SAMPLED_QQ)
def test_qq_cmp_sampled(verify_circuit, width, a, b, op_name):
    """QQ comparison: qint(a) op qint(b) at widths 4-5 bits.

    Sampled coverage includes boundary values and random pairs.
    """
    expected = OPS[op_name](a, b)
    ql_op = QL_OPS_QQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = op(qa, qb)
        return exp

    actual, exp = verify_circuit(circuit_builder, width=1)
    assert actual == exp, format_failure_message(f"qq_{op_name}", [a, b], width, exp, actual)


# --- CQ Comparison Tests ---


@pytest.mark.parametrize("width,a,b,op_name", EXHAUSTIVE_CQ)
def test_cq_cmp_exhaustive(verify_circuit, width, a, b, op_name):
    """CQ comparison: qint(a) op int(b) at widths 1-4 bits.

    Exhaustive coverage of all input pairs x all 6 operators
    for the classical-quantum comparison variant.
    """
    expected = OPS[op_name](a, b)
    ql_op = QL_OPS_CQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        _result = op(qa, b)
        return exp

    actual, exp = verify_circuit(circuit_builder, width=1)
    assert actual == exp, format_failure_message(f"cq_{op_name}", [a, b], width, exp, actual)


@pytest.mark.parametrize("width,a,b,op_name", SAMPLED_CQ)
def test_cq_cmp_sampled(verify_circuit, width, a, b, op_name):
    """CQ comparison: qint(a) op int(b) at widths 4-5 bits.

    Sampled coverage for the classical-quantum comparison variant.
    """
    expected = OPS[op_name](a, b)
    ql_op = QL_OPS_CQ[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        _result = op(qa, b)
        return exp

    actual, exp = verify_circuit(circuit_builder, width=1)
    assert actual == exp, format_failure_message(f"cq_{op_name}", [a, b], width, exp, actual)


# --- BUG-02 Regression Tests ---


class TestBug02Regression:
    """BUG-02 regression: three root causes fixed in Phase 29-16.

    These specific test cases were the original BUG-02 failures that were
    fixed. They verify the fixes remain intact. Note: the wider BUG-CMP-01
    and BUG-CMP-02 bugs affect OTHER comparison cases but these specific
    cases happen to produce correct results.
    """

    def test_msb_index_fix(self, verify_circuit):
        """Root cause 1: MSB at index 63 (not 64-width) in right-aligned storage.
        Regression for: qint(3) < qint(5) at 4-bit width."""

        def circuit_builder():
            x = ql.qint(3, width=4)
            y = ql.qint(5, width=4)
            _result = x < y
            return 1  # 3 < 5 is True

        actual, expected = verify_circuit(circuit_builder, width=1)
        assert actual == expected, "BUG-02 regression: MSB index fix failed"

    def test_gc_gate_reversal_fix(self, verify_circuit):
        """Root cause 2: comparison results must not have layer tracking.
        Regression for: qint(5) <= qint(5) at 4-bit width."""

        def circuit_builder():
            x = ql.qint(5, width=4)
            y = ql.qint(5, width=4)
            _result = x <= y
            return 1  # 5 <= 5 is True

        actual, expected = verify_circuit(circuit_builder, width=1)
        assert actual == expected, "BUG-02 regression: GC gate reversal fix failed"

    def test_unsigned_overflow_fix(self, verify_circuit):
        """Root cause 3: (n+1)-bit widened comparison for full unsigned range.
        Regression for: qint(0) <= qint(15) at 4-bit width."""

        def circuit_builder():
            x = ql.qint(0, width=4)
            y = ql.qint(15, width=4)
            _result = x <= y
            return 1  # 0 <= 15 is True

        actual, expected = verify_circuit(circuit_builder, width=1)
        assert actual == expected, "BUG-02 regression: unsigned overflow fix failed"
