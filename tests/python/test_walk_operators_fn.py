"""Tests for walk_operators.py: function-based R_A, R_B, walk_step.

Verifies the new function-based walk operator API using WalkConfig and
WalkRegisters.  Tests cover:

- Disjointness of R_A/R_B height controls
- R_A acts on even depths only (excluding root)
- R_B acts on odd depths plus root
- walk_step = R_B * R_A
- WalkOperatorState compilation and replay
- Norm preservation (unitarity)
- Validation of arguments
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


def _make_config_and_regs(max_depth, num_moves):
    """Create WalkConfig and WalkRegisters, init root.

    Returns (config, registers) tuple.
    """
    config = WalkConfig(max_depth=max_depth, num_moves=num_moves)
    regs = WalkRegisters(config)
    regs.init_root()
    return config, regs


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

    def test_R_A_identity_on_root_depth2(self):
        """R_A on depth=2 tree: even depths 0 (leaf, no-op) and 2 (root, excluded).

        R_A should have no effect on root state.
        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        sv_before = _simulate_statevector(ql.to_openqasm())

        build_R_A(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_before, sv_after, atol=1e-10), (
            "R_A should not affect root state for depth=2"
        )

    def test_R_A_nontrivial_depth3(self):
        """R_A on depth=3: even depth 2 is non-leaf, non-root.

        R_A should apply diffusion at depth 2 (controlled on h[2]).
        But since the walk starts at root (h[3]=1), and depth 2 is
        not active, R_A is still identity on root state.
        Qubits: 4 height + 3 branch + 1 count = 8 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(3, 2)
        sv_before = _simulate_statevector(ql.to_openqasm())

        build_R_A(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        # From root state, R_A has no effect because h[0] and h[2]
        # are both |0> (only h[3] is |1>)
        assert np.allclose(sv_before, sv_after, atol=1e-10), (
            "R_A should not affect root state (only even non-root depths)"
        )

    def test_R_A_preserves_norm(self):
        """R_A preserves statevector norm."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)

        build_R_A(config, regs)

        _keepalive = [regs]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"R_A should preserve norm, got {norm}"


# ---------------------------------------------------------------------------
# Group 4: R_B Tests
# ---------------------------------------------------------------------------


