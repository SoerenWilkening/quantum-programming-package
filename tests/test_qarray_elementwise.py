"""Tests for qarray element-wise operations - Phase 24 Element-wise Operations."""

import numpy as np
import pytest

import quantum_language as ql
from quantum_language.qarray import qarray
from quantum_language.qbool import qbool
from quantum_language.qint import qint


class TestElementwiseArithmetic:
    """ELM-01: Element-wise arithmetic operators."""

    def test_add_arrays(self):
        """C = A + B returns qarray with correct shape."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([4, 5, 6])
        c = a + b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_sub_arrays(self):
        """C = A - B returns qarray with correct shape."""
        _c = ql.circuit()
        a = ql.array([10, 20, 30])
        b = ql.array([1, 2, 3])
        c = a - b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_mul_arrays(self):
        """C = A * B returns qarray with correct shape."""
        pytest.skip("Multiplication inherits C backend segfault issue")
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([4, 5, 6])
        c = a * b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_add_scalar_int(self):
        """C = A + 5 broadcasts scalar to all elements."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = a + 5
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_add_scalar_reverse(self):
        """C = 5 + A works via __radd__."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = 5 + a
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_sub_scalar(self):
        """C = A - 5 broadcasts scalar."""
        _c = ql.circuit()
        a = ql.array([10, 20, 30])
        c = a - 5
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_sub_scalar_reverse(self):
        """C = 5 - A works via __rsub__ (non-commutative)."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = 5 - a
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_mul_scalar(self):
        """C = A * 5 broadcasts scalar."""
        pytest.skip("Multiplication inherits C backend segfault issue")
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = a * 5
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_mul_scalar_reverse(self):
        """C = 5 * A works via __rmul__."""
        pytest.skip("Multiplication inherits C backend segfault issue")
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = 5 * a
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_add_scalar_qint(self):
        """C = A + qint broadcasts qint scalar."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        s = qint(5, width=8)
        c = a + s
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint


class TestElementwiseBitwise:
    """ELM-02: Element-wise bitwise operators."""

    def test_and_arrays(self):
        """C = A & B returns qarray."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        b = ql.array([1, 4, 2])
        c = a & b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_or_arrays(self):
        """C = A | B returns qarray."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        b = ql.array([1, 4, 2])
        c = a | b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_xor_arrays(self):
        """C = A ^ B returns qarray."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        b = ql.array([1, 4, 2])
        c = a ^ b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_and_scalar(self):
        """C = A & 3 broadcasts scalar."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = a & 3
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_and_scalar_reverse(self):
        """C = 3 & A works via __rand__."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = 3 & a
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_or_scalar(self):
        """C = A | 3 broadcasts scalar."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = a | 3
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_or_scalar_reverse(self):
        """C = 3 | A works via __ror__."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = 3 | a
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_xor_scalar(self):
        """C = A ^ 3 broadcasts scalar."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = a ^ 3
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_xor_scalar_reverse(self):
        """C = 3 ^ A works via __rxor__."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = 3 ^ a
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint


class TestElementwiseComparison:
    """ELM-03: Element-wise comparison operators."""

    def test_lt_arrays(self):
        """C = A < B returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        b = ql.array([2, 4, 6])
        c = a < b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_le_arrays(self):
        """C = A <= B returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        b = ql.array([2, 4, 6])
        c = a <= b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_gt_arrays(self):
        """C = A > B returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        b = ql.array([2, 4, 6])
        c = a > b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_ge_arrays(self):
        """C = A >= B returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        b = ql.array([2, 4, 6])
        c = a >= b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_eq_arrays(self):
        """C = A == B returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        b = ql.array([2, 4, 6])
        c = a == b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_ne_arrays(self):
        """C = A != B returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        b = ql.array([2, 4, 6])
        c = a != b
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_lt_scalar(self):
        """C = A < 5 broadcasts scalar comparison."""
        _c = ql.circuit()
        a = ql.array([1, 5, 10])
        c = a < 5
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_le_scalar(self):
        """C = A <= 5 broadcasts scalar comparison."""
        _c = ql.circuit()
        a = ql.array([1, 5, 10])
        c = a <= 5
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_gt_scalar(self):
        """C = A > 5 broadcasts scalar comparison."""
        _c = ql.circuit()
        a = ql.array([1, 5, 10])
        c = a > 5
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_comparison_width(self):
        """Comparison result has width=1 (qbool)."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([4, 5, 6])
        c = a < b
        assert c.width == 1


class TestShapeValidation:
    """ELM-04: Shape validation for element-wise operations."""

    def test_shape_mismatch_arithmetic(self):
        """Mismatched shapes raise ValueError for arithmetic."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([1, 2])
        with pytest.raises(ValueError, match="Shape mismatch"):
            a + b

    def test_shape_mismatch_bitwise(self):
        """Mismatched shapes raise ValueError for bitwise."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([1, 2])
        with pytest.raises(ValueError, match="Shape mismatch"):
            a & b

    def test_shape_mismatch_comparison(self):
        """Mismatched shapes raise ValueError for comparison."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([1, 2])
        with pytest.raises(ValueError, match="Shape mismatch"):
            _ = a < b

    def test_shape_mismatch_inplace(self):
        """Mismatched shapes raise ValueError for in-place."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([1, 2])
        with pytest.raises(ValueError, match="Shape mismatch"):
            a += b

    def test_error_shows_both_shapes(self):
        """Error message contains both shapes."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([1, 2])
        with pytest.raises(ValueError) as exc_info:
            a + b
        msg = str(exc_info.value)
        assert "(3,)" in msg
        assert "(2,)" in msg


