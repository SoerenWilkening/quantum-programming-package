"""Phase 71: CLA Adder Tests.

Tests CLA QQ and CQ addition at widths >= CLA_THRESHOLD (2).
Uses Qiskit AerSimulator for exhaustive statevector verification.

Plan 71-01: BK QQ smoke tests + option tests.
Plan 71-02: KS QQ tests, BK/KS CQ tests, variant selection tests.

BK CLA is implemented and working for width >= 2 (Plan 71-05).
KS CLA still returns NULL (falls back to RCA).
BK CQ, controlled BK QQ, and controlled BK CQ are implemented (Plan 71-06).
Carry-copy ancilla are known to be dirty (documented trade-off per SC4).
"""

import gc
import warnings

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _enable_toffoli_cla():
    """Enable Toffoli mode with CLA enabled (default)."""
    ql.option("fault_tolerant", True)
    ql.option("cla", True)  # Ensure CLA is not overridden


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate a QASM circuit and extract result from specific qubit range."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(method="statevector")
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _get_num_qubits_from_qasm(qasm_str):
    """Extract qubit count from OpenQASM qubit declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _run_inplace_add(a_val, b_val, width):
    """Run in-place addition and extract result from qa register.

    qa += qb where qa is at physical qubits [0..width-1].
    """
    gc.collect()
    ql.circuit()
    _enable_toffoli_cla()
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qa += qb
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    # qa is first allocated, starts at qubit 0
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, qb)
    return actual


def _run_inplace_sub(a_val, b_val, width):
    """Run in-place subtraction and extract result from qa register.

    qa -= qb where qa is at physical qubits [0..width-1].
    """
    gc.collect()
    ql.circuit()
    _enable_toffoli_cla()
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qa -= qb
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, qb)
    return actual


class TestBKQQAddition:
    """Test Brent-Kung QQ addition at CLA-eligible widths."""

    @pytest.mark.parametrize("width", [4, 5, 6])
    def test_bk_qq_add_exhaustive(self, width):
        """Exhaustive test: a + b mod 2^width for all input pairs."""
        modulus = 1 << width
        failures = []

        for a_val in range(modulus):
            for b_val in range(modulus):
                expected = (a_val + b_val) % modulus
                actual = _run_inplace_add(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("bk_qq_add", [a_val, b_val], width, expected, actual)
                    )

        assert not failures, (
            f"BK QQ add width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )

    @pytest.mark.parametrize("width", [4, 5])
    def test_bk_qq_sub_exhaustive(self, width):
        """Exhaustive test: a - b mod 2^width for all input pairs."""
        modulus = 1 << width
        failures = []

        for a_val in range(modulus):
            for b_val in range(modulus):
                expected = (a_val - b_val) % modulus
                actual = _run_inplace_sub(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("bk_qq_sub", [a_val, b_val], width, expected, actual)
                    )

        assert not failures, (
            f"BK QQ sub width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )


class TestCLAOption:
    """Test CLA option override."""

    def test_cla_option_default_true(self):
        """CLA is enabled by default."""
        gc.collect()
        ql.circuit()
        assert ql.option("cla") is True

    def test_cla_option_disable(self):
        """ql.option('cla', False) disables CLA."""
        gc.collect()
        ql.circuit()
        ql.option("cla", False)
        assert ql.option("cla") is False

    def test_cla_option_re_enable(self):
        """CLA can be re-enabled."""
        gc.collect()
        ql.circuit()
        ql.option("cla", False)
        ql.option("cla", True)
        assert ql.option("cla") is True

    def test_cla_option_rejects_non_bool(self):
        """CLA option rejects non-bool values."""
        gc.collect()
        ql.circuit()
        with pytest.raises(ValueError, match="cla option requires bool"):
            ql.option("cla", 1)

    def test_cla_option_reset_on_new_circuit(self):
        """Creating a new circuit resets CLA to default (enabled)."""
        gc.collect()
        ql.circuit()
        ql.option("cla", False)
        assert ql.option("cla") is False
        ql.circuit()
        assert ql.option("cla") is True

    def test_cla_override_forces_rca(self):
        """With CLA disabled, width >= 4 still uses RCA (produces correct results)."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("cla", False)
        qa = ql.qint(5, width=4)
        qb = ql.qint(3, width=4)
        qa += qb
        qasm_str = ql.to_openqasm()
        num_qubits = _get_num_qubits_from_qasm(qasm_str)
        actual = _simulate_and_extract(qasm_str, num_qubits, 0, 4)
        assert actual == 8, f"Expected 8, got {actual}"
        _ = (qa, qb)


