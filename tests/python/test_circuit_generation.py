"""Characterization tests for circuit generation and output.

These tests capture the CURRENT BEHAVIOR of circuit generation as of 2026-01-26.
They serve as golden masters to detect regressions during refactoring.

Tests verify that circuit operations complete successfully,
not that they produce specific gate sequences.

Note: print_circuit() uses C stdout directly, so output cannot be captured
by Python's redirect_stdout. Tests verify the function completes without error.
"""

import quantum_language as ql

# ============================================================================
# Circuit Output Tests
# ============================================================================


def test_print_circuit_runs():
    """Test that print_circuit executes without error."""
    # Create qint and perform operation
    a = ql.qint(value=5, bits=8)
    a += 3

    # Call print_circuit - should complete without exception
    # (Output goes to C stdout, not capturable by Python)
    a.print_circuit()
    # If we got here, test passed


def test_print_circuit_multiple_operations():
    """Test circuit print after multiple operations."""
    # Create qints and perform multiple operations
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)
    c = a + b
    c -= 2

    # Should be able to print circuit
    c.print_circuit()
    # If we got here, test passed


# ============================================================================
# Circuit Initialization Tests
# ============================================================================


def test_circuit_initialization():
    """Test that circuit is initialized on first qint creation."""
    # Circuit should be initialized when creating first qint
    a = ql.qint(value=5, bits=8)

    # Should be able to print circuit
    a.print_circuit()
    # Test passes if no exception raised


def test_multiple_qints_same_circuit():
    """Test that multiple qints can print circuit."""
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)

    # Both should be able to print the circuit
    a.print_circuit()
    b.print_circuit()
    # Test passes if no exceptions


# ============================================================================
# Circuit Structure Tests
# ============================================================================


def test_circuit_with_operations():
    """Test that performing operations doesn't break circuit printing."""
    a = ql.qint(value=5, bits=8)

    # Print after creation
    a.print_circuit()

    # Perform operation
    a += 5

    # Print after operation
    a.print_circuit()
    # Both prints should succeed


# ============================================================================
# Integration-style Characterization Tests
# ============================================================================


def test_tic_tac_toe_pattern():
    """Test simplified tic-tac-toe pattern from test.py.

    This characterizes a realistic usage pattern combining:
    - Array creation
    - Controlled operations
    - Logic operations
    - Arithmetic operations
    """
    # Create grid (simplified - just 2x2 instead of 3x3)
    assigned = ql.array((2, 2), dtype=ql.qbool)
    unoccupied = ql.array((2, 2), dtype=ql.qbool)

    # Initialize unoccupied to True
    for i in range(2):
        for j in range(2):
            unoccupied[i][j] = ~unoccupied[i][j]

    # Create counter
    count_cross = ql.qint(value=0, bits=2)

    # Perform controlled operations (simplified pattern)
    for row in range(2):
        for col in range(2):
            # Conditional increment
            with ~assigned[row][col] & ~unoccupied[row][col]:
                count_cross += 1

    # Verify circuit can be printed
    count_cross.print_circuit()
    # Test passes if no exception


def test_conditional_arithmetic():
    """Test arithmetic operations within conditional context."""
    control = ql.qbool()
    counter = ql.qint(value=0, bits=4)

    # Conditional operations
    with control:
        counter += 1
        counter += 2
        counter -= 1

    # Verify circuit can be printed
    counter.print_circuit()
    # Test passes if no exception


def test_comparison_and_logic():
    """Test combining comparisons with logic operations."""
    a = ql.qint(value=5, bits=8)
    b = ql.qint(value=3, bits=8)

    # Create comparison results
    greater = a > b
    less = a < 10

    # Combine with logic
    result = greater & less

    # Use in conditional
    counter = ql.qint(value=0, bits=4)
    with result:
        counter += 1

    # Verify circuit can be printed
    counter.print_circuit()
    # Test passes if no exception


# ============================================================================
# Edge Cases
# ============================================================================


def test_circuit_with_no_operations():
    """Test circuit print with qints but no operations."""
    a = ql.qint(value=5, bits=8)

    # Print circuit without performing operations
    a.print_circuit()
    # Should complete without error


def test_circuit_with_only_qbool():
    """Test circuit with only qbool operations."""
    a = ql.qbool()
    b = ql.qbool()
    c = a & b

    # Print circuit
    c.print_circuit()
    # Should complete without error


def test_large_array_circuit():
    """Test circuit generation with larger arrays."""
    # Create larger array
    arr = ql.array(5, dtype=ql.qint)

    # Perform operations on array elements
    for element in arr:
        element += 1

    # Verify circuit can be printed
    arr[0].print_circuit()
    # Test passes if no exception
