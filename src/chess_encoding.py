"""Chess board encoding and legal move generation for quantum walk demo.

Square indexing convention:
    - Square index 0-63 where sq = rank * 8 + file
    - rank 0 = chess rank 1 (bottom of board from white's perspective)
    - rank, file = divmod(sq, 8)
    - qarray indexing: board[rank, file]

This module provides classical move generation for a simplified chess endgame
(2 kings + white knights). All move generation is purely classical since
starting positions are known at circuit construction time. The quantum part
(board encoding as qarrays) interfaces with quantum_language for Phase 104's
quantum walk.

Piece types supported:
    - White king (1 piece)
    - Black king (1 piece)
    - White knights (configurable, typically 1-2)
"""

import numpy as np

import quantum_language as ql

__all__ = [
    "encode_position",
    "knight_attacks",
    "king_attacks",
    "legal_moves_white",
    "legal_moves_black",
    "legal_moves",
]

# Knight L-shaped move offsets (rank_delta, file_delta)
_KNIGHT_OFFSETS = [
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
]

# King adjacent move offsets (rank_delta, file_delta)
_KING_OFFSETS = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
]


def encode_position(wk_sq, bk_sq, wn_squares):
    """Encode a chess position as qarrays.

    Creates separate qarrays for each piece type, with X-gates applied
    on occupied squares (classical initialization).

    Parameters
    ----------
    wk_sq : int
        White king square (0-63).
    bk_sq : int
        Black king square (0-63).
    wn_squares : list[int]
        White knight square(s), each 0-63.

    Returns
    -------
    dict
        Keys: 'white_king', 'black_king', 'white_knights'.
        Values: ql.qarray objects (8x8 qbool arrays).
    """
    wk = np.zeros((8, 8), dtype=int)
    wk[wk_sq // 8, wk_sq % 8] = 1

    bk = np.zeros((8, 8), dtype=int)
    bk[bk_sq // 8, bk_sq % 8] = 1

    wn = np.zeros((8, 8), dtype=int)
    for sq in wn_squares:
        wn[sq // 8, sq % 8] = 1

    return {
        "white_king": ql.qarray(wk, dtype=ql.qbool),
        "black_king": ql.qarray(bk, dtype=ql.qbool),
        "white_knights": ql.qarray(wn, dtype=ql.qbool),
    }


def knight_attacks(square):
    """Return sorted list of squares attacked by a knight on ``square``.

    Parameters
    ----------
    square : int
        Square index 0-63 (rank * 8 + file).

    Returns
    -------
    list[int]
        Attacked square indices, sorted ascending.
    """
    rank, file = divmod(square, 8)
    attacks = []
    for dr, df in _KNIGHT_OFFSETS:
        nr, nf = rank + dr, file + df
        if 0 <= nr < 8 and 0 <= nf < 8:
            attacks.append(nr * 8 + nf)
    return sorted(attacks)


def king_attacks(square):
    """Return sorted list of squares attacked by a king on ``square``.

    Parameters
    ----------
    square : int
        Square index 0-63 (rank * 8 + file).

    Returns
    -------
    list[int]
        Attacked square indices, sorted ascending.
    """
    rank, file = divmod(square, 8)
    attacks = []
    for dr, df in _KING_OFFSETS:
        nr, nf = rank + dr, file + df
        if 0 <= nr < 8 and 0 <= nf < 8:
            attacks.append(nr * 8 + nf)
    return sorted(attacks)


def legal_moves_white(wk_sq, bk_sq, wn_squares):
    """Return enumerated legal moves for white.

    Generates all legal moves for white's pieces (knights + king),
    filtering out moves to friendly-occupied squares and king moves
    to squares attacked by the black king.

    Parameters
    ----------
    wk_sq : int
        White king square (0-63).
    bk_sq : int
        Black king square (0-63).
    wn_squares : list[int]
        White knight square(s).

    Returns
    -------
    list[tuple[int, int]]
        Sorted list of (piece_square, destination_square) pairs.
        Index in list = branch register value.
    """
    moves = []
    friendly_squares = set(wn_squares) | {wk_sq}

    # Black king attacks -- squares white king cannot move to
    bk_attack_set = set(king_attacks(bk_sq)) | {bk_sq}

    # Knight moves (sorted by piece square for determinism)
    for sq in sorted(wn_squares):
        for dest in knight_attacks(sq):
            if dest not in friendly_squares:
                moves.append((sq, dest))

    # King moves
    for dest in king_attacks(wk_sq):
        if dest not in friendly_squares and dest not in bk_attack_set:
            moves.append((wk_sq, dest))

    # Sort by (piece_sq, dest_sq) for deterministic ordering
    moves.sort()
    return moves


def legal_moves_black(wk_sq, bk_sq, wn_squares):
    """Return enumerated legal moves for black.

    In the simplified KNK endgame, black only has a king.
    Filters out squares attacked by any white piece.

    Parameters
    ----------
    wk_sq : int
        White king square (0-63).
    bk_sq : int
        Black king square (0-63).
    wn_squares : list[int]
        White knight square(s).

    Returns
    -------
    list[tuple[int, int]]
        Sorted list of (bk_sq, destination_square) pairs.
        Index in list = branch register value.
    """
    # Compute white attack set: all squares attacked by white pieces
    white_attack_set = set(king_attacks(wk_sq)) | {wk_sq}
    for sq in wn_squares:
        white_attack_set |= set(knight_attacks(sq))

    # Black king moves, excluding attacked squares
    moves = []
    for dest in king_attacks(bk_sq):
        if dest not in white_attack_set:
            moves.append((bk_sq, dest))

    moves.sort()
    return moves


def legal_moves(wk_sq, bk_sq, wn_squares, side_to_move):
    """Convenience wrapper returning legal moves for the specified side.

    Parameters
    ----------
    wk_sq : int
        White king square (0-63).
    bk_sq : int
        Black king square (0-63).
    wn_squares : list[int]
        White knight square(s).
    side_to_move : str
        'white' or 'black'.

    Returns
    -------
    list[tuple[int, int]]
        Enumerated legal move list (index = branch register value).
    """
    if side_to_move == "white":
        return legal_moves_white(wk_sq, bk_sq, wn_squares)
    elif side_to_move == "black":
        return legal_moves_black(wk_sq, bk_sq, wn_squares)
    else:
        raise ValueError(f"side_to_move must be 'white' or 'black', got {side_to_move!r}")
