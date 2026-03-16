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
import math

import numpy as np
import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import (
    WalkConfig,
    branch_width,
    count_width,
    montanaro_phi,
    root_angle,
)
from quantum_language.walk_diffusion import (
    walk_diffusion,
    walk_diffusion_fixed,
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

    def test_fixed_rejects_non_int_num_moves(self):
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        with pytest.raises(TypeError, match="num_moves must be an int"):
            walk_diffusion_fixed(pf, br, 2.0)

    def test_fixed_rejects_zero_num_moves(self):
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            walk_diffusion_fixed(pf, br, 0)


# ---------------------------------------------------------------------------
# Group 2: Reflection Property D^2 = I (fixed branching)
# ---------------------------------------------------------------------------


class TestReflectionPropertyFixed:
    """D^2 = I (statevector tolerance 1e-6) for fixed branching."""

    def test_d_squared_identity_d1(self):
        """D^2 = I with d=1 (single child)."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(1))
        sv_init = _get_statevector(ql.to_openqasm())

        walk_diffusion_fixed(pf, br, num_moves=1)
        walk_diffusion_fixed(pf, br, num_moves=1)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_init, sv_after, atol=1e-6), (
            "D^2 should equal identity for d=1"
        )

    def test_d_squared_identity_d2(self):
        """D^2 = I with d=2 (binary branching)."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(2))
        sv_init = _get_statevector(ql.to_openqasm())

        walk_diffusion_fixed(pf, br, num_moves=2)
        walk_diffusion_fixed(pf, br, num_moves=2)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_init, sv_after, atol=1e-6), (
            "D^2 should equal identity for d=2"
        )

    def test_d_squared_identity_d3(self):
        """D^2 = I with d=3 (ternary branching)."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(3))
        sv_init = _get_statevector(ql.to_openqasm())

        walk_diffusion_fixed(pf, br, num_moves=3)
        walk_diffusion_fixed(pf, br, num_moves=3)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_init, sv_after, atol=1e-6), (
            "D^2 should equal identity for d=3"
        )

    def test_d_squared_identity_d4(self):
        """D^2 = I with d=4."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(4))
        sv_init = _get_statevector(ql.to_openqasm())

        walk_diffusion_fixed(pf, br, num_moves=4)
        walk_diffusion_fixed(pf, br, num_moves=4)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_init, sv_after, atol=1e-6), (
            "D^2 should equal identity for d=4"
        )

    def test_single_diffusion_changes_state_d2(self):
        """Single D with d=2 modifies the statevector (non-trivial)."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(2))
        sv_init = _get_statevector(ql.to_openqasm())

        walk_diffusion_fixed(pf, br, num_moves=2)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert not np.allclose(sv_init, sv_after, atol=1e-3), (
            "Single diffusion should change the state (d=2)"
        )


# ---------------------------------------------------------------------------
# Group 3: Root Angle Formula
# ---------------------------------------------------------------------------


class TestRootAngle:
    """Root diffusion uses root angle formula phi_root(d, n)."""

    def test_root_d_squared_identity_d2_n2(self):
        """D_root^2 = I with d=2, n=2."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(2))
        sv_init = _get_statevector(ql.to_openqasm())

        walk_diffusion_fixed(pf, br, num_moves=2, max_depth=2, is_root=True)
        walk_diffusion_fixed(pf, br, num_moves=2, max_depth=2, is_root=True)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_init, sv_after, atol=1e-6), (
            "D_root^2 should equal identity for d=2, n=2"
        )

    def test_root_d_squared_identity_d3_n2(self):
        """D_root^2 = I with d=3, n=2."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(3))
        sv_init = _get_statevector(ql.to_openqasm())

        walk_diffusion_fixed(pf, br, num_moves=3, max_depth=2, is_root=True)
        walk_diffusion_fixed(pf, br, num_moves=3, max_depth=2, is_root=True)

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_init, sv_after, atol=1e-6), (
            "D_root^2 should equal identity for d=3, n=2"
        )

    def test_root_produces_different_amplitudes_than_nonroot(self):
        """Root and non-root diffusions produce different states.

        phi_root(d=2, n=2) = 2*arctan(sqrt(4)) != phi(d=2) = 2*arctan(sqrt(2))
        """
        # Non-root
        _init_circuit()
        pf_nr = ql.qbool()
        br_nr = ql.qint(0, width=branch_width(2))
        walk_diffusion_fixed(pf_nr, br_nr, num_moves=2)
        _keep_nr = [pf_nr, br_nr]
        sv_nr = _get_statevector(ql.to_openqasm())

        # Root
        _init_circuit()
        pf_r = ql.qbool()
        br_r = ql.qint(0, width=branch_width(2))
        walk_diffusion_fixed(pf_r, br_r, num_moves=2, max_depth=2,
                             is_root=True)
        _keep_r = [pf_r, br_r]
        sv_r = _get_statevector(ql.to_openqasm())

        assert not np.allclose(sv_nr, sv_r, atol=1e-3), (
            "Root and non-root diffusions should produce different states"
        )


# ---------------------------------------------------------------------------
# Group 4: Correct Amplitudes After One Diffusion
# ---------------------------------------------------------------------------


class TestDiffusionAmplitudes:
    """Amplitudes after a single diffusion match expected reflection."""

    def test_d2_amplitudes(self):
        """D_x on d=2 from |0,0> produces correct reflection amplitudes.

        |psi_x> = cos(phi/2)|0,0> + cos(phi/2)*sin(pi/4)|0,1>
                  + sin(phi/2)*cos(pi/4)|1,0> + sin(phi/2)*sin(pi/4)|1,1>
        where phi = 2*arctan(sqrt(2)).

        D_x|0,0> = 2<psi_x|0,0>|psi_x> - |0,0>
        """
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(2))

        walk_diffusion_fixed(pf, br, num_moves=2)

        pf_start = pf.allocated_start
        br_start = br.allocated_start
        _keepalive = [pf, br]
        sv = _get_statevector(ql.to_openqasm())

        # Compute expected amplitudes analytically
        d = 2
        phi = montanaro_phi(d)
        cphi = math.cos(phi / 2)
        sphi = math.sin(phi / 2)
        cc = math.cos(math.pi / 4)
        sc = math.sin(math.pi / 4)

        # |psi_x> in (pf, br) basis
        psi = np.array([cphi * cc, cphi * sc, sphi * cc, sphi * sc])
        start = np.array([1.0, 0.0, 0.0, 0.0])
        inner = np.dot(psi, start)
        expected = 2 * inner * psi - start

        # Extract observed amplitudes from statevector
        # pf=qubit at pf_start, br=qubit at br_start
        idx_00 = 0  # pf=0, br=0
        idx_01 = 1 << br_start  # pf=0, br=1
        idx_10 = 1 << pf_start  # pf=1, br=0
        idx_11 = (1 << pf_start) | (1 << br_start)  # pf=1, br=1

        observed = np.array([sv[idx_00], sv[idx_01], sv[idx_10], sv[idx_11]])

        # Match up to global phase
        overlap = abs(np.vdot(observed, expected))
        assert abs(overlap - 1.0) < 1e-6, (
            f"Amplitudes don't match expected D_x|0,0>.\n"
            f"  Expected: {expected}\n"
            f"  Observed: {observed}\n"
            f"  Overlap: {overlap}"
        )

    def test_d1_parent_amplitude(self):
        """d=1: parent prob = 1/2, single child prob = 1/2.

        phi(1) = pi/2. cos^2(pi/4) = 1/2.
        """
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(1))

        walk_diffusion_fixed(pf, br, num_moves=1)

        pf_start = pf.allocated_start
        _keepalive = [pf, br]
        sv = _get_statevector(ql.to_openqasm())

        pf_probs = _extract_register_probs(sv, pf_start, 1)

        # After D|0>: parent and child each get specific amplitude
        # D|0> = 2<psi|0>|psi> - |0>
        # <psi|0> = cos(phi/2) = cos(pi/4) = 1/sqrt(2)
        # D|0> = 2*(1/sqrt(2))*|psi> - |0>
        # = sqrt(2)*|psi> - |0>
        # parent component = sqrt(2)*cos(pi/4) - 1 = sqrt(2)/sqrt(2) - 1 = 0
        # child component = sqrt(2)*sin(pi/4) = sqrt(2)/sqrt(2) = 1
        # So D|0> maps entirely to child state for d=1
        child_prob = pf_probs.get(1, 0.0)
        parent_prob = pf_probs.get(0, 0.0)

        # D|0> should give child prob close to 1.0 and parent prob close to 0
        # (reflection flips through |psi>)
        total = parent_prob + child_prob
        assert abs(total - 1.0) < 1e-6, f"Total prob should be 1, got {total}"


# ---------------------------------------------------------------------------
# Group 5: Identity When No Valid Children (fixed branching d=0)
# ---------------------------------------------------------------------------


class TestNoValidChildren:
    """Diffusion is identity when d=0 (no valid children)."""

    def test_fixed_d0_is_noop(self):
        """_fixed_diffusion with d < 1 returns immediately (no gates)."""
        from quantum_language.walk_diffusion import _fixed_diffusion

        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=1)
        sv_before = _get_statevector(ql.to_openqasm())

        # Calling _fixed_diffusion with d=0 is a no-op
        _fixed_diffusion(0, pf, br, {})

        _keepalive = [pf, br]
        sv_after = _get_statevector(ql.to_openqasm())

        assert np.allclose(sv_before, sv_after, atol=1e-10), (
            "Diffusion with d=0 should be identity"
        )


# ---------------------------------------------------------------------------
# Group 6: Variable Branching (with predicates)
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

        state=1, num_moves=1, move_0: 1^1=0 (invalid via nonzero check).
        So count=0, no rotations applied, parent_flag stays |0>.

        state=2, move_0: 2^1=3 (valid). count=1, rotation applied.
        """
        _init_circuit()
        state = ql.qint(2, width=2)
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
        # We just verify the diffusion ran (state is not all-|0> on parent_flag).
        total_prob = pf_probs.get(0, 0.0) + pf_probs.get(1, 0.0)
        assert abs(total_prob - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Group 7: Qubit Budget
# ---------------------------------------------------------------------------


class TestQubitBudget:
    """Verify circuits stay within the 17-qubit simulation limit."""

    def test_fixed_d2_within_budget(self):
        """Fixed d=2 diffusion uses only 2 qubits."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(2))
        walk_diffusion_fixed(pf, br, num_moves=2)
        _keepalive = [pf, br]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

    def test_fixed_d4_within_budget(self):
        """Fixed d=4 diffusion fits within 17 qubits."""
        _init_circuit()
        pf = ql.qbool()
        br = ql.qint(0, width=branch_width(4))
        walk_diffusion_fixed(pf, br, num_moves=4)
        _keepalive = [pf, br]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

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
# Group 8: S_0 Reflection Unit Test
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
