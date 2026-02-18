# Phase 26: Python API Bindings - Research

**Researched:** 2026-01-30
**Domain:** Cython Python/C API bindings, setuptools package configuration, optional dependencies
**Confidence:** HIGH

## Summary

Phase 26 creates Python bindings for the C backend's OpenQASM 3.0 export functionality. The implementation uses Cython to wrap `circuit_to_qasm_string()` (added in Phase 25) with proper memory management using try-finally blocks and explicit free() calls. The wrapper lives in a new `openqasm.pyx` module and is re-exported at package level as `ql.to_openqasm()`.

The standard approach is well-established: Cython provides C string → Python string conversion with automatic copying, malloc'd buffers must be freed in finally blocks to prevent leaks, and setup.py uses the existing Extension auto-discovery pattern. Optional Qiskit verification dependencies are configured via extras_require for users who want to verify exported circuits.

**Primary recommendation:** Use Cython's try-finally pattern with libc.stdlib malloc/free, leverage automatic char* → bytes conversion, declare C function in new openqasm.pxd file, and configure as auto-discovered Extension in setup.py's existing glob pattern.

## Standard Stack

The established libraries/tools for Cython Python/C bindings:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | >=3.0 | Python/C extension compilation | De facto standard for high-performance Python/C bindings, already used project-wide |
| setuptools | Latest | Package build configuration | Standard Python packaging tool with Extension class support |
| pytest | Latest | Testing framework | Already used in tests/python/, standard for Python testing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit | >=1.0 | Quantum circuit framework | Optional extra for OpenQASM verification only |
| qiskit-qasm3-import | Latest | OpenQASM 3 import to Qiskit | Optional extra for round-trip verification |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Cython | ctypes | ctypes: easier setup, runtime overhead. Cython: compile-time binding, faster, type-checked |
| Cython | CFFI | CFFI: cleaner API, less mature. Cython: mature, better NumPy integration (used elsewhere) |
| setuptools | poetry/hatch | Modern tools better for pure Python, setuptools better for compiled extensions |

**Installation:**
```bash
# Core (already installed)
pip install cython setuptools

# Optional verification dependencies
pip install quantum-assembly[verification]  # Adds qiskit>=1.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
├── openqasm.pyx        # New: Cython wrapper for OpenQASM export
├── openqasm.pxd        # New: C function declarations
├── _core.pyx           # Existing: Core circuit/qint logic
├── _core.pxd           # Existing: C declarations
└── __init__.py         # Modified: Re-export to_openqasm()
```

### Pattern 1: Memory-Safe C String Wrapper

**What:** Wrap C function returning malloc'd char* with automatic cleanup
**When to use:** Any C function that returns heap-allocated string buffer

**Example:**
```cython
# Source: https://cython.readthedocs.io/en/latest/src/tutorial/strings.html
from libc.stdlib cimport free, malloc

cdef extern from "circuit_output.h":
    char* circuit_to_qasm_string(circuit_t *circ)

def to_openqasm():
    """Export circuit as OpenQASM 3.0 string.

    Returns
    -------
    str
        Valid OpenQASM 3.0 representation

    Raises
    ------
    RuntimeError
        If circuit export fails or no circuit exists
    """
    cdef char* c_str = NULL
    try:
        # Get C string (malloc'd by C backend)
        c_str = circuit_to_qasm_string(<circuit_t*>_circuit)

        # Check for NULL (export failed)
        if c_str == NULL:
            raise RuntimeError("Failed to export circuit to OpenQASM")

        # Convert to Python string (automatic copy via decode)
        # Use slicing [:len] if length known for efficiency
        py_str = c_str.decode('utf-8')
        return py_str
    finally:
        # CRITICAL: Always free C buffer, even on exception
        if c_str != NULL:
            free(c_str)
```

**Key aspects:**
- `char* c_str = NULL` initialization ensures safe NULL check in finally
- `c_str.decode('utf-8')` automatically copies C string to Python string
- `finally` block guarantees cleanup even if decode() raises
- NULL check before free() is defensive (free(NULL) is safe but explicit is better)

### Pattern 2: Module-Level Function Accessing Global State

**What:** Python function that accesses Cython module global variables
**When to use:** API functions that operate on singleton circuit state

