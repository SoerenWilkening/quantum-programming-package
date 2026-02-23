"""Golden-master snapshot tests for the circuit optimizer.

Captures circuit gate sequences as JSON fixtures and compares against them
to detect regressions during optimizer changes (binary search, replay opts).

Usage:
    # Generate golden-master files (manual, not in CI):
    pytest tests/python/test_optimizer_golden_master.py -v -k golden_master_gen -m golden_master_gen

    # Verify golden-masters match current output (normal CI):
    pytest tests/python/test_optimizer_golden_master.py -v -k verify_golden_masters
"""

import json
from pathlib import Path

import pytest

import quantum_language as ql
from quantum_language._core import extract_gate_range, get_current_layer

# Directory for golden-master JSON files
GOLDEN_MASTERS_DIR = Path(__file__).parent.parent / "golden_masters"


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------


def capture_circuit_snapshot(name, setup_func):
    """Build a circuit and capture its gate sequence as a snapshot dict.

    Parameters
    ----------
    name : str
        Human-readable circuit name.
    setup_func : callable
        Function that builds the circuit (called after ``ql.circuit()``).

    Returns
    -------
    dict
        Snapshot with ``circuit_name``, ``total_gates``, ``total_layers``,
        and ``gates`` (list of gate dicts from ``extract_gate_range``).
    """
    ql.circuit()
    setup_func()
    layer_count = get_current_layer()
    gates = extract_gate_range(0, layer_count)
    return {
        "circuit_name": name,
        "total_gates": len(gates),
        "total_layers": layer_count,
        "gates": gates,
    }


def save_golden_master(name, snapshot):
    """Write a snapshot dict to ``tests/golden_masters/<name>.json``."""
    GOLDEN_MASTERS_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDEN_MASTERS_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)


def load_golden_master(name):
    """Read a snapshot dict from ``tests/golden_masters/<name>.json``."""
    path = GOLDEN_MASTERS_DIR / f"{name}.json"
    with open(path) as f:
        return json.load(f)


def compare_snapshots(expected, actual):
    """Compare two snapshot dicts gate-by-gate.

    Returns
    -------
    str or None
        A human-readable diff string if they differ, otherwise ``None``.
    """
    diffs = []
    name = expected.get("circuit_name", "unknown")

    if expected["total_gates"] != actual["total_gates"]:
        diffs.append(
            f"[{name}] total_gates: expected {expected['total_gates']}, got {actual['total_gates']}"
        )

    if expected["total_layers"] != actual["total_layers"]:
        diffs.append(
            f"[{name}] total_layers: expected {expected['total_layers']}, "
            f"got {actual['total_layers']}"
        )

    min_len = min(len(expected["gates"]), len(actual["gates"]))
    for i in range(min_len):
        eg = expected["gates"][i]
        ag = actual["gates"][i]
        for key in ("type", "target", "num_controls", "controls"):
            if eg.get(key) != ag.get(key):
                diffs.append(f"[{name}] gate {i} {key}: expected {eg.get(key)}, got {ag.get(key)}")
        # Angles compared with tolerance for floating-point
        if abs(eg.get("angle", 0.0) - ag.get("angle", 0.0)) > 1e-10:
            diffs.append(
                f"[{name}] gate {i} angle: expected {eg.get('angle')}, got {ag.get('angle')}"
            )

    if len(expected["gates"]) != len(actual["gates"]):
        diffs.append(
            f"[{name}] gate count: expected {len(expected['gates'])}, got {len(actual['gates'])}"
        )

    return "\n".join(diffs) if diffs else None


# ---------------------------------------------------------------------------
# Representative circuit builders
# ---------------------------------------------------------------------------


def _setup_add_2bit_toffoli():
    ql.option("fault_tolerant", True)
    a = ql.qint(1, bits=2)
    b = ql.qint(1, bits=2)
    _ = a + b


def _setup_add_4bit_toffoli():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a + b


def _setup_add_8bit_toffoli():
    ql.option("fault_tolerant", True)
    a = ql.qint(100, bits=8)
    b = ql.qint(50, bits=8)
    _ = a + b


def _setup_sub_4bit():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a - b


def _setup_mult_2bit():
    ql.option("fault_tolerant", True)
    a = ql.qint(1, bits=2)
    b = ql.qint(1, bits=2)
    _ = a * b


def _setup_mult_4bit():
    ql.option("fault_tolerant", True)
    a = ql.qint(3, bits=4)
    b = ql.qint(2, bits=4)
    _ = a * b


def _setup_lt_4bit():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a < b


def _setup_eq_4bit():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a == b


def _setup_xor_4bit():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a ^ b


def _setup_and_4bit():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a & b


def _setup_qft_add_4bit():
    ql.option("fault_tolerant", False)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a + b


