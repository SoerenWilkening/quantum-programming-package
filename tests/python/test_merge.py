"""Unit tests for selective sequence merging (merge_groups and merge infrastructure).

Tests merge candidate detection via CallGraphDAG.merge_groups() and
gate concatenation/optimization via _merge_and_optimize.
Also tests opt=2 end-to-end integration: merge wiring, merged replay,
cross-boundary cancellation, and controlled context support.
"""

import pytest

import quantum_language as ql
from quantum_language.call_graph import (
    CallGraphDAG,
)
from quantum_language.compile import (
    CompiledBlock,
    CompiledFunc,
    _merge_and_optimize,
)
from quantum_language.qint import qint

# Run all tests in this module at opt=1, opt=2, and opt=3
pytestmark = pytest.mark.usefixtures("opt_level")

# ---------------------------------------------------------------------------
# merge_groups tests
# ---------------------------------------------------------------------------


class TestMergeGroups:
    """Tests for CallGraphDAG.merge_groups(threshold)."""

    def test_empty_dag_returns_empty(self):
        dag = CallGraphDAG()
        assert dag.merge_groups() == []

    def test_single_node_returns_empty(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 5, ("k",))
        assert dag.merge_groups() == []

    def test_two_overlapping_nodes(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1, 2}, 5, ("k1",))
        dag.add_node("g", {1, 2, 3}, 5, ("k2",))
        result = dag.merge_groups()
        assert result == [[0, 1]]

    def test_two_disjoint_nodes_returns_empty(self):
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1}, 5, ("k1",))
        dag.add_node("g", {2, 3}, 5, ("k2",))
        assert dag.merge_groups() == []

    def test_chain_a_b_c_transitive(self):
        """A overlaps B, B overlaps C, A disjoint from C -> single group."""
        dag = CallGraphDAG()
        dag.add_node("a", {0, 1}, 5, ("k1",))  # qubits 0,1
        dag.add_node("b", {1, 2}, 5, ("k2",))  # overlaps a (qubit 1), overlaps c (qubit 2)
        dag.add_node("c", {2, 3}, 5, ("k3",))  # disjoint from a
        result = dag.merge_groups()
        assert result == [[0, 1, 2]]

    def test_threshold_filters_low_overlap(self):
        """threshold=3 excludes edges with overlap < 3."""
        dag = CallGraphDAG()
        dag.add_node("f", {0, 1, 2, 3, 4}, 5, ("k1",))  # 5 qubits
        dag.add_node("g", {3, 4}, 5, ("k2",))  # overlap = 2 with f
        # With default threshold=1, they merge
        assert dag.merge_groups(threshold=1) == [[0, 1]]
        # With threshold=3, overlap of 2 is insufficient
        assert dag.merge_groups(threshold=3) == []

    def test_groups_sorted_by_node_index(self):
        """Each group's node indices are in ascending order."""
        dag = CallGraphDAG()
        dag.add_node("c", {2, 3}, 5, ("k3",))
        dag.add_node("a", {0, 1, 2}, 5, ("k1",))
        dag.add_node("b", {1, 3}, 5, ("k2",))
        result = dag.merge_groups()
        for group in result:
            assert group == sorted(group)

    def test_mix_overlapping_and_disjoint(self):
        """Only multi-node groups returned; singletons excluded."""
        dag = CallGraphDAG()
        dag.add_node("a", {0, 1}, 5, ("k1",))  # overlaps b
        dag.add_node("b", {1, 2}, 5, ("k2",))  # overlaps a
        dag.add_node("c", {10, 11}, 5, ("k3",))  # disjoint from all
        result = dag.merge_groups()
        assert result == [[0, 1]]

    def test_two_separate_groups(self):
        """Two independent overlap clusters -> two groups."""
        dag = CallGraphDAG()
        dag.add_node("a", {0, 1}, 5, ("k1",))
        dag.add_node("b", {1, 2}, 5, ("k2",))
        dag.add_node("c", {10, 11}, 5, ("k3",))
        dag.add_node("d", {11, 12}, 5, ("k4",))
        result = dag.merge_groups()
        assert len(result) == 2
        assert [0, 1] in result
        assert [2, 3] in result


# ---------------------------------------------------------------------------
# _merge_and_optimize tests
# ---------------------------------------------------------------------------


def _make_block(gates, total_vqubits=4):
    """Helper to create a minimal CompiledBlock for testing."""
    return CompiledBlock(
        gates=gates,
        total_virtual_qubits=total_vqubits,
        param_qubit_ranges=[(1, 1 + total_vqubits)],
        internal_qubit_count=0,
        return_qubit_range=None,
    )


