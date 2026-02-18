# Phase 25 Research: C Backend OpenQASM Export

**Research Date:** 2026-01-30
**Phase Goal:** Production-quality OpenQASM 3.0 string export from C backend with all gate types, multi-controlled gates, measurements, and error handling
**Researcher:** Claude Sonnet 4.5

## Executive Summary

Phase 25 implements production-quality OpenQASM 3.0 export from the C backend. The existing `circuit_to_opanqasm()` function has critical bugs: missing gate implementations (Y, Rx, Ry, Rz are no-ops), incorrect measurement syntax, missing file cleanup, typo in function name, and ignored `large_control` array for multi-controlled gates. This phase will fix all existing bugs AND add a new `circuit_to_qasm_string()` function that returns a malloc'd string buffer for Python API integration.

**Key Finding:** The infrastructure for gate export exists but is incomplete and buggy. The `gate_t` structure already supports all needed gate types via `Standardgate_t` enum and `large_control` pointer for n-controlled gates. The main work is implementing correct OpenQASM 3.0 syntax for each gate type, fixing control flow for large_control, and adding robust error handling.

## What Do I Need to Know to PLAN This Phase Well?

### 1. Current State Analysis

#### Existing Code: `circuit_to_opanqasm()` (circuit_output.c:274-326)

**Current Implementation:**
```c
void circuit_to_opanqasm(circuit_t *circ, char *path) {
    char p[512];
    sprintf(p, "%s/circuit.qasm", path);
    FILE *oq_file = fopen(p, "w");
    fprintf(oq_file,
            "// Version declaration\n"
            "OPENQASM 3.0;\n\n"
            "// Include standard Library\n"
            "include \"stdgates.inc\";\n\n"
            "// Initialize Registers\n"
            "qubit[%d] q;\n\n"
            "// The quantum Circuit\n",
            circ->used_qubits + 1);

    for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {
        for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index];
             ++gate_index) {
            gate_t g = circ->sequence[layer_index][gate_index];
            // Export control prefix as "c" repeated NumControls times
            for (int i = 0; i < g.NumControls; i++)
                fprintf(oq_file, "c");
            // Export gate type
            switch (g.Gate) {
            case P:
                fprintf(oq_file, "p(%.20f) ", g.GateValue);
                break;
            case X:
                fprintf(oq_file, "x ");
                break;
            case H:
                fprintf(oq_file, "h ");
                break;
            case Z:
                fprintf(oq_file, "z ");
                break;
            case M:
                fprintf(oq_file, "m ");  // WRONG: should be "measure"
                break;
            case Y:
                break;  // BUG: No output
            case R:
                break;  // BUG: No output
            case Rx:
                break;  // BUG: No output
            case Ry:
                break;  // BUG: No output
            case Rz:
                break;  // BUG: No output
            }
            // Export control qubits (only uses Control[0], Control[1])
            for (int i = 0; i < g.NumControls; i++)
                fprintf(oq_file, "q[%d],", g.Control[i]);  // BUG: ignores large_control
            fprintf(oq_file, "q[%d];\n", g.Target);
        }
    }
    // BUG: Missing fclose(oq_file)
}
```

**Identified Bugs:**
1. **Function name typo:** `circuit_to_opanqasm` should be `circuit_to_openqasm`
2. **Missing fclose:** File handle leak
3. **Y gate no-op:** Line 310 `case Y: break;`
4. **R gate no-op:** Line 312 `case R: break;`
5. **Rx gate no-op:** Line 314 `case Rx: break;`
6. **Ry gate no-op:** Line 316 `case Ry: break;`
7. **Rz gate no-op:** Line 318 `case Rz: break;`
8. **Invalid measurement syntax:** Line 308 exports `m q[i];` instead of `measure q[i] -> c[i];`
9. **No classical register:** Measurements require `bit[n] c;` declaration
10. **large_control ignored:** Lines 322-323 only read from `g.Control[i]`, never check `g.large_control`
11. **Wrong multi-control syntax:** Exports `cccc...x` which is invalid OpenQASM 3 (should use `ctrl(n) @ gate`)
12. **No error handling:** No NULL check, no malloc failure handling
13. **Excessive precision:** `%.20f` for phase angles (should be `%.17g` for doubles)
14. **No angle normalization:** Phase angles not normalized to [0, 2π)

#### Gate Type Definitions

