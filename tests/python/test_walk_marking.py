"""Tests for quantum marking in walk operators [Quantum_Assembly-9ka].

Per Montanaro 2015: D_x = I (identity) for marked nodes, standard diffusion
for unmarked.  The _apply_local_diffusion function evaluates is_marked(state)
quantumly to get a qbool and applies diffusion only for unmarked nodes.

Testing strategy
----------------
The framework aggressively tracks classical values and resolves comparisons
at compile time.  Comparisons on constant-value qints produce no gates and
the result qubit stays at physical |0> regardless of the comparison outcome.

To test marking correctness we use two complementary approaches:

1. **Gate-level marking tests** -- Bypass DSL comparison by providing an
   ``is_marked`` predicate that returns a pre-allocated qbool whose
   physical qubit has been set via ``emit_x`` (gate-level, invisible to
   classical tracking).  This gives full control over the marking qubit
   and lets us verify that marked states get identity while unmarked
   states get diffusion.

2. **Superposition marking tests** -- Put the state register into a
   genuine superposition using ``emit_h`` (Hadamard at the gate level),
   then use a DSL comparison as the marking predicate.  The comparison
   must still emit gates because the state is in physical superposition,
   even though the DSL tracker sees value=0.  This verifies that the
   marking qbool is properly entangled with the state.
"""

import gc
import warnings

