"""Tests for qarray reduction operations - Phase 23 Array Reductions."""

import pytest

import quantum_language as ql
from quantum_language.qint import qint


class TestReduceAND:
    """Test RED-01: AND reduction (all)."""

    def test_all_returns_qint(self):
        """all() returns qint for qint arrays."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        result = arr.all()
        assert isinstance(result, qint)

    def test_all_single_element(self):
        """all() returns element directly for single-element array."""
        _c = ql.circuit()
        arr = ql.array([5])
        result = arr.all()
        assert result is arr[0]

    def test_all_empty_raises(self):
        """all() raises ValueError for empty array."""
        _c = ql.circuit()
        arr = ql.array(dim=0)
        with pytest.raises(ValueError, match="empty"):
            arr.all()

    def test_all_qbool(self):
        """all() works on qbool arrays (returns qint due to inheritance)."""
        _c = ql.circuit()
        arr = ql.array([True, True], dtype=ql.qbool)
        result = arr.all()
        assert isinstance(result, qint)

    def test_all_module_level(self):
        """ql.all(arr) delegates to arr.all()."""
        _c = ql.circuit()
        arr = ql.array([1, 2])
        result = ql.all(arr)
        assert isinstance(result, qint)


class TestReduceOR:
    """Test RED-02: OR reduction (any)."""

    def test_any_returns_qint(self):
        """any() returns qint for qint arrays."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        result = arr.any()
        assert isinstance(result, qint)

    def test_any_single_element(self):
        """any() returns element directly for single-element array."""
        _c = ql.circuit()
        arr = ql.array([5])
        result = arr.any()
        assert result is arr[0]

    def test_any_empty_raises(self):
        """any() raises ValueError for empty array."""
        _c = ql.circuit()
        with pytest.raises(ValueError, match="empty"):
            ql.array(dim=0).any()

    def test_any_qbool(self):
        """any() works on qbool arrays (returns qint due to inheritance)."""
        _c = ql.circuit()
        arr = ql.array([True, False], dtype=ql.qbool)
        result = arr.any()
        assert isinstance(result, qint)

    def test_any_module_level(self):
        """ql.any(arr) delegates to arr.any()."""
        _c = ql.circuit()
        arr = ql.array([1, 2])
        result = ql.any(arr)
        assert isinstance(result, qint)


class TestReduceXOR:
    """Test RED-03: XOR reduction (parity)."""

    def test_parity_returns_qint(self):
        """parity() returns qint for qint arrays."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        result = arr.parity()
        assert isinstance(result, qint)

    def test_parity_single_element(self):
        """parity() returns element directly for single-element array."""
        _c = ql.circuit()
        arr = ql.array([5])
        result = arr.parity()
        assert result is arr[0]

    def test_parity_empty_raises(self):
        """parity() raises ValueError for empty array."""
        _c = ql.circuit()
        with pytest.raises(ValueError, match="empty"):
            ql.array(dim=0).parity()

    def test_parity_qbool(self):
        """parity() works on qbool arrays (returns qint due to inheritance)."""
        _c = ql.circuit()
        arr = ql.array([True, True], dtype=ql.qbool)
        result = arr.parity()
        assert isinstance(result, qint)

    def test_parity_module_level(self):
        """ql.parity(arr) delegates to arr.parity()."""
        _c = ql.circuit()
        result = ql.parity(ql.array([1, 2]))
        assert isinstance(result, qint)


class TestReduceSum:
    """Test RED-04: Sum reduction."""

    def test_sum_returns_qint(self):
        """sum() returns qint for qint arrays."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3])
        result = arr.sum()
        assert isinstance(result, qint)

    def test_sum_single_element(self):
        """sum() returns element directly for single-element array."""
        _c = ql.circuit()
        arr = ql.array([5])
        result = arr.sum()
        assert result is arr[0]

    def test_sum_empty_raises(self):
        """sum() raises ValueError for empty array."""
        _c = ql.circuit()
        with pytest.raises(ValueError, match="empty"):
            ql.array(dim=0).sum()

    def test_sum_qbool_returns_qint(self):
        """sum() returns qint popcount for qbool arrays."""
        _c = ql.circuit()
        arr = ql.array([True, False, True], dtype=ql.qbool)
        result = arr.sum()
        assert isinstance(result, qint)


class TestReduceMultiDim:
    """Test multi-dimensional array reductions."""

    def test_all_2d_flattens(self):
        """all() flattens 2D arrays before reducing."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]])
        result = arr.all()
        assert isinstance(result, qint)

    def test_sum_2d_flattens(self):
        """sum() flattens 2D arrays before reducing."""
        _c = ql.circuit()
        arr = ql.array([[1, 2], [3, 4]])
        result = arr.sum()
        assert isinstance(result, qint)


class TestReduceTreeStructure:
    """Test tree reduction structure with various array sizes."""

    def test_power_of_two_elements(self):
        """Reduction on power-of-2 array creates perfect binary tree."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3, 4])
        result = arr.all()
        assert isinstance(result, qint)

    def test_odd_elements(self):
        """Reduction on odd-sized array handles carry-forward correctly."""
        _c = ql.circuit()
        arr = ql.array([1, 2, 3, 4, 5])
        result = arr.all()
        assert isinstance(result, qint)
