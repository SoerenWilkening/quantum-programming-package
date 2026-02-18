# Phase 21: Package Restructuring - Research

**Researched:** 2026-01-29
**Domain:** Python/Cython package organization, module splitting, build configuration
**Confidence:** HIGH

## Summary

Package restructuring involves splitting a 3,233-line Cython file into maintainable modules (~200-300 lines each), creating proper Python package structure with `__init__.py` files, and configuring multi-file Cython builds. The current codebase uses a single `quantum_language.pyx` file that gets preprocessed into `quantum_language_preprocessed.pyx` (containing classes: `circuit`, `qint`, `qbool`, `qint_mod` and module-level functions).

The standard approach combines **src layout** for production packages, **multiple Extension objects** in setup.py for Cython modules, **.pxd files** for sharing C-level declarations between modules, and **__init__.py** to expose a clean public API. Key constraint: CONTEXT.md specifies the package name as `quantum_language` with hard-break migration (all imports update at once).

**Primary recommendation:** Use src layout (`src/quantum_language/`), create one .pyx file per major class (qint.pyx, qbool.pyx, qint_mod.pyx), extract shared utilities to `_core.pyx`, use .pxd files for cimport declarations, add "." to include_dirs in Extension objects, and update setup.py to build multiple extensions with glob patterns.

## Standard Stack

