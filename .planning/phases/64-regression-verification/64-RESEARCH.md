# Phase 64: Regression Verification - Research

**Researched:** 2026-02-08
**Domain:** Python/C performance benchmarking and test suite regression verification
**Confidence:** HIGH

## Summary

Phase 64 is the final phase of the v2.3 Hardcoding Right-Sizing milestone. Its goal is to confirm that Phase 63's changes (shared QFT/IQFT factoring, regenerated C files reducing 79,867 to 53,598 lines) introduced no performance regression and no new test failures compared to the v2.2 baseline.

The project already has comprehensive benchmark infrastructure from Phase 62: `scripts/benchmark_sequences.py` (BENCH-01 import time, BENCH-02 first-call generation cost, BENCH-03 cached dispatch overhead) and `scripts/benchmark_eval.py` (evaluation and report generation). The Phase 62 baseline data is in `benchmarks/results/bench_raw.json` and `benchmarks/results/benchmark_report.json`. Phase 64 needs to re-run these benchmarks on the post-Phase-63 codebase, compare results against the Phase 62 baseline, and confirm the test suite passes. The code has already been rebuilt after Phase 63 changes and the 165 hardcoded sequence tests already passed during Phase 63 execution. Phase 64 adds the performance comparison dimension.

**Primary recommendation:** Re-run the existing `benchmark_sequences.py` benchmarks (BENCH-01, BENCH-02, BENCH-03) on the post-Phase-63 codebase, save results to a new file (e.g., `bench_raw_post63.json`), produce a comparison report against the Phase 62 baseline, and run the full test suite to confirm zero new failures. The comparison should tolerate noise (define acceptable regression threshold at 10-15% for timing measurements) and document any differences with justification.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scripts/benchmark_sequences.py` | Phase 62 | Primary benchmark script for BENCH-01/02/03 | Already proven, measures import time, first-call, and dispatch overhead |
| `scripts/benchmark_eval.py` | Phase 62 | Report generation and evaluation | Already produces comparison reports |
| `time.perf_counter_ns` | stdlib | Nanosecond-precision timing | Best available Python wallclock timer |
| `subprocess` | stdlib | Clean-process import and first-call measurement | Required for cache isolation |
| `json` | stdlib | Structured benchmark output | Machine-readable comparison data |
| `statistics` | stdlib | Mean, median, stdev | Statistical summarization |
| `pytest` | installed | Test suite runner | Existing infrastructure |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `benchmarks/results/bench_raw.json` | Phase 62 data | Baseline data for comparison | Reference point for regression detection |
| `benchmarks/results/benchmark_report.json` | Phase 62 data | Structured baseline report | Contains amortization and evaluation data |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Re-running benchmark_sequences.py | pytest-benchmark | pytest-benchmark adds overhead; custom script already optimized for this project's needs |
| Separate comparison script | Manual diff of JSON files | A script provides structured comparison with thresholds and formatting |
| Full 144-point BENCH-02 rerun | Spot-check key widths only | Full rerun gives comprehensive data but takes ~5 min; spot-check is faster but may miss width-specific regressions |

## Architecture Patterns

### Recommended Approach

```
scripts/
    benchmark_sequences.py      # Existing -- reuse as-is to collect post-Phase-63 data
benchmarks/
    results/
        bench_raw.json          # Phase 62 baseline (KEEP, do not overwrite)
        bench_raw_post63.json   # New: post-Phase-63 measurements
        benchmark_report.json   # Phase 62 report (KEEP)
        regression_report.md    # New: comparison of before vs after
        regression_report.json  # New: structured comparison data
```

### Pattern 1: Benchmark Comparison with Noise Tolerance
**What:** Compare Phase 62 (before) and post-Phase-63 (after) benchmark results with a configurable tolerance threshold for timing noise.
**When to use:** All timing comparisons.
**Key insight:** Timing measurements have inherent variance (Phase 62 reported 15.86ms stdev on 192ms import time = ~8% noise). A 10-15% tolerance is appropriate to avoid false-positive regression alarms.
**Example:**
```python
import json
import statistics

