# Phase 55: Profiling Infrastructure - Research

**Researched:** 2026-02-05
**Domain:** Python/Cython/C cross-layer profiling and benchmarking
**Confidence:** HIGH

## Summary

This research covers the profiling infrastructure needed for Phase 55 of the Quantum Assembly v2.2 Performance Optimization milestone. The phase establishes measurement-driven optimization by integrating Python-level profiling (cProfile), memory profiling (memray), Cython annotation analysis (cython -a), cross-layer profiling (py-spy --native), and reproducible benchmarking (pytest-benchmark).

The recommended approach is to:
1. Add profiling dependencies as an optional `[profiling]` extra in pyproject.toml
2. Create a `ql.profile()` context manager that wraps cProfile for inline profiling
3. Update setup.py to support profiling builds with Cython directives
4. Add Makefile targets for common profiling workflows
5. Create a benchmark suite using pytest-benchmark fixtures

**Primary recommendation:** Start with standard Python profiling tools (cProfile, memray, pytest-benchmark) rather than building custom C-level profilers. The existing ecosystem is mature and well-tested.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cProfile | stdlib | Function-level timing for Python code | Built-in, zero install, industry standard |
| memray | 1.19.1 | Memory allocation profiling including C extensions | Bloomberg production tool, traces native code |
| pytest-benchmark | 5.2.3 | Regression testing for performance | Integrates with existing pytest suite |
| snakeviz | 2.2.2 | cProfile visualization | Browser-based flame graphs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| py-spy | 0.4.1 | Sampling profiler with native support | Cross-layer profiling via `--native` flag |
| line_profiler | 5.0.0 | Line-by-line timing | Drilling into specific hot functions |
| scalene | 2.1.3 | All-in-one CPU/memory profiler | Comprehensive single-tool analysis |
| pstats | stdlib | cProfile statistics manipulation | Sorting and filtering profile data |

### Cython-Specific
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| cython -a | 3.2.4+ | Annotation HTML generation | Identifying Python/C boundary crossings |
| profile=True directive | 3.0+ | Enable cProfile hooks in Cython | When function-level timing needed |
| linetrace=True directive | 3.0+ | Enable line-level tracing | When coverage or line profiling needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| memray | memory_profiler | memory_profiler unmaintained since 2022 |
| py-spy | pyinstrument | pyinstrument cannot profile C extensions |
| cProfile | profile | profile is pure Python, 10x slower |
| snakeviz | tuna | snakeviz has more mature UI |
| pytest-benchmark | asv | asv is more complex, suited for larger projects |

**Installation:**
```bash
pip install "line-profiler>=5.0.0" "snakeviz>=2.2.2" "pytest-benchmark>=5.2.3"
pip install "memray>=1.19.1" "pytest-memray"
pip install "py-spy>=0.4.1" "scalene>=2.1.3"
```

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
    __init__.py             # Add profile() export
    profiler.py             # NEW: ql.profile() context manager (~150 LOC)

tests/
    benchmarks/             # NEW: pytest-benchmark tests
        conftest.py         # Benchmark fixtures
        test_arithmetic.py  # Benchmark qint operations
        test_compile.py     # Benchmark @ql.compile
```

### Pattern 1: cProfile Context Manager Wrapper
**What:** Wrap cProfile.Profile() with a user-friendly context manager that returns structured results
**When to use:** Inline profiling of specific code sections
**Example:**
```python
# Source: Python stdlib + custom wrapper
import cProfile
import pstats
from contextlib import contextmanager
from io import StringIO

class ProfileStats:
    """Container for profiling results."""
    def __init__(self):
        self._profiler = cProfile.Profile()
        self._stats = None

    def report(self, sort_key='cumulative', limit=20):
        """Generate human-readable report."""
        stream = StringIO()
        stats = pstats.Stats(self._profiler, stream=stream)
        stats.sort_stats(sort_key)
        stats.print_stats(limit)
        return stream.getvalue()

@contextmanager
def profile():
    """Profile quantum operations.

    Usage:
        with ql.profile() as stats:
            a = ql.qint(5, width=8)
            b = a + 3
        print(stats.report())
    """
    ps = ProfileStats()
    ps._profiler.enable()
    try:
        yield ps
    finally:
        ps._profiler.disable()
```

### Pattern 2: pytest-benchmark Fixtures
**What:** Use pytest-benchmark fixture to measure operation timing
**When to use:** Reproducible performance regression testing
**Example:**
```python
# Source: pytest-benchmark documentation
def test_qint_add_benchmark(benchmark, clean_circuit):
    """Benchmark qint addition operation."""
    a = ql.qint(5, width=8)
    b = ql.qint(3, width=8)

    result = benchmark(lambda: a + b)
    # Benchmark measures multiple iterations automatically
```

### Pattern 3: Profiling Build Mode
**What:** Conditionally enable Cython profiling directives via environment variable
**When to use:** When function-level profiling of Cython code is needed
**Example:**
```python
# Source: setup.py modification
import os