The established libraries/tools for Python package restructuring with Cython:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | >=3.0.11,<4.0 | Compile .pyx to C extensions | Industry standard for Python/C integration, active maintenance |
| setuptools | latest | Build system with Extension support | De facto standard, official packaging tool |
| pyproject.toml | - | Modern package metadata | PEP 518/621 standard configuration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest | Test framework | Already in use (found in tests/python/) |
| ruff | latest | Linting/formatting | Already configured in pyproject.toml |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| setuptools | meson-python/scikit-build | Better for complex C/C++ but overkill here, migration cost |
| setup.py | Pure pyproject.toml | Experimental for Cython (setuptools #4154), needs setup.py |
| src layout | flat layout | Flat simpler but src prevents import bugs during development |

**Installation:**
```bash
# Build dependencies already in pyproject.toml [build-system]
pip install -e .  # Editable install for development
```

## Architecture Patterns

### Recommended Project Structure
```
quantum_assembly/
├── src/
│   └── quantum_language/           # Main package
│       ├── __init__.py             # Public API: qint, qbool, qfixed
│       ├── __init__.pxd            # Package-level cimport declarations
│       ├── _core.pyx               # Shared utilities (circuit building, qubit management)
│       ├── _core.pxd               # C declarations for _core
│       ├── qint.pyx                # qint class and operations
│       ├── qint.pxd                # qint C-level interface
│       ├── qbool.pyx               # qbool class and operations
│       ├── qbool.pxd               # qbool C-level interface
│       ├── qint_mod.pyx            # qint_mod class
│       ├── qint_mod.pxd            # qint_mod C-level interface
│       └── state/                  # State management subpackage
│           ├── __init__.py         # State API exports
│           ├── qpu.pyx             # QPU state management
│           └── uncompute.pyx      # Uncomputation logic
├── python-backend/                 # Keep for now (legacy, will deprecate)
├── tests/
│   └── python/
│       ├── test_*.py              # Update imports to new structure
│       └── conftest.py            # Update fixture imports
└── pyproject.toml                 # Update package metadata
```

### Pattern 1: Multiple Cython Extensions in setup.py
**What:** Each .pyx file becomes a separate Extension object, compiled independently
**When to use:** When splitting a large Cython module into logical components

**Example:**
```python
# Source: https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html
from setuptools import setup, Extension
from Cython.Build import cythonize
import glob

# Shared C sources (Backend/*.c files)
c_sources = [
    os.path.join("..", "Backend", "src", "QPU.c"),
    # ... other C files
]

# Auto-discover .pyx files
extensions = []
for pyx_file in glob.glob("src/quantum_language/**/*.pyx", recursive=True):
    # Convert src/quantum_language/qint.pyx -> quantum_language.qint
    module_name = pyx_file.replace("src/", "").replace("/", ".").replace(".pyx", "")

    extensions.append(Extension(
        name=module_name,
        sources=[pyx_file] + c_sources,  # Each extension needs C sources
        language="c",
        include_dirs=[
            os.path.join("..", "Backend", "include"),
            os.path.join("..", "Execution", "include"),
            ".",  # CRITICAL: Allows cimport to find .pxd files
        ],
        extra_compile_args=["-O3", "-flto", "-pthread"],
    ))

setup(ext_modules=cythonize(extensions, language_level="3"))
```

### Pattern 2: Using .pxd Files for Cross-Module Declarations
**What:** Definition files (.pxd) declare C-level interfaces that other modules can cimport
**When to use:** When modules need to share cdef classes, cdef functions, or C types

**Example:**
```cython
# Source: https://cython.readthedocs.io/en/latest/src/tutorial/pxd_files.html

# _core.pxd - Declare shared circuit functionality
cdef class circuit:
    cdef circuit_t *_circuit
    cdef bint _circuit_initialized

cdef void initialize_circuit() nogil
cdef int allocate_qubit() nogil

# qint.pxd - Declare qint C interface
from quantum_language._core cimport circuit

cdef class qint(circuit):
    cdef unsigned int[:] qubit_array
    cdef int width

cdef qint create_qint(int value, int bits)

# qbool.pyx - Use cimport to access qint
from quantum_language.qint cimport qint, create_qint

cdef class qbool(qint):
    def __init__(self, value=None):
        # Can call C-level qint functions
        pass
```

### Pattern 3: Package __init__.py for Public API
**What:** Control package surface area using `__all__` and re-exports
**When to use:** Always - defines what users see when they `import quantum_language`

**Example:**
```python
# Source: https://realpython.com/python-all-attribute/

# src/quantum_language/__init__.py
"""Quantum programming language with natural syntax.

Import as: import quantum_language as ql
"""

__version__ = "0.1.0"

# Import types from Cython modules
from quantum_language.qint import qint
from quantum_language.qbool import qbool
from quantum_language.qint_mod import qint_mod

# Import module-level utilities
from quantum_language._core import (
    array,
    option,
    circuit_stats,
    get_current_layer,
    reverse_instruction_range,
)

# Explicit public API
__all__ = [
    # Types
    "qint",
    "qbool",
    "qint_mod",
    # Utilities
    "array",
    "option",
    "circuit_stats",
    "get_current_layer",
    "reverse_instruction_range",
    # Metadata
    "__version__",
]

# State subpackage accessible via quantum_language.state
# (imports handled in state/__init__.py)
```

### Pattern 4: Subpackage Organization
**What:** Group related functionality in subpackages with their own __init__.py
**When to use:** When functionality forms a cohesive unit (e.g., state management)

**Example:**
```python
# src/quantum_language/state/__init__.py
"""State management and uncomputation.

Import as: from quantum_language.state import ...
Or: import quantum_language as ql; ql.state.uncompute()
"""

from quantum_language.state.qpu import (
    QPUState,
    get_qpu_state,
    reset_qpu,
)

from quantum_language.state.uncompute import (
    uncompute_qbool,
    eager_mode,
    lazy_mode,
)

__all__ = [
    "QPUState",
    "get_qpu_state",
    "reset_qpu",
    "uncompute_qbool",
    "eager_mode",
    "lazy_mode",
]
```

### Anti-Patterns to Avoid
- **Large __init__.py files:** Don't put implementation in __init__.py, only imports/API definition
- **Wildcard imports in __init__.py:** Use explicit imports, not `from .module import *` (breaks static analysis)
- **Missing "." in include_dirs:** Without it, cimport cannot find .pxd files in same package
- **Forgetting language="c":** Cython defaults to C++, but this project uses C backend
- **Not listing all subpackages:** setup.py packages=["quantum_language", "quantum_language.state"] required

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Finding .pyx files | Manual paths list | `glob.glob("**/*.pyx", recursive=True)` | Auto-discovery scales, prevents forgotten files |
| Module name from path | String manipulation | `Path(pyx).relative_to("src").with_suffix("").as_posix().replace("/", ".")` | Handles edge cases (nested dirs, Windows paths) |
| Sharing C declarations | Copy-paste cdef | .pxd files with cimport | Single source of truth, compiler-checked |
| Public API definition | Comments/docs only | `__all__` list | Static type checkers use it, prevents wildcard pollution |
| Package discovery | Manual listing | `find_packages(where="src")` (setuptools) | Auto-finds nested packages |
| Import rewrites | Manual find/replace | sed/ast-based tool | Guarantees consistency, catches edge cases |

**Key insight:** Cython's .pxd system provides compile-time checked interfaces. Hand-rolling shared declarations in .pyx files leads to sync bugs and violates DRY. The extra file overhead pays dividends in maintainability.

## Common Pitfalls

### Pitfall 1: Missing include_dirs=["."]
**What goes wrong:** `cimport quantum_language.module` fails with "cannot find pxd file" even though it exists
**Why it happens:** Cython looks for .pxd files relative to include_dirs, not the package structure
**How to avoid:** Always add "." to include_dirs in every Extension object
**Warning signs:** Build succeeds but cimport statements fail during Cython compilation phase

### Pitfall 2: Circular cimport Dependencies
**What goes wrong:** `qbool.pyx` cimports from `qint.pxd`, `qint.pyx` cimports from `qbool.pxd` → import cycle
**Why it happens:** Type hierarchies (qbool inherits qint) create natural dependencies
**How to avoid:**
  - Extract shared declarations to `_core.pxd` that both import
  - Use forward declarations: `cdef class qbool` in qint.pxd without full definition
  - Prefer composition over inheritance when possible
**Warning signs:** Cython compiler errors about "incomplete type" or "circular dependency"

### Pitfall 3: Breaking Test Imports Silently
**What goes wrong:** Restructure passes build but `pytest` finds no tests or imports fail
**Why it happens:** Tests use `sys.path.insert()` to find old structure, new package not installed
**How to avoid:**
  - Remove manual sys.path manipulation in test files
  - Use `pip install -e .` for editable install during development
  - Run tests against installed package: `pytest tests/`
**Warning signs:** Tests passed before restructure, now 0 collected or ImportError

### Pitfall 4: Inconsistent Module Exports
**What goes wrong:** `from quantum_language import qint` works but `import quantum_language; quantum_language.qint` fails
**Why it happens:** Forgot to add qint to __init__.py or missing __all__ entry
**How to avoid:**
  - Always maintain __all__ in __init__.py
  - Test both import styles: `from X import Y` and `import X; X.Y`
  - Use static type checker (mypy/pyright) to catch export issues
**Warning signs:** Works in some contexts but not others, IDE autocomplete missing items

### Pitfall 5: Shared C Sources Duplication
**What goes wrong:** Each .pyx file needs Backend/*.c sources, easy to forget one
**Why it happens:** Copy-paste Extension definitions, miss updating sources list
**How to avoid:**
  - Define c_sources as shared variable: `c_sources = [...]`
  - Reference in each Extension: `sources=[pyx_file] + c_sources`
  - DRY principle - one source of truth
**Warning signs:** Linker errors about undefined symbols at build time

### Pitfall 6: File Size Targets Too Aggressive
**What goes wrong:** Split creates 50-line files with high import overhead
**Why it happens:** Misunderstanding "~300 lines max" as "must be under 200"
**How to avoid:**
  - Target 200-300 lines for most modules (not 50-100)
  - Prefer cohesive modules over arbitrary size limits
  - Community consensus: 150-500 lines is the sweet spot
**Warning signs:** Many tiny files, excessive cross-file imports, hard to navigate

### Pitfall 7: Tests in Package Root
**What goes wrong:** tests/ directory gets installed to site-packages/tests/, conflicts with other packages
**Why it happens:** Including tests in package_data or wrong find_packages() configuration
**How to avoid:**
  - Keep tests/ outside src/ directory
  - Use `packages=find_packages(where="src")` to exclude tests
  - Never include tests in package_data
**Warning signs:** pip install adds tests to site-packages, conflicts with other test dirs

## Code Examples

Verified patterns from official sources:

### Split Large Module: Class Extraction
```cython
# Before: quantum_language_preprocessed.pyx (3233 lines)
cdef class circuit:
    # ... 300 lines ...

cdef class qint(circuit):
    # ... 2000 lines ...

cdef class qbool(qint):
    # ... 500 lines ...

# After: Split by class responsibility

# --- src/quantum_language/_core.pyx (250 lines) ---
cdef class circuit:
    """Base circuit manipulation class."""
    cdef circuit_t *_circuit
    cdef bint _circuit_initialized

    def __cinit__(self):
        # Circuit initialization
        pass

# --- src/quantum_language/qint.pyx (280 lines) ---
from quantum_language._core cimport circuit

cdef class qint(circuit):
    """Quantum integer type."""
    cdef unsigned int[:] qubit_array
    cdef int width

    def __init__(self, value=None, bits=8):
        # qint initialization
        pass

    def __add__(self, other):
        # Addition logic
        pass

# --- src/quantum_language/qbool.pyx (220 lines) ---
from quantum_language.qint cimport qint

cdef class qbool(qint):
    """Quantum boolean (1-bit qint)."""

    def __init__(self, value=None):
        super().__init__(value=value, bits=1)
```

### Module-Level Functions: Utility Extraction
```python
# Before: All in quantum_language_preprocessed.pyx
def array(dim, dtype=qint):
    # 40 lines

def option(key, value=None):
    # 30 lines

def circuit_stats():
    # 40 lines

# After: Extract to appropriate modules

# --- src/quantum_language/_core.pyx ---
def array(dim: int | tuple[int, int] | list[int], dtype = qint) -> list[qint | qbool]:
    """Create array of quantum integers or booleans."""
    # Implementation
    pass

def circuit_stats():
    """Return circuit statistics."""
    # Implementation
    pass

# --- src/quantum_language/config.pyx ---
# Global configuration state
_qubit_saving_mode = False

def option(key: str, value=None):
    """Get or set quantum language options."""
    global _qubit_saving_mode

    if key == 'qubit_saving':
        if value is None:
            return _qubit_saving_mode
        _qubit_saving_mode = value
    else:
        raise ValueError(f"Unknown option: {key}")

# --- src/quantum_language/__init__.py ---
from quantum_language._core import array, circuit_stats
from quantum_language.config import option

__all__ = ["array", "circuit_stats", "option"]
```

### Setup.py: Multi-Extension Configuration
```python
# Source: https://github.com/cython/cython/wiki/PackageHierarchy
import os
import glob
from pathlib import Path
from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize

# Shared C sources from Backend
c_sources = [
    os.path.join("..", "Backend", "src", "QPU.c"),
    os.path.join("..", "Backend", "src", "optimizer.c"),
    os.path.join("..", "Backend", "src", "qubit_allocator.c"),
    os.path.join("..", "Backend", "src", "circuit_allocations.c"),
    os.path.join("..", "Backend", "src", "circuit_output.c"),
    os.path.join("..", "Backend", "src", "circuit_stats.c"),
    os.path.join("..", "Backend", "src", "circuit_optimizer.c"),
    os.path.join("..", "Backend", "src", "gate.c"),
    os.path.join("..", "Backend", "src", "Integer.c"),
    os.path.join("..", "Backend", "src", "IntegerAddition.c"),
    os.path.join("..", "Backend", "src", "IntegerComparison.c"),
    os.path.join("..", "Backend", "src", "IntegerMultiplication.c"),
    os.path.join("..", "Backend", "src", "LogicOperations.c"),
    os.path.join("..", "Execution", "src", "execution.c"),
]

compiler_args = ["-O3", "-flto", "-pthread"]

include_dirs = [
    os.path.join("..", "Backend", "include"),
    os.path.join("..", "Execution", "include"),
    ".",  # CRITICAL for cimport to find .pxd files
]

# Auto-discover all .pyx files in package
extensions = []
for pyx_file in glob.glob("src/quantum_language/**/*.pyx", recursive=True):
    # Convert path to module name
    # src/quantum_language/qint.pyx -> quantum_language.qint
    module_name = (
        Path(pyx_file)
        .relative_to("src")
        .with_suffix("")
        .as_posix()
        .replace("/", ".")
    )

    extensions.append(Extension(
        name=module_name,
        sources=[pyx_file] + c_sources,
        language="c",
        extra_compile_args=compiler_args,
        include_dirs=include_dirs,
    ))

setup(
    name="quantum-assembly",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=cythonize(
        extensions,
        language_level="3",
        compiler_directives={
            'embedsignature': True,  # Helps with docstrings
        },
    ),
    # Install .pxd files for potential cimport by other projects
    package_data={
        'quantum_language': ['*.pxd'],
        'quantum_language.state': ['*.pxd'],
    },
)
```

### Import Migration: Test Updates
```python
# Before: tests/python/test_circuit_generation.py
import os
import sys

# Manual path manipulation
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "python-backend"))

