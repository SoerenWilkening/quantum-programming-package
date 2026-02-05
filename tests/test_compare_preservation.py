"""Operand preservation verification tests for comparison operators (VCMP-03).

Tests that comparison operators do not corrupt their input qint operands.
Each operator has a different qubit layout (especially __gt__ with widened
temporaries), so calibration is performed per operator to determine extraction
positions for operand values in the measurement bitstring.

Pipeline: Python quantum_language API -> C backend -> OpenQASM 3.0 -> Qiskit simulate -> extract operands.

Operator implementation summary:
- eq QQ: subtract-add-back pattern (self -= other, check ==0, self += other)
- ne QQ: delegates to NOT(eq)
- lt QQ: subtract-add-back on self (self -= other, check MSB, self += other)
- gt QQ: creates widened (w+1) temporaries, does NOT modify originals
- le QQ: delegates to NOT(gt)
- ge QQ: delegates to NOT(lt)
- CQ variants: eq uses C-level CQ_equal_width; lt uses subtract-add-back;
  gt/le/ge/ne delegate to QQ paths via temp qint creation
"""

import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")

# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------

QL_OPS_QQ = {
    "eq": lambda qa, qb: qa == qb,
    "ne": lambda qa, qb: qa != qb,
    "lt": lambda qa, qb: qa < qb,
    "gt": lambda qa, qb: qa > qb,
    "le": lambda qa, qb: qa <= qb,
    "ge": lambda qa, qb: qa >= qb,
}

QL_OPS_CQ = {
    "eq": lambda qa, b: qa == b,
    "ne": lambda qa, b: qa != b,
    "lt": lambda qa, b: qa < b,
    "gt": lambda qa, b: qa > b,
    "le": lambda qa, b: qa <= b,
    "ge": lambda qa, b: qa >= b,
}


def _run_comparison_pipeline(width, a, b, op_name, variant="qq"):
    """Run comparison and return full bitstring for analysis.

    Returns (bool_result, bitstring, num_bits).
    """
    ql.circuit()
    qa = ql.qint(a, width=width)

    if variant == "qq":
        qb = ql.qint(b, width=width)
        _result = QL_OPS_QQ[op_name](qa, qb)
    else:
        _result = QL_OPS_CQ[op_name](qa, b)

    qasm_str = ql.to_openqasm()
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    # Boolean result is at bitstring[0] (highest qubit index = last allocated = leftmost)
    bool_result = int(bitstring[0], 2)
    return bool_result, bitstring, len(bitstring)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def _calibrate_extraction(width, a, b, op_name, variant="qq"):
    """Empirically determine operand extraction positions in the bitstring.

    Uses known values (a, b) to find where they appear in the measurement bitstring.
    For QQ variant, finds both a and b positions.
    For CQ variant, finds only a position (b is classical, not in circuit).

    Returns dict with keys: 'a_start', 'a_end', 'b_start', 'b_end'
    (b keys only for QQ variant).
    Returns None if calibration fails.
    """
    bool_result, bitstring, n = _run_comparison_pipeline(width, a, b, op_name, variant)

    if variant == "qq":
        # Try standard positions first: a at rightmost, b next
        a_start_std = n - width
        a_end_std = n
        b_start_std = n - 2 * width
        b_end_std = n - width

        a_val = int(bitstring[a_start_std:a_end_std], 2)
        b_val = int(bitstring[b_start_std:b_end_std], 2)

        if a_val == a and b_val == b:
            return {
                "a_start": a_start_std,
                "a_end": a_end_std,
                "b_start": b_start_std,
                "b_end": b_end_std,
            }

        # Search for operand values in all possible windows
        # Use distinct a != b to avoid ambiguity
        a_positions = []
        b_positions = []
        for start in range(n - width + 1):
            end = start + width
            val = int(bitstring[start:end], 2)
            if val == a:
                a_positions.append((start, end))
            if val == b:
                b_positions.append((start, end))

        # Find non-overlapping pair
        for a_s, a_e in a_positions:
            for b_s, b_e in b_positions:
                # Non-overlapping check
                if a_e <= b_s or b_e <= a_s:
                    return {
                        "a_start": a_s,
                        "a_end": a_e,
                        "b_start": b_s,
                        "b_end": b_e,
                    }

        return None  # Could not find operand positions

    else:
        # CQ variant: only a is a quantum register
        # Try standard position: a at rightmost
        a_start_std = n - width
        a_end_std = n
        a_val = int(bitstring[a_start_std:a_end_std], 2)

        if a_val == a:
            return {"a_start": a_start_std, "a_end": a_end_std}

        # Search all windows
        for start in range(n - width + 1):
            end = start + width
            val = int(bitstring[start:end], 2)
            if val == a:
                return {"a_start": start, "a_end": end}

        return None


# ---------------------------------------------------------------------------
# Module-scoped calibration fixtures
# ---------------------------------------------------------------------------

# Calibration values: distinct and non-zero to avoid ambiguity
CALIB_WIDTH = 3
CALIB_A = 3
CALIB_B = 5

OPERATORS = ["eq", "ne", "lt", "gt", "le", "ge"]

# Representative test pairs (width=3, range 0..7)
TEST_PAIRS = [
    (0, 7),
    (7, 0),
    (7, 7),
    (3, 5),
    (5, 3),
    (4, 4),
    (1, 6),
    (2, 3),
]


def _get_calibrations():
    """Run calibration for all operators and variants. Returns nested dict."""
    calibrations = {}
    for op in OPERATORS:
        calibrations[op] = {}
        for variant in ["qq", "cq"]:
            calibrations[op][variant] = _calibrate_extraction(
                CALIB_WIDTH, CALIB_A, CALIB_B, op, variant
            )
    return calibrations


