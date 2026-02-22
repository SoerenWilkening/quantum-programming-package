# Stack Research: v4.1 Quality & Efficiency

**Domain:** Quality improvement, bug fixing, tech debt, security hardening, binary size reduction, test coverage for an existing C/Cython/Python quantum programming framework
**Researched:** 2026-02-22
**Confidence:** HIGH

## Executive Summary

This milestone requires **targeted tool additions** across six areas: debugging, tech debt, security, binary size, performance, and test coverage. The existing stack (Python 3.11+, Cython 3.x, C23 backend, pytest, cProfile, memray, py-spy, pytest-benchmark, ruff, clang-format, AddressSanitizer, Valgrind) already covers most needs. The additions are lightweight, well-established tools that fill specific gaps.

Key insight: this is NOT a "pick a framework" decision. Every tool recommended below solves a concrete, identified problem from the codebase CONCERNS.md audit. No speculative additions.

## Recommended Stack Additions

### 1. Test Coverage Analysis

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest-cov | >=6.0,<8.0 | pytest plugin for coverage reporting | Integrates directly with existing `pytest tests/python/ -v` workflow; generates HTML/XML reports. v7.0.0 dropped subprocess measurement (irrelevant here since tests don't spawn subprocesses). Use >=6.0 for Cython plugin compatibility. |
| coverage[toml] | >=7.4 | Underlying coverage engine | Required by pytest-cov. v7.13.4 supports Python 3.10-3.15 including free-threading. The `[toml]` extra enables config via `pyproject.toml` (no `.coveragerc` needed). |

**Cython coverage note:** Cython coverage requires `linetrace=True` compiler directive and `CYTHON_TRACE=1` define. The project already has `QUANTUM_PROFILE=1` env var that enables these in `setup.py`. Coverage.py has a built-in Cython plugin (`Cython.Coverage`) that reads the generated C source comments to map lines back to `.pyx` files.

**Configuration to add to `pyproject.toml`:**
```toml
[tool.coverage.run]
source = ["src/quantum_language"]
plugins = ["Cython.Coverage"]
omit = [
    "*/test_*",
    "*_preprocessed.pyx",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
show_missing = true
fail_under = 0  # Start with 0, ratchet up as coverage improves
```

### 2. Dead Code & Tech Debt Detection

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| vulture | >=2.12 | Find unused Python functions/variables/imports | Specifically identifies dead code that ruff F401 (unused imports) and F841 (unused variables) miss: unused functions, unreachable code, unused class attributes. Confidence scoring (60-100%) reduces false positives. |

**Why vulture over alternatives:**
- `ruff` already handles unused imports (F401) and unused variables (F841) -- those rules are already enabled in `pyproject.toml`
- `vulture` fills the gap: unused functions, methods, classes, and unreachable code paths that ruff does not detect
- `deadcode` (alternative) is newer but less battle-tested; vulture has 10+ years of production use

**For C dead code:** No new tool needed. The `-ffunction-sections -fdata-sections` + `--gc-sections` linker flags (recommended in binary size section) will identify and remove dead C code at link time. Adding `-Wl,--print-gc-sections` will print which sections are removed, serving as a dead code report.

**For duplicate files:** No tool needed. The `qint_preprocessed.pyx` duplication is a known issue with a known fix: ensure `build_preprocessor.py` generates it automatically and add a CI check that the committed preprocessed file matches the generated one. This is a process fix, not a tool.

### 3. C Security Hardening

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| cppcheck | >=2.14 | Static analysis for C memory safety | Detects buffer overruns, null dereference, uninitialized memory, and array bounds issues without running the code. Specifically catches the `qubit_array` bounds and `q_address[64]` overflow risks identified in CONCERNS.md. |
| clang-tidy | (ships with clang) | C linting and modernization | Already available via clang installation (used for clang-format). Checks like `bugprone-*`, `clang-analyzer-*`, and `cert-*` catch security-relevant patterns. Integrates with the existing `.pre-commit-config.yaml`. |

**What NOT to add for C security:**
- **Coverity** -- commercial, overkill for this project size
- **CodeQL** -- designed for CI/CD (GitHub Actions), heavy setup, this project runs locally
- **Infer (Meta)** -- interprocedural analysis is powerful but slow; cppcheck + clang-tidy cover the identified concerns

**Already available (DO NOT re-add):**
- AddressSanitizer (ASan) -- `make asan-test` already exists in Makefile
- Valgrind -- `make memtest` already exists
- `-Wall -Wextra` -- already in CFLAGS

**Recommended cppcheck configuration:**
```bash
cppcheck --enable=warning,performance,portability,style \
         --std=c23 \
         --suppress=missingIncludeSystem \
         -I c_backend/include \
         c_backend/src/
```

**Recommended `.clang-tidy` config:**
```yaml
Checks: >
  bugprone-*,
  cert-*,
  clang-analyzer-*,
  -clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling
WarningsAsErrors: ''
HeaderFilterRegex: 'c_backend/include/.*'
```

### 4. Binary Size Reduction (Compiler Flags)

No new tools needed -- this is a compiler flag change in `setup.py`.

| Technique | Flag | Expected Impact | Why |
|-----------|------|-----------------|-----|
| Size optimization | `-Os` | 10-20% reduction | Optimizes for code size. Currently using `-O3` which optimizes for speed and produces larger binaries. For hardcoded sequences (which are lookup tables), `-Os` is equally fast. |
| Section garbage collection | `-ffunction-sections -fdata-sections` (compile) + `-Wl,--gc-sections` (link) | 5-15% reduction | Each function goes in its own ELF section; linker removes unreferenced sections. The ~107 sequence files likely have unused width variants per extension module. |
| Strip symbols | `-s` (link) or `strip` post-build | 20-30% reduction | Removes debug symbols from production `.so` files. Currently compiling without strip. |
| ThinLTO | `-flto=thin` | 10-20% reduction | Link-time dead code elimination across translation units. The project disabled LTO due to a GCC bug (comment in `setup.py`). ThinLTO is Clang-only and avoids that GCC issue. Test with Clang before enabling. |

**Current `.so` sizes (Linux x86_64):**
- `qint.so`: 12MB, `qarray.so`: 11MB, `_core.so`: 9MB, `qint_mod.so`: 8.7MB
- Total: ~75MB across all platform variants
- Each `.so` links ALL 107 sequence files (~344K lines of C) even though each module only uses a subset

**Biggest win:** Section garbage collection. Each `.so` currently includes ALL C backend code (sequences, Toffoli, QFT, CLA, Clifford+T) even though e.g. `openqasm.so` only needs circuit output functions. `-Wl,--gc-sections` will strip the unused sequences from each module.

**Implementation note:** These flags go in `setup.py` `extra_compile_args` and `extra_link_args`. Test build success and run full test suite before committing.

### 5. Performance Profiling (Already Available)

**No new tools needed.** The existing profiling stack is comprehensive:

| Tool | Already In Stack | Purpose |
|------|-----------------|---------|
| cProfile | Python stdlib | Function-level profiling |
| py-spy | `[profiling]` extra | Native flame graphs |
| memray | `[profiling]` extra | Memory profiling |
| pytest-benchmark | `[profiling]` extra | Regression benchmarks |
| line-profiler | `[profiling]` extra | Line-by-line timing |
| scalene | `[profiling]` extra | CPU + memory combined |
| Cython annotations | `make profile-cython` | Python/C boundary visualization |

**What to use for specific v4.1 tasks:**
- **Optimizer binary search** (replacing linear scan in `optimizer.c`): Use `py-spy --native` to confirm `smallest_layer_below_comp` is the bottleneck, then benchmark before/after with `pytest-benchmark`
- **Compile replay overhead**: Use `cProfile` with `QUANTUM_PROFILE=1` build to see Python dict iteration cost in `inject_remapped_gates`
- **Circuit rebuild per Grover attempt**: Use `line-profiler` on `grover.py` to measure `circuit()` reset overhead vs oracle execution

### 6. C Test Integration into pytest

No new tool needed. Write a pytest wrapper that compiles and runs C tests via `subprocess`.

```python
# tests/python/test_c_backend.py
import subprocess
import pytest

C_TESTS = [
    ("test_allocator_block", "run_alloc"),
    ("test_reverse_circuit", "run_reverse"),
]

@pytest.mark.parametrize("target,run_target", C_TESTS)
def test_c_backend(target, run_target):
    """Compile and run C backend tests via Makefile."""
    result = subprocess.run(
        ["make", "-C", "tests/c", target],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"

    result = subprocess.run(
        ["make", "-C", "tests/c", run_target],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"Test failed:\n{result.stderr}"
```

## Installation

```bash
# Add to pyproject.toml [project.optional-dependencies]
# dev group (already exists, extend it):
pip install -e ".[dev]"

# For coverage analysis (new):
pip install pytest-cov>=6.0 "coverage[toml]>=7.4"

# For dead code detection (new):
pip install vulture>=2.12

# System-level (not pip):
# cppcheck: brew install cppcheck (macOS) / apt install cppcheck (Linux)
# clang-tidy: ships with clang (already available)
```

**Updated `pyproject.toml` dependency groups:**
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pre-commit>=3.0",
    "ruff>=0.1.0",
    "vulture>=2.12",
]
quality = [
    "pytest-cov>=6.0,<8.0",
    "coverage[toml]>=7.4",
    "vulture>=2.12",
]
verification = [
    "qiskit>=1.0",
    "qiskit-aer>=0.14",  # NEW: was undeclared, now explicit
]
```

## Alternatives Considered

| Recommended | Alternative | Why Not Alternative |
|-------------|-------------|-------------------|
| vulture | deadcode | deadcode is newer (2024), less battle-tested, fewer downloads. vulture has 10+ years and better Cython interop. |
| cppcheck | Coverity | Coverity is commercial, requires cloud upload. cppcheck is open source, runs locally, sufficient for this codebase size. |
| cppcheck | CodeQL | CodeQL needs GitHub Actions integration, heavy setup. This project runs locally; cppcheck is simpler. |
| pytest-cov | coverage run pytest | pytest-cov auto-handles `.coverage` file management and parallel collection. Saves manual steps. |
| -Os | -O3 (keep current) | -O3 optimizes speed; -Os optimizes size. For lookup-table-heavy code (sequences), -Os is equally fast. -O3 is better for hot-path arithmetic where instruction scheduling matters. Use -Os for sequence files only if mixed flags are feasible. |
| -Wl,--gc-sections | Manual dead code removal | GC sections is automatic and tracks across link-time. Manual removal risks breaking code that IS used by some paths. |
| ThinLTO | Full LTO | Full LTO was disabled due to GCC bug. ThinLTO is Clang-only, faster compilation, same size benefits. |

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| pytest-xdist (parallel testing) | Tests share global circuit state via module globals -- parallel execution would produce corrupt circuits | Keep sequential test execution |
| mypy / pytype (static typing) | Cython `.pyx` files are not supported by mypy; adding type stubs for 60K lines of Cython is a separate milestone | ruff already catches type-related bugs via `UP` and `B` rules |
| gcov / lcov (C coverage) | The C code is compiled into Cython extensions, not standalone executables. gcov requires separate compilation which breaks the Cython integration | Use Cython.Coverage plugin via coverage.py for Cython line coverage; C functions called from Cython are implicitly covered |
| Fuzz testing (AFL, libFuzzer) | Valuable but out of scope for this milestone. Would need dedicated harness development | Focus on deterministic bug reproduction first |
| Docker / containerized testing | No deployment target; library is installed via pip. Containerization adds complexity without benefit | Keep local venv-based development |
| clang-analyzer (scan-build) | Significant overlap with cppcheck + clang-tidy. Three static analysis tools is diminishing returns | cppcheck + clang-tidy cover all identified concerns |
| SonarQube | Cloud-hosted, commercial, designed for enterprise CI/CD. Overkill for a single-developer open source project | cppcheck (C) + ruff (Python) + vulture (dead code) |

## Stack Patterns by Milestone Area

**If debugging quantum circuit bugs (BUG-MOD-REDUCE, BUG-COND-MUL-01, etc.):**
- Use `CYTHON_DEBUG=1 python setup.py build_ext --inplace` for bounds-checked Cython builds
- Use `make asan-test` for C-level memory bugs (32-bit segfault, qarray `*=` segfault)
- Use existing `verify_circuit` fixture with narrow width ranges to isolate failures
- No new tools needed; existing ASan + Valgrind + Cython debug mode cover this

**If doing tech debt cleanup (dead QPU stubs, duplicate files):**
- Use `vulture src/ --min-confidence 80` to find dead Python code
- Use `ruff check --select F401,F811` for unused imports (already configured)
- For `qint_preprocessed.pyx`, fix the build process (ensure `build_preprocessor.py` runs in CI), not a tool issue

**If security hardening (pointer validation, bounds checking):**
- Use `cppcheck --enable=all -I c_backend/include c_backend/src/` for static analysis
- Use `clang-tidy -checks='bugprone-*,cert-*' c_backend/src/*.c` for additional checks
- Add runtime assertions in Cython with `CYTHON_DEBUG=1` for development builds
- Add `assert(circ != NULL)` guards at C function entry points (manual code changes, not tools)

**If reducing binary size:**
- Apply `-ffunction-sections -fdata-sections` compile flags + `-Wl,--gc-sections` link flag in `setup.py`
- Apply `-s` (strip) for release builds only (keep debug symbols in dev)
- Evaluate `-Os` vs `-O3` with benchmark suite to ensure no performance regression
- Run `size` command on `.so` files before/after to measure impact

**If performance optimization:**
- Use existing `make benchmark` + `make profile-native` + `make profile-cprofile`
- For optimizer binary search: write a targeted benchmark, apply `bsearch()`, compare
- For compile replay: profile with `QUANTUM_PROFILE=1` build, identify dict overhead

**If closing test coverage gaps:**
- Add `pytest-cov` and run `pytest tests/python/ --cov=quantum_language --cov-report=html`
- Coverage report identifies which modules/lines are untested
- Focus on high-risk areas first: nested `with`-blocks, circuit reset, C test integration

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pytest-cov >=6.0,<8.0 | pytest >=7.0 (already in stack) | v7.0.0 dropped subprocess measurement, irrelevant for this project |
| coverage[toml] >=7.4 | Python 3.10-3.15 | Supports the project's Python 3.11+ requirement |
| vulture >=2.12 | Python 3.8+ | Works with all supported Python versions |
| cppcheck >=2.14 | C23 standard | Supports the project's `-std=c23` compilation |
| Cython.Coverage plugin | Cython >=3.0 | Built into Cython; requires `linetrace=True` directive |
| qiskit-aer >=0.14 | qiskit >=1.0 (already in stack) | Fixes the undeclared dependency identified in CONCERNS.md |

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Test coverage (pytest-cov) | HIGH | Official docs, PyPI release history, standard pytest ecosystem |
| Dead code detection (vulture) | HIGH | PyPI, 10+ years of releases, well-known in Python community |
| C static analysis (cppcheck) | HIGH | Official docs, widely used in open source C projects |
| Binary size reduction (compiler flags) | MEDIUM | Well-documented GCC/Clang flags, but ThinLTO needs testing with this specific codebase (LTO was previously disabled due to a bug) |
| Performance profiling | HIGH | All tools already in stack and validated in v2.2 |
| C test integration | HIGH | Standard subprocess + pytest pattern, no new dependencies |

## Sources

- [pytest-cov 7.0.0 on PyPI](https://pypi.org/project/pytest-cov/) -- version and compatibility verified
- [coverage.py 7.13.4 documentation](https://coverage.readthedocs.io/) -- Cython plugin docs, configuration format
- [Cython Coverage.py integration](https://github.com/cython/cython/blob/master/Cython/Coverage.py) -- plugin implementation details
- [vulture 2.14 on PyPI](https://pypi.org/project/vulture/) -- version and feature set verified
- [cppcheck 2.19.0 releases](https://github.com/danmar/cppcheck/releases) -- latest version, C23 support confirmed
- [GCC section garbage collection](https://www.vidarholen.net/contents/blog/?p=729) -- `-ffunction-sections` + `--gc-sections` effectiveness documented
- [Link-Time Optimization techniques](https://markaicode.com/link-time-optimization-cpp26/) -- ThinLTO vs full LTO comparison
- [Running C unit tests with pytest](https://p403n1x87.github.io/running-c-unit-tests-with-pytest.html) -- subprocess integration pattern
- Project codebase analysis: `.planning/codebase/CONCERNS.md`, `.planning/codebase/STACK.md`, `.planning/codebase/TESTING.md`

---
*Stack research for: v4.1 Quality & Efficiency milestone*
*Researched: 2026-02-22*
*Conclusion: 3 new pip packages (pytest-cov, coverage, vulture), 1 system tool (cppcheck), compiler flag changes, no architecture changes.*
