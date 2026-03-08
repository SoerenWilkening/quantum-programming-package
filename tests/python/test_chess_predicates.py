"""Tests for chess quantum predicates: piece-exists factory and compile/inverse verification.

Unit tests for Phase 114 requirements PRED-01 and PRED-05.
Statevector tests use 2x2 boards to stay within 17-qubit simulation budget.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import quantum_language as ql


def make_small_board(rows, cols, occupied_squares):
    """Create a small board qarray with specified pieces.

    Uses direct qarray construction (NOT encode_position, which hardcodes 8x8).

    Parameters
    ----------
    rows, cols : int
        Board dimensions.
    occupied_squares : list[tuple[int, int]]
        List of (rank, file) tuples where pieces are placed.

    Returns
    -------
    qarray
        A (rows x cols) qarray of qbool with specified squares set to |1>.
    """
    data = np.zeros((rows, cols), dtype=int)
    for r, f in occupied_squares:
        data[r, f] = 1
    return ql.qarray(data, dtype=ql.qbool)


def _get_result_probability(qasm_str, result_qubit_index, target_value=1):
    """Run statevector simulation and return probability of result qubit being target_value.

    Parameters
    ----------
    qasm_str : str
        OpenQASM 3.0 circuit string.
    result_qubit_index : int
        Physical qubit index of the result qbool.
    target_value : int
        0 or 1 -- which value to measure probability for.

    Returns
    -------
    float
        Sum of |amplitude|^2 for states where result qubit has target_value.
    """
    import qiskit.qasm3
    from qiskit_aer import AerSimulator

    qc = qiskit.qasm3.loads(qasm_str)
    qc.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    job = sim.run(qc)
    sv = job.result().get_statevector()

    probs = np.abs(np.array(sv)) ** 2
    total = 0.0
    for state_idx in range(len(probs)):
        # Check if bit at result_qubit_index position equals target_value
        bit = (state_idx >> result_qubit_index) & 1
        if bit == target_value:
            total += probs[state_idx]
    return total


class TestPieceExists:
    """PRED-01: Piece-exists predicate returns correct result for various board states."""

    def test_piece_present_valid_dest(self, clean_circuit):
        """Piece at (0,0), move (1,0), 2x2 board -> result is |1>."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(2, 2, [(0, 0)])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test", 1, 0, 2, 2)
        pred(board, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_one = _get_result_probability(qasm_str, result_qubit, target_value=1)
        assert prob_one > 0.99, f"Expected result |1>, got P(1)={prob_one:.4f}"

    def test_piece_absent(self, clean_circuit):
        """Empty board, move (1,0), 2x2 board -> result stays |0>."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(2, 2, [])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test", 1, 0, 2, 2)
        pred(board, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0>, got P(0)={prob_zero:.4f}"

    def test_dest_out_of_bounds(self, clean_circuit):
        """Piece at (0,0), move (2,0), 2x2 board -> result stays |0> (classical skip)."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(2, 2, [(0, 0)])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test", 2, 0, 2, 2)
        pred(board, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> (out of bounds), got P(0)={prob_zero:.4f}"

    def test_piece_at_different_square(self, clean_circuit):
        """Piece at (1,1), move (-1,-1), 2x2 board -> result is |1>."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(2, 2, [(1, 1)])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test", -1, -1, 2, 2)
        pred(board, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_one = _get_result_probability(qasm_str, result_qubit, target_value=1)
        assert prob_one > 0.99, f"Expected result |1>, got P(1)={prob_one:.4f}"


class TestCompileInverse:
    """PRED-05: Predicates use @ql.compile(inverse=True) with working adjoint.

    The piece-exists predicate allocates no internal ancillas, so .inverse()
    (which uncomputes ancillas) has no forward call record.  The correct API
    for "run the gate sequence in reverse" is .adjoint(), which is enabled by
    the @ql.compile(inverse=True) decorator.
    """

    def test_adjoint_callable(self, clean_circuit):
        """Create predicate, call it, then call .adjoint() -- no error raised."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(2, 2, [(0, 0)])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test", 1, 0, 2, 2)
        pred(board, result)

        # Calling .adjoint with same args should not raise
        pred.adjoint(board, result)

    def test_adjoint_roundtrip(self, clean_circuit):
        """Forward then adjoint should return result qbool to |0>."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(2, 2, [(0, 0)])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test", 1, 0, 2, 2)
        pred(board, result)
        pred.adjoint(board, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> after roundtrip, got P(0)={prob_zero:.4f}"


class TestScaling:
    """Scaling test: 8x8 circuit builds without error (no simulation)."""

    def test_8x8_circuit_builds(self, clean_circuit):
        """Create 8x8 board with piece at (4,4), knight offset (2,1) -> circuit builds."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(8, 8, [(4, 4)])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test_knight", 2, 1, 8, 8)
        # Should not raise -- just building the circuit, no simulation
        pred(board, result)