# Module-level calibration (runs once at import time)
_CALIBRATIONS = _get_calibrations()


# ---------------------------------------------------------------------------
# Parametrized preservation tests -- QQ variant
# ---------------------------------------------------------------------------


def _make_qq_params():
    """Generate pytest params for QQ preservation tests."""
    params = []
    for op in OPERATORS:
        calib = _CALIBRATIONS[op]["qq"]
        for a, b in TEST_PAIRS:
            test_id = f"{op}_qq_{a}v{b}"
            if calib is None:
                params.append(
                    pytest.param(
                        op,
                        a,
                        b,
                        calib,
                        id=test_id,
                        marks=pytest.mark.xfail(
                            reason=f"BUG-CMP-PRES-01: Calibration failed for {op} QQ "
                            f"-- operand positions unstable or undetectable",
                            strict=True,
                        ),
                    )
                )
            else:
                params.append(pytest.param(op, a, b, calib, id=test_id))
    return params


@pytest.mark.parametrize("op_name,a,b,calib", _make_qq_params())
def test_qq_preservation(op_name, a, b, calib):
    """Verify both QQ operands are preserved after comparison.

    For each operator, run comparison on (a, b) and extract operand values
    from the bitstring using calibrated positions. Both a and b must be
    unchanged after the comparison.
    """
    if calib is None:
        # xfail marker handles this, but assert to trigger the xfail
        pytest.fail(f"Calibration unavailable for {op_name} QQ")

    _bool_result, bitstring, n = _run_comparison_pipeline(CALIB_WIDTH, a, b, op_name, "qq")

    extracted_a = int(bitstring[calib["a_start"] : calib["a_end"]], 2)
    extracted_b = int(bitstring[calib["b_start"] : calib["b_end"]], 2)

    assert extracted_a == a, (
        f"Operand a corrupted after {op_name} QQ: "
        f"expected={a}, got={extracted_a}, bitstring={bitstring}"
    )
    assert extracted_b == b, (
        f"Operand b corrupted after {op_name} QQ: "
        f"expected={b}, got={extracted_b}, bitstring={bitstring}"
    )


# ---------------------------------------------------------------------------
# Parametrized preservation tests -- CQ variant
# ---------------------------------------------------------------------------


def _make_cq_params():
    """Generate pytest params for CQ preservation tests."""
    params = []
    for op in OPERATORS:
        calib = _CALIBRATIONS[op]["cq"]
        for a, b in TEST_PAIRS:
            test_id = f"{op}_cq_{a}v{b}"
            if calib is None:
                params.append(
                    pytest.param(
                        op,
                        a,
                        b,
                        calib,
                        id=test_id,
                        marks=pytest.mark.xfail(
                            reason=f"BUG-CMP-PRES-02: Calibration failed for {op} CQ "
                            f"-- operand positions unstable or undetectable",
                            strict=True,
                        ),
                    )
                )
            else:
                params.append(pytest.param(op, a, b, calib, id=test_id))
    return params


@pytest.mark.parametrize("op_name,a,b,calib", _make_cq_params())
def test_cq_preservation(op_name, a, b, calib):
    """Verify quantum operand a is preserved after CQ comparison.

    For CQ operators, only operand a is quantum (b is classical int).
    Extract a from the bitstring using calibrated positions and verify
    it is unchanged.
    """
    if calib is None:
        pytest.fail(f"Calibration unavailable for {op_name} CQ")

    _bool_result, bitstring, n = _run_comparison_pipeline(CALIB_WIDTH, a, b, op_name, "cq")

    extracted_a = int(bitstring[calib["a_start"] : calib["a_end"]], 2)

    assert extracted_a == a, (
        f"Operand a corrupted after {op_name} CQ: "
        f"expected={a}, got={extracted_a}, bitstring={bitstring}"
    )


# ---------------------------------------------------------------------------
# Calibration sanity tests (verify calibration itself is correct)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("op_name", OPERATORS)
def test_calibration_qq(op_name):
    """Verify QQ calibration found valid extraction positions."""
    calib = _CALIBRATIONS[op_name]["qq"]
    if calib is None:
        pytest.skip(f"Calibration failed for {op_name} QQ -- tested via preservation tests")
    # Verify calibration with the calibration values themselves
    _bool_result, bitstring, n = _run_comparison_pipeline(
        CALIB_WIDTH, CALIB_A, CALIB_B, op_name, "qq"
    )
    extracted_a = int(bitstring[calib["a_start"] : calib["a_end"]], 2)
    extracted_b = int(bitstring[calib["b_start"] : calib["b_end"]], 2)
    assert extracted_a == CALIB_A, (
        f"Calibration verification failed for {op_name} QQ operand a: "
        f"expected={CALIB_A}, got={extracted_a}"
    )
    assert extracted_b == CALIB_B, (
        f"Calibration verification failed for {op_name} QQ operand b: "
        f"expected={CALIB_B}, got={extracted_b}"
    )


@pytest.mark.parametrize("op_name", OPERATORS)
def test_calibration_cq(op_name):
    """Verify CQ calibration found valid extraction positions."""
    calib = _CALIBRATIONS[op_name]["cq"]
    if calib is None:
        pytest.skip(f"Calibration failed for {op_name} CQ -- tested via preservation tests")
    _bool_result, bitstring, n = _run_comparison_pipeline(
        CALIB_WIDTH, CALIB_A, CALIB_B, op_name, "cq"
    )
    extracted_a = int(bitstring[calib["a_start"] : calib["a_end"]], 2)
    assert extracted_a == CALIB_A, (
        f"Calibration verification failed for {op_name} CQ operand a: "
        f"expected={CALIB_A}, got={extracted_a}"
    )
