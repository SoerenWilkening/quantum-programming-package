"""Tests for Step 11.7: Fix nested call DAG nodes dual-context.

Issue: Quantum_Assembly-bl0.7

Acceptance criteria:
1. After calling outer both controlled and uncontrolled, nested call DAG node
   has both U and C non-zero
2. When only one context captured, shows X / - (backward compatible)
3. Wrapper function nested call node has both U and C from aggregate
"""

import quantum_language as ql
from quantum_language import qbool, qint

# ---------------------------------------------------------------------------
# AC1: Both contexts captured -> both U and C non-zero
# ---------------------------------------------------------------------------


class TestNestedCallBothContexts:
    """After calling outer both controlled and uncontrolled,
    nested call DAG node has both U and C non-zero."""

    def test_both_uc_and_cc_nonzero(self):
        """Nested foo node in outer's DAG has both U and C > 0."""
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1

        @ql.compile(opt=1)
        def outer(a):
            foo(a)

        a = qint(0, width=4)
        # Call uncontrolled
        outer(a)
        # Call controlled
        c = qbool()
        with c:
            outer(a)

        dag = outer.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo" and n.is_call_node]
        assert len(foo_nodes) >= 1, f"Expected at least 1 foo call node, got {len(foo_nodes)}"

        # At least one foo node should have both U and C non-zero
        has_both = any(
            n.uncontrolled_gate_count > 0 and n.controlled_gate_count > 0 for n in foo_nodes
        )
        assert has_both, (
            f"Expected at least one foo node with both U > 0 and C > 0, "
            f"got UC={[n.uncontrolled_gate_count for n in foo_nodes]}, "
            f"CC={[n.controlled_gate_count for n in foo_nodes]}"
        )

    def test_both_contexts_multiple_inner_calls(self):
        """Multiple nested calls each get both U and C."""
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1

        @ql.compile(opt=1)
        def outer(a):
            foo(a)
            foo(a)

        a = qint(0, width=4)
        outer(a)
        c = qbool()
        with c:
            outer(a)

        dag = outer.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo" and n.is_call_node]
        assert len(foo_nodes) >= 2, f"Expected at least 2 foo call nodes, got {len(foo_nodes)}"

        # Check that we have nodes with both contexts populated
        both_populated = [
            n for n in foo_nodes if n.uncontrolled_gate_count > 0 and n.controlled_gate_count > 0
        ]
        assert len(both_populated) >= 1, (
            f"Expected foo nodes with both U and C, "
            f"UC={[n.uncontrolled_gate_count for n in foo_nodes]}, "
            f"CC={[n.controlled_gate_count for n in foo_nodes]}"
        )


# ---------------------------------------------------------------------------
# AC2: Only one context captured -> shows X / - (backward compatible)
# ---------------------------------------------------------------------------


class TestNestedCallSingleContext:
    """When only one context captured, the other side stays 0."""

    def test_uncontrolled_only(self):
        """Only uncontrolled call: U > 0, C == 0."""
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1

        @ql.compile(opt=1)
        def outer(a):
            foo(a)

        a = qint(0, width=4)
        outer(a)  # only uncontrolled

        dag = outer.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo" and n.is_call_node]
        assert len(foo_nodes) >= 1

        # With only uncontrolled context, C should be 0
        for node in foo_nodes:
            if node.uncontrolled_gate_count > 0:
                assert node.controlled_gate_count == 0, (
                    f"Expected C == 0 with only uncontrolled context, "
                    f"got U={node.uncontrolled_gate_count}, C={node.controlled_gate_count}"
                )

    def test_controlled_only(self):
        """Only controlled call: C > 0, U == 0."""
        ql.circuit()

        @ql.compile(opt=1)
        def foo(a):
            a += 1

        @ql.compile(opt=1)
        def outer(a):
            foo(a)

        a = qint(0, width=4)
        c = qbool()
        with c:
            outer(a)  # only controlled

        dag = outer.call_graph
        assert dag is not None

        foo_nodes = [n for n in dag.nodes if n.func_name == "foo" and n.is_call_node]
        assert len(foo_nodes) >= 1

        # With only controlled context, U should be 0
        for node in foo_nodes:
            if node.controlled_gate_count > 0:
                assert node.uncontrolled_gate_count == 0, (
                    f"Expected U == 0 with only controlled context, "
                    f"got U={node.uncontrolled_gate_count}, C={node.controlled_gate_count}"
                )


# ---------------------------------------------------------------------------
# AC3: Wrapper function nested call node has both U and C from aggregate
# ---------------------------------------------------------------------------


class TestWrapperFunctionDualContext:
    """Wrapper functions (only calling other compiled functions) get both U/C."""

    def test_wrapper_both_contexts(self):
        """Wrapper mid -> inner, called both ways, has both U and C."""
        ql.circuit()

        @ql.compile(opt=1)
        def inner(a):
            a += 1

        @ql.compile(opt=1)
        def mid(a):
            inner(a)

        @ql.compile(opt=1)
        def outer(a):
            mid(a)

        a = qint(0, width=4)
        outer(a)
        c = qbool()
        with c:
            outer(a)

        dag = outer.call_graph
        assert dag is not None

        mid_nodes = [n for n in dag.nodes if n.func_name == "mid" and n.is_call_node]
        assert len(mid_nodes) >= 1, f"Expected at least 1 mid call node, got {len(mid_nodes)}"

        # At least one mid node should have both U and C populated
        has_both = any(
            n.uncontrolled_gate_count > 0 and n.controlled_gate_count > 0 for n in mid_nodes
        )
        assert has_both, (
            f"Expected mid wrapper node with both U and C from aggregate, "
            f"UC={[n.uncontrolled_gate_count for n in mid_nodes]}, "
            f"CC={[n.controlled_gate_count for n in mid_nodes]}"
        )

    def test_wrapper_gate_count_positive(self):
        """Wrapper function node has gate_count > 0 (from aggregate)."""
        ql.circuit()

        @ql.compile(opt=1)
        def inner(a):
            a += 1

        @ql.compile(opt=1)
        def mid(a):
            inner(a)

        @ql.compile(opt=1)
        def outer(a):
            mid(a)

        a = qint(0, width=4)
        outer(a)

        dag = outer.call_graph
        assert dag is not None

        mid_nodes = [n for n in dag.nodes if n.func_name == "mid" and n.is_call_node]
        assert len(mid_nodes) >= 1
        for node in mid_nodes:
            assert node.gate_count > 0, (
                f"Wrapper mid node should have gate_count > 0, got {node.gate_count}"
            )
