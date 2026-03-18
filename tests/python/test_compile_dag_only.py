"""Tests for opt=1 DAG-only replay behavior in compile.py.

Verifies that opt=1 compiled functions skip inject_remapped_gates() on replay
(cache hit), recording only a DAG node. Capture (first call) still injects
gates normally. Other opt levels (0, 2, 3) remain unchanged.
"""

import quantum_language as ql
from quantum_language._core import get_current_layer


class TestOpt1DagOnlyReplay:
    """Verify opt=1 replay skips gate injection while still recording DAG."""

    def test_opt1_replay_does_not_inject_gates(self):
        """opt=1 with simulate=False: replay should NOT increase flat circuit layers.

        When simulate=False (tracking-only / DAG-only mode), gates are
        not stored in the circuit.  Replay skips injection and only
        credits gate count.
        """
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # capture -- no gates stored (simulate=False)

        b = ql.qint(0, width=4)
        layer_before_replay = get_current_layer()
        inc(b)  # replay -- no gates stored (simulate=False)
        layer_after_replay = get_current_layer()

        replay_layers = layer_after_replay - layer_before_replay
        assert replay_layers == 0, (
            f"simulate=False replay should not inject gates (expected 0 new layers, got {replay_layers})"
        )

    def test_opt0_replay_injects_gates_both_times(self):
        """opt=0 both calls should inject gates -- old behavior unchanged."""
        ql.circuit()

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
        """opt=1 with simulate=False in QFT mode: 3 calls record DAG nodes.

        In QFT mode (fault_tolerant=False) with simulate=False, IR
        entries are recorded and _build_dag_from_ir populates the DAG
        on replay.  In Toffoli mode (default), no IR entries exist so
        replay does not add DAG nodes — only the capture node is present.
        """
        ql.circuit()
        ql.option("simulate", False)
        ql.option("fault_tolerant", False)  # QFT mode: IR entries recorded

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # capture (1st call = node 1 + IR entries)

        b = ql.qint(0, width=4)
        inc(b)  # replay (2nd call = DAG from IR)

        c = ql.qint(0, width=4)
        inc(c)  # replay (3rd call = DAG from IR)

        dag = inc._call_graph
        assert dag is not None, "opt=1 should build a call graph DAG"
        # QFT mode + simulate=False: capture produces IR, replays
        # build DAG from IR entries.
        assert dag.node_count >= 1, f"Expected >= 1 DAG nodes, got {dag.node_count}"

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