TOLERANCE_PERCENT = 15.0  # Accept up to 15% regression as noise

def compare_benchmarks(before_path, after_path):
    """Compare two bench_raw.json files and produce regression report."""
    with open(before_path) as f:
        before = json.load(f)
    with open(after_path) as f:
        after = json.load(f)

    results = {}

    # BENCH-01: Import time comparison
    before_import = before["bench_01_import_time"]["median_ms"]
    after_import = after["bench_01_import_time"]["median_ms"]
    pct_change = ((after_import - before_import) / before_import) * 100
    results["import_time"] = {
        "before_ms": before_import,
        "after_ms": after_import,
        "change_pct": round(pct_change, 1),
        "regression": pct_change > TOLERANCE_PERCENT,
    }

    # BENCH-02: First-call comparison per operation/width
    # ...similar pattern for each measurement...

    return results
```

### Pattern 2: Test Suite Baseline Comparison
**What:** Run the full test suite and compare pass/fail counts against known v2.2 baseline. Document pre-existing failures explicitly.
**When to use:** For the "zero new failures" success criterion.
**Key insight:** The project has documented pre-existing test failures:
  - `test_phase7_arithmetic` (32-bit multiplication segfault)
  - `test_array_creates_list_of_qint` (related segfault)
These are NOT new failures. Phase 64 must distinguish pre-existing from new.

**Test suite commands:**
```bash
# Full Python test suite
pytest tests/python/ -v

# Hardcoded sequence validation tests
pytest tests/test_hardcoded_sequences.py -v

# All root-level test files
pytest tests/test_add.py tests/test_sub.py tests/test_mul.py tests/test_bitwise.py \
       tests/test_compare.py tests/test_copy.py tests/test_div.py tests/test_mod.py -v

# Benchmark tests (optional)
pytest tests/benchmarks/ -v --benchmark-only
```

### Pattern 3: Structured Regression Report
**What:** Generate a markdown and JSON report comparing before/after measurements with pass/fail verdict.
**When to use:** Final deliverable of Phase 64.
**Structure:**
```markdown
# Regression Verification Report

## Verdict: PASS / FAIL

## Import Time (BENCH-01)
| Metric | Before (Phase 62) | After (Phase 63) | Change |
|--------|-------------------|-------------------|--------|
| Median | 192ms | Xms | +/-Y% |

## First-Call Generation (BENCH-02)
[Per-operation comparison tables]

## Cached Dispatch (BENCH-03)
[Hardcoded vs dynamic comparison]

## Test Suite
| Category | Before | After | New Failures |
|----------|--------|-------|-------------|
| tests/python/ | X pass | Y pass | 0 |

## .so Binary Sizes
[Before/after comparison -- expect reduction from factoring]

