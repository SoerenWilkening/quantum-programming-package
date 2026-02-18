# Phase 62: Measurement - Research

**Researched:** 2026-02-08
**Domain:** Python/C benchmarking of quantum gate sequence generation performance
**Confidence:** HIGH

## Summary

Phase 62 requires building comprehensive benchmarks to quantify the cost/benefit of hardcoded gate sequences for addition operations, and to evaluate whether multiplication, bitwise, and division operations warrant hardcoding. The project already has foundational benchmarking infrastructure (pytest-benchmark in `tests/benchmarks/`, a profiling module, and a memory profiling script), but no import-time or first-call generation cost benchmarking exists.

The core measurement challenge is distinguishing three separate costs: (1) import-time overhead from compiling ~80K lines of hardcoded C sequence files into the shared library, (2) first-call sequence generation cost (malloc + QFT + gate construction for dynamic; switch dispatch + static const access for hardcoded), and (3) per-call dispatch overhead after caching (pointer return from cache array vs pointer return from static const). The benchmark architecture must be designed to isolate these three costs cleanly.

**Primary recommendation:** Build a standalone benchmark script (`scripts/benchmark_sequences.py`) that uses `time.perf_counter_ns()` for microsecond-level timing, `subprocess` for clean-process import timing, and structured JSON output for the comparison report. Use the existing pytest-benchmark infrastructure as a secondary validation path but not as the primary measurement tool (pytest-benchmark adds overhead that obscures microsecond-level dispatch differences).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `time.perf_counter_ns` | stdlib | Nanosecond-precision timing | Best available wallclock timer in Python, no install needed |
| `subprocess` | stdlib | Import time measurement in clean process | Required to measure cold-start import without contamination |
| `json` | stdlib | Structured benchmark output | Machine-readable report for Phase 63 consumption |
| `statistics` | stdlib | Mean, median, stdev of measurements | Proper statistical summarization of timing data |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-benchmark` | >=5.2.3 | Secondary benchmark validation | Already installed as optional dep; use for cross-validation |
| `timeit` | stdlib | Micro-benchmark runner with repeat/number | Fallback timer when perf_counter_ns approach needs warmup control |
| `argparse` | stdlib | CLI for benchmark script | Make benchmark configurable (widths, iterations, operation types) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `time.perf_counter_ns` | `timeit.default_timer` | timeit is simpler but perf_counter_ns gives ns precision needed for dispatch overhead |
| Custom script | pytest-benchmark only | pytest-benchmark cannot easily measure subprocess import time or isolate first-call |
| JSON output | CSV | JSON better for nested structure (per-operation, per-width) |

## Architecture Patterns

### Recommended Project Structure
```
scripts/
    benchmark_sequences.py      # Primary benchmark script (BENCH-01..04)
    benchmark_eval.py           # Evaluation script for mul/bitwise/div (EVAL-01..03)
benchmarks/
    results/
        benchmark_report.json   # Machine-readable results
        benchmark_report.md     # Human-readable comparison report
```

### Pattern 1: Clean-Process Import Timing (BENCH-01)
**What:** Measure import time with and without hardcoded sequences by spawning subprocess
**When to use:** Import-time measurement must be isolated from the test process (which already has quantum_language loaded)
**Example:**
```python
import subprocess
import time
import json

def measure_import_time(iterations=10):
    """Measure import time in a clean subprocess."""
    script = """
import time
start = time.perf_counter_ns()
import quantum_language
end = time.perf_counter_ns()
print(end - start)
"""
    times = []
    for _ in range(iterations):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, cwd=project_root,
            env={**os.environ, "PYTHONPATH": "src"}
        )
        times.append(int(result.stdout.strip()))
    return times
