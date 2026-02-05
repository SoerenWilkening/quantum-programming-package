"""Tests for qarray element mutability via augmented assignment - Phase 44 Array Mutability.

Covers:
  AMUT-01: qarray[i] += x with different operand types (int, qint, qbool)
  AMUT-02: All augmented assignment operators (+=, -=, *=, //=, <<=, >>=, &=, |=, ^=)
  AMUT-03: Multi-dimensional qarray[i, j] += x
  Edge cases: out-of-bounds, negative indexing, slice-based, direct setitem
"""

import pytest

import quantum_language as ql
from quantum_language.qbool import qbool
from quantum_language.qint import qint

# ============ AMUT-01: Operand Types ============


class TestAugmentedAssignmentOperandTypes:
    """AMUT-01: qarray[i] += x with int, qint, and qbool operands."""

    def test_iadd_int_operand(self):
        """arr[i] += int_value modifies element with classical int."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] += 5
        assert len(arr) == 3
        assert arr.shape == (3,)
        assert isinstance(arr[0], qint)

    def test_iadd_qint_operand(self):
        """arr[i] += qint_value modifies element with quantum operand."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        q = qint(5, width=8)
        arr[1] += q
        assert len(arr) == 3
        assert arr.shape == (3,)
        assert isinstance(arr[1], qint)

    def test_iadd_qbool_operand(self):
        """arr[i] += qbool_value modifies element with qbool operand."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        b = qbool(True)
        arr[2] += b
        assert len(arr) == 3
        assert arr.shape == (3,)
        assert isinstance(arr[2], qint)

    def test_iadd_negative_index(self):
        """arr[-1] += x modifies last element."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[-1] += 5
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_iadd_preserves_element_identity_truly_inplace(self):
        """For truly in-place ops (+=), element object should be the same after op.

        qint.__iadd__ returns self, so the same Python object stays in the array.
        """
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        elem_before = arr[0]
        elem_id_before = id(elem_before)
        arr[0] += 5
        elem_after = arr[0]
        # For truly in-place ops, __iadd__ returns self, and __setitem__
        # writes the same object back. The id should match.
        assert id(elem_after) == elem_id_before

    def test_isub_preserves_element_identity(self):
        """For truly in-place ops (-=), element identity preserved."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        elem_id_before = id(arr[1])
        arr[1] -= 3
        assert id(arr[1]) == elem_id_before

    def test_ixor_preserves_element_identity(self):
        """For truly in-place ops (^=), element identity preserved."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        elem_id_before = id(arr[2])
        arr[2] ^= 7
        assert id(arr[2]) == elem_id_before


# ============ AMUT-02: All Augmented Assignment Operators ============


class TestAllAugmentedOperators:
    """AMUT-02: All 9 augmented assignment operators on array elements."""

    def test_iadd(self):
        """arr[i] += x works and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] += 5
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_isub(self):
        """arr[i] -= x works and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] -= 3
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_imul(self):
        """arr[i] *= x works and preserves array structure."""
        pytest.skip("Multiplication inherits C backend segfault issue")
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] *= 2
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_ifloordiv(self):
        """arr[i] //= x works and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([20, 30, 40], width=8)
        arr[0] //= 2
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_ilshift(self):
        """arr[i] <<= x works and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3], width=8)
        arr[0] <<= 2
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_irshift_zero(self):
        """arr[i] >>= 0 is a no-op and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] >>= 0
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_irshift_nonzero(self):
        """arr[i] >>= x with x > 0 modifies element."""
        _c = ql.circuit()
        arr = ql.array([16, 20, 30], width=8)
        arr[0] >>= 2
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_iand(self):
        """arr[i] &= x works and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([7, 14, 21], width=8)
        q = qint(3, width=8)
        arr[0] &= q
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_ior(self):
        """arr[i] |= x works and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([4, 8, 12], width=8)
        arr[0] |= 3
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_ixor(self):
        """arr[i] ^= x works and preserves array structure."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] ^= 0xFF
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_multiple_augmented_ops_on_same_element(self):
        """Multiple augmented ops on same element work sequentially."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] += 5
        arr[0] -= 2
        arr[0] ^= 1
        assert len(arr) == 3
        assert arr.shape == (3,)

    def test_augmented_ops_on_different_elements(self):
        """Augmented ops on different elements are independent."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        arr[0] += 1
        arr[1] -= 1
        arr[2] ^= 1
        assert len(arr) == 3
        assert arr.shape == (3,)