class TestCLABelowThreshold:
    """Verify widths below threshold still use RCA correctly."""

    @pytest.mark.parametrize("width", [2, 3])
    def test_below_threshold_still_works(self, width):
        """Widths below CLA threshold use RCA (existing behavior preserved)."""
        modulus = 1 << width
        failures = []
        for a_val in range(modulus):
            for b_val in range(modulus):
                expected = (a_val + b_val) % modulus
                actual = _run_inplace_add(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "below_threshold", [a_val, b_val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"Below-threshold width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )


# ============================================================================
# Phase 71-02: KS QQ, BK/KS CQ, and variant selection tests
# ============================================================================


def _run_ks_qq_add(a_val, b_val, width):
    """Run KS QQ addition (qubit_saving=False) and extract result."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("qubit_saving", False)  # KS is default when qubit_saving off
    ql.option("cla", True)
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    qa += qb
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, qb)
    return actual


def _run_bk_cq_add(self_val, val, width):
    """Run BK CQ addition (qubit_saving=True) and extract result."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("qubit_saving", True)  # BK when qubit_saving on
    ql.option("cla", True)
    qa = ql.qint(self_val, width=width)
    qa += val
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = qa
    return actual


def _run_bk_cq_sub(self_val, val, width):
    """Run BK CQ subtraction (qubit_saving=True) and extract result."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("qubit_saving", True)
    ql.option("cla", True)
    qa = ql.qint(self_val, width=width)
    qa -= val
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = qa
    return actual


def _run_ks_cq_add(self_val, val, width):
    """Run KS CQ addition (qubit_saving=False) and extract result."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("qubit_saving", False)  # KS when qubit_saving off
    ql.option("cla", True)
    qa = ql.qint(self_val, width=width)
    qa += val
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = qa
    return actual


class TestKSQQAddition:
    """Test Kogge-Stone QQ addition (default when qubit_saving off).

    KS QQ adder currently returns NULL (ancilla uncomputation impossibility),
    so these tests verify correctness via silent RCA fallback.
    """

    @pytest.mark.parametrize("width", [4, 5, 6])
    def test_ks_qq_add_exhaustive(self, width):
        """KS QQ addition: all input pairs."""
        modulus = 1 << width
        failures = []

        for a_val in range(modulus):
            for b_val in range(modulus):
                expected = (a_val + b_val) % modulus
                actual = _run_ks_qq_add(a_val, b_val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message("ks_qq_add", [a_val, b_val], width, expected, actual)
                    )

        assert not failures, (
            f"KS QQ add width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )


class TestBKCQAddition:
    """Test Brent-Kung CQ addition (qubit_saving=True).

    BK CQ adder is now implemented via sequence-copy from cached QQ BK
    (Plan 71-06). Uses X-init/cleanup with the BK CLA core.
    """

    @pytest.mark.parametrize("width", [4, 5])
    def test_bk_cq_add_exhaustive(self, width):
        """BK CQ addition: self += classical for all pairs."""
        modulus = 1 << width
        failures = []

        for val in range(modulus):
            for self_val in range(modulus):
                expected = (self_val + val) % modulus
                actual = _run_bk_cq_add(self_val, val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "bk_cq_add", [self_val, val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"BK CQ add width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )

    @pytest.mark.parametrize("width", [4, 5])
    def test_bk_cq_sub_exhaustive(self, width):
        """BK CQ subtraction: self -= classical for all pairs."""
        modulus = 1 << width
        failures = []

        for val in range(modulus):
            for self_val in range(modulus):
                expected = (self_val - val) % modulus
                actual = _run_bk_cq_sub(self_val, val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "bk_cq_sub", [self_val, val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"BK CQ sub width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )


class TestKSCQAddition:
    """Test Kogge-Stone CQ addition (qubit_saving=False).

    KS CQ adder currently returns NULL (ancilla uncomputation impossibility),
    so these tests verify correctness via silent RCA fallback.
    """

    @pytest.mark.parametrize("width", [4, 5])
    def test_ks_cq_add_exhaustive(self, width):
        """KS CQ addition: self += classical for all pairs."""
        modulus = 1 << width
        failures = []

        for val in range(modulus):
            for self_val in range(modulus):
                expected = (self_val + val) % modulus
                actual = _run_ks_cq_add(self_val, val, width)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            "ks_cq_add", [self_val, val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"KS CQ add width={width}: {len(failures)}/{modulus * modulus} failures:\n"
            + "\n".join(failures[:20])
        )


# ============================================================================
# Phase 71-03: Controlled CLA tests (cQQ and cCQ, BK and KS)
# ============================================================================


def _run_controlled_qq_add(a_val, b_val, width, ctrl_val, variant):
    """Run controlled QQ addition with CLA enabled and extract result."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("qubit_saving", variant == "bk")
    ql.option("cla", True)
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    ctrl = ql.qint(ctrl_val, width=1)
    with ctrl:
        qa += qb
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, qb, ctrl)
    return actual


def _run_controlled_qq_sub(a_val, b_val, width, ctrl_val, variant):
    """Run controlled QQ subtraction with CLA enabled and extract result."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("qubit_saving", variant == "bk")
    ql.option("cla", True)
    qa = ql.qint(a_val, width=width)
    qb = ql.qint(b_val, width=width)
    ctrl = ql.qint(ctrl_val, width=1)
    with ctrl:
        qa -= qb
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, qb, ctrl)
    return actual


def _run_controlled_cq_add(self_val, val, width, ctrl_val, variant):
    """Run controlled CQ addition with CLA enabled and extract result."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", True)
    ql.option("qubit_saving", variant == "bk")
    ql.option("cla", True)
    qa = ql.qint(self_val, width=width)
    ctrl = ql.qint(ctrl_val, width=1)
    with ctrl:
        qa += val
    qasm_str = ql.to_openqasm()
    num_qubits = _get_num_qubits_from_qasm(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, 0, width)
    _ = (qa, ctrl)
    return actual


class TestControlledCLAAddition:
    """Phase 71-03: Controlled CLA addition verification (cQQ and cCQ).

    BK controlled CLA adders (cQQ, cCQ) are now implemented via
    sequence-copy with ext_ctrl injection (Plan 71-06).
    KS controlled CLA adders still return NULL (fall back to controlled RCA).
    """

    @pytest.mark.parametrize("variant", ["bk", "ks"])
    @pytest.mark.parametrize("width", [4, 5])
    def test_cqq_cla_add_ctrl1(self, variant, width):
        """Controlled QQ CLA addition: a += b when control=|1>."""
        modulus = 1 << width
        failures = []

        for a_val in range(min(modulus, 8)):
            for b_val in range(min(modulus, 8)):
                expected = (a_val + b_val) % modulus
                actual = _run_controlled_qq_add(a_val, b_val, width, 1, variant)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            f"cqq_cla_{variant}_ctrl1", [a_val, b_val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"cQQ CLA {variant.upper()} add ctrl=1 width={width}: "
            f"{len(failures)} failures:\n" + "\n".join(failures[:20])
        )

    @pytest.mark.parametrize("variant", ["bk", "ks"])
    @pytest.mark.parametrize("width", [4, 5])
    def test_cqq_cla_add_ctrl0(self, variant, width):
        """Controlled QQ CLA addition: a unchanged when control=|0>."""
        modulus = 1 << width
        failures = []

        for a_val in range(min(modulus, 4)):
            for b_val in range(min(modulus, 4)):
                actual = _run_controlled_qq_add(a_val, b_val, width, 0, variant)
                if actual != a_val:
                    failures.append(
                        format_failure_message(
                            f"cqq_cla_{variant}_ctrl0", [a_val, b_val], width, a_val, actual
                        )
                    )

        assert not failures, (
            f"cQQ CLA {variant.upper()} add ctrl=0 width={width}: "
            f"{len(failures)} failures:\n" + "\n".join(failures[:20])
        )

    @pytest.mark.parametrize("variant", ["bk", "ks"])
    @pytest.mark.parametrize("width", [4, 5])
    def test_ccq_cla_add_ctrl1(self, variant, width):
        """Controlled CQ CLA addition: a += classical when control=|1>."""
        modulus = 1 << width
        failures = []

        for val in range(min(modulus, 8)):
            for self_val in range(min(modulus, 8)):
                expected = (self_val + val) % modulus
                actual = _run_controlled_cq_add(self_val, val, width, 1, variant)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            f"ccq_cla_{variant}_ctrl1", [self_val, val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"cCQ CLA {variant.upper()} add ctrl=1 width={width}: "
            f"{len(failures)} failures:\n" + "\n".join(failures[:20])
        )

    @pytest.mark.parametrize("variant", ["bk", "ks"])
    @pytest.mark.parametrize("width", [4, 5])
    def test_ccq_cla_add_ctrl0(self, variant, width):
        """Controlled CQ CLA addition: a unchanged when control=|0>."""
        modulus = 1 << width
        failures = []

        for self_val in range(min(modulus, 4)):
            actual = _run_controlled_cq_add(self_val, 3, width, 0, variant)
            if actual != self_val:
                failures.append(
                    format_failure_message(
                        f"ccq_cla_{variant}_ctrl0", [self_val, 3], width, self_val, actual
                    )
                )

        assert not failures, (
            f"cCQ CLA {variant.upper()} add ctrl=0 width={width}: "
            f"{len(failures)} failures:\n" + "\n".join(failures[:20])
        )

    @pytest.mark.parametrize("variant", ["bk", "ks"])
    def test_controlled_cla_subtraction(self, variant):
        """Controlled CLA subtraction works via inversion."""
        width = 4
        modulus = 16
        failures = []

        for a_val in range(min(modulus, 8)):
            for b_val in range(min(modulus, 8)):
                expected = (a_val - b_val) % modulus
                actual = _run_controlled_qq_sub(a_val, b_val, width, 1, variant)
                if actual != expected:
                    failures.append(
                        format_failure_message(
                            f"cqq_cla_{variant}_sub", [a_val, b_val], width, expected, actual
                        )
                    )

        assert not failures, (
            f"Controlled CLA {variant.upper()} sub width=4: "
            f"{len(failures)} failures:\n" + "\n".join(failures[:20])
        )


# ============================================================================
# Phase 71-06: BK CLA depth verification
# ============================================================================


class TestBKCLADepthVerification:
    """Verify BK CLA is actually being used (not RCA fallback).

    The BK CLA has O(log n) parallel depth, which is measurably less
    than RCA's O(n) depth. This test confirms BK CLA dispatch is
    working by checking that the circuit depth is significantly
    less than what RCA would produce.
    """

    def test_bk_depth_less_than_rca_width8(self):
        """BK CLA depth at width 8 is less than RCA depth."""
        gc.collect()
        c_rca = ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("cla", False)  # Force RCA
        qa = ql.qint(0, width=8)
        qb = ql.qint(0, width=8)
        qa += qb
        rca_depth = c_rca.depth
        _ = (qa, qb)

        gc.collect()
        c_bk = ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("cla", True)
        ql.option("qubit_saving", True)  # BK
        qa = ql.qint(0, width=8)
        qb = ql.qint(0, width=8)
        qa += qb
        bk_depth = c_bk.depth
        _ = (qa, qb)

        # RCA depth for width 8 is ~35 layers, BK should be ~19
        assert bk_depth < rca_depth, (
            f"BK depth ({bk_depth}) should be < RCA depth ({rca_depth}) at width 8. "
            f"BK CLA dispatch may not be working."
        )
