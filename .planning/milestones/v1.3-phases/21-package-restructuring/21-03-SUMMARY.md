---
phase: 21
plan: 03
subsystem: package-api
tags: [python, api-design, package-structure]
requires: ["21-01", "21-02"]
provides:
  - Public API surface via __init__.py
  - state/ subpackage for state management
  - Clean import interface (import quantum_language as ql)
affects: ["21-04", "21-05"]
tech-stack:
  added: []
  patterns:
    - "Re-export pattern for subpackage organization"
    - "Wrapper functions for default parameter injection"
key-files:
  created:
    - src/quantum_language/__init__.py
    - src/quantum_language/state/__init__.py
    - src/quantum_language/state/__init__.pxd
  modified: []
decisions:
  - decision: "Use re-export pattern for state subpackage"
    rationale: "Simpler than creating separate qpu.pyx/uncompute.pyx - avoids cdef global state duplication across modules"
  - decision: "array() wrapper in __init__.py injects default dtype=qint"
    rationale: "Avoids circular import - _core.array() can't reference qint since qint.pyx imports from _core"
  - decision: "State functions accessible both top-level and via subpackage"
    rationale: "Convenience for both ql.circuit_stats() and ql.state.circuit_stats() access patterns"
metrics:
  duration: "140 seconds (~2 min)"
  completed: "2026-01-29"
---

# Phase 21 Plan 03: Public API Surface Summary

**One-liner:** Created clean import interface with __init__.py exposing qint/qbool/qint_mod types and state subpackage.

## What Changed

### Created Files

**src/quantum_language/__init__.py** (~100 lines)
- Module docstring with usage examples
- Imports: qint, qbool, qint_mod types from respective modules
- Imports: circuit, option from _core
- Re-exports: circuit_stats, get_current_layer, reverse_instruction_range from _core
- Wrapper: array() function that injects default dtype=qint parameter
- __all__ list defining public API
- __version__ = "0.1.0"

**src/quantum_language/state/__init__.py** (~15 lines)
- Module docstring
- Re-exports: circuit_stats, get_current_layer, reverse_instruction_range from _core
- __all__ list for state subpackage

**src/quantum_language/state/__init__.pxd** (empty)
- Enables `from quantum_language.state cimport ...` syntax

## Technical Details

### Import Structure

```python
# Top-level package
import quantum_language as ql

# Types (top-level)
ql.qint, ql.qbool, ql.qint_mod

# Utilities (top-level)
ql.circuit(), ql.array(), ql.option()

# State management (both access patterns work)
ql.circuit_stats()            # Top-level convenience
ql.state.circuit_stats()      # Subpackage organization
```

### array() Wrapper Pattern

The __init__.py defines an array() wrapper that injects the default dtype:

```python
from quantum_language._core import array as _array_impl

def array(dim, dtype=None):
    if dtype is None:
        dtype = qint
    return _array_impl(dim, dtype)
```

This is necessary because _core.pyx cannot import qint (circular dependency - qint.pyx imports from _core).

### Re-export Pattern

State subpackage uses simple re-exports rather than duplicating function implementations:

```python
# state/__init__.py
from quantum_language._core import circuit_stats, get_current_layer, reverse_instruction_range
```

This avoids the complexity of sharing cdef global state (_circuit, _circuit_initialized) across Cython modules.

## Decisions Made

1. **Re-export pattern for state subpackage**
   - Keep implementations in _core.pyx
   - Re-export from state/__init__.py
   - Avoids cdef global state duplication
   - Simpler than creating separate qpu.pyx/uncompute.pyx modules

2. **array() wrapper injects default dtype**
   - _core.array() takes explicit dtype parameter
   - __init__.py wrapper defaults to qint
   - Avoids circular import (qint.pyx → _core, _core → qint)

3. **Dual access pattern for state functions**
   - Top-level: `ql.circuit_stats()` (convenience)
   - Subpackage: `ql.state.circuit_stats()` (organization)
   - Both work, users choose based on preference

4. **Explicit __all__ lists**
   - Enables static analysis tools
   - Controls wildcard imports
   - Documents public API surface

## Task Breakdown

| Task | Description | Commits |
|------|-------------|---------|
| 1 | Create state subpackage | bba5a5c |
| 2 | Create main __init__.py | 71d775a |

**Total commits:** 2 (both task commits)

## Testing Impact

No tests needed - this is pure package structure:
- No new behavior
- Only organizing existing functionality
- Import statements can be validated via Python import system

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Blockers:** None

**Recommendations:**
- Next plan (21-04) should verify package can be built with setuptools
- Consider testing import patterns in a fresh Python environment
- Verify Cython compilation works with new __init__.py

**Notes:**
- Package is now importable as `import quantum_language as ql`
- All type classes and utilities accessible at top level
- State management organized in subpackage
- Ready for build system integration (21-04)
