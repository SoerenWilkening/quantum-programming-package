#!/usr/bin/env python3
"""Demo script showcasing quantum_language package functionality.

Run after compiling with: python setup.py build_ext --inplace
"""

import itertools
import time

import numpy as np

import quantum_language as ql
from quantum_language.draw import render

#
# # detect win
# def detect_win(board: ql.qarray, step: ql.qint, player: int):
# 	# (step == player) | (step == 3)
# 	with (step == player) | (step == 3):
# 		step += 1
# 	# with (board[:, 0] == player).all() | (board[:, 1] == player).all() | (board[:, 2] == player).all():
# 	# with (board[:, 0] == player).all():
# 	# 	pass
# 	# 	step += 1
# 	#
# 	# with (board[0, :] == player).all() | (board[1, :] == player).all() | (board[2, :] == player).all():
# 	# 	step += 1
# 	#
# 	# with (board[0, 0] == player) | (board[1, 1] == player) | (board[2, 2] == player):
# 	# 	step += 1
# 	#
# 	# return step != 0
#
# CROSS = 0
# CIRCLE = 1
#
# board = ql.qarray([[2] * 3] * 3, width = 3)
#
# cr = ql.qint(0, width = 3)
# ci = ql.qint(0, width = 3)
#
# cr_win = detect_win(board, cr, CIRCLE)
#
# # board[0, 0] + 3
# # board[0, 0] += 1
# board[0, 0].print_circuit()


def knight_moves(position):
    file, rank = position

    # Convert chess notation to 0-based indices
    if isinstance(file, str):
        file = ord(file.lower()) - ord("a")
    if isinstance(rank, int) and rank >= 1:
        rank -= 1

    rank = 7 - rank
    board = np.zeros((8, 8), dtype=int)

    knight_offsets = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]

    for df, dr in knight_offsets:
        nf, nr = file + df, rank + dr
        if 0 <= nf < 8 and 0 <= nr < 8:
            board[nr, nf] = 1

    return board


# try some initialization
N_pos = np.zeros((8, 8))
N_pos[3, 5] = 1
N_pos[5, 4] = 1
N_pos[5, 3] = 1
print(N_pos)

knights = ql.qarray(N_pos, dtype=ql.qbool)

# determine which squares are attacked by white


@ql.compile(inverse=True)
def attack():
    arr = ql.qarray([[0] * 8] * 8, width=3)
    for i, j in itertools.product(["a", "b", "c", "d", "e", "f", "g", "h"], range(1, 8)):
        with knights[ord(i) - ord("a"), j]:  # knight on square
            arr += knight_moves((i, j))

    attacked = arr != 0

    king = ql.qarray([[0] * 8] * 8, dtype=ql.qbool)

    in_check = (king & attacked).any()
    return in_check


in_check = attack()
counter = ql.qint(width=5)
with in_check:
    counter += 1
attack.inverse()
knights[0, 0].print_circuit()

start = time.time()
data = knights[0, 0].draw_data()
img = render(data, overlap=False)
elapsed = time.time() - start
# Get draw data and render
img.save("test_circuit.png")
# img.show()
print(f"Size: {img.size}, rendered in {elapsed:.2f}s")