import quantum_language as ql  # noqa: E402

# After: Clean imports (assumes pip install -e .)
import quantum_language as ql

# No path manipulation needed - package is installed
# Tests run against installed package (editable mode during dev)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat layout | src/ layout | 2018+ (PEP 518) | Prevents import bugs, cleaner editable installs |
| setup.py only | pyproject.toml + setup.py | 2021+ (PEP 621) | Declarative metadata, tool standardization |
| Manual Extension lists | Glob patterns for .pyx | 2020+ | Auto-discovery, scales with project growth |
| Empty __init__.py | __all__ enforcement | 2022+ best practice | Better static analysis, explicit API |
| Cython <3.0 | Cython >=3.0.11 | 2023 | Breaking changes (.pxi handling, performance) |

**Deprecated/outdated:**
- **setup.cfg for metadata:** Replaced by pyproject.toml [project] section (PEP 621, 2021)
- **distutils.core:** Use setuptools.setup (distutils deprecated in Python 3.10, removed 3.12)
- **Single-file Cython packages:** Best practice now favors modular .pyx files (2020+)
- **Pyrex dotted naming:** Use proper package hierarchies (cython/cython/wiki/PackageHierarchy)

## Open Questions

Things that couldn't be fully resolved:

1. **Cython 3.0 Performance Impact of Multiple Files**
   - What we know: Large files have slow C compilation, Cython 3.0 is 3x slower than 0.29
   - What's unclear: Does splitting into 10 small files help or hurt overall build time?
   - Recommendation: Measure with `time pip install -e .` before/after split (compilation time), runtime performance should be identical

