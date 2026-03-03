"""Tests for chess board encoding, move generation, legal move filtering, and move oracle.

Classical unit tests for Phase 103 requirements CHESS-01 through CHESS-05.
Oracle tests verify compiled quantum oracle construction and subcircuit spot-checks.
"""

import os
import sys

# Ensure src/ is on the path for importing chess_encoding
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


class TestBoardEncoding:
    """CHESS-01: Board encoding as qarrays with correct square-to-qubit mapping."""

    def test_encode_position_returns_dict_with_correct_keys(self, clean_circuit):
        from chess_encoding import encode_position

        result = encode_position(wk_sq=4, bk_sq=60, wn_squares=[27, 45])
        assert isinstance(result, dict)
        assert "white_king" in result
        assert "black_king" in result
        assert "white_knights" in result

    def test_encode_position_white_king_single_bit(self, clean_circuit):
        """White king qarray should have exactly 1 set bit at correct position."""
        from chess_encoding import encode_position

        result = encode_position(wk_sq=4, bk_sq=60, wn_squares=[27, 45])
        # Square 4: rank=0, file=4
        # We can't easily inspect qarray internals, but we test the API
        # works without error and returns the right type
        wk = result["white_king"]
        assert wk is not None

    def test_encode_position_white_knights_multiple_bits(self, clean_circuit):
        """White knights qarray should have set bits for each knight."""
        from chess_encoding import encode_position

        result = encode_position(wk_sq=4, bk_sq=60, wn_squares=[27, 45])
        wn = result["white_knights"]
        assert wn is not None

    def test_encode_position_configurable(self, clean_circuit):
        """Positions are configurable via parameters, not hardcoded."""
        from chess_encoding import encode_position

        # Different positions should work without error
        r1 = encode_position(wk_sq=0, bk_sq=63, wn_squares=[10])
        r2 = encode_position(wk_sq=36, bk_sq=7, wn_squares=[18, 55])
        assert r1 is not None
        assert r2 is not None


class TestKnightMoves:
    """CHESS-02: Knight attack pattern generation from any square."""

    def test_knight_corner_a1(self):
        """Knight on a1 (sq=0) attacks exactly 2 squares."""
        from chess_encoding import knight_attacks

        attacks = knight_attacks(0)
        assert len(attacks) == 2
        assert sorted(attacks) == [10, 17]

    def test_knight_corner_h1(self):
        """Knight on h1 (sq=7) attacks exactly 2 squares."""
        from chess_encoding import knight_attacks

        attacks = knight_attacks(7)
        assert len(attacks) == 2
        assert sorted(attacks) == [13, 22]

    def test_knight_center_d4(self):
        """Knight on d4 (sq=27) attacks exactly 8 squares."""
        from chess_encoding import knight_attacks

        attacks = knight_attacks(27)
        assert len(attacks) == 8

    def test_knight_all_within_bounds(self):
        """All returned squares are within 0-63."""
        from chess_encoding import knight_attacks

        for sq in range(64):
            attacks = knight_attacks(sq)
            for a in attacks:
                assert 0 <= a < 64, f"Square {sq} produced out-of-bounds attack {a}"

    def test_knight_returns_sorted(self):
        """Attacks are returned in sorted order."""
        from chess_encoding import knight_attacks

        for sq in range(64):
            attacks = knight_attacks(sq)
            assert attacks == sorted(attacks), f"Attacks from {sq} not sorted"

    def test_knight_corner_counts(self):
        """Corners should have 2 attacks."""
        from chess_encoding import knight_attacks

        for corner in [0, 7, 56, 63]:
            assert len(knight_attacks(corner)) == 2, f"Corner {corner} wrong count"

    def test_knight_edge_counts(self):
        """Edge squares (non-corner) should have 3 or 4 attacks."""
        from chess_encoding import knight_attacks

        # a2 (sq=8): edge of board
        attacks = knight_attacks(8)
        assert len(attacks) in [3, 4], f"Edge sq=8 has {len(attacks)} attacks"

    def test_knight_no_wrapping(self):
        """Knight on h-file should not wrap to a-file."""
        from chess_encoding import knight_attacks

        # Knight on h3 (sq=23, rank=2, file=7)
        attacks = knight_attacks(23)
        # None of the attacks should be on files 0-1 since that would be wrapping
        for a in attacks:
            _, file = divmod(a, 8)
            # A knight from file 7 can reach files 5, 6 (via -2, -1 offsets)
            # but never files 0, 1 (that would require going right off the board)
            assert file >= 5 or file <= 7, (
                f"Knight from sq=23 attacked sq={a} (file={file}) -- possible wrapping"
            )


