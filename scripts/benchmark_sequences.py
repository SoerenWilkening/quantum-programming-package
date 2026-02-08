"""Benchmark script for measuring hardcoded sequence costs (Phase 62).

Measures three distinct costs:
  BENCH-01: Import time overhead (subprocess-isolated)
  BENCH-02: First-call generation cost per operation/width (subprocess-isolated)
  BENCH-03: Cached dispatch overhead for hardcoded vs dynamic paths (in-process)

All measurements are saved as structured JSON for consumption by Plan 02.

Usage:
    # Run all benchmarks (default)
    PYTHONPATH=src python scripts/benchmark_sequences.py

    # Run specific benchmarks
    PYTHONPATH=src python scripts/benchmark_sequences.py --bench 1
    PYTHONPATH=src python scripts/benchmark_sequences.py --bench 2 --widths 1-4
    PYTHONPATH=src python scripts/benchmark_sequences.py --bench 1,2,3

    # Override iteration counts
    PYTHONPATH=src python scripts/benchmark_sequences.py --iterations 5
"""

import argparse
import glob
import json
import os
import statistics
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Project root detection (same pattern as profile_memory_61.py)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default configuration
DEFAULT_IMPORT_ITERATIONS = 20
DEFAULT_FIRST_CALL_ITERATIONS = 10
DEFAULT_CACHED_ITERATIONS = 50_000
DEFAULT_WIDTH_MIN = 1
DEFAULT_WIDTH_MAX = 16

# Operation definitions for BENCH-02
# Each entry: (name, subprocess_script_template)
# The template receives {width} for substitution.
OPERATIONS = {
    "QQ_add": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "b = ql.qint(1, width={width})\n"
        "start = time.perf_counter_ns()\n"
        "a += b\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "CQ_add": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "start = time.perf_counter_ns()\n"
        "a += 3\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "cQQ_add": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "b = ql.qint(1, width={width})\n"
        "ctrl = ql.qbool(True)\n"
        "start = time.perf_counter_ns()\n"
        "ctrl.__enter__()\n"
        "a += b\n"
        "ctrl.__exit__(None, None, None)\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "cCQ_add": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "ctrl = ql.qbool(True)\n"
        "start = time.perf_counter_ns()\n"
        "ctrl.__enter__()\n"
        "a += 3\n"
        "ctrl.__exit__(None, None, None)\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "QQ_mul": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "b = ql.qint(1, width={width})\n"
        "start = time.perf_counter_ns()\n"
        "c = a * b\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "CQ_mul": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "start = time.perf_counter_ns()\n"
        "c = a * 3\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "Q_xor": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "b = ql.qint(1, width={width})\n"
        "start = time.perf_counter_ns()\n"
        "a ^= b\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "Q_and": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "b = ql.qint(1, width={width})\n"
        "start = time.perf_counter_ns()\n"
        "c = a & b\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
    "Q_or": (
        "import time, quantum_language as ql\n"
        "ql.circuit()\n"
        "a = ql.qint(1, width={width})\n"
        "b = ql.qint(1, width={width})\n"
        "start = time.perf_counter_ns()\n"
        "c = a | b\n"
        "end = time.perf_counter_ns()\n"
        "print(end - start)\n"
    ),
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _subprocess_env():
    """Return environment dict with PYTHONPATH set for quantum_language."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(PROJECT_ROOT, "src")
    return env


def _run_subprocess_script(script, timeout=120):
    """Run a Python script in a clean subprocess and return stdout.

    Returns None on failure (does not crash).
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=_subprocess_env(),
            timeout=timeout,
        )
        if result.returncode != 0:
            stderr_preview = result.stderr[:300] if result.stderr else "(no stderr)"
            print(f"  WARNING: subprocess failed (rc={result.returncode}): {stderr_preview}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  WARNING: subprocess timed out after {timeout}s")
        return None
    except Exception as exc:
        print(f"  WARNING: subprocess error: {exc}")
        return None


