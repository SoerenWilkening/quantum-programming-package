"""Quantum predicate factories for chess move conditions.

Provides factory functions that create compiled quantum predicates for
evaluating chess move legality in superposition. Each factory performs
classical precomputation (enumerating valid source squares, filtering
off-board destinations) then returns a @ql.compile(inverse=True) function
that operates only on quantum data.

Predicates follow the same factory pattern as _make_apply_move in
chess_encoding.py: classical closure data outside @ql.compile, quantum
operations inside.

Piece types supported:
    - Piece-exists: checks if a piece occupies any source square with a
      valid destination for a given move offset (dr, df).
"""

import quantum_language as ql

__all__ = ["make_piece_exists_predicate"]


def make_piece_exists_predicate(piece_id, dr, df, board_rows, board_cols):
    """Create a compiled predicate that checks if a piece can make move (dr, df).

    Returns a @ql.compile(inverse=True) function that flips result qbool
    to |1> if piece_qarray has a piece at any square (r, f) such that
    (r+dr, f+df) is within bounds.

    Classical precomputation enumerates all (r, f) with valid destinations
    at construction time. Off-board moves produce no quantum gates (classical
    skip). If no source square has the piece, the result stays |0> naturally.

    XOR vs OR note: For the KNK endgame, each piece type has exactly one
    instance per board qarray (1 white king, 1 black king). White knights
    qarray may have 2 knights, but the predicate is called per-move-offset
    (dr, df), and for a given (dr, df) each knight independently checks its
    own source square. Since each square has at most one piece, only one
    ``with board[r,f]:`` fires per basis state, so XOR = OR and the simple
    ``~result`` pattern is correct.

    Parameters
    ----------
    piece_id : str
        Identifier for debugging/logging (not used in quantum logic).
    dr : int
        Rank delta for the move.
    df : int
        File delta for the move.
    board_rows : int
        Number of rows on the board.
    board_cols : int
        Number of columns on the board.

    Returns
    -------
    CompiledFunc
        A @ql.compile(inverse=True) function with signature
        ``piece_exists(piece_qarray, result)`` where result is a qbool
        that gets flipped to |1> if the condition holds.
    """
    # Classical precomputation: which (r, f) have valid destinations
    valid_sources = []
    for r in range(board_rows):
        for f in range(board_cols):
            tr, tf = r + dr, f + df
            if 0 <= tr < board_rows and 0 <= tf < board_cols:
                valid_sources.append((r, f))

    @ql.compile(inverse=True)
    def piece_exists(piece_qarray, result):
        """Flip result to |1> if piece_qarray has a piece at any valid source.

        For each valid source (r, f), conditionally flips result when
        piece_qarray[r, f] is |1>. Uses flat sequential ``with`` blocks
        (no nesting) to respect the Toffoli-AND limitation.
        """
        for r, f in valid_sources:
            with piece_qarray[r, f]:
                ~result  # noqa: B018 -- quantum NOT (calls __invert__)

    return piece_exists
