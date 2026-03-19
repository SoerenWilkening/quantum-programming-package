"""Minimal 3-SAT instance for inspecting the walk_step call graph.

Uses 3 variables and 2 clauses — same structure as the full instance
but fast enough to generate the call graph in seconds.
"""

import quantum_language as ql

# Tiny instance: 3 variables, 2 clauses
NUM_VARS = 3
CLAUSES = [
    (1, -2, 3),
    (-1, 2, -3),
]
VAR_WIDTH = 2


@ql.compile(inverse=True)
def make_move(x, move_index):
    assigned = ql.qbool()
    for i in range(NUM_VARS):
        is_unassigned = x[i] == 2
        can_assign = is_unassigned & (~assigned)
        with can_assign:
            x[i] ^= 2 ^ move_index
            assigned ^= 1


def _literal_satisfied(x, literal):
    var_idx = abs(literal) - 1
    if literal > 0:
        return x[var_idx] == 1
    else:
        return x[var_idx] == 0


def _literal_assigned(x, literal):
    var_idx = abs(literal) - 1
    return x[var_idx] != 2


def is_valid(x):
    num_falsified = ql.qint(0, width=2)
    for clause in CLAUSES:
        l1, l2, l3 = clause
        all_assigned = (
            _literal_assigned(x, l1) & _literal_assigned(x, l2) & _literal_assigned(x, l3)
        )
        any_sat = _literal_satisfied(x, l1) | _literal_satisfied(x, l2) | _literal_satisfied(x, l3)
        falsified = all_assigned & (~any_sat)
        with falsified:
            num_falsified += 1
    return num_falsified == 0


def is_marked(x):
    num_unassigned = ql.qint(0, width=2)
    for i in range(NUM_VARS):
        unassigned = x[i] == 2
        with unassigned:
            num_unassigned += 1

    num_unsat = ql.qint(0, width=2)
    for clause in CLAUSES:
        l1, l2, l3 = clause
        any_sat = _literal_satisfied(x, l1) | _literal_satisfied(x, l2) | _literal_satisfied(x, l3)
        with ~any_sat:
            num_unsat += 1

    return (num_unassigned == 0) & (num_unsat == 0)


# --- Assembly ---

ql.option("simulate", False)

x = ql.qarray([2] * NUM_VARS, width=VAR_WIDTH)

config, registers = ql.walk(
    is_marked,
    max_depth=NUM_VARS,
    num_moves=2,
    state=x,
    make_move=make_move,
    is_valid=is_valid,
)

from quantum_language.call_graph import (  # noqa: E402
    CallGraphDAG,
    pop_dag_context,
    push_dag_context,
)
from quantum_language.walk_operators import walk_step  # noqa: E402

dag = CallGraphDAG()
push_dag_context(dag)

walk_step(config, registers)

pop_dag_context()
dag.freeze()

print(dag.report())
print()
# with open("walk_call_graph.dot", "w") as f:
#     f.write(dag.to_dot())

import graphviz  # noqa: E402

dot_str = dag.to_dot()
src = graphviz.Source(dot_str)
src.render("call_graph", format="png", view=True)
print(f"DOT written to walk_call_graph.dot ({dag.node_count} nodes)")
