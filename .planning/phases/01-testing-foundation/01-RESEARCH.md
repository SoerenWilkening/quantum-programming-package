# Phase 1: Testing Foundation - Research

**Researched:** 2026-01-25
**Domain:** Python testing (pytest), C memory testing (Valgrind/ASan), pre-commit automation
**Confidence:** HIGH

## Summary

This research identifies the standard testing stack for establishing characterization tests before refactoring a mixed C/Python quantum computing framework. The project has approximately 2,400 lines of C code across 9 source files and a Cython Python binding layer, with currently zero automated tests. The established approach combines pytest with snapshot/approval testing for Python, Unity for C backend testing, Valgrind and AddressSanitizer for memory validation, and pre-commit hooks for code quality enforcement.

Key findings: characterization tests capture current behavior as golden masters, enabling safe refactoring. Memory testing requires both Valgrind (comprehensive but slow) and ASan (fast but requires recompilation). Pre-commit hooks must enforce quality gates without blocking emergency fixes.

**Primary recommendation:** Use pytest with approvaltests for characterization testing, Unity for C unit tests, separate make targets for ASan vs Valgrind checks, and pre-commit framework with Ruff + clang-format configured to auto-fix and allow bypass.

## Standard Stack

The established libraries/tools for this domain:

### Core Testing
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x | Python test runner and framework | Industry standard, rich plugin ecosystem, parametrization support |
| approvaltests | 15.x | Snapshot/characterization testing | Purpose-built for golden master testing, diff tool integration |
| Unity | 2.5.x+ | C unit testing framework | Lightweight, embedded-friendly, pure C, single-file integration |
| pytest-valgrind | Latest | Integrate Valgrind with pytest | Enables per-test leak detection instead of just at exit |

### Memory Testing
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Valgrind | 3.22+ | Comprehensive memory error detection | Deep analysis, no recompilation needed, CI/CD validation |
| AddressSanitizer | Built into GCC/Clang | Fast memory error detection | Development workflow, rapid iteration |
| LeakSanitizer | Part of ASan | Memory leak detection | Complement to ASan for leak-specific checks |

### Code Quality
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pre-commit | 3.x+ | Git hook framework | Automate quality checks on every commit |
| Ruff | 0.14.14+ | Python linter and formatter | Replaces Black, Flake8, isort - all-in-one tool |
| clang-format | 18.x+ | C/C++ code formatter | Standard C formatting, configurable style |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| approvaltests | syrupy (pytest-snapshot) | Syrupy integrates better with pytest but approvaltests has superior diff tool support |
| Unity | Check, Criterion | Check offers process isolation (safer), Criterion has modern features, but Unity is simplest for embedded/pure C |
| Valgrind | Dr. Memory | Dr. Memory works on Windows, but Valgrind has better Linux support and maturity |

**Installation:**
```bash
# Python dependencies
pip install pytest approvaltests pytest-valgrind

# C testing (Unity - manual integration)
# Download unity.c and unity.h from github.com/ThrowTheSwitch/Unity

# Memory testing
sudo apt-get install valgrind  # Linux
# ASan: built into GCC/Clang, use -fsanitize=address flag

# Pre-commit
pip install pre-commit
pre-commit install
```

## Architecture Patterns

### Recommended Project Structure
```
.
├── tests/
│   ├── python/                 # Python characterization tests
│   │   ├── test_qint_operations.py
│   │   ├── test_qbool_operations.py
│   │   ├── test_circuit_generation.py
│   │   └── approvals/          # Golden master files (.approved.txt)
│   ├── c/                      # C unit tests
│   │   ├── test_gate.c
│   │   ├── test_integer_addition.c
│   │   └── test_circuit_allocations.c
│   └── integration/            # End-to-end tests
│       └── test_full_pipeline.py
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
├── .clang-format               # C formatting rules
├── Makefile                    # Test targets (test, memtest, asan-test)
└── pytest.ini                  # Pytest configuration
```

### Pattern 1: Characterization Test with Approval Testing
**What:** Capture current behavior as golden master, compare future runs against it
**When to use:** Before refactoring existing code whose behavior must be preserved
**Example:**
```python
# tests/python/test_qint_operations.py
import pytest
from approvaltests.approvals import verify
import quantum_language as ql

def test_qint_addition_generates_expected_circuit():
    """Characterization test: QInt addition circuit structure"""
    # Arrange
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)

    # Act
    c = a + b

    # Capture circuit output
    circuit_output = capture_circuit_output(c)

    # Assert: compare to golden master
    verify(circuit_output)
```

