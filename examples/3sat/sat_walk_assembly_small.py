"""3-SAT quantum walk assembly — small test (3 vars, 3 clauses)."""

import time

import quantum_language as ql
from quantum_language.walk_operators import walk_step

ql.option("simulate", False)  # gate counting only, no simulation

# Tiny instance: 3 variables, 3 clauses
# Known solution: [1, 0, 1]
SMALL_NUM_VARS = 3
SMALL_CLAUSES = [
    [(0, True), (1, False), (2, True)],  # x0 OR ~x1 OR x2
    [(0, False), (1, True), (2, False)],  # ~x0 OR x1 OR ~x2
    [(0, True), (1, True), (2, True)],  # x0 OR x1 OR x2
]


@ql.compile(opt=1, inverse=True)
def make_move(x, move_index):
    assigned = ql.qbool()
    for i in range(SMALL_NUM_VARS):
        is_unassigned = x[i] == 2
        can_assign = is_unassigned & (~assigned)
        with can_assign:
            x[i] ^= 2 ^ move_index
            assigned ^= 1


def is_valid(x):
    violation_count = ql.qint(0, width=3)
    for clause in SMALL_CLAUSES:
        (v0, p0), (v1, p1), (v2, p2) = clause
        f0 = x[v0] == (0 if p0 else 1)
        f1 = x[v1] == (0 if p1 else 1)
        f2 = x[v2] == (0 if p2 else 1)
        violated = f0 & f1 & f2
        with violated:
            violation_count += 1
    return violation_count == 0


def is_marked(x):
    unassigned_count = ql.qint(0, width=2)
    for i in range(SMALL_NUM_VARS):
        unassigned = x[i] == 2
        with unassigned:
            unassigned_count += 1

    violation_count = ql.qint(0, width=3)
    for clause in SMALL_CLAUSES:
        (v0, p0), (v1, p1), (v2, p2) = clause
        f0 = x[v0] == (0 if p0 else 1)
        f1 = x[v1] == (0 if p1 else 1)
        f2 = x[v2] == (0 if p2 else 1)
        violated = f0 & f1 & f2
        with violated:
            violation_count += 1

    all_assigned = unassigned_count == 0
    all_satisfied = violation_count == 0
    return all_assigned & all_satisfied


ql.option("simulate", False)
x = ql.qarray([2] * SMALL_NUM_VARS, width=3)

config, registers = ql.walk(
    is_marked,
    max_depth=SMALL_NUM_VARS,
    num_moves=2,
    state=x,
    make_move=make_move,
    is_valid=is_valid,
    # undo_move=make_move.inverse,
)

t0 = time.perf_counter()
walk_step(config, registers)
elapsed = time.perf_counter() - t0

print(ql.get_gate_count())
print(f"Walk step completed in {elapsed:.3f}s")