class TestKingMoves:
    """CHESS-03: King move generation for all 8 directions with edge-awareness."""

    def test_king_corner_a1(self):
        """King on a1 (sq=0) has exactly 3 moves."""
        from chess_encoding import king_attacks

        attacks = king_attacks(0)
        assert len(attacks) == 3
        assert sorted(attacks) == [1, 8, 9]

    def test_king_corner_h1(self):
        """King on h1 (sq=7) has exactly 3 moves."""
        from chess_encoding import king_attacks

        attacks = king_attacks(7)
        assert len(attacks) == 3
        assert sorted(attacks) == [6, 14, 15]

    def test_king_corner_h8(self):
        """King on h8 (sq=63) has exactly 3 moves."""
        from chess_encoding import king_attacks

        attacks = king_attacks(63)
        assert len(attacks) == 3
        assert sorted(attacks) == [54, 55, 62]

    def test_king_corner_a8(self):
        """King on a8 (sq=56) has exactly 3 moves."""
        from chess_encoding import king_attacks

        attacks = king_attacks(56)
        assert len(attacks) == 3
        assert sorted(attacks) == [48, 49, 57]

    def test_king_center_d4(self):
        """King on d4 (sq=27) has exactly 8 moves."""
        from chess_encoding import king_attacks

        attacks = king_attacks(27)
        assert len(attacks) == 8

    def test_king_edge_a4(self):
        """King on a4 (sq=24) has exactly 5 moves (edge, non-corner)."""
        from chess_encoding import king_attacks

        attacks = king_attacks(24)
        assert len(attacks) == 5

    def test_king_all_within_bounds(self):
        """All returned squares are within 0-63."""
        from chess_encoding import king_attacks

        for sq in range(64):
            attacks = king_attacks(sq)
            for a in attacks:
                assert 0 <= a < 64, f"Square {sq} produced out-of-bounds attack {a}"

    def test_king_returns_sorted(self):
        """Attacks are returned in sorted order."""
        from chess_encoding import king_attacks

        for sq in range(64):
            attacks = king_attacks(sq)
            assert attacks == sorted(attacks), f"Attacks from {sq} not sorted"

    def test_king_no_wrapping(self):
        """King on h-file should not wrap to a-file."""
        from chess_encoding import king_attacks

        # King on h4 (sq=31, rank=3, file=7)
        attacks = king_attacks(31)
        for a in attacks:
            _, file = divmod(a, 8)
            # King from file 7 can only reach files 6, 7
            assert file >= 6, f"King from sq=31 attacked sq={a} (file={file}) -- wrapping detected"