From `c_backend/include/types.h:64`:
```c
typedef enum { X, Y, Z, R, H, Rx, Ry, Rz, P, M } Standardgate_t;

typedef struct {
    qubit_t Control[MAXCONTROLS];  // Array for up to 2 controls
    qubit_t *large_control;        // Pointer for >2 controls
    num_t NumControls;             // Number of control qubits
    Standardgate_t Gate;           // Gate type enum
    double GateValue;              // Angle parameter for rotations
    qubit_t Target;                // Target qubit
    num_t NumBasisGates;
} gate_t;
```

**Key Insight:** The structure already has everything needed:
- `large_control` pointer for n-controlled gates (already allocated by comparison ops)
- `GateValue` for rotation angles
- `NumControls` to distinguish cx/ccx/ctrl(n)
- All gate types in enum

From `c_backend/src/gate.c:18-24`:
```c
static inline qubit_t gate_get_control(gate_t *g, int i) {
    if (g->NumControls > MAXCONTROLS && g->large_control != NULL) {
        return g->large_control[i];
    }
    return g->Control[i];
}
```

**Key Insight:** Helper function already exists for control access. Export code should use this pattern.

#### OpenQASM 3.0 Syntax Requirements

From `.planning/research/PITFALLS-OPENQASM-EXPORT.md`:

**Standard Gates (lowercase):**
```
X  → x q[i];
Y  → y q[i];
Z  → z q[i];
H  → h q[i];
```

**Rotation Gates (with angle parameter):**
```
P(θ)  → p(θ) q[i];
Rx(θ) → rx(θ) q[i];
Ry(θ) → ry(θ) q[i];
Rz(θ) → rz(θ) q[i];
```
- Angles in radians, normalized to [0, 2π)
- Format: `%.17g` for IEEE double precision

**Controlled Gates:**
```
1 control:  cx q[ctrl], q[target];
2 controls: ccx q[ctrl1], q[ctrl2], q[target];
n controls (n>2): ctrl(n) @ x q[ctrl0], q[ctrl1], ..., q[ctrln-1], q[target];
```

**Measurements:**
```
// Classical register declaration
bit[n] c;

// Measurement syntax
measure q[i] -> c[i];
```
- Must declare classical bits BEFORE any measurements
- Cannot use `m` keyword

**Header Format:**
```
OPENQASM 3.0;
include "stdgates.inc";

qubit[n] q;
bit[m] c;  // Only if measurements exist
```

### 2. Memory Management Patterns in Codebase

#### C-Level String Buffer Allocation

From `c_backend/src/qubit_allocator.c:14-62`:
```c
qubit_allocator_t *allocator_create(num_t initial_capacity) {
    // OWNERSHIP: Caller owns returned qubit_allocator_t*, must call allocator_destroy()
    if (initial_capacity == 0 || initial_capacity > ALLOCATOR_MAX_QUBITS) {
        return NULL;  // Error: return NULL
    }

    qubit_allocator_t *alloc = malloc(sizeof(qubit_allocator_t));
    if (alloc == NULL) {
        return NULL;  // malloc failure
    }

    alloc->indices = malloc(initial_capacity * sizeof(qubit_t));
    if (alloc->indices == NULL) {
        free(alloc);  // Clean up partial allocation
        return NULL;
    }

    // ... more initialization
    return alloc;
}
```

**Pattern:**
- NULL check inputs
- malloc() with sizeof()
- Check malloc() return value
- Clean up partial allocations on failure
- Return NULL on error
- Document ownership in comments

#### Cython Memory Management

From `src/quantum_language/_core.pxd:1`:
```cython
from libc.stdlib cimport free, malloc, calloc
```

From `src/quantum_language/qint.pyx:395`:
```cython
allocator_free(alloc, self.allocated_start, self.bits)
```

From `src/quantum_language/_core.pyx:470`:
```cython
free_circuit(<circuit_t*>_circuit)
```

**Pattern:**
- Import C stdlib functions in .pxd
- Call C functions directly in .pyx
- No PyMem_* wrappers (using stdlib directly)
- Explicit cleanup in __dealloc__ or scope exit

#### String Return Pattern for Python API

**Required for Phase 26:** New function must return malloc'd string that Python can convert and free:

