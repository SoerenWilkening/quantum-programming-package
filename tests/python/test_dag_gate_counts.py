"""Tests for Step 0.7: Wire gate counts through recording layer.

Validates that record_operation() passes sequence total_gate_count to
DAGNode.gate_count instead of 0.  Tests cover arithmetic, bitwise,
comparison, and division paths via the @ql.compile integration and
DAG context, as well as the record_operation() unit-level interface.
"""

import quantum_language as ql
from quantum_language import qint
from quantum_language.call_graph import (
    CallGraphDAG,
    _dag_builder_stack,
    pop_dag_context,
    push_dag_context,
    record_operation,
)

# ---------------------------------------------------------------------------
# Unit tests: record_operation() gate_count parameter
# ---------------------------------------------------------------------------


class TestRecordOperationGateCount:
    """Tests for the gate_count parameter on record_operation()."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_default_gate_count_is_zero(self):
        """Without gate_count kwarg, DAGNode.gate_count defaults to 0."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1, 2))
        node = dag.nodes[0]
        assert node.gate_count == 0

    def test_gate_count_passed_through(self):
        """gate_count kwarg is stored on the DAGNode."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1, 2), gate_count=42)
        node = dag.nodes[0]
        assert node.gate_count == 42

    def test_gate_count_large_value(self):
        """Large gate_count values are preserved."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("mul_qq", (0, 1, 2, 3), gate_count=100000)
        node = dag.nodes[0]
        assert node.gate_count == 100000

    def test_gate_count_with_other_kwargs(self):
        """gate_count works alongside sequence_ptr and invert."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_qq",
            (0, 1, 2, 3),
            gate_count=55,
            sequence_ptr=0xCAFE,
            invert=True,
        )
        node = dag.nodes[0]
        assert node.gate_count == 55
        assert node.sequence_ptr == 0xCAFE
        assert node.invert is True

    def test_aggregate_uses_gate_counts(self):
        """CallGraphDAG.aggregate() sums gate_counts from recorded operations."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1), gate_count=10)
        record_operation("mul_cq", (2, 3), gate_count=20)
        pop_dag_context()
        agg = dag.aggregate()
        assert agg["gates"] == 30


# ---------------------------------------------------------------------------
# Integration: addition DAG gate counts via @ql.compile
# ---------------------------------------------------------------------------


class TestAdditionDAGGateCount:
    """Tests that addition operations record nonzero gate_count on DAG nodes."""

    def test_addition_dag_count_nonzero(self):
        """After a += b inside @ql.compile, the add DAG node has gate_count > 0."""
        ql.circuit()

        @ql.compile(opt=1)
        def add_fn(x, y):
            x += y
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        add_fn(a, b)
        dag = add_fn.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) > 0, "Expected at least one add operation node"
        for node in add_nodes:
            assert node.gate_count > 0, f"add node gate_count should be > 0, got {node.gate_count}"

    def test_classical_addition_dag_count_nonzero(self):
        """After x += 1 inside @ql.compile, the add_cq DAG node has gate_count > 0."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(3, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if n.operation_type == "add_cq"]
        assert len(add_nodes) > 0, "Expected at least one add_cq operation node"
        for node in add_nodes:
            assert node.gate_count > 0, (
                f"add_cq node gate_count should be > 0, got {node.gate_count}"
            )

    def test_subtraction_dag_count_nonzero(self):
        """After x -= 1 inside @ql.compile, the add DAG node has gate_count > 0."""
        ql.circuit()

        @ql.compile(opt=1)
        def dec(x):
            x -= 1
            return x

        a = qint(5, width=4)
        dec(a)
        dag = dec.call_graph
        assert dag is not None
        add_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) > 0, "Expected at least one add operation node"
        for node in add_nodes:
            assert node.gate_count > 0, (
                f"add (sub) node gate_count should be > 0, got {node.gate_count}"
            )


# ---------------------------------------------------------------------------
# Integration: multiplication DAG gate counts via @ql.compile
# ---------------------------------------------------------------------------


class TestMultiplicationDAGGateCount:
    """Tests that multiplication operations record nonzero gate_count on DAG nodes."""

    def test_multiplication_dag_count_nonzero(self):
        """After a *= 2 with DAG context, the mul DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a *= 2
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type and "mul" in n.operation_type]
        assert len(mul_nodes) > 0, "Expected at least one mul operation node"
        for node in mul_nodes:
            assert node.gate_count > 0, f"mul node gate_count should be > 0, got {node.gate_count}"