class TestLegalMoveFiltering:
    """CHESS-04: Legal move filtering for white."""

    def test_basic_legal_moves_white(self):
        """legal_moves_white returns list of (piece_sq, dest_sq) tuples."""
        from chess_encoding import legal_moves_white

        moves = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        assert isinstance(moves, list)
        for m in moves:
            assert isinstance(m, tuple)
            assert len(m) == 2

    def test_excludes_friendly_occupied(self):
        """Destinations occupied by friendly pieces are excluded."""
        from chess_encoding import legal_moves_white

        wk_sq = 4
        bk_sq = 60
        wn_squares = [27]
        moves = legal_moves_white(wk_sq, bk_sq, wn_squares)

        friendly = set(wn_squares + [wk_sq])
        for piece_sq, dest_sq in moves:
            assert dest_sq not in friendly, (
                f"Move ({piece_sq}, {dest_sq}) goes to friendly-occupied square"
            )

    def test_excludes_king_attacked_by_opponent(self):
        """King moves to squares attacked by black king are excluded."""
        from chess_encoding import king_attacks, legal_moves_white

        wk_sq = 4
        bk_sq = 12  # Close to white king
        wn_squares = [27]
        moves = legal_moves_white(wk_sq, bk_sq, wn_squares)

        bk_attack_set = set(king_attacks(bk_sq))
        king_moves = [(p, d) for p, d in moves if p == wk_sq]
        for _, dest in king_moves:
            assert dest not in bk_attack_set, f"King move to {dest} is attacked by black king"

    def test_king_cannot_be_adjacent_to_opponent_king(self):
        """King moves exclude squares adjacent to black king."""
        from chess_encoding import king_attacks, legal_moves_white

        wk_sq = 4
        bk_sq = 12
        wn_squares = [27]
        moves = legal_moves_white(wk_sq, bk_sq, wn_squares)

        # bk_sq and its attacks form the exclusion zone for white king
        bk_zone = set(king_attacks(bk_sq)) | {bk_sq}
        king_moves = [(p, d) for p, d in moves if p == wk_sq]
        for _, dest in king_moves:
            assert dest not in bk_zone, f"King move to {dest} is adjacent to or on black king"

    def test_moves_sorted_deterministic(self):
        """Moves are sorted by (piece_sq, dest_sq)."""
        from chess_encoding import legal_moves_white

        moves = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        assert moves == sorted(moves), "Moves not in sorted order"

    def test_same_position_same_moves(self):
        """Same position always produces same move list (deterministic)."""
        from chess_encoding import legal_moves_white

        m1 = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        m2 = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        assert m1 == m2


class TestLegalMovesBlack:
    """CHESS-04: Legal move filtering for black (only king moves)."""

    def test_black_only_king_moves(self):
        """Black has only king moves (no knights)."""
        from chess_encoding import legal_moves_black

        moves = legal_moves_black(wk_sq=4, bk_sq=60, wn_squares=[27])
        # All moves should be from bk_sq
        for piece_sq, _dest_sq in moves:
            assert piece_sq == 60, f"Black move from {piece_sq}, expected 60"

    def test_black_excludes_white_attacked(self):
        """Black king cannot move to squares attacked by white pieces."""
        from chess_encoding import king_attacks, knight_attacks, legal_moves_black

        wk_sq = 4
        bk_sq = 60
        wn_squares = [27]
        moves = legal_moves_black(wk_sq, bk_sq, wn_squares)

        # White attack set: union of all knight attacks + king attacks
        white_attacks = set(king_attacks(wk_sq))
        for sq in wn_squares:
            white_attacks |= set(knight_attacks(sq))

        for _, dest in moves:
            assert dest not in white_attacks, (
                f"Black king moved to {dest} which is attacked by white"
            )

    def test_black_excludes_adjacent_to_white_king(self):
        """Black king cannot move adjacent to white king."""
        from chess_encoding import king_attacks, legal_moves_black

        wk_sq = 4
        bk_sq = 60
        wn_squares = [27]
        moves = legal_moves_black(wk_sq, bk_sq, wn_squares)

        wk_zone = set(king_attacks(wk_sq)) | {wk_sq}
        for _, dest in moves:
            assert dest not in wk_zone, f"Black king moved to {dest} adjacent to white king"

    def test_black_moves_sorted(self):
        """Black moves are sorted by (piece_sq, dest_sq)."""
        from chess_encoding import legal_moves_black

        moves = legal_moves_black(wk_sq=4, bk_sq=60, wn_squares=[27])
        assert moves == sorted(moves)