```c
char* circuit_to_qasm_string(circuit_t *circ) {
    // Check input
    if (circ == NULL) {
        return NULL;
    }

    // Estimate buffer size
    size_t estimated_size = 512 + (circ->used * 100);
    char *buffer = malloc(estimated_size);
    if (buffer == NULL) {
        return NULL;  // malloc failure
    }

    size_t offset = 0;
    // Build string with offset tracking
    offset += sprintf(buffer + offset, "OPENQASM 3.0;\n");
    // ... more content ...

    return buffer;  // OWNERSHIP: Caller must free()
}
```

**Cython Wrapper (Phase 26):**
```cython
def to_openqasm(self):
    """Export circuit as OpenQASM 3.0 string."""
    cdef char* c_str = NULL
    try:
        c_str = circuit_to_qasm_string(<circuit_t*>_circuit)
        if c_str == NULL:
            raise MemoryError("Failed to export circuit to OpenQASM")
        # Convert C string to Python string (copies data)
        py_str = c_str.decode('utf-8')
        return py_str
    finally:
        if c_str != NULL:
            free(c_str)  # CRITICAL: Always free, even on error
```

### 3. Implementation Strategy

#### Two-Function Approach

**Function 1: `circuit_to_qasm_string()` (NEW)**
- Returns malloc'd string buffer
- For Python API integration
- NULL circuit → return NULL
- malloc failure → return NULL
- Caller must free()

**Function 2: `circuit_to_openqasm()` (FIX EXISTING)**
- Writes to file path
- Fix all bugs listed above
- Add fclose()
- Return int (0 success, -1 error)
- Rename from `circuit_to_opanqasm`

**Code Reuse Strategy:**
Both functions should call shared helper:
```c
// Internal helper: build QASM string in pre-allocated buffer
static int _build_qasm_string(circuit_t *circ, char *buffer, size_t buffer_size, size_t *out_length);

// Public API: return malloc'd string
char* circuit_to_qasm_string(circuit_t *circ);

// Public API: write to file
int circuit_to_openqasm(circuit_t *circ, const char *path);
```

#### Gate Export Logic

**Control Qubit Helper:**
```c
static inline qubit_t _get_control_qubit(gate_t *g, int index) {
    if (g->NumControls > MAXCONTROLS && g->large_control != NULL) {
        return g->large_control[index];
    }
    return g->Control[index];
}
```
(Already exists in gate.c, may need to expose or duplicate)

**Gate Export Switch:**
```c
// Single-qubit gates (no controls)
if (g.NumControls == 0) {
    switch (g.Gate) {
    case X:
        offset += sprintf(buffer + offset, "x q[%d];\n", g.Target);
        break;
    case Y:
        offset += sprintf(buffer + offset, "y q[%d];\n", g.Target);
        break;
    case Z:
        offset += sprintf(buffer + offset, "z q[%d];\n", g.Target);
        break;
    case H:
        offset += sprintf(buffer + offset, "h q[%d];\n", g.Target);
        break;
    case P:
        offset += sprintf(buffer + offset, "p(%.17g) q[%d];\n",
                         normalize_angle(g.GateValue), g.Target);
        break;
    case Rx:
        offset += sprintf(buffer + offset, "rx(%.17g) q[%d];\n",
                         normalize_angle(g.GateValue), g.Target);
        break;
    case Ry:
        offset += sprintf(buffer + offset, "ry(%.17g) q[%d];\n",
                         normalize_angle(g.GateValue), g.Target);
        break;
    case Rz:
        offset += sprintf(buffer + offset, "rz(%.17g) q[%d];\n",
                         normalize_angle(g.GateValue), g.Target);
        break;
    case M:
        offset += sprintf(buffer + offset, "measure q[%d] -> c[%d];\n",
                         g.Target, measurement_index++);
        break;
    case R:
        offset += sprintf(buffer + offset, "reset q[%d];\n", g.Target);
        break;
    }
}
// Controlled gates
else if (g.NumControls == 1) {
    // Use cx, cy, cz, cp, etc.
    switch (g.Gate) {
    case X:
        offset += sprintf(buffer + offset, "cx q[%d], q[%d];\n",
                         _get_control_qubit(&g, 0), g.Target);
        break;
    // ... other controlled gates
    }
}
else if (g.NumControls == 2) {
    // Use ccx, ccy, ccz, ccp, etc.
    switch (g.Gate) {
    case X:
        offset += sprintf(buffer + offset, "ccx q[%d], q[%d], q[%d];\n",
                         _get_control_qubit(&g, 0),
                         _get_control_qubit(&g, 1),
                         g.Target);
        break;
    // ... other doubly-controlled gates
    }
}
else {
    // Use ctrl(n) @ gate syntax for n > 2
    offset += sprintf(buffer + offset, "ctrl(%d) @ ", g.NumControls);

    // Base gate name
    switch (g.Gate) {
    case X:
        offset += sprintf(buffer + offset, "x ");
        break;
    case Y:
        offset += sprintf(buffer + offset, "y ");
        break;
    // ... other gates
    }

    // Control qubits
    for (int i = 0; i < g.NumControls; i++) {
        offset += sprintf(buffer + offset, "q[%d], ", _get_control_qubit(&g, i));
    }

    // Target qubit
    offset += sprintf(buffer + offset, "q[%d];\n", g.Target);
}
```

