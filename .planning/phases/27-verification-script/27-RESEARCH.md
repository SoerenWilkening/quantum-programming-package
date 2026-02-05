# Phase 27: Verification Script - Research

**Researched:** 2026-01-30
**Domain:** Standalone Python verification script with Qiskit simulation
**Confidence:** HIGH

## Summary

Phase 27 requires implementing a standalone verification script (`scripts/verify_circuit.py`) that exports quantum circuits to OpenQASM 3.0, simulates them via Qiskit, and verifies deterministic outcomes match expected values. The script must test arithmetic, comparison, and bitwise operations with pytest-style output formatting.

The established approach uses:
1. **Qiskit 1.0+ with qasm3.loads()** for OpenQASM 3.0 parsing and AerSimulator for execution
2. **argparse** for CLI with flags (--fail-fast, --category, --show-qasm, --log)
3. **sys.stdout.isatty()** for automatic ANSI color detection
4. **Built-in test case classes** with deterministic 1-shot verification

**Primary recommendation:** Use Qiskit's qasm3.loads() with AerSimulator, argparse for CLI parsing, and minimal dependencies (no pytest runtime dependency). Structure as self-contained script with built-in test cases grouped by category.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| qiskit | >=1.0 | Quantum circuit simulation | Industry-standard quantum SDK, well-maintained, excellent OpenQASM 3 support |
| qiskit-aer | Latest (0.17+) | High-performance AerSimulator backend | Official Qiskit simulator, supports deterministic statevector simulation |
| argparse | stdlib | Command-line argument parsing | Python standard library, zero dependencies, well-tested |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sys | stdlib | TTY detection (isatty), exit codes | Always - auto-detect terminal for ANSI colors |
| os | stdlib | Environment variable checks | Optional - NO_COLOR, CLICOLOR support |
| dataclasses | stdlib (3.7+) | Test case structure | Recommended - clean test case definition |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| qiskit-aer | Qiskit BasicSimulator | AerSimulator is faster, better maintained, supports more backends |
| argparse | click/typer | argparse is stdlib (zero deps), sufficient for this use case |
| Built-in tests | External QASM files | Built-in ensures hermetic tests, no file I/O dependencies |
| Manual ANSI codes | colorama/rich | Manual codes work on modern terminals, avoid extra dependencies |

**Installation:**
```bash
# Already defined in setup.py extras_require
pip install -e .[verification]
# or explicitly:
pip install qiskit>=1.0 qiskit-aer
```

## Architecture Patterns

### Recommended Project Structure
```
scripts/
└── verify_circuit.py        # Self-contained standalone script

Internal structure (single file):
- Imports and constants (ANSI codes, exit codes)
- Test case dataclass definitions
- Test category classes (ArithmeticTests, ComparisonTests, BitwiseTests)
- Verification engine (run tests, compare results)
- Output formatter (pytest-style dots, colored output)
- CLI parser (argparse)
- Main entry point
```

### Pattern 1: Test Case Definition with Dataclasses
**What:** Use Python dataclasses to define deterministic test cases
**When to use:** All built-in test cases
**Example:**
```python
from dataclasses import dataclass
import quantum_language as ql

@dataclass
class TestCase:
    name: str
    category: str
    circuit_builder: callable  # Function that builds circuit and returns (expected_value, width)

class ArithmeticTests:
    @staticmethod
    def addition_basic():
        """3 + 5 = 8 (4-bit)"""
        c = ql.circuit()
        a = ql.qint(3, width=4)
        b = ql.qint(5, width=4)
        result = a + b
        return TestCase(
            name="addition_basic",
            category="arithmetic",
            circuit_builder=lambda: (8, 4)  # expected value, width
        )
```

### Pattern 2: Qiskit OpenQASM 3.0 Loading and Simulation
**What:** Load QASM string with qasm3.loads(), simulate with AerSimulator
**When to use:** Every test verification
**Example:**
```python
# Source: https://docs.quantum.ibm.com/guides/interoperate-qiskit-qasm3
import qiskit.qasm3
from qiskit_aer import AerSimulator

# Get QASM from ql
qasm_str = ql.to_openqasm()

# Load into Qiskit circuit
circuit = qiskit.qasm3.loads(qasm_str)

# Add measurement if not present
from qiskit import QuantumCircuit
if not circuit.cregs:
    circuit.measure_all()

# Simulate with 1 shot (deterministic)
simulator = AerSimulator(method='statevector')  # Exact simulation
job = simulator.run(circuit, shots=1)
result = job.result()
counts = result.get_counts()

# Extract single result (deterministic case)
bitstring = list(counts.keys())[0]
```

