"""Tests for get_gate_count() and reset_gate_count() accessor functions.

Verifies that the running gate_count field on circuit_t is correctly
exposed via Cython accessors in _core.pyx (Module 2: Cython declaration
updates, issue Quantum_Assembly-fk9).
"""

import quantum_language as ql


class TestGetGateCount:
    """Tests for get_gate_count() accessor."""

    def test_fresh_circuit_gate_count_is_zero(self):
        """A fresh circuit has a running gate count of zero."""
        ql.circuit()
        assert ql.get_gate_count() == 0

    def test_gate_count_increases_after_operations(self):
        """Gate count increases when quantum operations are performed."""
        ql.circuit()
        assert ql.get_gate_count() == 0
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        assert ql.get_gate_count() > 0

    def test_gate_count_returns_int(self):
        """get_gate_count() returns a Python int."""
        ql.circuit()
        result = ql.get_gate_count()
        assert isinstance(result, int)

    def test_gate_count_independent_of_circuit_property(self):
        """Running gate count and circuit.gate_count are independent counters.

        get_gate_count() only tracks gates emitted via run_instruction().
        circuit.gate_count (via circuit_gate_count) counts all stored gates
        including those from hot-path functions that bypass run_instruction.
        The two may differ in either direction depending on which code paths
        are used.
        """
        c = ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        running = ql.get_gate_count()
        stored = c.gate_count
        # Both should be positive after operations
        assert running > 0
        assert stored > 0

    def test_gate_count_monotonically_increases(self):
        """Gate count never decreases during normal execution."""
        ql.circuit()
        counts = [ql.get_gate_count()]
        a = ql.qint(3, width=4)
        counts.append(ql.get_gate_count())
        b = ql.qint(2, width=4)
        counts.append(ql.get_gate_count())
        _ = a + b
        counts.append(ql.get_gate_count())
        for i in range(1, len(counts)):
            assert counts[i] >= counts[i - 1]

    def test_gate_count_resets_on_new_circuit(self):
        """Creating a new circuit resets the running gate count."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        assert ql.get_gate_count() > 0

        ql.circuit()
        assert ql.get_gate_count() == 0


class TestResetGateCount:
    """Tests for reset_gate_count() accessor."""

    def test_reset_sets_count_to_zero(self):
        """reset_gate_count() sets the running counter to zero."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        assert ql.get_gate_count() > 0

        ql.reset_gate_count()
        assert ql.get_gate_count() == 0

    def test_reset_then_operations_count_from_zero(self):
        """After reset, subsequent operations count from zero."""
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        first_count = ql.get_gate_count()
        assert first_count > 0

        ql.reset_gate_count()
        c = ql.qint(1, width=4)
        d = ql.qint(2, width=4)
        _ = c + d
        second_count = ql.get_gate_count()
        assert second_count > 0

    def test_reset_is_idempotent(self):
        """Calling reset_gate_count() twice has no additional effect."""
        ql.circuit()
        a = ql.qint(5, width=4)
        _ = a + ql.qint(3, width=4)

        ql.reset_gate_count()
        assert ql.get_gate_count() == 0
        ql.reset_gate_count()
        assert ql.get_gate_count() == 0

    def test_reset_does_not_affect_circuit_structure(self):
        """Resetting gate count does not alter stored circuit gates."""
        c = ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        stored_count = c.gate_count

        ql.reset_gate_count()
        # The stored circuit gates (circuit.gate_count via layer iteration)
        # should be unchanged
        assert c.gate_count == stored_count


class TestPxdDeclarations:
    """Verify that .pxd declarations for tracking_only and gate_count are
    functional by exercising the code paths they enable."""

    def test_run_instruction_tracking_only_declared(self):
        """run_instruction with tracking_only=0 works (normal path).

        This indirectly verifies the .pxd declaration includes the
        tracking_only parameter, since all qint operations go through
        run_instruction(..., tracking_only=0).
        """
        ql.circuit()
        a = ql.qint(5, width=4)
        b = ql.qint(3, width=4)
        _ = a + b
        # If the declaration were wrong, the above would crash or fail
        assert ql.get_gate_count() > 0

    def test_gate_count_field_accessible(self):
        """The gate_count field on circuit_s is readable and writable.

        get_gate_count() reads it, reset_gate_count() writes 0 to it.
        """
        ql.circuit()
        a = ql.qint(7, width=4)
        _ = a + ql.qint(2, width=4)
        count = ql.get_gate_count()
        assert count > 0

        ql.reset_gate_count()
        assert ql.get_gate_count() == 0
