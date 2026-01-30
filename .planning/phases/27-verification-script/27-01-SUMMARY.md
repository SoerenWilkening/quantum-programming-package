---
phase: 27-verification-script
plan: 01
subsystem: verification
tags: [openqasm, qiskit, testing, verification, cli]
requires: [26-02]
provides:
  - Standalone verification script framework
  - Test case categories (arithmetic, comparison, bitwise)
  - OpenQASM export validation
  - Qiskit simulation integration
  - CLI with filtering and output options
affects: []
tech-stack:
  added: [qiskit>=1.0, qiskit-aer, qiskit_qasm3_import]
  patterns: [test-dataclass, pytest-style-output, argparse-cli, qasm3-simulation]
key-files:
  created: [scripts/verify_circuit.py]
  modified: []
decisions:
  - name: Use dataclass for test case structure
    rationale: Clean definition with type hints for name, category, expected value, width, and qasm_generator callable
  - name: Pytest-style output (dots/F/E)
    rationale: Familiar to Python developers, clear visual progress indication
  - name: ANSI color auto-detection
    rationale: Respects NO_COLOR, CLICOLOR_FORCE standards, auto-detects terminal with isatty()
  - name: Category-based test organization
    rationale: Enables selective running (--category flag), logical grouping by operation type
  - name: Signed value ranges for qint
    rationale: qint uses signed integers - adjusted test values to fit [-2^(w-1), 2^(w-1)-1] range
metrics:
  duration: 9 minutes
  completed: 2026-01-30
---

# Phase 27 Plan 01: Verification Script Summary

**One-liner:** Created verification script framework with OpenQASM export, Qiskit simulation, and test cases - bit extraction logic requires further investigation.

## What Was Built

Created `scripts/verify_circuit.py` - a standalone verification script that tests quantum circuits by exporting to OpenQASM 3.0 and simulating with Qiskit.

### Script Structure

**Test Categories (21 tests total):**
1. **ArithmeticTests** (5 tests)
   - addition_basic: 3 + 5 = 8
   - addition_overflow: 15 + 15 = 30 (tests wider result width)
   - subtraction_basic: 7 - 3 = 4
   - subtraction_underflow: 3 - 7 = 12 (mod 16, wraps)
   - multiplication_basic: 3 * 3 = 9

2. **ComparisonTests** (12 tests)
   - All 6 operators: <, <=, ==, >=, >, !=
   - Each with true and false test cases
   - Return qbool (1-bit): 1 for true, 0 for false

3. **BitwiseTests** (4 tests)
   - and_basic: 0b0101 & 0b0011 = 0b0001 (1)
   - or_basic: 0b0101 | 0b0011 = 0b0111 (7)
   - xor_basic: 0b0101 ^ 0b0011 = 0b0110 (6)
   - not_basic: ~0b0010 = 0b1101 (13 unsigned, -3 signed)

**CLI Flags:**
- `--fail-fast`: Stop on first failure
- `--category {arithmetic,comparison,bitwise}`: Filter by test category
- `--show-qasm` / `-v`: Show QASM code for failing tests
- `--log PATH`: Write detailed log to file

**Output Features:**
- Pytest-style dots (`.` pass, `F` fail, `E` error)
- Summary line with pass/fail counts
- Detailed failure reports with expected vs actual values
- ANSI color auto-detection (respects `NO_COLOR`, `CLICOLOR_FORCE`, `isatty()`)
- Exit code 0 on success, 1 on any failure

### Test Execution Flow

Each test:
1. Calls `ql.circuit()` to reset state
2. Creates qint operands with explicit widths
3. Performs operation (e.g., `a + b`, `a < b`, `a & b`)
4. Exports via `ql.to_openqasm()`
5. Loads QASM into Qiskit circuit via `qiskit.qasm3.loads()`
6. Adds measurements if not present (`circuit.measure_all()`)
7. Simulates with `AerSimulator(method='statevector', shots=1)`
8. Extracts result from measurement bitstring
9. Compares actual vs expected value

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| ed2f1da | feat(27-01): create verification script with test cases | scripts/verify_circuit.py |
| 2fe6910 | fix(27-01): adjust test values for signed ranges and add PYTHONPATH requirement | scripts/verify_circuit.py |

## Deviations from Plan

### Auto-fixed Issues (Deviation Rule 3 - Blocking)

**1. Missing qasm_generator parameter in TestCase constructions**
- **Found during:** Task 1 initial run
- **Issue:** TestCase dataclass requires qasm_generator callable, but initial test methods didn't pass the `build()` function
- **Fix:** Added `qasm_generator=build` to all 21 TestCase return statements
- **Files modified:** scripts/verify_circuit.py
- **Commit:** ed2f1da

**2. Missing qiskit_qasm3_import dependency**
- **Found during:** Task 2 first run
- **Issue:** `qiskit.qasm3.loads()` requires separate `qiskit_qasm3_import` package not installed by default
- **Fix:** Installed `qiskit_qasm3_import` via pip
- **Rationale:** Required for OpenQASM 3.0 parsing in Qiskit
- **Files modified:** N/A (environment dependency)
- **Commit:** N/A