def _parse_int_output(output):
    """Parse integer from subprocess output, return None on failure."""
    if output is None:
        return None
    try:
        return int(output.strip())
    except (ValueError, AttributeError):
        return None


def _parse_width_range(widths_str):
    """Parse width range string like '1-16' or '4' into list of ints."""
    if "-" in widths_str:
        parts = widths_str.split("-")
        return list(range(int(parts[0]), int(parts[1]) + 1))
    return [int(widths_str)]


# ---------------------------------------------------------------------------
# BENCH-01: Import Time Measurement
# ---------------------------------------------------------------------------


def bench_01_import_time(iterations=DEFAULT_IMPORT_ITERATIONS):
    """Measure quantum_language import time in clean subprocesses.

    Returns dict with median_ms, mean_ms, stdev_ms, samples, so_file_sizes_bytes.
    """
    print("=" * 60)
    print("BENCH-01: Import Time Measurement")
    print("=" * 60)

    script = (
        "import time; s=time.perf_counter_ns(); "
        "import quantum_language; "
        "print(time.perf_counter_ns()-s)"
    )

    times_ns = []
    for i in range(iterations):
        output = _run_subprocess_script(script, timeout=60)
        val = _parse_int_output(output)
        if val is not None:
            times_ns.append(val)
        if (i + 1) % 5 == 0 or i == 0:
            print(f"  Iteration {i + 1}/{iterations} ...")

    if len(times_ns) < 2:
        print("  ERROR: Not enough successful measurements for import time")
        return {
            "median_ms": None,
            "mean_ms": None,
            "stdev_ms": None,
            "samples": len(times_ns),
            "so_file_sizes_bytes": {},
        }

    median_ms = statistics.median(times_ns) / 1e6
    mean_ms = statistics.mean(times_ns) / 1e6
    stdev_ms = statistics.stdev(times_ns) / 1e6

    # Measure .so file sizes
    so_pattern = os.path.join(PROJECT_ROOT, "src", "quantum_language", "*.so")
    so_files = glob.glob(so_pattern)
    so_sizes = {}
    for f in so_files:
        name = os.path.basename(f)
        so_sizes[name] = os.path.getsize(f)

    total_so_mb = sum(so_sizes.values()) / (1024 * 1024)

    print("\n  Results:")
    print(f"    Median import time: {median_ms:.1f} ms")
    print(f"    Mean import time:   {mean_ms:.1f} ms")
    print(f"    Stdev:              {stdev_ms:.1f} ms")
    print(f"    Successful samples: {len(times_ns)}/{iterations}")
    print(f"    Total .so size:     {total_so_mb:.1f} MB ({len(so_files)} files)")
    for name, size in sorted(so_sizes.items()):
        print(f"      {name}: {size / 1024:.0f} KB")
    print()

    return {
        "median_ms": round(median_ms, 2),
        "mean_ms": round(mean_ms, 2),
        "stdev_ms": round(stdev_ms, 2),
        "samples": len(times_ns),
        "so_file_sizes_bytes": so_sizes,
    }


# ---------------------------------------------------------------------------
# BENCH-02: First-Call Generation Cost
# ---------------------------------------------------------------------------