```

**Key insight:** Comparing "with" vs "without" hardcoded sequences requires two builds. The practical approach is: (a) measure current build with hardcoded sequences, (b) build a variant with `-DSEQ_NO_WIDTH_1 -DSEQ_NO_WIDTH_2 ... -DSEQ_NO_WIDTH_16` to disable all hardcoded sequences, (c) measure that variant. However, this requires recompilation. A simpler alternative: measure current import time, estimate the hardcoded-free import time from the dynamic-only path (width 17+), and note the marginal cost.

**Practical alternative for BENCH-01:** Since import time is dominated by Python module loading and shared library loading (not sequence initialization -- hardcoded sequences are static const, initialized at load time by the linker), the import overhead from hardcoded sequences is primarily the additional binary size loaded into memory. This can be estimated by measuring .so file size difference rather than requiring two separate builds.

### Pattern 2: First-Call Generation Cost Isolation (BENCH-02)
**What:** Measure the first-call cost of each operation type where the sequence is generated/cached for the first time
**When to use:** To determine if dynamic generation is expensive enough to warrant hardcoding
**Example:**
```python
import quantum_language as ql

def measure_first_call_cost(op_func, width, iterations=5):
    """Measure first-call generation cost for an operation.

    Must use fresh circuit to ensure sequence cache is empty.
    The first iteration measures generation; subsequent measure cache.
    """
    times = []
    for _ in range(iterations):
        # Each process starts with empty caches
        # For in-process measurement, we exploit that sequences
        # are cached globally, so only the very first call generates.
        # After first call, all subsequent calls hit the cache.
        pass

    # The FIRST call to any operation at a given width triggers generation.
    # But caches are global (per-process lifetime), so we can only measure
    # first-call ONCE per width per process invocation.
    # Solution: use subprocess per width OR use a width never seen before.
```

**Critical insight:** The C-level sequence caches (`precompiled_QQ_add_width[]`, etc.) are global and persist for the process lifetime. There is no API to clear them. This means:
- First-call generation cost can only be measured ONCE per process per operation/width
- Subsequent calls hit the cache and measure dispatch overhead
- To measure first-call repeatedly, must use subprocess per measurement

For hardcoded operations (addition widths 1-16), the "first call" is a switch dispatch + pointer return (QQ_add, cQQ_add) or switch dispatch + malloc template + pointer return (CQ_add, cCQ_add). For dynamic operations, the "first call" involves malloc + loop over bits to build gate arrays.

### Pattern 3: Dispatch Overhead Measurement (BENCH-03)
**What:** Measure per-call overhead for operations that are already cached
**When to use:** To determine if the difference between hardcoded lookup and dynamic cache hit is measurable
**Example:**
```python
def measure_dispatch_overhead(width, iterations=10000):
    """Measure cached dispatch overhead.

    After the first call, both hardcoded and dynamic paths
    return from a cache array. The question is whether the
    switch statement vs simple array indexing matters.
    """
    ql.circuit()
    a = ql.qint(0, width=width)
    b = ql.qint(0, width=width)

    # Warm up (triggers first-call generation/lookup)
    a += b

    # Measure cached dispatch (many iterations)
    start = time.perf_counter_ns()
    for _ in range(iterations):
        a += b
    end = time.perf_counter_ns()

    return (end - start) / iterations  # ns per call