**Angle Normalization:**
```c
static double normalize_angle(double theta) {
    // Normalize to [0, 2π)
    double normalized = fmod(theta, 2.0 * M_PI);
    if (normalized < 0.0) {
        normalized += 2.0 * M_PI;
    }
    return normalized;
}
```

#### Buffer Size Estimation

**Calculation:**
- Header: ~150 chars (fixed)
- Classical register: ~30 chars (if measurements exist)
- Per gate: ~80 chars average
  - Single-qubit: "x q[12345];\n" = ~15 chars
  - Controlled: "cx q[12345], q[67890];\n" = ~25 chars
  - Multi-controlled: "ctrl(10) @ x q[1], q[2], ..., q[10], q[11];\n" = ~60 chars
  - Rotation: "rx(1.23456789012345) q[12345];\n" = ~40 chars
- Safety margin: 2x

**Formula:**
```c
size_t estimated_size = 512 + (circ->used * 100);
```

**Overflow Protection:**
Use dynamic reallocation if approaching limit:
```c
if (offset > estimated_size - 200) {
    size_t new_size = estimated_size * 2;
    char *new_buffer = realloc(buffer, new_size);
    if (new_buffer == NULL) {
        free(buffer);
        return NULL;
    }
    buffer = new_buffer;
    estimated_size = new_size;
}
```

#### Measurement Handling

**Count measurements first:**
```c
int num_measurements = 0;
for (int layer = 0; layer < circ->used_layer; layer++) {
    for (int gate = 0; gate < circ->used_gates_per_layer[layer]; gate++) {
        if (circ->sequence[layer][gate].Gate == M) {
            num_measurements++;
        }
    }
}
```

**Add classical register if needed:**
```c
if (num_measurements > 0) {
    offset += sprintf(buffer + offset, "bit[%d] c;\n\n", num_measurements);
}
```

**Track measurement index:**
```c
int measurement_index = 0;
// ... in gate export loop ...
case M:
    offset += sprintf(buffer + offset, "measure q[%d] -> c[%d];\n",
                     g.Target, measurement_index++);
    break;
```

### 4. Testing Strategy

#### Unit Tests (C Level)

**Test File:** `tests/c/test_openqasm_export.c`

Test cases:
1. **NULL circuit** → returns NULL
2. **Empty circuit** → valid header only
3. **Single X gate** → "x q[0];"
4. **All single-qubit gates** → X, Y, Z, H on different qubits
5. **Rotation gates** → P, Rx, Ry, Rz with various angles
6. **Controlled gates** → cx, ccx, ctrl(5) @ x
7. **Measurement** → classical register + measure syntax
8. **Large circuit** → 10k gates (performance test)
9. **Angle normalization** → π, 2π, -π/4, 3π
10. **large_control array** → gate with 10 controls

**Verification Method:**
- Parse exported QASM with OpenQASM parser (if available)
- String matching for syntax check
- Round-trip test (future): export → Qiskit import → compare

#### Integration Tests (Python Level - Phase 26)

Test via Cython wrapper:
```python
import quantum_language as ql

def test_export_basic():
    ql.initialize()
    a = ql.qint(5, width=4)  # Classical init
    qasm = ql.to_openqasm()

    assert "OPENQASM 3.0" in qasm
    assert "qubit[4] q;" in qasm
    assert "x q[0];" in qasm  # Bit 0 set
    assert "x q[2];" in qasm  # Bit 2 set
    # 5 = 0b0101

def test_export_measurement():
    ql.initialize()
    a = ql.qint(3, width=3)
    # Add measurement gate somehow
    qasm = ql.to_openqasm()

    assert "bit[" in qasm
    assert "measure q[" in qasm
```

### 5. Known Edge Cases and Risks