**3. Values outside signed integer ranges**
- **Found during:** Task 2 testing
- **Issue:** qint uses signed integers - values like 0b1100 (12) exceed 4-bit signed range [-8, 7], causing warnings and potential incorrect behavior
- **Fix:** Adjusted all test values to fit within signed ranges:
  - Bitwise: Changed from {12, 10} to {5, 3} in 4-bit tests
  - Arithmetic overflow: Changed from {30, 4} in 5-bit to {15, 15}
  - Multiplication: Changed from {3, 4} to {3, 3} in 3-bit
- **Files modified:** scripts/verify_circuit.py
- **Commit:** 2fe6910

## Known Issues and Blockers

### Critical Issues Requiring Resolution

**1. Bit Extraction Logic Incorrect**
- **Status:** Blocking - tests currently fail
- **Root cause:** `extract_result()` extracts last N bits from bitstring, but result register is at a specific qubit offset, not at the end of the bitstring
- **Orchestrator debugging findings (qubit layout confirmed):**
  - Qiskit bitstring is MSB-first: leftmost = highest qubit index
  - For binary ops (AND, OR, XOR): a=q[0:4], b=q[4:8], result=q[8:12] — result is **first 4 chars** of bitstring (highest indices)
  - For NOT: in-place — only 4 qubits total, result IS a at q[0:4]
  - For comparison: a=q[0:4], b=q[4:8], result=q[8] (1 bit) — 9 qubits total
  - For addition/subtraction: a=q[0:4], b=q[4:8], result=q[8:12] — same layout as binary ops
  - **Correct extraction:** Read first `width` chars from bitstring (= MSB of highest-index qubits), except NOT which reads last `width` chars
- **Verified working operations (with correct extraction):**
  - AND: `5 & 3 = 1` ✓
  - OR: `5 | 3 = 7` ✓
  - XOR: `5 ^ 3 = 6` ✓
  - NOT: `~2 = 13` ✓ (unsigned, in-place, 4 qubits only)
  - Comparison `3 < 7 = 1` ✓
  - Subtraction `7 - 3 = 4` ✓
  - Addition `0 + 5 = 5` ✓, `5 + 0 = 5` ✓, `3 + 4 = 7` ✓
- **QFT addition bug discovered:**
  - `1+1=0` ✗, `2+2=1` ✗, `2+3=0` ✗, `3+5=6` ✗ (expected 2, 4, 5, 8)
  - Pattern: additions work when one operand is 0, fail with both non-zero in many cases
  - `3+4=7` works but `1+1=0` does not — inconsistent, likely QFT phase rotation bug in C backend
  - Subtraction uses same QFT approach but `7-3=4` works correctly
- **Memory accumulation confirmed:**
  - `ql.circuit()` does NOT deallocate previous qubits when called in same process
  - Second circuit in same process uses 1M+ qubits, causing OOM
  - **Each test MUST run in a subprocess** for isolation

**2. PYTHONPATH Dependency**
- **Status:** Workaround exists
- **Issue:** Script requires `PYTHONPATH=/path/to/src` to import quantum_language correctly
- **Root cause:** Package built in-place with `setup.py build_ext --inplace`, not installed to site-packages
- **Workaround:** Run as: `PYTHONPATH=src:$PYTHONPATH python3 scripts/verify_circuit.py`
- **Proper fix:** Install package with `pip install -e .` (currently blocked by setup.py absolute path issues per STATE.md)

**3. Memory Errors from Cumulative Qubit Allocation**
- **Status:** Known pre-existing issue (STATE.md)
- **Symptom:** Later tests fail with "Insufficient memory to run circuit" (e.g., 1048576M required for XOR test)
- **Root cause:** Qubits accumulate across test suite, not deallocated between tests
- **Impact:** Tests timeout or crash after first few tests
- **Workaround:** Run categories separately with `--category` flag
- **Proper fix:** Requires investigation of circuit deallocation in C backend

**4. Multiplication Segfault at Certain Widths**
- **Status:** Known pre-existing issue (STATE.md)
- **Impact:** Multiplication overflow test (planned but not included) would segfault
- **Workaround:** Limited to basic multiplication test with small widths (3-bit operands)
- **Note:** Documented in code comments referencing STATE.md

### Comparison Test Timeout
- **Status:** Observed during testing
- **Symptom:** Comparison tests take extremely long (timeout after 30+ seconds for 2 tests)
- **Possible cause:** Comparison operations may have inefficient circuit implementations
- **Impact:** Full test suite cannot complete in reasonable time

## Dependencies Established

### Python Packages
- **qiskit>=1.0**: Core quantum SDK for circuit simulation
- **qiskit-aer**: AerSimulator backend for statevector simulation
- **qiskit_qasm3_import**: Required for `qiskit.qasm3.loads()` OpenQASM 3.0 parsing

