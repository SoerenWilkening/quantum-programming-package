# Technology Stack

**Project:** Quantum Assembly
**Researched:** 2026-01-25
**Overall confidence:** HIGH

## Recommended Stack

### Core Language & Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Cython** | 3.2.4 | C/Python bindings layer | Industry standard for scientific Python C extensions. Used by NumPy, SciPy, scikit-learn. Supports static typing, C++ integration, generates efficient C code. Latest version (Jan 2026) adds collection type decorators and enhanced exception handling. | HIGH |
| **Python** | 3.10-3.13 | Frontend API & testing | Current supported range. Python 3.13 adds sys.monitoring for better profiling. Stick to 3.10+ for testing (pytest 9.0.2 requirement). | HIGH |
| **GCC/Clang** | Latest stable | C compiler | Your setup.py already uses GCC with `-O3 -flto -pthread`. Keep these flags. LTO (Link-Time Optimization) critical for quantum circuit performance. | HIGH |

**Rationale:** Cython 3.2.4 is production-stable (released Jan 4, 2026) and used by the entire scientific Python ecosystem. Your existing architecture (C backend → Cython → Python) matches SciPy's approach exactly.

### Build System

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **setuptools + Cython.Build** | Current | Build orchestration | You're already using this (setup.py with cythonize). Don't change unless build complexity increases significantly. | HIGH |
| ~~scikit-build-core~~ | - | ❌ NOT RECOMMENDED | Only needed for CMake projects. You have simple C files, not CMake. Adds unnecessary complexity. | HIGH |
| ~~Meson~~ | - | ❌ NOT YET | SciPy migrated to Meson in 2021-2024, but Cython support is minimal. Premature for your project size. | MEDIUM |

**Recommendation:** Stick with setuptools + cythonize. It works, it's simple, and every contributor knows it.

### Testing Frameworks

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **pytest** | 9.0.2 | Python test runner | Latest stable (Dec 2025). 1300+ plugins, best assertion introspection, auto-discovery. Industry standard for scientific Python. | HIGH |
| **pytest-cython** | 0.3.1 | Test Cython .pyx code | Allows testing `cdef` functions. Actively maintained (releases in 2024). Assumes C extensions built in-place before test run. | MEDIUM |
| **unittest** (C) | - | C unit tests | Write pure C tests for Backend/ code. Use assert() + test runner script. No heavy framework needed. | HIGH |

**Installation:**
```bash
pip install pytest==9.0.2 pytest-cython==0.3.1
```

**Why pytest-cython:** Your Cython bindings (quantum_language.pyx) wrap C functions. You need to test both:
1. C layer directly (unit tests in C)
2. Cython layer (pytest-cython for .pyx code)
3. Python API (standard pytest)

**C testing approach:** Don't over-engineer. Create `Backend/tests/test_*.c` files with main() that runs asserts. Simple and fast.

### Memory Debugging

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Valgrind** | 3.26.0 | Memory leak detection | Gold standard for C memory debugging. Detects leaks, uninitialized memory, invalid frees. High overhead but comprehensive. | HIGH |
| **AddressSanitizer (ASan)** | LLVM built-in | Fast memory error detection | Compile-time instrumentation with `-fsanitize=address`. 10-100x faster than Valgrind. Catches use-after-free, buffer overflows. Use during development. | HIGH |
| **LeakSanitizer (LSan)** | LLVM built-in | Leak-only checking | Part of ASan. Can run standalone with `-fsanitize=leak`. Lower overhead than full ASan. | HIGH |

**Usage recommendation:**

**Development workflow:**
1. Compile with ASan: `gcc -fsanitize=address -g -O1 ...`
2. Run tests → ASan catches errors immediately
3. Weekly: Full Valgrind run for comprehensive check

**Why both:** ASan is fast enough for every commit. Valgrind finds edge cases ASan misses. Use ASan daily, Valgrind weekly.

**Python integration:**
- Python 3.13 supports `--with-address-sanitizer` at configure time
- For your project: compile C/Cython with ASan, run pytest
- Valgrind works directly: `valgrind --leak-check=full python -m pytest`

