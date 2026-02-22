# Coding Conventions

**Analysis Date:** 2026-02-22

## Naming Patterns

**Files:**
- Python source modules: `snake_case.py` (e.g., `amplitude_estimation.py`, `compile.py`)
- Cython extension modules: `snake_case.pyx` / `snake_case.pxd` (e.g., `_core.pyx`, `qint.pyx`)
- Private Cython includes: `snake_case.pxi` (e.g., `qint_arithmetic.pxi`)
- Internal/private modules prefixed with `_`: `_core.pyx`, `_gates.pyx`, `_core.pxd`
- C source files: `PascalCase.c` for domain objects (e.g., `ToffoliAdditionCLA.c`, `IntegerAddition.c`), `snake_case.c` for utilities (e.g., `circuit_allocations.c`, `qubit_allocator.c`)
- C headers: `PascalCase.h` for domain objects, `snake_case.h` for utilities (mirroring `.c` naming)
- Test files: `test_<feature_or_phase>.py` (e.g., `test_grover.py`, `test_phase15_initialization.py`)

**Functions:**
- Python: `snake_case` for all public and private functions
- Private/internal Python functions: leading underscore `_function_name` (e.g., `_grover_iterations`, `_resolve_widths`, `_simulate_single_shot`)
- C: `UPPER_CASE` for allocation/constructor functions that match the type name (e.g., `QINT`, `QBOOL`, `INT`)
- C helper functions: `snake_case` or `PascalCase_operation` (e.g., `allocator_alloc`, `CQ_add`, `QQ_add`)

**Variables:**
- Python: `snake_case` throughout (e.g., `register_widths`, `num_oracle_calls`, `theta_interval`)
- Constants: `UPPER_CASE` (e.g., `LAMBDA`, `SHOTS`, `HARDCODED_MAX_WIDTH`)
- C: `snake_case` for locals and struct fields (e.g., `quantum_int_t`, `circuit_t`, `qubit_t`)
- C macros: `UPPER_CASE` (e.g., `QINT_DEFAULT`, `M_PI`, `DEBUG_OWNERSHIP`)

**Classes:**
- Python: `PascalCase` (e.g., `CompiledFunc`, `CompiledBlock`, `AncillaRecord`, `AmplitudeEstimationResult`, `GroverOracle`)
- Private helper classes: leading underscore (e.g., `_InverseCompiledFunc`, `_AncillaInverseProxy`)
- C structs/typedefs: `snake_case_t` suffix (e.g., `quantum_int_t`, `circuit_t`, `qubit_t`, `sequence_t`)
- C header guards: `CQ_BACKEND_IMPROVED_<NAME>_H`

**Type Annotations:**
- Python functions use `type: return_type` in NumPy-style docstrings, not inline type hints
- Cython files (`.pyx`) use Cython's typed declarations (`cdef`, `cpdef`)
- Public API functions in pure Python use no inline annotations beyond occasional hints for documentation clarity

## Code Style

**Formatting:**
- Tool: Ruff (configured in `pyproject.toml`)
- Line length: 100 characters
- Target Python version: 3.11+
- String quotes: double quotes for all strings
- Indentation: 4 spaces
- Magic trailing comma: respected (skip-magic-trailing-comma = false)

**Linting:**
- Tool: Ruff with rule sets E, F, W, I, B, C4, UP
- E501 (line-too-long) is ignored (length handled by line-length setting)
- Import sorting enforced via `I` (isort-compatible)
- Pyupgrade rules enforced via `UP` (modern Python idioms)

**C Style:**
- LLVM style (per CLAUDE.md)
- Header guards use `#ifndef CQ_BACKEND_IMPROVED_<NAME>_H`
- Ownership comments on allocation functions (e.g., `// OWNERSHIP: Caller owns returned quantum_int_t*, must call free_element() when done`)
- `#ifdef DEBUG_OWNERSHIP` blocks for optional debug tracking