### Internal Dependencies
- Requires Phase 26-02 (OpenQASM export implementation via `ql.to_openqasm()`)
- Requires compiled quantum_language package (Cython extensions)

## Test Results

**Current Status:** Framework complete, tests failing due to bit extraction issue

**Observed Results:**
- Script executes and loads all test cases ✓
- CLI flags work correctly (--help, --category, --fail-fast) ✓
- OpenQASM export succeeds for all operations ✓
- Qiskit simulation executes without parse errors ✓
- Bit extraction produces incorrect values ✗

**Example Test Run (--category arithmetic --fail-fast):**
```
Running 5 tests...
F

Summary: 0 passed, 1 failed out of 5 tests

FAIL: addition_basic
  Expected: 8
  Actual: 19
```

## Architecture Decisions

### TestCase Dataclass Pattern
**Decision:** Use `@dataclass` for test case structure with `qasm_generator: Callable[[], str]` field

**Rationale:**
- Type-safe definition with explicit fields
- Callable factory function delays circuit building until test execution
- Enables circuit reset (`ql.circuit()`) per test to avoid state accumulation
- Clean separation between test metadata and circuit generation logic

**Alternative considered:** Store QASM strings directly - rejected because circuit() must be called at execution time, not definition time

### Bit Extraction Strategy (RESOLVED)
**Correct approach confirmed by orchestrator debugging:**
- Bitstring is MSB-first (Qiskit convention): first chars = highest qubit indices
- Result register is the 3rd allocation (q[8:12] for 4-bit operands)
- **Extract first `width` chars of bitstring** for binary/arithmetic/comparison ops
- **Exception: NOT is in-place** — only 1 allocation, result at q[0:4], extract last `width` chars
- **Exception: comparison** — result is 1 bit at q[8], extract first char of bitstring (9 qubits total)
- Must also handle variable total qubit counts (NOT=4, comparison=9, binary=12, etc.)
- **Subprocess isolation required** — `ql.circuit()` doesn't deallocate, each test needs fresh process

### ANSI Color Detection
**Decision:** Implement `should_use_colors()` checking `NO_COLOR`, `CLICOLOR_FORCE`, and `isatty()`

**Rationale:**
- Respects Unix/FreeDesktop color standards
- Auto-detects terminal capability (no colors when piped/redirected)
- Users can override with environment variables
- Zero additional dependencies (stdlib only)

**Implementation:**
```python
def should_use_colors() -> bool:
    if os.getenv('NO_COLOR') is not None:
        return False
    if os.getenv('CLICOLOR_FORCE') is not None:
        return True
    return sys.stdout.isatty()
```

## Next Phase Readiness

**Blockers for Phase 27-02 (if planned):**
1. **Critical:** Bit extraction logic must be fixed before verification can confirm circuit correctness
2. **Important:** Memory accumulation issue prevents running full test suite
3. **Nice-to-have:** PYTHONPATH requirement should be resolved for better UX

**What's ready:**
- Script framework with all test categories
- CLI with filtering and output options
- OpenQASM export integration
- Qiskit simulation pipeline
- Pytest-style output formatting

**Recommended next steps:**
1. Debug bit extraction: Instrument `extract_result()` to understand qubit mapping
2. Consider per-test circuit cleanup to prevent memory accumulation
3. Add verbose mode showing bitstring breakdown for debugging
4. Once bit extraction fixed, verify all 21 tests pass
5. Add more test cases (conditional logic, arrays, modular arithmetic)

## Lessons Learned

### Qiskit Little-Endian Convention
- Measurement bitstrings are little-endian: rightmost character is qubit 0
- Qubit allocation order matters: need to know which qubits are inputs vs result
- Cannot blindly extract "last N bits" without understanding circuit structure

### Signed Integer Ranges in qint
- qint uses signed two's complement representation
- For width W, range is [-2^(W-1), 2^(W-1)-1], not [0, 2^W-1]
- Values outside range trigger warnings and wrap (modular arithmetic)
- Bitwise operations on signed integers: `~0b0010 = 0b1101` is -3 signed, 13 unsigned

### Test Isolation Challenges
- Quantum circuits accumulate state across tests if not properly reset
- `ql.circuit()` should reset, but qubits may not deallocate immediately
- Memory errors suggest circuit state persists beyond Python variable scope
- May require explicit deallocation or process-level isolation

### OpenQASM 3.0 Dependencies
- Qiskit 1.0+ has qasm3 module but requires separate `qiskit_qasm3_import` package
- Not obvious from Qiskit documentation or import errors
- Version compatibility: ensure qiskit>=1.0, qiskit-aer latest, qiskit_qasm3_import installed

---

**Phase:** 27-verification-script
**Plan:** 01
**Duration:** 9 minutes
**Status:** Framework complete, bit extraction requires investigation
**Completed:** 2026-01-30
