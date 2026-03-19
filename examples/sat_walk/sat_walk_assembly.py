"""Assemble the 3-SAT quantum walk from verified functions (10 vars, 20 clauses)."""

from sat_walk import NUM_VARS, VAR_WIDTH, is_marked, is_valid, make_move

import quantum_language as ql

ql.option("simulate", False)

# State: array of 10 ternary qints, all initialized to 2 (unassigned)
x = ql.qarray([2] * NUM_VARS, width=VAR_WIDTH)

# Build marked walk configuration and registers.
config, registers = ql.walk(
    is_marked,
    max_depth=NUM_VARS,
    num_moves=2,
    state=x,
    make_move=make_move,
    is_valid=is_valid,
)
# print(config)

# Apply walk steps (phase-estimation wrapper is a future milestone)
# from quantum_language.call_graph import CallGraphDAG, push_dag_context, pop_dag_context
# dag = CallGraphDAG()
# push_dag_context(dag)
from time import time  # noqa: E402

from quantum_language.walk_operators import walk_step  # noqa: E402

t1 = time()
walk_step(config, registers)

print(time() - t1)
# dag = make_move.call_graph
# dag_str = dag.to_dot()

# import graphviz
#
# dot_str = dag.to_dot()
# src = graphviz.Source(dot_str)
# src.render("call_graph", format = "png", view = True)

print(ql.get_gate_count())

# pop_dag_context()
# dag.freeze()

# print(dag.report())
# print()
# with open("walk_call_graph.dot", "w") as f:
#     f.write(dag.to_dot())