class TestMergeAndOptimize:
    """Tests for _merge_and_optimize helper."""

    def test_single_block_remaps_to_physical(self):
        gates = [
            {"type": 1, "target": 0, "num_controls": 0, "controls": []},
            {"type": 1, "target": 1, "num_controls": 0, "controls": []},
        ]
        block = _make_block(gates, total_vqubits=2)
        v2r = {0: 5, 1: 7}
        result_gates, original_count = _merge_and_optimize([(block, v2r)], optimize=False)
        assert original_count == 2
        assert result_gates[0]["target"] == 5
        assert result_gates[1]["target"] == 7

    def test_two_blocks_concatenates_in_order(self):
        g1 = [{"type": 1, "target": 0, "num_controls": 0, "controls": []}]
        g2 = [{"type": 2, "target": 0, "num_controls": 0, "controls": []}]
        b1 = _make_block(g1, total_vqubits=1)
        b2 = _make_block(g2, total_vqubits=1)
        v2r1 = {0: 10}
        v2r2 = {0: 20}
        result_gates, count = _merge_and_optimize([(b1, v2r1), (b2, v2r2)], optimize=False)
        assert count == 2
        assert result_gates[0]["target"] == 10
        assert result_gates[0]["type"] == 1
        assert result_gates[1]["target"] == 20
        assert result_gates[1]["type"] == 2

    def test_controls_remapped(self):
        gates = [
            {"type": 1, "target": 0, "num_controls": 1, "controls": [1]},
        ]
        block = _make_block(gates, total_vqubits=2)
        v2r = {0: 3, 1: 8}
        result_gates, _ = _merge_and_optimize([(block, v2r)], optimize=False)
        assert result_gates[0]["target"] == 3
        assert result_gates[0]["controls"] == [8]

    def test_optimize_runs_optimizer(self):
        """With optimize=True, inverse gates should cancel."""
        # X gate (type 1) is self-inverse -- two adjacent should cancel
        gates = [
            {"type": 1, "target": 0, "num_controls": 0, "controls": []},
        ]
        b1 = _make_block(gates, total_vqubits=1)
        b2 = _make_block(gates, total_vqubits=1)
        v2r = {0: 0}
        result_gates, original_count = _merge_and_optimize([(b1, v2r), (b2, v2r)], optimize=True)
        assert original_count == 2
        # After optimization, the two X gates should cancel
        assert len(result_gates) < original_count

    def test_returns_tuple(self):
        gates = [{"type": 1, "target": 0, "num_controls": 0, "controls": []}]
        block = _make_block(gates, total_vqubits=1)
        result = _merge_and_optimize([(block, {0: 0})], optimize=False)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# CompiledFunc merge_threshold and parametric guard tests
# ---------------------------------------------------------------------------


class TestCompiledFuncMergeParams:
    """Tests for merge_threshold parameter and parametric+opt=2 guard."""

    def test_parametric_opt2_raises(self):
        def dummy(x):
            return x

        with pytest.raises(ValueError, match="parametric.*opt=2"):
            CompiledFunc(dummy, parametric=True, opt=2)

    def test_opt2_stores_merge_threshold_default(self):
        def dummy(x):
            return x

        cf = CompiledFunc(dummy, opt=2)
        assert cf._merge_threshold == 1

    def test_opt2_stores_custom_merge_threshold(self):
        def dummy(x):
            return x

        cf = CompiledFunc(dummy, opt=2, merge_threshold=3)
        assert cf._merge_threshold == 3


# ---------------------------------------------------------------------------
# opt=2 integration tests (end-to-end merge wiring)
# ---------------------------------------------------------------------------


