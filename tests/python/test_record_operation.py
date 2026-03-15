"""Tests for Module 7: Wire operations to call graph.

Validates record_operation() helper in call_graph.py and confirms that
Cython-level arithmetic, bitwise, and comparison operations record DAG
nodes during @ql.compile capture.
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    _dag_builder_stack,
    current_dag_context,
    pop_dag_context,
    push_dag_context,
    record_operation,
)


# ---------------------------------------------------------------------------
# record_operation() unit tests
# ---------------------------------------------------------------------------


class TestRecordOperation:
    """Tests for the record_operation() helper function."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_no_context_returns_none(self):
        result = record_operation("add_cq", (0, 1, 2))
        assert result is None

    def test_with_context_returns_node_index(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        result = record_operation("add_cq", (0, 1, 2, 3))
        assert result is not None
        assert isinstance(result, int)
        assert result == 0

    def test_records_operation_type(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("mul_qq", (0, 1, 2))
        node = dag.nodes[0]
        assert node.operation_type == "mul_qq"

    def test_records_qubit_mapping(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("xor", (5, 6, 7, 8))
        node = dag.nodes[0]
        assert node.qubit_mapping == (5, 6, 7, 8)

    def test_records_qubit_set(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("and", (3, 1, 4, 1, 5))
        node = dag.nodes[0]
        assert node.qubit_set == frozenset({1, 3, 4, 5})

    def test_records_sequence_ptr(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1), sequence_ptr=0xDEAD)
        node = dag.nodes[0]
        assert node.sequence_ptr == 0xDEAD

    def test_records_invert_true(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1), invert=True)
        node = dag.nodes[0]
        assert node.invert is True

    def test_records_invert_false_default(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1))
        node = dag.nodes[0]
        assert node.invert is False

    def test_execution_order_edge_created(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        i0 = record_operation("add_cq", (0, 1))
        i1 = record_operation("add_cq", (0, 1))
        edges = dag.execution_order_edges()
        assert (i0, i1) in edges

    def test_single_op_no_edge(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("xor", (0, 1))
        edges = dag.dag.edge_list()
        assert len(edges) == 0

    def test_multiple_operations_recorded(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1, 2, 3))
        record_operation("mul_cq", (4, 5, 6, 7))
        record_operation("xor", (0, 4))
        assert dag.node_count == 3
        assert dag.nodes[0].operation_type == "add_cq"
        assert dag.nodes[1].operation_type == "mul_cq"
        assert dag.nodes[2].operation_type == "xor"

    def test_func_name_matches_operation_type(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("eq_cq", (0, 1, 2))
        node = dag.nodes[0]
        assert node.func_name == "eq_cq"

    def test_gate_count_zero_for_primitive(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_qq", (0, 1, 2, 3))
        node = dag.nodes[0]
        assert node.gate_count == 0

    def test_list_qubit_indices_accepted(self):
        dag = CallGraphDAG()
        push_dag_context(dag)
        result = record_operation("add_cq", [0, 1, 2])
        assert result is not None
        node = dag.nodes[0]
        assert node.qubit_mapping == (0, 1, 2)


# ---------------------------------------------------------------------------
# Integration: operations recorded during @ql.compile capture
# ---------------------------------------------------------------------------


class TestCompileCaptureRecording:
    """Integration tests: Cython operations record DAG nodes during capture."""

    def test_addition_records_node(self):
        """In-place addition (+=) records a DAG node during compile capture."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        # Should have operation nodes (no wrapper node)
        assert dag.node_count >= 1
        # Check for add operation
        op_types = [n.operation_type for n in dag.nodes]
        assert any("add" in op for op in op_types), f"Expected add op, got {op_types}"

    def test_subtraction_records_node(self):
        """In-place subtraction (-=) records a DAG node during compile capture."""
        ql.circuit()

        @ql.compile(opt=1)
        def dec(x):
            x -= 1
            return x

        a = qint(5, width=4)
        dec(a)
        dag = dec.call_graph
        assert dag is not None
        op_types = [n.operation_type for n in dag.nodes]
        assert any("add" in op for op in op_types), f"Expected add op (sub uses invert), got {op_types}"

    def test_multiplication_records_node(self):
        """Multiplication records a DAG node when a DAG context is active."""
        # Note: *= inside @ql.compile triggers a pre-existing KeyError
        # (return value qubit mapping issue). Test via direct DAG context.
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a *= 2
        finally:
            pop_dag_context()
        op_types = [n.operation_type for n in dag.nodes]
        assert any("mul" in op for op in op_types), f"Expected mul op, got {op_types}"

    def test_xor_records_node(self):
        """In-place XOR (^=) records a DAG node during compile capture."""
        ql.circuit()

        @ql.compile(opt=1)
        def xor_op(x, y):
            x ^= y
            return x

        a = qint(3, width=4)
        b = qint(5, width=4)
        xor_op(a, b)
        dag = xor_op.call_graph
        assert dag is not None
        op_types = [n.operation_type for n in dag.nodes]
        assert any("xor" in op for op in op_types), f"Expected xor op, got {op_types}"

    def test_equality_records_node(self):
        """Equality comparison (==) records a DAG node during compile capture."""
        ql.circuit()

        @ql.compile(opt=1)
        def check_eq(x):
            result = (x == 5)
            return result

        a = qint(3, width=4)
        check_eq(a)
        dag = check_eq.call_graph
        assert dag is not None
        op_types = [n.operation_type for n in dag.nodes]
        assert any("eq" in op for op in op_types), f"Expected eq op, got {op_types}"

    def test_operation_has_qubit_mapping(self):
        """Recorded operations have non-empty qubit mappings."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        # Find operation nodes (not the top-level compile node)
        op_nodes = [n for n in dag.nodes if n.operation_type and n.operation_type != ""]
        assert len(op_nodes) > 0
        for node in op_nodes:
            assert len(node.qubit_mapping) > 0, (
                f"Operation {node.operation_type} has empty qubit_mapping"
            )

    def test_operations_are_direct_dag_nodes(self):
        """Recorded operations are direct DAG nodes with no wrapper."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        # All nodes should be operation nodes (no wrapper/placeholder)
        assert dag.node_count >= 1
        op_nodes = [n for n in dag.nodes if n.operation_type]
        assert len(op_nodes) == dag.node_count
        # No "call" edge type anywhere
        for eidx in dag.dag.edge_indices():
            edata = dag.dag.get_edge_data_by_index(eidx)
            assert edata.get("type") != "call"

    def test_subtraction_invert_flag(self):
        """In-place subtraction records with invert=True."""
        ql.circuit()

        @ql.compile(opt=1)
        def dec(x):
            x -= 1
            return x

        a = qint(5, width=4)
        dec(a)
        dag = dec.call_graph
        assert dag is not None
        # Find the add operation (subtraction is addition with invert=True)
        add_nodes = [n for n in dag.nodes if "add" in n.operation_type]
        assert len(add_nodes) > 0
        # At least one should have invert=True (the -= path)
        assert any(n.invert for n in add_nodes), (
            f"Expected invert=True on add node for subtraction, "
            f"got invert values: {[n.invert for n in add_nodes]}"
        )

    def test_no_recording_outside_compile(self):
        """Operations outside @ql.compile do NOT record DAG nodes."""
        ql.circuit()
        a = qint(3, width=4)
        b = qint(5, width=4)
        # These operations happen outside compile -- no DAG context
        c = a + b
        d = a & b
        # Verify no DAG context is active
        assert current_dag_context() is None

    def test_replay_does_not_double_record(self):
        """opt=1: replay does NOT record additional nodes (DAG frozen after capture)."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)  # Capture (records operation nodes)
        capture_count = inc.call_graph.node_count

        b = qint(5, width=4)
        inc(b)  # Replay (opt=1 skips DAG recording)
        replay_count = inc.call_graph.node_count

        # opt=1 does not grow the DAG on replay
        assert replay_count == capture_count

    def test_multiple_operations_in_one_compile(self):
        """Multiple operations in a single compiled function all get recorded."""
        ql.circuit()

        @ql.compile(opt=1)
        def multi_op(x, y):
            x += 1
            x += y
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        multi_op(a, b)
        dag = multi_op.call_graph
        assert dag is not None
        # Should have multiple operation nodes
        op_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        assert len(op_nodes) >= 2, f"Expected >=2 add ops, got {len(op_nodes)}"

    def test_and_operation_records_node(self):
        """Bitwise AND (&) records a DAG node during compile capture."""
        ql.circuit()

        @ql.compile(opt=1)
        def and_op(x, y):
            z = x & y
            return z

        a = qint(0b1100, width=4)
        b = qint(0b1010, width=4)
        and_op(a, b)
        dag = and_op.call_graph
        assert dag is not None
        op_types = [n.operation_type for n in dag.nodes]
        assert any("and" in op for op in op_types), f"Expected and op, got {op_types}"

    def test_or_operation_records_node(self):
        """Bitwise OR (|) records a DAG node during compile capture."""
        ql.circuit()

        @ql.compile(opt=1)
        def or_op(x, y):
            z = x | y
            return z

        a = qint(0b1100, width=4)
        b = qint(0b0011, width=4)
        or_op(a, b)
        dag = or_op.call_graph
        assert dag is not None
        op_types = [n.operation_type for n in dag.nodes]
        assert any("or" in op for op in op_types), f"Expected or op, got {op_types}"

    def test_not_operation_records_node(self):
        """Bitwise NOT (~) records a DAG node during compile capture."""
        ql.circuit()

        @ql.compile(opt=1)
        def not_op(x):
            ~x
            return x

        a = qint(0b1010, width=4)
        not_op(a)
        dag = not_op.call_graph
        assert dag is not None
        op_types = [n.operation_type for n in dag.nodes]
        assert any("not" in op for op in op_types), f"Expected not op, got {op_types}"

    def test_division_records_node(self):
        """Floor division records a DAG node when a DAG context is active."""
        # Note: //= inside @ql.compile triggers a pre-existing KeyError
        # (return value qubit mapping issue). Test via direct DAG context.
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(6, width=4)
            a //= 3
        finally:
            pop_dag_context()
        op_types = [n.operation_type for n in dag.nodes]
        assert any("div" in op for op in op_types), f"Expected divmod op, got {op_types}"


# ---------------------------------------------------------------------------
# Integration: recorded nodes have valid metadata
# ---------------------------------------------------------------------------


class TestRecordedNodeMetadata:
    """Tests that recorded operation nodes contain valid metadata."""

    def test_qubit_set_nonempty(self):
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        for node in dag.nodes:
            assert len(node.qubit_set) > 0

    def test_qubit_mapping_matches_qubit_set(self):
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        for node in dag.nodes:
            if node.operation_type and node.qubit_mapping:
                assert set(node.qubit_mapping).issubset(node.qubit_set)

    def test_bitmask_consistent_with_qubit_set(self):
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        for node in dag.nodes:
            expected_bitmask = 0
            for q in node.qubit_set:
                expected_bitmask |= 1 << q
            assert node.bitmask == expected_bitmask