```

**Key insight for BENCH-03:** For cached operations, the dispatch path is:
- **Hardcoded (QQ_add, cQQ_add):** `QQ_add(bits)` -> `if (bits <= HARDCODED_MAX_WIDTH)` -> `get_hardcoded_QQ_add(bits)` -> switch statement -> return static pointer
- **Dynamic cached:** `QQ_add(bits)` -> check `precompiled_QQ_add_width[bits] != NULL` -> return pointer
- Both paths end up at `run_instruction(seq, qa, invert, circ)` which is identical

The difference is a switch vs array lookup -- likely sub-microsecond and unmeasurable from Python.

### Pattern 4: Comparison Report Generation (BENCH-04)
**What:** Produce structured comparison of hardcoded vs dynamic costs with amortization analysis
**When to use:** Final output of the benchmark suite
**Structure:**
```json
{
    "import_time_ms": {"with_hardcoded": 123.4, "estimated_without": 120.0},
    "first_call_generation_us": {
        "QQ_add": {"1": 5.2, "2": 8.1, ...},
        "QQ_mul": {"1": 12.3, "2": 45.6, ...}
    },
    "cached_dispatch_ns": {
        "QQ_add": {"8_hardcoded": 150, "17_dynamic": 148}
    },
    "amortization": {
        "break_even_calls": 42,
        "recommendation": "keep|remove|factor"
    }
}
```

### Anti-Patterns to Avoid
- **Measuring timing in-process after import:** The import time includes many things beyond hardcoded sequences; subprocess isolation is essential
- **Using a single iteration for first-call measurement:** System noise dominates; need multiple subprocess runs and median
- **Assuming cache is empty in the same process:** Global C caches persist -- only first call per width generates
- **Benchmarking division directly as a sequence:** Division is implemented at the Python level using addition/subtraction/comparison loops, not as a single C sequence -- it requires different benchmarking approach

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Statistical analysis | Custom mean/stdev | `statistics` module | Handles edge cases, well-tested |
| Precise timing | `time.time()` | `time.perf_counter_ns()` | time.time() has ~1ms resolution; perf_counter_ns has ~100ns |
| Process isolation | in-process measurement | `subprocess.run()` | Global C caches cannot be reset |
| Benchmark harness | Custom iteration logic | Existing `profile_memory_61.py` pattern | Already proven to work in this codebase |

**Key insight:** The hardest part of this benchmarking is not the measurement code itself but correctly isolating what is being measured. The codebase has global C-level caches that cannot be reset without process restart.

## Common Pitfalls

### Pitfall 1: Cache Contamination
**What goes wrong:** Measuring "first-call" generation cost for width 8, but width 8 was already generated during warm-up or a previous test
**Why it happens:** `precompiled_QQ_add_width[8]` is set on first call and never cleared
**How to avoid:** Use subprocess isolation for first-call measurements; test one width per subprocess invocation
**Warning signs:** First-call times suspiciously close to cached dispatch times

### Pitfall 2: Python Overhead Dominating C Measurement
**What goes wrong:** The Python/Cython wrapper overhead (qubit extraction, GIL release, qubit_array construction) dominates the actual C-level generation time
**Why it happens:** For small widths, the C-level generation is microseconds, but the Cython wrapper adds ~50-100us overhead
**How to avoid:** For BENCH-02 (first-call generation), measure end-to-end from Python (which is what users experience); for BENCH-03 (dispatch overhead), compare same-width hardcoded vs dynamic to cancel out Python overhead
**Warning signs:** All operations show similar first-call times regardless of complexity

### Pitfall 3: Multiplication Uses MAXLAYERINSEQUENCE (10000)
**What goes wrong:** First-call generation for QQ_mul/cQQ_mul allocates 10000 layers with 10*bits gates each, even though most layers are empty
**Why it happens:** Multiplication sequences pre-allocate `MAXLAYERINSEQUENCE` layers instead of computing exact layer count
**How to avoid:** This is actually the generation cost that hardcoding would eliminate -- measure it as-is, it represents the real allocation overhead
**Warning signs:** Multiplication memory cost is much higher than addition for the same width

### Pitfall 4: CQ_add/cCQ_add Template vs Static Confusion
**What goes wrong:** Assuming CQ_add is fully static like QQ_add -- it is not. CQ_add hardcoded sequences are "template-init" (allocated on first call, then angles injected per-call)
**Why it happens:** QQ_add/cQQ_add are `static const` (zero first-call cost), but CQ_add/cCQ_add use `init_hardcoded_CQ_add_N()` which mallocs on first call
**How to avoid:** Distinguish between two hardcoding strategies in benchmarks: (a) static const (QQ, cQQ) and (b) template-init (CQ, cCQ)
**Warning signs:** CQ_add first-call times are much closer to dynamic than expected

### Pitfall 5: Division is Not a C Sequence
**What goes wrong:** Trying to benchmark "division generation cost" as a single C function call
**Why it happens:** Unlike addition/multiplication/bitwise, division is implemented entirely in Python/Cython using a loop of comparisons and conditional subtractions
**How to avoid:** For EVAL-03, measure end-to-end Python-level division cost (which calls comparison + addition + subtraction under the hood), not C-level sequence generation
**Warning signs:** Looking for a `Q_div()` C function that does not exist

### Pitfall 6: Bitwise Operations Are Already Trivial
**What goes wrong:** Expecting bitwise hardcoding to provide significant speedup
**Why it happens:** Q_xor, Q_and, Q_or generate O(bits) gates in O(1) or O(3) layers -- the generation is already trivially fast
**How to avoid:** Measure actual generation cost and compare against hardcoded-sequence maintenance burden
**Warning signs:** Bitwise generation times under 1 microsecond, making hardcoding pointless

## Code Examples

### Measuring Import Time via Subprocess
```python
import subprocess
import sys
import os
import statistics