profiling_directives = {}
if os.environ.get('QUANTUM_PROFILE'):
    profiling_directives = {
        'profile': True,
        'linetrace': True,
    }
    compiler_args.append('-DCYTHON_TRACE=1')

# In cythonize() call:
ext_modules=cythonize(
    extensions,
    language_level="3",
    compiler_directives={
        "embedsignature": True,
        **profiling_directives,
    },
)
```

### Anti-Patterns to Avoid
- **Profiling without representative workloads:** Don't profile only small circuits; use production-scale (1000+ gates)
- **Global Cython profile=True:** Adds overhead to all functions; enable only when needed
- **Memory profiling with -O3:** Optimizations can make allocation sites unclear; use -O1 for memory debugging
- **py-spy without --native:** Missing C extension activity; always use `--native` for this codebase

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Function timing | Custom timing decorators | cProfile | cProfile handles nested calls, statistics |
| Memory tracking | Custom malloc hooks | memray | memray traces all allocators, native code |
| Flame graphs | Custom visualization | snakeviz/py-spy SVG | Battle-tested visualization |
| Benchmark timing | time.perf_counter() loops | pytest-benchmark | Handles warmup, statistics, comparison |
| HTML annotation | Custom Cython parser | cython -a | Official tool, maintained with Cython |
| C profiling | Custom instrumentation | valgrind/perf | Deep integration with OS/CPU |

**Key insight:** Profiling is a solved problem. The challenge is integrating existing tools into the workflow, not building new profilers. Focus development time on optimization, not measurement infrastructure.

## Common Pitfalls

### Pitfall 1: Python 3.12+ Breaks Cython Profiling
**What goes wrong:** Cython's `profile=True` directive doesn't work correctly in Python 3.12+ due to PEP-669 changes to the profiling hooks.
**Why it happens:** CPython 3.12 changed how profiling callbacks work; Cython hasn't fully adapted.
**How to avoid:** Pin profiling work to Python 3.11. Use py-spy (sampling-based) for 3.12+ instead of cProfile.
**Warning signs:** Cython functions not appearing in cProfile output despite `profile=True`.

### Pitfall 2: memray Platform Limitations
**What goes wrong:** memray installation fails on Windows or unsupported platforms.
**Why it happens:** memray uses platform-specific memory tracking APIs (Linux/macOS only).
**How to avoid:** Document platform requirements; provide fallback guidance for Windows (use WSL2).
**Warning signs:** ImportError when trying to import memray on Windows.

### Pitfall 3: Unrepresentative Benchmark Workloads
**What goes wrong:** Benchmarks show improvement, but production code doesn't benefit.
**Why it happens:** Small test circuits have different cache/allocation patterns than large circuits.
**How to avoid:** Create benchmark suite with varying sizes: 10, 100, 1000, 10000 gates.
**Warning signs:** Optimization helps 4-bit but not 16-bit operations.

### Pitfall 4: Profiling Overhead Skews Results
**What goes wrong:** cProfile's instrumentation overhead makes fast functions appear slower than they are.
**Why it happens:** cProfile adds ~1us per function call; swamps sub-microsecond operations.
**How to avoid:** Use sampling profilers (py-spy) for micro-benchmarks; cProfile for macro analysis.
**Warning signs:** Profiled code is >50% slower than non-profiled code.

### Pitfall 5: Missing Native Frames in py-spy
**What goes wrong:** py-spy output shows only Python frames, C extension time attributed to Python call site.
**Why it happens:** Forgot `--native` flag or symbols not available.
**How to avoid:** Always use `py-spy record --native`; compile with `-g` for debug symbols.
**Warning signs:** All time attributed to single Python lines that call C functions.

## Code Examples

Verified patterns from official sources:

### cProfile Basic Usage
```python
# Source: Python stdlib documentation
import cProfile
import pstats

# Profile a function
cProfile.run('expensive_function()', 'profile.stats')

# Analyze results
stats = pstats.Stats('profile.stats')
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### memray Native Profiling
```bash
# Source: memray documentation
# Profile with native code tracking
memray run --native -o memray.bin your_script.py

# Generate flame graph
memray flamegraph memray.bin -o memory.html

# Check for leaks
memray stats memray.bin
```

### Cython Annotation Generation
```bash
# Source: Cython documentation
# Generate annotation HTML for all .pyx files
cython -a src/quantum_language/*.pyx

# Output: src/quantum_language/qint.html
# Yellow lines = Python C-API interaction = slow
# White lines = pure C = fast
```

### pytest-benchmark Complete Example
```python
# Source: pytest-benchmark documentation
import pytest
import quantum_language as ql

@pytest.fixture
def prepared_qints():
    """Setup qints outside of timing."""
    ql.circuit()
    return ql.qint(5, width=8), ql.qint(3, width=8)

def test_addition(benchmark, prepared_qints):
    a, b = prepared_qints
    result = benchmark(lambda: a + b)
    # benchmark handles iterations, warmup, statistics

def test_addition_large(benchmark):
    """Benchmark with different sizes."""
    ql.circuit()
    a = ql.qint(12345, width=16)
    b = ql.qint(67890, width=16)
    benchmark(lambda: a + b)
```

