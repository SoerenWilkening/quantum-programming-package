"""Tests for walk_search.py: quantum walk search configuration.

Verifies the walk() public API:
- Returns (config, registers) tuple
- Config has is_marked set
- Registers are initialized at root
- walk_step with is_marked produces correct operator
- Walk step preserves norm
- Marked states get identity (unchanged by walk step)

All test circuits use <= 17 qubits.
"""

import gc

import numpy as np
import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import WalkConfig
from quantum_language.walk_operators import walk_step
from quantum_language.walk_registers import WalkRegisters
from quantum_language.walk_search import (
    _max_walk_iterations,
    _tree_size,
    _validate_walk_args,
    walk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return np.asarray(result.get_statevector())


# ---------------------------------------------------------------------------
# Walk callback helpers
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


def _walk_with_state(is_marked, max_depth, num_moves, state_width=2,
                     state_value=0, **kwargs):
    """Call walk() with required state/make_move/is_valid parameters.

    Creates a state register and calls walk() with the XOR move callbacks.
    Returns (config, registers, state).
    """
    state = ql.qint(state_value, width=state_width)
    config, regs = walk(
        is_marked, max_depth, num_moves, state,
        _make_move_xor, _is_valid_nonzero,
        undo_move=_undo_move_xor, **kwargs,
    )
    return config, regs, state


# ---------------------------------------------------------------------------
# Group 1: Tree Size Tests
# ---------------------------------------------------------------------------


class TestTreeSize:
    """Test _tree_size computation."""

    def test_binary_depth1(self):
        assert _tree_size(2, 1) == 3

    def test_binary_depth2(self):
        assert _tree_size(2, 2) == 7

    def test_binary_depth3(self):
        assert _tree_size(2, 3) == 15

    def test_ternary_depth2(self):
        assert _tree_size(3, 2) == 13

    def test_unary_depth5(self):
        assert _tree_size(1, 5) == 6


# ---------------------------------------------------------------------------
# Group 2: Iteration Count Tests
# ---------------------------------------------------------------------------


class TestIterationCount:
    """Test _max_walk_iterations computation."""

    def test_minimum_is_4(self):
        assert _max_walk_iterations(2, 1) >= 4

    def test_increases_with_tree_size(self):
        small = _max_walk_iterations(2, 2)
        large = _max_walk_iterations(2, 4)
        assert large >= small

    def test_binary_depth2(self):
        result = _max_walk_iterations(2, 2)
        assert result == 4


# ---------------------------------------------------------------------------
# Group 3: Validation Tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Argument validation for walk()."""

    def _dummy_state(self):
        _init_circuit()
        return ql.qint(0, width=1)

    def test_rejects_none_is_marked(self):
        s = self._dummy_state()
        with pytest.raises(ValueError, match="is_marked must not be None"):
            _validate_walk_args(None, 2, 2, s, _make_move_xor,
                                _is_valid_nonzero)

    def test_rejects_non_int_max_depth(self):
        s = self._dummy_state()
        with pytest.raises(TypeError, match="max_depth must be an int"):
            _validate_walk_args(lambda s: None, 2.0, 2, s, _make_move_xor,
                                _is_valid_nonzero)

    def test_rejects_non_int_num_moves(self):
        s = self._dummy_state()
        with pytest.raises(TypeError, match="num_moves must be an int"):
            _validate_walk_args(lambda s: None, 2, 2.0, s, _make_move_xor,
                                _is_valid_nonzero)

    def test_rejects_zero_max_depth(self):
        s = self._dummy_state()
        with pytest.raises(ValueError, match="max_depth must be >= 1"):
            _validate_walk_args(lambda s: None, 0, 2, s, _make_move_xor,
                                _is_valid_nonzero)

    def test_rejects_zero_num_moves(self):
        s = self._dummy_state()
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 0, s, _make_move_xor,
                                _is_valid_nonzero)

    def test_rejects_none_state(self):
        with pytest.raises(ValueError, match="state must not be None"):
            _validate_walk_args(lambda s: None, 2, 2, None, _make_move_xor,
                                _is_valid_nonzero)

    def test_rejects_none_make_move(self):
        s = self._dummy_state()
        with pytest.raises(ValueError, match="make_move must not be None"):
            _validate_walk_args(lambda s: None, 2, 2, s, None,
                                _is_valid_nonzero)

    def test_rejects_none_is_valid(self):
        s = self._dummy_state()
        with pytest.raises(ValueError, match="is_valid must not be None"):
            _validate_walk_args(lambda s: None, 2, 2, s, _make_move_xor,
                                None)

    def test_rejects_non_int_max_iterations(self):
        s = self._dummy_state()
        with pytest.raises(TypeError, match="max_iterations must be an int"):
            _validate_walk_args(lambda s: None, 2, 2, s, _make_move_xor,
                                _is_valid_nonzero, max_iterations=2.0)

    def test_rejects_zero_max_iterations(self):
        s = self._dummy_state()
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 2, s, _make_move_xor,
                                _is_valid_nonzero, max_iterations=0)

    def test_rejects_negative_max_iterations(self):
        s = self._dummy_state()
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 2, s, _make_move_xor,
                                _is_valid_nonzero, max_iterations=-1)

    def test_accepts_valid_max_iterations(self):
        """No exception for valid max_iterations=1."""
        s = self._dummy_state()
        _validate_walk_args(lambda s: None, 2, 2, s, _make_move_xor,
                            _is_valid_nonzero, max_iterations=1)

    def test_max_iterations_none_accepted(self):
        """None is the default and should be accepted."""
        s = self._dummy_state()
        _validate_walk_args(lambda s: None, 2, 2, s, _make_move_xor,
                            _is_valid_nonzero, max_iterations=None)