### Pattern 3: Pytest-Style Output Formatting
**What:** Print dots for pass, F for fail, detailed failures at end
**When to use:** Main test runner loop
**Example:**
```python
# Source: https://docs.pytest.org/en/stable/how-to/output.html
import sys

# Auto-detect ANSI color support
use_colors = sys.stdout.isatty() and os.getenv('NO_COLOR') is None

GREEN = '\033[32m' if use_colors else ''
RED = '\033[31m' if use_colors else ''
RESET = '\033[0m' if use_colors else ''

failures = []
for test in tests:
    try:
        actual = run_test(test)
        if actual == test.expected:
            sys.stdout.write(f'{GREEN}.{RESET}')
            sys.stdout.flush()
        else:
            sys.stdout.write(f'{RED}F{RESET}')
            sys.stdout.flush()
            failures.append((test, actual))
    except Exception as e:
        sys.stdout.write(f'{RED}E{RESET}')
        sys.stdout.flush()
        failures.append((test, e))

# Print detailed failures
if failures:
    print("\n\n" + "="*70)
    print("FAILURES")
    print("="*70)
    for test, actual in failures:
        print(f"\n{test.name}:")
        print(f"  Expected: {test.expected}")
        print(f"  Actual:   {actual}")
```

### Pattern 4: CLI Argument Parsing with Argparse
**What:** Standard argparse pattern for standalone scripts
**When to use:** Main entry point
**Example:**
```python
# Source: https://docs.python.org/3/library/argparse.html
import argparse

def main():
    parser = argparse.ArgumentParser(
        description='Verify quantum circuits via OpenQASM export and Qiskit simulation'
    )
    parser.add_argument('--fail-fast', action='store_true',
                       help='Stop on first failure')
    parser.add_argument('--category', choices=['arithmetic', 'comparison', 'bitwise'],
                       help='Run only tests in specified category')
    parser.add_argument('--show-qasm', '-v', action='store_true',
                       help='Show QASM for failing tests')
    parser.add_argument('--log', type=str, metavar='PATH',
                       help='Write detailed log to file')

    args = parser.parse_args()

    # Use args
    exit_code = run_verification(
        fail_fast=args.fail_fast,
        category=args.category,
        show_qasm=args.show_qasm,
        log_file=args.log
    )
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
```

### Pattern 5: Bit Order Mapping (Qiskit Little-Endian)
**What:** Extract measurement results accounting for Qiskit's little-endian convention
**When to use:** Converting measurement bitstring to integer value
**Example:**
```python
# Source: https://docs.quantum.ibm.com/guides/bit-ordering
# Qiskit uses little-endian: qubit 0 is rightmost bit in bitstring
# For bitstring "101": bit[0]=1 (LSB), bit[1]=0, bit[2]=1 (MSB)

def bitstring_to_int(bitstring: str, width: int) -> int:
    """Convert Qiskit little-endian bitstring to integer.

    Args:
        bitstring: Measurement result from Qiskit (e.g., "101")
        width: Expected bit width

    Returns:
        Integer value in standard representation
    """
    # Qiskit: rightmost bit is qubit 0 (LSB)
    # Standard int: rightmost bit is LSB
    # Direct conversion works correctly
    return int(bitstring, 2)

# Example: bitstring="101" (Qiskit) -> int=5 (binary 101)
# Qubit layout: q[2]=1, q[1]=0, q[0]=1 (little-endian)
# Integer value: 1*4 + 0*2 + 1*1 = 5 ✓
```

### Anti-Patterns to Avoid
- **Don't use pytest at runtime:** Script should be standalone, not require pytest to run (only mimic pytest output style)
- **Don't parse QASM manually:** Use qiskit.qasm3.loads(), not regex or custom parsers
- **Don't ignore terminal detection:** Always check sys.stdout.isatty() before ANSI codes (respect NO_COLOR)
- **Don't use multi-shot for deterministic tests:** Classical initialization → 1 shot → exact match is sufficient

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenQASM parsing | Custom regex/parser | qiskit.qasm3.loads() | Handles all QASM 3.0 syntax, gates, includes, edge cases |
| Quantum simulation | Matrix multiplication | AerSimulator | Optimized C++, handles large circuits, supports GPU |
| ANSI color detection | Hardcode color codes | sys.stdout.isatty() + env vars | Works with pipes, NO_COLOR, CLICOLOR standards |
| Bit extraction | String slicing | int(bitstring, 2) | Respects Qiskit's little-endian convention automatically |
| CLI argument parsing | sys.argv slicing | argparse | Handles --help, validation, type conversion, errors |

**Key insight:** Qiskit's ecosystem provides battle-tested tools for every part of this workflow. The verification script's job is to orchestrate them, not reimplement them.

## Common Pitfalls

### Pitfall 1: Ignoring Qiskit's Little-Endian Bit Order
**What goes wrong:** Measurement results interpreted incorrectly, all tests fail with off-by-bit errors
**Why it happens:** Natural assumption that bit[0] is leftmost (big-endian), but Qiskit uses little-endian
**How to avoid:** Use int(bitstring, 2) directly - Python's int() and Qiskit's ordering align naturally
**Warning signs:** Test results off by powers of 2, or reversed bit patterns

