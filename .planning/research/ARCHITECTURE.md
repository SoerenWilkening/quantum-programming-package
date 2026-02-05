# Architecture Integration Patterns: OpenQASM Export & Verification

**Domain:** Quantum circuit export and verification
**Researched:** 2026-01-30
**Confidence:** HIGH

## Executive Summary

This research addresses how to integrate production-quality OpenQASM 3.0 string export and Qiskit-based verification into the existing three-layer stateless architecture (C backend → Cython bindings → Python frontend) without disrupting the established patterns.

### Key Findings

**Export approach:** Hybrid — C generates QASM to dynamically allocated buffer, Cython wraps with Python string, avoiding file I/O entirely.

**Verification location:** Standalone script at `scripts/verify_circuit.py` with optional Qiskit dependency, keeping verification separate from core library.

**Measurement integration:** Add measurement support to existing gate_t enum (already has M), expose via Python API for verification use cases.

**Integration pattern:** Minimal C changes, single new Cython binding, clean Python API addition (`ql.to_openqasm()`) maintaining architectural consistency.

## Recommended Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Python Layer (src/quantum_language/__init__.py)             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ql.to_openqasm() -> str                                 │ │
│ │ ql.circuit.measure(qint) -> None                        │ │
│ └─────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│ Cython Layer (src/quantum_language/_core.pyx)               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ def to_openqasm() -> str:                               │ │
│ │   cdef char* qasm_str = circuit_to_qasm_string(_circuit)│ │
│ │   py_str = qasm_str.decode('utf-8')                     │ │
│ │   free(qasm_str)  # C allocated, Python-managed free    │ │
│ │   return py_str                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│ C Backend (c_backend/src/circuit_output.c)                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ char* circuit_to_qasm_string(circuit_t *circ)           │ │
│ │   - Calculate buffer size (gate count estimate)         │ │
│ │   - malloc() buffer                                     │ │
│ │   - snprintf() QASM header                              │ │
│ │   - Iterate layers → gates → snprintf() gate strings    │ │
│ │   - Handle large_control for multi-controlled gates     │ │
│ │   - Return buffer (caller frees via Cython)             │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Verification (scripts/verify_circuit.py) — STANDALONE       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ import quantum_language as ql                           │ │
│ │ qasm_str = ql.to_openqasm()                             │ │
│ │ from qiskit.qasm3 import loads  # Optional dependency   │ │
│ │ circuit = loads(qasm_str)                               │ │
│ │ simulate and verify outcomes                            │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points with Existing Components

| Component | Current State | Required Changes | Integration Pattern |
|-----------|---------------|------------------|---------------------|
| **circuit_output.c** | Has `circuit_to_opanqasm(circ, path)` file-based export | Add `circuit_to_qasm_string(circ)` returning `char*` | New function alongside existing, reuse gate iteration logic |
| **circuit_output.h** | Declares file-based export | Add `char* circuit_to_qasm_string(circuit_t *circ);` | Single line addition |
| **_core.pxd** | No QASM export binding | Add `cdef extern from "circuit_output.h": char* circuit_to_qasm_string(circuit_t *circ)` | Standard Cython extern declaration |
| **_core.pyx** | Has circuit class with methods | Add `to_openqasm()` method to circuit class | Method returns decoded string, frees C buffer |
| **__init__.py** | Exports circuit class | Add `to_openqasm()` convenience function at module level | `def to_openqasm(): return circuit().to_openqasm()` |
| **setup.py** | No optional dependencies | Add `extras_require={"verification": ["qiskit>=1.0"]}` | Standard optional dependency pattern |

### New Components Needed

**1. C Function: `circuit_to_qasm_string()` in circuit_output.c**

Purpose: Generate OpenQASM 3.0 string in dynamically allocated buffer.

Signature:
```c
char* circuit_to_qasm_string(circuit_t *circ);
```

Implementation approach:
- Calculate buffer size estimate: `size = 200 + (circ->used * 80)` (header + ~80 chars per gate average)
- Use `malloc()` for buffer allocation
- Use `snprintf()` for safe string building (prevents overflow)
- Return buffer pointer (Cython layer handles free)