#### Edge Case 1: Very Large Circuits

**Scenario:** Circuit with >100k gates
**Risk:** Buffer overflow, OOM, slow export
**Mitigation:**
- Dynamic reallocation
- Size limit documentation
- Performance test at 10k, 100k gates

#### Edge Case 2: Angle Precision

**Scenario:** Phase angle π/1024 in QFT
**Risk:** Precision loss, wrong results
**Mitigation:**
- Use `%.17g` format (17 significant digits)
- Normalize to [0, 2π) to avoid large numbers
- Document precision limits

#### Edge Case 3: Zero Controls

**Scenario:** Gate with NumControls=0 but large_control != NULL
**Risk:** Access invalid pointer
**Mitigation:**
```c
if (g.NumControls > 0) {
    qubit_t ctrl = _get_control_qubit(&g, i);
}
```
Always check NumControls first.

#### Edge Case 4: Measurement Without Classical Bits

**Scenario:** M gate but forgot to declare classical register
**Risk:** Invalid OpenQASM syntax
**Mitigation:** Count measurements first, declare register in header

#### Edge Case 5: Gate Enum Out of Range

**Scenario:** Corrupted gate_t with invalid Gate value
**Risk:** No case match, silent skip
**Mitigation:**
```c
default:
    fprintf(stderr, "Warning: Unknown gate type %d\n", g.Gate);
    offset += sprintf(buffer + offset, "// Unknown gate\n");
    break;
```

### 6. Dependencies and Integration Points

#### Phase Dependencies

**Depends On:**
- v1.3 completion (Phase 24) ✓
- Circuit structure stable ✓
- Gate types defined ✓
- large_control implementation ✓

**Enables:**
- Phase 26: Python API Bindings
- Phase 27: Verification Script

#### File Modifications

**C Backend:**
- `c_backend/src/circuit_output.c` — implement new function, fix existing
- `c_backend/include/circuit_output.h` — add function declarations

**No Changes Needed:**
- types.h (gate_t already complete)
- gate.h (helper functions exist)
- circuit.h (no new circuit features)

#### Header Changes

`c_backend/include/circuit_output.h`:
```c
// Export circuit to OpenQASM 3.0 string (heap-allocated)
// Returns malloc'd string, caller must free()
// Returns NULL on error (NULL circuit, malloc failure)
char* circuit_to_qasm_string(circuit_t *circ);

// Export circuit to OpenQASM 3.0 file
// Returns 0 on success, -1 on error
int circuit_to_openqasm(circuit_t *circ, const char *path);

// DEPRECATED: Old function name with typo
// Use circuit_to_openqasm() instead
void circuit_to_opanqasm(circuit_t *circ, char *path);
```

### 7. Open Questions

#### Q1: Should R gate export as reset or error?

**Context:** Enum has `R` but usage unclear
**Options:**
1. Export as `reset q[i];` (standard OpenQASM)
2. Export as comment `// Reset gate not supported`
3. Return error if R gate encountered

**Decision:** Export as `reset q[i];` (standard instruction)

#### Q2: Do we support mid-circuit measurement?

**Context:** OpenQASM 3 allows measurements anywhere
**Current:** circuit_t may not track measurement positions
**Decision:** Export measurements where they appear in circuit. If all at end, QASM will show them at end. No special handling needed.

#### Q3: Buffer size limit?

**Context:** Very large circuits (1M gates) could need huge buffers
**Options:**
1. No limit (rely on malloc)
2. Hard limit (e.g., 100MB)
3. Streaming API (write chunks to file)

**Decision:** No hard limit, document scaling. Future phase can add streaming if needed.

#### Q4: Controlled rotation gates?

**Context:** Can you have `ctrl(n) @ rx(θ)`?
**Answer:** Yes, OpenQASM 3 allows `ctrl @ ` modifier on any gate
**Implementation:** Same as controlled X, just change base gate name

#### Q5: Global phase?

**Context:** Quantum circuits have global phase freedom
**Answer:** Not represented in OpenQASM gate sequence (phase is relative)
**Implementation:** No special handling needed

### 8. Success Criteria Validation

**EXP-01:** ✓ New `circuit_to_qasm_string()` C function returning malloc'd OpenQASM 3.0 string buffer
- Implementation: malloc buffer, sprintf gates, return pointer
- Verification: Return value != NULL, free() in test

