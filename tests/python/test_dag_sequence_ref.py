"""Tests for Step 12.3: DAG node stores sequence reference.

Validates that DAGNode stores is_composite and op_params fields, and that
record_operation populates sequence_ptr for non-composite operations and
is_composite=True with op_params for Toffoli-mode composite operations.
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    DAGNode,
    _dag_builder_stack,
    pop_dag_context,
    push_dag_context,
    record_operation,
)

# ---------------------------------------------------------------------------
# DAGNode is_composite and op_params unit tests
# ---------------------------------------------------------------------------


class TestDAGNodeCompositeFields:
    """Tests for the is_composite and op_params DAGNode fields."""

    def test_default_is_composite_false(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.is_composite is False

    def test_default_op_params_empty(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.op_params == {}

    def test_stores_is_composite_true(self):
        node = DAGNode("f", {0, 1}, 10, (), is_composite=True)
        assert node.is_composite is True

    def test_stores_op_params(self):
        node = DAGNode("f", {0}, 5, (), op_params={"width": 4, "value": 5})
        assert node.op_params == {"width": 4, "value": 5}

    def test_composite_with_all_fields(self):
        node = DAGNode(
            "add_cq",
            {0, 1, 2, 3},
            20,
            (),
            sequence_ptr=0,
            qubit_mapping=(0, 1, 2, 3),
            operation_type="add_cq",
            invert=True,
            is_composite=True,
            op_params={"width": 4, "value": 1},
        )
        assert node.is_composite is True
        assert node.op_params == {"width": 4, "value": 1}
        assert node.sequence_ptr == 0
        assert node.invert is True
        assert node.operation_type == "add_cq"

    def test_non_composite_has_sequence_ptr(self):
        node = DAGNode(
            "add_cq",
            {0, 1},
            10,
            (),
            sequence_ptr=0xDEAD,
            is_composite=False,
        )
        assert node.is_composite is False
        assert node.sequence_ptr == 0xDEAD

    def test_repr_includes_composite_when_true(self):
        node = DAGNode("f", {0}, 1, (), is_composite=True)
        r = repr(node)
        assert "composite=True" in r

    def test_repr_omits_composite_when_false(self):
        node = DAGNode("f", {0}, 1, ())
        r = repr(node)
        assert "composite" not in r


# ---------------------------------------------------------------------------
# CallGraphDAG.add_node passthrough tests
# ---------------------------------------------------------------------------


class TestAddNodeCompositePassthrough:
    """Tests that add_node passes is_composite and op_params to DAGNode."""

    def test_add_node_passes_is_composite(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, (), is_composite=True)
        assert dag.nodes[0].is_composite is True

    def test_add_node_passes_op_params(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 5, (), op_params={"width": 4})
        assert dag.nodes[0].op_params == {"width": 4}

    def test_add_node_defaults(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 1, ())
        node = dag.nodes[0]
        assert node.is_composite is False
        assert node.op_params == {}


# ---------------------------------------------------------------------------
# record_operation composite support tests
# ---------------------------------------------------------------------------


class TestRecordOperationComposite:
    """Tests for record_operation with is_composite and op_params."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_record_composite_operation(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2, 3),
            gate_count=20,
            is_composite=True,
            op_params={"width": 4, "value": 1},
        )
        node = dag.nodes[0]
        assert node.is_composite is True
        assert node.op_params == {"width": 4, "value": 1}
        assert node.sequence_ptr == 0

    def test_record_non_composite_operation(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1),
            gate_count=10,
            sequence_ptr=0xBEEF,
        )
        node = dag.nodes[0]
        assert node.is_composite is False
        assert node.op_params == {}
        assert node.sequence_ptr == 0xBEEF

    def test_composite_default_false(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("xor", (0, 1))
        node = dag.nodes[0]
        assert node.is_composite is False

    def test_mixed_composite_and_non_composite(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2, 3),
            is_composite=True,
            op_params={"width": 4, "value": 1},
        )
        record_operation(
            "not",
            (4, 5),
            sequence_ptr=0xCAFE,
        )
        assert dag.nodes[0].is_composite is True
        assert dag.nodes[0].op_params == {"width": 4, "value": 1}
        assert dag.nodes[1].is_composite is False
        assert dag.nodes[1].sequence_ptr == 0xCAFE


# ---------------------------------------------------------------------------
# Integration: Toffoli-mode operations record composite=True
# ---------------------------------------------------------------------------


class TestToffoliCompositeIntegration:
    """Integration tests: Toffoli-mode operations record is_composite=True."""

    def test_toffoli_add_cq_is_composite(self):
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if "add" in n.operation_type]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.is_composite is True
            assert "width" in node.op_params or "self_width" in node.op_params

    def test_toffoli_add_qq_is_composite(self):
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile(opt=1)
        def add_fn(x, y):
            x += y
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        add_fn(a, b)
        dag = add_fn.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if "add" in n.operation_type]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.is_composite is True
            assert "self_width" in node.op_params

    def test_qft_add_cq_has_sequence_ptr(self):
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if "add" in n.operation_type]
        assert len(add_nodes) > 0
        for node in add_nodes:
            assert node.sequence_ptr != 0
            assert node.is_composite is False

    def test_not_is_not_composite(self):
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile(opt=1)
        def not_op(x):
            x = ~x
            return x

        a = qint(0b1010, width=4)
        not_op(a)
        dag = not_op.call_graph
        assert dag is not None
        not_nodes = [n for n in dag.nodes if "not" in n.operation_type]
        assert len(not_nodes) > 0
        for node in not_nodes:
            assert node.sequence_ptr != 0
            assert node.is_composite is False

    def test_division_is_composite(self):
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(6, width=4)
            a //= 3
        finally:
            pop_dag_context()
        div_nodes = [n for n in dag.nodes if "div" in n.operation_type]
        assert len(div_nodes) > 0
        for node in div_nodes:
            assert node.is_composite is True
            assert "width" in node.op_params

    def test_composite_nodes_have_qubit_mapping(self):
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        for node in dag.nodes:
            if node.is_composite:
                assert len(node.qubit_mapping) > 0
