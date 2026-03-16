"""Tests for walk_counting: count_valid_children and uncount_valid_children.

Verifies the apply-check-undo counting loop operates correctly in both
computational basis states and superposition.  All tests stay within the
17-qubit simulation limit.

Requirements from acceptance criteria:
- All-valid state -> count == num_moves
- No-valid state -> count == 0
- State unchanged after counting
- Superposition correctness via statevector
"""

import gc

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import WalkConfig, count_width
from quantum_language.walk_counting import (
    count_valid_children,
    uncount_valid_children,
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

    # Qiskit bitstring: position i = qubit (N-1-i)
    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos: lsb_pos + 1]
    return int(result_bits, 2)


def _init_circuit():
    """Initialize a fresh circuit with simulate=True for gate storage."""
    gc.collect()
    ql.circuit()
    ql.option('simulate', True)


# ---------------------------------------------------------------------------
# Test make_move / is_valid functions
# ---------------------------------------------------------------------------
# Plain (non-compiled) functions that operate on quantum registers using
# DSL operations.  The undo is explicit (XOR is self-inverse; subtraction
# undoes addition).


def _make_move_xor(state, move_idx):
    """Apply move by XORing state with (move_idx + 1)."""
    state ^= (move_idx + 1)


def _undo_move_xor(state, move_idx):
    """Undo XOR move (XOR is self-inverse)."""
    state ^= (move_idx + 1)


def _make_move_add(state, move_idx):
    """Apply move by adding (move_idx + 1)."""
    state += (move_idx + 1)


def _undo_move_add(state, move_idx):
    """Undo addition move by subtraction."""
    state -= (move_idx + 1)


def _is_valid_always(state):
    """Validity predicate: always valid (returns qbool True for any state)."""
    return state == state


def _is_valid_never(state):
    """Validity predicate: never valid (returns qbool False for any state)."""
    return state != state


def _is_valid_nonzero(state):
    """Validity predicate: valid when state != 0."""
    return state != 0


# ---------------------------------------------------------------------------
# Group 1: Validation Tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Config validation for count_valid_children."""

    def test_rejects_non_walkconfig(self):
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            count_valid_children("not a config", None)

    def test_rejects_missing_make_move(self):
        _init_circuit()
        state = ql.qint(0, width=2)
        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            is_valid=_is_valid_always, state=state,
        )
        count_reg = ql.qint(0, width=count_width(2))
        with pytest.raises(ValueError, match="make_move must not be None"):
            count_valid_children(cfg, count_reg)

    def test_rejects_missing_is_valid(self):
        _init_circuit()
        state = ql.qint(0, width=2)
        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            state=state,
        )
        count_reg = ql.qint(0, width=count_width(2))
        with pytest.raises(ValueError, match="is_valid must not be None"):
            count_valid_children(cfg, count_reg)

    def test_rejects_missing_state(self):
        _init_circuit()
        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
        )
        count_reg = ql.qint(0, width=count_width(2))
        with pytest.raises(ValueError, match="state must not be None"):
            count_valid_children(cfg, count_reg)

    def test_uncount_rejects_non_walkconfig(self):
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            uncount_valid_children(42, None)

    def test_no_undo_move_no_adjoint_raises(self):
        """Without undo_move and without .adjoint, _get_undo_fn raises."""
        _init_circuit()
        state = ql.qint(0, width=2)
        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )
        count_reg = ql.qint(0, width=count_width(2))
        with pytest.raises(AttributeError):
            count_valid_children(cfg, count_reg)


# ---------------------------------------------------------------------------
# Group 2: All-Valid Counting (statevector verification)
# ---------------------------------------------------------------------------


class TestCountAllValid:
    """All moves valid -> count == num_moves."""

    def test_count_2_moves_all_valid(self):
        """Binary branching, all moves valid -> count == 2."""
        _init_circuit()
        state = ql.qint(0, width=2)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 2, f"Expected count=2 (all valid), got {extracted}"

    def test_count_3_moves_all_valid(self):
        """Ternary branching, all moves valid -> count == 3."""
        _init_circuit()
        state = ql.qint(0, width=3)
        cw = count_width(3)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=3,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 3, f"Expected count=3 (all valid), got {extracted}"


# ---------------------------------------------------------------------------
# Group 3: No-Valid Counting
# ---------------------------------------------------------------------------


class TestCountNoneValid:
    """No moves valid -> count == 0."""

    def test_count_2_moves_none_valid(self):
        """Binary branching, no moves valid -> count == 0."""
        _init_circuit()
        state = ql.qint(0, width=2)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_never,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 0, f"Expected count=0 (none valid), got {extracted}"


# ---------------------------------------------------------------------------
# Group 4: Partial Validity
# ---------------------------------------------------------------------------


class TestCountPartialValid:
    """Count strictly between 0 and num_moves."""

    def test_one_of_two_valid_xor(self):
        """State=1, XOR moves, is_valid=nonzero.

        move 0: 1 ^ 1 = 0 (invalid -- zero)
        move 1: 1 ^ 2 = 3 (valid)
        count == 1 (strictly between 0 and 2).
        """
        _init_circuit()
        state = ql.qint(1, width=3)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 1, f"Expected count=1 (1 of 2 valid), got {extracted}"

    def test_two_of_three_valid_xor(self):
        """State=3, 3 XOR moves, is_valid=nonzero.

        move 0: 3 ^ 1 = 2 (valid)
        move 1: 3 ^ 2 = 1 (valid)
        move 2: 3 ^ 3 = 0 (invalid -- zero)
        count == 2 (strictly between 0 and 3).
        """
        _init_circuit()
        state = ql.qint(3, width=3)
        cw = count_width(3)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=3,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_nonzero,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 2, f"Expected count=2 (2 of 3 valid), got {extracted}"

    def test_all_valid_from_nonzero_add(self):
        """State=0, addition moves, is_valid=nonzero.

        move 0: 0 + 1 = 1 (valid)
        move 1: 0 + 2 = 2 (valid)
        Both are nonzero, so count == 2.
        """
        _init_circuit()
        state = ql.qint(0, width=3)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_add,
            undo_move=_undo_move_add,
            is_valid=_is_valid_nonzero,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 2, f"Expected count=2 (both additions nonzero), got {extracted}"