**EXP-02:** ✓ Export all single-qubit gates: X, Y, Z, H (lowercase OpenQASM syntax)
- Implementation: case X/Y/Z/H → sprintf "x/y/z/h q[%d];"
- Verification: Test exports each gate, check output string

**EXP-03:** ✓ Export all rotation gates: P(θ), Rx(θ), Ry(θ), Rz(θ) with `%.17g` angle precision
- Implementation: sprintf "p/rx/ry/rz(%.17g) q[%d];" with normalize_angle()
- Verification: Test with π, check precision in output

**EXP-04:** ✓ Multi-controlled gate export: `cx` (1 ctrl), `ccx` (2 ctrl), `ctrl(n) @ gate` (>2 ctrl)
- Implementation: if/else chain on NumControls
- Verification: Test gates with 0, 1, 2, 5 controls

**EXP-05:** ✓ `large_control` array support for gates with >2 control qubits
- Implementation: Use _get_control_qubit() helper
- Verification: Test gate with NumControls=10, check all indices in output

**EXP-06:** ✓ Measurement export with classical register: `bit[n] c;` + `c[i] = measure q[i];`
- Implementation: Count M gates, declare register, export "measure q[i] -> c[i];"
- Verification: Test circuit with measurements, check classical register in output

**EXP-07:** ✓ Error handling: NULL circuit check, malloc failure returns NULL
- Implementation: if (circ == NULL) return NULL; if (malloc == NULL) return NULL;
- Verification: Test NULL input, mock malloc failure (if possible)

**EXP-08:** ✓ Fix existing `circuit_to_opanqasm()`: add fclose, fix gate no-ops, fix measurement syntax
- Implementation: Same fixes as new function, add fclose() at end
- Verification: Test file export, check file closed (lsof), check all gates exported

## Implementation Plan Outline

### Step 1: Add Helper Functions
- `normalize_angle(double theta)` — angle normalization
- `_get_control_qubit(gate_t *g, int index)` — control access (may already exist)
- `_count_measurements(circuit_t *circ)` — count M gates

### Step 2: Implement `circuit_to_qasm_string()`
- NULL check input
- Estimate buffer size
- malloc() buffer
- Write header (OPENQASM 3.0, include, qubit register)
- Count and declare classical register if needed
- Loop over layers and gates
- Export each gate with correct syntax
- Return buffer (or NULL on error)

### Step 3: Fix `circuit_to_opanqasm()`
- Rename function (keep old name as deprecated alias)
- Add fclose() at end
- Fix all gate export bugs
- Add error handling
- Return int instead of void

### Step 4: Update Header File
- Add `circuit_to_qasm_string()` declaration
- Update `circuit_to_openqasm()` signature
- Add deprecation comment for old name

### Step 5: Write Tests
- C unit tests for each gate type
- C tests for control counts
- C tests for error conditions
- Performance test with large circuit

## Research Confidence: HIGH

**Confidence Level:** 95%

**Reasoning:**
- Gate structure and export pattern clearly defined
- OpenQASM 3.0 syntax well-documented
- Existing code provides clear template (just buggy)
- Memory management patterns established in codebase
- No novel algorithms needed (string formatting only)

**Uncertainties:**
- R gate semantics (low impact)
- Exact buffer size needs (can over-allocate)
- Controlled rotation gate syntax (assumed same as controlled X)

**Risk Mitigation:**
- All uncertainties have reasonable defaults
- String export is forgiving (easy to test and fix)
- Comprehensive testing will catch edge cases

## References

**Codebase Files:**
- `c_backend/src/circuit_output.c` — Current export implementation
- `c_backend/include/circuit_output.h` — Export API
- `c_backend/include/types.h` — Gate and circuit types
- `c_backend/src/gate.c` — Gate helper functions
- `.planning/research/PITFALLS-OPENQASM-EXPORT.md` — OpenQASM syntax and pitfalls
- `.planning/REQUIREMENTS.md` — Phase 25 requirements

**OpenQASM Documentation:**
- OpenQASM 3.0 Spec: https://openqasm.com/
- Standard Library Gates: https://openqasm.com/language/standard_library.html
- Control Flow: https://openqasm.com/language/gates.html

**Prior Research:**
- `.planning/research/PITFALLS-OPENQASM-EXPORT.md` — Comprehensive pitfalls analysis
- Phase 25 success criteria in ROADMAP.md

---
*Research completed: 2026-01-30*
*Ready for planning: Yes*
*Blocking issues: None*
