# Coding Conventions

**Analysis Date:** 2026-02-22

## Naming Patterns

**Files:**
- Python source: `snake_case.py` (e.g., `amplitude_estimation.py`, `grover.py`, `oracle.py`)
- Cython extension source: `snake_case.pyx` / `snake_case.pxd` (e.g., `_core.pyx`, `qint.pyx`, `openqasm.pyx`)
- Cython include splits: `snake_case.pxi` (e.g., `qint_arithmetic.pxi`, `qint_bitwise.pxi`, `qint_comparison.pxi`, `qint_division.pxi`)
- C source: `PascalCase.c` for domain modules (e.g., `IntegerAddition.c`, `ToffoliMultiplication.c`, `LogicOperations.c`); `snake_case.c` for infrastructure (e.g., `qubit_allocator.c`, `circuit_stats.c`, `gate.c`)
- C headers: `snake_case.h` for infrastructure; `PascalCase.h` for domain (e.g., `qubit_allocator.h`, `circuit.h`, `Integer.h`, `QPU.h`)
- Test files Python: `test_<feature>.py` or `test_phase<N>_<feature>.py` (e.g., `test_grover.py`, `test_phase15_initialization.py`)
- Test files C: `test_<target>.c` (e.g., `test_allocator_block.c`, `test_reverse_circuit.c`)

**Functions (Python/Cython):**
- Public API functions: `snake_case` (e.g., `amplitude_estimate`, `grover_oracle`, `to_openqasm`, `diffusion`)
- Private helpers: `_snake_case` with leading underscore (e.g., `_grover_iterations`, `_resolve_widths`, `_bbht_search`, `_simulate_single_shot`, `_parse_bitstring`)
- Private helpers reused across modules are imported explicitly: `from .grover import _apply_hadamard_layer, _ensure_oracle, _parse_bitstring`

**Functions (C):**
- Domain operations: `OperandType_operation(args)` (e.g., `CQ_add`, `QQ_mul`, `allocator_create`, `allocator_free`, `allocator_alloc`)
- Static internal helpers: `static void helper_name(void)` with `static` keyword
- C test functions: `static void test_description(void)` (e.g., `test_block_alloc_contiguous`, `test_coalesce_three_way`)

**Variables (Python):**
- Local variables: `snake_case` (e.g., `register_widths`, `oracle_func`, `qasm_str`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `LAMBDA = 6 / 5`, `FREED_BLOCKS_INITIAL_SIZE = 32`)
- Private instance fields: `_snake_case` (e.g., `self._estimate`, `self._num_oracle_calls`, `self._confidence_interval`)

**Types (Python):**
- Classes: `PascalCase` (e.g., `AmplitudeEstimationResult`, `CompiledFunc`, `GroverOracle`)
- Public quantum types use lowercase by design: `qint`, `qbool`, `qarray`, `qint_mod`

**Types (C):**
- Struct typedefs: `snake_case_t` suffix (e.g., `qubit_allocator_t`, `allocator_stats_t`, `qubit_block_t`, `gate_t`, `circuit_t`)
- Primitive typedefs: `qubit_t`, `num_t`
- Enum typedef: `Standardgate_t`
- Macros and constants: `UPPER_SNAKE_CASE` (e.g., `ALLOCATOR_MAX_QUBITS`, `FREED_BLOCKS_INITIAL_SIZE`)

## Code Style

**Formatting (Python/Cython):**
- Tool: `ruff` (configured in `pyproject.toml`)
- Line length: 100 characters
- Target version: Python 3.11
- Quote style: double quotes
- Indent style: 4 spaces
- Linting rules enabled: E (pycodestyle errors), F (pyflakes), W (pycode warnings), I (isort), B (bugbear), C4 (comprehensions), UP (pyupgrade)
- E501 (line length) is ignored in linting — handled separately by `line-length` setting

**Formatting (C):**
- LLVM style (per `CLAUDE.md`)
- Header guard pattern: `#ifndef MODULE_H` / `#define MODULE_H` / `#endif // MODULE_H`
- Debug-conditional blocks: `#ifdef DEBUG` and `#ifdef DEBUG_OWNERSHIP` wrap optional instrumentation

## Import Organization

**Python import order (enforced by ruff isort):**
1. Standard library (e.g., `import math`, `import gc`, `import inspect`, `import warnings`)
2. Third-party (e.g., `import numpy as np`, `import pytest`, `import qiskit.qasm3`, `from qiskit_aer import AerSimulator`)
3. Local package with relative imports (e.g., `from ._core import circuit, option`, `from .qint import qint`)

**Path aliases:**
- Package always imported as `import quantum_language as ql` in tests and downstream code
- Internal imports use relative paths: `from ._core import ...`, `from .grover import _apply_hadamard_layer`

**Test-specific patterns:**
- Tests add `tests/` to `sys.path` when importing shared helpers across directories:
  ```python
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
  from verify_helpers import generate_exhaustive_pairs, generate_sampled_pairs
  ```
- Shared test helpers live in `tests/verify_helpers.py` and `tests/conftest.py` (root) and `tests/python/conftest.py`