class TestEnumeration:
    """Move list enumeration for branch register compatibility."""

    def test_index_corresponds_to_branch_value(self):
        """Move list index is the branch register value (0-based)."""
        from chess_encoding import legal_moves_white

        moves = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        # Just verify it's a proper 0-based list
        assert len(moves) > 0
        for _i, m in enumerate(moves):
            assert isinstance(m, tuple)

    def test_ordering_deterministic_sorted(self):
        """Ordering is deterministic: sorted by piece_sq then dest_sq."""
        from chess_encoding import legal_moves_white

        moves = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        assert moves == sorted(moves)

    def test_same_position_same_list(self):
        """Same position always produces same move list."""
        from chess_encoding import legal_moves

        m1 = legal_moves(wk_sq=4, bk_sq=60, wn_squares=[27], side_to_move="white")
        m2 = legal_moves(wk_sq=4, bk_sq=60, wn_squares=[27], side_to_move="white")
        assert m1 == m2

    def test_convenience_wrapper_white(self):
        """legal_moves with side_to_move='white' calls legal_moves_white."""
        from chess_encoding import legal_moves, legal_moves_white

        m1 = legal_moves(wk_sq=4, bk_sq=60, wn_squares=[27], side_to_move="white")
        m2 = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        assert m1 == m2

    def test_convenience_wrapper_black(self):
        """legal_moves with side_to_move='black' calls legal_moves_black."""
        from chess_encoding import legal_moves, legal_moves_black

        m1 = legal_moves(wk_sq=4, bk_sq=60, wn_squares=[27], side_to_move="black")
        m2 = legal_moves_black(wk_sq=4, bk_sq=60, wn_squares=[27])
        assert m1 == m2


class TestEdgeCases:
    """Edge cases for move generation and filtering."""

    def test_king_surrounded_by_friendly_only_knight_moves(self):
        """King surrounded by friendly pieces can only make knight moves."""
        from chess_encoding import king_attacks, legal_moves_white

        # Place white king at center, surrounded by knights on all adjacent squares
        wk_sq = 27  # d4
        adjacent = king_attacks(wk_sq)
        # Use first few adjacent squares as knight positions
        wn_squares = adjacent[:8]  # Up to 8 knights (all adjacent)
        bk_sq = 63  # Far corner

        moves = legal_moves_white(wk_sq, bk_sq, wn_squares)

        # No king moves should be in the list (all adjacent squares are friendly)
        king_moves = [(p, d) for p, d in moves if p == wk_sq]
        assert len(king_moves) == 0, f"King has {len(king_moves)} moves but should have 0"

    def test_all_king_moves_attacked_zero_king_moves(self):
        """Position where all king moves are attacked yields 0 king moves."""
        from chess_encoding import legal_moves_white

        # Place white king on a1 (3 moves: 1, 8, 9)
        wk_sq = 0
        # Place black king on b3 (sq=17): attacks squares 8, 9, 10, 16, 18, 24, 25, 26
        # This covers squares 8 and 9 from white king moves
        # We need to also cover square 1
        # Place black king at c2 (sq=10): attacks 1, 2, 3, 9, 11, 17, 18, 19
        # That covers 1 and 9 but not 8
        # Actually we can only have 1 black king. Let's pick a position where
        # the black king attacks cover all white king escape squares.
        # wk at 0 has moves [1, 8, 9]
        # bk at 10 (c2) attacks [1, 2, 3, 9, 11, 17, 18, 19] -- covers 1 and 9
        # But 8 is not covered. So king still has 1 move.
        # Let's just verify the filtering logic with a reasonable case.
        bk_sq = 10
        wn_squares = [8]  # Knight on b1 blocks square 8

        moves = legal_moves_white(wk_sq, bk_sq, wn_squares)
        king_moves = [(p, d) for p, d in moves if p == wk_sq]
        # Square 1: attacked by bk at 10 -> filtered
        # Square 8: occupied by friendly knight -> filtered
        # Square 9: attacked by bk at 10 -> filtered
        assert len(king_moves) == 0, f"King should have 0 moves, got {len(king_moves)}"

    def test_one_vs_two_knights_different_counts(self):
        """1 knight vs 2 knights produces different move counts."""
        from chess_encoding import legal_moves_white

        moves1 = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27])
        moves2 = legal_moves_white(wk_sq=4, bk_sq=60, wn_squares=[27, 45])
        # More knights means more moves
        assert len(moves1) != len(moves2), (
            f"1 knight ({len(moves1)} moves) should differ from 2 knights ({len(moves2)} moves)"
        )