## Conclusion
[Summary with justification for any acceptable trade-offs]
```

### Anti-Patterns to Avoid
- **Overwriting baseline data:** Never overwrite `bench_raw.json` -- it is the Phase 62 baseline. Save post-Phase-63 data to a separate file.
- **Treating any timing difference as regression:** Timing has inherent noise. Use statistical thresholds.
- **Ignoring pre-existing failures:** The 32-bit multiplication segfault and related crashes are pre-existing. Do not count them as new regressions.
- **Skipping import time measurement:** Phase 63 reduced C source from 80K to 54K lines, which could change .so size and import time. Must measure.
- **Running benchmarks without rebuilding:** The project must be rebuilt after Phase 63 changes. Phase 63 already did `python setup.py build_ext --inplace` -- verify this is current.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Benchmark measurement | Custom timing code | `scripts/benchmark_sequences.py` | Already proven, handles subprocess isolation, cache management |
| Report generation | Manual markdown | Script that generates from structured data | Ensures consistency, repeatability |
| Statistical comparison | Custom mean/stdev | `statistics` module | Well-tested, handles edge cases |
| JSON diffing | Custom comparison | Simple Python dict comparison | Straightforward key-by-key comparison |

**Key insight:** Nearly all the infrastructure needed for Phase 64 already exists from Phase 62. The primary new work is the comparison layer that takes two benchmark datasets and produces a regression verdict.

## Common Pitfalls

### Pitfall 1: Stale Binary Artifacts
**What goes wrong:** Running benchmarks against old .so files that don't reflect Phase 63 changes.
**Why it happens:** Python extension modules are cached after build. If the build step was skipped or failed silently, benchmarks would measure the pre-Phase-63 code.
**How to avoid:** Verify .so file modification timestamps are recent (after Phase 63 commits). Run `python setup.py build_ext --inplace` before benchmarking if there's any doubt.
**Warning signs:** Import time and .so sizes identical to Phase 62 baseline.

### Pitfall 2: False Regression from System Load
**What goes wrong:** Benchmarks show 20%+ regression, but it is due to system load differences between Phase 62 and Phase 64 runs.
**Why it happens:** The benchmarks run on a shared system. CPU throttling, background processes, and memory pressure all affect timing.
**How to avoid:** Run benchmarks multiple times (20+ iterations for import, 10+ for first-call) and use median (not mean). If results are suspicious, run a few more iterations. Document system conditions.
**Warning signs:** High stdev (>20% of median), inconsistent results across runs.

### Pitfall 3: Confusing Source Reduction with Binary Reduction
**What goes wrong:** Expecting the 32.9% C source reduction to translate directly to 32.9% binary size reduction.
**Why it happens:** Compiler optimizations may already deduplicate identical static const data. The source-level sharing may not reduce binary size proportionally.
**How to avoid:** Measure actual .so file sizes (benchmark_sequences.py already does this via BENCH-01). Report both source and binary changes. Any binary reduction is a bonus; the primary benefit was source maintainability.
**Warning signs:** .so sizes unchanged despite 26K fewer C source lines.

### Pitfall 4: Counting Pre-Existing Failures as Regressions
**What goes wrong:** Reporting the 32-bit multiplication segfault as a Phase 64 regression.
**Why it happens:** Not consulting the documented pre-existing failures list.
**How to avoid:** Maintain an explicit list of known pre-existing failures. Compare test results against this list. Only NEW failures count as regressions.
**Warning signs:** test_phase7_arithmetic or test_array_creates_list_of_qint in the "regression" column.

### Pitfall 5: Not Measuring the Right Thing for "Throughput"
**What goes wrong:** Measuring only dispatch time but not the full end-to-end circuit generation path.
**Why it happens:** Phase 62 benchmarks focused on micro-level measurements (import, first-call, dispatch). Phase 64 success criterion says "circuit generation throughput."
**How to avoid:** The existing benchmarks already measure what matters: BENCH-02 (first-call) and BENCH-03 (cached dispatch) are the two components of "circuit generation throughput." Together they cover the full path. No additional macro-benchmark is needed.
**Warning signs:** N/A -- the existing benchmarks are sufficient.

## Code Examples

### Running Benchmarks with Output to New File
```bash
# Rebuild first to ensure current Phase 63 code
cd /path/to/project
python setup.py build_ext --inplace

# Run all benchmarks, save to new file
PYTHONPATH=src python scripts/benchmark_sequences.py \
    --output benchmarks/results/bench_raw_post63.json

# Expected runtime: ~5-7 minutes
```

### Comparing Two Benchmark Files
```python
import json

def load_bench(path):
    with open(path) as f:
        return json.load(f)

def compare_import_time(before, after):
    b = before["bench_01_import_time"]
    a = after["bench_01_import_time"]
    pct = ((a["median_ms"] - b["median_ms"]) / b["median_ms"]) * 100
    return {
        "before_ms": b["median_ms"],
        "after_ms": a["median_ms"],
        "change_pct": round(pct, 1),
        "verdict": "PASS" if pct <= 15.0 else "INVESTIGATE"
    }