### py-spy with Native Profiling
```bash
# Source: py-spy documentation
# Record with native frame support
py-spy record --native -o profile.svg -- python test_circuit.py

# For Cython, use emit_linenums for accurate line mapping
# In setup.py: cythonize(..., emit_linenums=True)
```

### pyproject.toml Optional Dependencies
```toml
# Source: PEP 508, pyproject.toml specification
[project.optional-dependencies]
profiling = [
    "line-profiler>=5.0.0",
    "snakeviz>=2.2.2",
    "pytest-benchmark>=5.2.3",
    "memray>=1.19.1; sys_platform != 'win32'",
    "pytest-memray; sys_platform != 'win32'",
    "py-spy>=0.4.1",
    "scalene>=2.1.3",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| memory_profiler | memray | 2022 | Native code support, better performance |
| gprof for C | perf/valgrind | ~2015 | No recompilation needed, better accuracy |
| Manual timing | pytest-benchmark | ~2018 | Statistical rigor, regression detection |
| Print debugging | py-spy sampling | ~2019 | Zero code modification, production-safe |

**Deprecated/outdated:**
- **memory_profiler:** Unmaintained since 2022; use memray
- **profile (stdlib):** Pure Python, too slow; use cProfile
- **gprof:** Requires -pg compilation; use perf on Linux

## Open Questions

Things that couldn't be fully resolved:

1. **Cython profiling on Python 3.12+**
   - What we know: PEP-669 changed profiling hooks; Cython's profile=True may not work
   - What's unclear: Exact failure mode and whether there's a workaround
   - Recommendation: Test with Python 3.11 first; if 3.12+ needed, use py-spy instead

2. **memray on macOS ARM64**
   - What we know: memray supports macOS; some users report ARM64 issues
   - What's unclear: Current state of ARM64 support in memray 1.19.1
   - Recommendation: Test on target platform; document any issues

3. **Benchmark reproducibility across machines**
   - What we know: pytest-benchmark supports --benchmark-compare
   - What's unclear: How to normalize for CPU speed differences
   - Recommendation: Run benchmarks on consistent CI hardware; store relative improvements

## Sources

### Primary (HIGH confidence)
- [Python cProfile Documentation](https://docs.python.org/3/library/profile.html) - Official stdlib profiling guide
- [pytest-benchmark 5.2.3 Documentation](https://pytest-benchmark.readthedocs.io/en/latest/usage.html) - Fixture usage, CLI options
- [memray Documentation](https://bloomberg.github.io/memray/) - Native code profiling, run subcommand
- [Cython Profiling Tutorial](https://cython.readthedocs.io/en/latest/src/tutorial/profiling_tutorial.html) - profile/linetrace directives
- [Cython Annotation Guide](https://cython.readthedocs.io/en/latest/src/quickstart/cythonize.html) - Yellow lines interpretation

### Secondary (MEDIUM confidence)
- [py-spy Native Profiling](https://www.benfrederickson.com/profiling-native-python-extensions-with-py-spy/) - --native flag usage for Cython
- [Adam Johnson cProfile Context Manager](https://adamj.eu/tech/2023/07/23/python-profile-section-cprofile/) - Context manager pattern
- [scikit-learn Cython Best Practices](https://scikit-learn.org/stable/developers/cython.html) - Compiler directives

### Tertiary (LOW confidence)
- [MClare Cython Profiling Blog](https://mclare.blog/posts/further-adventures-in-cython-profiling/) - Community experience with py-spy + Cython

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools verified on PyPI with current versions
- Architecture: HIGH - Patterns derived from official documentation
- Pitfalls: MEDIUM - Some based on community reports, not personal verification

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - stable domain)

---

## Implementation Checklist for Planner

Based on this research, Phase 55 implementation should include:

1. **PROF-07: Add optional `[profiling]` extra to pyproject.toml**
   - Add all profiling dependencies with platform markers
   - Test installation on Linux/macOS

2. **PROF-01: Python function profiling**
   - Verify cProfile works with quantum_language operations
   - Document usage in README or docs

3. **PROF-05: Create `ql.profile()` context manager**
   - Add `profiler.py` module (~150 LOC)
   - Export from `__init__.py`
   - Write usage tests

4. **PROF-02: Memory profiling with memray**
   - Verify memray tracks C extension allocations
   - Add Makefile target for memray workflow

5. **PROF-03: Cython annotation HTML generation**
   - Add `cython-annotate` Makefile target
   - Document yellow line interpretation

6. **PROF-04: Cross-layer profiling with py-spy**
   - Add `profile-native` Makefile target
   - Test with `--native` flag on Cython code

7. **PROF-06: Benchmark suite with pytest-benchmark**
   - Create `tests/benchmarks/` directory
   - Add benchmark fixtures to conftest.py
   - Create initial benchmark tests for qint operations

8. **setup.py profiling build support**
   - Add QUANTUM_PROFILE environment variable check
   - Enable profile/linetrace directives conditionally