def measure_import_time(n=20):
    """Measure quantum_language import time in clean subprocess."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = "import time; s=time.perf_counter_ns(); import quantum_language; print(time.perf_counter_ns()-s)"

    times_ns = []
    for _ in range(n):
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": os.path.join(project_root, "src")},
            cwd=project_root
        )
        if r.returncode == 0:
            times_ns.append(int(r.stdout.strip()))

    return {
        "median_ms": statistics.median(times_ns) / 1e6,
        "mean_ms": statistics.mean(times_ns) / 1e6,
        "stdev_ms": statistics.stdev(times_ns) / 1e6 if len(times_ns) > 1 else 0,
        "samples": len(times_ns)
    }
```

### Measuring First-Call Generation Cost via Subprocess
```python
def measure_first_call(op_code, width, n=10):
    """Measure first-call generation cost for an operation at given width.

    op_code: string like "iadd_qq", "iadd_cq", "mul_qq", "xor", "and", "or"
    """
    script = f"""
import time, quantum_language as ql
ql.circuit()
a = ql.qint(1, width={width})
b = ql.qint(1, width={width})
start = time.perf_counter_ns()
{_get_op_statement(op_code)}
end = time.perf_counter_ns()
print(end - start)
"""
    times_ns = []
    for _ in range(n):
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": os.path.join(project_root, "src")},
            cwd=project_root
        )
        if r.returncode == 0:
            times_ns.append(int(r.stdout.strip()))
    return times_ns
```

### Measuring Cached Dispatch Overhead
```python
def measure_cached_dispatch(width, iterations=50000):
    """Measure per-call overhead for already-cached operations."""
    import quantum_language as ql

    ql.circuit()
    a = ql.qint(0, width=width)
    b = ql.qint(0, width=width)

    # Warm up - triggers first-call generation
    a += b

    # Measure many iterations of cached dispatch
    start = time.perf_counter_ns()
    for _ in range(iterations):
        a += b
    elapsed = time.perf_counter_ns() - start

    return elapsed / iterations  # nanoseconds per call
```

### Operation Type Mapping
```python
# Maps requirement operation names to actual Python operations
OPERATION_MAP = {
    "QQ_add":  lambda a, b: a.__iadd__(b),        # a += b (quantum+quantum)
    "CQ_add":  lambda a, _: a.__iadd__(3),         # a += 3 (classical+quantum)
    "cQQ_add": "controlled QQ_add",                 # requires controlled context
    "cCQ_add": "controlled CQ_add",                 # requires controlled context
    "QQ_mul":  lambda a, b: a.__mul__(b),           # a * b
    "CQ_mul":  lambda a, _: a.__mul__(3),           # a * 3
    "Q_xor":   lambda a, b: a.__xor__(b),           # a ^ b
    "Q_and":   lambda a, b: a.__and__(b),           # a & b
    "Q_or":    lambda a, b: a.__or__(b),            # a | b
}
```

### Controlled Operation Measurement
```python
def measure_controlled_op(op_type, width):
    """Measure controlled operations using qbool context manager."""
    script = f"""
import time, quantum_language as ql
ql.circuit()
a = ql.qint(1, width={width})
b = ql.qint(1, width={width})
ctrl = ql.qbool(True)
start = time.perf_counter_ns()
with ctrl:
    {"a += b" if op_type == "cQQ_add" else "a += 3"}