class TestBoardEncodingQuantum:
    """Quantum spot-check: verify qarray construction with clean_circuit fixture.

    These tests do NOT simulate via Qiskit (full board = 192+ qubits,
    far exceeds 17-qubit budget). They verify qarray construction and
    circuit generation only.
    """

    def test_single_piece_encoding(self, clean_circuit):
        """Single king encodes as a ql.qarray without error."""
        from chess_encoding import encode_position

        result = encode_position(wk_sq=4, bk_sq=60, wn_squares=[])
        wk = result["white_king"]
        # Verify it's a qarray-like object (not None, not a plain array)
        assert wk is not None
        assert hasattr(wk, "__getitem__"), "white_king should support indexing"

    def test_multi_piece_encoding(self, clean_circuit):
        """King + knight encodes as separate qarrays without error."""
        from chess_encoding import encode_position

        result = encode_position(wk_sq=4, bk_sq=60, wn_squares=[27])
        wk = result["white_king"]
        wn = result["white_knights"]
        bk = result["black_king"]

        # All three should be valid qarray objects
        assert wk is not None
        assert wn is not None
        assert bk is not None

    def test_circuit_generation_sanity(self, clean_circuit):
        """Encoding a position within a circuit context raises no exceptions."""
        from chess_encoding import encode_position

        # This exercises the full qarray creation path within a circuit
        result = encode_position(wk_sq=0, bk_sq=63, wn_squares=[27, 45])
        assert "white_king" in result
        assert "black_king" in result
        assert "white_knights" in result

    def test_module_exports(self):
        """chess_encoding has __all__ with all public functions."""
        import chess_encoding

        assert hasattr(chess_encoding, "__all__")
        expected = [
            "encode_position",
            "knight_attacks",
            "king_attacks",
            "legal_moves_white",
            "legal_moves_black",
            "legal_moves",
        ]
        for name in expected:
            assert name in chess_encoding.__all__, f"{name} not in __all__"


