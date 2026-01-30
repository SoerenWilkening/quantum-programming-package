#!/usr/bin/env python3
"""
Verification script for quantum circuit OpenQASM export.

This script tests quantum circuits by:
1. Building circuits using quantum_language (ql) API
2. Exporting to OpenQASM 3.0 via ql.to_openqasm()
3. Loading into Qiskit and simulating
4. Verifying outcomes match expected values

Usage:
    python scripts/verify_circuit.py                    # Run all tests
    python scripts/verify_circuit.py --category arithmetic  # Run specific category
    python scripts/verify_circuit.py --fail-fast         # Stop on first failure
    python scripts/verify_circuit.py -v                  # Show QASM on failure
"""

import argparse
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass


# ANSI color detection
def should_use_colors() -> bool:
    """Detect if ANSI colors should be used.

    Checks (in order):
    1. NO_COLOR env var (disable if set)
    2. CLICOLOR_FORCE env var (force if set)
    3. sys.stdout.isatty() (auto-detect terminal)
    """
    if os.getenv("NO_COLOR") is not None:
        return False
    if os.getenv("CLICOLOR_FORCE") is not None:
        return True
    return sys.stdout.isatty()


# ANSI color codes
if should_use_colors():
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
else:
    GREEN = RED = YELLOW = BLUE = RESET = BOLD = ""


@dataclass
class TestCase:
    """Single deterministic verification test case."""

    name: str
    category: str
    description: str
    expected: int  # Expected integer result
    width: int  # Bit width of result register
    qasm_generator: Callable[[], str]  # Builds circuit, returns QASM string


class ArithmeticTests:
    """Arithmetic operation test cases."""

    @staticmethod
    def all_tests() -> list[TestCase]:
        """Return all arithmetic test cases."""
        return [
            ArithmeticTests.addition_basic(),
            ArithmeticTests.addition_overflow(),
            ArithmeticTests.subtraction_basic(),
            ArithmeticTests.subtraction_underflow(),
            ArithmeticTests.multiplication_basic(),
            # Multiplication overflow skipped - see note below
        ]

    @staticmethod
    def addition_basic() -> TestCase:
        """3 + 5 = 8 (4-bit operands, 5-bit result)."""

        def build():
            import quantum_language as ql

            ql.circuit()  # Reset circuit state
            a = ql.qint(3, width=4)
            b = ql.qint(5, width=4)
            _ = a + b  # Result is 5-bit (max(4,4)+1), so 8 fits
            return ql.to_openqasm()

        return TestCase(
            name="addition_basic",
            category="arithmetic",
            description="3 + 5 = 8 (4-bit inputs)",
            expected=8,
            width=5,  # Addition produces max(width_a, width_b) + 1
            qasm_generator=build,
        )

    @staticmethod
    def addition_overflow() -> TestCase:
        """Test addition overflow: 15 + 16 = 31 (5-bit signed inputs, 6-bit result)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            # Use values within 5-bit signed range [-16, 15]
            a = ql.qint(15, width=5)
            b = ql.qint(15, width=5)
            _ = a + b  # Result is 6-bit: 30
            return ql.to_openqasm()

        return TestCase(
            name="addition_overflow",
            category="arithmetic",
            description="15 + 15 = 30 (5-bit inputs, 6-bit result)",
            expected=30,
            width=6,  # Result is width+1
            qasm_generator=build,
        )

    @staticmethod
    def subtraction_basic() -> TestCase:
        """7 - 3 = 4 (4-bit)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(7, width=4)
            b = ql.qint(3, width=4)
            _ = a - b
            return ql.to_openqasm()

        return TestCase(
            name="subtraction_basic",
            category="arithmetic",
            description="7 - 3 = 4 (4-bit)",
            expected=4,
            width=4,
            qasm_generator=build,
        )

    @staticmethod
    def subtraction_underflow() -> TestCase:
        """Test subtraction underflow: 3 - 7 wraps in 4-bit space (mod 16)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(3, width=4)
            b = ql.qint(7, width=4)
            _ = a - b  # -4 mod 16 = 12
            return ql.to_openqasm()

        return TestCase(
            name="subtraction_underflow",
            category="arithmetic",
            description="3 - 7 = 12 (4-bit, wraps mod 16)",
            expected=12,
            width=4,
            qasm_generator=build,
        )

    @staticmethod
    def multiplication_basic() -> TestCase:
        """3 * 3 = 9 (3-bit operands, 6-bit result)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            # Use values within 3-bit signed range [-4, 3]
            a = ql.qint(3, width=3)
            b = ql.qint(3, width=3)
            _ = a * b  # Result is width_a + width_b = 6 bits, value = 9
            return ql.to_openqasm()

        return TestCase(
            name="multiplication_basic",
            category="arithmetic",
            description="3 * 3 = 9 (3-bit inputs, 6-bit result)",
            expected=9,
            width=6,  # Multiplication: width_a + width_b
            qasm_generator=build,
        )

    # NOTE: Multiplication overflow test skipped due to known segfault at certain widths
    # See STATE.md: "Multiplication tests segfault at certain widths (C backend issue, tracked)"


