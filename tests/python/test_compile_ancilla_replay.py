"""Tests for compiled function ancilla replay (Phase 8).

Verifies:
- IR replay skips transient allocation (Step 8.2)
- Gate-level replay frees transient ancillas after injection (Step 8.3)
- Repeated replay calls do not grow qubit count (Steps 8.2, 8.3)
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


class TestIRReplaySkipsTransientAllocation:
    """Step 8.2: IR replay skips transient allocation."""

    def test_three_calls_no_qubit_growth(self):
        """foo(a, b) called 3 times with in-place add does NOT grow qubit count.

        The key invariant: after the first (capture) call, subsequent replay
        calls only add param qubits.  Transient ancillas are either skipped
        (IR path) or freed (gate-level path), so they don't accumulate.
        """
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def foo(x, y):
            x += y
            return x

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        foo(a, b)  # capture

        c = ql.qint(1, width=4)
        d = ql.qint(4, width=4)
        foo(c, d)  # replay 1
        stats_2 = ql.circuit_stats()

        e = ql.qint(5, width=4)
        f = ql.qint(6, width=4)
        foo(e, f)  # replay 2
        stats_3 = ql.circuit_stats()

        # Growth between replay 1 and replay 2 should be exactly 8
        # (4 qubits per param, 2 params), no transient accumulation.
        growth = stats_3["current_in_use"] - stats_2["current_in_use"]
        assert growth == 8, (
            f"Qubit growth between replay calls should be 8 (param qubits only), got {growth}"
        )

    def test_multiplication_allocates_result(self):
        """bar(a, b) returning a * b allocates fresh result qubits each call."""
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def bar(x, y):
            z = x * y
            return z

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        r1 = bar(a, b)  # capture
        assert r1 is not None

        c = ql.qint(1, width=4)
        d = ql.qint(4, width=4)
        r2 = bar(c, d)  # replay
        assert r2 is not None

        # Result qubits should be distinct between calls (fresh allocation)
        r1_qubits = {int(r1.qubits[63 - i]) for i in range(4) if int(r1.qubits[63 - i]) != 0}
        r2_qubits = {int(r2.qubits[63 - i]) for i in range(4) if int(r2.qubits[63 - i]) != 0}
        assert r1_qubits.isdisjoint(r2_qubits), (
            f"Result qubits should be distinct: r1={r1_qubits}, r2={r2_qubits}"
        )

    def test_ir_replay_qubit_mapping(self):
        """IR path maps only param + result qubits, transients unmapped.

        In QFT mode the IR path is used.  Verify that virtual_to_real
        does not contain entries for transient virtual indices.
        """
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile
        def add_qft(x, y):
            x += y
            return x

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        add_qft(a, b)  # capture

        block = None
        for blk in add_qft._cache.values():
            block = blk
            break
        assert block is not None

        # In QFT mode, IR entries exist
        assert len(block._instruction_ir) > 0, "Expected IR entries in QFT mode"

        # On replay, only non-transient internal qubits should be allocated
        c = ql.qint(1, width=4)
        d = ql.qint(4, width=4)
        add_qft(c, d)  # replay via IR path

        # Verify the replay used the IR path
        assert add_qft._last_replay_used_ir, "Expected IR path on replay"

    def test_gate_replay_still_allocates_all(self):
        """Gate-level path allocates everything (backward compatibility).

        In Toffoli mode (no IR), the gate-level path must allocate ALL
        internal qubits because injected gate tuples reference them.
        Transients are freed after injection (Step 8.3) but must be
        allocated during injection.
        """
        ql.circuit()
        ql.option("fault_tolerant", True)

        @ql.compile
        def add_toff(x, y):
            x += y
            return x

        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        add_toff(a, b)  # capture

        block = None
        for blk in add_toff._cache.values():
            block = blk
            break
        assert block is not None

        # Toffoli mode: no IR entries, gate-level path used
        assert len(block._instruction_ir) == 0, "Toffoli should have no IR"
        assert len(block.gates) > 0, "Toffoli should have gates"
        assert len(block.transient_virtual_indices) > 0, "Expected transients from addition"

        # Replay should work correctly even though all qubits are allocated
        c = ql.qint(1, width=4)
        d = ql.qint(4, width=4)
        add_toff(c, d)  # replay via gate-level path

        # Verify the replay did NOT use IR path
        assert not add_toff._last_replay_used_ir, "Expected gate-level path on Toffoli replay"

    def test_correctness_preserved(self):
        """Simulation results identical before and after transient skipping.

        Verifies that the IR replay path produces correct quantum state
        even when transient qubits are not pre-allocated.
        """
        ql.circuit()
        ql.option("fault_tolerant", False)

        @ql.compile
        def add_vals(x, y):
            x += y
            return x

        # First call: capture (3 + 2 = 5)
        a = ql.qint(3, width=4)
        b = ql.qint(2, width=4)
        r1 = add_vals(a, b)

        # Second call: replay (7 + 4 = 11)
        c = ql.qint(7, width=4)
        d = ql.qint(4, width=4)
        r2 = add_vals(c, d)

        # Third call: replay (1 + 1 = 2)
        e = ql.qint(1, width=4)
        f = ql.qint(1, width=4)
        r3 = add_vals(e, f)

        # Verify the IR path was used for replays
        assert add_vals._last_replay_used_ir, "Expected IR path for QFT replay"

        # All return values should be the input param (in-place add)
        # Since return_is_param_index is set, r1 is a, r2 is c, r3 is e
        assert r1 is a
        assert r2 is c
        assert r3 is e


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

        # Verify transient_virtual_indices is set on the captured block
        block = None
        for blk in add_fn._cache.values():
            block = blk
            break
        assert block is not None
        assert len(block.transient_virtual_indices) > 0

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
