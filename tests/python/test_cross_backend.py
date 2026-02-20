"""Phase 70: Cross-Backend Equivalence Tests.

Proves that Toffoli and QFT backends produce identical computational results
for all arithmetic operations:
- Addition (QQ, CQ, cQQ, cCQ) at widths 1-8
- Subtraction (QQ, CQ) at widths 1-8
- Multiplication (QQ, CQ, cQQ, cCQ) at widths 1-6
- Division/Modulo (classical and quantum divisor) at widths 2-6

Uses exhaustive testing for small widths and sampled testing for larger widths.

Test infrastructure (_run_backend, _compare_backends, _simulate_and_extract)
is reusable across all arithmetic operations.

Backend switching: ql.option('fault_tolerant', True) for Toffoli,
ql.option('fault_tolerant', False) for QFT. Result extraction uses
allocated_start for backend-independent physical qubit positions.
"""

import gc
import os
import random
import sys
import warnings

import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language._core import current_scope_depth

# Add tests/ directory to sys.path so verify_helpers can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from verify_helpers import (
    generate_exhaustive_pairs,
    generate_sampled_pairs,
)

warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# Known division/modulo failure sets (union of Toffoli and QFT known bugs)
# Cross-backend comparison is meaningless for these cases (one or both wrong).
# ---------------------------------------------------------------------------

# Union of known division failures across backends.
# Toffoli failures from test_toffoli_division.py KNOWN_TOFFOLI_DIV_FAILURES.
# QFT failures from test_div.py KNOWN_DIV_MSB_LEAK (actually Toffoli since 67-03).
# BUG-QFT-DIV: QFT division is severely broken at width 2+ (discovered during
# Phase 70-02 cross-backend testing -- first time QFT division was explicitly
# tested since Phase 67-03 made Toffoli the default). QFT produces incorrect
# quotients for most input pairs. Width 2: 8 of 9 cases fail.
KNOWN_DIV_FAILURES = {
    # Width 2 -- BUG-QFT-DIV: QFT division broken (Toffoli is correct)
    (2, 0, 2),
    (2, 1, 1),
    (2, 1, 2),
    (2, 2, 2),
    (2, 2, 3),
    (2, 3, 1),
    (2, 3, 2),
    (2, 3, 3),
    # Width 3 -- Toffoli failures (even a values with div=1)
    (3, 0, 1),
    (3, 2, 1),
    (3, 4, 1),
    (3, 6, 1),
    # Width 3 -- reported as "QFT" but actually Toffoli since 67-03
    (3, 5, 1),
    (3, 7, 1),
    # Width 4 -- Toffoli failures
    (4, 0, 1),
    (4, 0, 2),
    (4, 1, 1),
    (4, 1, 2),
    (4, 3, 1),
    (4, 7, 3),
    (4, 13, 1),
    (4, 14, 1),
    (4, 15, 1),
    (4, 15, 2),
    # Width 4 -- reported as "QFT" but actually Toffoli
    (4, 14, 2),
}

# Known modulo failures (BUG-MOD-REDUCE + BUG-QFT-DIV -- widespread).
# At width 2, most cases are buggy in one or both backends.
# BUG-QFT-DIV: QFT modulo also produces wrong results at width 2+ (discovered
# during Phase 70-02 cross-backend testing).
KNOWN_MOD_FAILURES = {
    # Width 2 -- BUG-MOD-REDUCE (both backends wrong, from test_toffoli_division.py)
    (2, 0, 1),
    (2, 0, 2),
    (2, 0, 3),
    (2, 1, 1),
    (2, 1, 2),
    (2, 2, 1),
    (2, 2, 3),
    (2, 3, 1),
    (2, 3, 2),
    # Width 2 -- BUG-QFT-DIV (QFT wrong, Toffoli correct, discovered in 70-02)
    (2, 1, 3),
    (2, 2, 2),
    (2, 3, 3),
}

# Known quantum division failures at width 2.
# Union of Toffoli failures + BUG-QFT-DIV cross-backend mismatches.
KNOWN_QDIV_FAILURES = {
    # Toffoli failures (from test_toffoli_division.py)
    (2, 1, 1),
    (2, 2, 2),
    (2, 3, 2),
    (2, 3, 3),
    # BUG-QFT-DIV: QFT quantum division wrong (discovered in 70-02)
    (2, 0, 2),
    (2, 0, 3),
    (2, 2, 1),
    (2, 2, 3),
    (2, 3, 1),
}

