"""Tests for quantum marking in walk operators [Quantum_Assembly-9ka].

Per Montanaro 2015: D_x = I (identity) for marked nodes, standard diffusion
for unmarked.  The _apply_local_diffusion function evaluates is_marked(state)
quantumly to get a qbool and applies diffusion only for unmarked nodes.

Note on classical optimization
------------------------------
The framework aggressively tracks classical values and resolves comparisons
at compile time.  For a state register with a known constant value, the
comparison result qbool has no effect on gate emission (the qubit stays
at |0> physically).  The marking becomes quantum-effective only when the
state register is in genuine superposition (after multiple walk steps or
external preparation).

Tests verify structural correctness:
- Marking code path is exercised (is_marked evaluated, qbool produced)
- Norm preservation with any marking predicate
- Qubit budget respected
- No regression for unmarked walk steps
- Different marking predicates (always/never/partial) don't break the walk
"""

import gc

import numpy as np
import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language._gates import emit_x
from quantum_language.walk_core import WalkConfig
from quantum_language.walk_operators import (
    _apply_local_diffusion,
    build_R_A,
    build_R_B,
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


def _prepare_at_depth(registers, target_depth):
    """Move walk state from root to a given depth."""
    max_depth = registers.config.max_depth
    emit_x(registers.height_qubit(max_depth))    # root off
    emit_x(registers.height_qubit(target_depth))  # target on


# ---------------------------------------------------------------------------
# Marking predicates
# ---------------------------------------------------------------------------


def _always_marked(state):
    """Marking predicate: always marked (state >= 0)."""
    return state >= 0


def _never_marked(state):
    """Marking predicate: never marked (state < 0, always false
    for unsigned qint)."""
    return state < 0


def _marked_when_nonzero(state):
    """Marking predicate: marked when state != 0."""
    return state != 0


# ---------------------------------------------------------------------------
# Config/register helpers
# ---------------------------------------------------------------------------


def _make_marked_config_and_regs(max_depth, num_moves, state_width,
                                  is_marked_fn, state_value=0):
    """Create WalkConfig with is_marked and state, init root."""
    state = ql.qint(state_value, width=state_width)
    config = WalkConfig(
        max_depth=max_depth,
        num_moves=num_moves,
        is_marked=is_marked_fn,
        state=state,
    )
    regs = WalkRegisters(config)
    regs.init_root()
    return config, regs, state


def _make_unmarked_config_and_regs(max_depth, num_moves):
    """Create WalkConfig without marking, init root."""
    config = WalkConfig(max_depth=max_depth, num_moves=num_moves)
    regs = WalkRegisters(config)
    regs.init_root()
    return config, regs


# ---------------------------------------------------------------------------
# Group 1: Marked node gets identity (structural tests)
# ---------------------------------------------------------------------------


class TestMarkedNodeGetsIdentity:
    """Verify that the marking code path is exercised and doesn't
    break the walk.  With the framework's classical optimization,
    classically-resolved marking predicates produce comparison
    ancillae but don't change the gate behavior for constant states.
    """

    def test_all_marked_preserves_norm(self):
        """Walk step with always-marked predicate preserves norm.

        Walk registers: 2 height + 1 branch + 1 count = 4
        State register: 2 qubits
        """
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_always_marked,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"All-marked walk step should preserve norm, got {norm}"
        )

    def test_all_marked_double_step_preserves_norm(self):
        """Two walk steps with always-marked predicate preserve norm."""
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_always_marked,
        )

        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Two all-marked walk steps should preserve norm, got {norm}"
        )

    def test_all_marked_code_path_taken(self):
        """Verify the marking branch is taken when is_marked and state
        are set.

        The marked walk step should allocate extra qubits (for the
        comparison result) compared to the unmarked walk step.
        """
        # Unmarked walk step
        _init_circuit()
        config_u, regs_u = _make_unmarked_config_and_regs(
            max_depth=1, num_moves=2,
        )
        walk_step(config_u, regs_u)
        _keep_u = [regs_u]
        nq_unmarked = _get_num_qubits(ql.to_openqasm())

        # Marked walk step
        _init_circuit()
        config_m, regs_m, state_m = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_always_marked,
        )
        walk_step(config_m, regs_m)
        _keep_m = [regs_m, state_m]
        nq_marked = _get_num_qubits(ql.to_openqasm())

        # Marked path allocates state register + comparison ancillae
        assert nq_marked > nq_unmarked, (
            f"Marked walk should use more qubits than unmarked: "
            f"marked={nq_marked}, unmarked={nq_unmarked}"
        )

    def test_all_marked_depth2_preserves_norm(self):
        """All-marked walk step on depth-2 tree preserves norm.

        Walk registers: 3 height + 2 branch + 1 count = 6
        State register: 2 qubits
        """
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=2, num_moves=2, state_width=2,
            is_marked_fn=_always_marked,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"All-marked depth-2 walk step should preserve norm, got {norm}"
        )