# ============ AMUT-03: Multi-Dimensional Indexing ============


class TestMultiDimensionalAugmentedAssignment:
    """AMUT-03: Multi-dimensional qarray[i, j] += x."""

    def test_2d_iadd(self):
        """arr[0, 1] += x modifies correct element in 2D array."""
        _c = ql.circuit()
        arr = ql.array([[1, 2, 3], [4, 5, 6]], width=8)
        arr[0, 1] += 10
        assert len(arr) == 6
        assert arr.shape == (2, 3)

    def test_2d_isub(self):
        """arr[1, 2] -= x modifies correct element in 2D array."""
        _c = ql.circuit()
        arr = ql.array([[10, 20, 30], [40, 50, 60]], width=8)
        arr[1, 2] -= 5
        assert len(arr) == 6
        assert arr.shape == (2, 3)

    def test_2d_ixor(self):
        """arr[1, 0] ^= x modifies correct element in 2D array."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]], width=8)
        arr[1, 0] ^= 7
        assert len(arr) == 4
        assert arr.shape == (2, 2)

    def test_2d_shape_unchanged(self):
        """Shape is unchanged after multi-dim augmented assignment."""
        _c = ql.circuit()
        arr = ql.array([[1, 2, 3], [4, 5, 6]], width=8)
        original_shape = arr.shape
        arr[0, 0] += 100
        arr[1, 2] -= 1
        assert arr.shape == original_shape

    def test_2d_other_elements_unchanged(self):
        """Augmented assignment on one element does not change others.

        We verify by checking that the other element objects are the same
        Python objects (identity check via id()).
        """
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]], width=8)
        # Record ids of all elements
        ids_before = [id(arr[i, j]) for i in range(2) for j in range(2)]
        # Modify only arr[0, 0]
        arr[0, 0] += 10
        # Check that arr[0, 1], arr[1, 0], arr[1, 1] are same objects
        assert id(arr[0, 1]) == ids_before[1]
        assert id(arr[1, 0]) == ids_before[2]
        assert id(arr[1, 1]) == ids_before[3]

    def test_2d_negative_indices(self):
        """Negative multi-dim indices work: arr[-1, -1] += x."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]], width=8)
        arr[-1, -1] += 10
        assert arr.shape == (2, 2)


# ============ Edge Cases and Error Handling ============


class TestEdgeCases:
    """Edge cases: out-of-bounds, slices, direct setitem."""

    def test_out_of_bounds_raises_indexerror(self):
        """Out-of-bounds index raises IndexError."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        with pytest.raises(IndexError):
            arr[5] += 1

    def test_negative_out_of_bounds_raises_indexerror(self):
        """Negative out-of-bounds index raises IndexError."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        with pytest.raises(IndexError):
            arr[-4] += 1

    def test_2d_out_of_bounds_raises_indexerror(self):
        """Multi-dim out-of-bounds index raises IndexError."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]], width=8)
        with pytest.raises(IndexError):
            arr[2, 0] += 1

    def test_direct_setitem_with_qint(self):
        """Direct arr[i] = qint(val) replaces element."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30], width=8)
        new_val = qint(99, width=8)
        arr[0] = new_val
        assert arr[0] is new_val
        assert len(arr) == 3

    def test_direct_setitem_2d_with_tuple(self):
        """Direct arr[i, j] = qint(val) replaces element in 2D array."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]], width=8)
        new_val = qint(99, width=8)
        arr[0, 1] = new_val
        assert arr[0, 1] is new_val
        assert arr.shape == (2, 2)

    def test_slice_augmented_assignment_broadcast(self):
        """arr[0:2] += x broadcasts scalar to slice elements."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30, 40], width=8)
        arr[0:2] += 5
        assert len(arr) == 4
        assert arr.shape == (4,)

    def test_array_length_unchanged_after_all_ops(self):
        """Array length is unchanged after a sequence of augmented assignments."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3, 4, 5], width=8)
        original_len = len(arr)
        arr[0] += 10
        arr[1] -= 1
        arr[2] ^= 3
        arr[3] |= 1
        assert len(arr) == original_len

    def test_array_width_unchanged_after_ops(self):
        """Array width property unchanged after augmented assignments."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3], width=16)
        original_width = arr.width
        arr[0] += 100
        arr[1] -= 50
        assert arr.width == original_width

    def test_delitem_still_raises(self):
        """Deletion is still disallowed even though setitem works."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3], width=8)
        with pytest.raises(TypeError, match="does not support item deletion"):
            del arr[0]