Key differences from existing `circuit_to_opanqasm()`:
- Returns `char*` instead of `void`
- Uses `malloc()` + `snprintf()` instead of `fprintf()`
- Handles all gate types (X, Y, Z, H, P, M, R, Rx, Ry, Rz)
- Correctly handles `large_control` for gates with `NumControls > 2`
- Includes error handling (NULL circuit, allocation failure)

**2. Cython Binding: `to_openqasm()` in _core.pyx**

Purpose: Wrap C string allocation with Python memory safety.

Implementation:
```python
def to_openqasm(self):
    """Export circuit to OpenQASM 3.0 string.

    Returns
    -------
    str
        OpenQASM 3.0 representation of circuit.
    """
    cdef char* qasm_cstr = circuit_to_qasm_string(<circuit_t*>_circuit)
    if qasm_cstr == NULL:
        raise RuntimeError("Failed to generate OpenQASM string")

    try:
        # Decode C string to Python string
        qasm_str = qasm_cstr.decode('utf-8')
    finally:
        # Free C-allocated buffer
        free(qasm_cstr)

    return qasm_str
```

Memory safety pattern:
- C allocates with `malloc()`
- Cython decodes to Python string (copies data)
- Cython frees C buffer with `free()` in finally block
- Python string is Python-managed (no manual free needed)

**3. Python API: `ql.to_openqasm()` in __init__.py**

Purpose: Provide module-level convenience function.

Implementation:
```python
def to_openqasm():
    """Export current circuit to OpenQASM 3.0 string.

    Returns
    -------
    str
        OpenQASM 3.0 representation of circuit.

    Examples
    --------
    >>> import quantum_language as ql
    >>> c = ql.circuit()
    >>> a = ql.qint(5, width=4)
    >>> qasm_str = ql.to_openqasm()
    >>> print(qasm_str)
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    ...
    """
    return circuit().to_openqasm()
```

**4. Verification Script: `scripts/verify_circuit.py`**

Purpose: Standalone verification tool with Qiskit integration.

Location: `scripts/` directory (not in package)

Structure:
```python
#!/usr/bin/env python3
"""Verify quantum_language circuits via Qiskit simulation.

Usage:
    python scripts/verify_circuit.py [--test-case CASE]

Optional dependency: qiskit>=1.0
Install with: pip install "quantum-assembly[verification]"
"""

def verify_circuit(qasm_string: str) -> bool:
    """Import QASM and simulate with Qiskit."""
    try:
        from qiskit.qasm3 import loads
        from qiskit_aer import AerSimulator
    except ImportError:
        print("ERROR: Qiskit not installed. Install with: pip install qiskit qiskit-aer")
        return False

    circuit = loads(qasm_string)
    simulator = AerSimulator()
    result = simulator.run(circuit, shots=1024).result()
    counts = result.get_counts()
    return counts

def test_classical_init():
    """Test case: qint(5) should measure as |101> with probability 1.0."""
    import quantum_language as ql

    c = ql.circuit()
    a = ql.qint(5, width=3)
    # TODO: Add measurement gates
    qasm = ql.to_openqasm()

    counts = verify_circuit(qasm)
    assert '101' in counts  # Binary 5 = 101
    assert counts['101'] > 900  # Should be ~1024 shots

if __name__ == '__main__':
    # Run built-in test cases
    test_classical_init()
    print("✓ All verification tests passed")
```

Why standalone script:
- Keeps Qiskit dependency optional (not required for core library)
- Provides example usage pattern for users
- Can be run independently during development
- Not imported by package (no import-time dependency check)

**5. Measurement Gate Support**

Current state: `gate_t` enum already includes `M` (measurement), but not exposed to Python.

Required additions:

In `_core.pyx`:
```python
def measure(self, qint_obj):
    """Add measurement gates for all qubits in quantum integer.

    Parameters
    ----------
    qint_obj : qint
        Quantum integer to measure.

    Notes
    -----
    Adds measurement gates to circuit. Outcomes available via
    OpenQASM export and external simulation.
    """
    # Iterate qubits in qint and add M gates
    # Use existing add_gate infrastructure
    pass
```

In `circuit_output.c` (`circuit_to_qasm_string`):
```c
case M:
    // OpenQASM 3.0 measurement syntax
    snprintf(gate_buf, sizeof(gate_buf), "measure q[%d];\n", g.Target);
    break;
```

Note: Measurement gates do not modify circuit structure, just add M gate type to sequence.

## Data Flow Changes

