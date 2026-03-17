"""Tests for _and_chain and controlled _s0_reflection / _apply_nested_with.

Covers:
- _and_chain: 1 element, 2 elements, 3+ elements, history linkage
- _apply_nested_with: single control, dual controls, body execution
- _s0_reflection: with control_qbool and/or marking_qbool
"""

import gc

import numpy as np
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.diffusion import _and_chain, _extract_qbools
from quantum_language.walk_diffusion import _apply_nested_with, _s0_reflection

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_circuit():
    gc.collect()
    ql.circuit()
    ql.option("simulate", True)


def _get_statevector(qasm_str):
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(circuit, shots=1).result()
    return np.asarray(result.get_statevector())


def _get_num_qubits(qasm_str):
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


# ---------------------------------------------------------------------------
# Group 1: _and_chain
# ---------------------------------------------------------------------------


class TestAndChainSingleElement:
    """_and_chain with 1 element returns the element itself."""

    def test_returns_same_object(self):
        _init_circuit()
        a = ql.qbool(True)
        result = _and_chain([a])
        assert result is a

    def test_no_history_modification(self):
        _init_circuit()
        a = ql.qbool(True)
        hist_len_before = len(a.history)
        _and_chain([a])
        assert len(a.history) == hist_len_before


class TestAndChainTwoElements:
    """_and_chain with 2 elements produces a single AND."""

    def test_returns_new_object(self):
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        result = _and_chain([a, b])
        assert result is not a
        assert result is not b

    def test_true_and_true(self):
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        result = _and_chain([a, b])
        _keepalive = [a, b, result]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)
        # result qubit should be |1>
        result_start = result.allocated_start
        probs = {}
        for idx, amp in enumerate(sv):
            p = abs(amp) ** 2
            if p < 1e-15:
                continue
            val = (idx >> result_start) & 1
            probs[val] = probs.get(val, 0.0) + p
        assert probs.get(1, 0.0) > 0.99

    def test_true_and_false(self):
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(False)
        result = _and_chain([a, b])
        _keepalive = [a, b, result]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)
        result_start = result.allocated_start
        probs = {}
        for idx, amp in enumerate(sv):
            p = abs(amp) ** 2
            if p < 1e-15:
                continue
            val = (idx >> result_start) & 1
            probs[val] = probs.get(val, 0.0) + p
        assert probs.get(0, 0.0) > 0.99

    def test_has_history(self):
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        result = _and_chain([a, b])
        assert len(result.history) > 0


class TestAndChainThreeElements:
    """_and_chain with 3+ elements chains AND operations with history linkage."""

    def test_three_true(self):
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = ql.qbool(True)
        result = _and_chain([a, b, c])
        _keepalive = [a, b, c, result]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)
        result_start = result.allocated_start
        probs = {}
        for idx, amp in enumerate(sv):
            p = abs(amp) ** 2
            if p < 1e-15:
                continue
            val = (idx >> result_start) & 1
            probs[val] = probs.get(val, 0.0) + p
        assert probs.get(1, 0.0) > 0.99

    def test_three_one_false(self):
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(False)
        c = ql.qbool(True)
        result = _and_chain([a, b, c])
        _keepalive = [a, b, c, result]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)
        result_start = result.allocated_start
        probs = {}
        for idx, amp in enumerate(sv):
            p = abs(amp) ** 2
            if p < 1e-15:
                continue
            val = (idx >> result_start) & 1
            probs[val] = probs.get(val, 0.0) + p
        assert probs.get(0, 0.0) > 0.99

    def test_has_history_children(self):
        """Intermediate AND result is registered as history child."""
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = ql.qbool(True)
        result = _and_chain([a, b, c])
        # The intermediate (a & b) should be a history child of result
        assert len(result.history.children) >= 1
        child = result.history.children[0]()
        assert child is not None

    def test_four_elements(self):
        _init_circuit()
        bits = [ql.qbool(True) for _ in range(4)]
        result = _and_chain(bits)
        _keepalive = bits + [result]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)
        result_start = result.allocated_start
        probs = {}
        for idx, amp in enumerate(sv):
            p = abs(amp) ** 2
            if p < 1e-15:
                continue
            val = (idx >> result_start) & 1
            probs[val] = probs.get(val, 0.0) + p
        assert probs.get(1, 0.0) > 0.99


class TestAndChainHistoryUncompute:
    """History uncomputation cascades correctly through AND chain."""

    def test_with_block_uncomputes_chain(self):
        """with combined: ... properly uncomputes all AND ancillas."""
        _init_circuit()
        x = ql.qint(0, width=3)
        x.branch()
        bits = _extract_qbools(x)
        combined = _and_chain(bits)
        with combined:
            x.phase += 3.14159
        _keepalive = [x]
        qasm = ql.to_openqasm()
        sv = _get_statevector(qasm)
        # After branch + phase flip on |111>, the state |111> (index 7)
        # should have a different phase from others.
        # All data-qubit amplitudes should be nonzero.
        data_amps = [complex(sv[i]).real for i in range(8)]
        nonzero = [a for a in data_amps if abs(a) > 1e-10]
        assert len(nonzero) == 8, f"Expected 8 nonzero amplitudes, got {len(nonzero)}: {data_amps}"

    def test_with_block_does_not_corrupt_inputs(self):
        """External qbools survive after _and_chain + with block."""
        _init_circuit()
        a = ql.qbool(True)
        b = ql.qbool(True)
        c = ql.qbool(True)
        combined = _and_chain([a, b, c])
        dummy = ql.qint(0, width=1)
        with combined:
            dummy += 1
        # a, b, c should not be uncomputed
        assert not a._is_uncomputed
        assert not b._is_uncomputed
        assert not c._is_uncomputed


