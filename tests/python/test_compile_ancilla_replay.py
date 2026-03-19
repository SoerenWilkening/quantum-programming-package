"""Tests for compiled function ancilla replay (Phase 8).

Verifies:
- Gate-level replay frees transient ancillas after injection (Step 8.3)
- Repeated gate-level replay calls do not grow qubit count (Step 8.3)
- Transient virtual indices are correctly classified during capture (Step 8.1)
"""

import quantum_language as ql


class TestTransientClassification:
    """Step 8.1: Transient virtual indices are classified after capture."""

    def test_addition_has_transients(self):
        """In-place addition produces transient ancillas (carry bits)."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_vals(x, y):
            x += y
            return x

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        add_vals(a, b)

        # Get the cached block
        block = None
        for blk in add_vals._cache.values():
            block = blk
            break
        assert block is not None

        # Addition uses carry bits that are freed during capture
        assert hasattr(block, "transient_virtual_indices")
        assert isinstance(block.transient_virtual_indices, frozenset)
        # Toffoli addition uses carry/temp qubits that are transient
        assert len(block.transient_virtual_indices) > 0

    def test_inplace_add_no_result_qubits(self):
        """In-place add returns a param -- no result qubit allocation needed."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_inplace(x, y):
            x += y
            return x

        a = ql.qint(1, width=4)
        b = ql.qint(2, width=4)
        add_inplace(a, b)

        block = None
        for blk in add_inplace._cache.values():
            block = blk
            break
        assert block is not None
        # return_is_param_index should be set (return value IS a parameter)
        assert block.return_is_param_index is not None

    def test_transient_indices_are_virtual(self):
        """Transient indices refer to virtual qubit space, not physical."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_fn(x, y):
            x += y
            return x

        a = ql.qint(0, width=4)
        b = ql.qint(0, width=4)
        add_fn(a, b)

        block = None
        for blk in add_fn._cache.values():
            block = blk
            break
        assert block is not None

        # All transient indices should be valid virtual indices
        param_max = max(end for _, end in block.param_qubit_ranges)
        for vidx in block.transient_virtual_indices:
            assert vidx >= param_max, (
                f"Transient index {vidx} overlaps with parameter range (max={param_max})"
            )
            assert vidx < block.total_virtual_qubits, (
                f"Transient index {vidx} >= total_virtual_qubits ({block.total_virtual_qubits})"
            )


class TestGateReplayFreesTransients:
    """Step 8.3: Gate-level replay frees transient ancillas."""

    def test_gate_replay_frees_transients(self):
        """After gate-level replay, transient qubits are back in the free pool."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_fn(x, y):
            x += y
            return x

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)

        # First call: capture
        add_fn(a, b)

        stats_after_capture = ql.circuit_stats()
        current_after_capture = stats_after_capture["current_in_use"]

        # Second call: replay (gate-level path)
        c = ql.qint(1, width=4)
        d = ql.qint(4, width=4)
        add_fn(c, d)

        stats_after_replay = ql.circuit_stats()
        current_after_replay = stats_after_replay["current_in_use"]

        # After replay, transient qubits should have been freed.
        # The current_in_use should account for: a(4) + b(4) + c(4) + d(4) = 16
        # NOT 16 + carry_bits (which would happen without freeing transients)
        # The exact value depends on how many transient qubits the addition uses,
        # but the key point is that replay should not leave extra qubits allocated.
        #
        # With 4-bit addition: 4 param qubits per arg = 8 param qubits per call.
        # First call uses 8 + capture ancillas. After capture, ancillas stay.
        # Second call allocates 8 new param qubits + temp ancillas, then frees them.
        assert current_after_replay <= current_after_capture + 8, (
            f"Replay grew qubits beyond expected: "
            f"after_capture={current_after_capture}, after_replay={current_after_replay}"
        )

    def test_gate_replay_three_calls_stable(self):
        """Gate-level replay path does not grow qubits on repeated calls."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_fn(x, y):
            x += y
            return x

        a = ql.qint(1, width=4)
        b = ql.qint(2, width=4)

        # First call: capture
        add_fn(a, b)

        # Second call: replay
        c = ql.qint(3, width=4)
        d = ql.qint(4, width=4)
        add_fn(c, d)
        stats_after_second = ql.circuit_stats()

        # Third call: replay
        e = ql.qint(5, width=4)
        f = ql.qint(6, width=4)
        add_fn(e, f)
        stats_after_third = ql.circuit_stats()

        # Current in use should grow by exactly the param qubits (8 per call),
        # not by param + transient qubits.
        growth_2_to_3 = stats_after_third["current_in_use"] - stats_after_second["current_in_use"]

        # Each call adds 8 param qubits (4 per arg), transients should be freed
        assert growth_2_to_3 == 8, (
            f"Qubit growth between calls 2 and 3 should be 8 (param qubits only), "
            f"got {growth_2_to_3}. second={stats_after_second['current_in_use']}, "
            f"third={stats_after_third['current_in_use']}"
        )

    def test_gate_replay_classical_add_stable(self):
        """Classical addition (x += 1) also frees transients on replay."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)  # capture

        b = ql.qint(0, width=4)
        inc(b)  # replay
        stats_after_second = ql.circuit_stats()

        c = ql.qint(0, width=4)
        inc(c)  # replay
        stats_after_third = ql.circuit_stats()

        # Growth between second and third call should be exactly the param width
        growth = stats_after_third["current_in_use"] - stats_after_second["current_in_use"]
        assert growth == 4, f"Expected growth of 4 (param qubits), got {growth}"