**Example:**
```cython
# In openqasm.pyx
from ._core cimport circuit_t
from ._core import _get_circuit, _get_circuit_initialized

cdef extern from "circuit_output.h":
    char* circuit_to_qasm_string(circuit_t *circ)

def to_openqasm():
    """Export current circuit to OpenQASM 3.0 string."""
    # Access global circuit via _core module's accessor
    if not _get_circuit_initialized():
        raise RuntimeError("No circuit initialized")

    cdef circuit_t* circ = <circuit_t*>_get_circuit()
    cdef char* c_str = NULL

    try:
        c_str = circuit_to_qasm_string(circ)
        if c_str == NULL:
            raise RuntimeError("Failed to export circuit to OpenQASM")
        return c_str.decode('utf-8')
    finally:
        if c_str != NULL:
            free(c_str)
```

**Key aspects:**
- Import global accessors from _core module
- Check circuit initialization before C call
- Cast pointer from Python int (from _get_circuit()) to C pointer

### Pattern 3: setup.py Extension Auto-Discovery

**What:** Automatically build all .pyx files as separate Extensions
**When to use:** Multi-module Cython projects

**Example:**
```python
# Source: Existing setup.py pattern
import glob
from pathlib import Path
from setuptools import Extension, setup
from Cython.Build import cythonize

# Shared C sources and includes (already defined)
c_sources = [...]
include_dirs = [...]

# Auto-discover all .pyx files
extensions = []
for pyx_file in glob.glob(os.path.join(SRC_DIR, "quantum_language", "**", "*.pyx"), recursive=True):
    module_name = Path(pyx_file).relative_to(SRC_DIR).with_suffix("").as_posix().replace("/", ".")

    extensions.append(
        Extension(
            name=module_name,
            sources=[pyx_file] + c_sources,
            language="c",
            extra_compile_args=["-O3", "-flto", "-pthread"],
            include_dirs=include_dirs,
        )
    )

setup(
    name="quantum-assembly",
    version="0.1.0",
    ext_modules=cythonize(extensions, language_level="3"),
    extras_require={
        "verification": ["qiskit>=1.0"],
    },
)
```

**Key aspects:**
- New openqasm.pyx automatically discovered by glob pattern
- Same C sources linked to all extensions (necessary for circuit access)
- extras_require adds optional dependencies without affecting base install

### Pattern 4: Package Re-Export for Clean API

**What:** Import Cython function in __init__.py and add to __all__
**When to use:** Making internal module functions available at package level

**Example:**
```python
# In __init__.py
from .openqasm import to_openqasm

__all__ = [
    # ... existing exports
    "to_openqasm",  # New: OpenQASM export
]
```

**Key aspects:**
- Users call `ql.to_openqasm()` not `ql.openqasm.to_openqasm()`
- Explicit __all__ declaration controls public API surface
- Import directly from module, not from .pyx (imports compiled .so/.pyd)

### Anti-Patterns to Avoid

- **Manual memory management without try-finally:** Memory leak if exception raised before free()
- **Using PyMem_Malloc for C-allocated strings:** Must match allocation type - use free() for malloc(), PyMem_Free() for PyMem_Malloc()
- **Forgetting to check NULL return:** Dereferencing NULL pointer crashes Python interpreter
- **c_str[:] without length:** Calls strlen() internally (inefficient), fails with embedded nulls
- **Keeping C pointer after free():** Dangling pointer causes use-after-free crashes

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| C string → Python string | Manual byte copying, strlen | Cython's automatic `.decode()` | Handles encoding, null termination, embedded nulls, exception safety |
| Memory cleanup on exception | Manual try-except with flags | try-finally block | Finally runs even on exception/return, cleaner pattern |
| Optional dependencies | Custom import checks | setuptools extras_require | Standard mechanism, pip integration, clear user communication |
| Extension compilation | Manual gcc commands | setuptools Extension + cythonize() | Handles platform differences, dependencies, parallel builds |
| Testing exceptions | Manual try-except in tests | pytest.raises() context manager | Better error messages, match parameter for message checking, excinfo object |

**Key insight:** Cython and setuptools handle the hard parts (ABI compatibility, reference counting, platform-specific compilation). Focus on correct try-finally structure and NULL checking - the rest is automated.

## Common Pitfalls

### Pitfall 1: Memory Leak from Missing Finally Block

**What goes wrong:** C buffer allocated but not freed if exception raised
```cython
# BAD: No finally block
def to_openqasm():
    cdef char* c_str = circuit_to_qasm_string(circ)
    if c_str == NULL:
        raise RuntimeError("Export failed")  # LEAK: c_str not freed
    result = c_str.decode('utf-8')
    free(c_str)  # Never reached if decode() raises
    return result
```

