"""Tests for chess quantum predicates: piece-exists, no-friendly-capture, check detection, and classical equivalence.

Unit tests for Phase 114 requirements PRED-01, PRED-02, PRED-05
and Phase 115 requirement PRED-03.
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


class TestNoFriendlyCapture:
    """PRED-02: No-friendly-capture predicate returns correct result."""

    def test_friendly_at_target_blocks(self, clean_circuit):
        """Piece at (0,0), friendly at (1,0), move (1,0), 2x2 -> result |0> (blocked)."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(2, 2, [(0, 0)])
        friendly = make_small_board(2, 2, [(1, 0)])
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(1, 0, 2, 2)
        pred(piece, friendly, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> (friendly blocks), got P(0)={prob_zero:.4f}"

    def test_target_clear(self, clean_circuit):
        """Piece at (0,0), no friendly at (1,0), move (1,0), 2x2 -> result |1> (safe)."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(2, 2, [(0, 0)])
        friendly = make_small_board(2, 2, [])
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(1, 0, 2, 2)
        pred(piece, friendly, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_one = _get_result_probability(qasm_str, result_qubit, target_value=1)
        assert prob_one > 0.99, f"Expected result |1> (target clear), got P(1)={prob_one:.4f}"

    def test_out_of_bounds_offset(self, clean_circuit):
        """Piece at (0,0), move (2,0), 2x2 -> result |0> (no valid sources)."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(2, 2, [(0, 0)])
        friendly = make_small_board(2, 2, [])
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(2, 0, 2, 2)
        pred(piece, friendly, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> (out of bounds), got P(0)={prob_zero:.4f}"

    def test_multiple_friendly_boards(self, clean_circuit):
        """2 friendly qarrays, one has piece at target -> result |0> (blocked)."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(2, 2, [(0, 0)])
        friendly1 = make_small_board(2, 2, [])  # empty
        friendly2 = make_small_board(2, 2, [(1, 0)])  # friendly at target
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(1, 0, 2, 2)
        pred(piece, friendly1, friendly2, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, (
            f"Expected result |0> (friendly on board 2), got P(0)={prob_zero:.4f}"
        )

    def test_no_piece_no_result(self, clean_circuit):
        """Empty piece board -> result |0> (no piece, nothing fires)."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(2, 2, [])
        friendly = make_small_board(2, 2, [(1, 0)])
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(1, 0, 2, 2)
        pred(piece, friendly, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> (no piece), got P(0)={prob_zero:.4f}"

    def test_adjoint_callable(self, clean_circuit):
        """No-friendly-capture predicate .adjoint() works without error."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(2, 2, [(0, 0)])
        friendly = make_small_board(2, 2, [])
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(1, 0, 2, 2)
        pred(piece, friendly, result)
        pred.adjoint(piece, friendly, result)

    def test_adjoint_roundtrip(self, clean_circuit):
        """Forward then adjoint returns result to |0>."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(2, 2, [(0, 0)])
        friendly = make_small_board(2, 2, [])
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(1, 0, 2, 2)
        pred(piece, friendly, result)
        pred.adjoint(piece, friendly, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> after roundtrip, got P(0)={prob_zero:.4f}"


class TestClassicalEquivalence:
    """Classical equivalence verification for both predicates on exhaustive 2x2 configs."""

    @staticmethod
    def _classical_piece_exists(occupied, dr, df, rows, cols):
        """Classical: does any piece at an occupied square have a valid dest for (dr, df)?"""
        for r, f in occupied:
            tr, tf = r + dr, f + df
            if 0 <= tr < rows and 0 <= tf < cols:
                return True
        return False

    @staticmethod
    def _classical_no_friendly_capture(piece_squares, friendly_squares, dr, df, rows, cols):
        """Classical: piece exists at valid source AND no friendly at target?

        Returns True if a piece exists at some (r,f) with valid (r+dr,f+df) and
        no friendly piece occupies (r+dr, f+df).
        """
        for r, f in piece_squares:
            tr, tf = r + dr, f + df
            if 0 <= tr < rows and 0 <= tf < cols:
                # Piece can move here -- check if target is friendly-free
                if (tr, tf) not in friendly_squares:
                    return True
        return False

    def test_piece_exists_all_configs_2x2(self, clean_circuit):
        """Exhaustively test piece-exists for all 2x2 single-piece + empty configs."""
        from chess_predicates import make_piece_exists_predicate

        rows, cols = 2, 2
        offsets = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (2, 0)]
        # All possible single-piece positions + empty board
        piece_configs = [()] + [((r, f),) for r in range(rows) for f in range(cols)]

        for dr, df in offsets:
            pred = make_piece_exists_predicate("test", dr, df, rows, cols)
            for occupied in piece_configs:
                ql.circuit()
                board = make_small_board(rows, cols, list(occupied))
                result = ql.qbool()
                pred(board, result)

                qasm_str = ql.to_openqasm()
                result_qubit = int(result.qubits[63])

                expected = self._classical_piece_exists(list(occupied), dr, df, rows, cols)
                expected_val = 1 if expected else 0
                prob = _get_result_probability(qasm_str, result_qubit, target_value=expected_val)
                assert prob > 0.99, (
                    f"piece_exists mismatch: occupied={occupied}, offset=({dr},{df}), "
                    f"expected={expected_val}, P({expected_val})={prob:.4f}"
                )

    def test_no_friendly_capture_configs_2x2(self, clean_circuit):
        """Test representative no-friendly-capture configs on 2x2 board."""
        from chess_predicates import make_no_friendly_capture_predicate

        rows, cols = 2, 2
        offsets = [(1, 0), (0, 1), (-1, 0), (0, -1)]

        # Test configs: (piece_squares, friendly_squares)
        configs = [
            ([(0, 0)], []),  # piece, no friendly
            ([(0, 0)], [(1, 0)]),  # piece at (0,0), friendly at target (1,0) for offset (1,0)
            ([(1, 1)], [(0, 1)]),  # piece at (1,1), friendly at (0,1) for offset (-1,0)
            ([], [(1, 0)]),  # no piece
            ([(0, 0)], [(0, 1)]),  # piece and friendly but friendly not at target for (1,0)
            ([(0, 0), (1, 1)], [(1, 0)]),  # two pieces (XOR edge case)
        ]

        for dr, df in offsets:
            pred = make_no_friendly_capture_predicate(dr, df, rows, cols)
            for piece_sq, friendly_sq in configs:
                ql.circuit()
                piece = make_small_board(rows, cols, piece_sq)
                friendly = make_small_board(rows, cols, friendly_sq)
                result = ql.qbool()
                pred(piece, friendly, result)

                qasm_str = ql.to_openqasm()
                result_qubit = int(result.qubits[63])

                expected = self._classical_no_friendly_capture(
                    piece_sq, set(map(tuple, friendly_sq)), dr, df, rows, cols
                )
                expected_val = 1 if expected else 0
                prob = _get_result_probability(qasm_str, result_qubit, target_value=expected_val)
                assert prob > 0.99, (
                    f"no_friendly_capture mismatch: piece={piece_sq}, friendly={friendly_sq}, "
                    f"offset=({dr},{df}), expected={expected_val}, P({expected_val})={prob:.4f}"
                )


class TestScaling:
    """Scaling test: 8x8 circuit builds without error (no simulation)."""

    def test_8x8_piece_exists_builds(self, clean_circuit):
        """Create 8x8 board with piece at (4,4), knight offset (2,1) -> circuit builds."""
        from chess_predicates import make_piece_exists_predicate

        board = make_small_board(8, 8, [(4, 4)])
        result = ql.qbool()

        pred = make_piece_exists_predicate("test_knight", 2, 1, 8, 8)
        # Should not raise -- just building the circuit, no simulation
        pred(board, result)

    def test_8x8_no_friendly_capture_builds(self, clean_circuit):
        """8x8 board with piece and friendly, knight offset -> circuit builds."""
        from chess_predicates import make_no_friendly_capture_predicate

        piece = make_small_board(8, 8, [(4, 4)])
        friendly = make_small_board(8, 8, [(6, 5)])
        result = ql.qbool()

        pred = make_no_friendly_capture_predicate(2, 1, 8, 8)
        # Should not raise -- just building the circuit, no simulation
        pred(piece, friendly, result)


# ---------------------------------------------------------------------------
# Phase 115 -- Check Detection Predicate (PRED-03)
# ---------------------------------------------------------------------------


class TestCheckDetection:
    """PRED-03: Check detection predicate returns correct result on 2x2 boards."""

    def test_king_safe_no_enemies(self, clean_circuit):
        """King at (0,0), no enemy pieces -> result |1> (safe)."""
        from chess_encoding import _KING_OFFSETS
        from chess_predicates import make_check_detection_predicate

        king = make_small_board(2, 2, [(0, 0)])
        enemy = make_small_board(2, 2, [])  # no enemies
        result = ql.qbool()

        # enemy_attacks: check king adjacency offsets
        enemy_attacks = [(_KING_OFFSETS, "king")]
        pred = make_check_detection_predicate("knight", 0, 0, 2, 2, enemy_attacks)
        pred(king, enemy, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_one = _get_result_probability(qasm_str, result_qubit, target_value=1)
        assert prob_one > 0.99, f"Expected result |1> (safe), got P(1)={prob_one:.4f}"

    def test_king_in_check(self, clean_circuit):
        """King at (0,0), enemy king at (1,0) with king adjacency -> result |0> (in check)."""
        from chess_encoding import _KING_OFFSETS
        from chess_predicates import make_check_detection_predicate

        king = make_small_board(2, 2, [(0, 0)])
        enemy = make_small_board(2, 2, [(1, 0)])  # enemy adjacent
        result = ql.qbool()

        enemy_attacks = [(_KING_OFFSETS, "king")]
        # Knight move: check king's current position (0,0). Enemy at (1,0) is
        # adjacent via offset (1,0) which is in _KING_OFFSETS -> in check.
        pred = make_check_detection_predicate("knight", 0, 0, 2, 2, enemy_attacks)
        pred(king, enemy, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> (in check), got P(0)={prob_zero:.4f}"

    def test_enemy_at_non_attacking_square(self, clean_circuit):
        """King at (0,0), enemy at (1,1) but only checking knight L-shape offsets -> safe."""
        from chess_encoding import _KNIGHT_OFFSETS
        from chess_predicates import make_check_detection_predicate

        king = make_small_board(2, 2, [(0, 0)])
        enemy = make_small_board(2, 2, [(1, 1)])  # enemy at (1,1)
        result = ql.qbool()

        # Only check knight attacks -- (1,1) is NOT a valid knight attack from (0,0)
        # on a 2x2 board (all knight offsets go out of bounds from (0,0))
        enemy_attacks = [(_KNIGHT_OFFSETS, "knight")]
        pred = make_check_detection_predicate("knight", 0, 0, 2, 2, enemy_attacks)
        pred(king, enemy, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_one = _get_result_probability(qasm_str, result_qubit, target_value=1)
        assert prob_one > 0.99, (
            f"Expected result |1> (safe, no knight attacks on 2x2), got P(1)={prob_one:.4f}"
        )

    def test_king_move_checks_destination(self, clean_circuit):
        """King move (1,0): check destination (1,0) for attacks, not current (0,0).

        King at (0,0), enemy at (1,1). King moves to (1,0).
        Check if (1,1) attacks (1,0): with king adjacency offset (0,1), yes -> in check.
        """
        from chess_encoding import _KING_OFFSETS
        from chess_predicates import make_check_detection_predicate

        king = make_small_board(2, 2, [(0, 0)])
        enemy = make_small_board(2, 2, [(1, 1)])  # enemy king at (1,1)
        result = ql.qbool()

        enemy_attacks = [(_KING_OFFSETS, "king")]
        # moving_piece_type="king", dr=1, df=0 -> check destination (0+1, 0+0) = (1,0)
        # Enemy at (1,1), offset (0,1) from (1,0) -> attacker at (1,1). In check.
        pred = make_check_detection_predicate("king", 1, 0, 2, 2, enemy_attacks)
        pred(king, enemy, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, (
            f"Expected result |0> (king moves into check), got P(0)={prob_zero:.4f}"
        )

    def test_knight_move_checks_current_pos(self, clean_circuit):
        """Knight move: check king's current position for attacks.

        King at (0,0), enemy king at (1,1) (adjacent via king offsets).
        Knight move doesn't change which square to check -> still (0,0).
        Enemy at (1,1) attacks (0,0) via offset (1,1) in _KING_OFFSETS -> in check.
        """
        from chess_encoding import _KING_OFFSETS
        from chess_predicates import make_check_detection_predicate

        king = make_small_board(2, 2, [(0, 0)])
        enemy = make_small_board(2, 2, [(1, 1)])  # enemy king diagonal
        result = ql.qbool()

        enemy_attacks = [(_KING_OFFSETS, "king")]
        # moving_piece_type="knight" -> check king's current pos (0,0)
        # Enemy at (1,1), offset (1,1) from (0,0) -> attacker. In check.
        pred = make_check_detection_predicate("knight", 2, 1, 2, 2, enemy_attacks)
        pred(king, enemy, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> (king in check), got P(0)={prob_zero:.4f}"

    def test_adjoint_roundtrip(self, clean_circuit):
        """Forward + adjoint returns result qbool to |0>."""
        from chess_encoding import _KING_OFFSETS
        from chess_predicates import make_check_detection_predicate

        king = make_small_board(2, 2, [(0, 0)])
        enemy = make_small_board(2, 2, [])
        result = ql.qbool()

        enemy_attacks = [(_KING_OFFSETS, "king")]
        pred = make_check_detection_predicate("knight", 0, 0, 2, 2, enemy_attacks)
        pred(king, enemy, result)
        pred.adjoint(king, enemy, result)

        qasm_str = ql.to_openqasm()
        result_qubit = int(result.qubits[63])
        prob_zero = _get_result_probability(qasm_str, result_qubit, target_value=0)
        assert prob_zero > 0.99, f"Expected result |0> after roundtrip, got P(0)={prob_zero:.4f}"


class TestCheckDetectionClassical:
    """Classical equivalence verification for check detection on 2x2."""

    @staticmethod
    def _classical_check_safe(
        king_pos, enemy_positions, enemy_attacks, moving_piece_type, dr, df, board_rows, board_cols
    ):
        """Classical: is king safe after move?

        For king moves: check if destination (kr+dr, kf+df) is attacked.
        For knight moves: check if king's current position is attacked.
        Returns True if safe (not in check).
        """
        kr, kf = king_pos
        if moving_piece_type == "king":
            check_r, check_f = kr + dr, kf + df
            if not (0 <= check_r < board_rows and 0 <= check_f < board_cols):
                return False  # destination off-board -> not a valid move
        else:
            check_r, check_f = kr, kf

        for enemy_idx, (offsets, _label) in enumerate(enemy_attacks):
            for adr, adf in offsets:
                ar, af = check_r + adr, check_f + adf
                if 0 <= ar < board_rows and 0 <= af < board_cols:
                    if (ar, af) in enemy_positions[enemy_idx]:
                        return False  # attacked!
        return True

    def test_classical_equivalence_2x2(self, clean_circuit):
        """Representative configs on 2x2 board with single enemy, king adjacency attacks."""
        from chess_encoding import _KING_OFFSETS
        from chess_predicates import make_check_detection_predicate

        rows, cols = 2, 2
        enemy_attacks = [(_KING_OFFSETS, "king")]

        # Test configs: (king_pos, enemy_squares, moving_piece_type, dr, df)
        configs = [
            # Knight moves -- check king's current pos
            ((0, 0), [(1, 0)], "knight", 2, 1),  # adjacent enemy -> unsafe
            ((0, 0), [], "knight", 2, 1),  # no enemy -> safe
            ((1, 1), [(0, 0)], "knight", 2, 1),  # diagonal enemy -> unsafe
            ((1, 0), [(0, 1)], "knight", 2, 1),  # diagonal enemy -> unsafe
            # King moves -- check destination
            ((0, 0), [(1, 1)], "king", 1, 0),  # dest (1,0), enemy (1,1) adj -> unsafe
            ((0, 0), [], "king", 1, 0),  # dest (1,0), no enemy -> safe
            ((0, 0), [(0, 1)], "king", 1, 0),  # dest (1,0), enemy (0,1) adj -> unsafe
        ]

        for king_pos, enemy_sq, mtype, dr, df in configs:
            ql.circuit()
            king = make_small_board(rows, cols, [king_pos])
            enemy = make_small_board(rows, cols, enemy_sq)
            result = ql.qbool()

            pred = make_check_detection_predicate(mtype, dr, df, rows, cols, enemy_attacks)
            pred(king, enemy, result)

            qasm_str = ql.to_openqasm()
            result_qubit = int(result.qubits[63])

            enemy_sets = [set(map(tuple, enemy_sq))]
            expected = self._classical_check_safe(
                king_pos, enemy_sets, enemy_attacks, mtype, dr, df, rows, cols
            )
            expected_val = 1 if expected else 0
            prob = _get_result_probability(qasm_str, result_qubit, target_value=expected_val)
            assert prob > 0.99, (
                f"check_safe mismatch: king={king_pos}, enemy={enemy_sq}, "
                f"move=({mtype},{dr},{df}), expected={expected_val}, "
                f"P({expected_val})={prob:.4f}"
            )


class TestScalingPhase115:
    """Scaling test: 8x8 check detection circuit builds without error (no simulation)."""

    def test_8x8_check_detection_builds(self, clean_circuit):
        """8x8 board, king at (4,4), enemy at (6,5), king adjacency attacks -> circuit builds."""
        from chess_encoding import _KING_OFFSETS
        from chess_predicates import make_check_detection_predicate

        king = make_small_board(8, 8, [(4, 4)])
        enemy = make_small_board(8, 8, [(6, 5)])
        result = ql.qbool()

        enemy_attacks = [(_KING_OFFSETS, "king")]
        pred = make_check_detection_predicate("knight", 2, 1, 8, 8, enemy_attacks)
        # Should not raise -- just building the circuit, no simulation
        pred(king, enemy, result)