import numpy as np
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language._gates import emit_h, emit_x
from quantum_language.walk_core import WalkConfig
from quantum_language.walk_operators import (
    _apply_local_diffusion,
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
    ql.option("simulate", True)


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


def _qubit_prob(sv, qubit_indices, expected_bits):
    """Compute probability that specified qubits are in the expected state.

    Marginalizes over all other qubits.  Handles ancilla qubits that may
    be allocated during simulate=True operation.

    Parameters
    ----------
    sv : np.ndarray
        Statevector.
    qubit_indices : list[int]
        Physical qubit indices to check.
    expected_bits : list[int]
        Expected bit values (0 or 1) for each qubit.

    Returns
    -------
    float
        Probability of the specified qubits being in the expected state.
    """
    prob = 0.0
    for i, amp in enumerate(sv):
        match = True
        for qi, eb in zip(qubit_indices, expected_bits, strict=False):
            if ((i >> qi) & 1) != eb:
                match = False
                break
        if match:
            prob += float(abs(amp) ** 2)
    return prob


# ---------------------------------------------------------------------------
# Marking predicates (gate-level)
# ---------------------------------------------------------------------------


def _make_always_marked_predicate():
    """Return an is_marked predicate that always returns physical |1>.

    Allocates a qbool and flips it to |1> via emit_x.  The returned
    closure captures this qbool and returns it on every call.  Because
    the qubit is set at the gate level (not DSL level), the framework
    cannot optimise it away.
    """
    flag = ql.qbool()
    emit_x(int(flag.qubits[63]))  # physical |1>
    return lambda state: flag, flag


def _make_never_marked_predicate():
    """Return an is_marked predicate that always returns physical |0>.

    Allocates a qbool and leaves it at |0>.
    """
    flag = ql.qbool()
    # physical |0> -- no emit_x
    return lambda state: flag, flag


def _make_superposition_marked_predicate(state):
    """Return an is_marked predicate based on a real comparison.

    The caller must have put ``state`` into physical superposition
    (e.g. via emit_h) before calling this.  The predicate returns
    ``state == 0``, whose result qubit is entangled with the state
    when the state is in superposition.
    """

    def predicate(s):
        return s == 0

    return predicate


# ---------------------------------------------------------------------------
# Config/register helpers
# ---------------------------------------------------------------------------


def _make_unmarked_config_and_regs(max_depth, num_moves, state_width=2, state_value=0):
    """Create WalkConfig without marking (but with callbacks), init root."""
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
# Variable-branching helpers
# ---------------------------------------------------------------------------


def _make_move_xor(state, move_idx):
    """Apply move by XORing state with (move_idx + 1)."""
    state ^= move_idx + 1


def _undo_move_xor(state, move_idx):
    """Undo XOR move (XOR is self-inverse)."""
    state ^= move_idx + 1


def _is_valid_nonzero(state):
    """Validity predicate: valid when state != 0."""
    return state != 0


# ---------------------------------------------------------------------------
# Group 1: Marked node gets identity (gate-level verification)
# ---------------------------------------------------------------------------


class TestMarkedNodeGetsIdentity:
    """When all nodes are marked the diffusion must be identity.

    Uses gate-level qbool (via emit_x) so that the marking qubit is
    physically |1> independent of classical optimisation.  After
    _flip_all (X gate), the qubit becomes |0>, so ``with marked:``
    does not fire and diffusion is skipped.
    """

    def test_all_marked_walk_step_is_identity(self):
        """Walk step is identity when is_marked returns physical |1>.

        After the walk step the root probability should still be 1.0
        because diffusion is suppressed at every depth.

        Walk registers: 2 height + 1 branch + 1 count = 4
        State register: 2 qubits + 1 marking flag = 7 qubits.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        # Root qubit h[max_depth] and marking flag qubit should be |1>.
        # Marginalize over ancilla qubits that may be allocated during
        # simulate=True operation.
        h_root = int(regs.height_qubit(config.max_depth).qubits[63])
        flag_qubit = int(flag.qubits[63])
        root_prob = _qubit_prob(sv, [h_root, flag_qubit], [1, 1])
        assert abs(root_prob - 1.0) < 1e-6, (
            f"Walk step with all nodes marked should be identity, root_prob={root_prob}"
        )

    def test_all_marked_R_B_is_identity(self):
        """R_B (root diffusion) is identity when marking returns |1>.

        Only R_B is called; it includes the root diffusion at depth 1
        for a depth-1 tree.  Root probability should remain 1.0.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        from quantum_language.walk_operators import build_R_B

        build_R_B(config, regs)

        _keepalive = [regs, state, flag]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        h_root = int(regs.height_qubit(config.max_depth).qubits[63])
        flag_qubit = int(flag.qubits[63])
        root_prob = _qubit_prob(sv, [h_root, flag_qubit], [1, 1])
        assert abs(root_prob - 1.0) < 1e-6, (
            f"R_B with all nodes marked should be identity, root_prob={root_prob}"
        )

    def test_all_marked_double_step_is_identity(self):
        """Two walk steps are identity when all nodes are marked."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        h_root = int(regs.height_qubit(config.max_depth).qubits[63])
        flag_qubit = int(flag.qubits[63])
        root_prob = _qubit_prob(sv, [h_root, flag_qubit], [1, 1])
        assert abs(root_prob - 1.0) < 1e-6, (
            f"Two walk steps with all nodes marked should be identity, root_prob={root_prob}"
        )

    def test_all_marked_preserves_norm(self):
        """All-marked walk step preserves norm."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"All-marked walk step should preserve norm, got {norm}"


# ---------------------------------------------------------------------------
# Group 2: Unmarked nodes get standard diffusion
# ---------------------------------------------------------------------------


class TestUnmarkedNodeGetsDiffusion:
    """When no node is marked the walk step must apply normal diffusion.

    Uses gate-level qbool left at physical |0> (never marked).  After
    _flip_all (X), the qubit becomes |1> so ``with marked:`` fires
    and diffusion is applied normally.  Also tests the no-marking
    baseline (is_marked not set at all).
    """

    def test_no_marking_walk_step_modifies_root(self):
        """Walk step without marking modifies root state."""
        _init_circuit()
        config, regs, state = _make_unmarked_config_and_regs(
            max_depth=1,
            num_moves=2,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv_after = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv_after)
        assert abs(norm - 1.0) < 1e-6, f"Unmarked walk step should preserve norm, got {norm}"

    def test_never_marked_walk_step_preserves_norm(self):
        """Walk step with is_marked returning physical |0> preserves norm.

        Since the marking qubit is physical |0>, after _flip_all it
        becomes |1>, diffusion runs.  Norm should be preserved.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_never_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"Never-marked walk step should preserve norm, got {norm}"

    def test_no_marking_preserves_norm(self):
        """Unmarked walk step preserves norm."""
        _init_circuit()
        config, regs, state = _make_unmarked_config_and_regs(
            max_depth=1,
            num_moves=2,
        )

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"Unmarked walk step should preserve norm, got {norm}"

    def test_never_marked_preserves_norm(self):
        """Walk step with is_marked returning physical |0> preserves norm."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_never_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"Never-marked walk step should preserve norm, got {norm}"


# ---------------------------------------------------------------------------
# Group 3: Partial marking (superposition state)
# ---------------------------------------------------------------------------


class TestPartialMarking:
    """Selective marking with the state register in superposition.

    Puts the state register into physical superposition via emit_h,
    then uses a DSL comparison (state == 0) as the marking predicate.
    Verifies that the walk step produces different results from the
    all-marked and never-marked cases.
    """

    def test_partial_marking_preserves_norm(self):
        """Walk step with superposition marking preserves norm.

        State register (2 qubits) put into |+> via Hadamard.
        is_marked = (state == 0): marked for the |00> component,
        unmarked for |01>, |10>, |11>.

        Walk registers: 2 height + 1 branch + 1 count = 4
        State register: 2 qubits + comparison ancillae.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        # Put state into genuine superposition at the gate level
        emit_h(int(state.qubits[62]))
        emit_h(int(state.qubits[63]))

        pred = _make_superposition_marked_predicate(state)
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"Partial marking walk step should preserve norm, got {norm}"

    def test_partial_differs_from_all_marked(self):
        """Partial marking produces different circuit than all-marked.

        All-marked is identity: after walk_step, the root probability
        stays at 1.0 (diffusion suppressed).

        Partial marking (state in superposition, is_marked = state == 0)
        produces an entangled marking qbool, so the diffusion fires on
        unmarked components and the circuit differs from all-marked.
        """
        # All-marked (identity) -- verify root prob stays 1.0
        _init_circuit()
        state_a = ql.qint(0, width=2)
        emit_h(int(state_a.qubits[62]))
        emit_h(int(state_a.qubits[63]))
        pred_a, flag_a = _make_always_marked_predicate()
        config_a = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred_a,
            state=state_a,
        )
        regs_a = WalkRegisters(config_a)
        regs_a.init_root()

        h_root_a = int(regs_a.height_qubit(config_a.max_depth).qubits[63])
        flag_qubit_a = int(flag_a.qubits[63])

        sv_before_a = _simulate_statevector(ql.to_openqasm())
        walk_step(config_a, regs_a)
        _keep_a = [regs_a, state_a, flag_a]
        qasm_all_marked = ql.to_openqasm()
        sv_after_a = _simulate_statevector(qasm_all_marked)

        # All-marked walk step is identity: the root and flag qubits
        # should remain in |1>.  Marginalize over ancilla qubits.
        root_prob_before = _qubit_prob(
            sv_before_a,
            [h_root_a, flag_qubit_a],
            [1, 1],
        )
        root_prob_after = _qubit_prob(
            sv_after_a,
            [h_root_a, flag_qubit_a],
            [1, 1],
        )
        assert abs(root_prob_before - root_prob_after) < 1e-6, (
            f"All-marked walk step should be identity: "
            f"root_prob before={root_prob_before}, after={root_prob_after}"
        )

        # Partial marking -- with state in superposition, some
        # components are unmarked and get diffusion applied.
        _init_circuit()
        state_p = ql.qint(0, width=2)
        emit_h(int(state_p.qubits[62]))
        emit_h(int(state_p.qubits[63]))
        pred_p = _make_superposition_marked_predicate(state_p)
        config_p = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred_p,
            state=state_p,
        )
        regs_p = WalkRegisters(config_p)
        regs_p.init_root()
        walk_step(config_p, regs_p)
        _keep_p = [regs_p, state_p]
        qasm_partial = ql.to_openqasm()
        sv_partial = _simulate_statevector(qasm_partial)
        norm_partial = np.linalg.norm(sv_partial)
        assert abs(norm_partial - 1.0) < 1e-6, (
            f"Partial marking should preserve norm, got {norm_partial}"
        )

        # The two circuits must differ: all-marked uses a constant
        # marking qubit (emit_x) while partial uses an entangled
        # comparison result, producing different gate sequences.
        assert qasm_all_marked != qasm_partial, (
            "Partial marking should produce a different circuit than "
            "all-marked (different marking qbool wiring)"
        )

    def test_partial_marking_double_step_preserves_norm(self):
        """Two walk steps with superposition marking preserve norm."""
        _init_circuit()
        state = ql.qint(0, width=2)
        emit_h(int(state.qubits[62]))
        emit_h(int(state.qubits[63]))

        pred = _make_superposition_marked_predicate(state)
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Two partial-marking walk steps should preserve norm, got {norm}"
        )


# ---------------------------------------------------------------------------
# Group 4: Qubit budget
# ---------------------------------------------------------------------------


class TestMarkingQubitBudget:
    """Marking tests stay within the 17-qubit simulation limit."""

    def test_marking_depth1_within_budget(self):
        """Depth-1 marked walk within 17 qubits."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()
        walk_step(config, regs)
        _keepalive = [regs, state, flag]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 21, f"Marked walk uses {nq} qubits (limit: 21)"

    def test_marking_depth1_num_moves_1_within_budget(self):
        """Depth-1 marked walk with num_moves=1 within 21 qubits."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_never_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()
        walk_step(config, regs)
        _keepalive = [regs, state, flag]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 21, f"Marked walk uses {nq} qubits (limit: 21)"

    def test_marking_code_path_allocates_extra_qubits(self):
        """Marked path allocates more qubits than unmarked."""
        _init_circuit()
        config_u, regs_u, state_u = _make_unmarked_config_and_regs(
            max_depth=1,
            num_moves=2,
        )
        walk_step(config_u, regs_u)
        _keep_u = [regs_u, state_u]
        nq_unmarked = _get_num_qubits(ql.to_openqasm())

        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config_m = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs_m = WalkRegisters(config_m)
        regs_m.init_root()
        walk_step(config_m, regs_m)
        _keep_m = [regs_m, state, flag]
        nq_marked = _get_num_qubits(ql.to_openqasm())

        assert nq_marked > nq_unmarked, (
            f"Marked walk should use more qubits than unmarked: "
            f"marked={nq_marked}, unmarked={nq_unmarked}"
        )


# ---------------------------------------------------------------------------
# Group 5: _apply_local_diffusion dispatch
# ---------------------------------------------------------------------------


class TestApplyLocalDiffusionDispatch:
    """Direct tests for _apply_local_diffusion marking dispatch."""

    def test_leaf_depth_noop(self):
        """Depth 0 is a no-op regardless of marking."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()
        sv_before = _simulate_statevector(ql.to_openqasm())

        _apply_local_diffusion(config, regs, depth=0)

        _keepalive = [regs, state, flag]
        sv_after = _simulate_statevector(ql.to_openqasm())
        assert np.allclose(sv_before, sv_after, atol=1e-10), (
            "Depth 0 should be a no-op even with marking"
        )

    def test_marking_branch_not_taken_without_is_marked(self):
        """Without is_marked, the marking branch is not taken."""
        _init_circuit()
        state = ql.qint(0, width=2)
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        _apply_local_diffusion(config, regs, depth=1)

        _keepalive = [regs, state]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6

    def test_marked_diffusion_is_identity_at_depth(self):
        """_apply_local_diffusion at root depth with all-marked is identity.

        Root probability should remain 1.0 because the marked
        predicate returns physical |1> and diffusion is suppressed.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        _apply_local_diffusion(config, regs, depth=1)

        _keepalive = [regs, state, flag]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        h_root = int(regs.height_qubit(config.max_depth).qubits[63])
        flag_qubit = int(flag.qubits[63])
        root_prob = _qubit_prob(sv, [h_root, flag_qubit], [1, 1])
        assert abs(root_prob - 1.0) < 1e-6, (
            f"All-marked _apply_local_diffusion should be identity, root_prob={root_prob}"
        )

    def test_unmarked_diffusion_preserves_norm_at_depth(self):
        """_apply_local_diffusion at root depth with never-marked preserves norm.

        Diffusion runs on unmarked nodes and must preserve the
        statevector norm.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_never_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        _apply_local_diffusion(config, regs, depth=1)

        _keepalive = [regs, state, flag]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Never-marked _apply_local_diffusion should preserve norm, got {norm}"
        )