### Current OpenQASM Export Flow (File-Based)

```
User → calls circuit_to_opanqasm(circ, path)
     → C function opens file at path/circuit.qasm
     → fprintf() writes QASM to file
     → User reads file externally
```

### New OpenQASM Export Flow (String-Based)

```
User → calls ql.to_openqasm()
     → Python forwards to _core.circuit.to_openqasm()
     → Cython calls circuit_to_qasm_string(_circuit)
     → C allocates buffer with malloc()
     → C writes QASM to buffer with snprintf()
     → C returns char* to Cython
     → Cython decodes char* to Python str
     → Cython frees C buffer
     → Python string returned to user
```

### Verification Flow (External Script)

```
User builds circuit in quantum_language
     → calls ql.to_openqasm() → gets string
     → runs scripts/verify_circuit.py
     → script imports Qiskit (optional dep)
     → Qiskit loads QASM string
     → Simulate and verify outcomes
```

## Patterns to Follow

### Pattern 1: C String Return with Cython Cleanup

**Context:** C function needs to return variable-length string to Python.

**Problem:** C can't know Python's memory management; Python can't free C's malloc.

**Solution:** C allocates with malloc(), Cython decodes and frees.

**Example:**
```c
// C side (circuit_output.c)
char* circuit_to_qasm_string(circuit_t *circ) {
    size_t bufsize = 200 + (circ->used * 80);
    char *buf = malloc(bufsize);
    if (!buf) return NULL;

    // Build string with snprintf
    size_t offset = 0;
    offset += snprintf(buf + offset, bufsize - offset, "OPENQASM 3.0;\n");
    // ... more snprintf calls

    return buf;  // Caller must free
}
```

```python
# Cython side (_core.pyx)
def to_openqasm(self):
    cdef char* c_str = circuit_to_qasm_string(<circuit_t*>_circuit)
    if c_str == NULL:
        raise RuntimeError("Export failed")
    try:
        py_str = c_str.decode('utf-8')
    finally:
        free(c_str)  # Use libc.stdlib.free
    return py_str
```

**Why this works:**
- C allocates exactly the size needed
- Cython copies to Python string (immutable, GC-managed)
- Cython frees C memory immediately
- No Python object created in C (avoids mixed allocators)