def _setup_qft_add_8bit():
    ql.option("fault_tolerant", False)
    a = ql.qint(100, bits=8)
    b = ql.qint(50, bits=8)
    _ = a + b


def _setup_grover_3q():
    ql.option("fault_tolerant", True)

    @ql.compile
    def equals_five(x):
        return x == 5

    ql.grover(equals_five, width=3, iterations=1)


def _setup_compiled_add_one():
    ql.option("fault_tolerant", True)

    @ql.compile
    def add_one(x):
        x += 1

    a = ql.qint(5, bits=4)
    add_one(a)


def _setup_controlled_add():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    _ = ql.qint(3, bits=4)
    ctrl = ql.qbool(True)
    with ctrl:
        a += 1


def _setup_mixed_add_sub():
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    a += 3
    a -= 2


def _setup_add_const_4bit():
    """Addition with a constant (different code path than variable add)."""
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    a += 7


def _setup_sub_const_4bit():
    """Subtraction of a constant."""
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    a -= 3


def _setup_chained_ops_4bit():
    """Multiple chained operations on same register."""
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    a += 1
    a += 2
    a += 3
    a -= 1


def _setup_qft_sub_4bit():
    """QFT-mode subtraction."""
    ql.option("fault_tolerant", False)
    a = ql.qint(5, bits=4)
    b = ql.qint(3, bits=4)
    _ = a - b


# ---------------------------------------------------------------------------
# Registry: name -> builder function
# ---------------------------------------------------------------------------

CIRCUIT_REGISTRY = {
    "add_2bit_toffoli": _setup_add_2bit_toffoli,
    "add_4bit_toffoli": _setup_add_4bit_toffoli,
    "add_8bit_toffoli": _setup_add_8bit_toffoli,
    "sub_4bit_toffoli": _setup_sub_4bit,
    "mult_2bit_toffoli": _setup_mult_2bit,
    "mult_4bit_toffoli": _setup_mult_4bit,
    "lt_4bit_toffoli": _setup_lt_4bit,
    "eq_4bit_toffoli": _setup_eq_4bit,
    "xor_4bit_toffoli": _setup_xor_4bit,
    "and_4bit_toffoli": _setup_and_4bit,
    "qft_add_4bit": _setup_qft_add_4bit,
    "qft_add_8bit": _setup_qft_add_8bit,
    "qft_sub_4bit": _setup_qft_sub_4bit,
    "grover_3q": _setup_grover_3q,
    "compiled_add_one": _setup_compiled_add_one,
    "controlled_add_4bit": _setup_controlled_add,
    "mixed_add_sub_4bit": _setup_mixed_add_sub,
    "add_const_4bit": _setup_add_const_4bit,
    "sub_const_4bit": _setup_sub_const_4bit,
    "chained_ops_4bit": _setup_chained_ops_4bit,
}


# ---------------------------------------------------------------------------
# Golden-master generation (manual only)
# ---------------------------------------------------------------------------


@pytest.mark.golden_master_gen
def test_generate_golden_masters():
    """Generate golden-master JSON fixtures for all registered circuits.

    Run manually:
        pytest tests/python/test_optimizer_golden_master.py -v \
            -k golden_master_gen -m golden_master_gen
    """
    for name, builder in CIRCUIT_REGISTRY.items():
        snapshot = capture_circuit_snapshot(name, builder)
        save_golden_master(name, snapshot)
        print(
            f"  generated {name}: {snapshot['total_gates']} gates, "
            f"{snapshot['total_layers']} layers"
        )

    # Verify files were written
    for name in CIRCUIT_REGISTRY:
        path = GOLDEN_MASTERS_DIR / f"{name}.json"
        assert path.exists(), f"Golden master not created: {path}"

    print(f"\n  {len(CIRCUIT_REGISTRY)} golden-master files written to {GOLDEN_MASTERS_DIR}")


# ---------------------------------------------------------------------------
# Golden-master verification (CI / normal pytest)
# ---------------------------------------------------------------------------


def _golden_master_names():
    """Return list of golden-master names that have committed JSON files."""
    if not GOLDEN_MASTERS_DIR.exists():
        return []
    return [p.stem for p in sorted(GOLDEN_MASTERS_DIR.glob("*.json")) if p.stem in CIRCUIT_REGISTRY]


@pytest.mark.parametrize("circuit_name", _golden_master_names())
def test_verify_golden_masters(circuit_name):
    """Verify that current circuit output matches committed golden-master.

    Parametrized over all committed golden-master JSON files.
    Fails if any gate sequence differs from the snapshot.
    """
    builder = CIRCUIT_REGISTRY[circuit_name]
    expected = load_golden_master(circuit_name)
    actual = capture_circuit_snapshot(circuit_name, builder)

    diff = compare_snapshots(expected, actual)
    assert diff is None, f"Golden-master mismatch for '{circuit_name}':\n{diff}"
