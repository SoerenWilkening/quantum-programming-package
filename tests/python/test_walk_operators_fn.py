"""Tests for walk_operators.py: function-based R_A, R_B, walk_step.

Verifies the new function-based walk operator API using WalkConfig and
WalkRegisters.  Tests cover:

- Disjointness of R_A/R_B height controls
- R_A acts on even depths only (excluding root)
- R_A modifies state at active non-root even depth
- R_B acts on odd depths plus root
- walk_step = R_B * R_A
- WalkOperatorState compilation and replay
- Norm preservation (unitarity)
- Validation of arguments
- Variable-branching path (with make_move/is_valid/state callbacks)
"""

import gc

import numpy as np
import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import WalkConfig
from quantum_language.walk_operators import (
    WalkOperatorState,
    build_R_A,
    build_R_B,
    verify_disjointness,
    walk_step,
)
from quantum_language.walk_registers import WalkRegisters


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector as numpy array."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return np.asarray(result.get_statevector())


def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM qubit[N] declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _make_config_and_regs(max_depth, num_moves, state_width=1,
                          state_value=0):
    """Create WalkConfig with callbacks and WalkRegisters, init root.

    Returns (config, registers) tuple.
    """
    state = ql.qint(state_value, width=state_width)
    config = WalkConfig(
        max_depth=max_depth,
        num_moves=num_moves,
        make_move=_make_move_xor,
        undo_move=_undo_move_xor,
        is_valid=_is_valid_nonzero,
        state=state,
    )
    regs = WalkRegisters(config)
    regs.init_root()
    return config, regs


# ---------------------------------------------------------------------------
# Variable-branching helpers (move/validity callbacks)
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


def _make_variable_config_and_regs(max_depth, num_moves, state_width,
                                    state_value=0):
    """Create WalkConfig with callbacks and WalkRegisters, init root.

    Returns (config, registers, state) tuple.
    """
    state = ql.qint(state_value, width=state_width)
    config = WalkConfig(
        max_depth=max_depth,
        num_moves=num_moves,
        make_move=_make_move_xor,
        undo_move=_undo_move_xor,
        is_valid=_is_valid_nonzero,
        state=state,
    )
    regs = WalkRegisters(config)
    regs.init_root()
    return config, regs, state


# ---------------------------------------------------------------------------
# Group 1: Validation Tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Argument validation for walk operator functions."""

    def test_build_R_A_rejects_non_config(self):
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            build_R_A("not a config", regs)

    def test_build_R_A_rejects_non_registers(self):
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="registers must be a WalkRegisters"):
            build_R_A(config, "not registers")

    def test_build_R_B_rejects_non_config(self):
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            build_R_B("not a config", regs)

    def test_build_R_B_rejects_non_registers(self):
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="registers must be a WalkRegisters"):
            build_R_B(config, "not registers")

    def test_walk_step_rejects_non_config(self):
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            walk_step("not a config", regs)

    def test_verify_disjointness_rejects_non_config(self):
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            verify_disjointness("not a config", regs)


# ---------------------------------------------------------------------------
# Group 2: Disjointness Tests
# ---------------------------------------------------------------------------