### Documentation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Sphinx** | 9.1.0 | Documentation generator | Latest stable (Dec 31, 2025). Used by NumPy, SciPy, scikit-learn, Django. Supports C, C++, Python. Extensive extension ecosystem. | HIGH |
| **numpydoc** | 1.11.0 | NumPy docstring format | Released Dec 2, 2025. Sphinx extension for NumPy-style docstrings. Standard for scientific Python. Supports Parameters, Returns, Examples sections. | HIGH |
| **MyST-Parser** | Latest | Markdown support | Write docs in Markdown instead of reStructuredText. Recommended by Scientific Python Development Guide. | MEDIUM |
| **sphinx.ext.autodoc** | Built-in | Auto-generate API docs | Extracts docstrings from Python code. Essential for API reference. | HIGH |
| **sphinx.ext.napoleon** | Built-in | Google/NumPy docstrings | Parses NumPy and Google style docstrings. Use with numpydoc. | HIGH |

**Installation:**
```bash
pip install sphinx==9.1.0 numpydoc==1.11.0 myst-parser furo
```

**Theme recommendation:** `furo` - modern, clean, used by Scientific Python projects.

**Docstring format:** Use NumPy style (matches scientific Python ecosystem):
```python
def add_integers(a, b):
    """
    Add two quantum integers.

    Parameters
    ----------
    a : qint
        First quantum integer
    b : qint
        Second quantum integer

    Returns
    -------
    qint
        Sum of a and b

    Examples
    --------
    >>> a = qint(5, size=4)
    >>> b = qint(3, size=4)
    >>> result = add_integers(a, b)
    """
```

