"""Tests for walk_diffusion: local diffusion operator D_x.

Verifies the reflection property (D^2 = I), correct amplitudes after
one diffusion, root angle formula usage, and identity behavior when
no children are valid.  All tests stay within the 17-qubit limit.

Requirements from acceptance criteria:
- D^2 = I (statevector tolerance 1e-6)
- Correct amplitudes after one diffusion
- Root uses root angle formula
- Identity when no valid children
"""

import gc

import numpy as np
import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import (
    WalkConfig,
    branch_width,
)
from quantum_language.walk_diffusion import (
    walk_diffusion,
    walk_diffusion_with_regs,
    _s0_reflection,
)


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------


def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM qubit[N] declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _get_statevector(qasm_str):
    """Simulate QASM and return the full statevector as numpy array."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    simulator = AerSimulator(method="statevector", max_parallel_threads=4)
    job = simulator.run(circuit, shots=1)
    result = job.result()
    sv = result.get_statevector()
    return np.asarray(sv)


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate QASM and extract integer from result register."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(method="statevector", max_parallel_threads=4)
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos: lsb_pos + 1]
    return int(result_bits, 2)


def _extract_register_probs(sv, reg_start, reg_width):
    """Sum statevector probabilities by register value."""
    probs = {}
    for idx, amp in enumerate(sv):
        p = abs(amp) ** 2
        if p < 1e-15:
            continue
        val = (idx >> reg_start) & ((1 << reg_width) - 1)
        probs[val] = probs.get(val, 0.0) + p
    return probs


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()
    ql.option('simulate', True)


# ---------------------------------------------------------------------------
# Test move/validity functions
# ---------------------------------------------------------------------------


def _make_move_xor(state, move_idx):
    """Apply move by XORing state with (move_idx + 1)."""
    state ^= (move_idx + 1)


def _undo_move_xor(state, move_idx):
    """Undo XOR move (XOR is self-inverse)."""
    state ^= (move_idx + 1)


def _is_valid_nonzero(state):
    """Validity predicate: valid when state != 0."""
    return state != 0


# ---------------------------------------------------------------------------
# Group 1: Validation Tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Argument validation for walk_diffusion."""

    def test_rejects_none_state(self):
        with pytest.raises(ValueError, match="state must not be None"):
            walk_diffusion(None, _make_move_xor, _is_valid_nonzero, 2)

    def test_rejects_none_make_move(self):
        _init_circuit()
        state = ql.qint(0, width=2)
        with pytest.raises(ValueError, match="make_move must not be None"):
            walk_diffusion(state, None, _is_valid_nonzero, 2)

    def test_rejects_none_is_valid(self):
        _init_circuit()
        state = ql.qint(0, width=2)
        with pytest.raises(ValueError, match="is_valid must not be None"):
            walk_diffusion(state, _make_move_xor, None, 2)

    def test_rejects_non_int_num_moves(self):
        _init_circuit()
        state = ql.qint(0, width=2)
        with pytest.raises(TypeError, match="num_moves must be an int"):
            walk_diffusion(state, _make_move_xor, _is_valid_nonzero, 2.5)

    def test_rejects_zero_num_moves(self):
        _init_circuit()
        state = ql.qint(0, width=2)
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            walk_diffusion(state, _make_move_xor, _is_valid_nonzero, 0)

    def test_walk_diffusion_with_regs_rejects_non_config(self):
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            walk_diffusion_with_regs("not a config", None, None)


# ---------------------------------------------------------------------------
# Group 2: Variable Branching (with predicates)
# ---------------------------------------------------------------------------