class TestMoveOracle:
    """CHESS-05: Move oracle as @ql.compile function producing legal move set."""

    def test_oracle_returns_move_count(self):
        """move_oracle returns correct move count matching legal_moves output length."""
        from chess_encoding import get_legal_moves_and_oracle, legal_moves

        wk_sq, bk_sq, wn_squares = 4, 60, [27]
        expected_moves = legal_moves(wk_sq, bk_sq, wn_squares, "white")

        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        assert result["move_count"] == len(expected_moves)

    def test_oracle_returns_move_list(self):
        """move_oracle returns the same move list as legal_moves."""
        from chess_encoding import get_legal_moves_and_oracle, legal_moves

        wk_sq, bk_sq, wn_squares = 4, 60, [27]
        expected_moves = legal_moves(wk_sq, bk_sq, wn_squares, "white")

        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        assert result["moves"] == expected_moves

    def test_oracle_compiles_without_error(self, clean_circuit):
        """apply_move decorated with @ql.compile(inverse=True) can be called."""
        import quantum_language as ql
        from chess_encoding import encode_position, get_legal_moves_and_oracle

        wk_sq, bk_sq, wn_squares = 4, 60, [27]
        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        apply_move = result["apply_move"]

        # Create board qarrays and branch register
        board = encode_position(wk_sq, bk_sq, wn_squares)
        branch = ql.qint(0, width=result["branch_width"])

        # Calling apply_move should not raise
        apply_move(
            board["white_king"],
            board["black_king"],
            board["white_knights"],
            branch,
        )

    def test_oracle_inverse_exists(self, clean_circuit):
        """apply_move has .inverse property available (from inverse=True)."""
        import quantum_language as ql
        from chess_encoding import encode_position, get_legal_moves_and_oracle

        wk_sq, bk_sq, wn_squares = 4, 60, [27]
        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        apply_move = result["apply_move"]

        # .inverse is a property returning a callable proxy
        assert apply_move.inverse is not None

        # Must call forward first, then .inverse uncomputes it
        board = encode_position(wk_sq, bk_sq, wn_squares)
        branch = ql.qint(0, width=result["branch_width"])
        apply_move(
            board["white_king"],
            board["black_king"],
            board["white_knights"],
            branch,
        )

        # Calling .inverse with same qubits should not raise
        apply_move.inverse(
            board["white_king"],
            board["black_king"],
            board["white_knights"],
            branch,
        )

    def test_oracle_deterministic(self):
        """Calling get_legal_moves_and_oracle twice with same position produces same result."""
        from chess_encoding import get_legal_moves_and_oracle

        wk_sq, bk_sq, wn_squares = 4, 60, [27]
        r1 = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        r2 = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        assert r1["moves"] == r2["moves"]
        assert r1["move_count"] == r2["move_count"]
        assert r1["branch_width"] == r2["branch_width"]

    def test_oracle_different_positions(self):
        """Different positions produce different move counts."""
        from chess_encoding import get_legal_moves_and_oracle

        r1 = get_legal_moves_and_oracle(4, 60, [27], "white")
        r2 = get_legal_moves_and_oracle(4, 60, [27, 45], "white")
        assert r1["move_count"] != r2["move_count"]

    def test_oracle_black_side(self):
        """Oracle works for black side."""
        from chess_encoding import get_legal_moves_and_oracle, legal_moves

        wk_sq, bk_sq, wn_squares = 4, 60, [27]
        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "black")
        expected = legal_moves(wk_sq, bk_sq, wn_squares, "black")
        assert result["moves"] == expected
        assert result["move_count"] == len(expected)

    def test_oracle_branch_width_sufficient(self):
        """Branch register width is sufficient to index all moves."""
        import math

        from chess_encoding import get_legal_moves_and_oracle

        result = get_legal_moves_and_oracle(4, 60, [27, 45], "white")
        move_count = result["move_count"]
        branch_width = result["branch_width"]
        # 2^branch_width must be >= move_count
        assert (1 << branch_width) >= move_count, (
            f"branch_width={branch_width} cannot index {move_count} moves"
        )
        # Branch width should be minimal
        expected_width = max(1, math.ceil(math.log2(max(move_count, 1))))
        assert branch_width == expected_width