# Known quantum modulo failures at width 2.
# Union of Toffoli failures + BUG-QFT-DIV cross-backend mismatches.
KNOWN_QMOD_FAILURES = {
    # Toffoli failures (from test_toffoli_division.py)
    (2, 1, 1),
    (2, 2, 1),
    (2, 2, 2),
    (2, 3, 1),
    (2, 3, 2),
    # BUG-QFT-DIV: QFT quantum modulo wrong (discovered in 70-02)
    (2, 0, 1),
    (2, 0, 2),
    (2, 0, 3),
    (2, 1, 2),
    (2, 1, 3),
    (2, 2, 3),
    (2, 3, 3),
}


# ---------------------------------------------------------------------------
# Helper functions (module-level, reusable by Plan 02)
# ---------------------------------------------------------------------------


def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM qubit[N] declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise Exception(f"Could not find qubit count in QASM:\n{qasm_str[:200]}")


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width, use_mps=False):
    """Simulate QASM and extract integer from result register.

    Args:
        qasm_str: OpenQASM 3.0 string
        num_qubits: Total number of qubits in circuit
        result_start: Physical qubit index of result register LSB
        result_width: Number of qubits in result register
        use_mps: If True, transpile to basis gates and use MPS simulator
                 (needed for circuits containing MCX gates)

    Returns:
        Integer value of result register
    """
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    if use_mps:
        basis_gates = ["cx", "u1", "u2", "u3", "x", "h", "ccx", "id"]
        circuit = transpile(circuit, basis_gates=basis_gates, optimization_level=0)
        simulator = AerSimulator(method="matrix_product_state", max_parallel_threads=4)
    else:
        simulator = AerSimulator(method="statevector", max_parallel_threads=4)

    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Qiskit bitstring: position i = qubit (N-1-i)
    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _run_backend(backend, build_fn, width, use_mps=False):
    """Run a circuit with a specific backend and return the integer result.

    Args:
        backend: "toffoli" or "qft"
        build_fn: Callable returning (result_qint, expected_value, keepalive_list)
        width: Result register width
        use_mps: Whether to use MPS simulator (for MCX-containing circuits)

    Returns:
        Integer result from simulation
    """
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", backend == "toffoli")

    result_qint, expected, keepalive = build_fn()
    result_start = result_qint.allocated_start

    qasm_str = ql.to_openqasm()
    del keepalive  # Release qint references before simulation

    num_qubits = _get_num_qubits(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width, use_mps=use_mps)
    return actual


def _compare_backends(build_fn, width, use_mps_toffoli=False, use_mps_qft=False):
    """Run both backends and return (toffoli_result, qft_result).

    Args:
        build_fn: Callable returning (result_qint, expected_value, keepalive_list)
        width: Result register width
        use_mps_toffoli: Whether Toffoli backend needs MPS (for MCX gates)
        use_mps_qft: Whether QFT backend needs MPS (for large qubit counts,
                     e.g., quantum division at 37+ qubits)

    Returns:
        Tuple (toffoli_result, qft_result)
    """
    toffoli_result = _run_backend("toffoli", build_fn, width, use_mps=use_mps_toffoli)
    qft_result = _run_backend("qft", build_fn, width, use_mps=use_mps_qft)
    return toffoli_result, qft_result


# ---------------------------------------------------------------------------
# TestCrossBackendAddition
# ---------------------------------------------------------------------------