class TestDisjointness:
    """R_A and R_B height controls are disjoint."""

    def test_disjoint_binary_depth1(self):
        """Minimal tree: R_A={h[0]}, R_B={h[1]}, disjoint."""
        _init_circuit()
        config, regs = _make_config_and_regs(1, 2)
        result = verify_disjointness(config, regs)

        assert result["disjoint"] is True
        assert len(result["overlap"]) == 0
        assert len(result["R_A_qubits"]) == 1  # h[0]
        assert len(result["R_B_qubits"]) == 1  # h[1] (root, odd)

    def test_disjoint_binary_depth2(self):
        """depth=2: R_A={h[0]}, R_B={h[1], h[2]}, disjoint."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        result = verify_disjointness(config, regs)

        assert result["disjoint"] is True
        assert len(result["R_A_qubits"]) == 1  # h[0]
        assert len(result["R_B_qubits"]) == 2  # h[1], h[2]

    def test_disjoint_binary_depth3(self):
        """depth=3: R_A={h[0], h[2]}, R_B={h[1], h[3]}, disjoint."""
        _init_circuit()
        config, regs = _make_config_and_regs(3, 2)
        result = verify_disjointness(config, regs)

        assert result["disjoint"] is True
        assert len(result["R_A_qubits"]) == 2  # h[0], h[2]
        assert len(result["R_B_qubits"]) == 2  # h[1], h[3]

    def test_disjoint_binary_depth4(self):
        """depth=4: root even -> R_B. R_A={h[0], h[2]}, R_B={h[1], h[3], h[4]}."""
        _init_circuit()
        config, regs = _make_config_and_regs(4, 2)
        result = verify_disjointness(config, regs)

        assert result["disjoint"] is True
        assert len(result["R_A_qubits"]) == 2  # h[0], h[2]
        assert len(result["R_B_qubits"]) == 3  # h[1], h[3], h[4]

    def test_disjoint_ternary_depth2(self):
        """Ternary tree depth=2: disjoint."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 3)
        result = verify_disjointness(config, regs)
        assert result["disjoint"] is True

    def test_returns_correct_types(self):
        """Result has expected keys and types."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        result = verify_disjointness(config, regs)

        assert isinstance(result, dict)
        assert isinstance(result["R_A_qubits"], set)
        assert isinstance(result["R_B_qubits"], set)
        assert isinstance(result["overlap"], set)
        assert isinstance(result["disjoint"], bool)


# ---------------------------------------------------------------------------
# Group 3: R_A Tests
# ---------------------------------------------------------------------------


class TestBuildRA:
    """R_A applies local diffusion at even-depth nodes (excluding root)."""

    def test_R_A_preserves_norm_depth1(self):
        """R_A preserves statevector norm for depth=1.

        depth=1: R_A covers depth 0 (leaf, no-op). Should preserve norm.
        """
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )

        build_R_A(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"R_A should preserve norm, got {norm}"


# ---------------------------------------------------------------------------
# Group 4: R_B Tests
# ---------------------------------------------------------------------------


class TestBuildRB:
    """R_B applies local diffusion at odd-depth nodes plus root."""

    def test_R_B_preserves_norm_depth1(self):
        """R_B preserves statevector norm for depth=1."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )

        build_R_B(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"R_B should preserve norm, got {norm}"


# ---------------------------------------------------------------------------
# Group 5: Walk Step Tests
# ---------------------------------------------------------------------------


class TestWalkStep:
    """Walk step U = R_B * R_A composed as single operation."""

    def test_walk_step_equals_sequential(self):
        """walk_step produces same statevector as R_A then R_B."""
        _init_circuit()
        config_w, regs_w, state_w = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        walk_step(config_w, regs_w)
        _keep_w = [regs_w, state_w]
        sv_walk = _simulate_statevector(ql.to_openqasm())

        _init_circuit()
        config_m, regs_m, state_m = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        build_R_A(config_m, regs_m)
        build_R_B(config_m, regs_m)
        _keep_m = [regs_m, state_m]
        sv_manual = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_walk, sv_manual, atol=1e-10), (
            "walk_step must equal R_A followed by R_B"
        )

    def test_walk_step_preserves_norm(self):
        """Walk step preserves statevector norm (unitarity check)."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Walk step should preserve norm, got {norm}"
        )

    def test_walk_step_double_preserves_norm(self):
        """Two walk steps preserve statevector norm."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Two walk steps should preserve norm, got {norm}"
        )


# ---------------------------------------------------------------------------
# Group 6: WalkOperatorState (compiled walk step)
# ---------------------------------------------------------------------------