### Code Quality & Formatting

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **ruff** | 0.14.14 | Linting + Formatting | Latest (Jan 22, 2026). Replaces Black, Flake8, isort, pyupgrade. 10-100x faster. 800+ rules. Used by FastAPI, Pandas, PyTorch. | HIGH |
| **mypy** | Latest | Type checking | Static type analysis. Use with Ruff (Ruff doesn't do types). 99% clean commits when paired. | HIGH |
| **pre-commit** | Latest | Git hooks | Auto-run Ruff, mypy before commits. Standard for scientific Python. | HIGH |

**Why Ruff instead of Black:**
- Ruff formatter is 99.9% compatible with Black output (tested on Django, Zulip)
- Consolidates 5+ tools into one
- Fast enough to run on every file save
- Active development (weekly releases)

**Installation:**
```bash
pip install ruff==0.14.14 mypy pre-commit
```

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.14
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
```

**Order matters:** Run `ruff` (linter with --fix), then `ruff-format` (formatter), then `mypy` (types).

### Performance Profiling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Scalene** | Latest | CPU/GPU/memory profiler | AI-powered optimization suggestions. Line-level profiling. Separates Python vs native code time. Low overhead (10-20%). | HIGH |
| **cProfile** | Built-in | Function-level profiling | Python standard library. Works with Cython 3.1+ (sys.monitoring support). Good for quick checks. | HIGH |
| **perf** (Linux) | System tool | C-level profiling | Low overhead Linux profiler. Essential for C backend optimization. Use for Cython cdef functions. | MEDIUM |

**When to use:**
- **Scalene:** First profiling pass. Shows where time goes (Python vs C), memory growth.
- **cProfile:** Dive into Python/Cython layer after Scalene identifies hot spots.
- **perf:** Profile C backend directly. Lower overhead than cProfile for many small functions.

**Installation:**
```bash
pip install scalene
# perf: install via package manager (Linux only)
```

### CI/CD

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **GitHub Actions** | - | Continuous integration | Tight GitHub integration, flexible design. Recommended by Scientific Python Development Guide. Free for open source. | HIGH |
| **uv** | Latest (Astral) | Fast package management | Modern Python package installer (2025). 10-100x faster than pip. Manages Python versions. Used in recent CI setups. | MEDIUM |
| **pytest-cov** | Latest | Coverage reporting | Generate coverage reports in CI. Standard pytest plugin. | HIGH |

**GitHub Actions matrix:**
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    os: [ubuntu-latest, macos-latest, windows-latest]
```

**Why test on all platforms:** C compilation behavior differs (GCC vs Clang vs MSVC). Quantum Assembly has C backend, must verify cross-platform.

### Benchmarking

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **pytest-benchmark** | Latest | Python benchmarks | Microbenchmarking within pytest. Track performance regressions. | MEDIUM |
| **Custom scripts** | - | Circuit generation benchmarks | You already have `circuit-gen-results/`. Keep custom benchmarks. More relevant than generic frameworks. | HIGH |

**Recommendation:** Don't over-engineer benchmarking. Your existing approach (custom scripts comparing against Qiskit, Cirq, PennyLane) is perfect. Add pytest-benchmark for micro-optimizations only.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not | Confidence |
|----------|-------------|-------------|---------|------------|
| **Build System** | setuptools + cythonize | Meson | Cython support still minimal. Overkill for simple C files. | HIGH |
| **Build System** | setuptools + cythonize | scikit-build-core | Designed for CMake projects. You don't have CMake. | HIGH |
| **Formatter** | Ruff | Black | Ruff is Black-compatible but 10-100x faster and includes linting. | HIGH |
| **Linter** | Ruff | Flake8 | Ruff reimplements all Flake8 rules in Rust. Much faster. | HIGH |
| **Memory debugger** | Valgrind + ASan | Only Valgrind | ASan is fast enough for daily use. Valgrind too slow for every commit. | HIGH |
| **Docs** | Sphinx | mkdocs | Sphinx is standard for scientific Python. Better autodoc for C/Cython. | HIGH |
| **Python tester** | pytest | unittest | pytest has better fixtures, assertion introspection, plugin ecosystem. | HIGH |

## NOT Recommended

### Do NOT use:
1. **pytest-valgrind** - Plugin is unmaintained. Run Valgrind directly: `valgrind python -m pytest`
2. **Separate import sorter (isort)** - Ruff includes this. Don't add extra tools.
3. **Separate formatter (Black)** - Ruff formatter replaces it.
4. **Meson** (for now) - Premature. Revisit if C codebase grows 10x.
5. **CMake** - You have simple C files. Don't add build complexity.

## Installation Commands

### Core development dependencies:
```bash
# Package management
pip install --upgrade pip setuptools wheel

# Build dependencies
pip install Cython==3.2.4

# Testing
pip install pytest==9.0.2 pytest-cython==0.3.1 pytest-cov

# Code quality
pip install ruff==0.14.14 mypy pre-commit

# Documentation
pip install sphinx==9.1.0 numpydoc==1.11.0 myst-parser furo

# Profiling
pip install scalene

# Optional: Fast package management (2025 tooling)
pip install uv
```

### System dependencies (for memory debugging):
```bash
# Ubuntu/Debian
sudo apt-get install valgrind

# macOS
brew install valgrind  # Note: ARM Mac has limited support

# Compiler with sanitizers (usually pre-installed)
gcc --version  # Check for GCC
clang --version  # Check for Clang
```

### Setup pre-commit:
```bash
pre-commit install
```

## Compiler Flags Recommendations

### Current flags (from setup.py):
```python
compiler_args = ["-O3", "-flto", "-pthread"]
```

**Keep these.** They're correct for production builds.

### Add for development builds:
```python
# Debug + AddressSanitizer
debug_args = ["-g", "-O1", "-fsanitize=address", "-fno-omit-frame-pointer"]

# Debug + LeakSanitizer only
leak_check_args = ["-g", "-O1", "-fsanitize=leak"]
```

**Recommendation:** Create environment variable to switch:
```python
import os
if os.getenv("ASAN_BUILD"):
    compiler_args = ["-g", "-O1", "-fsanitize=address", "-fno-omit-frame-pointer"]
else:
    compiler_args = ["-O3", "-flto", "-pthread"]
```

**Usage:**
```bash
# Production build
python setup.py build_ext --inplace

# Development build with ASan
ASAN_BUILD=1 python setup.py build_ext --inplace
```

## Memory Management Patterns from Quantum Computing Ecosystem

### Hybrid C/Python architecture (your approach):
**Pattern:** C++ backend + Python interface
- **Examples:** Qiskit (C++ backend), Intel Quantum Simulator (C++ with shared/distributed memory)
- **Your architecture matches industry standard**

### Key patterns for quantum circuits:
1. **Qubit lifetime tracking:** Modern languages like Guppy use ownership annotations. For C/Python: track allocation/deallocation explicitly in C layer, expose lifetime to Python via context managers.

2. **Memory pools:** Pre-allocate gate/qubit structures instead of malloc per operation. Reduces fragmentation for large circuits.

3. **Circuit representation:** Full-state representation (what you have) vs dynamic state pruning (optimization for later).

4. **Shared-memory parallelization:** OpenMP for multi-core. Your `-pthread` flag suggests this direction.

### Recommendations for Quantum Assembly:
1. **Add ownership tracking:** Document which layer (C/Cython/Python) owns each allocation. Use comments: `/* Owned by: caller */`

2. **Use context managers for cleanup:**
```python
class QuantumCircuit:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._cleanup_c_resources()
```

3. **Memory pools for gates:** Instead of:
```c
gate_t* g = malloc(sizeof(gate_t));  // Every gate allocation
```
Do:
```c
gate_t* gate_pool = malloc(MAX_GATES * sizeof(gate_t));  // Once
gate_t* g = &gate_pool[next_gate_idx++];  // Per gate
```

4. **Clear allocation invariants:** Document in each C function:
```c
/**
 * Allocates new qint structure.
 * Caller must free with qint_free().
 * Returns NULL on allocation failure.
 */
qint_t* qint_create(size_t bits);
```

## Version Compatibility Matrix

| Component | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|-----------|-------------|-------------|-------------|-------------|
| Cython 3.2.4 | ✓ | ✓ | ✓ | ✓ |
| pytest 9.0.2 | ✓ | ✓ | ✓ | ✓ |
| Sphinx 9.1.0 | ✓ | ✓ | ✓ | ✓ |
| Ruff 0.14.14 | ✓ | ✓ | ✓ | ✓ |
| AddressSanitizer | ✓ | ✓ | ✓ | ✓ (enhanced) |

**Note:** Python 3.13 has best profiling support (sys.monitoring). Python 3.10 is minimum for pytest 9.x.

## Sources

### Cython & Scientific Python
- [Cython official documentation](https://cython.readthedocs.io/) - HIGH confidence
- [Cython PyPI page](https://pypi.org/project/Cython/) - Version 3.2.4 confirmed (Jan 2026) - HIGH confidence
- [Extending Python with Cython — Python for Scientific Computing](https://aaltoscicomp.github.io/python-for-scicomp/cython/) - HIGH confidence
- [An Empirical Study on the Performance and Energy Usage of Compiled Python Code](https://arxiv.org/html/2505.02346v1) - 2025 benchmarks - MEDIUM confidence

### Testing
- [pytest PyPI page](https://pypi.org/project/pytest/) - Version 9.0.2 confirmed (Dec 2025) - HIGH confidence
- [10 Best Python Testing Frameworks in 2025 - GeeksforGeeks](https://www.geeksforgeeks.org/python/best-python-testing-frameworks/) - MEDIUM confidence
- [pytest-cython PyPI page](https://pypi.org/project/pytest-cython/) - Version 0.3.1 confirmed - HIGH confidence
- [pytest-cython GitHub](https://github.com/lgpage/pytest-cython) - HIGH confidence

### Memory Debugging
- [Memory error checking in C and C++: Comparing Sanitizers and Valgrind | Red Hat Developer](https://developers.redhat.com/blog/2021/05/05/memory-error-checking-in-c-and-c-comparing-sanitizers-and-valgrind) - HIGH confidence
- [Valgrind Documentation Release 3.26.0](https://valgrind.org/docs/manual/valgrind_manual.pdf) - Version confirmed (Oct 2025) - HIGH confidence
- [Sanitizers, The Alternative To Valgrind - LinuxJedi](https://linuxjedi.co.uk/sanitizers-the-alternative-to-valgrind/) - MEDIUM confidence
- [Cython in Practice: A Deep Dive into Legacy C Integration and Debugging - PyCon US 2025](https://us.pycon.org/2025/schedule/presentation/56/) - 2025 conference - MEDIUM confidence

### Documentation
- [Sphinx PyPI page](https://pypi.org/project/Sphinx/) - Version 9.1.0 confirmed (Dec 2025) - HIGH confidence
- [Writing documentation - Scientific Python Development Guide](https://scientific-python-cookie.readthedocs.io/en/latest/guides/docs/) - HIGH confidence
- [numpydoc PyPI page](https://pypi.org/project/numpydoc/) - Version 1.11.0 confirmed (Dec 2025) - HIGH confidence
- [Style guide — numpydoc v1.11.0 Manual](https://numpydoc.readthedocs.io/en/latest/format.html) - HIGH confidence

### Code Quality
- [Ruff PyPI page](https://pypi.org/project/ruff/) - Version 0.14.14 confirmed (Jan 2026) - HIGH confidence
- [Ruff FAQ](https://docs.astral.sh/ruff/faq/) - HIGH confidence
- [Ruff Linting Rules 2025](https://www.johal.in/ruff-linting-rules-python-black-flake8-alternatives-configuration-2025/) - MEDIUM confidence
- [Ruff pre-commit GitHub](https://github.com/astral-sh/ruff-pre-commit) - HIGH confidence

### Build Systems
- [Scikit-build-core - SciPy Proceedings](https://proceedings.scipy.org/articles/FMKR8387) - HIGH confidence
- [Moving SciPy to the Meson build system | Quansight Labs](https://labs.quansight.org/blog/2021/07/moving-scipy-to-meson) - HIGH confidence
- [RFC: switch to Meson as a build system · Issue #13615 · scipy/scipy](https://github.com/scipy/scipy/issues/13615) - HIGH confidence

### CI/CD
- [A Github Actions setup for Python projects in 2025](https://ber2.github.io/posts/2025_github_actions_python/) - MEDIUM confidence
- [GHA: GitHub Actions intro - Scientific Python Development Guide](https://learn.scientific-python.org/development/guides/gha-basic/) - HIGH confidence
- [Building and testing Python - GitHub Docs](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python) - HIGH confidence

### Profiling
- [Scalene GitHub](https://github.com/plasma-umass/scalene) - HIGH confidence
- [CPU and Memory Profiling Python Code with Scalene | Medium](https://lynn-kwong.medium.com/cpu-and-memory-profiling-python-code-tools-and-techniques-with-scalene-in-focus-b0f016d73d40) - Nov 2025 - MEDIUM confidence
- [Profiling — Cython 3.3.0 documentation](https://cython.readthedocs.io/en/latest/src/tutorial/profiling_tutorial.html) - HIGH confidence

### Quantum Computing Architecture
- [Memory Management Strategies for Software Quantum Simulators - MDPI](https://www.mdpi.com/2624-960X/7/3/41) - HIGH confidence
- [Guppy: Programming the Next Generation of Quantum Computers](https://www.quantinuum.com/blog/guppy-programming-the-next-generation-of-quantum-computers) - MEDIUM confidence
- [Architectural patterns for designing quantum AI systems - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0164121225001244) - 2025 - MEDIUM confidence
- [Quantum Computing 2025: From Verifiable Advantage to Fault-Tolerant Architectures | Medium](https://nehalmr.medium.com/quantum-computing-2025-from-verifiable-advantage-to-fault-tolerant-architectures-201754bdd0a9) - Jan 2026 - MEDIUM confidence

## Confidence Assessment

| Category | Confidence | Reasoning |
|----------|-----------|-----------|
| **Cython & build** | HIGH | Versions verified via PyPI (Jan 2026). Your existing setup already correct. |
| **Testing frameworks** | HIGH | pytest 9.0.2 verified (Dec 2025), pytest-cython 0.3.1 verified (April 2024). |
| **Memory debugging** | HIGH | Valgrind 3.26.0 official docs (Oct 2025). ASan is LLVM standard. |
| **Documentation** | HIGH | Sphinx 9.1.0 + numpydoc 1.11.0 verified via PyPI (Dec 2025). |
| **Code quality** | HIGH | Ruff 0.14.14 verified (Jan 2026). Used by major projects. |
| **Profiling** | MEDIUM | Scalene actively developed, perf is Linux-standard. cProfile version-dependent behavior. |
| **Build alternatives** | MEDIUM | Meson/scikit-build info from 2021-2024 sources. Still evolving. |
| **CI/CD** | MEDIUM | GitHub Actions standard practice. uv is very new (2025), less proven. |
| **Quantum patterns** | MEDIUM | Web search results from 2025, not verified with official framework docs. |

## Summary

**Core stack (HIGH confidence):**
- Cython 3.2.4 for C/Python integration
- pytest 9.0.2 + pytest-cython 0.3.1 for testing
- Valgrind 3.26.0 + AddressSanitizer for memory debugging
- Sphinx 9.1.0 + numpydoc 1.11.0 for documentation
- Ruff 0.14.14 + mypy for code quality
- GitHub Actions for CI

**Keep your existing:**
- setuptools + cythonize build system
- GCC with `-O3 -flto -pthread` flags
- Custom benchmark scripts

**Add development mode:**
- ASan builds for daily memory debugging
- Pre-commit hooks for automatic linting
- Scalene for performance profiling

**Don't add (yet):**
- Meson/CMake (premature complexity)
- pytest-valgrind (unmaintained)
- Separate Black/Flake8/isort (Ruff replaces all)

This stack matches the 2025-2026 scientific Python ecosystem standard while staying lean for a mid-size quantum computing framework.