### Pattern 2: Parametrized Operation Tests
**What:** Test same operation with multiple input configurations
**When to use:** Testing operations that work across different bit widths or value ranges
**Example:**
```python
# tests/python/test_qint_operations.py
import pytest
import quantum_language as ql

@pytest.mark.parametrize("bits,val_a,val_b", [
    (4, 5, 3),    # 4-bit integers
    (8, 100, 50), # 8-bit integers
    (16, 1000, 2000), # 16-bit integers
])
def test_qint_addition_various_widths(bits, val_a, val_b):
    """Test addition works across different bit widths"""
    a = ql.qint(value=val_a, bits=bits)
    b = ql.qint(value=val_b, bits=bits)
    c = a + b

    # Verify circuit was generated without errors
    assert c is not None
    assert c.bits == bits
```

### Pattern 3: C Unit Test with Unity
**What:** Minimal C test using Unity's TEST macro and assertions
**When to use:** Testing C backend functions in isolation
**Example:**
```c
// tests/c/test_gate.c
#include "unity.h"
#include "gate.h"

void setUp(void) {
    // Runs before each test
}

void tearDown(void) {
    // Runs after each test
}

void test_gate_creation_initializes_fields(void) {
    gate_t g;
    x(&g, 0);  // Create X gate on qubit 0

    TEST_ASSERT_EQUAL(X, g.Gate);
    TEST_ASSERT_EQUAL(0, g.Target);
    TEST_ASSERT_EQUAL(0, g.NumControls);
}

void test_controlled_gate_sets_control_qubit(void) {
    gate_t g;
    cx(&g, 1, 0);  // CX with control=0, target=1

    TEST_ASSERT_EQUAL(CX, g.Gate);
    TEST_ASSERT_EQUAL(1, g.Target);
    TEST_ASSERT_EQUAL(1, g.NumControls);
    TEST_ASSERT_EQUAL(0, g.Control[0]);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_gate_creation_initializes_fields);
    RUN_TEST(test_controlled_gate_sets_control_qubit);
    return UNITY_END();
}
```

### Pattern 4: Makefile Test Targets
**What:** Separate targets for unit tests, memory tests, and quick checks
**When to use:** Always - enables developer choice of test depth
**Example:**
```makefile
# Quick tests - run frequently during development
.PHONY: test
test:
	pytest tests/python -v
	./build/test_runner  # Unity C tests

# Memory leak detection with Valgrind (slow, comprehensive)
.PHONY: memtest
memtest:
	PYTHONMALLOC=malloc valgrind --leak-check=full --error-exitcode=1 \
		python -m pytest tests/python -v
	valgrind --leak-check=full --error-exitcode=1 ./build/test_runner

# Fast memory testing with AddressSanitizer
.PHONY: asan-test
asan-test:
	$(CC) -fsanitize=address -g -O1 $(CFLAGS) tests/c/*.c Backend/src/*.c -o build/test_runner_asan
	./build/test_runner_asan

# Pre-commit validation (what hooks will check)
.PHONY: check
check:
	pre-commit run --all-files
	pytest tests/python -v --tb=short
```

### Anti-Patterns to Avoid
- **Testing implementation details:** Don't test internal gate sequences, test circuit behavior (gate counts, qubit usage, output correctness)
- **Brittle golden masters:** Include normalization in approval tests to ignore irrelevant formatting differences
- **Mixing memory test modes:** Don't run Valgrind and ASan in same build - they conflict
- **Blocking commits unconditionally:** Pre-commit should allow bypass for emergencies (`--no-verify`)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diff visualization | Custom text comparison | approvaltests + diff tool integration | Handles diff tools (Beyond Compare, KDiff3, etc.), cross-platform |
| Test discovery | Manual test registration | pytest discovery (test_*.py) | Automatic, standard, supports parallel execution |
| Memory leak detection | Manual malloc tracking | Valgrind/ASan | Detects use-after-free, buffer overflows, uninitialized reads |
| Circuit output capture | Custom stdout redirection | pytest capsys fixture | Built-in, reliable, testable |
| Parametrized tests | Loop-based tests | @pytest.mark.parametrize | Better reporting, isolated failures, parallel execution |
| Code formatting | Manual style checks | Ruff + clang-format | Auto-fix, fast, comprehensive |

**Key insight:** Testing infrastructure is complex - snapshot comparison, process isolation, memory tracking all have edge cases that mature tools handle. Custom testing code becomes technical debt that distracts from actual feature work.

## Common Pitfalls

### Pitfall 1: Valgrind Python Compatibility
**What goes wrong:** Valgrind reports false positives from Python's memory allocator
**Why it happens:** Python uses its own memory pool (pymalloc) that Valgrind sees as leaks
**How to avoid:** Use `PYTHONMALLOC=malloc` environment variable to disable pymalloc
**Warning signs:** Many "possibly lost" blocks in Python code
**Fix:**
```bash
# Wrong - pymalloc causes false positives
valgrind python -m pytest tests/

# Correct - use system malloc
PYTHONMALLOC=malloc valgrind --leak-check=full python -m pytest tests/
```

