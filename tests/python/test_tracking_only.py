"""Tests for simulate option and tracking-only mode in @ql.compile.

Verifies that when ql.option('simulate') is explicitly set to False,
gates are counted but not stored in the global circuit.  The DAG should
still record gate counts via the circ->gate_count delta.

Note: The default after ql.circuit() is simulate=True (set by
_clear_all_caches), so tests that need tracking-only mode must
explicitly call ql.option('simulate', False).
"""

import quantum_language as ql
from quantum_language._core import get_current_layer


class TestSimulateOption:
    """Verify ql.option('simulate') get/set behavior."""

    def test_default_simulate_is_true(self):
        """simulate defaults to True after ql.circuit().

        _clear_all_caches enables simulate so that QASM export,
        compiled function replay, and simulation work out of the box.
        """
        ql.circuit()
        assert ql.option("simulate") is True

    def test_set_simulate_true(self):
        """Can set simulate to True and read it back."""
        ql.circuit()
        ql.option("simulate", True)
        assert ql.option("simulate") is True

    def test_set_simulate_false(self):
        """Can set simulate to False and read it back."""
        ql.circuit()
        ql.option("simulate", False)
        assert ql.option("simulate") is False


class TestSimulateFalseCapture:
    """Verify simulate=False uses tracking-only mode."""

    def test_simulate_false_no_circuit_gates(self):
        """simulate=False should not add gates to the flat circuit.

        The layer count should not increase during capture when
        tracking-only mode is active.
        """
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        layer_before = get_current_layer()
        inc(a)
        layer_after = get_current_layer()

        assert layer_after == layer_before, (
            f"simulate=False should not inject gates into circuit "
            f"(expected 0 new layers, got {layer_after - layer_before})"
        )

    def test_simulate_false_dag_has_gate_count(self):
        """simulate=False should still record gate counts in the DAG.

        The DAG should have at least 1 node with a positive gate_count
        even though no gates were stored in the circuit.  In Toffoli
        mode (default), the capture body produces operation-type nodes
        via record_operation.
        """
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        dag = inc._call_graph
        assert dag is not None, "opt=1 should build a call graph DAG"
        assert dag.node_count >= 1, "DAG should have at least 1 node"

        # Check that at least one node has a positive gate count.
        # In Toffoli mode, capture produces operation-type nodes (e.g.
        # "add_cq") via record_operation rather than call-level nodes.
        nodes_with_gates = [n for n in dag.nodes if n.gate_count > 0]
        assert len(nodes_with_gates) >= 1, (
            f"Should have at least 1 node with positive gate_count, "
            f"got gate_counts={[n.gate_count for n in dag.nodes]}"
        )

    def test_simulate_false_returns_qint(self):
        """simulate=False capture should still return a valid qint."""
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        result = inc(a)

        assert result is not None, "Should return a qint"
        assert result.width == 4, f"Return width should be 4, got {result.width}"


class TestSimulateTrueExplicit:
    """Verify simulate=True enables normal gate injection."""

    def test_simulate_true_injects_gates(self):
        """simulate=True (default) should inject gates into circuit."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        layer_before = get_current_layer()
        inc(a)
        layer_after = get_current_layer()

        assert layer_after > layer_before, (
            f"simulate=True should inject gates (expected > 0 new layers, "
            f"got {layer_after - layer_before})"
        )

    def test_simulate_true_dag_gate_count_matches(self):
        """simulate=True DAG gate count should be positive."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        dag = inc._call_graph
        assert dag is not None
        assert dag.node_count >= 1, "DAG should have at least 1 node"
        nodes_with_gates = [n for n in dag.nodes if n.gate_count > 0]
        assert len(nodes_with_gates) >= 1, "Should have at least 1 node with positive gate_count"


class TestSimulateFalseAggregate:
    """Verify aggregate gate counts work correctly with simulate=False."""

    def test_multiple_calls_aggregate(self):
        """Multiple calls with simulate=False should aggregate gate counts."""
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # capture (call 1)

        b = ql.qint(0, width=4)
        inc(b)  # replay (call 2)

        dag = inc._call_graph
        assert dag is not None

        agg = dag.aggregate()
        assert agg["gates"] > 0, "Aggregate should have positive gate count"