# ---------------------------------------------------------------------------
# Integration: bitwise DAG gate counts
# ---------------------------------------------------------------------------


class TestBitwiseDAGGateCount:
    """Tests that bitwise operations record nonzero gate_count on DAG nodes."""

    def test_and_dag_count_nonzero(self):
        """After a & b with DAG context, the and DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(0b1101, width=4)
            b = qint(0b1011, width=4)
            _ = a & b
        finally:
            pop_dag_context()
        and_nodes = [n for n in dag.nodes if n.operation_type == "and"]
        assert len(and_nodes) > 0, "Expected at least one and operation node"
        for node in and_nodes:
            assert node.gate_count > 0, f"and node gate_count should be > 0, got {node.gate_count}"

    def test_or_dag_count_nonzero(self):
        """After a | b with DAG context, the or DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(0b1100, width=4)
            b = qint(0b0011, width=4)
            _ = a | b
        finally:
            pop_dag_context()
        or_nodes = [n for n in dag.nodes if n.operation_type == "or"]
        assert len(or_nodes) > 0, "Expected at least one or operation node"
        for node in or_nodes:
            assert node.gate_count > 0, f"or node gate_count should be > 0, got {node.gate_count}"

    def test_xor_dag_count_nonzero(self):
        """After a ^ b with DAG context, the xor DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(0b1100, width=4)
            b = qint(0b0110, width=4)
            _ = a ^ b
        finally:
            pop_dag_context()
        xor_nodes = [n for n in dag.nodes if n.operation_type == "xor"]
        assert len(xor_nodes) > 0, "Expected at least one xor operation node"
        for node in xor_nodes:
            assert node.gate_count > 0, f"xor node gate_count should be > 0, got {node.gate_count}"

    def test_ixor_cq_dag_count_nonzero(self):
        """After a ^= 5 with DAG context, the ixor_cq DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(0b1100, width=4)
            a ^= 5
        finally:
            pop_dag_context()
        ixor_nodes = [n for n in dag.nodes if n.operation_type == "ixor_cq"]
        assert len(ixor_nodes) > 0, "Expected at least one ixor_cq operation node"
        for node in ixor_nodes:
            assert node.gate_count > 0, (
                f"ixor_cq node gate_count should be > 0, got {node.gate_count}"
            )

    def test_not_dag_count_nonzero(self):
        """After ~a with DAG context, the not DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(0b1010, width=4)
            _ = ~a
        finally:
            pop_dag_context()
        not_nodes = [n for n in dag.nodes if n.operation_type == "not"]
        assert len(not_nodes) > 0, "Expected at least one not operation node"
        for node in not_nodes:
            assert node.gate_count > 0, f"not node gate_count should be > 0, got {node.gate_count}"


# ---------------------------------------------------------------------------
# Integration: comparison DAG gate counts
# ---------------------------------------------------------------------------


class TestComparisonDAGGateCount:
    """Tests that comparison operations record nonzero gate_count on DAG nodes."""

    def test_eq_cq_dag_count_nonzero(self):
        """After a == 5 with DAG context, the eq_cq DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            _ = a == 5
        finally:
            pop_dag_context()
        eq_nodes = [n for n in dag.nodes if n.operation_type == "eq_cq"]
        assert len(eq_nodes) > 0, "Expected at least one eq_cq operation node"
        for node in eq_nodes:
            assert node.gate_count > 0, (
                f"eq_cq node gate_count should be > 0, got {node.gate_count}"
            )


# ---------------------------------------------------------------------------
# Integration: division DAG gate counts
# ---------------------------------------------------------------------------


