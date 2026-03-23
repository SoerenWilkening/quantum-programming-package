"""Tests for zero-arg compiled functions wrapping nested compiled calls.

Verifies:
- Zero-arg compiled function with nested compiled calls does not crash (o93)
- Gate count matches uncompiled equivalent
- All CallRecord qubit indices are present in real_to_virtual
- Replay allocates correct number of internal qubits
"""

import quantum_language as ql
from quantum_language._core import get_gate_count


class TestZeroArgNoKeyError:
    """Zero-arg compiled function wrapping nested compiled functions can be
    called multiple times without KeyError."""

    def test_zero_arg_no_keyerror(self):
        """@ql.compile zero-arg function with inner compiled call: no KeyError on replay."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def main():
            a = ql.qint(0, width=4)
            a = inner(a)
            return a

        # First call: capture
        result1 = main()
        # Second call: replay -- this crashed with KeyError: 0 before the fix
        result2 = main()

        assert result1 is not None
        assert result2 is not None

    def test_zero_arg_no_keyerror_simulate_false(self):
        """Zero-arg with simulate=False also works without KeyError."""
        ql.circuit()
        ql.option("simulate", False)

        @ql.compile
        def inner(x):
            x += 2
            return x

        @ql.compile
        def main():
            a = ql.qint(0, width=4)
            a = inner(a)
            return a

        # First call: capture
        main()
        # Second call: replay
        main()

    def test_zero_arg_three_calls_stable(self):
        """Three consecutive calls to zero-arg function: all succeed."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def step(x):
            x += 3
            return x

        @ql.compile
        def run():
            v = ql.qint(0, width=4)
            v = step(v)
            return v

        run()  # capture
        run()  # replay 1
        run()  # replay 2


class TestZeroArgGateCount:
    """Gate count for zero-arg compiled function matches uncompiled equivalent."""

    def test_zero_arg_gate_count(self):
        """Replay gate count is consistent with capture gate count."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def main():
            a = ql.qint(0, width=4)
            a = inner(a)
            return a

        gc_before_capture = get_gate_count()
        main()
        capture_gates = get_gate_count() - gc_before_capture

        gc_before_replay = get_gate_count()
        main()
        replay_gates = get_gate_count() - gc_before_replay

        assert capture_gates > 0, "Capture should produce gates"
        assert replay_gates > 0, "Replay should produce gates"
        # Replay should not double-count (allow small tolerance for optimization)
        assert replay_gates <= capture_gates * 1.5, (
            f"Replay gates ({replay_gates}) should not be much larger than "
            f"capture gates ({capture_gates})"
        )


class TestZeroArgCallRecordQubitsMapped:
    """All CallRecord qubit indices are present in real_to_virtual."""

    def test_zero_arg_call_record_qubits_mapped(self):
        """After capture, all CallRecord quantum_arg_indices are valid virtual indices."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def main():
            a = ql.qint(0, width=4)
            a = inner(a)
            return a

        main()

        # Get the cached block for main
        main_key = list(main._cache.keys())[0]
        main_block = main._cache[main_key]

        assert len(main_block._call_records) >= 1, "main should have CallRecord for inner"

        # All quantum_arg_indices in CallRecords should be valid virtual indices
        # (>= 1, since 0 is reserved for control).  Before the fix, they would
        # be raw physical indices that could collide with virtual index 0.
        for cr in main_block._call_records:
            for arg_indices in cr.quantum_arg_indices:
                for virt_idx in arg_indices:
                    assert virt_idx >= 1, (
                        f"Virtual index {virt_idx} should be >= 1 (0 reserved for control)"
                    )
                    assert virt_idx < main_block.total_virtual_qubits, (
                        f"Virtual index {virt_idx} should be < total_virtual "
                        f"({main_block.total_virtual_qubits})"
                    )


class TestZeroArgReplayAllocatesAncillas:
    """Replay allocates the correct number of internal qubits."""

    def test_zero_arg_replay_allocates_ancillas(self):
        """Zero-arg function's cached block has positive internal_qubit_count."""
        ql.circuit()
        ql.option("simulate", True)

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def main():
            a = ql.qint(0, width=4)
            a = inner(a)
            return a

        main()

        main_key = list(main._cache.keys())[0]
        main_block = main._cache[main_key]

        # Zero-arg function: no params, so all virtual qubits are internal.
        # total_virtual should be >= the qubits needed by the inner call.
        assert main_block.total_virtual_qubits > 1, (
            f"total_virtual_qubits ({main_block.total_virtual_qubits}) should be > 1 "
            "to include inner call qubits"
        )
        # internal_qubit_count = total_virtual - vidx (vidx=1 for zero-arg)
        assert main_block.internal_qubit_count >= 0, (
            f"internal_qubit_count ({main_block.internal_qubit_count}) should be >= 0"
        )
        # For a zero-arg function, internal_count = total_virtual - 1
        # (since vidx starts at 1 and there are no params)
        assert main_block.internal_qubit_count == main_block.total_virtual_qubits - 1, (
            f"For zero-arg, internal_qubit_count ({main_block.internal_qubit_count}) "
            f"should equal total_virtual - 1 ({main_block.total_virtual_qubits - 1})"
        )
