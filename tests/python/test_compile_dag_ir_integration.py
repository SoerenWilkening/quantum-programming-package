"""Tests for opt=1 DAG integration with compile pipeline (instruction IR).

Issue: Quantum_Assembly-4qk
Spec: R16.8

Tests that:
1. DAG nodes built from instruction IR have correct controlled metadata.
2. Instruction IR integrates with DAG building (nodes appear in DAG).
3. opt=1 with simulate=False still records IR without emitting gates.
"""

import gc

import quantum_language as ql
from quantum_language._compile_state import InstructionRecord
from quantum_language.call_graph import (
    CallGraphDAG,
    _dag_builder_stack,
    push_dag_context,
)
from quantum_language.compile import CompiledBlock, _build_dag_from_ir


def _make_block_with_ir(entries):
    """Create a CompiledBlock with pre-populated IR entries."""
    block = CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )
    block._instruction_ir = list(entries)
    return block


# ---------------------------------------------------------------------------
# Unit tests: _build_dag_from_ir
# ---------------------------------------------------------------------------


class TestBuildDagFromIR:
    """Unit tests for _build_dag_from_ir function."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_no_dag_context_returns_zero(self):
        """Without a DAG context, _build_dag_from_ir returns 0."""
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1, 2), 0xCAFE, 0xBEEF),
            ]
        )
        count = _build_dag_from_ir(block, "test_fn")
        assert count == 0

    def test_empty_ir_returns_zero(self):
        """Empty IR produces no DAG nodes."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir([])
        count = _build_dag_from_ir(block, "test_fn")
        assert count == 0
        assert dag.node_count == 0

    def test_single_ir_entry_creates_one_node(self):
        """One IR entry produces one DAG node."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1, 2), 0xCAFE, 0xBEEF),
            ]
        )
        count = _build_dag_from_ir(block, "test_fn")
        assert count == 1
        assert dag.node_count == 1

    def test_multiple_ir_entries_create_multiple_nodes(self):
        """Multiple IR entries produce corresponding DAG nodes."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x1, 0x2),
                InstructionRecord("mul_cq", (2, 3), 0x3, 0x4),
                InstructionRecord("eq_cq", (0, 1, 2, 3), 0x5, 0x6),
            ]
        )
        count = _build_dag_from_ir(block, "test_fn")
        assert count == 3
        assert dag.node_count == 3

    def test_node_has_correct_operation_type(self):
        """DAG node operation_type matches IR entry name."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1, 2), 0xCAFE, 0),
            ]
        )
        _build_dag_from_ir(block, "test_fn")
        node = dag.nodes[0]
        assert node.operation_type == "add_cq"

    def test_node_has_correct_qubit_set(self):
        """DAG node qubit_set matches IR entry registers."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (5, 6, 7), 0x1, 0),
            ]
        )
        _build_dag_from_ir(block, "test_fn")
        node = dag.nodes[0]
        assert node.qubit_set == frozenset({5, 6, 7})

    def test_node_has_invert_flag(self):
        """DAG node invert matches IR entry invert."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x1, 0, invert=True),
            ]
        )
        _build_dag_from_ir(block, "test_fn")
        node = dag.nodes[0]
        assert node.invert is True

    def test_node_controlled_false_by_default(self):
        """DAG node controlled=False when not specified."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x1, 0),
            ]
        )
        _build_dag_from_ir(block, "test_fn")
        node = dag.nodes[0]
        assert node.controlled is False

    def test_node_controlled_true_when_specified(self):
        """DAG node controlled=True when is_controlled=True."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x1, 0x2),
            ]
        )
        _build_dag_from_ir(block, "test_fn", is_controlled=True)
        node = dag.nodes[0]
        assert node.controlled is True

    def test_controlled_selects_controlled_seq(self):
        """When is_controlled=True, sequence_ptr uses controlled_seq."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0xAAAA, 0xBBBB),
            ]
        )
        _build_dag_from_ir(block, "test_fn", is_controlled=True)
        node = dag.nodes[0]
        assert node.sequence_ptr == 0xBBBB

    def test_uncontrolled_selects_uncontrolled_seq(self):
        """When is_controlled=False, sequence_ptr uses uncontrolled_seq."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0xAAAA, 0xBBBB),
            ]
        )
        _build_dag_from_ir(block, "test_fn", is_controlled=False)
        node = dag.nodes[0]
        assert node.sequence_ptr == 0xAAAA

    def test_qubit_mapping_remaps_registers(self):
        """qubit_mapping remaps IR entry registers in DAG nodes."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1, 2), 0x1, 0),
            ]
        )
        mapping = {0: 10, 1: 11, 2: 12}
        _build_dag_from_ir(block, "test_fn", qubit_mapping=mapping)
        node = dag.nodes[0]
        assert node.qubit_set == frozenset({10, 11, 12})
        assert node.qubit_mapping == (10, 11, 12)

    def test_execution_order_edges_for_shared_qubits(self):
        """DAG nodes sharing qubits get execution-order edges."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x1, 0),
                InstructionRecord("mul_cq", (1, 2), 0x2, 0),
            ]
        )
        _build_dag_from_ir(block, "test_fn")
        edges = dag.execution_order_edges()
        assert (0, 1) in edges


# ---------------------------------------------------------------------------
# Integration: opt=1 DAG from IR during capture
# ---------------------------------------------------------------------------


class TestOpt1CaptureBuildsDAGFromIR:
    """opt=1 capture builds DAG nodes from instruction IR."""

    def test_opt1_capture_produces_ir_dag_nodes_qft(self):
        """opt=1 capture in QFT mode produces DAG nodes from IR entries."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        dag = inc.call_graph
        assert dag is not None
        # IR-based nodes should be present
        ir_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(ir_nodes) > 0, "Expected IR-based add_cq nodes in DAG"

    def test_opt1_capture_controlled_marks_ir_nodes(self):
        """opt=1 capture inside with-block marks IR DAG nodes as controlled."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        c = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c:
            inc(a)

        dag = inc.call_graph
        assert dag is not None
        ir_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(ir_nodes) > 0
        for node in ir_nodes:
            assert node.controlled is True, (
                f"IR DAG node should be marked controlled, got {node.controlled}"
            )


# ---------------------------------------------------------------------------
# Integration: opt=1 replay builds DAG from IR
# ---------------------------------------------------------------------------


class TestOpt1ReplayBuildsDAGFromIR:
    """opt=1 replay (cache hit) builds DAG nodes from instruction IR."""

    def test_opt1_replay_produces_ir_dag_nodes(self):
        """opt=1 replay adds DAG nodes from IR for each call."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # capture
        nodes_after_capture = inc.call_graph.node_count

        b = ql.qint(0, width=4)
        inc(b)  # replay

        dag = inc.call_graph
        assert dag is not None
        assert dag.node_count > nodes_after_capture, (
            f"Replay should add nodes to DAG: had {nodes_after_capture}, now {dag.node_count}"
        )

    def test_opt1_replay_controlled_marks_nodes(self):
        """opt=1 replay inside with-block marks DAG nodes as controlled."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=2)
        inc(a)  # capture (uncontrolled)

        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        nodes_before = inc.call_graph.node_count
        with c:
            inc(b)  # replay (controlled)

        dag = inc.call_graph
        # New nodes added by replay
        new_nodes = dag.nodes[nodes_before:]
        assert len(new_nodes) > 0
        for node in new_nodes:
            assert node.controlled is True

    def test_opt1_three_calls_grows_dag(self):
        """opt=1 with 3 calls produces growing DAG."""
        gc.collect()
        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        counts = []
        for _ in range(3):
            x = ql.qint(0, width=4)
            inc(x)
            counts.append(inc.call_graph.node_count)

        # Each call should add at least one node
        assert counts[1] > counts[0], f"2nd call should add nodes: {counts}"
        assert counts[2] > counts[1], f"3rd call should add nodes: {counts}"


# ---------------------------------------------------------------------------
# Integration: opt=1 with simulate=False records IR without emitting
# ---------------------------------------------------------------------------


class TestOpt1SimulateFalseRecordsIR:
    """opt=1 with simulate=False records IR and builds DAG without gates."""

    def test_opt1_simulate_false_records_ir(self):
        """opt=1 with simulate=False records IR entries on the cached block."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        block = list(inc._cache.values())[0]
        assert len(block._instruction_ir) > 0, "IR should be recorded even with simulate=False"

    def test_opt1_simulate_false_builds_dag(self):
        """opt=1 with simulate=False builds DAG from IR."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        dag = inc.call_graph
        assert dag is not None
        assert dag.node_count > 0, "DAG should have nodes even with simulate=False"

    def test_opt1_simulate_false_replay_builds_dag(self):
        """opt=1 replay with simulate=False adds DAG nodes from IR."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)
        nodes_after_capture = inc.call_graph.node_count

        b = ql.qint(0, width=4)
        inc(b)

        dag = inc.call_graph
        assert dag.node_count > nodes_after_capture, (
            f"Replay should add nodes: had {nodes_after_capture}, now {dag.node_count}"
        )

    def test_opt1_simulate_false_no_gates_emitted(self):
        """opt=1 with simulate=False does not emit gates to the circuit."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        ql.option("fault_tolerant", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        from quantum_language._core import get_current_layer

        layer_before = get_current_layer()
        a = ql.qint(0, width=4)
        inc(a)
        layer_after = get_current_layer()

        # No gates should be injected into the circuit
        assert layer_after == layer_before, (
            f"simulate=False should not inject gates: "
            f"layers went from {layer_before} to {layer_after}"
        )

    def test_opt1_simulate_false_controlled_records_ir(self):
        """opt=1 with simulate=False inside with-block still records IR."""
        gc.collect()
        ql.circuit()
        ql.option("simulate", False)
        ql.option("fault_tolerant", False)  # QFT mode

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        c = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c:
            inc(a)

        block = list(inc._cache.values())[0]
        assert len(block._instruction_ir) > 0
        assert block._captured_controlled is True

        dag = inc.call_graph
        assert dag is not None
        ir_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(ir_nodes) > 0
        for node in ir_nodes:
            assert node.controlled is True


# ---------------------------------------------------------------------------
# DAGNode controlled metadata
# ---------------------------------------------------------------------------


class TestDAGNodeControlledMetadata:
    """Verify DAGNode.controlled attribute on IR-built nodes."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_all_nodes_have_controlled_attribute(self):
        """Every DAG node from _build_dag_from_ir has a controlled attribute."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x1, 0x2),
                InstructionRecord("mul_cq", (2, 3), 0x3, 0x4),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=False)
        _build_dag_from_ir(block, "fn", is_controlled=True)
        for node in dag.nodes:
            assert hasattr(node, "controlled")

    def test_mixed_controlled_uncontrolled(self):
        """Building DAG from IR with mixed control contexts works."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block_uc = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x1, 0),
            ]
        )
        block_c = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (2, 3), 0x2, 0x3),
            ]
        )
        _build_dag_from_ir(block_uc, "fn", is_controlled=False)
        _build_dag_from_ir(block_c, "fn", is_controlled=True)

        assert dag.nodes[0].controlled is False
        assert dag.nodes[1].controlled is True
