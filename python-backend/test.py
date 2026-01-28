#!/usr/bin/env python3
"""
Comprehensive test suite for Quantum Assembly Language.

Phase 16: Dependency Tracking Tests
Tests verify dependency tracking infrastructure for all multi-operand operations.
"""

import gc
import sys

sys.path.insert(0, ".")

import quantum_language as ql

# =============================================================================
# Phase 16: Dependency Tracking Tests
# =============================================================================


def test_dependency_tracking_bitwise_and():
    """TRACK-01: Test dependency tracking for AND operation."""
    c = ql.circuit()  # noqa: F841
    a = ql.qbool(True)
    b = ql.qbool(False)
    result = a & b

    # Should have 2 parents (a and b)
    assert len(result.dependency_parents) == 2, (
        f"Expected 2 parents, got {len(result.dependency_parents)}"
    )
    assert result.operation_type == "AND", f"Expected 'AND', got {result.operation_type}"

    # Verify parents are accessible via get_live_parents
    live_parents = result.get_live_parents()
    assert len(live_parents) == 2, "Both parents should be alive"
    print("  AND dependency tracking: PASS")


def test_dependency_tracking_bitwise_or():
    """TRACK-01: Test dependency tracking for OR operation."""
    c = ql.circuit()  # noqa: F841
    a = ql.qbool(True)
    b = ql.qbool(False)
    result = a | b

    assert len(result.dependency_parents) == 2
    assert result.operation_type == "OR"
    print("  OR dependency tracking: PASS")


def test_dependency_tracking_bitwise_xor():
    """TRACK-01: Test dependency tracking for XOR operation."""
    c = ql.circuit()  # noqa: F841
    a = ql.qbool(True)
    b = ql.qbool(False)
    result = a ^ b

    assert len(result.dependency_parents) == 2
    assert result.operation_type == "XOR"
    print("  XOR dependency tracking: PASS")


def test_dependency_tracking_classical_operand():
    """TRACK-01: Classical operands should not be tracked."""
    c = ql.circuit()  # noqa: F841
    a = ql.qint(5, width=4)
    result = a & 3  # Classical operand

    # Should only have 1 parent (a), not the classical 3
    assert len(result.dependency_parents) == 1, (
        f"Expected 1 parent for classical operand, got {len(result.dependency_parents)}"
    )
    print("  Classical operand (no tracking): PASS")


def test_dependency_tracking_not_skipped():
    """TRACK-01: Single-operand NOT should NOT create dependencies."""
    c = ql.circuit()  # noqa: F841
    a = ql.qbool(True)
    _result = ~a  # NOT is in-place, returns self  # noqa: F841

    # NOT modifies in-place, no new dependency graph entry
    # The original 'a' should still have empty dependency_parents
    assert len(a.dependency_parents) == 0, "NOT should not add dependencies (single operand)"
    print("  NOT skips dependency tracking: PASS")


def test_dependency_tracking_comparison_eq():
    """TRACK-02: Test dependency tracking for equality comparison."""
    c = ql.circuit()  # noqa: F841
    a = ql.qint(5, width=4)
    b = ql.qint(3, width=4)
    result = a == b

    assert len(result.dependency_parents) == 2, (
        f"Expected 2 parents for ==, got {len(result.dependency_parents)}"
    )
    assert result.operation_type == "EQ"
    print("  Equality comparison tracking: PASS")


def test_dependency_tracking_comparison_lt():
    """TRACK-02: Test dependency tracking for less-than comparison."""
    c = ql.circuit()  # noqa: F841
    a = ql.qint(3, width=4)
    b = ql.qint(5, width=4)
    result = a < b

    assert len(result.dependency_parents) == 2
    assert result.operation_type == "LT"
    print("  Less-than comparison tracking: PASS")


def test_dependency_tracking_comparison_gt():
    """TRACK-02: Test dependency tracking for greater-than comparison."""
    c = ql.circuit()  # noqa: F841
    a = ql.qint(5, width=4)
    b = ql.qint(3, width=4)
    result = a > b

    assert len(result.dependency_parents) == 2
    assert result.operation_type == "GT"
    print("  Greater-than comparison tracking: PASS")