end = time.perf_counter_ns()
print(end - start)
"""
    # Use subprocess for clean cache state
    pass
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All dynamic generation | Hardcoded sequences for add widths 1-16 | Phase 58-59 (2026-02-05/06) | Eliminates malloc+generation for common widths |
| Python-level qubit shuffling | C hot path migration | Phase 60 (2026-02-06) | Removes Python/C boundary crossings |
| MAXLAYERINSEQUENCE for all seqs | Exact layer count for addition | Phase 61 (2026-02-08) | Reduced memory for addition sequences |
| cProfile-based profiling | Dedicated profiler + memray | Phase 55 (2026-02-05) | Better profiling infrastructure |

**Current state of hardcoding:**
- Addition (QQ_add, cQQ_add, CQ_add, cCQ_add): Hardcoded for widths 1-16, dynamic for 17+
- Multiplication (QQ_mul, CQ_mul, cQQ_mul, cCQ_mul): Fully dynamic, uses `MAXLAYERINSEQUENCE=10000` pre-allocation
- Bitwise (Q_xor, Q_and, Q_or): Fully dynamic, trivial O(bits) generation
- Division: Implemented in Python via addition/subtraction/comparison loop, no C sequence
- Comparison: Stub functions in C, implemented in Python

## Operation Complexity Analysis

Understanding generation complexity is critical for hardcoding recommendations:

| Operation | Sequence Layers | Gates per Layer | Generation Complexity | Cache Strategy |
|-----------|----------------|----------------|-----------------------|----------------|
| QQ_add(N) | 5N-2 | up to 2N | O(N^2) CP gates | Global array, exact alloc |
| cQQ_add(N) | ~N^2 | up to 2N | O(N^2) complex decomposition | Global array, exact alloc |
| CQ_add(N) | 5N-2 | up to 2N | O(N^2) angle computation | Global array, exact alloc |
| cCQ_add(N) | 5N-2 | up to 2N | O(N^2) angle computation | Global array, exact alloc |
| QQ_mul(N) | ~N^3 | up to 10N | O(N^3) CCP decomposition | Global array, MAXLAYER alloc |
| CQ_mul(N) | ~N^2 | up to 10N | O(N^2) angle computation | **NOT cached** (new each call) |
| cQQ_mul(N) | ~N^3 | up to 10N | O(N^3) complex decomposition | Global array, MAXLAYER alloc |
| Q_xor(N) | 1 | N CNOTs | O(N) trivial | **NOT cached** (new each call) |
| Q_and(N) | 1 | N Toffolis | O(N) trivial | **NOT cached** (new each call) |
| Q_or(N) | 3 | N each | O(N) trivial | **NOT cached** (new each call) |

**Critical observation:** Multiplication uses `MAXLAYERINSEQUENCE=10000` for layer allocation regardless of width, allocating `10000 * 10N * sizeof(gate_t)` bytes. For N=16, that is `10000 * 160 * 40 = 64MB` per sequence. This massive allocation is a primary candidate for hardcoding benefit measurement.

**Correction on CQ_mul caching:** CQ_mul is NOT cached (returns newly allocated sequence each call). This means every `a * 3` call at a given width re-generates the sequence. QQ_mul IS cached.

## Benchmark Design Decisions

### BENCH-01: Import Time
- Use subprocess with `time.perf_counter_ns()` for clean measurement
- Run 20+ iterations, report median (most stable statistic for timing)
- "Without hardcoded" estimate: measure .so file size difference OR measure import with width-17-only operations

### BENCH-02: First-Call Generation Cost
- One subprocess per (operation, width) pair
- 9 operations x 16 widths = 144 measurement points
- 10 subprocess runs per point, report median
- Total: ~1440 subprocess calls (~5 minutes with 200ms each)

### BENCH-03: Cached Dispatch Overhead
- In-process measurement (cache is what we want to measure)
- Compare width 8 (hardcoded) vs width 17 (dynamic) for addition
- 50,000+ iterations per measurement
- Need to measure: is the difference even above noise?

### BENCH-04: Comparison Report
- JSON output with all measurements
- Markdown report with tables and recommendations
- Amortization formula: `break_even = import_overhead_ns / (dynamic_first_call_ns - hardcoded_first_call_ns)`

### EVAL-01: Multiplication
- QQ_mul first-call cost at widths 1-16 (O(N^3) generation + MAXLAYER allocation)
- CQ_mul per-call cost (no caching, regenerated each call)
- Compare against addition generation cost at same widths
- Hardcoding recommendation based on: generation cost >> addition? Binary size implications?

### EVAL-02: Bitwise
- Q_xor, Q_and, Q_or first-call cost at widths 1-16
- Expected to be trivially fast (O(N) with small constant)
- Hardcoding recommendation: likely "skip" due to trivial generation

### EVAL-03: Division
- Division is Python-level, not C-level: measure end-to-end `a // b` and `a % b`
- Decompose cost: how many addition/subtraction/comparison operations per division?
- For classical divisor: N comparison+subtraction loops (N = width)
- For quantum divisor: 2^N loops (exponential) -- clearly cannot be hardcoded
- Hardcoding recommendation: likely "skip" -- cost is in the loop structure, not sequence generation

## File Size Impact Analysis

The 16 hardcoded sequence files plus dispatch total ~80K lines of C code and ~4MB on disk. When compiled:
- Each .pyx extension links ALL c_sources (including all 17 sequence files)
- There are multiple .pyx modules (qint, qbool, _core, openqasm, qarray, qint_mod) each linking the same C files
- The compiled .so files contain the same hardcoded data replicated across modules

This means the binary size impact is `number_of_extensions * size_of_hardcoded_data`. Understanding this impact is important for the import-time analysis.

## Open Questions

1. **Can we disable hardcoded sequences at runtime?**
   - What we know: Preprocessor guards (`SEQ_NO_WIDTH_N`) control compile-time inclusion
   - What's unclear: Whether there is a runtime toggle for A/B benchmarking
   - Recommendation: For BENCH-01, estimate rather than rebuild. For BENCH-02/03, compare hardcoded widths (1-16) vs dynamic widths (17+) at comparable sizes

2. **Is CQ_mul truly uncached?**
   - What we know: `CQ_mul()` does not check/set any cache array, unlike `QQ_mul()` which uses `precompiled_QQ_mul_width[]`
   - What's unclear: Whether this was intentional or an oversight
   - Recommendation: Verify by code inspection (confirmed above -- CQ_mul returns fresh malloc each call)

3. **What is the actual .so size contribution of hardcoded sequences?**
   - What we know: Source is ~4MB, compiled size will be different
   - What's unclear: Exact binary size impact after compilation and linking
   - Recommendation: Measure `ls -la *.so` and compare against a build without sequences (or estimate from object file sizes)

## Sources

### Primary (HIGH confidence)
- Source code analysis of `c_backend/src/IntegerAddition.c` - cache strategy, hardcoded dispatch
- Source code analysis of `c_backend/src/IntegerMultiplication.c` - MAXLAYERINSEQUENCE allocation
- Source code analysis of `c_backend/src/LogicOperations.c` - trivial generation for bitwise
- Source code analysis of `c_backend/include/sequences.h` - preprocessor guard system
- Source code analysis of `src/quantum_language/qint_division.pxi` - Python-level division
- Source code analysis of `setup.py` - build system, C source linking
- Source code analysis of `scripts/profile_memory_61.py` - existing benchmarking patterns
- Source code analysis of `tests/benchmarks/test_qint_benchmark.py` - existing benchmark tests

### Secondary (MEDIUM confidence)
- Python `time.perf_counter_ns()` documentation - nanosecond timer availability

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using only stdlib tools, verified available in project Python
- Architecture: HIGH - patterns directly derived from existing codebase patterns
- Pitfalls: HIGH - identified from direct code analysis of cache mechanisms and sequence types
- Operation complexity: HIGH - derived from reading actual C generation code

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable -- no external dependency changes expected)
