"""Modulo verification tests (VARITH-04).

Tests qint % int (classical divisor modulo) through the full pipeline:
Python quantum_language API -> C backend circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check.

Exhaustive at widths 1-3, sampled at width 4. Modulo by zero is skipped per design.

Result extraction: Uses allocated_start from the remainder qint object to determine
physical qubit positions. In the Qiskit MSB-first bitstring of length n,
physical qubit i maps to bitstring position n-1-i.

Phase 91: All BUG-DIV-02 / BUG-MOD-REDUCE xfail markers removed. C-level restoring
divmod fixes all previously-failing cases.
"""

import random
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------
def _run_mod(width, a_val, divisor):
    """Run modulo through full pipeline, return (actual_remainder, total_qubits, bitstring)."""
    ql.circuit()
    a = ql.qint(a_val, width=width)
    r = a % divisor
    result_start = r.allocated_start
    result_width = r.width
    qasm_str = ql.to_openqasm()

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="matrix_product_state", max_parallel_threads=4)
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    n = len(bitstring)
    # Qiskit bitstring: position i = qubit (N-1-i)
    msb_pos = n - result_start - result_width
    lsb_pos = n - 1 - result_start
    remainder_bits = bitstring[msb_pos : lsb_pos + 1]
    actual = int(remainder_bits, 2)
    return actual, n, bitstring


# ---------------------------------------------------------------------------
# Test data generation
# ---------------------------------------------------------------------------
def _exhaustive_mod_cases():
    """Generate (width, a, divisor) for widths 1-3, divisor in [1, 2^width)."""
    cases = []
    for width in [1, 2, 3]:
        for a_val in range(1 << width):
            for divisor in range(1, 1 << width):
                cases.append((width, a_val, divisor))
    return cases


def _sampled_mod_cases():
    """Generate ~30 (width, a, divisor) for width 4 with deterministic seed."""
    width = 4
    max_val = (1 << width) - 1
    pairs = set()
    # Edge cases
    for a_val in [0, 1, max_val - 1, max_val]:
        for divisor in [1, 2, max_val - 1, max_val]:
            pairs.add((a_val, divisor))
    # Random fill to ~30
    rng = random.Random(42)
    while len(pairs) < 30:
        a_val = rng.randint(0, max_val)
        divisor = rng.randint(1, max_val)
        pairs.add((a_val, divisor))
    return [(width, a, d) for a, d in sorted(pairs)]


EXHAUSTIVE_MOD = _exhaustive_mod_cases()
SAMPLED_MOD = _sampled_mod_cases()


# ---------------------------------------------------------------------------
# Parametrized tests
# Phase 91: All xfail markers removed -- C-level divmod fixes all cases.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("width,a,divisor", EXHAUSTIVE_MOD, ids=lambda *args: None)
def test_mod_exhaustive(width, a, divisor):
    """Modulo: qint(a) % divisor at widths 1-3 (exhaustive)."""
    expected = a % divisor
    actual, _n, _bs = _run_mod(width, a, divisor)
    assert actual == expected, format_failure_message("mod", [a, divisor], width, expected, actual)


@pytest.mark.parametrize("width,a,divisor", SAMPLED_MOD, ids=lambda *args: None)
def test_mod_sampled(width, a, divisor):
    """Modulo: qint(a) % divisor at width 4 (sampled)."""
    expected = a % divisor
    actual, _n, _bs = _run_mod(width, a, divisor)
    assert actual == expected, format_failure_message("mod", [a, divisor], width, expected, actual)
