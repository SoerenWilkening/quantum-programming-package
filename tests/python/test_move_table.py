"""Tests for build_move_table() -- position-independent move enumeration.

Verifies that the move table provides a fixed mapping from branch register
index to (piece_id, dr, df) triples for quantum walk circuit construction.
"""

from chess_encoding import _KING_OFFSETS, _KNIGHT_OFFSETS, build_move_table


class TestMoveTableSizes:
    """Table size must be exactly 8 * len(pieces)."""

    def test_table_sizes_white_knk(self):
        """White KNK config (king + 2 knights) produces 24 entries."""
        pieces = [("wk", "king"), ("wn1", "knight"), ("wn2", "knight")]
        table = build_move_table(pieces)
        assert len(table) == 24

    def test_table_sizes_black_k(self):
        """Black K config (single king) produces 8 entries."""
        pieces = [("bk", "king")]
        table = build_move_table(pieces)
        assert len(table) == 8


class TestOffsetCorrectness:
    """Knight entries use L-shapes, king entries use adjacencies."""

    def test_knight_offsets(self):
        """Knight entries must use exactly the 8 L-shaped offsets."""
        pieces = [("wn1", "knight")]
        table = build_move_table(pieces)
        offsets = [(dr, df) for _, dr, df in table]
        assert offsets == list(_KNIGHT_OFFSETS)

    def test_king_offsets(self):
        """King entries must use exactly the 8 adjacency offsets."""
        pieces = [("wk", "king")]
        table = build_move_table(pieces)
        offsets = [(dr, df) for _, dr, df in table]
        assert offsets == list(_KING_OFFSETS)


class TestPieceIdPreserved:
    """Each entry's piece_id matches the input piece_id for that block."""

    def test_piece_id_preserved(self):
        """All entries for a piece block carry that piece's id."""
        pieces = [("wk", "king"), ("wn1", "knight"), ("wn2", "knight")]
        table = build_move_table(pieces)
        # First 8 entries belong to wk
        for entry in table[0:8]:
            assert entry[0] == "wk"
        # Next 8 belong to wn1
        for entry in table[8:16]:
            assert entry[0] == "wn1"
        # Last 8 belong to wn2
        for entry in table[16:24]:
            assert entry[0] == "wn2"


class TestSequentialIndexing:
    """First 8 entries belong to first piece, next 8 to second, etc."""

    def test_sequential_indexing(self):
        """Entries are grouped sequentially by piece order."""
        pieces = [("wk", "king"), ("wn1", "knight")]
        table = build_move_table(pieces)
        assert len(table) == 16
        # King block
        king_ids = {entry[0] for entry in table[0:8]}
        assert king_ids == {"wk"}
        # Knight block
        knight_ids = {entry[0] for entry in table[8:16]}
        assert knight_ids == {"wn1"}


class TestEmptyConfig:
    """Empty pieces list returns empty table."""

    def test_empty_config(self):
        table = build_move_table([])
        assert table == []


class TestSinglePiece:
    """Single knight produces exactly 8 entries with all knight offsets."""

    def test_single_knight(self):
        pieces = [("wn1", "knight")]
        table = build_move_table(pieces)
        assert len(table) == 8
        for pid, dr, df in table:
            assert pid == "wn1"
            assert (dr, df) in _KNIGHT_OFFSETS
        # All 8 unique offsets present
        offsets = {(dr, df) for _, dr, df in table}
        assert offsets == set(_KNIGHT_OFFSETS)
