# Phase 27: Verification Script - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Standalone script that exports quantum circuits to OpenQASM 3.0 via `ql.to_openqasm()`, simulates them with Qiskit, and verifies outcomes match expected values. Covers arithmetic, comparison, and bitwise operations. No conditional logic tests, no external QASM input.

</domain>

<decisions>
## Implementation Decisions

### Test case design
- Cover four arithmetic operations: addition, subtraction, multiplication, division
- All six comparison operators: <, <=, ==, >=, >, !=
- Bitwise operations: AND, OR, XOR, NOT
- Edge cases (overflow, zero operands, identity) embedded within operation tests, not separate
- No conditional logic tests (if/else on comparisons) — stick to operations
- Bit widths: Claude's discretion per test case (balance simulation speed vs realism)

### Output & reporting
- Pytest-style output: dots for pass, F for fail, detailed failures printed at end
- Failing tests show expected vs actual values (per success criteria)
- QASM string shown on failure only with `--show-qasm` or `-v` flag
- ANSI colors auto-detected: colored when stdout is a terminal, plain when piped/redirected
- Optional log file via `--log <path>` flag — no log file by default

### Script invocation
- Location: `scripts/verify_circuit.py`
- Default: run all tests, report at end
- `--fail-fast` flag to stop on first failure
- `--category <name>` flag to run subset (arithmetic, comparison, bitwise)
- Built-in test cases only — no external QASM file input
- Exit non-zero on any failure (per success criteria)

### Verification method
- All tests deterministic: classical initialization via ql API (e.g., `qint(5, width=4)`) → 1 shot → exact match
- No probabilistic/multi-shot tests
- Use Qiskit's built-in little-endian convention for bit ordering — document the mapping
- No pre-simulation QASM syntax check — let Qiskit's simulation surface parse errors naturally

### Claude's Discretion
- Exact bit widths per test case
- Test case data values (specific numbers to add, compare, etc.)
- Internal script structure (classes, functions, test registration)
- Qiskit simulator choice (Aer vs built-in)
- Error message formatting details

</decisions>

<specifics>
## Specific Ideas

- Output style should feel like pytest — familiar to Python developers
- Script should be self-contained and runnable with `python scripts/verify_circuit.py`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-verification-script*
*Context gathered: 2026-01-30*
