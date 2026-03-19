"""3-SAT quantum walk assembly — single walk step with gate count."""

import time

from sat_instance import MAX_DEPTH, NUM_MOVES, NUM_VARS
from sat_walk import is_marked, is_valid, make_move

import quantum_language as ql
from quantum_language.walk_operators import walk_step

ql.option("simulate", False)  # gate counting only, no simulation

# Initialize state: 10 ternary variables, all unassigned (value 2)
x = ql.qarray([2] * NUM_VARS, width=3)

# Build marked walk configuration and registers
config, registers = ql.walk(
    is_marked,
    max_depth=MAX_DEPTH,
    num_moves=NUM_MOVES,
    state=x,
    make_move=make_move,
    is_valid=is_valid,
    undo_move=make_move.inverse,
)

# Run a single walk step
t0 = time.perf_counter()
walk_step(config, registers)
elapsed = time.perf_counter() - t0

# Display gate count and timing
print(ql.get_gate_count())
print(f"Walk step completed in {elapsed:.3f}s")