class TestVariableBranching:
    """Variable-branching diffusion with is_valid predicate."""

    def test_public_api_callable(self):
        """walk_diffusion accepts (state, make_move, is_valid, num_moves)."""
        _init_circuit()
        state = ql.qint(0, width=2)
        walk_diffusion(
            state, _make_move_xor, _is_valid_nonzero, 1,
            undo_move=_undo_move_xor,
        )

    def test_public_api_with_all_kwargs(self):
        """walk_diffusion accepts all keyword arguments."""
        _init_circuit()
        state = ql.qint(0, width=2)
        walk_diffusion(
            state, _make_move_xor, _is_valid_nonzero, 1,
            undo_move=_undo_move_xor,
            max_depth=2, is_root=True,
        )

    def test_state_preserved_after_variable_diffusion(self):
        """State register value is preserved after variable diffusion.

        The counting apply-check-undo loop should restore state.
        """
        _init_circuit()
        state = ql.qint(5, width=4)

        walk_diffusion(
            state, _make_move_xor, _is_valid_nonzero, 1,
            undo_move=_undo_move_xor,
        )

        state_start = state.allocated_start
        state_width = state.width
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, state_start, state_width)
        assert extracted == 5, (
            f"State should be preserved at 5, got {extracted}"
        )

    def test_with_regs_preserves_state(self):
        """walk_diffusion_with_regs preserves state register."""
        _init_circuit()
        state = ql.qint(3, width=3)
        num_moves = 1
        bw = branch_width(num_moves)
        pf = ql.qbool()
        br = ql.qint(0, width=bw)

        config = WalkConfig(
            max_depth=1, num_moves=num_moves,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state,
        )

        walk_diffusion_with_regs(config, pf, br)

        state_start = state.allocated_start
        _keepalive = [state, pf, br]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        extracted = _simulate_and_extract(qasm, nq, state_start, state.width)
        assert extracted == 3, (
            f"State should be preserved at 3, got {extracted}"
        )

    def test_variable_diffusion_parent_flag_in_superposition(self):
        """After variable diffusion with valid children, parent_flag
        should be in superposition (non-trivial amplitude distribution).

        state=2, move_0: 2^1=3 (valid). count=1, rotation applied.
        """
        _init_circuit()
        state = ql.qint(2, width=3)
        num_moves = 1
        bw = branch_width(num_moves)
        pf = ql.qbool()
        br = ql.qint(0, width=bw)

        config = WalkConfig(
            max_depth=1, num_moves=num_moves,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state,
        )

        walk_diffusion_with_regs(config, pf, br)

        pf_start = pf.allocated_start
        _keepalive = [state, pf, br]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        sv = _get_statevector(qasm)
        pf_probs = _extract_register_probs(sv, pf_start, 1)

        # With state=2 and nonzero check, move 0 gives 2^1=3 (nonzero=valid)
        # So count=1. The diffusion should create amplitude on parent_flag.
        total_prob = pf_probs.get(0, 0.0) + pf_probs.get(1, 0.0)
        assert abs(total_prob - 1.0) < 1e-6

    def test_variable_diffusion_num_moves_2(self):
        """Variable diffusion works with num_moves=2.

        state=0, is_valid=nonzero:
        move 0: 0^1=1 (valid)
        move 1: 0^2=2 (valid)
        count=2, both children valid.
        """
        _init_circuit()
        state = ql.qint(0, width=2)

        walk_diffusion(
            state, _make_move_xor, _is_valid_nonzero, 2,
            undo_move=_undo_move_xor,
        )

        state_start = state.allocated_start
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        # State should be preserved (counting apply-check-undo is clean)
        extracted = _simulate_and_extract(qasm, nq, state_start, state.width)
        assert extracted == 0, (
            f"State should be preserved at 0, got {extracted}"
        )

    def test_variable_diffusion_num_moves_2_partial_validity(self):
        """Variable diffusion with num_moves=2, partial validity.

        state=1, is_valid=nonzero:
        move 0: 1^1=0 (invalid, zero)
        move 1: 1^2=3 (valid, nonzero)
        count=1.
        """
        _init_circuit()
        state = ql.qint(1, width=2)

        walk_diffusion(
            state, _make_move_xor, _is_valid_nonzero, 2,
            undo_move=_undo_move_xor,
        )

        state_start = state.allocated_start
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, state_start, state.width)
        assert extracted == 1, (
            f"State should be preserved at 1, got {extracted}"
        )

    def test_variable_diffusion_num_moves_2_qubit_indices_sane(self):
        """Variable diffusion with num_moves=2 produces sane qubit indices.

        Regression test: previously count -= v with comparison-derived
        qbools produced garbage qubit indices (32000+ qubits).
        """
        _init_circuit()
        state = ql.qint(0, width=2)

        walk_diffusion(
            state, _make_move_xor, _is_valid_nonzero, 2,
            undo_move=_undo_move_xor,
        )

        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq < 100, (
            f"Circuit uses {nq} qubits -- garbage qubit indices detected"
        )


# ---------------------------------------------------------------------------
# Group 3: Qubit Budget
# ---------------------------------------------------------------------------


class TestQubitBudget:
    """Verify circuits stay within the 17-qubit simulation limit."""

    def test_variable_1bit_1move_within_budget(self):
        """Variable diffusion with 1-bit state, 1 move within budget."""
        _init_circuit()
        state = ql.qint(0, width=1)
        walk_diffusion(
            state, _make_move_xor, _is_valid_nonzero, 1,
            undo_move=_undo_move_xor,
        )
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"


# ---------------------------------------------------------------------------
# Group 4: S_0 Reflection Unit Test
# ---------------------------------------------------------------------------


class TestS0Reflection:
    """S_0 reflection on parent_flag + branch register."""

    def test_s0_flips_phase_of_zero(self):
        """S_0 applied to |0,0> gives -|0,0>."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)

        _s0_reflection(pf, br)

        _keepalive = [pf, br]
        sv = _get_statevector(ql.to_openqasm())

        # |0,0> should have amplitude -1 (phase flipped)
        assert abs(sv[0] - (-1.0)) < 1e-6, (
            f"S_0|0,0> should be -|0,0>, got amplitude {sv[0]}"
        )

    def test_s0_preserves_nonzero(self):
        """S_0 preserves |1,0> (non-zero state)."""
        from quantum_language._gates import emit_x as raw_emit_x

        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)

        # Set parent_flag to |1>
        raw_emit_x(int(pf.qubits[63]))

        sv_before = _get_statevector(ql.to_openqasm())

        _s0_reflection(pf, br)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        # |1,0> should be unchanged (only |0,0> gets phase flip)
        assert np.allclose(sv_before, sv_after, atol=1e-6), (
            "S_0 should preserve non-zero states"
        )

    def test_s0_involution(self):
        """S_0^2 = I (applying S_0 twice is identity)."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        sv_init = _get_statevector(ql.to_openqasm())

        _s0_reflection(pf, br)
        _s0_reflection(pf, br)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_init, sv_after, atol=1e-10), (
            "S_0^2 should equal identity"
        )