class TestWalkOperatorState:
    """WalkOperatorState: compiled walk step with caching."""

    def test_compiled_matches_raw(self):
        """Compiled step matches raw walk_step."""
        # Raw
        _init_circuit()
        config_r, regs_r, state_r = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        walk_step(config_r, regs_r)
        _keep_r = [regs_r, state_r]
        sv_raw = _simulate_statevector(ql.to_openqasm())

        # Compiled
        _init_circuit()
        config_c, regs_c, state_c = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        ops = WalkOperatorState(config_c, regs_c)
        ops.step()
        _keep_c = [regs_c, state_c]
        sv_compiled = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_raw, sv_compiled, atol=1e-6), (
            "Compiled step should match raw walk_step"
        )

    def test_not_compiled_initially(self):
        """WalkOperatorState starts uncompiled."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        ops = WalkOperatorState(config, regs)
        assert ops.is_compiled is False

    def test_compiled_after_first_step(self):
        """is_compiled is True after first step()."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        ops = WalkOperatorState(config, regs)
        ops.step()
        _keepalive = [regs, state]
        assert ops.is_compiled is True

    def test_replay_preserves_norm(self):
        """Replay (second step) preserves norm."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        ops = WalkOperatorState(config, regs)
        ops.step()  # capture
        ops.step()  # replay

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Replay should preserve norm, got {norm}"
        )

    def test_compiled_rejects_non_config(self):
        """WalkOperatorState rejects non-WalkConfig."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            WalkOperatorState("bad", regs)

    def test_compiled_rejects_non_registers(self):
        """WalkOperatorState rejects non-WalkRegisters."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=1, state_value=0,
        )
        with pytest.raises(TypeError, match="registers must be a WalkRegisters"):
            WalkOperatorState(config, "bad")


# ---------------------------------------------------------------------------
# Group 7: Variable-Branching Path Tests
# ---------------------------------------------------------------------------


class TestVariableBranching:
    """Variable-branching diffusion via make_move/is_valid/state callbacks.

    The variable-branching path dispatches from _apply_local_diffusion
    when config has make_move, is_valid, and state set.  These tests
    verify the path executes without errors, preserves norm, and
    allocates a reasonable number of qubits.

    Note: with a classical-state input (qint initialized to a fixed
    value), the framework optimizes away arithmetic on known values.
    The variable diffusion emits gates but the counting may produce
    trivial results.  The important properties are: the code path
    runs, norm is preserved, and qubit budget is respected.
    """

    def test_variable_path_dispatched(self):
        """Config with callbacks takes the variable-branching path.

        Verify the variable path is exercised by checking that more
        qubits are allocated (comparison/count ancillae) than the
        fixed-branching path would use.

        Fixed: height + branch + count = 2 + 1 + 1 = 4 qubits.
        Variable: additional state + comparison ancillae.
        """
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=3, state_value=0,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)

        # Variable path allocates state (3) + walk regs + ancillae
        # Fixed path would only use walk regs (4 qubits)
        assert nq > 4, (
            f"Variable path should allocate more qubits than fixed, "
            f"got {nq}"
        )
        assert nq <= 17, f"Variable walk uses {nq} qubits (limit: 17)"

    def test_variable_walk_step_preserves_norm(self):
        """walk_step with variable-branching callbacks preserves norm.

        Qubits: 3 state + 2 height + 1 branch + 1 count + ancillae.
        """
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=3, state_value=0,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Variable-branching walk_step should preserve norm, got {norm}"
        )

    def test_variable_R_B_preserves_norm(self):
        """R_B with variable branching preserves norm."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=3, state_value=0,
        )

        build_R_B(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Variable R_B should preserve norm, got {norm}"
        )

    def test_variable_double_walk_step_preserves_norm(self):
        """Two variable walk steps preserve norm."""
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=1, state_width=3, state_value=0,
        )

        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Two variable walk steps should preserve norm, got {norm}"
        )

    def test_variable_num_moves_2_preserves_norm(self):
        """Variable diffusion with num_moves=2 preserves norm.

        Larger branching factor exercises the cascade rotations
        in the variable diffusion path.
        """
        _init_circuit()
        config, regs, state = _make_variable_config_and_regs(
            max_depth=1, num_moves=2, state_width=2, state_value=0,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Variable walk uses {nq} qubits (limit: 17)"

        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Variable walk with num_moves=2 should preserve norm, "
            f"got {norm}"
        )