class ComparisonTests:
    """Comparison operator test cases."""

    @staticmethod
    def all_tests() -> list[TestCase]:
        """Return all comparison test cases."""
        return [
            ComparisonTests.less_than_true(),
            ComparisonTests.less_than_false(),
            ComparisonTests.less_equal_true(),
            ComparisonTests.less_equal_false(),
            ComparisonTests.equal_true(),
            ComparisonTests.equal_false(),
            ComparisonTests.greater_equal_true(),
            ComparisonTests.greater_equal_false(),
            ComparisonTests.greater_than_true(),
            ComparisonTests.greater_than_false(),
            ComparisonTests.not_equal_true(),
            ComparisonTests.not_equal_false(),
        ]

    @staticmethod
    def less_than_true() -> TestCase:
        """3 < 7 = True (1)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(3, width=4)
            b = ql.qint(7, width=4)
            _ = a < b  # Returns qbool (1-bit)
            return ql.to_openqasm()

        return TestCase(
            name="less_than_true",
            category="comparison",
            description="3 < 7 = True",
            expected=1,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def less_than_false() -> TestCase:
        """7 < 3 = False (0)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(7, width=4)
            b = ql.qint(3, width=4)
            _ = a < b
            return ql.to_openqasm()

        return TestCase(
            name="less_than_false",
            category="comparison",
            description="7 < 3 = False",
            expected=0,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def less_equal_true() -> TestCase:
        """5 <= 5 = True (1)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(5, width=4)
            b = ql.qint(5, width=4)
            _ = a <= b
            return ql.to_openqasm()

        return TestCase(
            name="less_equal_true",
            category="comparison",
            description="5 <= 5 = True",
            expected=1,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def less_equal_false() -> TestCase:
        """7 <= 3 = False (0)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(7, width=4)
            b = ql.qint(3, width=4)
            _ = a <= b
            return ql.to_openqasm()

        return TestCase(
            name="less_equal_false",
            category="comparison",
            description="7 <= 3 = False",
            expected=0,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def equal_true() -> TestCase:
        """5 == 5 = True (1)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(5, width=4)
            b = ql.qint(5, width=4)
            _ = a == b
            return ql.to_openqasm()

        return TestCase(
            name="equal_true",
            category="comparison",
            description="5 == 5 = True",
            expected=1,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def equal_false() -> TestCase:
        """3 == 7 = False (0)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(3, width=4)
            b = ql.qint(7, width=4)
            _ = a == b
            return ql.to_openqasm()

        return TestCase(
            name="equal_false",
            category="comparison",
            description="3 == 7 = False",
            expected=0,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def greater_equal_true() -> TestCase:
        """7 >= 5 = True (1)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(7, width=4)
            b = ql.qint(5, width=4)
            _ = a >= b
            return ql.to_openqasm()

        return TestCase(
            name="greater_equal_true",
            category="comparison",
            description="7 >= 5 = True",
            expected=1,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def greater_equal_false() -> TestCase:
        """3 >= 7 = False (0)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(3, width=4)
            b = ql.qint(7, width=4)
            _ = a >= b
            return ql.to_openqasm()

        return TestCase(
            name="greater_equal_false",
            category="comparison",
            description="3 >= 7 = False",
            expected=0,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def greater_than_true() -> TestCase:
        """7 > 3 = True (1)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(7, width=4)
            b = ql.qint(3, width=4)
            _ = a > b
            return ql.to_openqasm()

        return TestCase(
            name="greater_than_true",
            category="comparison",
            description="7 > 3 = True",
            expected=1,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def greater_than_false() -> TestCase:
        """3 > 7 = False (0)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(3, width=4)
            b = ql.qint(7, width=4)
            _ = a > b
            return ql.to_openqasm()

        return TestCase(
            name="greater_than_false",
            category="comparison",
            description="3 > 7 = False",
            expected=0,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def not_equal_true() -> TestCase:
        """3 != 7 = True (1)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(3, width=4)
            b = ql.qint(7, width=4)
            _ = a != b
            return ql.to_openqasm()

        return TestCase(
            name="not_equal_true",
            category="comparison",
            description="3 != 7 = True",
            expected=1,
            width=1,
            qasm_generator=build,
        )

    @staticmethod
    def not_equal_false() -> TestCase:
        """5 != 5 = False (0)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            a = ql.qint(5, width=4)
            b = ql.qint(5, width=4)
            _ = a != b
            return ql.to_openqasm()

        return TestCase(
            name="not_equal_false",
            category="comparison",
            description="5 != 5 = False",
            expected=0,
            width=1,
            qasm_generator=build,
        )


class BitwiseTests:
    """Bitwise operation test cases."""

    @staticmethod
    def all_tests() -> list[TestCase]:
        """Return all bitwise test cases."""
        return [
            BitwiseTests.and_basic(),
            BitwiseTests.or_basic(),
            BitwiseTests.xor_basic(),
            BitwiseTests.not_basic(),
        ]

    @staticmethod
    def and_basic() -> TestCase:
        """0b0101 & 0b0011 = 0b0001 = 1."""

        def build():
            import quantum_language as ql

            ql.circuit()
            # Use values within 4-bit signed range [-8, 7]
            a = ql.qint(0b0101, width=4)  # 5
            b = ql.qint(0b0011, width=4)  # 3
            _ = a & b  # Result: 0b0001 = 1
            return ql.to_openqasm()

        return TestCase(
            name="and_basic",
            category="bitwise",
            description="0b0101 & 0b0011 = 0b0001 (1)",
            expected=1,
            width=4,
            qasm_generator=build,
        )

    @staticmethod
    def or_basic() -> TestCase:
        """0b0101 | 0b0011 = 0b0111 = 7."""

        def build():
            import quantum_language as ql

            ql.circuit()
            # Use values within 4-bit signed range [-8, 7]
            a = ql.qint(0b0101, width=4)  # 5
            b = ql.qint(0b0011, width=4)  # 3
            _ = a | b  # Result: 0b0111 = 7
            return ql.to_openqasm()

        return TestCase(
            name="or_basic",
            category="bitwise",
            description="0b0101 | 0b0011 = 0b0111 (7)",
            expected=7,
            width=4,
            qasm_generator=build,
        )

    @staticmethod
    def xor_basic() -> TestCase:
        """0b0101 ^ 0b0011 = 0b0110 = 6."""

        def build():
            import quantum_language as ql

            ql.circuit()
            # Use values within 4-bit signed range [-8, 7]
            a = ql.qint(0b0101, width=4)  # 5
            b = ql.qint(0b0011, width=4)  # 3
            _ = a ^ b  # Result: 0b0110 = 6
            return ql.to_openqasm()

        return TestCase(
            name="xor_basic",
            category="bitwise",
            description="0b0101 ^ 0b0011 = 0b0110 (6)",
            expected=6,
            width=4,
            qasm_generator=build,
        )

    @staticmethod
    def not_basic() -> TestCase:
        """~0b0010 = 0b1101 = -3 in 4-bit signed (13 unsigned)."""

        def build():
            import quantum_language as ql

            ql.circuit()
            # Use value within 4-bit signed range [-8, 7]
            a = ql.qint(0b0010, width=4)  # 2
            _ = ~a  # Result: ~2 = -3 in signed, or 0b1101 = 13 unsigned
            return ql.to_openqasm()

        return TestCase(
            name="not_basic",
            category="bitwise",
            description="~0b0010 = 0b1101 (-3 signed, 13 unsigned)",
            expected=13,  # Extract as unsigned
            width=4,
            qasm_generator=build,
        )


def collect_all_tests(category: str | None = None) -> list[TestCase]:
    """Gather tests from all categories, optionally filtered by category name."""
    all_tests = []

    if category is None or category == "arithmetic":
        all_tests.extend(ArithmeticTests.all_tests())

    if category is None or category == "comparison":
        all_tests.extend(ComparisonTests.all_tests())

    if category is None or category == "bitwise":
        all_tests.extend(BitwiseTests.all_tests())

    return all_tests


def extract_result(counts: dict[str, int], test: TestCase) -> int:
    """Extract integer result from Qiskit measurement counts.

    Args:
        counts: Qiskit measurement counts dictionary
        test: Test case with expected width

    Returns:
        Integer value extracted from bitstring

    Note:
        Qiskit uses little-endian convention: rightmost bit is qubit 0 (LSB).
        We extract the last `width` bits from the full measurement bitstring.
    """
    # Get single measurement result (deterministic case)
    bitstring = list(counts.keys())[0]

    # For now, extract the rightmost (last allocated) bits
    # This assumes the result variable is the most recently allocated
    # and appears at the end of the measurement string
    if len(bitstring) >= test.width:
        result_bits = bitstring[-test.width :]
    else:
        result_bits = bitstring

    # Convert to integer (little-endian compatible)
    return int(result_bits, 2)


def run_verification(
    tests: list[TestCase],
    fail_fast: bool = False,
    show_qasm: bool = False,
    log_file: str | None = None,
) -> int:
    """Run verification tests and return exit code.

    Args:
        tests: List of test cases to run
        fail_fast: Stop on first failure
        show_qasm: Show QASM code in failure reports
        log_file: Optional path to write detailed log

    Returns:
        0 if all tests pass, 1 if any fail
    """
    try:
        import qiskit.qasm3
        from qiskit_aer import AerSimulator
    except ImportError as e:
        print(f"{RED}ERROR:{RESET} Missing required dependency: {e}")
        print("Install with: pip install qiskit>=1.0 qiskit-aer")
        return 1

    # Create simulator once
    simulator = AerSimulator(method="statevector")

    failures = []
    errors = []
    passed = 0

    print(f"\n{BOLD}Running {len(tests)} tests...{RESET}\n")

    for test in tests:
        try:
            # Generate QASM
            qasm_str = test.qasm_generator()

            # Load into Qiskit
            circuit = qiskit.qasm3.loads(qasm_str)

            # Add measurements if not present
            if not circuit.cregs:
                circuit.measure_all()

            # Simulate with 1 shot (deterministic)
            job = simulator.run(circuit, shots=1)
            result = job.result()
            counts = result.get_counts()

            # Extract result
            actual = extract_result(counts, test)

            # Verify
            if actual == test.expected:
                sys.stdout.write(f"{GREEN}.{RESET}")
                sys.stdout.flush()
                passed += 1
            else:
                sys.stdout.write(f"{RED}F{RESET}")
                sys.stdout.flush()
                failures.append(
                    {"test": test, "actual": actual, "qasm": qasm_str if show_qasm else None}
                )

                if fail_fast:
                    break

        except Exception as e:
            sys.stdout.write(f"{RED}E{RESET}")
            sys.stdout.flush()
            errors.append(
                {
                    "test": test,
                    "error": str(e),
                    "qasm": qasm_str if (show_qasm and "qasm_str" in locals()) else None,
                }
            )

            if fail_fast:
                break

    # Print summary
    total = len(tests)
    failed = len(failures) + len(errors)
    print(f"\n\n{'=' * 70}")
    print(f"{BOLD}Summary:{RESET} {passed} passed, {failed} failed out of {total} tests")
    print("=" * 70)

    # Print detailed failures
    if failures or errors:
        print(f"\n{BOLD}{RED}FAILURES AND ERRORS{RESET}")
        print("=" * 70)

        for f in failures:
            test = f["test"]
            print(f"\n{RED}FAIL:{RESET} {BOLD}{test.name}{RESET}")
            print(f"  Category:    {test.category}")
            print(f"  Description: {test.description}")
            print(f"  Expected:    {test.expected}")
            print(f"  Actual:      {f['actual']}")

            if f.get("qasm"):
                print(f"\n  {BLUE}QASM:{RESET}")
                for line in f["qasm"].split("\n")[:30]:
                    print(f"    {line}")

        for e in errors:
            test = e["test"]
            print(f"\n{RED}ERROR:{RESET} {BOLD}{test.name}{RESET}")
            print(f"  Category:    {test.category}")
            print(f"  Description: {test.description}")
            print(f"  Error:       {e['error']}")

            if e.get("qasm"):
                print(f"\n  {BLUE}QASM:{RESET}")
                for line in e["qasm"].split("\n")[:30]:
                    print(f"    {line}")

    # Write log file if requested
    if log_file:
        try:
            with open(log_file, "w") as f:
                f.write("Verification Log\n")
                f.write(f"{'=' * 70}\n")
                f.write(f"Total tests: {total}\n")
                f.write(f"Passed: {passed}\n")
                f.write(f"Failed: {failed}\n\n")

                for failure in failures:
                    test = failure["test"]
                    f.write(f"\nFAILURE: {test.name}\n")
                    f.write(f"  Category: {test.category}\n")
                    f.write(f"  Description: {test.description}\n")
                    f.write(f"  Expected: {test.expected}\n")
                    f.write(f"  Actual: {failure['actual']}\n")
                    if failure.get("qasm"):
                        f.write("\n  QASM:\n")
                        for line in failure["qasm"].split("\n"):
                            f.write(f"    {line}\n")

                for error in errors:
                    test = error["test"]
                    f.write(f"\nERROR: {test.name}\n")
                    f.write(f"  Category: {test.category}\n")
                    f.write(f"  Description: {test.description}\n")
                    f.write(f"  Error: {error['error']}\n")
                    if error.get("qasm"):
                        f.write("\n  QASM:\n")
                        for line in error["qasm"].split("\n"):
                            f.write(f"    {line}\n")

            print(f"\n{BLUE}Log written to:{RESET} {log_file}")

        except Exception as e:
            print(f"\n{RED}ERROR writing log file:{RESET} {e}")

    return 0 if (not failures and not errors) else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify quantum circuits via OpenQASM export and Qiskit simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Run all tests
  %(prog)s --category arithmetic     Run only arithmetic tests
  %(prog)s --fail-fast              Stop on first failure
  %(prog)s -v                       Show QASM for failing tests
  %(prog)s --log results.txt        Write detailed log
        """,
    )

    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")

    parser.add_argument(
        "--category",
        choices=["arithmetic", "comparison", "bitwise"],
        help="Run only tests in specified category",
    )

    parser.add_argument(
        "--show-qasm", "-v", action="store_true", help="Show QASM code for failing tests"
    )

    parser.add_argument("--log", type=str, metavar="PATH", help="Write detailed log to file")

    args = parser.parse_args()

    # Collect tests
    tests = collect_all_tests(category=args.category)

    if not tests:
        print(f"{YELLOW}WARNING:{RESET} No tests found for category '{args.category}'")
        return 0

    # Run verification
    exit_code = run_verification(
        tests=tests, fail_fast=args.fail_fast, show_qasm=args.show_qasm, log_file=args.log
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