def bench_02_first_call(widths, iterations=DEFAULT_FIRST_CALL_ITERATIONS):
    """Measure first-call generation cost for all operations at given widths.

    Each measurement uses a clean subprocess (C caches cannot be reset).
    Returns dict mapping operation -> {width_str: median_us, ...}.
    """
    print("=" * 60)
    print("BENCH-02: First-Call Generation Cost")
    print("=" * 60)

    total_measurements = len(OPERATIONS) * len(widths)
    measurement_idx = 0
    results = {}

    for op_name, script_template in OPERATIONS.items():
        results[op_name] = {}

        for width in widths:
            measurement_idx += 1

            # Skip QQ_mul for widths > 16 (safety per MEM-01)
            if op_name == "QQ_mul" and width > 16:
                print(
                    f"  BENCH-02: {op_name} width={width} "
                    f"[{measurement_idx}/{total_measurements}] SKIPPED (width > 16)"
                )
                results[op_name][str(width)] = None
                continue

            print(f"  BENCH-02: {op_name} width={width} [{measurement_idx}/{total_measurements}]")

            script = script_template.format(width=width)
            times_ns = []

            for _ in range(iterations):
                output = _run_subprocess_script(script, timeout=60)
                val = _parse_int_output(output)
                if val is not None:
                    times_ns.append(val)

            if times_ns:
                median_us = statistics.median(times_ns) / 1e3  # ns -> us
                results[op_name][str(width)] = round(median_us, 2)
            else:
                print(f"    WARNING: No successful measurements for {op_name} width={width}")
                results[op_name][str(width)] = None

    # Print summary
    print("\n  Summary (median first-call cost in microseconds):")
    print(f"  {'Operation':<12}", end="")
    for w in widths:
        print(f"  {w:>6}", end="")
    print()
    for op_name in OPERATIONS:
        print(f"  {op_name:<12}", end="")
        for w in widths:
            val = results[op_name].get(str(w))
            if val is not None:
                if val >= 1000:
                    print(f"  {val / 1000:>5.1f}m", end="")
                else:
                    print(f"  {val:>6.0f}", end="")
            else:
                print(f"  {'N/A':>6}", end="")
        print()
    print()

    return results


# ---------------------------------------------------------------------------
# BENCH-03: Cached Dispatch Overhead
# ---------------------------------------------------------------------------


def bench_03_cached_dispatch(iterations=DEFAULT_CACHED_ITERATIONS):
    """Measure cached dispatch overhead for hardcoded vs dynamic paths.

    Compares addition operations at width 8 (hardcoded) vs width 17 (dynamic).
    Runs in-process (cache is what we want to measure).

    Returns dict with per-call nanoseconds.
    """
    print("=" * 60)
    print("BENCH-03: Cached Dispatch Overhead")
    print("=" * 60)

    # Import quantum_language for in-process measurement
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
    import quantum_language as ql

    results = {}

    for op_name, _op_label in [("QQ_add", "a += b"), ("CQ_add", "a += 3")]:
        results[op_name] = {}

        for width, tag in [(8, "8_hardcoded"), (17, "17_dynamic")]:
            # Create fresh circuit and operands
            ql.circuit()
            a = ql.qint(0, width=width)
            if op_name == "QQ_add":
                b = ql.qint(0, width=width)

            # Warm up -- trigger first-call generation/cache fill
            if op_name == "QQ_add":
                a += b
            else:
                a += 3

            # Measure many iterations of cached dispatch
            start = time.perf_counter_ns()
            if op_name == "QQ_add":
                for _ in range(iterations):
                    a += b
            else:
                for _ in range(iterations):
                    a += 3
            elapsed = time.perf_counter_ns() - start

            ns_per_call = elapsed / iterations
            results[op_name][tag] = round(ns_per_call, 1)

            print(
                f"  {op_name} width={width} ({tag}): "
                f"{ns_per_call:.1f} ns/call "
                f"({ns_per_call / 1000:.2f} us/call) "
                f"[{iterations} iterations]"
            )

    # Print comparison
    print("\n  Dispatch overhead comparison:")
    for op_name in results:
        hc = results[op_name].get("8_hardcoded", 0)
        dyn = results[op_name].get("17_dynamic", 0)
        if hc and dyn:
            diff = dyn - hc
            pct = (diff / hc * 100) if hc > 0 else 0
            print(
                f"    {op_name}: hardcoded={hc:.1f}ns, dynamic={dyn:.1f}ns, "
                f"diff={diff:+.1f}ns ({pct:+.1f}%)"
            )
    print()

    return results