def compare_first_call(before, after):
    """Compare first-call generation cost per operation."""
    results = {}
    b_fc = before["bench_02_first_call_us"]
    a_fc = after["bench_02_first_call_us"]
    for op in b_fc:
        results[op] = {}
        for width in b_fc[op]:
            b_val = b_fc[op][width]
            a_val = a_fc.get(op, {}).get(width)
            if b_val and a_val:
                pct = ((a_val - b_val) / b_val) * 100
                results[op][width] = {
                    "before_us": b_val,
                    "after_us": a_val,
                    "change_pct": round(pct, 1)
                }
    return results
```

### Running Full Test Suite with Failure Collection
```bash
# Run Python unit tests
pytest tests/python/ -v --tb=short 2>&1 | tee test_results_python.txt

# Run hardcoded sequence tests
pytest tests/test_hardcoded_sequences.py -v --tb=short 2>&1 | tee test_results_hardcoded.txt

# Run root-level verification tests (skip known crashers)
pytest tests/test_add.py tests/test_sub.py tests/test_bitwise.py \
       tests/test_compare.py tests/test_copy.py -v --tb=short 2>&1 | tee test_results_verification.txt
```

### Pre-Existing Failures (v2.2 Baseline)
```python
# These failures exist in v2.2 and are NOT regressions
PRE_EXISTING_FAILURES = {
    "test_phase7_arithmetic": "32-bit multiplication segfault (buffer overflow in C backend)",
    "test_array_creates_list_of_qint": "Related segfault in array creation",
}
```

## Phase 62 Baseline Data (Reference)

The following are the key Phase 62 measurements to compare against:

### BENCH-01: Import Time
- Median: 192.35 ms
- Mean: 189.86 ms
- Stdev: 15.86 ms
- Total .so size: 17,164,280 bytes (16.4 MB)

### BENCH-02: First-Call Generation Cost (key widths, in microseconds)
| Operation | Width 1 | Width 4 | Width 8 | Width 16 |
|-----------|---------|---------|---------|----------|
| QQ_add | 189.6 | 425.6 | 206.0 | 405.1 |
| CQ_add | 217.4 | 216.6 | 235.3 | 229.4 |
| cQQ_add | 215.0 | 396.6 | 481.1 | 578.1 |
| cCQ_add | 189.2 | 226.5 | 223.7 | 240.2 |

### BENCH-03: Cached Dispatch Overhead (nanoseconds per call)
| Operation | Hardcoded (w=8) | Dynamic (w=17) |
|-----------|----------------|----------------|
| QQ_add | 17,578.9 ns | 107,924.9 ns |
| CQ_add | 12,450.1 ns | 30,988.8 ns |

### .so File Sizes (bytes)
| Extension | Size |
|-----------|------|
| qint.so | 4,952,256 |
| qarray.so | 3,795,408 |
| _core.so | 2,466,640 |
| qint_mod.so | 2,213,840 |
| qbool.so | 1,982,056 |
| openqasm.so | 1,754,080 |

## Expected Outcomes

Based on the Phase 63 changes (shared QFT/IQFT factoring, 32.9% C source reduction), these are the expected outcomes:

| Metric | Expected Change | Reasoning |
|--------|----------------|-----------|
| Import time | Slight decrease (5-15%) or unchanged | Less C source compiled into .so, but compiler may already deduplicate |
| .so binary sizes | Slight decrease or unchanged | Compiler deduplication may have already handled this |
| First-call QQ_add/cQQ_add | Unchanged (within noise) | Static const dispatch is identical -- sharing is source-only |
| First-call CQ_add/cCQ_add | Unchanged (within noise) | Template-init still mallocs same data, just via shared helpers |
| Cached dispatch | Unchanged (within noise) | Run_instruction path is untouched |
| Hardcoded sequence correctness | Pass (already verified in Phase 63) | 165 tests passed after regeneration |

**What could cause actual regression:**
- Bug in shared helper functions causing incorrect gate sequences (would show as test failures, not timing regression)
- Segmented optimization (+1 layer for widths >= 2) adding overhead (negligible -- single extra pointer in LAYERS array)
- Compiler generating worse code for shared static const references vs inline definitions (unlikely, same data, same access pattern)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No baseline benchmarks | Structured benchmark suite | Phase 62 (2026-02-08) | Enables data-driven regression detection |
| Duplicated QFT/IQFT per variant | Shared QFT/IQFT arrays | Phase 63 (2026-02-08) | 32.9% source reduction, potential binary reduction |
| Manual regression checking | Automated comparison report | Phase 64 (this phase) | Repeatable, quantified regression verification |

## Open Questions

1. **Does the segmented optimization (+1 layer) affect dispatch performance?**
   - What we know: For widths >= 2, segmented optimization adds 1 extra layer to prevent cross-boundary merging. This adds one extra pointer to the LAYERS array.
   - What's unclear: Whether this single extra layer is measurable in dispatch timing.
   - Recommendation: The BENCH-03 measurements will show this. Expected to be well within noise.

2. **Did the compiler already deduplicate identical static const data?**
   - What we know: GCC/Clang with -O3 can merge identical read-only data sections. Phase 63 research flagged this as LOW confidence.
   - What's unclear: Whether the pre-Phase-63 .so files already had deduplication, meaning Phase 63 sharing provides no binary size benefit.
   - Recommendation: Compare .so file sizes before and after. If unchanged, note that the benefit is source maintainability, not binary size.

3. **Are there pre-existing test failures beyond the documented ones?**
   - What we know: Phase 63 documented `test_phase7_arithmetic` and `test_array_creates_list_of_qint` as pre-existing segfaults. STATE.md documents BUG-DIV-02, BUG-MOD-REDUCE, BUG-COND-MUL-01, BUG-WIDTH-ADD as known issues.
   - What's unclear: Whether additional test files (test_mul.py, test_div.py, test_mod.py) have pre-existing failures related to these bugs.
   - Recommendation: Run the full test suite and compare against a v2.2 baseline run. Any failures also present in v2.2 are pre-existing.

## Sources

### Primary (HIGH confidence)
- Source code analysis of `scripts/benchmark_sequences.py` (559 lines) -- complete benchmark measurement infrastructure
- Source code analysis of `scripts/benchmark_eval.py` (1001 lines) -- evaluation and report generation
- `benchmarks/results/bench_raw.json` -- Phase 62 baseline timing data
- `benchmarks/results/benchmark_report.json` -- Phase 62 structured report with amortization
- `.planning/phases/63-right-sizing-implementation/63-VERIFICATION.md` -- Phase 63 verification confirming 165 tests pass
- `.planning/phases/63-right-sizing-implementation/63-01-SUMMARY.md` -- Phase 63 execution results
- `.planning/phases/63-right-sizing-implementation/RIGHT_SIZING_DECISION.md` -- Phase 63 before/after line count data
- `.planning/ROADMAP.md` -- Phase 64 success criteria and requirements
- `.planning/STATE.md` -- Pre-existing bugs and known failures

### Secondary (MEDIUM confidence)
- Phase 62 research on timing measurement methodology (subprocess isolation, cache management)
- Estimated binary size impact from Phase 63 research (compiler deduplication behavior)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- reusing existing Phase 62 benchmark infrastructure, no new tools needed
- Architecture: HIGH -- straightforward comparison of two benchmark runs with known baseline
- Pitfalls: HIGH -- identified from direct experience in Phase 62 and Phase 63 execution
- Expected outcomes: MEDIUM -- binary size impact depends on compiler behavior (not yet measured)

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (stable -- no external dependency changes expected)
