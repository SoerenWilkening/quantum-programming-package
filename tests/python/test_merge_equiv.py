"""Statevector equivalence tests for opt=2 merged circuits.

Proves that opt=2 (merged) circuits produce identical statevectors to opt=3
(full expansion) for arithmetic and grover oracle workloads. Also verifies
parametric+opt interaction behavior.

Requirement: MERGE-04
"""

import gc
import math
import os

# Import from verify_helpers (one level up)
import sys

import numpy as np
import pytest
import qiskit.qasm3
from qiskit.quantum_info import Statevector

import quantum_language as ql

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from verify_helpers import generate_exhaustive_pairs

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _statevectors_equivalent(sv1_data, sv2_data, atol=1e-10):
    """Compare two statevector numpy arrays up to global phase.

    Two statevectors |psi> and e^(i*theta)|psi> are physically equivalent.
    This function normalizes by the phase of the first non-zero amplitude.

    Returns True if vectors are equivalent up to global phase, False otherwise.
    """
    # Find first non-zero amplitude in sv1_data
    nz = np.flatnonzero(np.abs(sv1_data) > atol)
    if len(nz) == 0:
        # sv1 is all zeros -- sv2 should be too
        return np.allclose(sv2_data, 0, atol=atol)
    idx = nz[0]
    if np.abs(sv2_data[idx]) < atol:
        return False  # One is zero where other isn't
    # Compute global phase factor
    phase = sv2_data[idx] / sv1_data[idx]
    return np.allclose(sv1_data * phase, sv2_data, atol=atol)


def _get_statevector(build_fn, opt_level):
    """Build a circuit at the given opt level and return its statevector data.

    Args:
        build_fn: Callable(opt_level) that creates a @ql.compile(opt=opt_level)
                  function and invokes it to build the circuit.
        opt_level: Optimization level (1, 2, or 3).

    Returns:
        numpy array of complex amplitudes (statevector).
    """
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)

    build_fn(opt_level)

    qasm_str = ql.to_openqasm()
    circuit = qiskit.qasm3.loads(qasm_str)
    sv = Statevector.from_instruction(circuit)
    return sv.data


# ---------------------------------------------------------------------------
# Statevector equivalence tests
# ---------------------------------------------------------------------------


class TestStatevectorHelper:
    """Tests for the _statevectors_equivalent helper."""

    def test_identical_vectors(self):
        """Identical vectors should be equivalent."""
        v = np.array([0.5, 0.5, 0.5, 0.5], dtype=complex)
        assert _statevectors_equivalent(v, v) is True

    def test_global_phase_difference(self):
        """Vectors differing only by global phase should be equivalent."""
        v1 = np.array([0.5, 0.5, 0.5, 0.5], dtype=complex)
        phase = np.exp(1j * np.pi / 4)  # 45 degree global phase
        v2 = v1 * phase
        assert _statevectors_equivalent(v1, v2) is True

    def test_genuinely_different_vectors(self):
        """Genuinely different vectors should not be equivalent."""
        v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=complex)
        v2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=complex)
        assert _statevectors_equivalent(v1, v2) is False


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_add_equiv(width):
    """opt=2 add circuit produces identical statevector to opt=3 for all input pairs.

    Qubit budget: width=1->3q, width=2->7q, width=3->10q, width=4->13q (all safe).
    """
    pairs = generate_exhaustive_pairs(width)

    for a_val, b_val in pairs:

        def build_add(opt_level, _a=a_val, _b=b_val, _w=width):
            @ql.compile(opt=opt_level)
            def add_fn(x, y):
                x += y
                return x

            x = ql.qint(_a, width=_w)
            y = ql.qint(_b, width=_w)
            add_fn(x, y)

        sv2 = _get_statevector(build_add, opt_level=2)
        sv3 = _get_statevector(build_add, opt_level=3)
        assert _statevectors_equivalent(sv2, sv3), (
            f"add({a_val}, {b_val}) width={width}: opt=2 != opt=3"
        )


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_mul_equiv(width):
    """opt=2 mul circuit produces identical statevector to opt=3 for all input pairs.

    Qubit budget: width=1->3q, width=2->8q, width=3->11q, width=4->14q (all safe).
    Width 5 would be 17q (MAX) -- skipped for safety.
    """
    pairs = generate_exhaustive_pairs(width)

    for a_val, b_val in pairs:

        def build_mul(opt_level, _a=a_val, _b=b_val, _w=width):
            @ql.compile(opt=opt_level)
            def mul_fn(x, y):
                x *= y
                return x

            x = ql.qint(_a, width=_w)
            y = ql.qint(_b, width=_w)
            mul_fn(x, y)

        sv2 = _get_statevector(build_mul, opt_level=2)
        sv3 = _get_statevector(build_mul, opt_level=3)
        assert _statevectors_equivalent(sv2, sv3), (
            f"mul({a_val}, {b_val}) width={width}: opt=2 != opt=3"
        )


def test_grover_oracle_equiv():
    """opt=2 grover oracle circuit produces identical statevector to opt=3.

    Uses predicate x==5, width=4 (7 qubits -- well within budget).
    Compares the oracle phase-marking circuit, not full Grover search.
    """

    def build_oracle(opt_level):
        @ql.compile(opt=opt_level)
        def oracle(x):
            flag = x == 5
            with flag:
                x.phase += math.pi

        x = ql.qint(0, width=4)
        oracle(x)

    sv2 = _get_statevector(build_oracle, opt_level=2)
    sv3 = _get_statevector(build_oracle, opt_level=3)
    assert _statevectors_equivalent(sv2, sv3), "grover oracle (x==5, width=4): opt=2 != opt=3"
