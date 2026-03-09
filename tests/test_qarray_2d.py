"""Tests for 2D qarray construction, indexing, mutation, and view semantics.

Covers Phase 120 requirements:
  ARR-01: 2D qarray creation via ql.qarray(dim=(rows, cols), dtype=ql.qbool)
  ARR-02: 2D indexing (read, mutate), row-level augmented assignment fix,
          view identity, qint index error message
"""

import pytest

import quantum_language as ql
from quantum_language.qarray import qarray
from quantum_language.qbool import qbool
from quantum_language.qint import qint


class TestQarray2DConstruction:
    """ARR-01: 2D qarray construction via dim= and nested lists."""

    def test_dim_qbool_creates_2d_array(self):
        """ql.qarray(dim=(2,2), dtype=ql.qbool) creates a 4-element 2D qbool array."""
        _c = ql.circuit()
        arr = ql.qarray(dim=(2, 2), dtype=ql.qbool)
        assert arr.shape == (2, 2)
        assert len(arr) == 4
        assert arr.dtype == qbool
        assert arr.width == 1

    def test_dim_qbool_all_elements_are_qbool(self):
        """All elements of a dim-created qbool array are qbool instances."""
        _c = ql.circuit()
        arr = ql.qarray(dim=(2, 2), dtype=ql.qbool)
        for elem in arr:
            assert isinstance(elem, qbool)

    def test_nested_list_creates_2d_qint_array(self):
        """ql.qarray([[1,2],[3,4]]) creates a 2D qint array with correct shape."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]])
        assert arr.shape == (2, 2)
        assert len(arr) == 4
        assert arr.dtype == qint

    def test_dim_3x3_qint(self):
        """ql.qarray(dim=(3,3)) creates a 9-element 2D qint array."""
        _c = ql.circuit()
        arr = ql.qarray(dim=(3, 3))
        assert arr.shape == (3, 3)
        assert len(arr) == 9
        assert arr.dtype == qint


class TestQarray2DViewIdentity:
    """ARR-02: View identity -- arr[r, c] returns the same Python object each time."""

    def test_element_identity_on_repeated_access(self):
        """arr[r, c] returns the same Python object on repeated access (identity via `is`)."""
        _c = ql.circuit()
        arr = ql.qarray(dim=(2, 2), dtype=ql.qbool)
        elem1 = arr[0, 0]
        elem2 = arr[0, 0]
        assert elem1 is elem2

    def test_element_identity_across_different_positions(self):
        """Different positions return different objects."""
        _c = ql.circuit()
        arr = ql.qarray(dim=(2, 2), dtype=ql.qbool)
        assert arr[0, 0] is not arr[0, 1]
        assert arr[0, 0] is not arr[1, 0]

    def test_row_view_shares_identity_with_original(self):
        """arr[row_idx] on 2D returns a view; view elements share identity with original."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2, 3], [4, 5, 6]], width=8)
        row0 = arr[0]
        assert isinstance(row0, qarray)
        assert row0[0] is arr[0, 0]
        assert row0[1] is arr[0, 1]
        assert row0[2] is arr[0, 2]

    def test_row_slice_shares_identity(self):
        """arr[r, :] returns a view sharing identity with original elements."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        row_view = arr[0, :]
        assert isinstance(row_view, qarray)
        assert row_view[0] is arr[0, 0]
        assert row_view[1] is arr[0, 1]

    def test_column_slice_shares_identity(self):
        """arr[:, c] returns a view sharing identity with original elements."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        col_view = arr[:, 0]
        assert isinstance(col_view, qarray)
        assert col_view[0] is arr[0, 0]
        assert col_view[1] is arr[1, 0]


class TestQarray2DMutation:
    """ARR-02: In-place mutation of 2D qarray elements."""

    def test_qbool_ior_on_2d(self):
        """arr[r, c] |= ql.qbool(True) works without error on qbool 2D array."""
        _c = ql.circuit()
        arr = ql.qarray(dim=(2, 2), dtype=ql.qbool)
        flag = ql.qbool(True)
        arr[0, 1] |= flag
        # Should not raise; element should still be qbool
        assert isinstance(arr[0, 1], qbool)

    def test_qbool_iadd_on_2d(self):
        """arr[r, c] += 1 on qbool 2D array works."""
        _c = ql.circuit()
        arr = ql.qarray(dim=(2, 2), dtype=ql.qbool)
        arr[1, 0] += 1
        assert isinstance(arr[1, 0], qbool)

    def test_qint_iadd_per_element_on_2d(self):
        """arr[r, c] += 1 on qint 2D array works correctly."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        original_elem = arr[0, 1]
        arr[0, 1] += 10
        # Identity preserved for in-place ops
        assert arr[0, 1] is original_elem


class TestQarray2DRowAssignment:
    """ARR-02: Row-level augmented assignment on 2D arrays (THE BUG FIX)."""

    def test_row_iadd_does_not_raise(self):
        """arr[row_idx] += x on a 2D qint array does NOT raise NotImplementedError."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        # This should NOT raise NotImplementedError
        arr[0] += 1
        # Elements should still be accessible
        assert arr.shape == (2, 2)
        assert isinstance(arr[0, 0], qint)
        assert isinstance(arr[0, 1], qint)

    def test_row_isub_on_2d(self):
        """arr[row_idx] -= x on a 2D qint array works."""
        _c = ql.circuit()
        arr = ql.qarray([[10, 20], [30, 40]], width=8)
        arr[1] -= 5
        assert arr.shape == (2, 2)

    def test_row_assignment_preserves_other_rows(self):
        """Row-level augmented assignment does not affect other rows."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        row1_elem0 = arr[1, 0]
        row1_elem1 = arr[1, 1]
        arr[0] += 10
        # Row 1 elements should be the same Python objects
        assert arr[1, 0] is row1_elem0
        assert arr[1, 1] is row1_elem1

    def test_negative_row_index_on_2d(self):
        """Negative row index arr[-1] on 2D works correctly."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        last_row = arr[-1]
        assert isinstance(last_row, qarray)
        assert len(last_row) == 2
        # Verify it's the last row (shares identity with row 1)
        assert last_row[0] is arr[1, 0]
        assert last_row[1] is arr[1, 1]

    def test_negative_row_assignment_on_2d(self):
        """arr[-1] += x works via __setitem__ on 2D array."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        arr[-1] += 1
        assert arr.shape == (2, 2)

    def test_row_assignment_out_of_bounds_raises(self):
        """Out-of-bounds row index raises IndexError on 2D array."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        with pytest.raises(IndexError):
            arr[5] = ql.qarray([99, 99], width=8)


class TestQarray2DErrorMessages:
    """Error message improvements for 2D qarrays."""

    def test_qint_index_raises_typeerror(self):
        """arr[qint_var, 0] raises TypeError mentioning 'quantum indexing'."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        q_idx = ql.qint(0, width=4)
        with pytest.raises(TypeError, match="(?i)quantum indexing"):
            arr[q_idx, 0]

    def test_qint_index_not_notimplementederror(self):
        """arr[qint_var, 0] should NOT raise NotImplementedError with 'Complex slicing'."""
        _c = ql.circuit()
        arr = ql.qarray([[1, 2], [3, 4]], width=8)
        q_idx = ql.qint(0, width=4)
        with pytest.raises(TypeError):
            arr[q_idx, 0]
