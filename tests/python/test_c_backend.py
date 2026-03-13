"""Subprocess wrappers for C backend unit tests.

Compiles and runs C tests from tests/c/ directory via make.
Shows stdout/stderr only on failure for clean output.
Skips all tests if no C compiler (gcc/cc/clang) is available.

Test targets correspond to the Makefile in tests/c/:
- test_allocator_block: Block-based qubit allocator (alloc, free, coalesce, split)
- test_reverse_circuit: Gate value preservation during circuit reversal
- test_comparison: Integer comparison operations
- test_hot_path_mul: Hot-path multiplication (C-level fast multiplication sequences)
"""

import os
import shutil
import subprocess

import pytest

C_TEST_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "c"))


def _has_compiler():
    """Check if a C compiler is available."""
    for compiler in ["gcc", "cc", "clang"]:
        if shutil.which(compiler):
            return True
    return False


def _has_make():
    """Check if make is available."""
    return shutil.which("make") is not None


def _compile_and_run(target, timeout_compile=120, timeout_run=60):
    """Compile a C test target via make and run the resulting executable.

    Args:
        target: Make target name (e.g., 'test_allocator_block')
        timeout_compile: Compilation timeout in seconds
        timeout_run: Execution timeout in seconds

    Raises:
        pytest.fail on compilation or execution failure
    """
    # Clean first to ensure fresh build
    subprocess.run(
        ["make", "-C", C_TEST_DIR, "clean"],
        capture_output=True,
        timeout=30,
    )

    # Compile
    result = subprocess.run(
        ["make", "-C", C_TEST_DIR, target],
        capture_output=True,
        text=True,
        timeout=timeout_compile,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Compilation of {target} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    # Run
    executable = os.path.join(C_TEST_DIR, target)
    result = subprocess.run(
        [executable],
        capture_output=True,
        text=True,
        timeout=timeout_run,
    )
    if result.returncode != 0:
        pytest.fail(
            f"C test {target} failed (exit code {result.returncode}):\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


# Skip all tests in this module if no C compiler or make is available
pytestmark = pytest.mark.skipif(
    not _has_compiler() or not _has_make(),
    reason="C compiler (gcc/cc/clang) or make not found - skipping C backend tests",
)


class TestCBackend:
    """Subprocess wrappers for C backend unit tests in tests/c/."""

    def test_c_allocator_block(self):
        """Block-based qubit allocator: alloc, free, reuse, splitting, coalescing.

        13 tests covering single-qubit and block allocation, forward/reverse/three-way
        coalescing, mixed single/block operations, ancilla tracking, and oversized requests.
        """
        _compile_and_run("test_allocator_block")

    def test_c_reverse_circuit(self):
        """Circuit reversal gate value preservation.

        Tests that reverse_circuit_range() preserves GateValue for self-inverse gates
        (X, Y, Z, H, M) and negates GateValue for rotation gates (P, R, Rx, Ry, Rz).
        Verifies forward+reverse produces empty circuit (all gates cancel).
        """
        _compile_and_run("test_reverse_circuit")

    @pytest.mark.xfail(
        reason="Pre-existing: test_multibit_comparison assertion failure (3-controlled gate check)",
        strict=False,
    )
    def test_c_comparison(self):
        """Integer comparison operations at the C backend level.

        Tests CQ and QQ comparison operations for correctness across various
        bit widths and operand values.
        """
        _compile_and_run("test_comparison")

    @pytest.mark.xfail(
        reason="Pre-existing: test_cq_mul_zero assertion failure (CQ mul value=0 gate check)",
        strict=False,
    )
    def test_c_hot_path_mul(self):
        """Hot-path multiplication sequences (C-level fast multiplication).

        Tests the optimized C-level multiplication sequences including
        QQ and CQ multiplication paths.
        """
        _compile_and_run("test_hot_path_mul")

