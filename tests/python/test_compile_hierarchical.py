"""Tests for hierarchical compiled function gate count and visualization (Phase 9.4).

Verifies:
- CallRecord dataclass stores func ref, cache key, and arg indices
- Hierarchical gate_count property computes own + referenced gates recursively
- report() distinguishes own gates from referenced (call) gates
- to_dot() renders call relationship edges and call nodes with dashed style
"""

import quantum_language as ql
from quantum_language._compile_state import CallRecord, _record_call
from quantum_language.call_graph import CallGraphDAG
from quantum_language.compile import CompiledBlock


class TestCallRecordFields:
    """CallRecord stores compiled func ref, cache key, and arg indices."""

    def test_call_record_has_required_fields(self):
        """CallRecord dataclass has compiled_func_ref, cache_key, quantum_arg_indices."""
        cr = CallRecord(
            compiled_func_ref="dummy_func",
            cache_key=(1, 2, 3),
            quantum_arg_indices=[[0, 1], [2, 3]],
        )
        assert cr.compiled_func_ref == "dummy_func"
        assert cr.cache_key == (1, 2, 3)
        assert cr.quantum_arg_indices == [[0, 1], [2, 3]]

    def test_call_record_is_dataclass(self):
        """CallRecord is a proper dataclass with equality support."""
        cr1 = CallRecord("f", (1,), [[0]])
        cr2 = CallRecord("f", (1,), [[0]])
        assert cr1 == cr2

    def test_call_record_in_block(self):
        """CallRecord can be stored in a CompiledBlock's _call_records list."""
        block = CompiledBlock(
            gates=[],
            total_virtual_qubits=0,
            param_qubit_ranges=[],
            internal_qubit_count=0,
            return_qubit_range=None,
        )
        cr = CallRecord("inner", (1, 2), [[0, 1]])
        block._call_records.append(cr)
        assert len(block._call_records) == 1
        assert block._call_records[0].compiled_func_ref == "inner"


class TestRecordCall:
    """_record_call appends CallRecord to active block."""

    def test_record_call_no_active_block(self):
        """_record_call is a no-op when no compile block is active."""
        # Should not raise
        _record_call("func", (1,), [[0]])

    def test_record_call_appends_to_block(self):
        """_record_call appends a CallRecord when a block is active."""
        from quantum_language._compile_state import (
            _get_active_compile_block,
            _set_active_compile_block,
        )

        block = CompiledBlock(
            gates=[],
            total_virtual_qubits=0,
            param_qubit_ranges=[],
            internal_qubit_count=0,
            return_qubit_range=None,
        )
        prev = _get_active_compile_block()
        _set_active_compile_block(block)
        try:
            _record_call("inner_func", (1, 2, 3), [[0, 1], [2, 3]])
            assert len(block._call_records) == 1
            cr = block._call_records[0]
            assert cr.compiled_func_ref == "inner_func"
            assert cr.cache_key == (1, 2, 3)
            assert cr.quantum_arg_indices == [[0, 1], [2, 3]]
        finally:
            _set_active_compile_block(prev)