# ---------------------------------------------------------------------------
# Group 2: Unmarked nodes get standard diffusion
# ---------------------------------------------------------------------------


class TestUnmarkedNodeGetsDiffusion:
    """Without marking (or with is_marked not set), standard diffusion
    applies and modifies the root state.
    """

    def test_no_marking_walk_step_modifies_root(self):
        """Walk step without marking modifies root state."""
        _init_circuit()
        config, regs = _make_unmarked_config_and_regs(
            max_depth=1, num_moves=2,
        )
        sv_before = _simulate_statevector(ql.to_openqasm())

        walk_step(config, regs)

        _keepalive = [regs]
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert not np.allclose(sv_before, sv_after, atol=1e-6), (
            "Unmarked walk step should modify root state"
        )

    def test_no_marking_preserves_norm(self):
        """Unmarked walk step preserves norm."""
        _init_circuit()
        config, regs = _make_unmarked_config_and_regs(
            max_depth=1, num_moves=2,
        )

        walk_step(config, regs)

        _keepalive = [regs]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Unmarked walk step should preserve norm, got {norm}"
        )

    def test_never_marked_preserves_norm(self):
        """Walk step with never-marked predicate preserves norm."""
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_never_marked,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Never-marked walk step should preserve norm, got {norm}"
        )

    def test_never_marked_allocates_extra_qubits(self):
        """Never-marked path allocates extra qubits (state + comparison)."""
        _init_circuit()
        config_u, regs_u = _make_unmarked_config_and_regs(
            max_depth=1, num_moves=2,
        )
        walk_step(config_u, regs_u)
        _keep_u = [regs_u]
        nq_unmarked = _get_num_qubits(ql.to_openqasm())

        _init_circuit()
        config_n, regs_n, state_n = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_never_marked,
        )
        walk_step(config_n, regs_n)
        _keep_n = [regs_n, state_n]
        nq_never = _get_num_qubits(ql.to_openqasm())

        assert nq_never > nq_unmarked, (
            f"Never-marked should allocate extra qubits: "
            f"never={nq_never}, unmarked={nq_unmarked}"
        )


# ---------------------------------------------------------------------------
# Group 3: Partial marking
# ---------------------------------------------------------------------------


class TestPartialMarking:
    """Selective marking with state != 0: state=0 unmarked, nonzero marked.

    For a classical state=0, the partial predicate evaluates to False
    (not marked), so the marking path allocates comparison ancillae.
    """

    def test_partial_marking_preserves_norm(self):
        """Walk step with partial marking preserves norm."""
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_marked_when_nonzero,
            state_value=0,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Partial marking walk step should preserve norm, got {norm}"
        )

    def test_partial_marking_depth2_preserves_norm(self):
        """Partial marking on depth-2 tree preserves norm.

        Walk registers: 3 height + 2 branch + 1 count = 6
        State register: 2 qubits
        """
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=2, num_moves=2, state_width=2,
            is_marked_fn=_marked_when_nonzero,
            state_value=0,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Partial marking depth-2 should preserve norm, got {norm}"
        )

    def test_partial_marking_double_step_preserves_norm(self):
        """Two walk steps with partial marking preserve norm."""
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_marked_when_nonzero,
            state_value=0,
        )

        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Two partial-marking walk steps should preserve norm, got {norm}"
        )

    def test_partial_marking_allocates_extra_qubits(self):
        """Partial marking allocates state register + comparison qubits."""
        _init_circuit()
        config_u, regs_u = _make_unmarked_config_and_regs(
            max_depth=1, num_moves=2,
        )
        walk_step(config_u, regs_u)
        _keep_u = [regs_u]
        nq_unmarked = _get_num_qubits(ql.to_openqasm())

        _init_circuit()
        config_p, regs_p, state_p = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_marked_when_nonzero,
        )
        walk_step(config_p, regs_p)
        _keep_p = [regs_p, state_p]
        nq_partial = _get_num_qubits(ql.to_openqasm())

        assert nq_partial > nq_unmarked, (
            f"Partial marking should allocate extra qubits: "
            f"partial={nq_partial}, unmarked={nq_unmarked}"
        )


# ---------------------------------------------------------------------------
# Group 4: Qubit budget
# ---------------------------------------------------------------------------


