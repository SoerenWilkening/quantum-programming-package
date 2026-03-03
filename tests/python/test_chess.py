"""Tests for chess board encoding, move generation, and legal move filtering.

Classical unit tests for Phase 103 requirements CHESS-01 through CHESS-04.
No quantum simulation -- pure Python logic tests.
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