**Why it happens:** Exceptions skip remaining code in function, free() never called
**How to avoid:** Always use try-finally for malloc'd memory
```cython
# GOOD: Finally guarantees cleanup
def to_openqasm():
    cdef char* c_str = NULL
    try:
        c_str = circuit_to_qasm_string(circ)
        if c_str == NULL:
            raise RuntimeError("Export failed")
        return c_str.decode('utf-8')
    finally:
        if c_str != NULL:
            free(c_str)
```

**Warning signs:** Growing memory usage in repeated calls, valgrind reports leaks

### Pitfall 2: Using Wrong Free Function

**What goes wrong:** Segfault from freeing PyMem_Malloc memory with free()
```cython
# BAD: Mismatched allocation/deallocation
from cpython.mem cimport PyMem_Malloc, PyMem_Free
cdef char* buf = <char*>PyMem_Malloc(1024)
# ... use buffer ...
free(buf)  # WRONG: Should be PyMem_Free(buf)
```

**Why it happens:** Different allocators use different internal structures, cross-freeing corrupts heap
**How to avoid:** Match allocator and deallocator
- malloc() → free()
- PyMem_Malloc() → PyMem_Free()
- C backend uses malloc() → always use free() in Cython wrapper

**Warning signs:** Segfault in free(), heap corruption errors, non-deterministic crashes

### Pitfall 3: NULL Pointer Dereference

**What goes wrong:** Accessing c_str.decode() when c_str is NULL
```cython
# BAD: No NULL check
cdef char* c_str = circuit_to_qasm_string(circ)
return c_str.decode('utf-8')  # Crash if c_str is NULL
```

**Why it happens:** C backend returns NULL on error (malloc failure, invalid circuit)
**How to avoid:** Always check NULL before dereferencing
```cython
# GOOD: Explicit NULL check
cdef char* c_str = circuit_to_qasm_string(circ)
if c_str == NULL:
    raise RuntimeError("Export failed")
return c_str.decode('utf-8')
```

**Warning signs:** Segfault in decode(), AttributeError on NoneType (if Cython converts NULL to None)

### Pitfall 4: Importing .pyx Instead of Compiled Module

**What goes wrong:** Import error when trying to import from .pyx file
```python
# BAD: Can't import from .pyx
from .openqasm.pyx import to_openqasm  # ModuleNotFoundError
```

**Why it happens:** .pyx is source code, compiled to .so/.pyd with different name
**How to avoid:** Import from module name (without extension)
```python
# GOOD: Import from compiled module
from .openqasm import to_openqasm
```

**Warning signs:** ModuleNotFoundError, ImportError mentioning .pyx file

### Pitfall 5: Forgetting to Add to __all__

**What goes wrong:** Function works but not discoverable via help() or autocomplete
```python
# BAD: Imported but not exported
from .openqasm import to_openqasm
# __all__ doesn't include "to_openqasm"
```

**Why it happens:** __all__ controls what `from package import *` exports and what appears in API docs
**How to avoid:** Add all public functions to __all__
```python
# GOOD: Explicit public API
__all__ = [
    # ... existing
    "to_openqasm",
]
```

**Warning signs:** Function missing from dir(ql), not in autocomplete, not in Sphinx docs

## Code Examples

Verified patterns from official sources:

### C String Return with Memory Management

**Source:** https://cython.readthedocs.io/en/latest/src/tutorial/strings.html

```cython
from libc.stdlib cimport free, malloc
from libc.string cimport strcpy

# Declare external C function
cdef extern from "circuit_output.h":
    ctypedef struct circuit_t:
        pass
    char* circuit_to_qasm_string(circuit_t *circ)

def to_openqasm():
    """Export circuit to OpenQASM 3.0 string.

    Returns
    -------
    str
        Valid OpenQASM 3.0 circuit representation

    Raises
    ------
    RuntimeError
        If export fails or circuit not initialized
    """
    from ._core import _get_circuit, _get_circuit_initialized

    # Check circuit exists
    if not _get_circuit_initialized():
        raise RuntimeError("No circuit initialized")

    cdef circuit_t* circ = <circuit_t*>_get_circuit()
    cdef char* c_str = NULL

    try:
        # Call C function (returns malloc'd buffer)
        c_str = circuit_to_qasm_string(circ)

        # Check for error (NULL return)
        if c_str == NULL:
            raise RuntimeError("Failed to export circuit to OpenQASM")

        # Convert C string to Python string (automatic copy)
        py_str = c_str.decode('utf-8')
        return py_str
    finally:
        # Always free C buffer
        if c_str != NULL:
            free(c_str)
```

### Testing Exception Behavior

**Source:** https://docs.pytest.org/en/stable/how-to/assert.html

