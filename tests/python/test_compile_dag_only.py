"""Tests for opt=1 DAG-only replay behavior in compile.py.

Verifies that opt=1 compiled functions skip inject_remapped_gates() on replay
(cache hit), recording only a DAG node. Capture (first call) still injects
gates normally. Other opt levels (0, 2, 3) remain unchanged.
"""

import quantum_language as ql
from quantum_language._core import get_current_layer


class TestOpt1DagOnlyReplay:
    """Verify opt=1 replay skips gate injection while still recording DAG."""

    def test_opt1_replay_injects_gates_when_simulate_true(self):
        """opt=1 capture and replay both inject gates when simulate=True.

        With simulate=True, the user expects every call to produce gates
        in the circuit.  The opt=1 skip-injection optimisation only
        applies when simulate=False (DAG-only / tracking mode).
        """
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        layer_before_capture = get_current_layer()
        inc(a)  # capture -- gates injected
        layer_after_capture = get_current_layer()

        capture_layers = layer_after_capture - layer_before_capture
        assert capture_layers > 0, "Capture must inject gates (layers should increase)"

        b = ql.qint(0, width=4)
        layer_before_replay = get_current_layer()
        inc(b)  # replay -- opt=1 with simulate=True SHOULD inject gates
        layer_after_replay = get_current_layer()

        replay_layers = layer_after_replay - layer_before_replay
        assert replay_layers > 0, (
            f"opt=1 replay with simulate=True should inject gates (expected > 0 layers, got {replay_layers})"
        )

    def test_opt0_replay_injects_gates_both_times(self):
        """opt=0 both calls should inject gates -- old behavior unchanged."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile(opt=0)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        layer_before_capture = get_current_layer()
        inc(a)  # capture
        layer_after_capture = get_current_layer()

        capture_layers = layer_after_capture - layer_before_capture
        assert capture_layers > 0, "Capture must inject gates"

        b = ql.qint(0, width=4)
        layer_before_replay = get_current_layer()
        inc(b)  # replay
        layer_after_replay = get_current_layer()

        replay_layers = layer_after_replay - layer_before_replay
        assert replay_layers > 0, (
            f"opt=0 replay should inject gates (expected > 0 layers, got {replay_layers})"
        )

    def test_opt1_dag_records_three_nodes(self):
        """opt=1 called 3 times produces DAG with >= 3 nodes and correct aggregate.

        Capture produces an operation-type node (from record_operation
        during body execution) and replays produce call-level nodes
        (from dag.add_node in _call_inner).  All replay call nodes
        should have equal gate counts.
        """
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # capture (1st call = operation-type node)

        b = ql.qint(0, width=4)
        inc(b)  # replay (2nd call = call-level node)

        c = ql.qint(0, width=4)
        inc(c)  # replay (3rd call = call-level node)

        dag = inc._call_graph
        assert dag is not None, "opt=1 should build a call graph DAG"
        assert dag.node_count >= 3, f"Expected >= 3 DAG nodes, got {dag.node_count}"

        agg = dag.aggregate()
        assert agg["gates"] > 0, "Aggregate gate count should be positive"

        # Replay call-level nodes (no operation_type) should have equal
        # gate counts.
        call_nodes = [n for n in dag.nodes if not n.operation_type or n.operation_type == ""]
        assert len(call_nodes) >= 2, (
            f"Expected >= 2 call-level nodes from replays, got {len(call_nodes)}"
        )
        gate_counts = [n.gate_count for n in call_nodes]
        assert len(set(gate_counts)) == 1, (
            f"All replay call nodes should have same gate count, got {gate_counts}"
        )

        # Aggregate should equal sum of all node gate counts
        total = sum(n.gate_count for n in dag.nodes)
        assert agg["gates"] == total, (
            f"Aggregate should equal sum of all nodes ({total}), got {agg['gates']}"
        )

    def test_opt1_replay_returns_correct_qint(self):
        """opt=1 replay still correctly returns quantum values."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        r1 = inc(a)  # capture
        assert r1 is not None, "Capture should return a qint"
        assert r1.width == 4, f"Capture return width should be 4, got {r1.width}"

        b = ql.qint(0, width=4)
        r2 = inc(b)  # replay
        assert r2 is not None, "Replay should return a qint"
        assert r2.width == 4, f"Replay return width should be 4, got {r2.width}"

        # Return qubits should be different from input qubits (new allocation)
        # and different from the first call's return qubits
        assert not (r2.qubits == r1.qubits).all(), (
            "Replay return should have different qubit indices than capture return"
        )


class TestSimulateReplayInjection:
    """Verify opt=1 replay gate injection depends on simulate mode."""

    def test_simulate_true_uncontrolled_replay_injects(self):
        """With simulate=True, calling foo() 3 times uncontrolled produces
        gates in the circuit for all 3 calls."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        # First call: capture
        a = ql.qint(0, width=4)
        layer_before = get_current_layer()
        inc(a)
        layer_after_first = get_current_layer()
        first_layers = layer_after_first - layer_before
        assert first_layers > 0, "First call (capture) must inject gates"

        # Second call: replay
        b = ql.qint(0, width=4)
        layer_before_second = get_current_layer()
        inc(b)
        layer_after_second = get_current_layer()
        second_layers = layer_after_second - layer_before_second
        assert second_layers > 0, (
            f"Second call (replay) with simulate=True must inject gates, got {second_layers} layers"
        )

        # Third call: replay
        c = ql.qint(0, width=4)
        layer_before_third = get_current_layer()
        inc(c)
        layer_after_third = get_current_layer()
        third_layers = layer_after_third - layer_before_third
        assert third_layers > 0, (
            f"Third call (replay) with simulate=True must inject gates, got {third_layers} layers"
        )

    def test_simulate_false_uncontrolled_replay_skips(self):
        """With simulate=False, opt=1 uncontrolled replay skips gate injection
        (DAG-only mode preserved)."""
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        # First call: capture (no gates stored in simulate=False mode)
        a = ql.qint(0, width=4)
        inc(a)

        # Second call: replay -- should NOT inject gates
        b = ql.qint(0, width=4)
        layer_before_second = get_current_layer()
        inc(b)
        layer_after_second = get_current_layer()
        replay_layers = layer_after_second - layer_before_second
        assert replay_layers == 0, (
            f"opt=1 replay with simulate=False should not inject gates, got {replay_layers} layers"
        )