class TestInplaceOperations:
    """ELM-05: In-place element-wise operations."""

    def test_iadd_array(self):
        """A += B modifies A in-place."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([4, 5, 6])
        orig_id = id(a)
        a += b
        assert id(a) == orig_id  # Same object
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_isub_array(self):
        """A -= B modifies A in-place."""
        _c = ql.circuit()
        a = ql.array([10, 20, 30])
        b = ql.array([1, 2, 3])
        orig_id = id(a)
        a -= b
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_imul_array(self):
        """A *= B modifies A in-place."""
        pytest.skip("Multiplication inherits C backend segfault issue")
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        b = ql.array([4, 5, 6])
        orig_id = id(a)
        a *= b
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_iand_array(self):
        """A &= B modifies A in-place."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        b = ql.array([1, 4, 2])
        orig_id = id(a)
        a &= b
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_ior_array(self):
        """A |= B modifies A in-place."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        b = ql.array([1, 4, 2])
        orig_id = id(a)
        a |= b
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_ixor_array(self):
        """A ^= B modifies A in-place."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        b = ql.array([1, 4, 2])
        orig_id = id(a)
        a ^= b
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_iadd_scalar(self):
        """A += 5 broadcasts scalar in-place."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        orig_id = id(a)
        a += 5
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_isub_scalar(self):
        """A -= 5 broadcasts scalar in-place."""
        _c = ql.circuit()
        a = ql.array([10, 20, 30])
        orig_id = id(a)
        a -= 5
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)

    def test_iand_scalar(self):
        """A &= 3 broadcasts scalar in-place."""
        pytest.skip(
            "In-place AND with scalar triggers uncomputation issue in qint.__iand__ - pre-existing C backend issue"
        )
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        orig_id = id(a)
        a &= 3
        assert id(a) == orig_id
        assert isinstance(a, qarray)
        assert a.shape == (3,)


class TestShapePreservation:
    """Result arrays preserve input shape."""

    def test_2d_add_preserves_shape(self):
        """2D array addition preserves shape."""
        _c = ql.circuit()
        a = ql.array([[1, 2], [3, 4]])
        b = ql.array([[5, 6], [7, 8]])
        c = a + b
        assert c.shape == (2, 2)
        assert isinstance(c, qarray)

    def test_2d_sub_preserves_shape(self):
        """2D array subtraction preserves shape."""
        _c = ql.circuit()
        a = ql.array([[10, 20], [30, 40]])
        b = ql.array([[1, 2], [3, 4]])
        c = a - b
        assert c.shape == (2, 2)
        assert isinstance(c, qarray)

    def test_2d_bitwise_preserves_shape(self):
        """2D bitwise operation preserves shape."""
        _c = ql.circuit()
        a = ql.array([[3, 5], [7, 9]])
        b = ql.array([[1, 4], [2, 8]])
        c = a & b
        assert c.shape == (2, 2)
        assert isinstance(c, qarray)

    def test_2d_comparison_preserves_shape(self):
        """2D comparison preserves shape."""
        _c = ql.circuit()
        a = ql.array([[1, 2], [3, 4]])
        b = ql.array([[5, 6], [7, 8]])
        c = a < b
        assert c.shape == (2, 2)
        assert c.dtype == qbool

    def test_2d_inplace_preserves_shape(self):
        """2D in-place operation preserves shape."""
        _c = ql.circuit()
        a = ql.array([[1, 2], [3, 4]])
        b = ql.array([[5, 6], [7, 8]])
        orig_id = id(a)
        a += b
        assert id(a) == orig_id
        assert a.shape == (2, 2)

    def test_scalar_on_2d_preserves_shape(self):
        """Scalar broadcast on 2D array preserves shape."""
        _c = ql.circuit()
        a = ql.array([[1, 2], [3, 4]])
        c = a + 10
        assert c.shape == (2, 2)
        assert isinstance(c, qarray)

    def test_scalar_comparison_on_2d_preserves_shape(self):
        """Scalar comparison on 2D array preserves shape."""
        _c = ql.circuit()
        a = ql.array([[1, 2], [3, 4]])
        c = a < 3
        assert c.shape == (2, 2)
        assert c.dtype == qbool


class TestListArithmetic:
    """Element-wise arithmetic between qarray and Python list."""

    def test_add_list(self):
        """qarray + list returns qarray with correct shape."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = a + [4, 5, 6]
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_radd_list(self):
        """list + qarray returns qarray via __radd__."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = [4, 5, 6] + a
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_sub_list(self):
        """qarray - list returns qarray."""
        _c = ql.circuit()
        a = ql.array([10, 20, 30])
        c = a - [1, 2, 3]
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_rsub_list(self):
        """list - qarray returns qarray via __rsub__."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = [10, 20, 30] - a
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_and_list(self):
        """qarray & list returns qarray."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = a & [1, 4, 2]
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_or_list(self):
        """qarray | list returns qarray."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = a | [1, 4, 2]
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_xor_list(self):
        """qarray ^ list returns qarray."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = a ^ [1, 4, 2]
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_lt_list(self):
        """qarray < list returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        c = a < [2, 4, 6]
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_eq_list(self):
        """qarray == list returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = a == [1, 5, 3]
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_list_shape_mismatch(self):
        """Mismatched list shape raises ValueError."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        with pytest.raises(ValueError, match="Shape mismatch"):
            a + [1, 2]

    def test_iadd_list(self):
        """qarray += list modifies in-place."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        orig_id = id(a)
        a += [10, 20, 30]
        assert id(a) == orig_id
        assert a.shape == (3,)

    def test_isub_list(self):
        """qarray -= list modifies in-place."""
        _c = ql.circuit()
        a = ql.array([10, 20, 30])
        orig_id = id(a)
        a -= [1, 2, 3]
        assert id(a) == orig_id
        assert a.shape == (3,)

    def test_2d_add_list(self):
        """2D qarray + nested list preserves shape."""
        _c = ql.circuit()
        a = ql.array([[1, 2], [3, 4]])
        c = a + [[10, 20], [30, 40]]
        assert isinstance(c, qarray)
        assert c.shape == (2, 2)


class TestNumpyArithmetic:
    """Element-wise arithmetic between qarray and numpy array."""

    def test_add_numpy(self):
        """qarray + np.ndarray returns qarray."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = a + np.array([4, 5, 6])
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qint

    def test_radd_numpy(self):
        """np.ndarray + qarray returns qarray via __radd__."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = np.array([4, 5, 6]) + a
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_sub_numpy(self):
        """qarray - np.ndarray returns qarray."""
        _c = ql.circuit()
        a = ql.array([10, 20, 30])
        c = a - np.array([1, 2, 3])
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_rsub_numpy(self):
        """np.ndarray - qarray returns qarray via __rsub__."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        c = np.array([10, 20, 30]) - a
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_and_numpy(self):
        """qarray & np.ndarray returns qarray."""
        _c = ql.circuit()
        a = ql.array([3, 5, 7])
        c = a & np.array([1, 4, 2])
        assert isinstance(c, qarray)
        assert c.shape == (3,)

    def test_lt_numpy(self):
        """qarray < np.ndarray returns qbool array."""
        _c = ql.circuit()
        a = ql.array([1, 5, 3])
        c = a < np.array([2, 4, 6])
        assert isinstance(c, qarray)
        assert c.shape == (3,)
        assert c.dtype == qbool

    def test_numpy_shape_mismatch(self):
        """Mismatched numpy shape raises ValueError."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        with pytest.raises(ValueError, match="Shape mismatch"):
            a + np.array([1, 2])

    def test_iadd_numpy(self):
        """qarray += np.ndarray modifies in-place."""
        _c = ql.circuit()
        a = ql.array([1, 2, 3])
        orig_id = id(a)
        a += np.array([10, 20, 30])
        assert id(a) == orig_id
        assert a.shape == (3,)

    def test_2d_add_numpy(self):
        """2D qarray + 2D np.ndarray preserves shape."""
        _c = ql.circuit()
        a = ql.array([[1, 2], [3, 4]])
        c = a + np.array([[10, 20], [30, 40]])
        assert isinstance(c, qarray)
        assert c.shape == (2, 2)