# ---------------------------------------------------------------------------
# Output / JSON
# ---------------------------------------------------------------------------


def save_results(bench_01_data, bench_02_data, bench_03_data, output_path):
    """Save all benchmark results to JSON file."""
    data = {
        "bench_01_import_time": bench_01_data or {},
        "bench_02_first_call_us": bench_02_data or {},
        "bench_03_cached_dispatch_ns": bench_03_data or {},
        "metadata": {
            "python_version": sys.version,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project_root": PROJECT_ROOT,
            "iterations": {
                "import_time": DEFAULT_IMPORT_ITERATIONS,
                "first_call": DEFAULT_FIRST_CALL_ITERATIONS,
                "cached_dispatch": DEFAULT_CACHED_ITERATIONS,
            },
        },
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Results saved to: {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark hardcoded sequence costs (Phase 62)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--bench",
        type=str,
        default="1,2,3",
        help="Which benchmarks to run (default: '1,2,3'). "
        "E.g., '1' for import only, '2,3' for first-call and cached dispatch.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Override default iteration count for all benchmarks.",
    )
    parser.add_argument(
        "--widths",
        type=str,
        default=f"{DEFAULT_WIDTH_MIN}-{DEFAULT_WIDTH_MAX}",
        help=f"Width range for BENCH-02 (default: '{DEFAULT_WIDTH_MIN}-{DEFAULT_WIDTH_MAX}'). "
        "E.g., '1-4' or '8'.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(PROJECT_ROOT, "benchmarks", "results", "bench_raw.json"),
        help="Output JSON file path.",
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    benches = {int(b.strip()) for b in args.bench.split(",")}
    widths = _parse_width_range(args.widths)

    print("Phase 62: Benchmark Sequences")
    print("=" * 60)
    print(f"  Benchmarks: {sorted(benches)}")
    print(f"  Widths:     {widths[0]}-{widths[-1]} ({len(widths)} widths)")
    print(f"  Python:     {sys.version.split()[0]}")
    print(f"  Project:    {PROJECT_ROOT}")
    print(f"  Output:     {args.output}")
    print()

    bench_01_data = None
    bench_02_data = None
    bench_03_data = None

    total_start = time.perf_counter_ns()

    # BENCH-01: Import time
    if 1 in benches:
        iters = args.iterations if args.iterations else DEFAULT_IMPORT_ITERATIONS
        bench_01_data = bench_01_import_time(iterations=iters)

    # BENCH-02: First-call generation cost
    if 2 in benches:
        iters = args.iterations if args.iterations else DEFAULT_FIRST_CALL_ITERATIONS
        bench_02_data = bench_02_first_call(widths, iterations=iters)

    # BENCH-03: Cached dispatch overhead
    if 3 in benches:
        iters = args.iterations if args.iterations else DEFAULT_CACHED_ITERATIONS
        bench_03_data = bench_03_cached_dispatch(iterations=iters)

    total_elapsed_s = (time.perf_counter_ns() - total_start) / 1e9

    # Save results
    save_results(bench_01_data, bench_02_data, bench_03_data, args.output)

    # Final summary
    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Total time: {total_elapsed_s:.1f}s")
    if bench_01_data and bench_01_data.get("median_ms"):
        print(f"  Import time: {bench_01_data['median_ms']:.1f} ms (median)")
    if bench_02_data:
        # Print a few key values
        for op in ["QQ_add", "QQ_mul", "Q_xor"]:
            val = bench_02_data.get(op, {}).get("8")
            if val is not None:
                print(f"  {op}@8: {val:.0f} us (first-call)")
    if bench_03_data:
        for op in bench_03_data:
            hc = bench_03_data[op].get("8_hardcoded")
            dyn = bench_03_data[op].get("17_dynamic")
            if hc and dyn:
                print(f"  {op} dispatch: {hc:.0f}ns (hardcoded) vs {dyn:.0f}ns (dynamic)")


if __name__ == "__main__":
    main()