### Pitfall 2: Multi-Shot Simulation for Deterministic Tests
**What goes wrong:** Non-deterministic noise in results, intermittent failures, slow execution
**Why it happens:** Copy-paste from probabilistic examples, over-engineering verification
**How to avoid:** Use shots=1 with statevector method for classically-initialized circuits
**Warning signs:** Tests occasionally fail, execution time grows with shot count

### Pitfall 3: Missing measure_all() Call
**What goes wrong:** Qiskit simulation returns empty counts, all tests fail
**Why it happens:** Exported QASM may not include measurement instructions
**How to avoid:** Check circuit.cregs after loading QASM, call circuit.measure_all() if empty
**Warning signs:** get_counts() returns {} or crashes with "no classical registers"

### Pitfall 4: Hardcoding ANSI Color Codes
**What goes wrong:** Escape codes appear as garbage in CI logs, piped output, or non-TTY contexts
**Why it happens:** Testing only in interactive terminal, not considering automation use cases
**How to avoid:** Always gate color codes on sys.stdout.isatty() and check NO_COLOR env var
**Warning signs:** CI logs show "\033[32m" literally, complaints about unreadable output

### Pitfall 5: Not Handling Qiskit Parse Errors
**What goes wrong:** Script crashes with traceback instead of clear error message
**Why it happens:** Assuming QASM export always succeeds, not wrapping qasm3.loads()
**How to avoid:** Wrap in try/except, print QASM snippet on parse error if --show-qasm enabled
**Warning signs:** Cryptic Qiskit errors without context, no indication which test failed

## Code Examples

Verified patterns from official sources:

### Complete Test Case Pattern
```python
# Combines patterns from existing test files and Qiskit docs
import quantum_language as ql
from dataclasses import dataclass
from typing import Callable, Tuple

@dataclass
class TestCase:
    """Single deterministic verification test."""
    name: str
    category: str
    description: str
    expected: int
    width: int
    qasm_generator: Callable[[], str]  # Returns QASM string

def make_arithmetic_test(name: str, a: int, b: int, op: str, expected: int, width: int) -> TestCase:
    """Factory for arithmetic test cases."""
    def build_circuit():
        c = ql.circuit()
        qa = ql.qint(a, width=width)
        qb = ql.qint(b, width=width)

        if op == '+':
            result = qa + qb
        elif op == '-':
            result = qa - qb
        elif op == '*':
            result = qa * qb
        elif op == '//':
            result = qa // qb

        return ql.to_openqasm()

    return TestCase(
        name=f"{name}_{a}{op}{b}",
        category="arithmetic",
        description=f"{a} {op} {b} = {expected} ({width}-bit)",
        expected=expected,
        width=width,
        qasm_generator=build_circuit
    )

# Usage
test = make_arithmetic_test("add", 3, 5, '+', 8, 4)
```

### Complete Verification Engine
```python
# Source: Combines Qiskit docs + pytest output style
import qiskit.qasm3
from qiskit_aer import AerSimulator
import sys

def run_verification(tests: list, fail_fast: bool = False, show_qasm: bool = False) -> int:
    """Run all tests and return exit code."""
    simulator = AerSimulator(method='statevector')
    failures = []

    for test in tests:
        try:
            # Generate QASM
            qasm = test.qasm_generator()

            # Load and simulate
            circuit = qiskit.qasm3.loads(qasm)
            if not circuit.cregs:
                circuit.measure_all()

            job = simulator.run(circuit, shots=1)
            counts = job.result().get_counts()

            # Extract result
            bitstring = list(counts.keys())[0]
            actual = int(bitstring, 2)

            # Verify
            if actual == test.expected:
                sys.stdout.write('.')
                sys.stdout.flush()
            else:
                sys.stdout.write('F')
                sys.stdout.flush()
                failures.append({
                    'test': test,
                    'actual': actual,
                    'qasm': qasm if show_qasm else None
                })

                if fail_fast:
                    break

        except Exception as e:
            sys.stdout.write('E')
            sys.stdout.flush()
            failures.append({
                'test': test,
                'error': str(e),
                'qasm': qasm if show_qasm else None
            })

            if fail_fast:
                break

    # Print summary
    print(f"\n\n{'='*70}")
    print(f"Ran {len(tests)} tests: {len(tests)-len(failures)} passed, {len(failures)} failed")

    if failures:
        print(f"\n{'='*70}")
        print("FAILURES")
        print('='*70)
        for f in failures:
            print(f"\n{f['test'].name}: {f['test'].description}")
            print(f"  Expected: {f['test'].expected}")
            if 'actual' in f:
                print(f"  Actual:   {f['actual']}")
            else:
                print(f"  Error:    {f['error']}")
            if f.get('qasm'):
                print(f"\n  QASM:")
                for line in f['qasm'].split('\n')[:20]:  # First 20 lines
                    print(f"    {line}")

    return 1 if failures else 0
```