# ---------------------------------------------------------------------------
# Group 4: walk() Return Type Tests
# ---------------------------------------------------------------------------


class TestWalkReturnType:
    """walk() returns (WalkConfig, WalkRegisters) tuple."""

    def test_returns_tuple(self):
        """walk() returns a 2-tuple."""
        _init_circuit()
        state = ql.qint(0, width=2)
        result = walk(
            lambda s: s == 0, 1, 1, state,
            _make_move_xor, _is_valid_nonzero,
            undo_move=_undo_move_xor,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_walkconfig(self):
        """First element is a WalkConfig."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
        )
        assert isinstance(config, WalkConfig)

    def test_second_element_is_walkregisters(self):
        """Second element is WalkRegisters."""
        _init_circuit()
        _, registers, _ = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
        )
        assert isinstance(registers, WalkRegisters)

    def test_config_has_is_marked(self):
        """Config has is_marked set to the provided predicate."""
        pred = lambda s: s == 3
        _init_circuit()
        config, _, _ = _walk_with_state(pred, max_depth=1, num_moves=1)
        assert config.is_marked is pred

    def test_config_has_correct_depth(self):
        """Config has correct max_depth."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            lambda s: s == 0, max_depth=2, num_moves=1,
        )
        assert config.max_depth == 2

    def test_config_has_correct_num_moves(self):
        """Config has correct num_moves."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=2,
        )
        assert config.num_moves == 2

    def test_registers_initialized_at_root(self):
        """Registers are initialized (init_root called).

        Calling init_root() again should raise RuntimeError.
        """
        _init_circuit()
        _, registers, _ = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
        )
        with pytest.raises(RuntimeError, match="init_root.*already"):
            registers.init_root()

    def test_registers_match_config(self):
        """Registers config matches the returned config."""
        _init_circuit()
        config, registers, _ = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
        )
        assert registers.config is config

    def test_state_passed_through(self):
        """state parameter is passed to config."""
        _init_circuit()
        state = ql.qint(0, width=2)
        config, _ = walk(
            lambda s: s == 0, 1, 1, state, _make_move_xor,
            _is_valid_nonzero,
        )
        assert config.state is state

    def test_make_move_passed_through(self):
        """make_move parameter is passed to config."""
        fn = lambda s, m: None
        _init_circuit()
        state = ql.qint(0, width=1)
        config, _ = walk(
            lambda s: s == 0, 1, 1, state, fn, _is_valid_nonzero,
        )
        assert config.make_move is fn

    def test_is_valid_passed_through(self):
        """is_valid parameter is passed to config."""
        fn = lambda s: s != 0
        _init_circuit()
        state = ql.qint(0, width=1)
        config, _ = walk(
            lambda s: s == 0, 1, 1, state, _make_move_xor, fn,
        )
        assert config.is_valid is fn

    def test_undo_move_passed_through(self):
        """undo_move parameter is passed to config."""
        fn = lambda s, m: None
        _init_circuit()
        state = ql.qint(0, width=1)
        config, _ = walk(
            lambda s: s == 0, 1, 1, state, _make_move_xor,
            _is_valid_nonzero, undo_move=fn,
        )
        assert config.undo_move is fn


# ---------------------------------------------------------------------------
# Group 5: max_iterations edge cases
# ---------------------------------------------------------------------------


class TestMaxIterationsEdgeCases:
    """walk() max_iterations validation and behavior."""

    def test_max_iterations_zero_raises(self):
        _init_circuit()
        state = ql.qint(0, width=1)
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            walk(lambda s: False, 1, 1, state, _make_move_xor,
                 _is_valid_nonzero, max_iterations=0)

    def test_max_iterations_negative_raises(self):
        _init_circuit()
        state = ql.qint(0, width=1)
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            walk(lambda s: False, 1, 1, state, _make_move_xor,
                 _is_valid_nonzero, max_iterations=-1)

    def test_max_iterations_float_raises(self):
        _init_circuit()
        state = ql.qint(0, width=1)
        with pytest.raises(TypeError, match="max_iterations must be an int"):
            walk(lambda s: False, 1, 1, state, _make_move_xor,
                 _is_valid_nonzero, max_iterations=4.0)


# ---------------------------------------------------------------------------
# Group 6: Quantum Marking Integration Tests
# ---------------------------------------------------------------------------


class TestQuantumMarkingIntegration:
    """walk_step with is_marked produces correct operator behavior.

    When is_marked is set together with state on the config, the walk
    operators apply identity to marked nodes and standard diffusion to
    unmarked nodes (Montanaro 2015).
    """

    def test_walk_step_with_marking_preserves_norm(self):
        """Walk step with is_marked preserves statevector norm."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred = lambda s: s == 1

        config = WalkConfig(
            max_depth=1, num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred, state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [state]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Walk step with marking should preserve norm, got {norm}"
        )

    def test_walk_step_without_marking_preserves_norm(self):
        """Walk step without is_marked also preserves norm (baseline)."""
        _init_circuit()
        state = ql.qint(0, width=2)
        config = WalkConfig(
            max_depth=1, num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [state]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Walk step without marking should preserve norm, got {norm}"
        )

    def test_marking_changes_walk_dynamics(self):
        """Marking changes the walk operator vs the unmarked walk.

        The all-marked walk step (is_marked returns physical |1> via
        gate-level emit_x) acts as identity: root probability stays
        at 1.0 because diffusion is suppressed.  Without marking,
        the walk step applies diffusion normally.

        To prove the operator differs, we verify that (a) the
        all-marked step truly produces identity (root prob = 1.0)
        and (b) the marked and unmarked paths produce different QASM
        (different gate sequences).  Together these confirm that the
        marking predicate is wired into the walk operator correctly.

        Qubits: 2 height + 1 branch + 1 count + 2 state + ancillae <= 17
        """
        from quantum_language._gates import emit_x

        # All-marked walk step (identity): root prob should stay 1.0.
        _init_circuit()
        state_m = ql.qint(0, width=2)
        # Gate-level marking: always |1>, invisible to DSL tracker
        mark_flag = ql.qbool()
        emit_x(int(mark_flag.qubits[63]))

        config_m = WalkConfig(
            max_depth=1, num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=lambda s: mark_flag,
            state=state_m,
        )
        regs_m = WalkRegisters(config_m)
        regs_m.init_root()
        walk_step(config_m, regs_m)

        _keep_m = [regs_m, state_m, mark_flag]
        qasm_marked = ql.to_openqasm()
        sv_marked = _simulate_statevector(qasm_marked)

        h_root_m = int(regs_m.height_qubit(config_m.max_depth).qubits[63])
        flag_qubit_m = int(mark_flag.qubits[63])
        # Initial state: h_root=|1>, mark_flag=|1>, state=|00>
        initial_idx = (1 << h_root_m) | (1 << flag_qubit_m)
        marked_root_prob = float(abs(sv_marked[initial_idx]) ** 2)

        assert abs(marked_root_prob - 1.0) < 1e-6, (
            f"All-marked walk should be identity, "
            f"root_prob={marked_root_prob}"
        )

        # Unmarked walk step: no is_marked, diffusion runs normally.
        _init_circuit()
        state_u = ql.qint(0, width=2)
        config_u = WalkConfig(
            max_depth=1, num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state_u,
        )
        regs_u = WalkRegisters(config_u)
        regs_u.init_root()
        walk_step(config_u, regs_u)

        _keep_u = [regs_u, state_u]
        qasm_unmarked = ql.to_openqasm()
        sv_unmarked = _simulate_statevector(qasm_unmarked)
        assert abs(np.linalg.norm(sv_unmarked) - 1.0) < 1e-6

        # The two circuits must differ because the marked path wraps
        # the diffusion rotations with marking controls.
        assert qasm_marked != qasm_unmarked, (
            "Marked and unmarked walks should produce different QASM "
            "(marking adds control gates)"
        )

    def test_walk_returns_usable_config_and_registers(self):
        """walk() returns config/registers that can be used with walk_step."""
        _init_circuit()
        config, regs, state = _walk_with_state(
            lambda s: s == 3, max_depth=1, num_moves=1,
        )

        # Should be able to call walk_step without error
        walk_step(config, regs)

        _keepalive = [state]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6

    def test_walk_qubit_budget(self):
        """Walk registers fit within qubit budget.

        max_depth=3, num_moves=2: 4 height + 3 branch + 2 count = 9 <= 15
        """
        config = WalkConfig(max_depth=3, num_moves=2)
        total = config.total_walk_qubits()
        assert total <= 15, f"Walk uses {total} qubits"


# ---------------------------------------------------------------------------
# Group 7: Consistency Tests
# ---------------------------------------------------------------------------


class TestConsistency:
    """Consistency of walk() output."""

    def test_deterministic_config(self):
        """walk() produces consistent config across runs."""
        pred = lambda s: s == 0
        configs = []
        for _ in range(3):
            _init_circuit()
            c, _, _ = _walk_with_state(pred, max_depth=1, num_moves=1)
            configs.append(c)
        assert all(c.max_depth == 1 for c in configs)
        assert all(c.num_moves == 1 for c in configs)
        assert all(c.is_marked is pred for c in configs)

    def test_walk_importable(self):
        """walk is importable from quantum_language."""
        from quantum_language import walk as w
        assert callable(w)