## Import Organization

**Order (Python):**
1. Standard library (e.g., `import inspect`, `import math`, `import gc`)
2. Third-party libraries (e.g., `import numpy as np`, `import pytest`, `import qiskit.qasm3`)
3. Internal package imports (e.g., `from ._core import circuit`, `from .qint import qint`)

**Path Aliases:**
- Package imported as `ql` in all user-facing code and tests: `import quantum_language as ql`
- Internal imports use relative paths: `from ._core import ...`, `from .qint import qint`
- Qiskit imported lazily inside functions that need it (not at module top-level), e.g., in `_simulate_single_shot` and `_simulate_multi_shot`

## Error Handling

**Patterns:**
- `ValueError` for invalid arguments (width out of range, missing required params, ambiguous combinations)
- `TypeError` for wrong argument types (e.g., unrecognized oracle types)
- `RecursionError` for depth-limit violations in compiled function nesting
- `ImportError` for optional dependency failures (e.g., Pillow for `draw_circuit`)
- `warnings.warn(message, stacklevel=N)` for soft failures and limit proximity alerts (e.g., approaching 17-qubit simulator limit, epsilon too small)
- Exception re-raise pattern in tests: `raise Exception(error_msg) from e` including QASM in message for debugging

**C Error Handling:**
- Return `NULL` on allocation failure
- Validate inputs at function entry with early return `NULL`
- Never silently ignore allocation failures

## Logging / Debug Output

**Framework:** `sys.stderr` via `print(..., file=sys.stderr)` for debug output

**Patterns:**
- Debug output gated behind `debug=True` parameter on `CompiledFunc`
- Debug stats exposed via `.stats` property, not printed unconditionally
- `#ifdef DEBUG_OWNERSHIP` C preprocessor blocks for C-level debug (compile-time opt-in)
- Production code produces no stdout output (only warnings via `warnings.warn`)

## Comments

**When to Comment:**
- Ownership semantics for C allocations (mandatory at every allocation site)
- Non-obvious algorithm steps (e.g., Qiskit bitstring endianness, BBHT growth factor source)
- Known limitations and workarounds (inline at the workaround location)
- Phase/requirement tracking in C files (e.g., `// CC_add removed (Phase 11)`)

**Docstrings:**
- All public Python functions and classes use NumPy-style docstrings
- Docstring sections: summary line, blank line, Parameters, Returns, Raises, Examples
- Module-level docstrings explain purpose, key algorithms, and usage examples
- Private functions (`_prefix`) also get docstrings explaining parameters and returns
- Cython files use module-level docstrings but lighter per-function docs

**Section Separators:**
- Long files use `# --- Section Name ---` (dashes) or `# ============ Name ============` (equals) comment banners
- Consistent 75-80 character width for separators

## Function Design

**Size:** Functions stay focused; large files are organized into logical sections with banner comments

**Parameters:**
- Keyword-only parameters for optional configuration: `def grover(oracle, *registers, width=None, widths=None, m=None, ...)`
- `*args` star-separator pattern used to force keyword-only arguments

**Return Values:**
- Prefer tuples for multi-value returns: `(value, iterations)`, `(lower, upper)`
- `None` as explicit no-result (not omitted)
- Typed return documented in docstring Returns section

## Module Design

**Exports:**
- Explicit `__all__` list in `src/quantum_language/__init__.py`
- Public API re-exported from submodules via `__init__.py` imports
- Internal helpers prefixed with `_` and not included in `__all__`

**Class Design:**
- `__slots__` used on performance-critical data classes (`CompiledBlock`, `AncillaRecord`)
- Properties used for computed/derived attributes (`estimate`, `num_oracle_calls`, `stats`)
- `functools.update_wrapper(self, func)` on decorator wrappers for `__name__` propagation
- `__repr__` defined on all wrapper classes

---

*Convention analysis: 2026-02-22*