class TestDivisionDAGGateCount:
    """Tests that division operations record nonzero gate_count on DAG nodes."""

    def test_floordiv_dag_count_nonzero(self):
        """After a // 3 with DAG context, the divmod_cq DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a // 3
        finally:
            pop_dag_context()
        div_nodes = [n for n in dag.nodes if n.operation_type and "divmod" in n.operation_type]
        assert len(div_nodes) > 0, "Expected at least one divmod operation node"
        for node in div_nodes:
            assert node.gate_count > 0, (
                f"divmod node gate_count should be > 0, got {node.gate_count}"
            )

    def test_mod_dag_count_nonzero(self):
        """After a % 3 with DAG context, the divmod_cq DAG node has gate_count > 0."""
        ql.circuit()
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(7, width=4)
            _ = a % 3
        finally:
            pop_dag_context()
        div_nodes = [n for n in dag.nodes if n.operation_type and "divmod" in n.operation_type]
        assert len(div_nodes) > 0, "Expected at least one divmod operation node"
        for node in div_nodes:
            assert node.gate_count > 0, (
                f"divmod node gate_count should be > 0, got {node.gate_count}"
            )


# ---------------------------------------------------------------------------
# Integration: DAG gate count is positive
# ---------------------------------------------------------------------------


class TestDAGCountPositive:
    """Tests that DAG aggregate gate count is positive after operations."""

    def test_dag_aggregate_positive(self):
        """DAG aggregate gate count should be > 0 after @ql.compile with addition."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(0, width=4)
        inc(a)

        dag = inc.call_graph
        assert dag is not None
        agg = dag.aggregate()
        assert agg["gates"] > 0, f"DAG aggregate gate count should be > 0, got {agg['gates']}"

    def test_operation_counts_sum_positive(self):
        """Sum of operation-level gate counts should be positive."""
        ql.circuit()

        @ql.compile(opt=1)
        def add_twice(x, y):
            x += y
            x += 1
            return x

        a = qint(3, width=4)
        b = qint(2, width=4)
        add_twice(a, b)
        dag = add_twice.call_graph
        assert dag is not None
        op_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        total_op_gates = sum(n.gate_count for n in op_nodes)
        assert total_op_gates > 0, (
            f"Sum of operation gate counts should be > 0, got {total_op_gates}"
        )


# ---------------------------------------------------------------------------
# Integration: report() output contains non-zero gate counts
# ---------------------------------------------------------------------------


class TestReportShowsCounts:
    """Tests that the DAG report() output reflects non-zero gate counts."""

    def test_report_shows_counts(self):
        """report() output should contain non-zero gate count values."""
        ql.circuit()

        @ql.compile(opt=1)
        def inc(x):
            x += 1
            return x

        a = qint(0, width=4)
        inc(a)
        dag = inc.call_graph
        assert dag is not None
        op_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        for node in op_nodes:
            assert node.gate_count > 0
        agg = dag.aggregate()
        assert agg["gates"] > 0


# ---------------------------------------------------------------------------
# Phase 5c.5: Toffoli-mode gate count propagation
# ---------------------------------------------------------------------------


class TestToffoliReportNonzero:
    """Tests that report() shows non-zero gate counts in Toffoli mode."""

    def test_toffoli_report_nonzero(self):
        """report() output shows non-zero gate counts (not '- / -') in Toffoli mode."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
        finally:
            pop_dag_context()
        dag.report()
        # report() should NOT contain '- / -' for the add operation row
        add_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) > 0, "Expected at least one add operation node"
        for node in add_nodes:
            uc = node.uncontrolled_gate_count
            cc = node.controlled_gate_count
            assert uc > 0 or cc > 0, f"Expected non-zero dual gate count, got uc={uc}, cc={cc}"

    def test_toffoli_report_no_dash_dash(self):
        """report() should not show '- / -' for Toffoli-mode operations."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 2
        finally:
            pop_dag_context()
        report_str = dag.report()
        # Check that we don't have the "- / -" pattern for add nodes
        lines = report_str.split("\n")
        for line in lines:
            if "add" in line.lower() and "TOTAL" not in line:
                assert "- / -" not in line, (
                    f"report() still shows '- / -' for Toffoli-mode add: {line}"
                )