**C include order:**
1. Implementation's own header (e.g., `#include "qubit_allocator.h"`)
2. Other project headers (e.g., `#include "QPU.h"`)
3. Standard library (e.g., `#include <stdlib.h>`, `#include <stdio.h>`, `#include <string.h>`)

## Error Handling

**Python patterns:**
- `ValueError` for invalid parameters (e.g., width out of range 1-64, mismatched moduli, `widths` length mismatch, missing required `width`/`widths`)
- `ZeroDivisionError` for division by zero
- `TypeError` for wrong argument types
- `NotImplementedError` with actionable message: `"qint_mod * int"` tells user correct form
- `ImportError` with install instructions for optional dependencies (e.g., Pillow for visualization)
- Simulation errors include QASM in message for debugging:
  ```python
  raise Exception(f"Simulation failed: {str(e)}\n\nOpenQASM 3.0:\n{qasm_str}") from e
  ```

**Python warnings:**
- `warnings.warn(..., stacklevel=N)` for non-fatal issues: qubit limit approach, value truncation overflow, IQAE `max_iterations` cap hit
- Tests assert warnings with `pytest.warns(UserWarning, match="pattern")`

**C patterns:**
- Return `NULL` on allocation failure; callers always check for `NULL` before use
- Return `(qubit_t)-1` for invalid qubit allocation (sentinel value)
- Return `0` on success, `-1` on error (e.g., `allocator_free` returns `-1` on double-free)
- `assert()` for internal invariants; active in debug builds
- Memory ownership documented inline:
  ```c
  // OWNERSHIP: Caller owns returned qubit_allocator_t*, must call allocator_destroy()
  ```

**Known bug tracking:**
- Known bugs are tracked inline in comments and test code with codes like `BUG-QFT-DIV`, `BUG-CQQ-QFT`, `BUG-MOD-REDUCE`, `BUG-COND-MUL-01`
- Corresponding test cases use `pytest.mark.xfail(reason="BUG-X: explanation", strict=False)` to document and track failures without blocking CI

## Logging

**Framework:** None (no structured logging framework in production code)

**Patterns:**
- C test suite uses `printf("test_name... ")` followed by `printf("PASS\n")` with `fflush(stdout)` for progress indication
- Python production code has no `print()` or logging calls; debug information surfaces only via exception messages
- No `logging` module usage observed

## Comments

**Python docstrings:**
- All public functions and classes have NumPy-style docstrings with `Parameters`, `Returns`, `Raises`, and `Examples` sections
- Private helper functions also document parameters, returns, and raises
- Module-level docstrings summarize purpose, calling styles, and usage examples with `>>>` code blocks
- Test function docstrings: one-line explaining what is verified and the expected outcome (e.g., `"N=8, M=1 -> k=1 (floor(pi/4 * sqrt(8) - 0.5) = floor(1.72) = 1)."`)

**C documentation:**
- Every C header function has Doxygen-style block comment with `@file`, `@brief`, `@param`, `@return`
- Complex algorithm sections get inline comments explaining non-obvious logic
- Phase/plan attribution in section dividers: `/* ------------------------------------------------------------------ */` with description
- Known bugs documented inline: `// BUG-QFT-DIV: QFT division broken at width 3+`

## Function Design

**Size:** Functions are focused; helper functions are extracted aggressively. `grover.py` has 8 private helpers before the public `grover()` function.

**Parameters (Python):**
- Use keyword-only arguments for optional configuration:
  ```python
  def grover(oracle, *registers, width=None, widths=None, m=None, iterations=None, max_attempts=None):
  ```
- `None` defaults handled explicitly with conditional dispatch

**Return Values (Python):**
- Typed returns documented in docstring; no bare `None` returns from meaningful operations
- Tuple returns documented: `Returns (actual, expected) tuple`, `Returns (*values, total_iterations)`
- `AmplitudeEstimationResult` wraps float with metadata and supports arithmetic operators directly

**Return Values (C):**
- Return codes: `0` success, `-1` error
- Sentinel values: `NULL`, `(qubit_t)-1`
- Caller-owned allocations documented with `OWNERSHIP:` comment

## Module Design

**Exports (Python):**
- Explicit `__all__` in `src/quantum_language/__init__.py` listing all public API symbols
- All quantum types and algorithms re-exported from `__init__.py`: `qint`, `qbool`, `qarray`, `qint_mod`, `circuit`, `grover`, `amplitude_estimate`, `compile`, `diffusion`, `to_openqasm`, etc.
- Private internals (prefixed `_`) not in `__all__` but importable for tests

**Barrel file:**
- `src/quantum_language/__init__.py` is the single barrel; all test code uses `import quantum_language as ql`

**Cython module split:**
- `_core.pyx`, `_gates.pyx` — low-level C bindings (underscore prefix indicates internal)
- `qint.pyx`, `qbool.pyx`, `qarray.pyx`, `qint_mod.pyx`, `openqasm.pyx` — quantum type implementations
- `qint_arithmetic.pxi`, `qint_bitwise.pxi`, `qint_comparison.pxi`, `qint_division.pxi` — `.pxi` include files split out of `qint.pyx` to keep file size manageable

---

*Convention analysis: 2026-02-22*