2. **Optimal Granularity for qint Operations**
   - What we know: qint class has ~2000 lines including arithmetic, comparison, bitwise
   - What's unclear: Should operations split into qint_arithmetic.pyx, qint_comparison.pyx or stay in qint.pyx?
   - Recommendation: Keep operations in qint.pyx (cohesion > size for 200-300 line modules), only split if qint.pyx exceeds 400 lines after base split

3. **State Subpackage Module Organization**
   - What we know: CONTEXT.md specifies `quantum_language.state` subpackage for QPU state and uncomputation
   - What's unclear: Current code has `_qubit_saving_mode` flag and scope stack - exact split unclear
   - Recommendation: qpu.pyx (QPU state/circuit management), uncompute.pyx (uncomputation logic, qubit_saving_mode), scope.pyx (scope stack, context managers)

## Sources

### Primary (HIGH confidence)
- [Cython Source Files and Compilation](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html) - Official docs on multi-file Cython structure
- [Cython pxd Files Tutorial](https://cython.readthedocs.io/en/latest/src/tutorial/pxd_files.html) - Using .pxd for sharing declarations
- [Cython Sharing Declarations](https://cython.readthedocs.io/en/latest/src/userguide/sharing_declarations.html) - cimport between modules
- [Cython PackageHierarchy Wiki](https://github.com/cython/cython/wiki/PackageHierarchy) - Package structure best practices
- [Python Packaging: src vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) - Official PyPA guidance on src layout

### Secondary (MEDIUM confidence)
- [Structuring Your Project - Hitchhiker's Guide](https://docs.python-guide.org/writing/structure/) - General Python package structure
- [Python __all__ Attribute - Real Python](https://realpython.com/python-all-attribute/) - __all__ best practices
- [setuptools Extension Modules](https://setuptools.pypa.io/en/latest/userguide/ext_modules.html) - Building C extensions
- [pytest Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) - Testing with src layout
- [Python Packages Guide - Package Structure](https://py-pkgs.org/04-package-structure.html) - Modern package layout

### Tertiary (LOW confidence - informational)
- [ArjanCodes - Organizing Python Code](https://arjancodes.com/blog/organizing-python-code-with-packages-and-modules/) - Code organization patterns
- [Fixing Circular Imports - Python Morsels](https://www.pythonmorsels.com/fixing-circular-imports/) - Circular import solutions
- [DataCamp - Python Circular Import](https://www.datacamp.com/tutorial/python-circular-import) - Common import issues
- [Right-Sizing Python Files (Medium)](https://medium.com/@eamonn.faherty_58176/right-sizing-your-python-files-the-150-500-line-sweet-spot-for-ai-code-editors-340d550dcea4) - File size best practices
- [Common Python Packaging Mistakes (jwodder)](https://jwodder.github.io/kbits/posts/pypkg-mistakes/) - Packaging pitfalls

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Cython + setuptools + pyproject.toml is industry standard, verified in official docs
- Architecture: HIGH - src layout and multi-Extension patterns from official Cython docs and PyPA guides
- Pitfalls: HIGH - Derived from official docs (include_dirs), known issues (Cython #4425), and community patterns

**Research date:** 2026-01-29
**Valid until:** 2026-03-29 (60 days - Python packaging stable, Cython releases infrequent)