class TestHierarchicalGateCount:
    """gate_count property computes own + referenced gates recursively."""

    def test_gate_count_no_cache(self):
        """gate_count returns zeros when nothing is cached."""

        @ql.compile
        def noop(x):
            return x

        noop.clear_cache()
        counts = noop.gate_count
        assert counts["own"] == 0
        assert counts["referenced"] == 0
        assert counts["total"] == 0

    def test_gate_count_own_only(self):
        """gate_count with no call records shows only own gates."""
        ql.circuit()

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        counts = inc.gate_count
        assert counts["own"] > 0
        assert counts["referenced"] == 0
        assert counts["total"] == counts["own"]

    def test_gate_count_with_call_records(self):
        """gate_count includes referenced function gates when CallRecords exist."""
        ql.circuit()

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def outer(x):
            x += 2
            return x

        # Capture both functions to populate caches
        a = ql.qint(0, width=4)
        inner(a)
        b = ql.qint(0, width=4)
        outer(b)

        # Manually add a CallRecord to outer's cached block referencing inner
        inner_cache_key = list(inner._cache.keys())[0]
        outer_cache_key = list(outer._cache.keys())[0]
        outer_block = outer._cache[outer_cache_key]
        outer_block._call_records.append(
            CallRecord(
                compiled_func_ref=inner,
                cache_key=inner_cache_key,
                quantum_arg_indices=[[1, 2, 3, 4]],
            )
        )

        counts = outer.gate_count
        inner_counts = inner.gate_count
        assert counts["own"] > 0
        assert counts["referenced"] == inner_counts["total"]
        assert counts["total"] == counts["own"] + counts["referenced"]

    def test_hierarchical_gate_count_total_matches_sum(self):
        """Total matches sum of all functions' own gates."""
        ql.circuit()

        @ql.compile
        def f1(x):
            x += 1
            return x

        @ql.compile
        def f2(x):
            x += 3
            return x

        @ql.compile
        def f3(x):
            x += 5
            return x

        # Capture all three
        a = ql.qint(0, width=4)
        f1(a)
        b = ql.qint(0, width=4)
        f2(b)
        c = ql.qint(0, width=4)
        f3(c)

        # f3 calls f2, f2 calls f1 (via CallRecords)
        f1_key = list(f1._cache.keys())[0]
        f2_key = list(f2._cache.keys())[0]

        f2._cache[f2_key]._call_records.append(CallRecord(f1, f1_key, [[1, 2, 3, 4]]))
        f3._cache[list(f3._cache.keys())[0]]._call_records.append(
            CallRecord(f2, f2_key, [[1, 2, 3, 4]])
        )

        counts_f3 = f3.gate_count
        counts_f2 = f2.gate_count
        counts_f1 = f1.gate_count

        # f3.total = f3.own + f2.total = f3.own + f2.own + f1.total
        assert counts_f3["total"] == counts_f3["own"] + counts_f2["total"]
        assert counts_f2["total"] == counts_f2["own"] + counts_f1["total"]

    def test_hierarchical_gate_count_cycle_detection(self):
        """gate_count handles cycles gracefully (returns 0 for revisited nodes)."""
        ql.circuit()

        @ql.compile
        def cyclic(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        cyclic(a)

        # Create a self-referencing CallRecord (artificial cycle)
        cache_key = list(cyclic._cache.keys())[0]
        cyclic._cache[cache_key]._call_records.append(CallRecord(cyclic, cache_key, [[1, 2, 3, 4]]))

        # Should not hang or raise -- cycle detected, referenced = own (one pass)
        counts = cyclic.gate_count
        assert counts["total"] >= counts["own"]

    def test_gate_count_breakdown_lists_referenced(self):
        """gate_count breakdown lists each referenced function."""
        ql.circuit()

        @ql.compile
        def helper(x):
            x += 1
            return x

        @ql.compile
        def main_fn(x):
            x += 2
            return x

        a = ql.qint(0, width=4)
        helper(a)
        b = ql.qint(0, width=4)
        main_fn(b)

        helper_key = list(helper._cache.keys())[0]
        main_key = list(main_fn._cache.keys())[0]
        main_fn._cache[main_key]._call_records.append(
            CallRecord(helper, helper_key, [[1, 2, 3, 4]])
        )

        counts = main_fn.gate_count
        assert len(counts["breakdown"]) == 1
        assert counts["breakdown"][0]["gate_count"] == helper.gate_count["total"]


class TestReportShowsHierarchy:
    """report() distinguishes own gates from referenced gates."""

    def test_report_with_call_nodes(self):
        """Report includes hierarchical breakdown when call nodes are present."""
        dag = CallGraphDAG()
        dag.add_node("outer", frozenset({0, 1}), 10, (), is_call_node=False)
        dag.add_node("inner", frozenset({0, 1}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 1)

        report = dag.report()
        assert "Hierarchical Breakdown" in report
        assert "Own gates" in report
        assert "Referenced gates" in report
        assert "outer -> inner" in report

    def test_report_without_call_nodes(self):
        """Report omits hierarchical section when no call nodes exist."""
        dag = CallGraphDAG()
        dag.add_node("func_a", frozenset({0, 1}), 10, ())
        dag.add_node("func_b", frozenset({2, 3}), 8, ())

        report = dag.report()
        assert "Hierarchical Breakdown" not in report

    def test_report_hierarchical_gate_sums(self):
        """Report shows correct own vs referenced gate counts."""
        dag = CallGraphDAG()
        dag.add_node("main", frozenset({0, 1}), 20, ())
        dag.add_node("sub_call", frozenset({0, 1}), 15, (), is_call_node=True)
        dag.add_call_edge(0, 1)

        report = dag.report()
        assert "Own gates:        20" in report
        assert "Referenced gates:  15" in report
        assert "Total:            35" in report


class TestDotShowsCallEdges:
    """DOT output contains call relationship edges."""

    def test_dot_contains_call_edge(self):
        """DOT output includes call edges with dashed blue style."""
        dag = CallGraphDAG()
        dag.add_node("caller", frozenset({0}), 10, ())
        dag.add_node("callee", frozenset({1}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 1)

        dot = dag.to_dot()
        assert 'label="call"' in dot
        assert "style=dashed" in dot
        assert "color=blue" in dot

    def test_dot_call_node_has_dashed_border(self):
        """Call nodes are rendered with dashed border style."""
        dag = CallGraphDAG()
        dag.add_node("regular", frozenset({0}), 10, ())
        dag.add_node("ref_call", frozenset({1}), 5, (), is_call_node=True)

        dot = dag.to_dot()
        # The call node (n1) should have style=dashed
        lines = dot.split("\n")
        n1_lines = [ln for ln in lines if "n1" in ln and "label=" in ln]
        assert len(n1_lines) == 1
        assert "style=dashed" in n1_lines[0]

        # The regular node (n0) should NOT have style=dashed
        n0_lines = [ln for ln in lines if "n0" in ln and "label=" in ln]
        assert len(n0_lines) == 1
        assert "style=dashed" not in n0_lines[0]

    def test_dot_both_exec_and_call_edges(self):
        """DOT output can contain both execution-order and call edges."""
        dag = CallGraphDAG()
        # Two nodes sharing qubits (creates execution-order edge)
        dag.add_node("step1", frozenset({0, 1}), 10, ())
        dag.add_node("step2", frozenset({0, 1}), 8, ())
        # A call node
        dag.add_node("inner_call", frozenset({2}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 2)

        dot = dag.to_dot()
        assert 'label="exec"' in dot
        assert 'label="call"' in dot

    def test_call_edges_method(self):
        """call_edges() returns only call-type edges."""
        dag = CallGraphDAG()
        dag.add_node("a", frozenset({0, 1}), 10, ())
        dag.add_node("b", frozenset({0, 1}), 8, ())  # exec edge 0->1
        dag.add_node("c", frozenset({2}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 2)

        cedges = dag.call_edges()
        assert len(cedges) == 1
        assert cedges[0] == (0, 2)

        # execution_order_edges should still work
        eoe = dag.execution_order_edges()
        assert len(eoe) >= 1