class TestBuildRB:
    """R_B applies local diffusion at odd-depth nodes plus root."""

    def test_R_B_modifies_root_depth2(self):
        """R_B on depth=2: includes root diffusion (depth 2, even but added).

        R_B should modify root state.
        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        sv_before = _simulate_statevector(ql.to_openqasm())

        build_R_B(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert not np.allclose(sv_before, sv_after, atol=1e-6), (
            "R_B should modify root state (includes root diffusion)"
        )

    def test_R_B_modifies_root_depth3(self):
        """R_B on depth=3: root at odd depth, included naturally.

        Qubits: 4 height + 3 branch + 1 count = 8 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(3, 2)
        sv_before = _simulate_statevector(ql.to_openqasm())

        build_R_B(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert not np.allclose(sv_before, sv_after, atol=1e-6), (
            "R_B should modify root state (root at odd depth)"
        )

    def test_R_B_preserves_norm(self):
        """R_B preserves statevector norm."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)

        build_R_B(config, regs)

        _keepalive = [regs]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"R_B should preserve norm, got {norm}"


# ---------------------------------------------------------------------------
# Group 5: Walk Step Tests
# ---------------------------------------------------------------------------


class TestWalkStep:
    """Walk step U = R_B * R_A composed as single operation."""

    def test_walk_step_equals_sequential(self):
        """walk_step produces same statevector as R_A then R_B.

        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config_w, regs_w = _make_config_and_regs(2, 2)
        walk_step(config_w, regs_w)
        _keep_w = [regs_w]
        sv_walk = _simulate_statevector(ql.to_openqasm())

        _init_circuit()
        config_m, regs_m = _make_config_and_regs(2, 2)
        build_R_A(config_m, regs_m)
        build_R_B(config_m, regs_m)
        _keep_m = [regs_m]
        sv_manual = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_walk, sv_manual, atol=1e-10), (
            "walk_step must equal R_A followed by R_B"
        )

    def test_walk_step_modifies_root(self):
        """Walk step modifies root state.

        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        sv_before = _simulate_statevector(ql.to_openqasm())

        walk_step(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert not np.allclose(sv_before, sv_after, atol=1e-6), (
            "Walk step should modify root state"
        )

    def test_walk_step_preserves_norm(self):
        """Walk step preserves statevector norm (unitarity check).

        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        walk_step(config, regs)

        _keepalive = [regs]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Walk step should preserve norm, got {norm}"
        )

    def test_walk_step_not_identity_squared(self):
        """U^2 != I (walk step is not a reflection).

        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        sv_initial = _simulate_statevector(ql.to_openqasm())

        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert not np.allclose(sv_initial, sv_after, atol=1e-6), (
            "U^2 should not equal identity"
        )

    def test_walk_step_ternary_depth2(self):
        """Walk step on ternary tree depth=2 modifies root state.

        Qubits: 3 height + 4 branch + 2 count = 9 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 3)
        sv_before = _simulate_statevector(ql.to_openqasm())

        walk_step(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert not np.allclose(sv_before, sv_after, atol=1e-6)

    def test_walk_step_binary_depth3(self):
        """Walk step on binary tree depth=3.

        Qubits: 4 height + 3 branch + 1 count = 8 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(3, 2)
        sv_before = _simulate_statevector(ql.to_openqasm())

        walk_step(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert not np.allclose(sv_before, sv_after, atol=1e-6)

    def test_walk_step_double_preserves_norm(self):
        """Two walk steps preserve statevector norm.

        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs]
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
        """Compiled step matches raw walk_step.

        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        # Raw
        _init_circuit()
        config_r, regs_r = _make_config_and_regs(2, 2)
        walk_step(config_r, regs_r)
        _keep_r = [regs_r]
        sv_raw = _simulate_statevector(ql.to_openqasm())

        # Compiled
        _init_circuit()
        config_c, regs_c = _make_config_and_regs(2, 2)
        ops = WalkOperatorState(config_c, regs_c)
        ops.step()
        _keep_c = [regs_c]
        sv_compiled = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_raw, sv_compiled, atol=1e-6), (
            "Compiled step should match raw walk_step"
        )

    def test_not_compiled_initially(self):
        """WalkOperatorState starts uncompiled."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        ops = WalkOperatorState(config, regs)
        assert ops.is_compiled is False

    def test_compiled_after_first_step(self):
        """is_compiled is True after first step()."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        ops = WalkOperatorState(config, regs)
        ops.step()
        _keepalive = [regs]
        assert ops.is_compiled is True

    def test_replay_preserves_norm(self):
        """Replay (second step) preserves norm.

        Qubits: 3 height + 2 branch + 1 count = 6 <= 17.
        """
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        ops = WalkOperatorState(config, regs)
        ops.step()  # capture
        ops.step()  # replay

        _keepalive = [regs]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Replay should preserve norm, got {norm}"
        )

    def test_compiled_rejects_non_config(self):
        """WalkOperatorState rejects non-WalkConfig."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            WalkOperatorState("bad", regs)

    def test_compiled_rejects_non_registers(self):
        """WalkOperatorState rejects non-WalkRegisters."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        with pytest.raises(TypeError, match="registers must be a WalkRegisters"):
            WalkOperatorState(config, "bad")


# ---------------------------------------------------------------------------
# Group 7: Qubit Budget
# ---------------------------------------------------------------------------


class TestQubitBudget:
    """Walk operators stay within the 17-qubit simulation limit."""

    def test_depth2_binary_within_budget(self):
        """Binary depth=2: 3 + 2 + 1 = 6 qubits."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 2)
        walk_step(config, regs)
        _keepalive = [regs]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

    def test_depth3_binary_within_budget(self):
        """Binary depth=3: 4 + 3 + 1 = 8 qubits."""
        _init_circuit()
        config, regs = _make_config_and_regs(3, 2)
        walk_step(config, regs)
        _keepalive = [regs]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

    def test_depth2_ternary_within_budget(self):
        """Ternary depth=2: 3 + 4 + 2 = 9 qubits."""
        _init_circuit()
        config, regs = _make_config_and_regs(2, 3)
        walk_step(config, regs)
        _keepalive = [regs]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"