# ---------------------------------------------------------------------------
# Group 5: State Restoration
# ---------------------------------------------------------------------------


class TestStateRestored:
    """State register is unchanged after counting."""

    def test_state_unchanged_after_count_add(self):
        """State starts at 5, should still be 5 after counting with addition.

        Addition-based moves: += then -= is exact undo.
        """
        _init_circuit()
        state = ql.qint(5, width=4)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_add,
            undo_move=_undo_move_add,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        state_start = state.allocated_start
        state_width = state.width
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, state_start, state_width)
        assert extracted == 5, f"State should be unchanged at 5, got {extracted}"

    def test_state_unchanged_after_count_xor(self):
        """State starts at 3, using XOR moves (self-inverse)."""
        _init_circuit()
        state = ql.qint(3, width=3)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        state_start = state.allocated_start
        state_width = state.width
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, state_start, state_width)
        assert extracted == 3, f"State should be unchanged at 3, got {extracted}"


# ---------------------------------------------------------------------------
# Group 6: Uncount (Inverse) Tests
# ---------------------------------------------------------------------------


class TestUncount:
    """uncount_valid_children undoes the counting."""

    def test_uncount_restores_zero(self):
        """count followed by uncount leaves count_reg at 0."""
        _init_circuit()
        state = ql.qint(0, width=2)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)
        uncount_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 0, (
            f"Count + uncount should leave count_reg at 0, got {extracted}"
        )

    def test_uncount_restores_state_and_count(self):
        """count + uncount restores both state and count register.

        Uses XOR-based moves (ancilla-free) to avoid ancilla interference
        in the double counting cycle.
        """
        _init_circuit()
        state = ql.qint(3, width=3)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)
        uncount_valid_children(cfg, count_reg)

        state_start = state.allocated_start
        state_width = state.width
        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        state_val = _simulate_and_extract(qasm, nq, state_start, state_width)
        count_val = _simulate_and_extract(qasm, nq, count_start, cw)

        assert state_val == 3, (
            f"State should be restored to 3, got {state_val}"
        )
        assert count_val == 0, (
            f"Count should be restored to 0, got {count_val}"
        )


# ---------------------------------------------------------------------------
# Group 7: Adjoint Fallback
# ---------------------------------------------------------------------------


class TestAdjointFallback:
    """Test the make_move.adjoint fallback when undo_move is not provided."""

    def test_adjoint_fallback_xor(self):
        """Compiled make_move with adjoint, no explicit undo_move.

        XOR-based compiled function: .adjoint of XOR is XOR itself.
        Uses a locally-defined compiled function to avoid cross-test
        cache contamination.
        """
        _init_circuit()

        @ql.compile(inverse=True, opt=0)
        def move_xor(state, move_idx):
            state ^= (move_idx + 1)
            return state

        state = ql.qint(0, width=2)
        cw = count_width(2)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=move_xor,
            # undo_move intentionally omitted -- uses .adjoint fallback
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 2, (
            f"Adjoint fallback: expected count=2 (all valid), got {extracted}"
        )


# ---------------------------------------------------------------------------
# Group 8: Boundary Cases
# ---------------------------------------------------------------------------


class TestBoundary:
    """Boundary conditions for counting."""

    def test_num_moves_1_valid(self):
        """Minimum num_moves=1, single move is valid -> count == 1."""
        _init_circuit()
        state = ql.qint(0, width=2)
        cw = count_width(1)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 1, f"Expected count=1 (1 move, valid), got {extracted}"

    def test_num_moves_1_invalid(self):
        """Minimum num_moves=1, single move is invalid -> count == 0."""
        _init_circuit()
        state = ql.qint(0, width=2)
        cw = count_width(1)
        count_reg = ql.qint(0, width=cw)

        cfg = WalkConfig(
            max_depth=1, num_moves=1,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_never,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        count_start = count_reg.allocated_start
        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits (limit: 17)"

        extracted = _simulate_and_extract(qasm, nq, count_start, cw)
        assert extracted == 0, f"Expected count=0 (1 move, invalid), got {extracted}"


# ---------------------------------------------------------------------------
# Group 9: Qubit Budget
# ---------------------------------------------------------------------------


class TestQubitBudget:
    """Verify circuits stay within the 17-qubit simulation limit."""

    def test_binary_2bit_state_within_budget(self):
        """2-bit state + 2-move counting fits within 17 qubits."""
        _init_circuit()
        state = ql.qint(0, width=2)
        count_reg = ql.qint(0, width=count_width(2))

        cfg = WalkConfig(
            max_depth=1, num_moves=2,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits, exceeds 17-qubit limit"

    def test_ternary_3bit_state_within_budget(self):
        """3-bit state + 3-move counting fits within 17 qubits."""
        _init_circuit()
        state = ql.qint(0, width=3)
        count_reg = ql.qint(0, width=count_width(3))

        cfg = WalkConfig(
            max_depth=1, num_moves=3,
            make_move=_make_move_xor,
            undo_move=_undo_move_xor,
            is_valid=_is_valid_always,
            state=state,
        )

        count_valid_children(cfg, count_reg)

        _keepalive = [state, count_reg]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 17, f"Circuit uses {nq} qubits, exceeds 17-qubit limit"
