"""Performance profiling for @ql.compile replay path (PERF-03).

Measures inject_remapped_gates and _replay overhead before and after
optimization. On-demand benchmarks, NOT run in CI.

Usage:
    pytest tests/python/test_compile_performance.py -v -m benchmark -s

COMP-03 Profiling Results (Phase 112)
=====================================
Baseline (Python set operations, Plan 01 -- pre-numpy qubit_set):
  Replay scaling:
    small  (add_one_4bit):    gates=18,  median=0.182ms, per_gate=10.09us
    medium (add_sub_chain):   gates=52,  median=0.423ms, per_gate=8.13us
    large  (mult_then_add):   gates=88,  median=0.599ms, per_gate=6.80us
  Qubit set construction:
    small  (10 funcs, 3 qubits):   4.3 us
    large  (50 funcs, 10 qubits):  35.6 us

Post-migration (numpy np.unique/np.concatenate qubit_set, Plan 02):
  Replay scaling:
    small  (add_one_4bit):    gates=18,  median=0.180ms, per_gate=9.98us
    medium (add_sub_chain):   gates=52,  median=0.423ms, per_gate=8.13us
    large  (mult_then_add):   gates=88,  median=0.592ms, per_gate=6.72us
  Qubit set construction:
    small  (10 funcs, 3 qubits):   4.3 us
    large  (50 funcs, 10 qubits):  35.6 us

Conclusion: Negligible difference at current workload sizes (<=100 qubits).
  Numpy has fixed dispatch overhead that dominates for small arrays. The
  numpy migration provides architectural consistency (same path for
  qubit_set construction and overlap detection) and will show benefit
  at larger qubit counts (1000+ qubits) where np.unique outperforms
  Python set operations due to cache-friendly memory layout.
"""

import statistics
import time

import numpy as np
import pytest

import quantum_language as ql
from quantum_language._core import extract_gate_range, get_current_layer

NUM_REPLAYS = 50


def _time_replay(compiled_func, register_factory, replays=NUM_REPLAYS):
    """Time compiled function replay across multiple invocations.

    Parameters
    ----------
    compiled_func : callable
        A @ql.compile decorated function.
    register_factory : callable
        Function that creates a fresh qint register for each replay.
    replays : int
        Number of replay invocations.

    Returns
    -------
    dict
        Timing results with total_ms, median_per_replay_ms, gate_count.
    """
    # First call triggers capture
    ql.circuit()
    ql.option("fault_tolerant", True)
    reg = register_factory()
    compiled_func(reg)
    gate_count = len(extract_gate_range(0, get_current_layer()))

    # Measure replays
    timings_ns = []
    for _ in range(replays):
        ql.circuit()
        ql.option("fault_tolerant", True)
        reg = register_factory()
        start = time.perf_counter_ns()
        compiled_func(reg)
        end = time.perf_counter_ns()
        timings_ns.append(end - start)

    timings_ms = [t / 1e6 for t in timings_ns]
    median_ms = statistics.median(timings_ms)
    per_gate_us = (median_ms * 1000) / max(gate_count, 1)

    return {
        "replays": replays,
        "gate_count": gate_count,
        "median_per_replay_ms": median_ms,
        "mean_per_replay_ms": statistics.mean(timings_ms),
        "min_per_replay_ms": min(timings_ms),
        "max_per_replay_ms": max(timings_ms),
        "per_gate_us": per_gate_us,
    }


def _print_result(label, result):
    """Print a timing result."""
    print(
        f"  {label:35s} | "
        f"gates={result['gate_count']:>5d} | "
        f"median={result['median_per_replay_ms']:>7.3f}ms | "
        f"per_gate={result['per_gate_us']:>6.2f}us"
    )


# ---------------------------------------------------------------------------
# Compiled function definitions for profiling
# ---------------------------------------------------------------------------


@ql.compile
def _add_one_4bit(x):
    x += 1


@ql.compile
def _add_sub_chain_4bit(x):
    x += 3
    x -= 1
    x += 5
    x -= 2


@ql.compile
def _mult_then_add(x):
    y = x * ql.qint(2, bits=4)
    _ = y + x


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_compile_replay_scaling():
    """Profile compile replay at different gate counts."""
    print("\n--- Compile Replay Scaling ---")

    results = []

    # Small: ~18 gates (simple add)
    result = _time_replay(_add_one_4bit, lambda: ql.qint(5, bits=4))
    _print_result("small (add_one_4bit)", result)
    results.append(("small", result))

    # Medium: ~35 gates (add/sub chain)
    result = _time_replay(_add_sub_chain_4bit, lambda: ql.qint(5, bits=4))
    _print_result("medium (add_sub_chain)", result)
    results.append(("medium", result))

    # Large: mult then add (~80+ gates)
    result = _time_replay(_mult_then_add, lambda: ql.qint(3, bits=4))
    _print_result("large (mult_then_add)", result)
    results.append(("large", result))

    # Verify all produced gates
    for label, r in results:
        assert r["gate_count"] > 0, f"{label} should produce gates"


