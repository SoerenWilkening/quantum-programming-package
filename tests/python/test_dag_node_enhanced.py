"""Tests for enhanced DAGNode with sequence metadata fields.

Validates the new sequence_ptr, qubit_mapping, operation_type, and invert
fields added to DAGNode and CallGraphDAG.add_node() (Module 6).
"""

from quantum_language.call_graph import CallGraphDAG, DAGNode


# ---------------------------------------------------------------------------
# DAGNode direct construction tests
# ---------------------------------------------------------------------------


class TestDAGNodeSequenceMetadata:
    """Tests for the four new DAGNode fields."""

    def test_stores_sequence_ptr(self):
        node = DAGNode("f", {0, 1}, 10, (), sequence_ptr=0xDEADBEEF)
        assert node.sequence_ptr == 0xDEADBEEF

    def test_stores_qubit_mapping(self):
        node = DAGNode("f", {0, 1, 2, 3}, 10, (), qubit_mapping=(0, 1, 2, 3))
        assert node.qubit_mapping == (0, 1, 2, 3)

    def test_stores_operation_type(self):
        node = DAGNode("f", {0}, 5, (), operation_type="add")
        assert node.operation_type == "add"

    def test_stores_invert_true(self):
        node = DAGNode("f", {0}, 5, (), invert=True)
        assert node.invert is True

    def test_stores_invert_false(self):
        node = DAGNode("f", {0}, 5, (), invert=False)
        assert node.invert is False

    def test_defaults_sequence_ptr_zero(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.sequence_ptr == 0

    def test_defaults_qubit_mapping_empty(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.qubit_mapping == ()

    def test_defaults_operation_type_empty(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.operation_type == ""

    def test_defaults_invert_false(self):
        node = DAGNode("f", {0}, 1, ())
        assert node.invert is False

    def test_all_four_fields_together(self):
        node = DAGNode(
            "sub_op", {2, 3, 4}, 50, ("k",),
            sequence_ptr=12345,
            qubit_mapping=(2, 3, 4),
            operation_type="mul",
            invert=True,
        )
        assert node.sequence_ptr == 12345
        assert node.qubit_mapping == (2, 3, 4)
        assert node.operation_type == "mul"
        assert node.invert is True

    def test_existing_fields_unaffected(self):
        """New fields do not break existing metadata storage."""
        node = DAGNode(
            "my_func", {0, 1, 2}, 42, ("key", 3),
            depth=5, t_count=14,
            sequence_ptr=99, qubit_mapping=(0, 1, 2),
            operation_type="xor", invert=False,
        )
        assert node.func_name == "my_func"
        assert node.qubit_set == frozenset({0, 1, 2})
        assert node.gate_count == 42
        assert node.cache_key == ("key", 3)
        assert node.depth == 5
        assert node.t_count == 14
        assert node.bitmask == 0b111


# ---------------------------------------------------------------------------
# DAGNode __repr__ tests
# ---------------------------------------------------------------------------


class TestDAGNodeRepr:
    """Tests for enhanced __repr__ output."""

    def test_repr_includes_operation_type(self):
        node = DAGNode("f", {0}, 1, (), operation_type="add")
        r = repr(node)
        assert "add" in r

    def test_repr_includes_invert_when_true(self):
        node = DAGNode("f", {0}, 1, (), invert=True)
        r = repr(node)
        assert "invert=True" in r

    def test_repr_omits_operation_type_when_empty(self):
        node = DAGNode("f", {0}, 1, ())
        r = repr(node)
        assert "op=" not in r

    def test_repr_omits_invert_when_false(self):
        node = DAGNode("f", {0}, 1, ())
        r = repr(node)
        assert "invert" not in r

    def test_repr_with_both_op_and_invert(self):
        node = DAGNode("f", {0}, 1, (), operation_type="sub", invert=True)
        r = repr(node)
        assert "sub" in r
        assert "invert=True" in r


# ---------------------------------------------------------------------------
# CallGraphDAG.add_node() passthrough tests
# ---------------------------------------------------------------------------


class TestAddNodePassthrough:
    """Tests that add_node() passes new parameters to DAGNode."""

    def test_add_node_passes_sequence_ptr(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, (), sequence_ptr=42)
        assert dag.nodes[0].sequence_ptr == 42

    def test_add_node_passes_qubit_mapping(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 10, (), qubit_mapping=(0, 1))
        assert dag.nodes[0].qubit_mapping == (0, 1)

    def test_add_node_passes_operation_type(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 5, (), operation_type="eq")
        assert dag.nodes[0].operation_type == "eq"

    def test_add_node_passes_invert(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 5, (), invert=True)
        assert dag.nodes[0].invert is True

    def test_add_node_defaults(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0}, 1, ())
        node = dag.nodes[0]
        assert node.sequence_ptr == 0
        assert node.qubit_mapping == ()
        assert node.operation_type == ""
        assert node.invert is False

    def test_add_node_all_metadata(self):
        dag = CallGraphDAG()
        dag.add_node(
            "op", {0, 1, 2}, 100, ("ck",),
            depth=10, t_count=7,
            sequence_ptr=0xCAFE, qubit_mapping=(0, 1, 2),
            operation_type="lt", invert=False,
        )
        node = dag.nodes[0]
        assert node.sequence_ptr == 0xCAFE
        assert node.qubit_mapping == (0, 1, 2)
        assert node.operation_type == "lt"
        assert node.invert is False
        assert node.depth == 10
        assert node.t_count == 7

    def test_add_node_with_metadata(self):
        dag = CallGraphDAG()
        dag.add_node("op1", {0, 1, 2}, 20, ())
        c = dag.add_node(
            "op2", {0, 1}, 5, (),
            sequence_ptr=999, qubit_mapping=(0, 1),
            operation_type="xor", invert=True,
        )
        child_node = dag.nodes[c]
        assert child_node.sequence_ptr == 999
        assert child_node.operation_type == "xor"
        assert child_node.invert is True
        # Execution-order edge from shared qubits
        edges = dag.execution_order_edges()
        assert (0, c) in edges