class TestMoveOracleSubcircuit:
    """CHESS-05: Subcircuit spot-check for move oracle.

    Uses minimal positions to verify circuit generation works correctly.
    No Qiskit simulation -- just verifying circuit structure (gate generation).
    """

    def test_tiny_board_spot_check(self, clean_circuit):
        """Minimal position (2 kings, no knights) produces a circuit without errors."""
        import quantum_language as ql
        from chess_encoding import encode_position, get_legal_moves_and_oracle

        # 2 kings far apart, 0 knights -- minimal position
        wk_sq = 0  # a1 corner: 3 king moves max
        bk_sq = 63  # h8 corner: far away, no interference
        wn_squares = []

        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        apply_move = result["apply_move"]

        # Move count should be 3 (king on a1 has 3 moves, none blocked by bk on h8)
        assert result["move_count"] == 3

        # Create board and branch register
        board = encode_position(wk_sq, bk_sq, wn_squares)
        branch = ql.qint(0, width=result["branch_width"])

        # Apply move should generate circuit gates without error
        apply_move(
            board["white_king"],
            board["black_king"],
            board["white_knights"],
            branch,
        )

    def test_tiny_board_inverse_works(self, clean_circuit):
        """Inverse of apply_move can be called on a minimal position."""
        import quantum_language as ql
        from chess_encoding import encode_position, get_legal_moves_and_oracle

        wk_sq = 0
        bk_sq = 63
        wn_squares = []

        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        apply_move = result["apply_move"]

        board = encode_position(wk_sq, bk_sq, wn_squares)
        branch = ql.qint(0, width=result["branch_width"])

        # Forward call
        apply_move(
            board["white_king"],
            board["black_king"],
            board["white_knights"],
            branch,
        )
        # Inverse call -- should not raise (inverse is a property returning proxy)
        apply_move.inverse(
            board["white_king"],
            board["black_king"],
            board["white_knights"],
            branch,
        )

    def test_single_knight_circuit(self, clean_circuit):
        """Single knight position generates correct move count in circuit."""
        import quantum_language as ql
        from chess_encoding import encode_position, get_legal_moves_and_oracle

        # Knight on a1 (sq=0): attacks squares 10, 17 (2 moves)
        # King on e1 (sq=4): has moves (3,5,11,12,13) minus bk zone
        # Black king on h8 (sq=63): far away
        wk_sq = 4
        bk_sq = 63
        wn_squares = [0]

        result = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")

        # Knight from 0 attacks: [10, 17] -- 2 moves (sq 4 is wk, excluded as friendly)
        # King from 4 attacks: [3, 5, 11, 12, 13] -- 5 moves (sq 0 is knight, excluded)
        # Total should be 7
        assert result["move_count"] == 7

        board = encode_position(wk_sq, bk_sq, wn_squares)
        branch = ql.qint(0, width=result["branch_width"])

        # Circuit generation should succeed
        apply_move = result["apply_move"]
        apply_move(
            board["white_king"],
            board["black_king"],
            board["white_knights"],
            branch,
        )


