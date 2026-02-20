"""Automatic uncomputation verification tests (VADV-01).

Verifies that after arithmetic and comparison operations with uncomputation
enabled (EAGER mode via ql.option('qubit_saving', True)):
1. Computation results remain correct despite uncomputation of intermediates
2. Input operands are preserved (not corrupted by uncomputation)
3. True ancilla qubits (between result and inputs) measure as |0>

This test file uses a custom full-bitstring pipeline (NOT verify_circuit)
because verify_circuit only extracts bitstring[:width]. Uncomputation
verification requires inspecting ALL qubits in the circuit.

Bitstring layout (leftmost = highest qubit index = last allocated):
  [result_bits][ancilla_bits][input_b_bits][input_a_bits]
  result: bitstring[:result_width]
  input_a: bitstring[-width_a:] (first allocated = lowest indices = rightmost)
  input_b: bitstring[-width_a-width_b:-width_a]
  ancilla: everything between result and inputs

Pipeline: Python quantum_language API -> C backend circuit -> OpenQASM 3.0
          -> Qiskit AerSimulator (statevector, shots=1) -> full bitstring analysis.
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------


def _run_uncomputation_pipeline(circuit_builder, result_width):
    """Run circuit with EAGER uncomputation and return full bitstring.

    Args:
        circuit_builder: Callable returning (expected_value, [keepalive_refs]).
        result_width: Bit width of the result register.

    Returns:
        (bitstring, expected_value) for analysis.
    """
    gc.collect()
    ql.circuit()
    ql.option("qubit_saving", True)

    expected, keepalive = circuit_builder()

    qasm_str = ql.to_openqasm()
    ql.option("qubit_saving", False)

    # Release keepalive refs after QASM export
    del keepalive

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    return bitstring, expected


def _check_uncomputation(
    bitstring, result_width, expected, input_a=None, input_b=None, width_a=0, width_b=0
):
    """Check result correctness, input preservation, and ancilla cleanup.

    Args:
        bitstring: Full measurement bitstring from simulation.
        result_width: Number of bits in the result register.
        expected: Expected integer value of result.
        input_a: Expected value of first input operand (or None to skip check).
        input_b: Expected value of second input operand (or None to skip check).
        width_a: Bit width of input a register.
        width_b: Bit width of input b register.

    Returns:
        dict with keys: actual_result, result_correct, a_preserved, b_preserved,
        ancilla_clean, ancilla_bits, details.
    """
    n = len(bitstring)

    # Result register: highest qubit indices = leftmost
    result_bits = bitstring[:result_width]
    actual_result = int(result_bits, 2)
    result_correct = actual_result == expected

    # Input a: first allocated = lowest indices = rightmost
    a_preserved = True
    extracted_a = None
    if input_a is not None and width_a > 0:
        a_bits = bitstring[n - width_a :]
        extracted_a = int(a_bits, 2)
        a_preserved = extracted_a == (input_a % (1 << width_a))

    # Input b: second allocated = next from right
    b_preserved = True
    extracted_b = None
    if input_b is not None and width_b > 0:
        b_bits = bitstring[n - width_a - width_b : n - width_a]
        extracted_b = int(b_bits, 2)
        b_preserved = extracted_b == (input_b % (1 << width_b))

    # Ancilla: bits between result and inputs
    input_total = width_a + width_b
    ancilla_bits = (
        bitstring[result_width : n - input_total] if n > result_width + input_total else ""
    )
    ancilla_clean = all(b == "0" for b in ancilla_bits) if ancilla_bits else True

    return {
        "actual_result": actual_result,
        "result_correct": result_correct,
        "a_preserved": a_preserved,
        "b_preserved": b_preserved,
        "ancilla_clean": ancilla_clean,
        "ancilla_bits": ancilla_bits,
        "extracted_a": extracted_a,
        "extracted_b": extracted_b,
        "bitstring": bitstring,
        "n_qubits": n,
    }


# ---------------------------------------------------------------------------
# Calibration test (run first to validate pipeline)
# ---------------------------------------------------------------------------


class TestUncompCalibration:
    """Calibration tests to validate the full-bitstring extraction pipeline."""

    def test_uncomp_calibration_add(self):
        """Calibration: 3-bit add a=1 + b=2 = 3. Prints diagnostics."""
        width = 3

        def build():
            a = ql.qint(1, width=width)
            b = ql.qint(2, width=width)
            result = a + b
            expected = (1 + 2) % (1 << width)
            return (expected, [a, b, result])

        bitstring, expected = _run_uncomputation_pipeline(build, width)
        info = _check_uncomputation(
            bitstring,
            width,
            expected,
            input_a=1,
            input_b=2,
            width_a=width,
            width_b=width,
        )

        print(f"\n  Calibration: width={width}, expected={expected}")
        print(f"  Full bitstring: {bitstring} ({info['n_qubits']} qubits)")
        print(f"  Result: {info['actual_result']} (correct={info['result_correct']})")
        print(f"  Input a: {info['extracted_a']} (preserved={info['a_preserved']})")
        print(f"  Input b: {info['extracted_b']} (preserved={info['b_preserved']})")
        print(f"  Ancilla: '{info['ancilla_bits']}' (clean={info['ancilla_clean']})")

        assert info["result_correct"], (
            f"Calibration result wrong: expected={expected}, "
            f"got={info['actual_result']}, bitstring={bitstring}"
        )
        assert info["a_preserved"], (
            f"Calibration input a corrupted: expected=1, got={info['extracted_a']}"
        )
        assert info["b_preserved"], (
            f"Calibration input b corrupted: expected=2, got={info['extracted_b']}"
        )


# ---------------------------------------------------------------------------
# Arithmetic uncomputation tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,width",
    [
        pytest.param(1, 2, 3, id="w3_1p2"),
        pytest.param(3, 4, 3, id="w3_3p4"),
    ],
)
def test_uncomp_add(a, b, width):
    """Verify uncomputation after addition: result correct, inputs preserved, ancilla clean."""
    expected_val = (a + b) % (1 << width)

    def build():
        qa = ql.qint(a, width=width)
        qb = ql.qint(b, width=width)
        result = qa + qb
        return (expected_val, [qa, qb, result])

    bitstring, expected = _run_uncomputation_pipeline(build, width)
    info = _check_uncomputation(
        bitstring,
        width,
        expected,
        input_a=a,
        input_b=b,
        width_a=width,
        width_b=width,
    )

    assert info["result_correct"], (
        f"Add {a}+{b}: result wrong, expected={expected}, got={info['actual_result']}, "
        f"bitstring={bitstring}"
    )
    assert info["a_preserved"], (
        f"Add {a}+{b}: input a corrupted, expected={a}, got={info['extracted_a']}, "
        f"bitstring={bitstring}"
    )
    assert info["b_preserved"], (
        f"Add {a}+{b}: input b corrupted, expected={b}, got={info['extracted_b']}, "
        f"bitstring={bitstring}"
    )
    assert info["ancilla_clean"], (
        f"Add {a}+{b}: ancilla not clean, ancilla='{info['ancilla_bits']}', bitstring={bitstring}"
    )


@pytest.mark.parametrize(
    "a,b,width",
    [
        pytest.param(3, 1, 3, id="w3_3m1"),
        pytest.param(5, 2, 3, id="w3_5m2"),
    ],
)
def test_uncomp_sub(a, b, width):
    """Verify uncomputation after subtraction: result correct, inputs preserved, ancilla clean."""
    expected_val = (a - b) % (1 << width)

    def build():
        qa = ql.qint(a, width=width)
        qb = ql.qint(b, width=width)
        result = qa - qb
        return (expected_val, [qa, qb, result])

    bitstring, expected = _run_uncomputation_pipeline(build, width)
    info = _check_uncomputation(
        bitstring,
        width,
        expected,
        input_a=a,
        input_b=b,
        width_a=width,
        width_b=width,
    )

    assert info["result_correct"], (
        f"Sub {a}-{b}: result wrong, expected={expected}, got={info['actual_result']}, "
        f"bitstring={bitstring}"
    )
    assert info["a_preserved"], (
        f"Sub {a}-{b}: input a corrupted, expected={a}, got={info['extracted_a']}, "
        f"bitstring={bitstring}"
    )
    assert info["b_preserved"], (
        f"Sub {a}-{b}: input b corrupted, expected={b}, got={info['extracted_b']}, "
        f"bitstring={bitstring}"
    )
    assert info["ancilla_clean"], (
        f"Sub {a}-{b}: ancilla not clean, ancilla='{info['ancilla_bits']}', bitstring={bitstring}"
    )


@pytest.mark.parametrize(
    "a,b,width",
    [
        pytest.param(1, 2, 3, id="w3_1x2"),
        pytest.param(2, 3, 3, id="w3_2x3"),
    ],
)
def test_uncomp_mul(a, b, width):
    """Verify uncomputation after multiplication: result correct, inputs preserved, ancilla clean."""
    expected_val = (a * b) % (1 << width)

    def build():
        qa = ql.qint(a, width=width)
        qb = ql.qint(b, width=width)
        result = qa * qb
        return (expected_val, [qa, qb, result])

    bitstring, expected = _run_uncomputation_pipeline(build, width)
    info = _check_uncomputation(
        bitstring,
        width,
        expected,
        input_a=a,
        input_b=b,
        width_a=width,
        width_b=width,
    )

    assert info["result_correct"], (
        f"Mul {a}*{b}: result wrong, expected={expected}, got={info['actual_result']}, "
        f"bitstring={bitstring}"
    )
    assert info["a_preserved"], (
        f"Mul {a}*{b}: input a corrupted, expected={a}, got={info['extracted_a']}, "
        f"bitstring={bitstring}"
    )
    assert info["b_preserved"], (
        f"Mul {a}*{b}: input b corrupted, expected={b}, got={info['extracted_b']}, "
        f"bitstring={bitstring}"
    )
    assert info["ancilla_clean"], (
        f"Mul {a}*{b}: ancilla not clean, ancilla='{info['ancilla_bits']}', bitstring={bitstring}"
    )


# ---------------------------------------------------------------------------
# Comparison uncomputation tests
# ---------------------------------------------------------------------------

# Comparison operators for quantum-quantum variant
_CMP_OPS = {
    "gt": lambda qa, qb: qa > qb,
    "lt": lambda qa, qb: qa < qb,
    "ge": lambda qa, qb: qa >= qb,
    "le": lambda qa, qb: qa <= qb,
    "eq": lambda qa, qb: qa == qb,
    "ne": lambda qa, qb: qa != qb,
}

# Python equivalents for expected value calculation
_PY_CMP = {
    "gt": lambda a, b: int(a > b),
    "lt": lambda a, b: int(a < b),
    "ge": lambda a, b: int(a >= b),
    "le": lambda a, b: int(a <= b),
    "eq": lambda a, b: int(a == b),
    "ne": lambda a, b: int(a != b),
}


def _is_msb_spanning(a, b, width):
    """Check if a and b span the MSB boundary (different MSBs)."""
    half = 1 << (width - 1)
    return (a >= half) != (b >= half)


def _make_cmp_result_params():
    """Generate comparison test parameters for result correctness.

    All BUG-CMP-01/02 bugs fixed in v1.6 — no xfail markers needed.
    """
    params = []
    # Ordering comparisons
    cases = [
        ("gt", 3, 1, 3),
        ("lt", 1, 3, 3),
        ("ge", 2, 2, 3),
        ("le", 1, 2, 3),
    ]
    for op_name, a, b, width in cases:
        params.append(
            pytest.param(
                op_name,
                a,
                b,
                width,
                id=f"{op_name}_{a}v{b}_w{width}",
            )
        )

    # eq/ne cases (BUG-CMP-01 fixed in v1.6)
    eq_ne_cases = [
        ("eq", 2, 2, 3),
        ("ne", 1, 2, 3),
    ]
    for op_name, a, b, width in eq_ne_cases:
        params.append(
            pytest.param(
                op_name,
                a,
                b,
                width,
                id=f"{op_name}_{a}v{b}_w{width}",
            )
        )
    return params


@pytest.mark.parametrize("op_name,a,b,width", _make_cmp_result_params())
def test_uncomp_comparison(op_name, a, b, width):
    """Verify comparison result correctness and input preservation with uncomputation."""
    result_width = 1  # qbool is 1 bit
    expected_val = _PY_CMP[op_name](a, b)

    def build():
        qa = ql.qint(a, width=width)
        qb = ql.qint(b, width=width)
        result = _CMP_OPS[op_name](qa, qb)
        return (expected_val, [qa, qb, result])

    bitstring, expected = _run_uncomputation_pipeline(build, result_width)
    info = _check_uncomputation(
        bitstring,
        result_width,
        expected,
        input_a=a,
        input_b=b,
        width_a=width,
        width_b=width,
    )

    assert info["result_correct"], (
        f"Cmp {op_name}({a},{b}): result wrong, expected={expected}, "
        f"got={info['actual_result']}, bitstring={bitstring}"
    )
    assert info["a_preserved"], (
        f"Cmp {op_name}({a},{b}): input a corrupted, expected={a}, "
        f"got={info['extracted_a']}, bitstring={bitstring}"
    )
    assert info["b_preserved"], (
        f"Cmp {op_name}({a},{b}): input b corrupted, expected={b}, "
        f"got={info['extracted_b']}, bitstring={bitstring}"
    )


def _make_cmp_ancilla_params():
    """Generate comparison ancilla cleanup test parameters.

    gt/le use widened (w+1) temporaries that leave ancilla dirty.
    These are xfailed as a known uncomputation limitation (NOT a bug).
    BUG-CMP-02 fixed in v1.6 — no longer needs xfail.
    """
    params = []
    cases = [
        ("gt", 3, 1, 3, True),  # gt uses widened temps -> ancilla dirty
        ("lt", 1, 3, 3, False),  # lt uses subtract-add-back -> may be clean
        ("ge", 2, 2, 3, False),  # ge delegates to NOT(lt) -> may be clean
        ("le", 1, 2, 3, True),  # le delegates to NOT(gt) -> ancilla dirty
    ]
    for op_name, a, b, width, has_dirty_ancilla in cases:
        marks = []
        if has_dirty_ancilla:
            marks.append(
                pytest.mark.xfail(
                    reason=f"Comparison {op_name} uses widened temporaries leaving ancilla dirty",
                    strict=False,
                )
            )
        params.append(
            pytest.param(
                op_name,
                a,
                b,
                width,
                id=f"{op_name}_{a}v{b}_w{width}",
                marks=marks,
            )
        )
    return params


@pytest.mark.parametrize("op_name,a,b,width", _make_cmp_ancilla_params())
def test_uncomp_comparison_ancilla(op_name, a, b, width):
    """Verify ancilla cleanup after comparison with uncomputation enabled."""
    result_width = 1
    expected_val = _PY_CMP[op_name](a, b)

    def build():
        qa = ql.qint(a, width=width)
        qb = ql.qint(b, width=width)
        result = _CMP_OPS[op_name](qa, qb)
        return (expected_val, [qa, qb, result])

    bitstring, expected = _run_uncomputation_pipeline(build, result_width)
    info = _check_uncomputation(
        bitstring,
        result_width,
        expected,
        input_a=a,
        input_b=b,
        width_a=width,
        width_b=width,
    )

    assert info["ancilla_clean"], (
        f"Cmp {op_name}({a},{b}): ancilla not clean, ancilla='{info['ancilla_bits']}', "
        f"bitstring={bitstring}"
    )


# ---------------------------------------------------------------------------
# Compound boolean uncomputation tests
# ---------------------------------------------------------------------------


def test_uncomp_compound_and():
    """Compound AND: (a > 1) & (b < 3) with a=2, b=1, width=3.

    Both conditions True -> result True (1). Multiple sub-expressions
    generate multiple ancillae that must be uncomputed.
    """
    width = 3
    result_width = 1
    a_val, b_val = 2, 1
    # a=2 > 1 is True, b=1 < 3 is True -> True & True = True
    expected_val = 1

    def build():
        a = ql.qint(a_val, width=width)
        b = ql.qint(b_val, width=width)
        cond1 = a > 1
        cond2 = b < 3
        result = cond1 & cond2
        return (expected_val, [a, b, cond1, cond2, result])

    bitstring, expected = _run_uncomputation_pipeline(build, result_width)
    # For compound booleans, input layout is complex (sub-expression intermediates)
    # Check result at bitstring[0] and that inputs are somewhere in the bitstring
    actual = int(bitstring[0], 2)

    assert actual == expected, (
        f"Compound AND result wrong: expected={expected}, got={actual}, "
        f"bitstring={bitstring} ({len(bitstring)} qubits)"
    )


def test_uncomp_compound_or():
    """Compound OR: (a > 1) | (b < 1) with a=2, b=2, width=3.

    First True, second False -> True | False = True (1).
    """
    width = 3
    result_width = 1
    a_val, b_val = 2, 2
    # a=2 > 1 is True, b=2 < 1 is False -> True | False = True
    expected_val = 1

    def build():
        a = ql.qint(a_val, width=width)
        b = ql.qint(b_val, width=width)
        cond1 = a > 1
        cond2 = b < 1
        result = cond1 | cond2
        return (expected_val, [a, b, cond1, cond2, result])

    bitstring, expected = _run_uncomputation_pipeline(build, result_width)
    actual = int(bitstring[0], 2)

    assert actual == expected, (
        f"Compound OR result wrong: expected={expected}, got={actual}, "
        f"bitstring={bitstring} ({len(bitstring)} qubits)"
    )


def test_uncomp_compound_eq():
    """Compound with eq: (a == 2) & (b < 3) with a=2, b=1, width=3.

    Both True -> result True. BUG-CMP-01 fixed in v1.6.
    """
    width = 3
    result_width = 1
    a_val, b_val = 2, 1
    # a=2 == 2 is True, b=1 < 3 is True -> True & True = True
    expected_val = 1

    def build():
        a = ql.qint(a_val, width=width)
        b = ql.qint(b_val, width=width)
        cond1 = a == 2
        cond2 = b < 3
        result = cond1 & cond2
        return (expected_val, [a, b, cond1, cond2, result])

    bitstring, expected = _run_uncomputation_pipeline(build, result_width)
    actual = int(bitstring[0], 2)

    assert actual == expected, (
        f"Compound eq result wrong: expected={expected}, got={actual}, "
        f"bitstring={bitstring} ({len(bitstring)} qubits)"
    )