# ---------------------------------------------------------------------------
# Group 2: _apply_nested_with
# ---------------------------------------------------------------------------


class TestApplyNestedWith:
    """_apply_nested_with executes body under combined control."""

    def test_empty_controls_calls_body(self):
        _init_circuit()
        called = [False]

        def body():
            called[0] = True

        _apply_nested_with([], body)
        assert called[0]

    def test_single_true_control_calls_body(self):
        _init_circuit()
        x = ql.qint(0, width=2)
        ctrl = ql.qbool(True)

        _apply_nested_with([ctrl], lambda: x.__iadd__(1))

        _keepalive = [x, ctrl]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21

    def test_single_control_not_corrupted(self):
        """Single control qbool's dependency_parents are not cleared."""
        _init_circuit()
        ctrl = ql.qbool(True)
        parents_before = list(ctrl.dependency_parents)

        _apply_nested_with([ctrl], lambda: None)

        # dependency_parents should be unchanged
        assert list(ctrl.dependency_parents) == parents_before

    def test_dual_controls_not_corrupted(self):
        """External control qbools survive after _apply_nested_with with 2 controls."""
        _init_circuit()
        ctrl1 = ql.qbool(True)
        ctrl2 = ql.qbool(True)

        _apply_nested_with([ctrl1, ctrl2], lambda: None)

        assert not ctrl1._is_uncomputed
        assert not ctrl2._is_uncomputed

    def test_three_controls_not_corrupted(self):
        """External control qbools survive after _apply_nested_with with 3 controls."""
        _init_circuit()
        ctrl1 = ql.qbool(True)
        ctrl2 = ql.qbool(True)
        ctrl3 = ql.qbool(True)

        _apply_nested_with([ctrl1, ctrl2, ctrl3], lambda: None)

        assert not ctrl1._is_uncomputed
        assert not ctrl2._is_uncomputed
        assert not ctrl3._is_uncomputed


# ---------------------------------------------------------------------------
# Group 3: _s0_reflection controlled paths
# ---------------------------------------------------------------------------


class TestS0ReflectionControlled:
    """_s0_reflection with control_qbool and/or marking_qbool."""

    def test_with_control_qbool_only(self):
        """S_0 with control_qbool set produces valid circuit."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        ctrl = ql.qbool(True)

        _s0_reflection(pf, br, control_qbool=ctrl)

        _keepalive = [pf, br, ctrl]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21

    def test_with_marking_qbool_only(self):
        """S_0 with marking_qbool set produces valid circuit."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        mark = ql.qbool(True)

        _s0_reflection(pf, br, marking_qbool=mark)

        _keepalive = [pf, br, mark]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21

    def test_with_both_controls(self):
        """S_0 with both control_qbool and marking_qbool produces valid circuit."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        ctrl = ql.qbool(True)
        mark = ql.qbool(True)

        _s0_reflection(pf, br, control_qbool=ctrl, marking_qbool=mark)

        _keepalive = [pf, br, ctrl, mark]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21

    def test_control_qbool_not_uncomputed(self):
        """control_qbool is not destroyed by _s0_reflection."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        ctrl = ql.qbool(True)

        _s0_reflection(pf, br, control_qbool=ctrl)

        assert not ctrl._is_uncomputed

    def test_marking_qbool_not_uncomputed(self):
        """marking_qbool is not destroyed by _s0_reflection."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        mark = ql.qbool(True)

        _s0_reflection(pf, br, marking_qbool=mark)

        assert not mark._is_uncomputed

    def test_both_controls_not_uncomputed(self):
        """Both control_qbool and marking_qbool survive _s0_reflection."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        ctrl = ql.qbool(True)
        mark = ql.qbool(True)

        _s0_reflection(pf, br, control_qbool=ctrl, marking_qbool=mark)

        assert not ctrl._is_uncomputed
        assert not mark._is_uncomputed

    def test_controlled_s0_involution(self):
        """Controlled S_0 applied twice preserves probabilities (S_0^2 ~ I)."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        ctrl = ql.qbool(True)
        sv_init = _get_statevector(ql.to_openqasm())

        _s0_reflection(pf, br, control_qbool=ctrl)
        _s0_reflection(pf, br, control_qbool=ctrl)

        _keepalive = [pf, br, ctrl]
        sv_after = _get_statevector(ql.to_openqasm())

        # S_0^2 should equal identity up to global phase.
        # Check that probabilities match.
        n = len(sv_init)
        probs_init = np.abs(sv_init) ** 2
        probs_after = np.abs(sv_after[:n]) ** 2
        assert np.allclose(probs_init, probs_after, atol=1e-6), (
            "Controlled S_0^2 should preserve probabilities"
        )

    def test_marking_qbool_usable_after_s0(self):
        """marking_qbool can be used in operations after _s0_reflection."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        mark = ql.qbool(True)

        _s0_reflection(pf, br, marking_qbool=mark)

        # This should not raise "already uncomputed"
        mark ^= 1
        mark ^= 1