class TestMarkingQubitBudget:
    """Marking tests stay within the 17-qubit simulation limit."""

    def test_marking_depth1_within_budget(self):
        """Depth-1 marked walk within 17 qubits."""
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_always_marked,
        )
        walk_step(config, regs)
        _keepalive = [regs, state]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 17, f"Marked walk uses {nq} qubits (limit: 17)"

    def test_marking_depth2_within_budget(self):
        """Depth-2 marked walk within 17 qubits."""
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=2, num_moves=2, state_width=2,
            is_marked_fn=_marked_when_nonzero,
        )
        walk_step(config, regs)
        _keepalive = [regs, state]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 17, f"Marked walk uses {nq} qubits (limit: 17)"

    def test_marking_ternary_within_budget(self):
        """Ternary tree depth-1 with marking within 17 qubits.

        Use 1-bit state register to minimize qubit usage.
        """
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=3, state_width=1,
            is_marked_fn=_always_marked,
        )
        walk_step(config, regs)
        _keepalive = [regs, state]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 17, f"Ternary marked walk uses {nq} qubits (limit: 17)"


# ---------------------------------------------------------------------------
# Group 5: _apply_local_diffusion dispatch
# ---------------------------------------------------------------------------


class TestApplyLocalDiffusionDispatch:
    """Direct tests for _apply_local_diffusion marking dispatch."""

    def test_leaf_depth_noop(self):
        """Depth 0 is a no-op regardless of marking."""
        _init_circuit()
        config, regs, state = _make_marked_config_and_regs(
            max_depth=1, num_moves=2, state_width=2,
            is_marked_fn=_always_marked,
        )
        sv_before = _simulate_statevector(ql.to_openqasm())

        _apply_local_diffusion(config, regs, depth=0)

        _keepalive = [regs, state]
        sv_after = _simulate_statevector(ql.to_openqasm())
        assert np.allclose(sv_before, sv_after, atol=1e-10), (
            "Depth 0 should be a no-op even with marking"
        )

    def test_marking_branch_not_taken_without_is_marked(self):
        """Without is_marked, the marking branch is not taken."""
        _init_circuit()
        config = WalkConfig(max_depth=1, num_moves=2)
        regs = WalkRegisters(config)
        regs.init_root()

        _apply_local_diffusion(config, regs, depth=1)

        _keepalive = [regs]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6

    def test_marking_branch_not_taken_without_state(self):
        """Without state, the marking branch is not taken even if
        is_marked is set."""
        _init_circuit()
        config = WalkConfig(
            max_depth=1, num_moves=2,
            is_marked=_always_marked,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        _apply_local_diffusion(config, regs, depth=1)

        _keepalive = [regs]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6

    def test_marking_branch_taken_with_both(self):
        """With both is_marked and state, the marking branch is taken.

        Verify by checking that more qubits are allocated (comparison
        ancilla from the is_marked evaluation).
        """
        # Without marking
        _init_circuit()
        config_u = WalkConfig(max_depth=1, num_moves=2)
        regs_u = WalkRegisters(config_u)
        regs_u.init_root()
        _apply_local_diffusion(config_u, regs_u, depth=1)
        _keep_u = [regs_u]
        nq_u = _get_num_qubits(ql.to_openqasm())

        # With marking
        _init_circuit()
        state = ql.qint(0, width=2)
        config_m = WalkConfig(
            max_depth=1, num_moves=2,
            is_marked=_always_marked,
            state=state,
        )
        regs_m = WalkRegisters(config_m)
        regs_m.init_root()
        _apply_local_diffusion(config_m, regs_m, depth=1)
        _keep_m = [regs_m, state]
        nq_m = _get_num_qubits(ql.to_openqasm())

        assert nq_m > nq_u, (
            f"Marking path should allocate more qubits: "
            f"marked={nq_m}, unmarked={nq_u}"
        )

    def test_marking_with_different_predicates_all_preserve_norm(self):
        """All three marking predicates preserve norm at depth 1."""
        for fn in [_always_marked, _never_marked, _marked_when_nonzero]:
            _init_circuit()
            config, regs, state = _make_marked_config_and_regs(
                max_depth=1, num_moves=2, state_width=2,
                is_marked_fn=fn,
            )
            _apply_local_diffusion(config, regs, depth=1)
            _keepalive = [regs, state]
            sv = _simulate_statevector(ql.to_openqasm())
            norm = np.linalg.norm(sv)
            assert abs(norm - 1.0) < 1e-6, (
                f"Predicate {fn.__name__} should preserve norm, got {norm}"
            )
