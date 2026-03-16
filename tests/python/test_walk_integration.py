"""Walk integration tests: end-to-end on complete tiny problems.

Exercises walk() and walk_diffusion() on realistic SAT-like problems,
verifying:
- walk() returns (WalkConfig, WalkRegisters) with is_marked set
- walk_step with marking produces valid unitary operator
- walk_diffusion usable standalone
- Custom walk via diffusion building block

All circuits stay within the 17-qubit simulation limit.

[Quantum_Assembly-nvx]
"""

import gc

import numpy as np
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import (
    WalkConfig,
    branch_width,
)
from quantum_language.walk_diffusion import (
    walk_diffusion,
    walk_diffusion_with_regs,
)
from quantum_language.walk_operators import walk_step
from quantum_language.walk_registers import WalkRegisters
from quantum_language.walk_search import walk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()
    ql.option('simulate', True)


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector."""
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
    result_bits = bitstring[msb_pos:lsb_pos + 1]
    return int(result_bits, 2)


# ---------------------------------------------------------------------------
# Walk callback helpers
# ---------------------------------------------------------------------------


def _make_move_xor(state, move_idx):
    """Apply move by XORing state with (move_idx + 1)."""
    state ^= (move_idx + 1)


def _undo_move_xor(state, move_idx):
    """Undo XOR move (XOR is self-inverse)."""
    state ^= (move_idx + 1)


def _is_valid_nonzero_walk(state):
    """Validity predicate: valid when state != 0."""
    return state != 0


def _walk_with_state(is_marked, max_depth, num_moves, state_width=2,
                     state_value=0, **kwargs):
    """Call walk() with required state/make_move/is_valid parameters.

    Creates a state register and calls walk(). Returns (config, regs, state).
    """
    state = ql.qint(state_value, width=state_width)
    config, regs = walk(
        is_marked, max_depth, num_moves, state,
        _make_move_xor, _is_valid_nonzero_walk,
        undo_move=_undo_move_xor, **kwargs,
    )
    return config, regs, state


# ---------------------------------------------------------------------------
# SAT predicate helpers
# ---------------------------------------------------------------------------


def _sat_2var_satisfiable(state):
    """2-variable SAT: (x0 OR x1) AND (NOT x0 OR x1).

    Variables encoded in branch pattern bits:
        bit 0 = x0, bit 1 = x1

    Truth table:
        x0=0, x1=0 -> (0|0) & (1|0) = 0 & 1 = False
        x0=1, x1=0 -> (1|0) & (0|0) = 1 & 0 = False
        x0=0, x1=1 -> (0|1) & (1|1) = 1 & 1 = True  (solution)
        x0=1, x1=1 -> (1|1) & (0|1) = 1 & 1 = True  (solution)

    2 satisfying assignments out of 4.
    """
    x0 = (state >> 0) & 1
    x1 = (state >> 1) & 1
    clause1 = x0 | x1
    clause2 = (1 - x0) | x1
    return bool(clause1 and clause2)


def _sat_2var_unsatisfiable(state):
    """2-variable SAT: (x0) AND (NOT x0).

    Always unsatisfiable: x0 and (not x0) can never both be true.

    Truth table:
        x0=0, x1=0 -> 0 & 1 = False
        x0=1, x1=0 -> 1 & 0 = False
        x0=0, x1=1 -> 0 & 1 = False
        x0=1, x1=1 -> 1 & 0 = False
    """
    x0 = (state >> 0) & 1
    return bool(x0 and (not x0))


def _sat_2var_all_satisfy(state):
    """Tautology: always true (all assignments satisfy).

    Truth table: all 4 assignments are marked.
    """
    return True


def _sat_single_solution(state):
    """Exactly one solution: state == 2 (x0=0, x1=1).

    Marks only the pattern 0b10 = 2.
    """
    return state == 2


# ---------------------------------------------------------------------------
# Group 1: walk() Returns Correct Config and Registers
# ---------------------------------------------------------------------------


class TestWalkReturnsConfigAndRegisters:
    """walk() returns (WalkConfig, WalkRegisters) with correct setup.

    Tree: max_depth=2, num_moves=2
    Walk qubits: 3 height + 2 branch + 2 count = 7 <= 17
    """

    def test_returns_tuple(self):
        """walk() returns a 2-tuple."""
        _init_circuit()
        state = ql.qint(0, width=2)
        result = walk(
            lambda s: s == 0, 1, 1, state,
            _make_move_xor, _is_valid_nonzero_walk,
            undo_move=_undo_move_xor,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_config_type(self):
        """First element is WalkConfig."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            _sat_2var_satisfiable, max_depth=1, num_moves=1,
        )
        assert isinstance(config, WalkConfig)

    def test_registers_type(self):
        """Second element is WalkRegisters."""
        _init_circuit()
        _, regs, _ = _walk_with_state(
            _sat_2var_satisfiable, max_depth=1, num_moves=1,
        )
        assert isinstance(regs, WalkRegisters)

    def test_config_has_is_marked(self):
        """Config has is_marked set to the SAT predicate."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            _sat_2var_satisfiable, max_depth=1, num_moves=1,
        )
        assert config.is_marked is _sat_2var_satisfiable

    def test_config_parameters(self):
        """Config has correct max_depth and num_moves."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            _sat_2var_satisfiable, max_depth=1, num_moves=1,
        )
        assert config.max_depth == 1
        assert config.num_moves == 1

    def test_registers_initialized(self):
        """Registers are initialized at root (init_root already called)."""
        _init_circuit()
        _, regs, _ = _walk_with_state(
            _sat_2var_satisfiable, max_depth=1, num_moves=1,
        )
        # init_root was already called, so calling again should raise
        import pytest
        with pytest.raises(RuntimeError, match="init_root.*already"):
            regs.init_root()

    def test_qubit_budget(self):
        """Walk uses reasonable number of qubits."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            _sat_2var_satisfiable, max_depth=1, num_moves=1,
        )
        total = config.total_walk_qubits()
        assert total <= 17, f"Walk uses {total} qubits"


# ---------------------------------------------------------------------------
# Group 2: walk_step with Marking Produces Valid Operator
# ---------------------------------------------------------------------------


class TestWalkStepWithMarking:
    """walk_step on walk()-returned config produces valid unitary.

    Verifies norm preservation and correct gate emission.
    """

    def test_walk_step_preserves_norm(self):
        """walk_step on walk() output preserves statevector norm.

        Qubits: 7 <= 17
        """
        _init_circuit()
        config, regs, _state = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
        )
        walk_step(config, regs)

        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Walk step should preserve norm, got {norm}"
        )

    def test_multiple_walk_steps_preserve_norm(self):
        """Multiple walk steps preserve norm."""
        _init_circuit()
        config, regs, _state = _walk_with_state(
            _sat_single_solution, max_depth=1, num_moves=1,
        )
        for _ in range(3):
            walk_step(config, regs)

        _keepalive = [_state]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Multiple walk steps should preserve norm, got {norm}"
        )

    def test_walk_step_emits_gates(self):
        """walk_step on walk() output emits gates (non-trivial).

        Verify by comparing QASM length before and after walk_step.
        """
        _init_circuit()
        config, regs, _state = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
        )
        qasm_before = ql.to_openqasm()
        walk_step(config, regs)
        qasm_after = ql.to_openqasm()
        assert len(qasm_after) > len(qasm_before), (
            "walk_step should emit gates (QASM should grow)"
        )

    def test_never_marked_preserves_norm(self):
        """Config with never-marking predicate preserves norm."""
        _init_circuit()
        config, regs, _state = _walk_with_state(
            lambda s: s != s, max_depth=1, num_moves=1,
        )
        walk_step(config, regs)
        _keepalive = [_state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Walk with never-marking should preserve norm, got {norm}"
        )


# ---------------------------------------------------------------------------
# Group 3: Edge Cases
# ---------------------------------------------------------------------------


class TestWalkEdgeCases:
    """Edge cases for walk() new API."""

    def test_walk_with_custom_max_iterations(self):
        """walk() accepts custom max_iterations without error."""
        _init_circuit()
        config, _, _ = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
            max_iterations=1,
        )
        assert isinstance(config, WalkConfig)


# ---------------------------------------------------------------------------
# Group 4: Standalone walk_diffusion
# ---------------------------------------------------------------------------


def _make_move_flip(state, move_idx):
    """Move function: XOR state with (move_idx + 1)."""
    state ^= (move_idx + 1)


def _undo_move_flip(state, move_idx):
    """Undo XOR move (XOR is self-inverse)."""
    state ^= (move_idx + 1)


def _is_valid_nonzero(state):
    """Validity predicate: state != 0."""
    return state != 0


class TestWalkDiffusionStandalone:
    """walk_diffusion usable standalone (without full walk).

    Verifies that walk_diffusion can be called independently as a
    building block, produces gates, and preserves quantum state.
    """

    def test_standalone_diffusion_runs(self):
        """walk_diffusion completes without error.

        state=1, 2-bit width, num_moves=2.
        Qubits: 2 (state) + 1 (pf) + 1 (branch) + 2 (count) + 2 (validity)
               = 8 <= 17
        """
        _init_circuit()
        state = ql.qint(1, width=2)
        walk_diffusion(
            state, _make_move_flip, _is_valid_nonzero, 2,
            undo_move=_undo_move_flip,
        )

    def test_standalone_diffusion_emits_gates(self):
        """walk_diffusion emits gates (non-trivial operation)."""
        _init_circuit()
        gc_before = ql.get_gate_count()
        state = ql.qint(1, width=2)
        walk_diffusion(
            state, _make_move_flip, _is_valid_nonzero, 2,
            undo_move=_undo_move_flip,
        )
        gc_after = ql.get_gate_count()
        assert gc_after > gc_before, "walk_diffusion should emit gates"

    def test_standalone_diffusion_within_budget(self):
        """walk_diffusion circuit stays within 17-qubit budget."""
        _init_circuit()
        state = ql.qint(0, width=2)
        walk_diffusion(
            state, _make_move_flip, _is_valid_nonzero, 2,
            undo_move=_undo_move_flip,
        )
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

    def test_standalone_diffusion_preserves_state(self):
        """walk_diffusion preserves user's state register value.

        The counting apply-check-undo loop restores state after evaluation.
        Measurement of state register should deterministically return the
        initial value (5).
        """
        _init_circuit()
        state = ql.qint(5, width=4)
        walk_diffusion(
            state, _make_move_flip, _is_valid_nonzero, 1,
            undo_move=_undo_move_flip,
        )
        state_start = state.allocated_start
        state_width = state.width
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        extracted = _simulate_and_extract(
            qasm, nq, state_start, state_width,
        )
        assert extracted == 5, (
            f"State should be preserved at 5, got {extracted}"
        )

    def test_standalone_diffusion_valid_statevector(self):
        """walk_diffusion produces a normalized statevector."""
        _init_circuit()
        state = ql.qint(1, width=2)
        walk_diffusion(
            state, _make_move_flip, _is_valid_nonzero, 2,
            undo_move=_undo_move_flip,
        )
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Statevector norm should be 1.0, got {norm}"
        )

    def test_standalone_diffusion_with_root_flag(self):
        """walk_diffusion accepts is_root=True without error."""
        _init_circuit()
        state = ql.qint(0, width=2)
        walk_diffusion(
            state, _make_move_flip, _is_valid_nonzero, 2,
            undo_move=_undo_move_flip,
            max_depth=2, is_root=True,
        )
        _keepalive = [state]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

    def test_standalone_diffusion_importable_from_ql(self):
        """walk_diffusion is importable from quantum_language top level."""
        from quantum_language import walk_diffusion as wd
        assert callable(wd)


# ---------------------------------------------------------------------------
# Group 5: Custom Walk via Diffusion Building Block
# ---------------------------------------------------------------------------


class TestCustomWalkViaDiffusion:
    """Custom walk using walk_diffusion_with_regs as a building block.

    Demonstrates that users can build their own walk step by composing
    diffusion operators directly on pre-allocated registers.
    """

    def test_custom_walk_with_regs_api(self):
        """walk_diffusion_with_regs allows pre-allocated register usage.

        This is the lower-level API for building custom walks with
        variable branching (predicate-based).

        Qubits: 4 (state) + 1 (pf) + 1 (branch) + 1 (count) + 1 (validity)
               = 8 <= 17
        """
        _init_circuit()
        state = ql.qint(5, width=4)
        num_moves = 1
        bw = branch_width(num_moves)
        pf = ql.qbool()
        br = ql.qint(0, width=bw)

        config = WalkConfig(
            max_depth=1, num_moves=num_moves,
            make_move=_make_move_flip,
            undo_move=_undo_move_flip,
            is_valid=_is_valid_nonzero,
            state=state,
        )

        walk_diffusion_with_regs(config, pf, br)

        _keepalive = [state, pf, br]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        sv = _simulate_statevector(qasm)
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6

    def test_double_diffusion_with_regs_preserves_state(self):
        """walk_diffusion_with_regs applied twice preserves user state.

        Uses predicate-based (variable branching) diffusion.
        state=2, move_0: 2^1=3 (valid). count=1.

        After D^2, the state register should still read 2 (the initial
        value), verifying the diffusion is a reflection.

        Qubits: <= 17
        """
        _init_circuit()
        state = ql.qint(2, width=3)
        num_moves = 1
        bw = branch_width(num_moves)
        pf = ql.qbool()
        br = ql.qint(0, width=bw)

        config = WalkConfig(
            max_depth=1, num_moves=num_moves,
            make_move=_make_move_flip,
            undo_move=_undo_move_flip,
            is_valid=_is_valid_nonzero,
            state=state,
        )

        # Apply D twice (D^2 should be identity-like)
        walk_diffusion_with_regs(config, pf, br)
        walk_diffusion_with_regs(config, pf, br)

        state_start = state.allocated_start
        state_width = state.width
        _keepalive = [state, pf, br]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17

        extracted = _simulate_and_extract(
            qasm, nq, state_start, state_width,
        )
        assert extracted == 2, (
            f"State should be preserved at 2 after D^2, got {extracted}"
        )


# ---------------------------------------------------------------------------
# Group 6: End-to-End Complete Scenarios
# ---------------------------------------------------------------------------


class TestEndToEndScenarios:
    """Full end-to-end scenarios combining multiple walk features."""

    def test_walk_consistency_across_runs(self):
        """walk() produces consistent config across 3 runs."""
        results = []
        for _ in range(3):
            _init_circuit()
            c, _, _ = _walk_with_state(
                lambda s: s == 0, max_depth=1, num_moves=1,
            )
            results.append((c.max_depth, c.num_moves))
        assert all(r == results[0] for r in results)

    def test_walk_and_diffusion_same_import(self):
        """Both walk and walk_diffusion importable from quantum_language."""
        from quantum_language import walk as w
        from quantum_language import walk_diffusion as wd
        assert callable(w)
        assert callable(wd)

    def test_walk_diffusion_then_walk_no_interference(self):
        """Using walk_diffusion standalone does not interfere with walk().

        Call walk_diffusion first on its own circuit, then call walk()
        on a new circuit. Both should succeed independently.
        """
        # Standalone diffusion
        _init_circuit()
        state = ql.qint(1, width=2)
        walk_diffusion(
            state, _make_move_flip, _is_valid_nonzero, 2,
            undo_move=_undo_move_flip,
        )

        # Now run walk() on a new circuit
        _init_circuit()
        config, _, _ = _walk_with_state(
            lambda s: s == 0, max_depth=1, num_moves=1,
        )
        assert isinstance(config, WalkConfig)