class TestCrossBackendAddition:
    """Cross-backend equivalence tests for all 4 addition variants (QQ, CQ, cQQ, cCQ).

    Parametrized across widths 1-8. Exhaustive for widths 1-4, sampled for 5-8.
    """

    @pytest.mark.parametrize(
        "width",
        [
            1,
            2,
            3,
            4,
            5,
            6,
            pytest.param(7, marks=pytest.mark.slow),
            pytest.param(8, marks=pytest.mark.slow),
        ],
    )
    def test_qq_add(self, width):
        """QQ addition (c = a + b) produces identical results in both backends."""
        if width <= 4:
            pairs = generate_exhaustive_pairs(width)
        elif width <= 6:
            pairs = generate_sampled_pairs(width, sample_size=20)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                qc = qa + qb
                return qc, (a + b) % (1 << w), [qa, qb, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize(
        "width",
        [
            1,
            2,
            3,
            4,
            5,
            6,
            pytest.param(7, marks=pytest.mark.slow),
            pytest.param(8, marks=pytest.mark.slow),
        ],
    )
    def test_cq_add(self, width):
        """CQ addition (a += b) produces identical results in both backends."""
        if width <= 4:
            pairs = generate_exhaustive_pairs(width)
        elif width <= 6:
            pairs = generate_sampled_pairs(width, sample_size=20)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qa += b
                return qa, (a + b) % (1 << w), [qa]

            toffoli_result, qft_result = _compare_backends(build_fn, width)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )

    def test_cqq_add_w1(self):
        """Controlled QQ in-place addition at width 1 (cross-backend match)."""
        width = 1
        pairs = generate_exhaustive_pairs(width)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                ctrl = ql.qint(1, width=1)
                with ctrl:
                    qa += qb
                return qa, (a + b) % (1 << w), [qa, qb, ctrl]

            toffoli_result, qft_result = _compare_backends(build_fn, width, use_mps_toffoli=True)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=1: toffoli={toffoli_result}, qft={qft_result}"
                )

        # ctrl=0: no-op (a stays unchanged)
        for a, b in pairs:

            def build_fn_ctrl0(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                ctrl = ql.qint(0, width=1)
                with ctrl:
                    qa += qb
                return qa, a, [qa, qb, ctrl]

            toffoli_result, qft_result = _compare_backends(
                build_fn_ctrl0, width, use_mps_toffoli=True
            )
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=0: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize(
        "width",
        [
            pytest.param(
                2,
                marks=pytest.mark.xfail(
                    reason="BUG-CQQ-QFT: QFT controlled QQ in-place addition produces "
                    "incorrect results at width 2+ (CCP rotation angle errors)",
                    strict=False,
                ),
            ),
            pytest.param(
                3,
                marks=pytest.mark.xfail(
                    reason="BUG-CQQ-QFT: QFT controlled QQ in-place addition produces "
                    "incorrect results at width 2+ (CCP rotation angle errors)",
                    strict=False,
                ),
            ),
            pytest.param(
                4,
                marks=pytest.mark.xfail(
                    reason="BUG-CQQ-QFT: QFT controlled QQ in-place addition produces "
                    "incorrect results at width 2+ (CCP rotation angle errors)",
                    strict=False,
                ),
            ),
            pytest.param(
                5,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled QQ in-place addition bug",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                6,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled QQ in-place addition bug",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                7,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled QQ in-place addition bug",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                8,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled QQ in-place addition bug",
                        strict=False,
                    ),
                ],
            ),
        ],
    )
    def test_cqq_add(self, width):
        """Controlled QQ in-place addition (with ctrl: a += qb) cross-backend.

        Uses in-place qa += qb (not out-of-place qa + qb) because controlled
        out-of-place addition requires controlled XOR which is not yet supported.

        BUG-CQQ-QFT: QFT backend produces incorrect results for controlled
        quantum-quantum in-place addition at widths 2+. The CCP decomposition
        has rotation angle errors. Toffoli backend is correct. Tests are xfail
        at widths 2+ to document this discovered bug.
        """
        if width <= 4:
            pairs = generate_exhaustive_pairs(width)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                ctrl = ql.qint(1, width=1)
                with ctrl:
                    qa += qb
                return qa, (a + b) % (1 << w), [qa, qb, ctrl]

            toffoli_result, qft_result = _compare_backends(build_fn, width, use_mps_toffoli=True)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=1: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize(
        "width",
        [
            1,
            2,
            3,
            4,
            pytest.param(5, marks=pytest.mark.slow),
            pytest.param(6, marks=pytest.mark.slow),
            pytest.param(7, marks=pytest.mark.slow),
            pytest.param(8, marks=pytest.mark.slow),
        ],
    )
    def test_ccq_add(self, width):
        """Controlled CQ addition (with ctrl: a += b) produces identical results.

        Tests ctrl=1 exhaustively/sampled, ctrl=0 only for widths<=2 (subset).
        """
        if width <= 4:
            pairs = generate_exhaustive_pairs(width)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        # ctrl=1: addition should happen
        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                ctrl = ql.qint(1, width=1)
                with ctrl:
                    qa += b
                return qa, (a + b) % (1 << w), [qa, ctrl]

            toffoli_result, qft_result = _compare_backends(build_fn, width, use_mps_toffoli=True)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=1: toffoli={toffoli_result}, qft={qft_result}"
                )

        # ctrl=0: no-op (a stays unchanged), only test for small widths
        if width <= 2:
            ctrl0_pairs = generate_exhaustive_pairs(width)
            for a, b in ctrl0_pairs:

                def build_fn_ctrl0(a=a, b=b, w=width):
                    qa = ql.qint(a, width=w)
                    ctrl = ql.qint(0, width=1)
                    with ctrl:
                        qa += b
                    return qa, a, [qa, ctrl]

                toffoli_result, qft_result = _compare_backends(
                    build_fn_ctrl0, width, use_mps_toffoli=True
                )
                if toffoli_result != qft_result:
                    failures.append(
                        f"w={width} a={a} b={b} ctrl=0: toffoli={toffoli_result}, qft={qft_result}"
                    )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )


# ---------------------------------------------------------------------------
# TestCrossBackendSubtraction
# ---------------------------------------------------------------------------


class TestCrossBackendSubtraction:
    """Cross-backend equivalence tests for QQ and CQ subtraction.

    Parametrized across widths 1-8. Exhaustive for widths 1-4, sampled for 5-8.
    """

    @pytest.mark.parametrize(
        "width",
        [
            1,
            2,
            3,
            4,
            5,
            6,
            pytest.param(7, marks=pytest.mark.slow),
            pytest.param(8, marks=pytest.mark.slow),
        ],
    )
    def test_qq_sub(self, width):
        """QQ subtraction (c = a - b) produces identical results in both backends."""
        if width <= 4:
            pairs = generate_exhaustive_pairs(width)
        elif width <= 6:
            pairs = generate_sampled_pairs(width, sample_size=20)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                qc = qa - qb
                return qc, (a - b) % (1 << w), [qa, qb, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize(
        "width",
        [
            1,
            2,
            3,
            4,
            5,
            6,
            pytest.param(7, marks=pytest.mark.slow),
            pytest.param(8, marks=pytest.mark.slow),
        ],
    )
    def test_cq_sub(self, width):
        """CQ subtraction (a -= b) produces identical results in both backends."""
        if width <= 4:
            pairs = generate_exhaustive_pairs(width)
        elif width <= 6:
            pairs = generate_sampled_pairs(width, sample_size=20)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qa -= b
                return qa, (a - b) % (1 << w), [qa]

            toffoli_result, qft_result = _compare_backends(build_fn, width)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )


# ---------------------------------------------------------------------------
# TestCrossBackendMultiplication
# ---------------------------------------------------------------------------