```python
import pytest
import quantum_language as ql

def test_openqasm_export_basic(clean_circuit):
    """Verify basic OpenQASM export."""
    a = ql.qint(5, width=4)
    qasm = ql.to_openqasm()

    # Check header
    assert "OPENQASM 3.0" in qasm
    assert 'include "stdgates.inc"' in qasm

    # Check qubit declaration
    assert "qubit[4] q;" in qasm

    # Check gates (5 = 0b0101 → X on bits 0 and 2)
    assert "x q[0];" in qasm
    assert "x q[2];" in qasm

def test_openqasm_export_no_circuit():
    """Verify error when no circuit initialized."""
    with pytest.raises(RuntimeError, match="No circuit initialized"):
        ql.to_openqasm()

def test_openqasm_export_returns_string(clean_circuit):
    """Verify return type is string."""
    a = ql.qint(1, width=1)
    result = ql.to_openqasm()
    assert isinstance(result, str)
    assert len(result) > 0
```

### Optional Dependencies Configuration

**Source:** https://setuptools.pypa.io/en/latest/userguide/dependency_management.html

```python
# setup.py
setup(
    name="quantum-assembly",
    version="0.1.0",
    # ... existing config ...
    extras_require={
        "verification": [
            "qiskit>=1.0",
        ],
    },
)
```

**Installation:**
```bash
# Base package (no Qiskit)
pip install quantum-assembly

# With verification dependencies
pip install quantum-assembly[verification]

# Development install with extras
pip install -e .[verification]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual char* handling | Automatic `.decode()` conversion | Cython 0.29+ | Simpler code, automatic encoding handling |
| setup.py with distutils | setup.py with setuptools | Python 3.12+ | distutils deprecated, setuptools standard |
| Single-file Cython projects | Multi-module .pyx files | Cython 3.0+ | Better organization, faster incremental builds |
| install_requires for all deps | extras_require for optional | setuptools 36+ | Lighter base install, user choice for extras |

**Deprecated/outdated:**
- `PyString_*` functions (Python 2): Use bytes/str and `.decode()` instead
- distutils Extension: Use setuptools.Extension (same API, better maintained)
- Manual .pyx to .c compilation: Use cythonize() (handles dependencies, parallel builds)

## Open Questions

### Q1: Should to_openqasm() take optional filename parameter?

**What we know:** Context decisions specify module-level function with no parameters
**What's unclear:** Whether file export should be separate function or optional parameter
**Recommendation:** Follow CONTEXT.md - no parameters, file export is out of scope (users can write string to file themselves)

### Q2: What Qiskit version to require in verification extras?

**What we know:** Qiskit 1.0 released 2024, major API changes from 0.x
**What's unclear:** Whether to support older versions or require 1.0+
**Recommendation:** Require `qiskit>=1.0` - modern API, active support, avoids compatibility issues with legacy code

### Q3: Should we validate QASM syntax before returning?

**What we know:** C backend generates syntactically correct QASM (tested in Phase 25)
**What's unclear:** Whether Python wrapper should validate or trust C backend
**Recommendation:** Trust C backend - validation adds overhead, Phase 25 tests ensure correctness, users can validate with Qiskit if needed

## Sources

### Primary (HIGH confidence)

- [Cython Memory Allocation Tutorial](https://cython.readthedocs.io/en/latest/src/tutorial/memory_allocation.html) - Memory management patterns, try-finally, PyMem vs malloc
- [Cython String Handling](https://cython.readthedocs.io/en/latest/src/tutorial/strings.html) - char* conversion, decode() usage, memory ownership
- [setuptools Dependency Management](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html) - extras_require syntax, version constraints
- [Cython Source Files and Compilation](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html) - Extension configuration, cythonize()
- [pytest Assertion Documentation](https://docs.pytest.org/en/stable/how-to/assert.html) - pytest.raises() usage, exception testing

### Secondary (MEDIUM confidence)

- [Qiskit QASM3 API](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qasm3) - dumps(), loads() functions for verification
- Existing codebase: setup.py, _core.pyx, __init__.py patterns

### Tertiary (LOW confidence)

- None - all findings verified with official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use (Cython, setuptools, pytest)
- Architecture: HIGH - Patterns verified in official Cython docs and existing codebase
- Pitfalls: HIGH - Documented in official sources with examples

**Research date:** 2026-01-30
**Valid until:** ~30 days (stable technology stack, no breaking changes expected)

---

**Ready for planning:** Yes
**Blocking issues:** None
**Phase 25 dependency:** Complete (circuit_to_qasm_string() implemented and tested)