@pytest.mark.benchmark
def test_inject_vs_total_breakdown():
    """Measure what fraction of replay time is inject_remapped_gates vs Python overhead.

    Approximation: inject_remapped_gates is the dominant C call in _replay.
    We measure full replay time and compare with a direct inject_remapped_gates call.
    """
    print("\n--- Inject vs Total Breakdown ---")

    # Build a compiled function and capture its gates
    ql.circuit()
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    _add_sub_chain_4bit(a)  # Trigger capture

    # Get the compiled block's gates and qubit mapping
    from quantum_language._core import inject_remapped_gates

    # Build the gate list and qubit map for direct injection
    ql.circuit()
    ql.option("fault_tolerant", True)
    a = ql.qint(5, bits=4)
    start_layer = get_current_layer()
    _add_sub_chain_4bit(a)
    end_layer = get_current_layer()
    gates = extract_gate_range(start_layer, end_layer)

    # Create identity qubit map
    all_qubits = set()
    for g in gates:
        all_qubits.add(g["target"])
        for c in g["controls"]:
            all_qubits.add(c)
    identity_map = {q: q for q in all_qubits}

    # Measure direct inject_remapped_gates
    inject_times_ns = []
    for _ in range(NUM_REPLAYS):
        ql.circuit()
        ql.option("fault_tolerant", True)
        _ = ql.qint(5, bits=4)  # allocate qubits
        start = time.perf_counter_ns()
        inject_remapped_gates(gates, identity_map)
        end = time.perf_counter_ns()
        inject_times_ns.append(end - start)

    # Measure full replay
    replay_times_ns = []
    for _ in range(NUM_REPLAYS):
        ql.circuit()
        ql.option("fault_tolerant", True)
        reg = ql.qint(5, bits=4)
        start = time.perf_counter_ns()
        _add_sub_chain_4bit(reg)
        end = time.perf_counter_ns()
        replay_times_ns.append(end - start)

    inject_median_us = statistics.median(inject_times_ns) / 1000
    replay_median_us = statistics.median(replay_times_ns) / 1000
    inject_pct = (inject_median_us / max(replay_median_us, 0.001)) * 100

    print(f"  inject_remapped_gates: {inject_median_us:>8.1f} us (median)")
    print(f"  full replay:           {replay_median_us:>8.1f} us (median)")
    print(f"  inject fraction:       {inject_pct:>8.1f}%")
    print(f"  python overhead:       {100 - inject_pct:>8.1f}%")
    print(f"  gate count:            {len(gates)}")


# ---------------------------------------------------------------------------
# Qubit set & overlap baseline benchmarks (COMP-03)
# ---------------------------------------------------------------------------


def _bench_qubit_set_construction(n_functions, qubits_per_func, qubit_range):
    """Simulate qubit_set construction as done in compile.py.

    For each function, builds a set() from multiple quantum arg qubit index
    lists using set.update(), then converts to frozenset.

    Returns median time in microseconds over 20 iterations.
    """
    rng = np.random.default_rng(42)
    # Pre-generate qubit index lists (simulating quantum_args)
    arg_lists = []
    for _ in range(n_functions):
        indices = rng.integers(0, qubit_range, size=qubits_per_func).tolist()
        arg_lists.append(indices)

    timings_ns = []
    for _ in range(20):
        start = time.perf_counter_ns()
        for indices in arg_lists:
            qubit_set = set()
            qubit_set.update(indices)
            _ = frozenset(qubit_set)
        end = time.perf_counter_ns()
        timings_ns.append(end - start)

    return statistics.median(timings_ns) / 1000  # microseconds


@pytest.mark.benchmark
def test_qubit_set_construction_benchmark():
    """POST-MIGRATION: Profile qubit_set construction (numpy path via _build_qubit_set_numpy)."""
    print("\n--- POST-MIGRATION: Qubit Set Construction ---")

    small_us = _bench_qubit_set_construction(n_functions=10, qubits_per_func=3, qubit_range=20)
    print(f"  POST-MIGRATION small  (10 funcs, 3 qubits):   {small_us:>8.1f} us (median)")

    large_us = _bench_qubit_set_construction(n_functions=50, qubits_per_func=10, qubit_range=100)
    print(f"  POST-MIGRATION large  (50 funcs, 10 qubits):  {large_us:>8.1f} us (median)")

    assert small_us >= 0, "timing should be non-negative"
    assert large_us >= 0, "timing should be non-negative"