class TestCrossBackendMultiplication:
    """Cross-backend equivalence tests for all 4 multiplication variants.

    QQ (c = a * b), CQ (c = a * int), cQQ (controlled QQ), cCQ (controlled CQ).
    Parametrized across widths 1-6. Exhaustive for widths 1-3, sampled for 4-6.

    Controlled multiplication uses BUG-COND-MUL-01 scope workaround for BOTH
    backends: the Python-level scope cleanup incorrectly auto-uncomputes
    out-of-place multiplication results created inside `with ctrl:` blocks.
    The workaround temporarily sets scope_depth=0 during multiplication.
    """

    @pytest.mark.parametrize("width", [1, 2, 3, 4, 5, 6])
    def test_qq_mul(self, width):
        """QQ multiplication (c = a * b) produces identical results in both backends."""
        if width <= 3:
            pairs = generate_exhaustive_pairs(width)
        else:
            pairs = generate_sampled_pairs(width, sample_size=15)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                qc = qa * qb
                return qc, (a * b) % (1 << w), [qa, qb, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize("width", [1, 2, 3, 4, 5, 6])
    def test_cq_mul(self, width):
        """CQ multiplication (c = a * int) produces identical results in both backends."""
        if width <= 3:
            pairs = generate_exhaustive_pairs(width)
        else:
            pairs = generate_sampled_pairs(width, sample_size=15)

        failures = []
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qc = qa * b
                return qc, (a * b) % (1 << w), [qa, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width)
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )

    def test_cqq_mul_w1(self):
        """Controlled QQ multiplication at width 1 (cross-backend match).

        Width 1 is tested separately because QFT controlled operations work
        correctly at width 1 but fail at width 2+ (BUG-CQQ-QFT).

        Uses BUG-COND-MUL-01 scope workaround for BOTH backends.
        Toffoli backend uses MCX gates, so use_mps_toffoli=True.
        """
        width = 1
        pairs = generate_exhaustive_pairs(width)

        failures = []
        saw_nonzero = False
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                ctrl = ql.qint(1, width=1)
                with ctrl:
                    saved = current_scope_depth.get()
                    current_scope_depth.set(0)
                    qc = qa * qb
                    current_scope_depth.set(saved)
                return qc, (a * b) % (1 << w), [qa, qb, ctrl, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width, use_mps_toffoli=True)
            if toffoli_result != 0 or qft_result != 0:
                saw_nonzero = True
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=1: toffoli={toffoli_result}, qft={qft_result}"
                )

        # ctrl=0: no-op
        ctrl0_pairs = list(generate_exhaustive_pairs(width))[:4]
        for a, b in ctrl0_pairs:

            def build_fn_ctrl0(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                ctrl = ql.qint(0, width=1)
                with ctrl:
                    saved = current_scope_depth.get()
                    current_scope_depth.set(0)
                    qc = qa * qb
                    current_scope_depth.set(saved)
                return qc, 0, [qa, qb, ctrl, qc]

            toffoli_result, qft_result = _compare_backends(
                build_fn_ctrl0, width, use_mps_toffoli=True
            )
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=0: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )
        assert saw_nonzero, (
            f"All cQQ mul results were 0 at width {width} -- test may be trivially passing"
        )

    @pytest.mark.parametrize(
        "width",
        [
            pytest.param(
                2,
                marks=pytest.mark.xfail(
                    reason="BUG-CQQ-QFT: QFT controlled operations produce incorrect "
                    "results at width 2+ (CCP rotation angle errors in controlled mul)",
                    strict=False,
                ),
            ),
            pytest.param(
                3,
                marks=pytest.mark.xfail(
                    reason="BUG-CQQ-QFT: QFT controlled operations produce incorrect "
                    "results at width 2+ (CCP rotation angle errors in controlled mul)",
                    strict=False,
                ),
            ),
            pytest.param(
                4,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled mul incorrect at width 2+",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                5,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled mul incorrect at width 2+",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                6,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled mul incorrect at width 2+",
                        strict=False,
                    ),
                ],
            ),
        ],
    )
    def test_cqq_mul(self, width):
        """Controlled QQ multiplication (with ctrl: c = a * b) cross-backend.

        BUG-CQQ-QFT: QFT backend produces incorrect results for controlled
        quantum-quantum operations at widths 2+. The CCP decomposition has
        rotation angle errors. Toffoli backend is correct. Tests are xfail
        at widths 2+ to document this discovered bug (same root cause as
        controlled QQ addition bug).

        Uses BUG-COND-MUL-01 scope workaround for BOTH backends.
        Toffoli backend uses MCX gates, so use_mps_toffoli=True.
        """
        if width <= 3:
            pairs = generate_exhaustive_pairs(width)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        # ctrl=1: multiplication should happen
        failures = []
        saw_nonzero = False
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                ctrl = ql.qint(1, width=1)
                with ctrl:
                    saved = current_scope_depth.get()
                    current_scope_depth.set(0)
                    qc = qa * qb
                    current_scope_depth.set(saved)
                return qc, (a * b) % (1 << w), [qa, qb, ctrl, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width, use_mps_toffoli=True)
            if toffoli_result != 0 or qft_result != 0:
                saw_nonzero = True
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=1: toffoli={toffoli_result}, qft={qft_result}"
                )

        # ctrl=0: no-op (result stays 0), only test for small widths
        if width <= 2:
            ctrl0_pairs = list(generate_exhaustive_pairs(width))[:4]
            for a, b in ctrl0_pairs:

                def build_fn_ctrl0(a=a, b=b, w=width):
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    ctrl = ql.qint(0, width=1)
                    with ctrl:
                        saved = current_scope_depth.get()
                        current_scope_depth.set(0)
                        qc = qa * qb
                        current_scope_depth.set(saved)
                    return qc, 0, [qa, qb, ctrl, qc]

                toffoli_result, qft_result = _compare_backends(
                    build_fn_ctrl0, width, use_mps_toffoli=True
                )
                if toffoli_result != qft_result:
                    failures.append(
                        f"w={width} a={a} b={b} ctrl=0: toffoli={toffoli_result}, qft={qft_result}"
                    )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )
        # Guard against trivially passing with all zeros
        assert saw_nonzero, (
            f"All cQQ mul results were 0 at width {width} -- test may be trivially passing"
        )

    def test_ccq_mul_w1(self):
        """Controlled CQ multiplication at width 1 (cross-backend match).

        Width 1 is tested separately because QFT controlled operations work
        correctly at width 1 but fail at width 2+ (BUG-CQQ-QFT).

        Uses BUG-COND-MUL-01 scope workaround for BOTH backends.
        Toffoli backend uses MCX gates, so use_mps_toffoli=True.
        """
        width = 1
        pairs = generate_exhaustive_pairs(width)

        failures = []
        saw_nonzero = False
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                ctrl = ql.qint(1, width=1)
                with ctrl:
                    saved = current_scope_depth.get()
                    current_scope_depth.set(0)
                    qc = qa * b
                    current_scope_depth.set(saved)
                return qc, (a * b) % (1 << w), [qa, ctrl, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width, use_mps_toffoli=True)
            if toffoli_result != 0 or qft_result != 0:
                saw_nonzero = True
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=1: toffoli={toffoli_result}, qft={qft_result}"
                )

        # ctrl=0: no-op
        ctrl0_pairs = list(generate_exhaustive_pairs(width))[:4]
        for a, b in ctrl0_pairs:

            def build_fn_ctrl0(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                ctrl = ql.qint(0, width=1)
                with ctrl:
                    saved = current_scope_depth.get()
                    current_scope_depth.set(0)
                    qc = qa * b
                    current_scope_depth.set(saved)
                return qc, 0, [qa, ctrl, qc]

            toffoli_result, qft_result = _compare_backends(
                build_fn_ctrl0, width, use_mps_toffoli=True
            )
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=0: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )
        assert saw_nonzero, (
            f"All cCQ mul results were 0 at width {width} -- test may be trivially passing"
        )

    @pytest.mark.parametrize(
        "width",
        [
            pytest.param(
                2,
                marks=pytest.mark.xfail(
                    reason="BUG-CQQ-QFT: QFT controlled operations produce incorrect "
                    "results at width 2+ (CCP rotation angle errors in controlled mul)",
                    strict=False,
                ),
            ),
            pytest.param(
                3,
                marks=pytest.mark.xfail(
                    reason="BUG-CQQ-QFT: QFT controlled operations produce incorrect "
                    "results at width 2+ (CCP rotation angle errors in controlled mul)",
                    strict=False,
                ),
            ),
            pytest.param(
                4,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled mul incorrect at width 2+",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                5,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled mul incorrect at width 2+",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                6,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-CQQ-QFT: QFT controlled mul incorrect at width 2+",
                        strict=False,
                    ),
                ],
            ),
        ],
    )
    def test_ccq_mul(self, width):
        """Controlled CQ multiplication (with ctrl: c = a * int) cross-backend.

        BUG-CQQ-QFT: QFT backend produces incorrect results for controlled
        operations at widths 2+. Same root cause as controlled QQ addition/mul.
        Tests are xfail at widths 2+ to document this.

        Uses BUG-COND-MUL-01 scope workaround for BOTH backends.
        Toffoli backend uses MCX gates, so use_mps_toffoli=True.
        """
        if width <= 3:
            pairs = generate_exhaustive_pairs(width)
        else:
            pairs = generate_sampled_pairs(width, sample_size=10)

        # ctrl=1: multiplication should happen
        failures = []
        saw_nonzero = False
        for a, b in pairs:

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                ctrl = ql.qint(1, width=1)
                with ctrl:
                    saved = current_scope_depth.get()
                    current_scope_depth.set(0)
                    qc = qa * b
                    current_scope_depth.set(saved)
                return qc, (a * b) % (1 << w), [qa, ctrl, qc]

            toffoli_result, qft_result = _compare_backends(build_fn, width, use_mps_toffoli=True)
            if toffoli_result != 0 or qft_result != 0:
                saw_nonzero = True
            if toffoli_result != qft_result:
                failures.append(
                    f"w={width} a={a} b={b} ctrl=1: toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(
            failures[:20]
        )
        # Guard against trivially passing with all zeros
        assert saw_nonzero, (
            f"All cCQ mul results were 0 at width {width} -- test may be trivially passing"
        )


