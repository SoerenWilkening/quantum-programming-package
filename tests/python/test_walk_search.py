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

    def test_rejects_none_is_marked(self):
        with pytest.raises(ValueError, match="is_marked must not be None"):
            _validate_walk_args(None, 2, 2)

    def test_rejects_non_int_max_depth(self):
        with pytest.raises(TypeError, match="max_depth must be an int"):
            _validate_walk_args(lambda s: None, 2.0, 2)

    def test_rejects_non_int_num_moves(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            _validate_walk_args(lambda s: None, 2, 2.0)

    def test_rejects_zero_max_depth(self):
        with pytest.raises(ValueError, match="max_depth must be >= 1"):
            _validate_walk_args(lambda s: None, 0, 2)

    def test_rejects_zero_num_moves(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 0)

    def test_rejects_non_int_max_iterations(self):
        with pytest.raises(TypeError, match="max_iterations must be an int"):
            _validate_walk_args(lambda s: None, 2, 2, max_iterations=2.0)

    def test_rejects_zero_max_iterations(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 2, max_iterations=0)

    def test_rejects_negative_max_iterations(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            _validate_walk_args(lambda s: None, 2, 2, max_iterations=-1)

    def test_accepts_valid_max_iterations(self):
        """No exception for valid max_iterations=1."""
        _validate_walk_args(lambda s: None, 2, 2, max_iterations=1)

    def test_max_iterations_none_accepted(self):
        """None is the default and should be accepted."""
        _validate_walk_args(lambda s: None, 2, 2, max_iterations=None)


# ---------------------------------------------------------------------------
# Group 4: walk() Return Type Tests
# ---------------------------------------------------------------------------


class TestWalkReturnType:
    """walk() returns (WalkConfig, WalkRegisters) tuple."""

    def test_returns_tuple(self):
        """walk() returns a 2-tuple.

        Qubits: 3 height + 2 branch + 2 count = 7 <= 17
        """
        result = walk(lambda s: s == 0, max_depth=2, num_moves=2)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_walkconfig(self):
        """First element is a WalkConfig."""
        config, _ = walk(lambda s: s == 0, max_depth=2, num_moves=2)
        assert isinstance(config, WalkConfig)

    def test_second_element_is_walkregisters(self):
        """Second element is WalkRegisters."""
        _, registers = walk(lambda s: s == 0, max_depth=2, num_moves=2)
        assert isinstance(registers, WalkRegisters)

    def test_config_has_is_marked(self):
        """Config has is_marked set to the provided predicate."""
        pred = lambda s: s == 3
        config, _ = walk(pred, max_depth=2, num_moves=2)
        assert config.is_marked is pred

    def test_config_has_correct_depth(self):
        """Config has correct max_depth."""
        config, _ = walk(lambda s: s == 0, max_depth=3, num_moves=2)
        assert config.max_depth == 3

    def test_config_has_correct_num_moves(self):
        """Config has correct num_moves."""
        config, _ = walk(lambda s: s == 0, max_depth=2, num_moves=3)
        assert config.num_moves == 3

    def test_registers_initialized_at_root(self):
        """Registers are initialized (init_root called).

        Calling init_root() again should raise RuntimeError.
        """
        _, registers = walk(lambda s: s == 0, max_depth=2, num_moves=2)
        with pytest.raises(RuntimeError, match="init_root.*already"):
            registers.init_root()

    def test_registers_match_config(self):
        """Registers config matches the returned config."""
        config, registers = walk(
            lambda s: s == 0, max_depth=2, num_moves=2,
        )
        assert registers.config is config

    def test_state_passed_through(self):
        """state parameter is passed to config and usable with walk_step.

        Verifies that the state register survives walk() (is not
        invalidated) and that walk_step with marking produces a
        different operator than the standard unmarked walk.

        Qubits: 3 height + 2 branch + 2 count + 2 state = 9 + ancillas <= 17
        """
        # Unmarked baseline
        _init_circuit()
        config_std = WalkConfig(max_depth=2, num_moves=2)
        regs_std = WalkRegisters(config_std)
        regs_std.init_root()
        walk_step(config_std, regs_std)
        sv_std = _simulate_statevector(ql.to_openqasm())

        # Marked walk via walk() with pre-existing state register
        _init_circuit()
        state = ql.qint(0, width=2)
        config, regs = walk(
            lambda s: s == 0, max_depth=2, num_moves=2, state=state,
        )
        assert config.state is state
        walk_step(config, regs)
        _keepalive = [state]
        sv_marked = _simulate_statevector(ql.to_openqasm())

        # Both should be valid unit vectors
        assert abs(np.linalg.norm(sv_std) - 1.0) < 1e-6
        assert abs(np.linalg.norm(sv_marked) - 1.0) < 1e-6

        # They should differ because marking changes the operator
        min_len = min(len(sv_std), len(sv_marked))
        assert not np.allclose(
            sv_std[:min_len], sv_marked[:min_len], atol=1e-3,
        ), "walk() with state should produce marked walk, not standard"

    def test_make_move_passed_through(self):
        """make_move parameter is passed to config."""
        fn = lambda s, m: None
        config, _ = walk(
            lambda s: s == 0, max_depth=2, num_moves=2, make_move=fn,
        )
        assert config.make_move is fn

    def test_is_valid_passed_through(self):
        """is_valid parameter is passed to config."""
        fn = lambda s: s != 0
        config, _ = walk(
            lambda s: s == 0, max_depth=2, num_moves=2, is_valid=fn,
        )
        assert config.is_valid is fn


# ---------------------------------------------------------------------------
# Group 5: max_iterations edge cases
# ---------------------------------------------------------------------------


class TestMaxIterationsEdgeCases:
    """walk() max_iterations validation and behavior."""

    def test_max_iterations_zero_raises(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            walk(lambda s: False, max_depth=2, num_moves=2,
                 max_iterations=0)

    def test_max_iterations_negative_raises(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            walk(lambda s: False, max_depth=2, num_moves=2,
                 max_iterations=-1)

    def test_max_iterations_float_raises(self):
        with pytest.raises(TypeError, match="max_iterations must be an int"):
            walk(lambda s: False, max_depth=2, num_moves=2,
                 max_iterations=4.0)


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
        """Walk step with is_marked preserves statevector norm.

        Qubits: 4 height + 3 branch + 2 count + 4 state = 13 <= 17
        """
        _init_circuit()
        state = ql.qint(0, width=4)
        pred = lambda s: s == 5

        config = WalkConfig(
            max_depth=3, num_moves=2,
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
        """Walk step without is_marked also preserves norm (baseline).

        Qubits: 3 height + 2 branch + 2 count = 7 <= 17
        """
        _init_circuit()
        config = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Walk step without marking should preserve norm, got {norm}"
        )

    def test_marking_changes_walk_dynamics(self):
        """Walk step with marking differs from walk step without marking.

        When is_marked and state are both set, the walk step applies
        identity to marked nodes (D_x = I) and standard diffusion to
        unmarked nodes.  This produces a different operator than the
        fully unmarked walk.

        Qubits: 3 height + 2 branch + 2 count + 2 state = 9 + ancillas <= 17
        """
        # Unmarked walk
        _init_circuit()
        config_std = WalkConfig(max_depth=2, num_moves=2)
        regs_std = WalkRegisters(config_std)
        regs_std.init_root()
        walk_step(config_std, regs_std)
        sv_std = _simulate_statevector(ql.to_openqasm())

        # Marked walk (with state, some nodes marked)
        _init_circuit()
        state = ql.qint(0, width=2)
        config_marked = WalkConfig(
            max_depth=2, num_moves=2,
            is_marked=lambda s: s == 0, state=state,
        )
        regs_marked = WalkRegisters(config_marked)
        regs_marked.init_root()
        walk_step(config_marked, regs_marked)
        _keepalive = [state]
        sv_marked = _simulate_statevector(ql.to_openqasm())

        # Both should be valid unit vectors
        assert abs(np.linalg.norm(sv_std) - 1.0) < 1e-6
        assert abs(np.linalg.norm(sv_marked) - 1.0) < 1e-6

        # They should differ because marking changes the operator
        min_len = min(len(sv_std), len(sv_marked))
        assert not np.allclose(
            sv_std[:min_len], sv_marked[:min_len], atol=1e-3,
        ), "Marked walk should differ from unmarked walk"

    def test_no_marking_gives_standard_walk(self):
        """Without is_marked, walk step is the standard walk.

        Config without is_marked should produce same result as a
        config that has never heard of marking.

        Qubits: 3 height + 2 branch + 2 count = 7 <= 17
        """
        # Standard walk (no marking)
        _init_circuit()
        config_std = WalkConfig(max_depth=2, num_moves=2)
        regs_std = WalkRegisters(config_std)
        regs_std.init_root()
        walk_step(config_std, regs_std)
        sv_std = _simulate_statevector(ql.to_openqasm())

        # Walk with is_marked=None (default)
        _init_circuit()
        config_none = WalkConfig(max_depth=2, num_moves=2, is_marked=None)
        regs_none = WalkRegisters(config_none)
        regs_none.init_root()
        walk_step(config_none, regs_none)
        sv_none = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_std, sv_none, atol=1e-10), (
            "Walk without marking should match standard walk"
        )

    def test_walk_returns_usable_config_and_registers(self):
        """walk() returns config/registers that can be used with walk_step.

        Qubits: 3 height + 2 branch + 2 count = 7 <= 17
        """
        config, regs = walk(lambda s: s == 3, max_depth=2, num_moves=2)

        # Should be able to call walk_step without error
        walk_step(config, regs)

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
        """walk() produces consistent config across runs.

        Qubits: 7 <= 17
        """
        pred = lambda s: s == 0
        configs = []
        for _ in range(3):
            c, _ = walk(pred, max_depth=2, num_moves=2)
            configs.append(c)
        assert all(c.max_depth == 2 for c in configs)
        assert all(c.num_moves == 2 for c in configs)
        assert all(c.is_marked is pred for c in configs)

    def test_walk_importable(self):
        """walk is importable from quantum_language."""
        from quantum_language import walk as w
        assert callable(w)
