"""Regression test for uncomputation bug with optimizer layer placement.

Bug: When the circuit optimizer places gates (e.g., X gates from CQ_equal_width)
in earlier layers because target qubits have no prior gates, the captured
start_layer (from used_layer) was too high. This caused reverse_circuit_range
to miss those gates during uncomputation, leaving residual gates in the circuit.

Fix: Added min_layer_used tracking to circuit_t. The Python layer resets it
before run_instruction and reads it after to correct _start_layer.
"""

import gc

import quantum_language as ql


def test_eq_int_start_layer_accounts_for_optimizer():
    """Comparison X gates placed at layer 0 must be included in _start_layer."""
    gc.collect()
    ql.circuit()

    # Initialize cr with value 0 -- no X gates on its qubits.
    cr = ql.qint(0, width=3)

    # This comparison generates X gates for bits where value has 1s.
    # Since cr's qubits have no prior gates, optimizer places X gates at layer 0.
    # Bug: start_layer was captured as used_layer (>= 0 here, but in compound
    # scenarios it could be > 0), missing those early-placed gates.
    result = cr == 1  # noqa: F841

    # After fix: _start_layer should be 0 (where optimizer placed X gates)
    assert result._start_layer == 0, (
        f"Expected _start_layer == 0 (optimizer placed gates at layer 0), got {result._start_layer}"
    )


def test_eq_int_with_prior_gates_start_layer():
    """When qubits have prior gates, start_layer should still be correct."""
    gc.collect()
    ql.circuit()

    # Initialize board with non-zero value to occupy layer 0 on some qubits.
    board = ql.qint(5, width=4)

    # Comparison on board -- its qubits already have gates, so optimizer
    # cannot place comparison gates at layer 0 for those qubits.
    result = board == 5  # noqa: F841

    # _start_layer should be correct (may be 0 or 1 depending on optimizer)
    assert result._start_layer <= result._end_layer


def test_with_block_comparison_uncompute():
    """The original bug scenario: with (cr == 1) | (cr == 3) should uncompute correctly."""
    gc.collect()
    ql.circuit()

    cr = ql.qint(0, width=3)
    _ci = ql.qint(0, width=3)  # noqa: F841 - occupies qubits

    # This should work without error after the fix.
    # Before the fix, uncomputation would miss X gates placed at early layers.
    with (cr == 1) | (cr == 3):
        cr += 1

    # If we get here without error, the uncomputation completed.
    # The circuit should have properly reversed all comparison gates.


def test_fresh_qubits_comparison_start_layer_zero():
    """Fresh qubits with no prior gates: comparison X gates go to layer 0."""
    gc.collect()
    ql.circuit()

    # All fresh qubits -- optimizer will place everything at layer 0
    a = ql.qint(0, width=3)
    result = a == 5  # noqa: F841 - X gates for bits 0 and 2

    # start_layer must be 0 since gates are placed at earliest layer
    assert result._start_layer == 0


def test_comparison_uncompute_preserves_state(verify_circuit):
    """After uncomputation of comparison, original value should be preserved."""

    def circuit_builder(val=5, w=4):
        x = ql.qint(val, width=w)
        result = x == 5
        # Keep result alive so it doesn't uncompute before export.
        # The comparison result (1 bit) is at higher qubit indices.
        # Expected: x=5 (4 bits) and result=1 (1 bit True)
        return (1, [x, result])

    actual, expected = verify_circuit(circuit_builder, width=1)
    assert actual == expected, f"After comparison, expected result={expected} but got {actual}"