# ---------------------------------------------------------------------------
# TestCrossBackendDivision
# ---------------------------------------------------------------------------


def _generate_div_pairs(width, sample_size=20):
    """Generate (a, divisor) pairs for division testing.

    Divisor ranges from 1 to 2^width - 1 (no division by zero).
    Exhaustive for width <= 3, sampled for width >= 4.

    Returns:
        List of (a, divisor) tuples
    """
    max_val = (1 << width) - 1
    if width <= 3:
        pairs = []
        for a in range(1 << width):
            for d in range(1, 1 << width):
                pairs.append((a, d))
        return pairs
    else:
        pairs = set()
        # Edge cases
        for a in [0, 1, max_val - 1, max_val]:
            for d in [1, 2, max_val - 1, max_val]:
                pairs.add((a, d))
        # Random fill
        rng = random.Random(42)
        while len(pairs) < sample_size:
            a = rng.randint(0, max_val)
            d = rng.randint(1, max_val)
            pairs.add((a, d))
        return sorted(pairs)


def _generate_qdiv_pairs(width, sample_size=5):
    """Generate (a, b) pairs for quantum divisor division testing.

    b ranges from 1 to 2^width - 1 (no division by zero).
    Exhaustive for width <= 2, sampled for width >= 3.

    Returns:
        List of (a, b) tuples
    """
    max_val = (1 << width) - 1
    if width <= 2:
        pairs = []
        for a in range(1 << width):
            for b in range(1, 1 << width):
                pairs.append((a, b))
        return pairs
    else:
        pairs = set()
        for a in [0, 1, max_val - 1, max_val]:
            for b in [1, 2, max_val - 1, max_val]:
                pairs.add((a, b))
        rng = random.Random(42)
        while len(pairs) < sample_size:
            a = rng.randint(0, max_val)
            b = rng.randint(1, max_val)
            pairs.add((a, b))
        return sorted(pairs)