class TestTransientFreeingCorrectness:
    """Verify that freeing transients does not break correctness."""

    def test_transient_qubits_reused(self):
        """Freed transient qubits are available for reuse by subsequent allocations."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_fn(x, y):
            x += y
            return x

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        add_fn(a, b)  # capture

        # Get block to check transient count
        block = None
        for blk in add_fn._cache.values():
            block = blk
            break
        num_transients = len(block.transient_virtual_indices) if block else 0
        assert num_transients > 0, "Expected transient ancillas from addition"

        # Replay and check that peak allocated does not keep growing
        peak_values = []
        for i in range(3):
            c = ql.qint(i, width=4)
            d = ql.qint(i + 1, width=4)
            add_fn(c, d)
            stats = ql.circuit_stats()
            peak_values.append(stats["peak_allocated"])

        # Peak should stabilize (not grow indefinitely)
        # After a few calls, the peak should not increase because
        # freed transient qubits are being reused
        assert peak_values[-1] <= peak_values[0] + 8 * 3, (
            f"Peak allocated grew too much: {peak_values}"
        )


class TestControlledReplayFreesTransients:
    """Controlled replay path (compiled function inside `with` block) frees transients."""

    def test_controlled_replay_frees_transients(self):
        """Calling a compiled function inside a `with` block on replay frees transients."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_fn(x, y):
            x += y
            return x

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)

        # First call: capture (uncontrolled)
        add_fn(a, b)

        # Verify transient_virtual_indices is propagated to controlled block
        block = None
        for blk in add_fn._cache.values():
            block = blk
            break
        assert block is not None
        assert block.controlled_block is not None
        assert block.controlled_block.transient_virtual_indices == block.transient_virtual_indices
        assert len(block.controlled_block.transient_virtual_indices) > 0

        # Second call: controlled replay inside a `with` block
        c = ql.qint(1, width=4)
        d = ql.qint(4, width=4)
        cond = ql.qbool()
        with cond:
            add_fn(c, d)

        stats_after_controlled = ql.circuit_stats()

        # Third call: another controlled replay
        e = ql.qint(5, width=4)
        f = ql.qint(6, width=4)
        cond2 = ql.qbool()
        with cond2:
            add_fn(e, f)

        stats_after_third = ql.circuit_stats()

        # Growth between controlled calls should be param qubits (8) + 1 cond qbool
        # Transient ancillas should be freed and not accumulate
        growth = stats_after_third["current_in_use"] - stats_after_controlled["current_in_use"]
        assert growth <= 9, (
            f"Controlled replay grew qubits beyond expected: growth={growth}, "
            f"after_second={stats_after_controlled['current_in_use']}, "
            f"after_third={stats_after_third['current_in_use']}"
        )