### Pitfall 2: ASan Runtime Conflicts
**What goes wrong:** Cannot combine ASan with Valgrind in same run
**Why it happens:** Both tools instrument memory operations; they conflict
**How to avoid:** Use separate make targets (asan-test vs memtest)
**Warning signs:** "ASan runtime does not come first" error message
**Fix:**
```makefile
# Separate targets - never run together
asan-test: CFLAGS += -fsanitize=address
asan-test: build test

memtest: build
	valgrind --leak-check=full ./test_runner
```

### Pitfall 3: Approval Test File Organization
**What goes wrong:** Approved files scattered, hard to manage, accidentally committed
**Why it happens:** Default approvaltests configuration creates files next to tests
**How to avoid:** Configure output directory, add to .gitignore carefully
**Warning signs:** `.approved.txt` files throughout source tree
**Fix:**
```python
# tests/python/conftest.py
from approvaltests.approvals import set_default_reporter
from approvaltests.reporters import GenericDiffReporter

# Configure approval file location
def pytest_configure(config):
    # Files saved to tests/python/approvals/
    set_default_reporter(GenericDiffReporter.create("diff"))
```

### Pitfall 4: Pre-commit Hook Too Strict
**What goes wrong:** Developers bypass hooks with --no-verify, defeating purpose
**Why it happens:** Hooks run slow tests or block urgent hotfixes
**How to avoid:** Only fast checks in pre-commit, full suite in CI
**Warning signs:** Frequent `git commit --no-verify` in team
**Fix:**
```yaml
# .pre-commit-config.yaml - only fast checks
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.14
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-clang-format
    rev: v18.1.4
    hooks:
      - id: clang-format

# DO NOT include slow tests in pre-commit
# Run pytest in CI instead
```

### Pitfall 5: Characterization Tests Without Cleanup
**What goes wrong:** Tests capture uninitialized memory or timing-dependent output
**Why it happens:** Circuit output includes memory addresses or timestamps
**How to avoid:** Normalize output before approval comparison
**Warning signs:** Approval tests fail randomly with same code
**Fix:**
```python
def normalize_circuit_output(output: str) -> str:
    """Remove non-deterministic elements from circuit output"""
    import re
    # Remove memory addresses (0x...)
    output = re.sub(r'0x[0-9a-fA-F]+', '0xADDRESS', output)
    # Remove timing information
    output = re.sub(r'\d+\.\d+s', 'TIME', output)
    return output

def test_circuit_generation():
    output = get_circuit_output()
    normalized = normalize_circuit_output(output)
    verify(normalized)
```

## Code Examples

Verified patterns from official sources:

### Pytest Fixture for Circuit Initialization
```python
# tests/python/conftest.py
import pytest
import quantum_language as ql

@pytest.fixture
def clean_circuit():
    """Provides a fresh circuit for each test"""
    circ = ql.circuit()
    yield circ
    # Cleanup happens automatically via Python GC
    # but explicit cleanup could go here if needed

@pytest.fixture
def sample_qints():
    """Provides sample quantum integers for testing"""
    return {
        'small': ql.qint(value=5, bits=4),
        'medium': ql.qint(value=100, bits=8),
        'large': ql.qint(value=5000, bits=16)
    }
```

### Unity Test Runner Pattern
```c
// tests/c/test_runner.c
#include "unity.h"

// Declare test functions
void test_gate_creation(void);
void test_integer_addition(void);
void test_circuit_allocation(void);

void setUp(void) {}
void tearDown(void) {}

int main(void) {
    UNITY_BEGIN();

    // Gate tests
    RUN_TEST(test_gate_creation);

    // Integer operation tests
    RUN_TEST(test_integer_addition);

    // Circuit tests
    RUN_TEST(test_circuit_allocation);

    return UNITY_END();
}
```

### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
# Source: https://github.com/astral-sh/ruff-pre-commit
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.14
    hooks:
      # Run linter with auto-fix
      - id: ruff-check
        args: [--fix]
      # Run formatter
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-clang-format
    rev: v18.1.4
    hooks:
      - id: clang-format
        types_or: [c, c++]
```

### Pytest Configuration
```ini
# pytest.ini
[pytest]
testpaths = tests/python
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
```

### Makefile Memory Test Integration
```makefile
# Source: https://gist.github.com/Cxarli/b29e613e54a50146c5b2a6e9790112f8
# Makefile with ASan and Valgrind targets

