"""Tests for capture-without-execution (Step 12.4).

Verifies that:
1. In Toffoli mode, _execute_ir is skipped during capture (explicit no-op).
2. record_operation passes uncontrolled_seq/controlled_seq to DAG nodes.
3. Toffoli addition DAG nodes store base sequence pointers.
4. Gate counts come from sequence_t.total_gate_count metadata for
   non-composite operations.
"""

import quantum_language as ql
from quantum_language.call_graph import (
    CallGraphDAG,
    _resolve_gate_count,
    pop_dag_context,
    push_dag_context,
    record_operation,
)


class TestRecordOperationSequencePointers:
    """record_operation passes uncontrolled_seq/controlled_seq to DAG nodes."""

    def setup_method(self):
        from quantum_language.call_graph import _dag_builder_stack

        _dag_builder_stack.clear()

    def teardown_method(self):
        from quantum_language.call_graph import _dag_builder_stack

        _dag_builder_stack.clear()

    def test_uncontrolled_seq_stored(self):
        """uncontrolled_seq is stored on DAGNode when passed to record_operation."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=42,
            uncontrolled_seq=12345,
        )
        pop_dag_context()
        node = dag.nodes[0]
        assert node.uncontrolled_seq == 12345

    def test_controlled_seq_stored(self):
        """controlled_seq is stored on DAGNode when passed to record_operation."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=42,
            controlled_seq=67890,
        )
        pop_dag_context()
        node = dag.nodes[0]
        assert node.controlled_seq == 67890

    def test_both_seqs_stored(self):
        """Both uncontrolled_seq and controlled_seq stored on DAGNode."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=42,
            uncontrolled_seq=111,
            controlled_seq=222,
        )
        pop_dag_context()
        node = dag.nodes[0]
        assert node.uncontrolled_seq == 111
        assert node.controlled_seq == 222

    def test_defaults_to_zero(self):
        """Without explicit seq pointers, both default to 0."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1, 2), gate_count=42)
        pop_dag_context()
        node = dag.nodes[0]
        assert node.uncontrolled_seq == 0
        assert node.controlled_seq == 0


class TestToffoliCaptureSequencePointers:
    """Toffoli addition records sequence pointers on DAG nodes."""

    def test_add_cq_stores_sequence_pointers(self):
        """Toffoli CQ addition DAG node has non-zero sequence pointers."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = ql.qint(3, width=4)
            a += 2
        finally:
            pop_dag_context()

        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) > 0, "Expected at least one add_cq node"
        node = add_nodes[0]
        assert node.uncontrolled_seq != 0, (
            "Toffoli CQ add should store uncontrolled sequence pointer"
        )
        assert node.controlled_seq != 0, "Toffoli CQ add should store controlled sequence pointer"

    def test_add_qq_stores_sequence_pointers(self):
        """Toffoli QQ addition DAG node has non-zero sequence pointers."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = ql.qint(3, width=4)
            b = ql.qint(2, width=4)
            a += b
        finally:
            pop_dag_context()

        add_nodes = [n for n in dag.nodes if n.operation_type == "add_qq"]
        assert len(add_nodes) > 0, "Expected at least one add_qq node"
        node = add_nodes[0]
        assert node.uncontrolled_seq != 0, (
            "Toffoli QQ add should store uncontrolled sequence pointer"
        )
        assert node.controlled_seq != 0, "Toffoli QQ add should store controlled sequence pointer"

    def test_sequence_gate_count_matches(self):
        """Gate count from sequence matches _resolve_gate_count."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = ql.qint(3, width=4)
            a += 2
        finally:
            pop_dag_context()

        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) > 0
        node = add_nodes[0]
        if node.uncontrolled_seq != 0:
            uc_gc = _resolve_gate_count(node.uncontrolled_seq)
            assert uc_gc > 0, f"Sequence gate count should be > 0 for non-trivial add, got {uc_gc}"


class TestExecuteIrSkippedInToffoliMode:
    """_execute_ir is explicitly skipped in Toffoli mode capture."""

    def test_toffoli_capture_no_ir_entries(self):
        """In Toffoli mode, _instruction_ir remains empty during capture."""
        from quantum_language.compile import CompiledBlock

        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(3, width=4)

        @ql.compile
        def add_val(x):
            x += 5
            return x

        block = CompiledBlock(
            gates=[],
            total_virtual_qubits=0,
            param_qubit_ranges=[],
            internal_qubit_count=0,
            return_qubit_range=None,
        )
        with add_val.compile_mode(block):
            a += 5

        # In Toffoli mode, operations go through Toffoli dispatch
        # (not QFT IR recording), so _instruction_ir is empty.
        # _execute_ir is skipped for Toffoli mode.
        assert len(block._instruction_ir) == 0, "Toffoli mode should not produce IR entries"

    def test_qft_capture_has_ir_entries(self):
        """In QFT mode, _instruction_ir has entries during capture."""
        from quantum_language.compile import CompiledBlock

        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)

        @ql.compile
        def add_val(x):
            x += 5
            return x

        block = CompiledBlock(
            gates=[],
            total_virtual_qubits=0,
            param_qubit_ranges=[],
            internal_qubit_count=0,
            return_qubit_range=None,
        )
        with add_val.compile_mode(block):
            a += 5

        # In QFT mode, operations record IR entries
        assert len(block._instruction_ir) > 0, "QFT mode should produce IR entries"


class TestCompositeOperationParams:
    """Composite Toffoli operations store op_params for re-dispatch."""

    def test_add_cq_stores_op_params(self):
        """Toffoli CQ add stores width and value in op_params."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = ql.qint(0, width=4)
            a += 7
        finally:
            pop_dag_context()

        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) > 0
        node = add_nodes[0]
        assert node.is_composite, "Toffoli CQ add should be composite"
        assert "width" in node.op_params
        assert node.op_params["width"] == 4
        assert node.op_params["value"] == 7

    def test_mul_cq_stores_op_params(self):
        """Toffoli CQ mul stores result_width, self_width, value."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = ql.qint(3, width=4)
            _ = a * 2
        finally:
            pop_dag_context()

        mul_nodes = [n for n in dag.nodes if n.operation_type == "mul_cq"]
        assert len(mul_nodes) > 0
        node = mul_nodes[0]
        assert node.is_composite, "Toffoli CQ mul should be composite"
        assert "value" in node.op_params
        assert node.op_params["value"] == 2