def test_dependency_tracking_comparison_le():
    """TRACK-02: Test dependency tracking for less-than-or-equal comparison."""
    c = ql.circuit()  # noqa: F841
    a = ql.qint(3, width=4)
    b = ql.qint(5, width=4)
    result = a <= b

    assert len(result.dependency_parents) == 2
    assert result.operation_type == "LE"
    print("  Less-than-or-equal comparison tracking: PASS")


def test_dependency_tracking_comparison_classical():
    """TRACK-02: Classical comparisons track only qint operand."""
    c = ql.circuit()  # noqa: F841
    a = ql.qint(5, width=4)
    result = a == 3  # Classical operand

    assert len(result.dependency_parents) == 1, "Classical comparison should track only qint"
    print("  Classical comparison tracking: PASS")


def test_dependency_weak_references():
    """TRACK-03: Weak references allow garbage collection."""
    c = ql.circuit()  # noqa: F841

    a = ql.qbool(True)
    b = ql.qbool(False)
    result = a & b

    # Both parents alive
    assert len(result.get_live_parents()) == 2

    # Delete one parent
    del a
    gc.collect()

    # Now only one parent should be alive
    live = result.get_live_parents()
    assert len(live) == 1, f"Expected 1 live parent after del, got {len(live)}"
    print("  Weak references allow GC: PASS")


def test_dependency_creation_order():
    """TRACK-03: Creation order prevents circular references."""
    c = ql.circuit()  # noqa: F841
    a = ql.qbool(True)
    b = ql.qbool(False)
    result = a & b

    # Verify creation order is assigned
    assert a._creation_order < b._creation_order < result._creation_order, (
        "Creation order should be monotonically increasing"
    )

    # Attempting to add result as dependency of itself should fail
    # (this would be caught by the assertion in add_dependency)
    try:
        result.add_dependency(result)
        raise AssertionError("Should have raised AssertionError for self-dependency")
    except AssertionError as e:
        if "Should have raised" in str(e):
            raise
        pass  # Expected cycle detection error

    print("  Creation order cycle prevention: PASS")


def test_dependency_scope_capture():
    """TRACK-04: Scope depth is captured at creation time."""
    c = ql.circuit()  # noqa: F841

    # Top level (scope 0)
    a = ql.qbool(True)
    assert a.creation_scope == 0, f"Expected scope 0, got {a.creation_scope}"

    print("  Scope depth capture: PASS")


def test_dependency_control_context_capture():
    """TRACK-04: Control context is captured at creation time."""
    c = ql.circuit()  # noqa: F841

    # Outside with block - no control
    a = ql.qbool(True)
    assert len(a.control_context) == 0, "No control context outside with block"

    # Inside with block - control qubit captured
    control = ql.qbool(True)
    with control:
        b = ql.qbool(False)
        # b should have captured control's qubit
        assert len(b.control_context) == 1, (
            f"Expected 1 control qubit, got {len(b.control_context)}"
        )

    print("  Control context capture: PASS")


def test_dependency_chained_operations():
    """Test dependency tracking through chained operations."""
    c = ql.circuit()  # noqa: F841
    a = ql.qbool(True)
    b = ql.qbool(False)
    d = ql.qbool(True)

    # c = a & b, then e = c | d
    intermediate = a & b
    final = intermediate | d

    # final should have 2 parents: intermediate and d
    assert len(final.dependency_parents) == 2

    # intermediate should have 2 parents: a and b
    assert len(intermediate.dependency_parents) == 2

    print("  Chained operation tracking: PASS")


def run_dependency_tracking_tests():
    """Run all Phase 16 dependency tracking tests."""
    print("\n=== Phase 16: Dependency Tracking Tests ===")

    test_dependency_tracking_bitwise_and()
    test_dependency_tracking_bitwise_or()
    test_dependency_tracking_bitwise_xor()
    test_dependency_tracking_classical_operand()
    test_dependency_tracking_not_skipped()
    test_dependency_tracking_comparison_eq()
    test_dependency_tracking_comparison_lt()
    test_dependency_tracking_comparison_gt()
    test_dependency_tracking_comparison_le()
    test_dependency_tracking_comparison_classical()
    test_dependency_weak_references()
    test_dependency_creation_order()
    test_dependency_scope_capture()
    test_dependency_control_context_capture()
    test_dependency_chained_operations()

    print("\n=== All Dependency Tracking Tests PASSED ===\n")


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == "__main__":
    try:
        run_dependency_tracking_tests()
        print("\nAll tests completed successfully!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n\nTest FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