**Reference:** [Python C Extension Memory Management](https://docs.python.org/3/c-api/memory.html), [Cython Unicode and Passing Strings](https://cython.readthedocs.io/en/latest/src/tutorial/strings.html)

### Pattern 2: Optional Dependencies via extras_require

**Context:** Verification needs Qiskit, but core library should not.

**Problem:** Don't want to force all users to install Qiskit (large dependency).

**Solution:** Use `extras_require` in setup.py for optional feature sets.

**Implementation:**

In `setup.py`:
```python
setup(
    name="quantum-assembly",
    version="0.1.0",
    # ... existing config
    python_requires=">=3.11",
    install_requires=[
        "numpy>=1.24",
    ],
    extras_require={
        "verification": [
            "qiskit>=1.0",
            "qiskit-aer>=0.13",
        ],
    },
)
```

In `pyproject.toml` (for modern tooling):
```toml
[project.optional-dependencies]
verification = [
    "qiskit>=1.0",
    "qiskit-aer>=0.13",
]
```

**Installation:**
```bash
# Core library only
pip install quantum-assembly

# With verification support
pip install "quantum-assembly[verification]"
```

**Why this works:**
- Core library remains lightweight
- Users who need verification can opt-in
- CI/CD can install [verification] extra for testing
- Follows Python packaging best practices

**Reference:** [Setuptools Dependency Management](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html)

### Pattern 3: Standalone Verification Script

**Context:** Verification needs Qiskit but shouldn't be part of package imports.

**Problem:** Don't want `import quantum_language` to fail if Qiskit not installed.

**Solution:** Verification script in `scripts/` (not in package), checks dependencies at runtime.

**Structure:**
```
Quantum_Assembly/
├── src/
│   └── quantum_language/       # Package code
│       ├── __init__.py
│       └── _core.pyx
├── scripts/                    # Not in package
│   └── verify_circuit.py       # Standalone tool
└── setup.py
```

**Import safety:**
```python
# scripts/verify_circuit.py
def verify_circuit(qasm_str: str):
    try:
        from qiskit.qasm3 import loads
        from qiskit_aer import AerSimulator
    except ImportError:
        raise RuntimeError(
            "Verification requires Qiskit. Install with:\n"
            "    pip install 'quantum-assembly[verification]'"
        )
    # ... proceed with verification
```

**Why this works:**
- `scripts/` not installed as package data
- Can be run as `python scripts/verify_circuit.py`
- Lazy import checks dependencies only when script runs
- Clear error message if dependencies missing

**Reference:** Python packaging conventions for scripts vs packages

### Pattern 4: Extend Existing C Functions vs New Functions

**Context:** Existing `circuit_to_opanqasm()` writes to file; need string version.

**Decision:** Create new function `circuit_to_qasm_string()`, keep old function.

**Rationale:**
- Old function may be used by existing code (main.c uses it)
- Different memory semantics (file I/O vs malloc)
- Can share gate iteration logic via helper function if needed

**Implementation:**
```c
// Shared helper (internal)
static void format_gate_qasm(gate_t *g, char *buf, size_t bufsize) {
    // Format single gate to QASM
    size_t offset = 0;
    for (int i = 0; i < g->NumControls; i++)
        offset += snprintf(buf + offset, bufsize - offset, "c");
    // ... gate type, qubits
}

// File-based (existing)
void circuit_to_opanqasm(circuit_t *circ, char *path) {
    FILE *f = fopen(...);
    // ... iterate gates
    char gate_buf[256];
    format_gate_qasm(&g, gate_buf, sizeof(gate_buf));
    fprintf(f, "%s", gate_buf);
    fclose(f);
}

// String-based (new)
char* circuit_to_qasm_string(circuit_t *circ) {
    char *buf = malloc(...);
    size_t offset = 0;
    // ... iterate gates
    char gate_buf[256];
    format_gate_qasm(&g, gate_buf, sizeof(gate_buf));
    offset += snprintf(buf + offset, bufsize - offset, "%s", gate_buf);
    return buf;
}
```

**Why this works:**
- No breaking changes to existing code
- Code reuse via shared helper
- Clear separation of concerns

## Anti-Patterns to Avoid

### Anti-Pattern 1: Python-Managed Buffer Passed to C

**What:** Pass pre-allocated Python buffer to C to fill.

**Why bad:**
- Python strings are immutable (can't modify after creation)
- Python bytearray would work but requires size estimation in Python
- Requires two function calls (size query, then fill)
- More complex than C allocation

**Instead:** Let C allocate exact size needed, Cython copies to Python string.

### Anti-Pattern 2: C Function Returns Python Object

**What:** Use Python C API in C backend to create Python string.

**Why bad:**
- Mixes Python C API into pure C backend
- Breaks clean layer separation
- Requires linking against Python headers in C backend
- Violates stateless C backend principle

**Instead:** C returns C types (char*), Cython handles Python conversion.

### Anti-Pattern 3: Required Qiskit Dependency

**What:** Add Qiskit to `install_requires` in setup.py.

**Why bad:**
- Qiskit is large (~500MB with dependencies)
- Most users don't need verification
- Slows down installation
- Violates "lightweight core" principle

**Instead:** Use `extras_require` for optional verification feature.

### Anti-Pattern 4: Inline Verification in Package

**What:** Add verification functions to quantum_language/__init__.py.

**Why bad:**
- Forces `import qiskit` at package import time (or complex lazy loading)
- Increases package complexity
- Mixes concerns (circuit building vs verification)

**Instead:** Standalone script in `scripts/`, imported only when needed.

### Anti-Pattern 5: File-Based Export as Primary API

**What:** Keep only `circuit.export_qasm(filename)` API.

**Why bad:**
- Requires file I/O for every export
- Awkward for testing (create temp files)
- Doesn't compose well with other tools
- Less Pythonic than returning string

**Instead:** String-based API (`ql.to_openqasm() -> str`), optionally add file convenience method later.

## Scalability Considerations

### Buffer Size Estimation

**At 100 gates:**
- Header: ~200 bytes
- Gates: ~50-80 bytes each (multi-controlled gates longer)
- Total: ~8KB
- Strategy: `malloc(200 + gates * 80)` with safety margin

**At 10K gates:**
- Total: ~800KB
- Strategy: Same formula works, check allocation success
- Consider: May want to switch to file-based export for very large circuits

**At 1M gates:**
- Total: ~80MB
- Strategy: File-based export recommended (`circuit_to_opanqasm()`)
- String API still works but inefficient for huge circuits

**Recommendation:** Provide both APIs, document file-based for large circuits.

### Measurement Overhead

**Impact:** Measurement gates are single-qubit, minimal overhead.

**At 64 qubits:** +64 gates (negligible compared to typical circuit size).

**Strategy:** Measurements added only when user explicitly calls `.measure()` or verification script adds them.

## Build Order Considerations

### Existing Dependencies

```
types.h (foundation)
  ↓
gate.h, circuit.h
  ↓
circuit_output.h (visualization, file export)
  ↓
_core.pxd (Cython declarations)
  ↓
_core.pyx (Cython implementation)
  ↓
__init__.py (Python API)
```

### New Dependencies Added

```
circuit_output.h
  + char* circuit_to_qasm_string(circuit_t*)  [new declaration]
  ↓
circuit_output.c
  + circuit_to_qasm_string() implementation    [new function]
  ↓
_core.pxd
  + extern char* circuit_to_qasm_string(...)   [new binding]
  ↓
_core.pyx
  + circuit.to_openqasm() method               [new method]
  ↓
__init__.py
  + to_openqasm() convenience function         [new export]
  ↓
scripts/verify_circuit.py                      [new script, standalone]
```

### Suggested Build Order for Implementation

1. **Phase 1: C String Export**
   - Modify `circuit_output.c`: Add `circuit_to_qasm_string()`
   - Modify `circuit_output.h`: Declare new function
   - Test: Write C test that calls function, prints result, frees buffer

2. **Phase 2: Cython Binding**
   - Modify `_core.pxd`: Add extern declaration
   - Modify `_core.pyx`: Add `circuit.to_openqasm()` method
   - Test: Python test calls method, checks QASM format

3. **Phase 3: Python API**
   - Modify `__init__.py`: Add module-level `to_openqasm()` function
   - Add to `__all__` exports
   - Test: Import-level function works

4. **Phase 4: Measurement Support**
   - Modify `_core.pyx`: Add `circuit.measure(qint)` method
   - Modify `circuit_output.c`: Ensure M gates export correctly
   - Test: Measurement gates appear in QASM

5. **Phase 5: Verification Script**
   - Create `scripts/verify_circuit.py`
   - Implement test cases
   - Modify `setup.py`: Add extras_require
   - Test: Install with [verification], run script

**Rationale:** Bottom-up build ensures each layer works before adding next.

## OpenQASM 3.0 Specification Compliance

### Required Elements

Based on [OpenQASM 3.0 specification](https://openqasm.com/versions/3.0/index.html):

**1. Version Declaration**
```qasm
OPENQASM 3.0;
```

**2. Standard Gate Library Include**
```qasm
include "stdgates.inc";
```

**3. Qubit Register Declaration**
```qasm
qubit[n] q;
```

**4. Gate Syntax**
- Single-qubit: `gate q[index];`
- Controlled: `cgate q[ctrl], q[target];`
- Multi-controlled: `ccgate q[ctrl1], q[ctrl2], q[target];`
- Parametric: `p(angle) q[index];`

**5. Measurement Syntax**
```qasm
measure q[index];
```

Note: OpenQASM 3.0 supports measurement without explicit bit declaration for simple cases.

### Current Implementation Gaps

**Missing in existing `circuit_to_opanqasm()`:**
- Y, R, Rx, Ry, Rz gates (marked as no-ops)
- Correct handling of `large_control` (uses Control[i] which only stores 2 controls)
- Error handling (NULL circuit check)

**Fix in new `circuit_to_qasm_string()`:**
```c
// Handle all gates
case Y:
    snprintf(gate_buf, sizeof(gate_buf), "y ");
    break;
case R:
    snprintf(gate_buf, sizeof(gate_buf), "r(%.20f) ", g.GateValue);
    break;
case Rx:
    snprintf(gate_buf, sizeof(gate_buf), "rx(%.20f) ", g.GateValue);
    break;
case Ry:
    snprintf(gate_buf, sizeof(gate_buf), "ry(%.20f) ", g.GateValue);
    break;
case Rz:
    snprintf(gate_buf, sizeof(gate_buf), "rz(%.20f) ", g.GateValue);
    break;

// Handle large_control correctly
qubit_t *controls = (g.NumControls > 2) ? g.large_control : g.Control;
for (int i = 0; i < g.NumControls; i++) {
    offset += snprintf(buf + offset, bufsize - offset, "q[%d],", controls[i]);
}
```

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| C string return pattern | HIGH | Standard C idiom, used in many C libraries |
| Cython memory safety | HIGH | Official Cython docs pattern for C string wrapping |
| Optional dependencies | HIGH | Standard Python packaging practice |
| OpenQASM 3.0 format | HIGH | Official spec available, clear syntax |
| Qiskit import | MEDIUM | Qiskit API changes between versions, but loads() is stable |
| Buffer sizing | MEDIUM | Estimate works for typical cases, may need adjustment for edge cases |

### Sources

**Official Documentation:**
- [OpenQASM 3.0 Specification](https://openqasm.com/versions/3.0/index.html) — Gate syntax, measurement format
- [Cython Unicode and Passing Strings](https://cython.readthedocs.io/en/latest/src/tutorial/strings.html) — String handling best practices
- [Python C-API Memory Management](https://docs.python.org/3/c-api/memory.html) — Memory allocation domains
- [Setuptools Dependency Management](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html) — Optional dependencies pattern

**Qiskit Integration:**
- [Qiskit OpenQASM 3 Import](https://quantum.cloud.ibm.com/docs/en/guides/interoperate-qiskit-qasm3) — loads() and load() functions
- [Qiskit qasm3 API](https://docs.quantum.ibm.com/api/qiskit/qasm3) — Official Qiskit import/export

## Gaps and Open Questions

### Resolved During Research

- **String allocation:** C malloc + Cython free pattern confirmed safe
- **Dependency management:** extras_require is standard approach
- **Measurement syntax:** OpenQASM 3.0 spec clarifies measurement format

### Remaining for Implementation

1. **Exact buffer size formula:** Current estimate `200 + (gates * 80)` is conservative; profile actual gate string lengths during implementation.

2. **Multi-controlled gate representation:** OpenQASM 3.0 has `ctrl @ gate` syntax for arbitrary controls, but current implementation uses `ccc...gate` syntax (compatible with OpenQASM 2). Decision: Use compatible syntax unless Qiskit import requires newer syntax.

3. **Measurement bit allocation:** OpenQASM 3.0 allows measurement without classical bit declaration (`measure q[0];`) or with explicit assignment (`measure q[0] -> c[0];`). Decision needed during implementation based on Qiskit import requirements.

4. **Error handling detail:** What errors to check in C (NULL circuit, allocation failure, invalid gate types)? Recommendation: Check NULL circuit and malloc failure, log warning for unknown gate types.

### Phase-Specific Research Flags

**Phase 1 (C String Export):** Unlikely to need deeper research — straightforward C implementation.

**Phase 2 (Cython Binding):** Unlikely to need research — standard pattern.

**Phase 3 (Python API):** Unlikely to need research — thin wrapper.

**Phase 4 (Measurement):** May need research on measurement semantics if qint measurement requires classical bit tracking.

**Phase 5 (Verification):** May need research on Qiskit simulator configuration (shots, measurement basis, outcome interpretation).

## Implementation Recommendations Summary

### Critical Success Factors

1. **Memory safety:** Use try/finally in Cython to ensure C buffer freed even on decode error
2. **Buffer overflow protection:** Use snprintf() throughout, check remaining space
3. **Compatibility:** Keep file-based export for backward compatibility
4. **Dependency isolation:** Qiskit only in extras_require, not core dependencies
5. **Clear errors:** RuntimeError with helpful message if export fails

### Integration Strategy

**Incremental approach:** Add string export first (usable immediately), then add verification script (users can opt-in).

**Testing strategy:**
- Unit tests for C function (verify buffer allocation, gate formatting)
- Integration tests for Python API (verify string returned, QASM valid)
- Optional verification tests (skip if Qiskit not installed)

**Documentation needs:**
- Docstring for `ql.to_openqasm()` with example
- README section on OpenQASM export
- Verification script usage in docstring
- Installation instructions for [verification] extra

### Ready for Roadmap

All integration points identified, patterns validated, build order clear. Proceeding to roadmap creation.