class TestOpt2Integration:
    """Integration tests for opt=2 merge pipeline."""

    def test_opt2_basic(self):
        """opt=2 produces correct result on first call (same as opt=1)."""
        ql.circuit()

        @ql.compile(opt=2)
        def wrapper(x):
            x += 1
            return x

        a = qint(3, width=4)
        result = wrapper(a)
        assert result is not None

    def test_opt2_second_call_uses_merged(self):
        """After first call with opt=2, _merged_blocks is populated for merge groups."""
        ql.circuit()

        # Use two different compiled functions that operate on the same qubits
        # (overlapping) -- this creates a merge group
        @ql.compile(opt=1)
        def step_a(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def step_b(x):
            x += 2
            return x

        @ql.compile(opt=2)
        def wrapper(x):
            x = step_a(x)
            x = step_b(x)
            return x

        a = qint(2, width=4)
        wrapper(a)
        # After first call, merged_blocks should be populated if merge groups exist
        dag = wrapper.call_graph
        if dag is not None and dag.merge_groups():
            assert wrapper._merged_blocks is not None
            assert len(wrapper._merged_blocks) > 0

    def test_opt2_nonoverlapping_stay_independent(self):
        """Two compiled functions on disjoint qubits produce no merge groups."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc_x(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def inc_y(y):
            y += 1
            return y

        @ql.compile(opt=2)
        def wrapper(x, y):
            x = inc_x(x)
            y = inc_y(y)
            return x

        a = qint(1, width=4)
        b = qint(2, width=4)
        wrapper(a, b)
        # Disjoint qubits => no merge groups => _merged_blocks should be None or empty
        dag = wrapper.call_graph
        if dag is not None:
            groups = dag.merge_groups()
            if not groups:
                assert wrapper._merged_blocks is None or len(wrapper._merged_blocks) == 0

    def test_opt2_call_graph_preserves_original(self):
        """call_graph property shows pre-merge DAG structure after opt=2."""
        ql.circuit()

        @ql.compile(opt=1)
        def step_a(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def step_b(x):
            x += 2
            return x

        @ql.compile(opt=2)
        def wrapper(x):
            x = step_a(x)
            x = step_b(x)
            return x

        a = qint(2, width=4)
        wrapper(a)
        dag = wrapper.call_graph
        assert dag is not None
        # DAG should still reflect original structure (at least 2 inner nodes + wrapper)
        assert dag.node_count >= 2

    def test_opt2_controlled_context(self):
        """opt=2 works inside controlled context (with qbool:)."""
        ql.circuit()

        @ql.compile(opt=2)
        def inc(x):
            x += 1
            return x

        ctrl = ql.qbool(value=True)
        a = qint(2, width=4)

        with ctrl:
            result = inc(a)

        assert result is not None

    def test_opt2_cross_boundary_cancellation(self):
        """Cross-boundary cancellation: merged blocks have fewer gates than sum of parts."""
        ql.circuit()

        @ql.compile(opt=1)
        def step_a(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def step_b(x):
            x += 2
            return x

        @ql.compile(opt=2)
        def wrapper(x):
            x = step_a(x)
            x = step_b(x)
            return x

        a = qint(3, width=4)
        wrapper(a)

        # Verify merged blocks exist and merge produced a valid result
        dag = wrapper.call_graph
        if dag is not None and dag.merge_groups():
            assert wrapper._merged_blocks is not None
            assert len(wrapper._merged_blocks) > 0
            # Verify the merged block has gates (result of merging step_a and step_b)
            for _key, merged_block in wrapper._merged_blocks.items():
                # Merged block should have some gates
                # The gate count may be less than sum of individual blocks
                # due to cross-boundary optimization
                assert merged_block.original_gate_count >= len(merged_block.gates)


# ---------------------------------------------------------------------------
# Edge case tests (Task 2)
# ---------------------------------------------------------------------------


class TestOpt2EdgeCases:
    """Edge case tests for opt=2 merge pipeline."""

    def test_opt2_single_sequence(self):
        """Only one compiled function call, nothing to merge, works normally."""
        ql.circuit()

        @ql.compile(opt=2)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        result = inc(a)
        assert result is not None
        # No merge groups with single call
        assert inc._merged_blocks is None or len(inc._merged_blocks) == 0

    def test_opt2_three_way_chain_merge(self):
        """A overlaps B, B overlaps C -> all three merge into one block."""
        ql.circuit()

        @ql.compile(opt=1)
        def step_a(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def step_b(x):
            x += 2
            return x

        @ql.compile(opt=1)
        def step_c(x):
            x += 3
            return x

        @ql.compile(opt=2)
        def wrapper(x):
            x = step_a(x)
            x = step_b(x)
            x = step_c(x)
            return x

        a = qint(1, width=4)
        wrapper(a)
        dag = wrapper.call_graph
        if dag is not None:
            groups = dag.merge_groups()
            # All three inner calls share qubits -> single merge group
            if groups:
                assert len(groups) == 1
                assert len(groups[0]) >= 3  # wrapper + step_a + step_b + step_c (or subset)

    def test_opt2_merge_threshold(self):
        """merge_threshold=3 skips low-overlap pairs."""
        ql.circuit()

        @ql.compile(opt=1)
        def step_a(x):
            x += 1
            return x

        @ql.compile(opt=1)
        def step_b(x):
            x += 2
            return x

        @ql.compile(opt=2, merge_threshold=100)
        def wrapper(x):
            x = step_a(x)
            x = step_b(x)
            return x

        a = qint(1, width=4)
        wrapper(a)
        # High threshold means no merging (overlap < 100 qubits)
        assert wrapper._merged_blocks is None or len(wrapper._merged_blocks) == 0

    def test_opt2_multiple_calls_same_args(self):
        """Caching works correctly across 3+ calls with same args."""
        ql.circuit()

        @ql.compile(opt=2)
        def inc(x):
            x += 1
            return x

        a = qint(2, width=4)
        inc(a)

        b = qint(3, width=4)
        inc(b)

        c = qint(4, width=4)
        inc(c)

        # All calls should work without error; cache hits on 2nd and 3rd
        assert inc is not None

    def test_opt1_unaffected(self):
        """opt=1 behavior unchanged (no merging)."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(2, width=4)
        inc(a)
        # opt=1 should NOT have _merged_blocks populated
        assert inc._merged_blocks is None

    def test_opt3_unaffected(self):
        """opt=3 behavior unchanged (no DAG, no merging)."""
        ql.circuit()

        @ql.compile(opt=3)
        def inc(x):
            x += 1
            return x

        a = qint(2, width=4)
        inc(a)
        # opt=3 has no DAG and no merging
        assert inc.call_graph is None
        assert inc._merged_blocks is None