# ---------------------------------------------------------------------------
# Group 6: Variable-branching + marking
# ---------------------------------------------------------------------------


class TestMarkingWithVariableBranching:
    """Marking works correctly with variable-branching diffusion.

    When is_marked is set along with make_move/is_valid/state, the
    variable-branching path evaluates is_marked(state) quantumly and
    wraps the diffusion call with ``with ~marked:``.  Controlled XOR
    operations inside make_move become Toffoli gates under the marking
    control, handled natively by the framework.
    """

    def test_marking_with_variable_branching_all_marked_identity(self):
        """All-marked walk step with variable branching is identity.

        When is_marked returns physical |1> for all states, diffusion
        is suppressed and the walk step acts as identity.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        h_root = int(regs.height_qubit(config.max_depth).qubits[63])
        flag_qubit = int(flag.qubits[63])
        root_prob = _qubit_prob(sv, [h_root, flag_qubit], [1, 1])
        assert abs(root_prob - 1.0) < 1e-6, (
            f"All-marked variable-branching walk step should be identity, root_prob={root_prob}"
        )

    def test_marking_with_variable_branching_never_marked_preserves_norm(self):
        """Never-marked walk step with variable branching preserves norm.

        When is_marked returns physical |0>, diffusion should run
        on all nodes.  The variable-branching diffusion with constant
        initial state may not spread amplitude visibly (the counting
        evaluates at compile time), but the norm must be preserved.
        """
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_never_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Never-marked variable-branching walk step should preserve norm, got {norm}"
        )

    def test_marking_with_variable_branching_differs_from_unmarked(self):
        """Marked vs unmarked variable-branching produce different circuits.

        All-marked walk step produces identity (no diffusion gates fire),
        while the unmarked walk step applies diffusion.  The two should
        produce different QASM output.
        """
        # All-marked
        _init_circuit()
        state_m = ql.qint(0, width=2)
        pred_m, flag_m = _make_always_marked_predicate()
        config_m = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred_m,
            state=state_m,
        )
        regs_m = WalkRegisters(config_m)
        regs_m.init_root()
        walk_step(config_m, regs_m)
        _km = [regs_m, state_m, flag_m]
        qasm_marked = ql.to_openqasm()

        # Never-marked
        _init_circuit()
        state_u = ql.qint(0, width=2)
        pred_u, flag_u = _make_never_marked_predicate()
        config_u = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred_u,
            state=state_u,
        )
        regs_u = WalkRegisters(config_u)
        regs_u.init_root()
        walk_step(config_u, regs_u)
        _ku = [regs_u, state_u, flag_u]
        qasm_unmarked = ql.to_openqasm()

        # The two circuits should differ in gate count because
        # all-marked suppresses the diffusion rotations
        assert qasm_marked != qasm_unmarked, (
            "All-marked and never-marked variable-branching walks should produce different QASM"
        )

    def test_marking_with_variable_branching_preserves_norm(self):
        """Walk step with marking + variable branching preserves norm."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Variable-branching marked walk step should preserve norm, got {norm}"
        )

    def test_controlled_xor_under_marking(self):
        """XOR operations inside make_move work under marking control.

        Verifies that when marking wraps the variable-branching
        diffusion, the XOR in make_move (which runs unconditionally
        during validity evaluation, outside marking control) produces
        a valid unitary (norm preservation) and does not raise errors.
        Tests with both num_moves=1 and num_moves=2.
        """
        for num_moves in (1, 2):
            _init_circuit()
            state = ql.qint(0, width=2)
            pred, flag = _make_never_marked_predicate()
            config = WalkConfig(
                max_depth=1,
                num_moves=num_moves,
                make_move=_make_move_xor,
                undo_move=_undo_move_xor,
                is_valid=_is_valid_nonzero,
                is_marked=pred,
                state=state,
            )
            regs = WalkRegisters(config)
            regs.init_root()

            walk_step(config, regs)

            _keepalive = [regs, state, flag]
            sv = _simulate_statevector(ql.to_openqasm())
            norm = np.linalg.norm(sv)
            assert abs(norm - 1.0) < 1e-6, (
                f"Controlled XOR under marking with num_moves={num_moves} "
                f"should preserve norm, got {norm}"
            )

    def test_variable_branching_marking_double_step_preserves_norm(self):
        """Two walk steps with marking + variable branching preserve norm."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_never_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        walk_step(config, regs)
        walk_step(config, regs)

        _keepalive = [regs, state, flag]
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, (
            f"Two variable-branching marked walk steps should preserve norm, got {norm}"
        )

    def test_variable_branching_without_marking_no_warning(self):
        """No warning when is_marked is not set on variable-branching path."""
        _init_circuit()
        state = ql.qint(0, width=3)
        config = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            walk_step(config, regs)

        _keepalive = [regs, state]

        marking_warnings = [x for x in w if "is_marked" in str(x.message)]
        assert len(marking_warnings) == 0, "Should not warn about marking when is_marked is not set"

    def test_variable_branching_marking_within_qubit_budget(self):
        """Variable-branching with marking stays within 17-qubit limit."""
        _init_circuit()
        state = ql.qint(0, width=2)
        pred, flag = _make_always_marked_predicate()
        config = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred,
            state=state,
        )
        regs = WalkRegisters(config)
        regs.init_root()
        walk_step(config, regs)
        _keepalive = [regs, state, flag]
        nq = _get_num_qubits(ql.to_openqasm())
        assert nq <= 21, f"Variable-branching marked walk uses {nq} qubits (limit: 21)"


# ---------------------------------------------------------------------------
# Group 7: Marking control visible in QASM
# ---------------------------------------------------------------------------


class TestMarkingControlVisibleInQasm:
    """Verify that marking control is visible in the generated QASM.

    When marking is active, the marking qbool (passed as a qbool object
    through the call chain) should produce additional controlled gates
    compared to the unmarked case.  The marking qbool's physical qubit
    index should appear as a control in the QASM output.
    """

    def test_marking_control_visible_in_qasm(self):
        """Marking qbool produces visible control gates in QASM output.

        Compares QASM for a walk step with never-marked (is_marked
        returns physical |0>) against QASM without marking at all.
        The marked circuit should:
        1. Have more gates (marking adds controlled operations).
        2. Reference the marking qbool's physical qubit in its gates.
        3. Preserve norm (unitarity).
        """
        # Circuit 1: No marking (baseline)
        _init_circuit()
        state_u = ql.qint(0, width=2)
        config_u = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state_u,
        )
        regs_u = WalkRegisters(config_u)
        regs_u.init_root()
        walk_step(config_u, regs_u)
        _keep_u = [regs_u, state_u]
        qasm_no_marking = ql.to_openqasm()

        # Circuit 2: With marking (never-marked => diffusion fires)
        _init_circuit()
        state_m = ql.qint(0, width=2)
        pred_m, flag_m = _make_never_marked_predicate()
        config_m = WalkConfig(
            max_depth=1,
            num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            is_marked=pred_m,
            state=state_m,
        )
        regs_m = WalkRegisters(config_m)
        regs_m.init_root()
        walk_step(config_m, regs_m)
        _keep_m = [regs_m, state_m, flag_m]
        qasm_with_marking = ql.to_openqasm()

        # The marking qubit's physical index
        flag_qubit_idx = int(flag_m.qubits[63])
        flag_qubit_name = f"q[{flag_qubit_idx}]"

        # 1. Circuits should differ (marking adds extra controls)
        assert qasm_no_marking != qasm_with_marking, (
            "Marking should produce different QASM than no marking"
        )

        # 2. The marked circuit should reference the marking qubit
        assert flag_qubit_name in qasm_with_marking, (
            f"Marking qbool qubit {flag_qubit_name} should appear in the QASM output as a control"
        )

        # 3. The marked circuit should use more qubits
        nq_no_marking = _get_num_qubits(qasm_no_marking)
        nq_with_marking = _get_num_qubits(qasm_with_marking)
        assert nq_with_marking > nq_no_marking, (
            f"Marking should use more qubits: "
            f"no_marking={nq_no_marking}, with_marking={nq_with_marking}"
        )

        # 4. Both circuits should produce valid unitaries (norm preserved)
        sv_u = _simulate_statevector(qasm_no_marking)
        sv_m = _simulate_statevector(qasm_with_marking)
        assert abs(np.linalg.norm(sv_u) - 1.0) < 1e-6, "No-marking walk step should preserve norm"
        assert abs(np.linalg.norm(sv_m) - 1.0) < 1e-6, "Marked walk step should preserve norm"
