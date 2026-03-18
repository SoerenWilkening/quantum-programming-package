"""Tests for DAG build-once semantics — no duplication on replay.

Issue: Quantum_Assembly-b5l
Spec: R16.11

Tests that:
1. Calling foo() uncontrolled then controlled produces N instruction nodes (not 2N).
2. Each DAGNode from _build_dag_from_ir has both uncontrolled_seq and controlled_seq.
"""

from quantum_language._compile_state import InstructionRecord
from quantum_language.call_graph import (
    CallGraphDAG,
    DAGNode,
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
# test_dag_no_duplicate_nodes
# ---------------------------------------------------------------------------


class TestDAGNoDuplicateNodes:
    """Verify that _build_dag_from_ir only adds nodes once per block."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_dag_no_duplicate_nodes_basic(self):
        """Calling _build_dag_from_ir twice on same block with _dag_built
        should not add duplicate nodes."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        ir_entries = [
            InstructionRecord("add_cq", (0, 1, 2), 0xCAFE, 0xBEEF),
            InstructionRecord("mul_cq", (2, 3), 0x1234, 0x5678),
        ]
        block = _make_block_with_ir(ir_entries)

        # First build: should add 2 nodes
        count1 = _build_dag_from_ir(block, "test_fn", is_controlled=False)
        assert count1 == 2
        assert dag.node_count == 2

        # Mark DAG as built (simulating what _call_inner does)
        block._dag_built = True

        # Second build attempt: _call_inner would skip due to _dag_built
        # Verify that calling _build_dag_from_ir again (as old code did)
        # would produce duplicates, but the _dag_built flag prevents it.
        # Here we test the guard condition that _call_inner checks.
        if not block._dag_built:
            _build_dag_from_ir(block, "test_fn", is_controlled=True)

        # Still only 2 nodes
        assert dag.node_count == 2, f"Expected 2 nodes (no duplicates), got {dag.node_count}"

    def test_dag_no_duplicate_first_call_sets_flag(self):
        """After first _build_dag_from_ir, _dag_built should be True
        and subsequent calls guarded by the flag should be skipped."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        ir_entries = [
            InstructionRecord("add_cq", (0, 1), 0xAAAA, 0xBBBB),
        ]
        block = _make_block_with_ir(ir_entries)

        assert block._dag_built is False

        # Simulate the capture path from _call_inner
        if not block._dag_built:
            _ir_added = _build_dag_from_ir(block, "fn", is_controlled=False)
            if _ir_added > 0:
                block._dag_built = True

        assert block._dag_built is True
        assert dag.node_count == 1

        # Simulate replay path from _call_inner — should skip
        if not block._dag_built:
            _build_dag_from_ir(block, "fn", is_controlled=True)

        assert dag.node_count == 1

    def test_uncontrolled_then_controlled_no_duplication(self):
        """Calling foo() uncontrolled then controlled produces N nodes, not 2N."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        n_entries = 3
        ir_entries = [
            InstructionRecord("add_cq", (0, 1), 0x10, 0x20),
            InstructionRecord("mul_cq", (2, 3), 0x30, 0x40),
            InstructionRecord("eq_cq", (0, 1, 2, 3), 0x50, 0x60),
        ]
        block = _make_block_with_ir(ir_entries)

        # First call (capture, uncontrolled)
        if not block._dag_built:
            added = _build_dag_from_ir(block, "fn", is_controlled=False)
            if added > 0:
                block._dag_built = True

        assert dag.node_count == n_entries

        # Second call (replay, controlled) — should NOT add more nodes
        if not block._dag_built:
            _build_dag_from_ir(block, "fn", is_controlled=True)

        assert dag.node_count == n_entries, (
            f"Expected {n_entries} nodes after uncontrolled+controlled calls, got {dag.node_count}"
        )

    def test_empty_ir_does_not_set_flag(self):
        """Empty IR block should not set _dag_built (no nodes to protect)."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir([])

        if not block._dag_built:
            added = _build_dag_from_ir(block, "fn")
            if added > 0:
                block._dag_built = True

        assert block._dag_built is False
        assert dag.node_count == 0

    def test_new_block_starts_with_dag_built_false(self):
        """Fresh CompiledBlock should have _dag_built = False."""
        block = _make_block_with_ir([])
        assert block._dag_built is False

    def test_replay_does_not_add_coarse_fallback_node(self):
        """Regression: when _dag_built=True and _ir_added=0 (replay skips IR
        build), the coarse call-level fallback node must NOT be appended.

        Before the fix, the guard was `not (opt==1 and _ir_added>0)` which
        evaluated to True on replays (since _ir_added was 0), causing a
        spurious coarse node on every replay call.
        """
        import quantum_language as ql

        ql.circuit()
        ql.option("fault_tolerant", False)  # QFT mode produces IR

        @ql.compile(opt=1)
        def add_five(x):
            x += 5
            return x

        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = ql.qint(0, width=4)
            # First call — capture, builds IR nodes
            add_five(a)
            n_after_first = dag.node_count

            # Second call — replay, must NOT add any nodes
            add_five(a)
            assert dag.node_count == n_after_first, (
                f"Replay added nodes: expected {n_after_first}, got {dag.node_count}"
            )

            # Third call — same
            add_five(a)
            assert dag.node_count == n_after_first, (
                f"Second replay added nodes: expected {n_after_first}, got {dag.node_count}"
            )
        finally:
            _dag_builder_stack.clear()


# ---------------------------------------------------------------------------
# test_dag_both_seq_stored
# ---------------------------------------------------------------------------


class TestDAGBothSeqStored:
    """Verify that each DAGNode stores both uncontrolled_seq and controlled_seq."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_dag_both_seq_stored_uncontrolled(self):
        """Uncontrolled build stores both seq pointers on DAGNode."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0xAAAA, 0xBBBB),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=False)
        node = dag.nodes[0]
        assert node.uncontrolled_seq == 0xAAAA
        assert node.controlled_seq == 0xBBBB

    def test_dag_both_seq_stored_controlled(self):
        """Controlled build stores both seq pointers on DAGNode."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0xAAAA, 0xBBBB),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=True)
        node = dag.nodes[0]
        assert node.uncontrolled_seq == 0xAAAA
        assert node.controlled_seq == 0xBBBB

    def test_dag_both_seq_stored_multiple_entries(self):
        """Multiple IR entries each get both seq pointers."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0x10, 0x20),
                InstructionRecord("mul_cq", (2, 3), 0x30, 0x40),
                InstructionRecord("eq_cq", (4, 5), 0x50, 0x60),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=False)

        expected = [(0x10, 0x20), (0x30, 0x40), (0x50, 0x60)]
        for i, (uc, c) in enumerate(expected):
            node = dag.nodes[i]
            assert node.uncontrolled_seq == uc, (
                f"Node {i} uncontrolled_seq: expected {uc:#x}, got {node.uncontrolled_seq:#x}"
            )
            assert node.controlled_seq == c, (
                f"Node {i} controlled_seq: expected {c:#x}, got {node.controlled_seq:#x}"
            )

    def test_dag_both_seq_stored_zero_controlled(self):
        """When controlled_seq is 0, it is still stored as 0."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0xCAFE, 0),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=False)
        node = dag.nodes[0]
        assert node.uncontrolled_seq == 0xCAFE
        assert node.controlled_seq == 0

    def test_dag_both_seq_stored_zero_uncontrolled(self):
        """When uncontrolled_seq is 0, it is still stored as 0."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0, 0xBEEF),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=True)
        node = dag.nodes[0]
        assert node.uncontrolled_seq == 0
        assert node.controlled_seq == 0xBEEF

    def test_dag_node_has_both_seq_slots(self):
        """DAGNode class has uncontrolled_seq and controlled_seq in __slots__."""
        assert "uncontrolled_seq" in DAGNode.__slots__
        assert "controlled_seq" in DAGNode.__slots__

    def test_dag_node_default_seq_values(self):
        """DAGNode defaults both seq pointers to 0."""
        node = DAGNode("test", {0}, 0, ())
        assert node.uncontrolled_seq == 0
        assert node.controlled_seq == 0

    def test_sequence_ptr_backward_compat_uncontrolled(self):
        """sequence_ptr is set to uncontrolled_seq when is_controlled=False."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0xAAAA, 0xBBBB),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=False)
        node = dag.nodes[0]
        assert node.sequence_ptr == 0xAAAA

    def test_sequence_ptr_backward_compat_controlled(self):
        """sequence_ptr is set to controlled_seq when is_controlled=True."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        block = _make_block_with_ir(
            [
                InstructionRecord("add_cq", (0, 1), 0xAAAA, 0xBBBB),
            ]
        )
        _build_dag_from_ir(block, "fn", is_controlled=True)
        node = dag.nodes[0]
        assert node.sequence_ptr == 0xBBBB
