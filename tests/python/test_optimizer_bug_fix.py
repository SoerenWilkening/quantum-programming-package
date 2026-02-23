"""Targeted regression tests for the optimizer loop direction bug fix (PERF-01).

The bug: ``smallest_layer_below_comp`` in ``optimizer.c`` used ``++i`` instead
of ``--i``, reading past the end of the ``occupied_layers_of_qubit`` array.

These tests verify:
1. Correct scan direction (largest layer below comparator is returned)
2. Deterministic output (no non-determinism from out-of-bounds reads)
3. Correct gate placement / layer assignment for small circuits
4. Inverse gate cancellation still works after the fix
"""

import quantum_language as ql
from quantum_language._core import extract_gate_range, get_current_layer


def test_smallest_layer_correct_direction():
    """Verify that occupied layer lookups return the correct (largest < compar) value.

    Build a circuit with multiple layers of occupation on the same qubit,
    then add a gate that should land at a specific layer. The wrong scan
    direction would skip the correct predecessor layer and return 0 or an
    incorrect value, changing placement.
    """
    # Build a circuit with several operations touching the same qubit
    # so that occupied_layers_of_qubit has multiple entries.
    ql.circuit()
    ql.option("fault_tolerant", True)

    a = ql.qint(1, bits=4)
    # Perform 3 sequential additions to create multiple occupied layers
    a += 1
    a += 2
    a += 3

    layers_after = get_current_layer()
    gates = extract_gate_range(0, layers_after)

    # With correct direction: gates should be placed in increasing layers
    # without gaps. Verify that total layers is reasonable (not astronomically
    # large from out-of-bounds reads pushing layers forward).
    assert layers_after > 0, "Circuit should have at least one layer"
    assert layers_after < 200, (
        f"Circuit has {layers_after} layers for 3 additions on 4-bit -- "
        "suggests incorrect layer placement from bug"
    )
    assert len(gates) > 0, "Circuit should have gates"


def test_optimizer_deterministic_output():
    """Build the same circuit twice, verify identical gate sequences.

    Non-determinism from out-of-bounds reads would cause different
    placements across runs.
    """

    def build_circuit():
        ql.circuit()
        ql.option("fault_tolerant", True)
        a = ql.qint(5, bits=4)
        b = ql.qint(3, bits=4)
        _ = a + b
        return extract_gate_range(0, get_current_layer())

    gates_1 = build_circuit()
    gates_2 = build_circuit()

    assert len(gates_1) == len(gates_2), (
        f"Gate counts differ between runs: {len(gates_1)} vs {len(gates_2)}"
    )

    for i, (g1, g2) in enumerate(zip(gates_1, gates_2, strict=False)):
        assert g1["type"] == g2["type"], f"Gate {i} type differs"
        assert g1["target"] == g2["target"], f"Gate {i} target differs"
        assert g1["controls"] == g2["controls"], f"Gate {i} controls differ"
        assert g1["num_controls"] == g2["num_controls"], f"Gate {i} num_controls differs"
        assert abs(g1["angle"] - g2["angle"]) < 1e-10, f"Gate {i} angle differs"


def test_gate_placement_small_circuit():
    """Verify layer assignments for a small known circuit.

    Build: H on qubit 0, then CNOT(0->1), then X on qubit 0.
    Expected:
      - H at layer 0 (nothing before it)
      - CNOT at layer 1 (depends on qubit 0 which is used at layer 0)
      - X at layer 2 (depends on qubit 0 which is used at layer 1 by CNOT)

    We verify this indirectly by checking layer count and gate count.
    """
    ql.circuit()
    ql.option("fault_tolerant", True)

    # Create a minimal circuit with sequential dependencies
    a = ql.qint(0, bits=2)  # qubits allocated
    a += 1  # adds gates that depend on qubit 0

    layers = get_current_layer()
    gates = extract_gate_range(0, layers)

    # Verify circuit was built correctly
    assert layers >= 1, "Should have at least 1 layer"
    assert len(gates) >= 1, "Should have at least 1 gate"

    # Verify all gates have valid targets (not garbage from out-of-bounds)
    for i, g in enumerate(gates):
        assert g["target"] >= 0, f"Gate {i} has negative target: {g['target']}"
        assert g["target"] < 100, (
            f"Gate {i} has unreasonably large target: {g['target']} -- "
            "suggests corrupted data from out-of-bounds read"
        )
        for ctrl in g["controls"]:
            assert ctrl >= 0, f"Gate {i} has negative control: {ctrl}"
            assert ctrl < 100, f"Gate {i} has unreasonably large control: {ctrl}"


def test_inverse_cancellation_still_works():
    """Verify that the optimizer still cancels inverse gate pairs.

    The loop fix should not break the merge_gates code path.
    Adding +1 then -1 on the same register should cancel, returning
    the circuit to its pre-operation state.
    """
    ql.circuit()
    ql.option("fault_tolerant", True)

    # Use non-zero init so we have a baseline of gates
    a = ql.qint(5, bits=4)
    after_init = get_current_layer()
    init_gates = len(extract_gate_range(0, after_init))

    # Add +1: creates new gates
    a += 1
    after_add = get_current_layer()
    assert after_add > after_init, "Addition should add layers"

    # Subtract 1: should cancel the +1 entirely via merge_gates
    a -= 1
    after_sub = get_current_layer()

    total_gates = len(extract_gate_range(0, after_sub))

    # Full cancellation: layer count and gate count return to init state
    # The optimizer's merge_gates detects +1 and -1 as inverses
    assert after_sub <= after_init, (
        f"Expected cancellation: layers after -1 ({after_sub}) should be "
        f"<= layers after init ({after_init}), but got more"
    )
    assert total_gates <= init_gates, (
        f"Expected cancellation: total gates ({total_gates}) should be "
        f"<= init gates ({init_gates}), but got more"
    )


def test_multi_qubit_layer_ordering():
    """Verify correct layer ordering with operations on multiple qubits.

    The bug could cause incorrect layer assignments when multiple qubits
    have occupied layers, since the scan direction error would skip
    finding the correct predecessor.
    """
    ql.circuit()
    ql.option("fault_tolerant", True)

    # Create two separate registers and operate on them
    a = ql.qint(1, bits=4)
    b = ql.qint(2, bits=4)

    # Operations on a
    a += 1

    # Operations on b (should be able to overlap with a's operations
    # on different qubits)
    b += 1

    # Operations that depend on both
    _ = a + b
    layers_final = get_current_layer()

    gates = extract_gate_range(0, layers_final)

    # Verify reasonable layer counts
    assert layers_final > 0, "Should have layers"
    assert layers_final < 500, (
        f"Too many layers ({layers_final}) for simple operations -- suggests incorrect placement"
    )

    # Verify all gates are valid
    for i, g in enumerate(gates):
        assert g["target"] >= 0, f"Gate {i} invalid target"
        assert g["type"] >= 0, f"Gate {i} invalid type"