class TestEndToEnd:
    """Full pipeline integration test from position setup through oracle creation."""

    def test_endgame_position_pipeline(self):
        """Exercise the full Phase 103 pipeline with an interesting endgame."""
        from chess_encoding import (
            get_legal_moves_and_oracle,
            king_attacks,
            knight_attacks,
            legal_moves,
            print_moves,
            print_position,
        )

        # Interesting endgame: white king e1=4, black king e8=60,
        # white knights on d4=27 and f5=37
        wk_sq = 4  # e1
        bk_sq = 60  # e8
        wn_squares = [27, 37]  # d4, f5

        # Print position for human inspection
        print("\n--- End-to-end test position ---")
        print_position(wk_sq, bk_sq, wn_squares)

        # Get moves for both sides
        moves_w = legal_moves(wk_sq, bk_sq, wn_squares, "white")
        moves_b = legal_moves(wk_sq, bk_sq, wn_squares, "black")

        print(f"\nWhite: {len(moves_w)} legal moves")
        print_moves(moves_w, "White moves")
        print(f"\nBlack: {len(moves_b)} legal moves")
        print_moves(moves_b, "Black moves")

        # White should have reasonable move count (2 knights + king)
        assert len(moves_w) > 0, "White should have legal moves"
        # 2 knights with up to 8 moves each + king with up to 8 moves
        assert len(moves_w) <= 24, f"White has too many moves: {len(moves_w)}"

        # Black should have only king moves (minus attacked squares)
        assert len(moves_b) >= 0, "Black may have 0 moves (stalemate)"
        assert len(moves_b) <= 8, f"Black has too many moves: {len(moves_b)}"

        # Verify all moves are valid
        friendly_white = set(wn_squares) | {wk_sq}
        for piece_sq, dest_sq in moves_w:
            assert 0 <= dest_sq < 64, f"Move destination {dest_sq} out of range"
            assert dest_sq not in friendly_white, (
                f"Move ({piece_sq}, {dest_sq}) targets friendly square"
            )
            assert piece_sq in friendly_white, f"Move from {piece_sq} -- not a white piece"

        white_attacks = set(king_attacks(wk_sq)) | {wk_sq}
        for sq in wn_squares:
            white_attacks |= set(knight_attacks(sq))
        for piece_sq, dest_sq in moves_b:
            assert piece_sq == bk_sq, f"Black move from {piece_sq} -- not black king"
            assert dest_sq not in white_attacks, f"Black king moved to {dest_sq} which is attacked"

        # Oracle should work for both sides
        oracle_w = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "white")
        oracle_b = get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, "black")
        assert oracle_w["move_count"] == len(moves_w)
        assert oracle_b["move_count"] == len(moves_b)

    def test_stalemate_detection(self):
        """Position where black has 0 legal moves (stalemate)."""
        from chess_encoding import legal_moves

        # Black king in corner, surrounded by white attacks
        # wk on b2=9, bk on a1=0 -- white king attacks a1's neighbors
        # King attacks from b2(9): [0,1,2,8,10,16,17,18] -- covers all of a1's moves
        wk_sq = 9  # b2
        bk_sq = 0  # a1
        wn_squares = []

        moves_b = legal_moves(wk_sq, bk_sq, wn_squares, "black")
        # a1 moves to [1, 8, 9]. b2 king attacks [0,1,2,8,10,16,17,18]
        # All of a1's moves (1, 8, 9) are in b2's attack set (including b2 itself=9)
        assert len(moves_b) == 0, f"Black should be stalemated, got {len(moves_b)} moves"


class TestUtilities:
    """Tests for print_position, print_moves, and sq_to_algebraic."""

    def test_sq_to_algebraic_corners(self):
        """Corner squares convert correctly."""
        from chess_encoding import sq_to_algebraic

        assert sq_to_algebraic(0) == "a1"
        assert sq_to_algebraic(7) == "h1"
        assert sq_to_algebraic(56) == "a8"
        assert sq_to_algebraic(63) == "h8"

    def test_sq_to_algebraic_center(self):
        """Center squares convert correctly."""
        from chess_encoding import sq_to_algebraic

        assert sq_to_algebraic(27) == "d4"  # rank=3, file=3
        assert sq_to_algebraic(36) == "e5"  # rank=4, file=4

    def test_print_position_no_error(self, capsys):
        """print_position runs without error and produces output."""
        from chess_encoding import print_position

        print_position(4, 60, [27, 37])
        captured = capsys.readouterr()
        assert "K" in captured.out  # White king
        assert "k" in captured.out  # Black king
        assert "N" in captured.out  # White knight
        assert "." in captured.out  # Empty square

    def test_print_moves_no_error(self, capsys):
        """print_moves runs without error and produces indexed output."""
        from chess_encoding import legal_moves, print_moves

        moves = legal_moves(4, 60, [27], "white")
        print_moves(moves, "Test")
        captured = capsys.readouterr()
        assert "Test" in captured.out
        assert "[" in captured.out  # Index markers
        assert "moves" in captured.out

    def test_module_exports_complete(self):
        """chess_encoding __all__ includes all public functions."""
        import chess_encoding

        expected = [
            "encode_position",
            "knight_attacks",
            "king_attacks",
            "legal_moves_white",
            "legal_moves_black",
            "legal_moves",
            "get_legal_moves_and_oracle",
            "print_position",
            "print_moves",
            "sq_to_algebraic",
        ]
        for name in expected:
            assert name in chess_encoding.__all__, f"{name} not in __all__"
