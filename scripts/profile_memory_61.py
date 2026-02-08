"""Memory profiling script for Phase 61 optimization.

Exercises the three hot-path operations (add, mul, xor) at configurable
bit widths to capture allocation patterns with memray.

Usage:
    # Direct run (for quick check)
    PYTHONPATH=src python scripts/profile_memory_61.py 8

    # With memray profiling
    PYTHONPATH=src memray run -o /tmp/memray_61_8bit.bin -- python scripts/profile_memory_61.py 8

    # With native C tracking
    PYTHONPATH=src memray run --native -o /tmp/memray_61_8bit.bin -- python scripts/profile_memory_61.py 8
"""

import argparse
import sys
import time


def get_gate_t_size():
    """Estimate gate_t struct size based on types.h definition.

    gate_t contains:
        qubit_t Control[2]  = 2 * 4 = 8 bytes  (unsigned int)
        qubit_t *large_control = 8 bytes (pointer, 64-bit)
        num_t NumControls   = 4 bytes  (unsigned int)
        Standardgate_t Gate = 4 bytes  (enum/int)
        double GateValue    = 8 bytes
        qubit_t Target      = 4 bytes  (unsigned int)
        num_t NumBasisGates = 4 bytes  (unsigned int)
    Total raw = 40 bytes, with alignment likely 40-48 bytes.
    """
    return 40  # Conservative estimate from types.h


def run_addition_phase(width, iterations):
    """Run in-place addition for N iterations.

    Uses iadd (+=) which is the hot path migrated in Phase 60.
    This exercises run_instruction() and the optimizer pipeline.
    """
    import quantum_language as ql

    ql.circuit()
    a = ql.qint(5, width=width)
    b = ql.qint(3, width=width)

    start = time.perf_counter()
    for _ in range(iterations):
        a += b
    elapsed = time.perf_counter() - start

    print(
        f"  Addition ({width}-bit): {iterations} iterations in {elapsed:.3f}s "
        f"({iterations / elapsed:.0f} ops/s)"
    )
    return elapsed


def run_multiplication_phase(width, iterations):
    """Run multiplication for N iterations.

    Uses pedantic setup (fresh circuit each time) since multiplication
    allocates new qubits per call.

    Note: 32-bit multiplication causes a segfault in the C backend
    (buffer overflow in circuit allocation). We cap at 24-bit for safety.
    """
    import quantum_language as ql

    if width > 24:
        print(f"  Multiplication ({width}-bit): SKIPPED (segfault at width > 24)")
        print("    Running at 24-bit instead for scaling comparison")
        width = 24

    start = time.perf_counter()
    for _ in range(iterations):
        ql.circuit()
        a = ql.qint(5, width=width)
        b = ql.qint(3, width=width)
        _ = a * b
    elapsed = time.perf_counter() - start

    print(
        f"  Multiplication ({width}-bit): {iterations} iterations in {elapsed:.3f}s "
        f"({iterations / elapsed:.0f} ops/s)"
    )
    return elapsed


def run_xor_phase(width, iterations):
    """Run in-place XOR for N iterations.

    Uses ixor (^=) which is the hot path migrated in Phase 60.
    """
    import quantum_language as ql

    ql.circuit()
    a = ql.qint(5, width=width)
    b = ql.qint(3, width=width)

    start = time.perf_counter()
    for _ in range(iterations):
        a ^= b
    elapsed = time.perf_counter() - start

    print(
        f"  XOR ({width}-bit): {iterations} iterations in {elapsed:.3f}s "
        f"({iterations / elapsed:.0f} ops/s)"
    )
    return elapsed


def main():
    parser = argparse.ArgumentParser(description="Memory profiling for Phase 61 optimization")
    parser.add_argument(
        "width", type=int, nargs="?", default=8, help="Bit width for operations (default: 8)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per operation (default: 100)",
    )
    args = parser.parse_args()

    width = args.width
    iterations = args.iterations

    print("Phase 61 Memory Profiling")
    print("========================")
    print(f"Width: {width}-bit")
    print(f"Iterations: {iterations}")
    print(f"Estimated gate_t size: {get_gate_t_size()} bytes")
    print(f"Python: {sys.version}")
    print()

    # Phase 1: Addition
    print("Phase 1: Addition (iadd)")
    t_add = run_addition_phase(width, iterations)
    print()

    # Phase 2: Multiplication
    # Reduce iterations for multiplication (much heavier, especially at higher widths)
    mul_iterations = max(1, iterations // 10) if width >= 16 else iterations
    print(f"Phase 2: Multiplication (mul, {mul_iterations} iterations)")
    t_mul = run_multiplication_phase(width, mul_iterations)
    print()

    # Phase 3: XOR
    print("Phase 3: XOR (ixor)")
    t_xor = run_xor_phase(width, iterations)
    print()

    print(f"Total time: {t_add + t_mul + t_xor:.3f}s")
    print("Done. Use memray stats/flamegraph on the .bin file for analysis.")


if __name__ == "__main__":
    main()