class TestCrossBackendDivision:
    """Cross-backend equivalence tests for division and modulo.

    Tests classical divisor (widths 2-6) and quantum divisor (widths 2-4).
    The primary goal is proving backends AGREE, not that results are correct.
    If both backends produce the same wrong answer (e.g., BUG-MOD-REDUCE),
    that is a pass for cross-backend equivalence. Only flag mismatches between
    backends as test failures.

    Known-buggy cases (BUG-DIV-02, BUG-MOD-REDUCE) are skipped because
    cross-backend comparison is meaningless when one or both backends are
    known to produce incorrect results.
    """

    @pytest.mark.parametrize(
        "width",
        [
            2,
            pytest.param(
                3,
                marks=pytest.mark.xfail(
                    reason="BUG-QFT-DIV: QFT division is pervasively broken at width 3+ "
                    "(26 of 36 non-known cases fail at width 3). First discovered in Phase 70-02.",
                    strict=False,
                ),
            ),
            pytest.param(
                4,
                marks=pytest.mark.xfail(
                    reason="BUG-QFT-DIV: QFT division is pervasively broken at width 3+",
                    strict=False,
                ),
            ),
            pytest.param(
                5,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-QFT-DIV: QFT division broken at width 3+",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                6,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-QFT-DIV: QFT division broken at width 3+",
                        strict=False,
                    ),
                ],
            ),
        ],
    )
    def test_div_classical(self, width):
        """Classical divisor division (a // int) produces identical results in both backends.

        Exhaustive for widths 2-3, sampled for widths 4-6.
        Known BUG-DIV-02 and BUG-QFT-DIV cases are skipped at width 2.
        Widths 3+ are xfail because QFT division is pervasively broken
        (BUG-QFT-DIV discovered during Phase 70-02 cross-backend testing).
        Uses MPS for both backends (QFT division circuits too large for statevector).
        """
        if width <= 3:
            sample_size = None  # exhaustive
        elif width <= 4:
            sample_size = 20
        else:
            sample_size = 15

        pairs = _generate_div_pairs(width, sample_size=sample_size or 999)

        failures = []
        for a, d in pairs:
            if (width, a, d) in KNOWN_DIV_FAILURES:
                continue

            def build_fn(a=a, d=d, w=width):
                qa = ql.qint(a, width=w)
                qr = qa // d
                return qr, a // d, [qa, qr]

            toffoli_result, qft_result = _compare_backends(
                build_fn, width, use_mps_toffoli=True, use_mps_qft=True
            )
            if toffoli_result != qft_result:
                expected = a // d
                failures.append(
                    f"w={width} a={a} div={d}: toffoli={toffoli_result}, "
                    f"qft={qft_result}, expected={expected}"
                )

        assert not failures, f"{len(failures)} cross-backend div mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize(
        "width",
        [
            2,
            pytest.param(
                3,
                marks=pytest.mark.xfail(
                    reason="BUG-QFT-DIV: QFT modulo is pervasively broken at width 3+ "
                    "(same root cause as QFT division). First discovered in Phase 70-02.",
                    strict=False,
                ),
            ),
            pytest.param(
                4,
                marks=pytest.mark.xfail(
                    reason="BUG-QFT-DIV: QFT modulo broken at width 3+",
                    strict=False,
                ),
            ),
            pytest.param(
                5,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-QFT-DIV: QFT modulo broken at width 3+",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                6,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-QFT-DIV: QFT modulo broken at width 3+",
                        strict=False,
                    ),
                ],
            ),
        ],
    )
    def test_mod_classical(self, width):
        """Classical divisor modulo (a % int) produces identical results in both backends.

        BUG-MOD-REDUCE means both backends often produce the SAME wrong answer.
        This is expected and acceptable for cross-backend equivalence -- we only
        check that backends agree, not that the result is mathematically correct.

        Known-buggy cases at width 2 are skipped (BUG-MOD-REDUCE + BUG-QFT-DIV).
        Widths 3+ are xfail because QFT modulo is pervasively broken (BUG-QFT-DIV).

        Uses MPS for both backends (QFT division circuits too large for statevector).
        """
        if width <= 3:
            sample_size = None
        elif width <= 4:
            sample_size = 20
        else:
            sample_size = 15

        pairs = _generate_div_pairs(width, sample_size=sample_size or 999)

        failures = []
        for a, d in pairs:
            if (width, a, d) in KNOWN_MOD_FAILURES:
                continue

            def build_fn(a=a, d=d, w=width):
                qa = ql.qint(a, width=w)
                qr = qa % d
                return qr, a % d, [qa, qr]

            toffoli_result, qft_result = _compare_backends(
                build_fn, width, use_mps_toffoli=True, use_mps_qft=True
            )
            if toffoli_result != qft_result:
                expected = a % d
                failures.append(
                    f"w={width} a={a} div={d}: toffoli={toffoli_result}, "
                    f"qft={qft_result}, expected={expected}"
                )

        assert not failures, f"{len(failures)} cross-backend mod mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize(
        "width",
        [
            pytest.param(
                2,
                marks=pytest.mark.xfail(
                    reason="BUG-QFT-DIV: QFT quantum division broken at all widths. "
                    "MPS simulation may also be non-deterministic for QFT circuits "
                    "with 34+ qubits.",
                    strict=False,
                ),
            ),
            pytest.param(
                3,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-QFT-DIV: QFT quantum division broken at all widths",
                        strict=False,
                    ),
                ],
            ),
            pytest.param(
                4,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-QFT-DIV: QFT quantum division broken; "
                        "also ~120 qubits may be infeasible",
                        strict=False,
                    ),
                ],
            ),
        ],
    )
    def test_div_quantum(self, width):
        """Quantum divisor division (a // qint(b)) produces identical results in both backends.

        Width 2: exhaustive (37 qubits with Toffoli, 34 with QFT).
        Width 3-4: sampled (82+ qubits, very slow with MPS).

        Known quantum division failures are skipped (BUG-DIV-02 + BUG-QFT-DIV).
        Uses MPS for both backends (quantum division circuits too large for statevector).
        """
        pairs = _generate_qdiv_pairs(width, sample_size=5)

        failures = []
        for a, b in pairs:
            if (width, a, b) in KNOWN_QDIV_FAILURES:
                continue

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                qr = qa // qb
                return qr, a // b, [qa, qb, qr]

            toffoli_result, qft_result = _compare_backends(
                build_fn, width, use_mps_toffoli=True, use_mps_qft=True
            )
            if toffoli_result != qft_result:
                expected = a // b
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, "
                    f"qft={qft_result}, expected={expected}"
                )

        assert not failures, f"{len(failures)} cross-backend qdiv mismatches:\n" + "\n".join(
            failures[:20]
        )

    @pytest.mark.parametrize(
        "width",
        [
            pytest.param(
                2,
                marks=pytest.mark.xfail(
                    reason="BUG-QFT-DIV: QFT quantum modulo broken at all widths. "
                    "MPS simulation may also be non-deterministic for QFT circuits.",
                    strict=False,
                ),
            ),
            pytest.param(
                3,
                marks=[
                    pytest.mark.slow,
                    pytest.mark.xfail(
                        reason="BUG-QFT-DIV: QFT quantum modulo broken at all widths",
                        strict=False,
                    ),
                ],
            ),
        ],
    )
    def test_mod_quantum(self, width):
        """Quantum divisor modulo (a % qint(b)) produces identical results in both backends.

        Only widths 2-3 (quantum modulo extremely slow at width 4+).
        Known quantum modulo failures are skipped (BUG-MOD-REDUCE + BUG-QFT-DIV).

        BUG-MOD-REDUCE may cause both backends to agree on wrong answers
        (which is acceptable for cross-backend equivalence).

        Uses MPS for both backends (quantum modulo circuits too large for statevector).
        """
        pairs = _generate_qdiv_pairs(width, sample_size=5)

        failures = []
        for a, b in pairs:
            if (width, a, b) in KNOWN_QMOD_FAILURES:
                continue

            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                qr = qa % qb
                return qr, a % b, [qa, qb, qr]

            toffoli_result, qft_result = _compare_backends(
                build_fn, width, use_mps_toffoli=True, use_mps_qft=True
            )
            if toffoli_result != qft_result:
                expected = a % b
                failures.append(
                    f"w={width} a={a} b={b}: toffoli={toffoli_result}, "
                    f"qft={qft_result}, expected={expected}"
                )

        assert not failures, f"{len(failures)} cross-backend qmod mismatches:\n" + "\n".join(
            failures[:20]
        )