### ANSI Color Detection (Modern Pattern)
```python
# Source: https://blog.mathieu-leplatre.info/colored-output-in-console-with-python.html
import sys
import os

def should_use_colors() -> bool:
    """Detect if ANSI colors should be used.

    Checks (in order):
    1. NO_COLOR env var (disable if set)
    2. CLICOLOR_FORCE env var (force if set)
    3. sys.stdout.isatty() (auto-detect terminal)
    """
    # Respect NO_COLOR standard
    if os.getenv('NO_COLOR') is not None:
        return False

    # Force colors if requested
    if os.getenv('CLICOLOR_FORCE') is not None:
        return True

    # Auto-detect terminal
    return sys.stdout.isatty()

# Usage
if should_use_colors():
    GREEN = '\033[32m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    RESET = '\033[0m'
else:
    GREEN = RED = YELLOW = RESET = ''
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| qiskit.qasm2 | qiskit.qasm3 | Qiskit 1.0 (2024) | QASM 3.0 support, modern syntax |
| QasmSimulator | AerSimulator | Qiskit Aer 0.9+ (2021) | Unified backend, better performance |
| Manual bit reversal | Direct int(bitstring, 2) | Always valid | Natural alignment with Qiskit little-endian |
| shots=1024 for deterministic | shots=1 with statevector | Best practice | Faster, exact results for classical init |

**Deprecated/outdated:**
- **execute()**: Deprecated in Qiskit 1.0, use simulator.run() instead
- **Aer.get_backend()**: Old import style, use direct AerSimulator() constructor
- **qasm2.loads()**: Only for legacy QASM 2.0, use qasm3.loads() for QASM 3.0

## Open Questions

Things that couldn't be fully resolved:

1. **Qiskit version pinning**
   - What we know: Qiskit 1.0+ supports qasm3.loads(), setup.py specifies "qiskit>=1.0"
   - What's unclear: Whether Qiskit 1.x vs 2.x will break compatibility
   - Recommendation: Keep ">=1.0" for now, test with latest stable

2. **QASM 3.0 feature coverage**
   - What we know: Phase 25 exports basic gates, qubits, classical init
   - What's unclear: Which QASM 3.0 features the C backend uses (includes, custom gates, etc.)
   - Recommendation: Test with actual exported QASM, handle parse errors gracefully

3. **Measurement instruction handling**
   - What we know: Some QASM exports may not include measurements
   - What's unclear: Whether ql.to_openqasm() always includes measurement or never includes it
   - Recommendation: Always check circuit.cregs after load, call measure_all() if needed

## Sources

### Primary (HIGH confidence)
- [Qiskit OpenQASM 3 and Qiskit SDK Documentation](https://quantum.cloud.ibm.com/docs/en/guides/interoperate-qiskit-qasm3) - QASM 3.0 parsing with qasm3.loads()
- [Qiskit Bit-ordering Guide](https://docs.quantum.ibm.com/guides/bit-ordering) - Little-endian convention
- [Qiskit AerSimulator Documentation](https://qiskit.github.io/qiskit-aer/tutorials/1_aersimulator.html) - Simulation methods
- [Python argparse Documentation](https://docs.python.org/3/library/argparse.html) - CLI argument parsing
- [Pytest Output Management](https://docs.pytest.org/en/stable/how-to/output.html) - Dots and F output style

### Secondary (MEDIUM confidence)
- [Behind the Mystery of Wrong Qubit Ordering in Qiskit](https://lukaszpalt.com/behind-the-mystery-of-wrong-qubit-ordering-in-qiskit/) - Little-endian explanation
- [Python TTY Detection with isatty()](https://thelinuxcode.com/python-file-isatty-method/) - Terminal detection pattern
- [ANSI Color Codes Standard](http://bixense.com/clicolors/) - NO_COLOR, CLICOLOR environment variables
- [Testing argparse Applications](https://pytest-with-eric.com/pytest-argparse-typer/) - Argparse testing patterns

### Tertiary (LOW confidence)
- WebSearch results on quantum circuit verification (2026) - General verification concepts
- Existing test files in codebase - Pattern examples (not authoritative for Qiskit)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Qiskit 1.0+ is well-documented, argparse is stdlib standard
- Architecture: HIGH - Verified patterns from official docs and existing codebase
- Pitfalls: MEDIUM - Inferred from Qiskit docs and common patterns, not exhaustive testing

**Research date:** 2026-01-30
**Valid until:** ~90 days (Qiskit stable, Python stdlib stable, patterns unlikely to change)