class TestToffoliUncontrolledGateCount:
    """Tests that uncontrolled Toffoli calls populate uncontrolled_gate_count."""

    def test_toffoli_uncontrolled_gate_count(self):
        """Uncontrolled Toffoli addition populates uncontrolled_gate_count > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a += 1
        finally:
            pop_dag_context()
        add_nodes = [n for n in dag.nodes if n.operation_type and "add" in n.operation_type]
        assert len(add_nodes) > 0, "Expected at least one add operation node"
        for node in add_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"uncontrolled_gate_count should be > 0, got {node.uncontrolled_gate_count}"
            )
            assert node.controlled_gate_count == 0, (
                f"controlled_gate_count should be 0 for uncontrolled op, got {node.controlled_gate_count}"
            )

    def test_toffoli_uncontrolled_mul(self):
        """Uncontrolled Toffoli multiplication populates uncontrolled_gate_count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            a *= 2
        finally:
            pop_dag_context()
        mul_nodes = [n for n in dag.nodes if n.operation_type and "mul" in n.operation_type]
        assert len(mul_nodes) > 0, "Expected at least one mul operation node"
        for node in mul_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"mul uncontrolled_gate_count should be > 0, got {node.uncontrolled_gate_count}"
            )

    def test_toffoli_uncontrolled_bitwise(self):
        """Uncontrolled Toffoli NOT populates uncontrolled_gate_count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(0b1010, width=4)
            _ = ~a
        finally:
            pop_dag_context()
        not_nodes = [n for n in dag.nodes if n.operation_type == "not"]
        assert len(not_nodes) > 0, "Expected at least one not operation node"
        for node in not_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"not uncontrolled_gate_count should be > 0, got {node.uncontrolled_gate_count}"
            )

    def test_toffoli_uncontrolled_eq(self):
        """Uncontrolled Toffoli equality populates uncontrolled_gate_count."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(5, width=4)
            _ = a == 5
        finally:
            pop_dag_context()
        eq_nodes = [n for n in dag.nodes if n.operation_type == "eq_cq"]
        assert len(eq_nodes) > 0, "Expected at least one eq_cq operation node"
        for node in eq_nodes:
            assert node.uncontrolled_gate_count > 0, (
                f"eq_cq uncontrolled_gate_count should be > 0, got {node.uncontrolled_gate_count}"
            )


class TestToffoliControlledGateCount:
    """Tests that calls inside `with` populates controlled_gate_count."""

    def test_toffoli_controlled_gate_count(self):
        """Controlled Toffoli addition (inside with) populates controlled_gate_count > 0."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        dag = CallGraphDAG()
        push_dag_context(dag)
        try:
            a = qint(3, width=4)
            b = qint(5, width=4)
            cond = a == 3
            with cond:
                b += 1
        finally:
            pop_dag_context()
        # Find add nodes that were recorded in controlled context
        add_nodes = [
            n for n in dag.nodes if n.operation_type and "add" in n.operation_type and n.controlled
        ]
        assert len(add_nodes) > 0, "Expected at least one controlled add operation node"
        for node in add_nodes:
            assert node.controlled_gate_count > 0, (
                f"controlled_gate_count should be > 0, got {node.controlled_gate_count}"
            )


class TestToffoliDepthNonzero:
    """Tests that depth and t_count are propagated when explicitly passed."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_depth_passthrough(self):
        """record_operation() depth parameter is stored on DAGNode."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("add_cq", (0, 1, 2), gate_count=42, depth=10)
        pop_dag_context()
        node = dag.nodes[0]
        assert node.depth == 10, f"Expected depth=10, got {node.depth}"

    def test_t_count_passthrough(self):
        """record_operation() t_count parameter is stored on DAGNode."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation("mul_cq", (0, 1), gate_count=30, t_count=21)
        pop_dag_context()
        node = dag.nodes[0]
        assert node.t_count == 21, f"Expected t_count=21, got {node.t_count}"


class TestToffoliTCountNonzero:
    """Tests for controlled flag propagation on record_operation()."""

    def setup_method(self):
        _dag_builder_stack.clear()

    def teardown_method(self):
        _dag_builder_stack.clear()

    def test_record_operation_controlled_flag(self):
        """record_operation() controlled=True populates controlled_gate_count."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=42,
            controlled=True,
        )
        pop_dag_context()
        node = dag.nodes[0]
        assert node.controlled_gate_count == 42
        assert node.uncontrolled_gate_count == 0

    def test_record_operation_uncontrolled_flag(self):
        """record_operation() controlled=False populates uncontrolled_gate_count."""
        dag = CallGraphDAG()
        push_dag_context(dag)
        record_operation(
            "add_cq",
            (0, 1, 2),
            gate_count=42,
            controlled=False,
        )
        pop_dag_context()
        node = dag.nodes[0]
        assert node.uncontrolled_gate_count == 42
        assert node.controlled_gate_count == 0