CC = gcc
CFLAGS = -Wall -Wextra -g -O2
ASAN_FLAGS = -fsanitize=address -fno-omit-frame-pointer
SOURCES = Backend/src/*.c
TEST_SOURCES = tests/c/*.c

.PHONY: test asan-test memtest

test:
	$(CC) $(CFLAGS) $(SOURCES) $(TEST_SOURCES) -o build/test_runner
	./build/test_runner

asan-test:
	$(CC) $(CFLAGS) $(ASAN_FLAGS) $(SOURCES) $(TEST_SOURCES) -o build/test_runner_asan
	./build/test_runner_asan

memtest: test
	valgrind --leak-check=full --show-leak-kinds=all \
		--error-exitcode=1 \
		./build/test_runner
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| unittest | pytest | 2015+ | Simpler syntax, better parametrization, rich plugin ecosystem |
| nose | pytest | 2016+ | nose unmaintained, pytest is standard |
| Manual approval testing | approvaltests/syrupy | 2020+ | Automated diff tools, better DX |
| Check (C testing) | Unity/Criterion | 2018+ | Unity lighter weight, Criterion has modern features |
| Print debugging | Valgrind/ASan | Always used, but better tooling | CI integration, automated leak detection |
| Black + isort + Flake8 | Ruff | 2023-2024 | 10-100x faster, single tool |

**Deprecated/outdated:**
- nose: Unmaintained since 2016, use pytest
- Python 2 unittest discover: Python 3's pytest is standard
- Custom snapshot testing: Use established libraries (approvaltests, syrupy)
- Manual .clang-format rules: Use preset styles (Google, LLVM, Mozilla) as base

## Open Questions

1. **Characterization Test Granularity**
   - What we know: Can test at operation level (qint + qint) or circuit level (full algorithm)
   - What's unclear: Optimal balance between test count and coverage
   - Recommendation: Start with operation-level tests for all existing operations (addition, subtraction, comparison, logic), add circuit-level for complex algorithms (QFT benchmarks)

2. **Unity Integration in CMake**
   - What we know: Unity is single-file C library, easy to integrate
   - What's unclear: CMake vs Makefile for test builds (project uses both)
   - Recommendation: Use Makefile for test targets (simpler, matches existing pattern), CMake for main build

3. **Valgrind Performance Impact on CI**
   - What we know: Valgrind slows tests 10-50x, ASan only 2-3x
   - What's unclear: Whether to run Valgrind on every commit or nightly
   - Recommendation: ASan in pre-commit/PR checks, Valgrind nightly or weekly deep analysis

## Sources

### Primary (HIGH confidence)
- [pytest documentation](https://docs.pytest.org/) - Official pytest docs on parametrization and fixtures
- [approvaltests GitHub](https://github.com/approvals/ApprovalTests.Python) - Official Python approval testing library
- [Unity GitHub](https://github.com/ThrowTheSwitch/Unity) - Official Unity C testing framework
- [Ruff pre-commit](https://github.com/astral-sh/ruff-pre-commit) - Official Ruff pre-commit integration
- [AddressSanitizer Wiki](https://github.com/google/sanitizers/wiki) - Official ASan documentation
- [Valgrind Manual](https://valgrind.org/docs/manual/) - Official Valgrind documentation

### Secondary (MEDIUM confidence)
- [Valgrind vs AddressSanitizer](https://undo.io/resources/gdb-watchpoint/a-quick-introduction-to-using-valgrind-and-addresssanitizer/) - Comparison of memory testing tools
- [Pre-commit Hooks Guide 2025](https://gatlenculp.medium.com/effortless-code-quality-the-ultimate-pre-commit-hooks-guide-for-2025-57ca501d9835) - Modern pre-commit practices
- [C Unit Testing Framework Comparison](https://www.throwtheswitch.org/comparison-of-unit-test-frameworks) - Unity vs Check vs others
- [Makefile with ASan/Valgrind](https://gist.github.com/Cxarli/b29e613e54a50146c5b2a6e9790112f8) - Integration pattern example

### Tertiary (LOW confidence)
- Various Medium articles on pytest best practices - cross-referenced with official docs
- Stack Overflow discussions on Valgrind Python compatibility - verified with official Valgrind docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest, Unity, Valgrind, ASan are industry standards with extensive documentation
- Architecture: HIGH - patterns verified from official documentation and established projects
- Pitfalls: HIGH - documented in official sources (Valgrind Python issues, ASan conflicts)
- Quantum-specific testing: MEDIUM - general testing patterns applied to quantum domain, no quantum-specific testing frameworks found

**Research date:** 2026-01-25
**Valid until:** 60 days (testing tools are stable, slow-moving domain)

**Project-specific notes:**
- Codebase has ~2,400 LOC C code with zero existing unit tests
- Current test.py is example/integration test, not test suite
- Memory bugs documented in CONCERNS.md (malloc without checks, sizeof errors, uninitialized sequences)
- Precompilation optimization in IntegerAddition.c must be tested carefully (cache invalidation issues)
- Global state (QPU_state, circuit) requires test isolation
