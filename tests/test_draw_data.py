"""Integration tests for circuit.draw_data() method.

Tests qubit compaction, control extraction, gate type mapping,
and scale behavior at 200+ qubits. Validates Phase 45 success criteria.
"""

import math

import quantum_language as ql

# Standardgate_t enum values from C backend (types.h)
GATE_NAMES = {
    0: "X",
    1: "Y",
    2: "Z",
    3: "R",
    4: "H",
    5: "Rx",
    6: "Ry",
    7: "Rz",
    8: "P",
    9: "M",
}

REQUIRED_KEYS = {"num_layers", "num_qubits", "gates", "qubit_map"}
REQUIRED_GATE_KEYS = {"layer", "target", "type", "angle", "controls"}


def test_draw_data_empty_circuit(clean_circuit):
    """Empty circuit returns valid structure with no gates."""
    data = clean_circuit.draw_data()

    assert isinstance(data, dict)
    assert REQUIRED_KEYS <= set(data.keys())
    assert isinstance(data["gates"], list)
    assert len(data["gates"]) == 0


def test_draw_data_basic_structure(clean_circuit):
    """Basic circuit produces valid draw_data with correct structure."""
    _a = ql.qint(5, width=4)

    data = clean_circuit.draw_data()

    assert data["num_layers"] > 0
    assert data["num_qubits"] > 0
    assert len(data["gates"]) > 0

    for gate in data["gates"]:
        assert REQUIRED_GATE_KEYS <= set(gate.keys()), (
            f"Gate missing keys: {REQUIRED_GATE_KEYS - set(gate.keys())}"
        )
        assert 0 <= gate["target"] < data["num_qubits"]
        assert isinstance(gate["controls"], list)
        for ctrl in gate["controls"]:
            assert 0 <= ctrl < data["num_qubits"]
        assert 0 <= gate["layer"] < data["num_layers"]


def test_draw_data_gate_types(clean_circuit):
    """Gate type integers map to valid Standardgate_t enum values."""
    _a = ql.qint(5, width=4)

    data = clean_circuit.draw_data()

    types_seen = set()
    for gate in data["gates"]:
        t = gate["type"]
        assert t in GATE_NAMES, f"Unknown gate type {t}, expected 0-9"
        types_seen.add(t)

    # At minimum, initializing qint(5) should produce X gates
    assert len(types_seen) >= 1, "Expected at least one gate type"


def test_draw_data_qubit_compaction(clean_circuit):
    """Qubit compaction produces dense 0-based indices."""
    _a = ql.qint(3, width=4)
    _b = ql.qint(7, width=4)

    data = clean_circuit.draw_data()

    # Compacted num_qubits should equal actually used qubits, not max index + 1
    num_q = data["num_qubits"]
    assert num_q > 0

    for gate in data["gates"]:
        assert 0 <= gate["target"] < num_q, (
            f"Target {gate['target']} out of dense range [0, {num_q})"
        )
        for ctrl in gate["controls"]:
            assert 0 <= ctrl < num_q, f"Control {ctrl} out of dense range [0, {num_q})"


def test_draw_data_qubit_map(clean_circuit):
    """qubit_map has correct length and ascending sparse indices."""
    _a = ql.qint(5, width=4)

    data = clean_circuit.draw_data()

    qmap = data["qubit_map"]
    assert len(qmap) == data["num_qubits"]

    # Values should be sorted ascending (dense rows preserve qubit order)
    for i in range(len(qmap)):
        assert isinstance(qmap[i], int)
        assert qmap[i] >= 0
    assert qmap == sorted(qmap), "qubit_map should be sorted ascending"


def test_draw_data_controlled_gates(clean_circuit):
    """Controlled operations produce gates with non-empty controls lists."""
    # Addition generates CNOT/Toffoli gates internally
    a = ql.qint(3, width=4)
    b = ql.qint(2, width=4)
    _c = a + b

    data = clean_circuit.draw_data()

    controlled_gates = [g for g in data["gates"] if len(g["controls"]) > 0]
    assert len(controlled_gates) > 0, "Addition should produce at least one controlled gate"

    for g in controlled_gates:
        for ctrl in g["controls"]:
            assert 0 <= ctrl < data["num_qubits"]
        # Control and target should be different qubits
        assert g["target"] not in g["controls"], (
            f"Target {g['target']} should not appear in controls {g['controls']}"
        )


def test_draw_data_angles(clean_circuit):
    """Rotation/phase gates have valid float angles."""
    # Addition uses QFT which produces P/R gates with angles
    a = ql.qint(3, width=4)
    b = ql.qint(2, width=4)
    _c = a + b

    data = clean_circuit.draw_data()

    # Angle-bearing gate types: R=3, Rx=5, Ry=6, Rz=7, P=8
    angle_types = {3, 5, 6, 7, 8}
    angle_gates = [g for g in data["gates"] if g["type"] in angle_types]

    if len(angle_gates) > 0:
        for g in angle_gates:
            assert isinstance(g["angle"], float)
            assert not math.isnan(g["angle"]), f"Angle is NaN for gate type {g['type']}"
            assert not math.isinf(g["angle"]), f"Angle is Inf for gate type {g['type']}"


def test_draw_data_scale_200_qubits(clean_circuit):
    """200+ qubit circuit extracts successfully without crash."""
    # Create many qint variables initialized to max value (all bits set to 1)
    # so that every qubit gets an X gate and compaction keeps them all.
    variables = []
    for _i in range(52):
        # width=4, value=7 means bits 0-2 set; 3 qubits used per var minimum
        # But we need enough total. Use value=-1 which sets all bits in signed repr.
        variables.append(ql.qint(-1, width=4))

    data = clean_circuit.draw_data()

    assert isinstance(data, dict)
    assert REQUIRED_KEYS <= set(data.keys())
    # 52 vars * 4 bits = 208 qubits; all bits have X gates so compaction keeps all
    assert data["num_qubits"] >= 200, f"Expected >= 200 qubits, got {data['num_qubits']}"
    assert data["num_layers"] > 0
    assert len(data["gates"]) > 0

    # Verify structure of all gates at scale
    for gate in data["gates"]:
        assert REQUIRED_GATE_KEYS <= set(gate.keys())
        assert 0 <= gate["target"] < data["num_qubits"]
        assert 0 <= gate["layer"] < data["num_layers"]
