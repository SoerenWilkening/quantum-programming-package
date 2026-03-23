"""Tests for opt=1 DAG-only mode control context recording.

Verify that opt=1 (DAG-only) mode respects control context. The cached
block records whether the call was controlled via ``_captured_controlled``,
and each context captures its own block independently.

Requirements: Quantum_Assembly-aql.3
"""

import gc
import warnings

import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")


class TestOpt1DagRecordsControl:
    """opt=1 mode records control context on cached blocks and DAG nodes."""

    def test_opt1_dag_records_control_uncontrolled(self):
        """opt=1 capture outside with-block records _captured_controlled=False."""

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        block = list(inc._cache.values())[0]
        assert block._captured_controlled is False

    def test_opt1_dag_records_control_controlled(self):
        """opt=1 capture inside with-block records _captured_controlled=True."""

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        c = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c:
            _ = inc(a)

        block = list(inc._cache.values())[0]
        assert block._captured_controlled is True

    def test_opt1_dag_node_has_controlled_attribute(self):
        """DAGNode objects always have a controlled attribute."""

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        a = ql.qint(0, width=2)
        _ = inc(a)

        dag = inc.call_graph
        assert dag is not None
        for node in dag._nodes:
            assert hasattr(node, "controlled")

    def test_opt0_dag_records_control(self):
        """opt=0 replay DAG node also records controlled flag."""

        @ql.compile(opt=0)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()

        # Capture uncontrolled
        a = ql.qint(0, width=2)
        _ = inc(a)

        # Replay controlled
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)

        dag = inc.call_graph
        assert dag is not None
        inc_nodes = [n for n in dag._nodes if n.func_name == "inc"]
        # opt=0 records a DAG node on replay
        assert len(inc_nodes) >= 1
        # The last inc node should be controlled
        assert inc_nodes[-1].controlled is True


class TestOpt1CaptureRespectsControl:
    """First (capture) call in opt=1 mode handles control correctly."""

    def test_opt1_capture_in_with_one_entry(self):
        """opt=1 first call inside with-block stores one entry."""

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        c = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c:
            _ = inc(a)

        # One cache entry for the controlled context
        assert len(inc._cache) == 1

    def test_opt1_capture_uncontrolled_then_controlled(self):
        """opt=1 capture uncontrolled, then controlled creates two entries."""

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)

        # Capture uncontrolled
        a = ql.qint(0, width=2)
        _ = inc(a)
        assert len(inc._cache) == 1

        # Controlled call -- should create separate cache entry
        c = ql.qbool(True)
        b = ql.qint(0, width=2)
        with c:
            _ = inc(b)

        # Per-context cache: uncontrolled and controlled are separate entries
        assert len(inc._cache) == 2

    def test_opt1_no_controlled_block_attribute(self):
        """opt=1 blocks do not have a controlled_block attribute."""

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        gc.collect()
        ql.circuit()
        ql.option("simulate", True)
        c = ql.qbool(True)
        a = ql.qint(0, width=2)
        with c:
            _ = inc(a)

        block = list(inc._cache.values())[0]
        assert not hasattr(block, "controlled_block")
