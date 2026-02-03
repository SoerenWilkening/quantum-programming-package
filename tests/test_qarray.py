"""Tests for qarray class - Phase 22 Array Class Foundation."""

import numpy as np
import pytest

import quantum_language as ql
from quantum_language.qarray import qarray
from quantum_language.qbool import qbool
from quantum_language.qint import qint


class TestQarrayConstruction:
    """Test ARR-01 through ARR-08: Array construction."""

    def test_create_from_list(self):
        """ARR-04: Initialize from Python list with auto-width."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        assert isinstance(arr, qarray)
        assert arr.shape == (3,)
        assert arr.width == 8  # INTEGERSIZE default

    def test_create_from_list_large_values(self):
        """ARR-04: Auto-width from large values."""
        _c = ql.circuit()
        arr = ql.array([0, 1000])
        assert arr.width == 10  # 1000 needs 10 bits

    def test_create_with_explicit_width(self):
        """ARR-05: Initialize with explicit width."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3], width=16)
        assert arr.width == 16

    def test_create_from_dimensions(self):
        """ARR-06: Initialize from dimensions."""
        _c = ql.circuit()
        arr = ql.array(dim=(3, 3), dtype=ql.qint)
        assert arr.shape == (3, 3)
        assert len(arr) == 9

    def test_create_qbool_array(self):
        """ARR-03: Support qbool arrays."""
        _c = ql.circuit()
        arr = ql.array([True, False, True], dtype=ql.qbool)
        assert arr.dtype == qbool
        assert arr.width == 1

    def test_create_from_numpy(self):
        """ARR-04: Initialize from NumPy array."""
        _c = ql.circuit()
        np_arr = np.array([1, 2, 3], dtype=np.int32)
        arr = ql.array(np_arr)
        assert arr.shape == (3,)
        assert arr.width == 32

    def test_multidimensional(self):
        """ARR-07: Support multi-dimensional arrays."""
        _c = ql.circuit()
        arr = ql.array([[1, 2, 3], [4, 5, 6]])
        assert arr.shape == (2, 3)
        assert len(arr) == 6

    def test_jagged_array_error(self):
        """ARR-07: Jagged arrays raise error."""
        _c = ql.circuit()
        with pytest.raises(ValueError, match="Jagged"):
            ql.array([[1, 2], [3]])

    def test_mixed_type_error(self):
        """ARR-08: Mixed qint/qbool raises error."""
        _c = ql.circuit()
        with pytest.raises(ValueError, match="homogeneous"):
            ql.array([qint(1), qbool(True)])


class TestQarrayPythonIntegration:
    """Test PYI-01 through PYI-04: Python integration."""

    def test_len_flattened(self):
        """PYI-01: len() returns flattened length."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]])
        assert len(arr) == 4

    def test_iteration(self):
        """PYI-02: Iteration over flattened elements."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        elements = list(arr)
        assert len(elements) == 3
        assert all(isinstance(e, qint) for e in elements)

    def test_single_index(self):
        """PYI-03: Single element access."""
        _c = ql.circuit()
        arr = ql.array([10, 20, 30])
        # Access elements and verify they are qint objects
        elem0 = arr[0]
        elem1 = arr[1]
        elem_last = arr[-1]
        assert isinstance(elem0, qint)
        assert isinstance(elem1, qint)
        assert isinstance(elem_last, qint)

    def test_multidimensional_index(self):
        """PYI-03: Multi-dimensional indexing."""
        _c = ql.circuit()
        arr = ql.array([[1, 2, 3], [4, 5, 6]])
        # Access elements and verify they are qint objects
        elem00 = arr[0, 0]
        elem01 = arr[0, 1]
        elem12 = arr[1, 2]
        assert isinstance(elem00, qint)
        assert isinstance(elem01, qint)
        assert isinstance(elem12, qint)

    def test_row_access(self):
        """PYI-03: Row access returns view."""
        _c = ql.circuit()
        arr = ql.array([[1, 2, 3], [4, 5, 6]])
        row = arr[0]
        assert isinstance(row, qarray)
        assert len(row) == 3

    def test_column_slice(self):
        """PYI-03: Column access A[:, j]."""
        _c = ql.circuit()
        arr = ql.array([[1, 2, 3], [4, 5, 6]])
        col = arr[:, 1]
        assert isinstance(col, qarray)
        assert len(col) == 2

    def test_slicing(self):
        """PYI-04: Slicing returns view."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3, 4, 5])
        sliced = arr[1:4]
        assert isinstance(sliced, qarray)
        assert len(sliced) == 3


class TestQarrayImmutability:
    """Test immutability enforcement."""

    def test_setitem_works(self):
        """setitem supports element assignment for augmented assignment patterns."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        arr[0] = ql.qint(5, width=8)
        # Verify assignment did not raise

    def test_setitem_out_of_bounds(self):
        """setitem raises IndexError for out-of-bounds index."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        with pytest.raises(IndexError):
            arr[5] = ql.qint(5, width=8)

    def test_delitem_raises(self):
        """Arrays are immutable - delitem raises TypeError."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        with pytest.raises(TypeError, match="does not support item deletion"):
            del arr[0]


class TestQarrayRepr:
    """Test repr formatting."""

    def test_repr_format(self):
        """Repr shows ql.array<dtype:width, shape=...>[...]."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        r = repr(arr)
        assert "ql.array" in r
        assert "qint:8" in r
        assert "shape=(3,)" in r

    def test_repr_multidimensional(self):
        """Multi-dimensional uses nested brackets."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]])
        r = repr(arr)
        assert "shape=(2, 2)" in r
        assert "[[" in r or "], [" in r  # Nested structure

    def test_repr_truncation(self):
        """Large arrays truncate with ellipsis."""
        _c = ql.circuit()
        arr = ql.array(list(range(100)))
        r = repr(arr)
        assert "..." in r
        assert "shape=(100,)" in r


class TestQarrayViewSemantics:
    """Test view semantics for slicing."""

    def test_slice_shares_elements(self):
        """Sliced array shares qint objects with original."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        sliced = arr[1:3]
        # Same qint objects (reference equality)
        assert sliced[0] is arr[1]
        assert sliced[1] is arr[2]
