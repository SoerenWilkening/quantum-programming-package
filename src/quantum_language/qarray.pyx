"""
Quantum array implementation with NumPy-style indexing.

Provides immutable quantum arrays that store qint/qbool elements
in a flattened representation with shape metadata.
"""

from collections.abc import Sequence
import warnings
import numpy as np
from quantum_language.qint cimport qint
from quantum_language.qbool cimport qbool
from quantum_language._core cimport INTEGERSIZE


def _infer_width(values, default_width=8):
    """
    Infer the bit width needed to represent all values.

    Args:
        values: Iterable of integer values
        default_width: Width to use if all values are 0 or negative

    Returns:
        int: Minimum bit width, floored at INTEGERSIZE
    """
    if not values:
        return default_width

    max_val = max(abs(v) for v in values)
    if max_val == 0:
        return default_width

    width = max_val.bit_length()
    # Floor at INTEGERSIZE (typically 8)
    return max(width, INTEGERSIZE)


def _detect_shape(data):
    """
    Detect shape from nested list structure.

    Args:
        data: Nested list structure

    Returns:
        tuple: Shape tuple (e.g., (3, 4) for 2D array)

    Raises:
        ValueError: If array is jagged (inconsistent dimensions)
    """
    if not isinstance(data, list):
        return ()

    if len(data) == 0:
        return (0,)

    # Check if this is a list of scalars or nested lists
    if not isinstance(data[0], list):
        # Flat list
        return (len(data),)

    # Nested list - recursively detect shape
    first_shape = _detect_shape(data[0])

    # Verify all elements have the same shape
    for i, item in enumerate(data[1:], start=1):
        item_shape = _detect_shape(item)
        if item_shape != first_shape:
            raise ValueError(
                f"Jagged array detected: element 0 has shape {first_shape}, "
                f"but element {i} has shape {item_shape}"
            )

    return (len(data),) + first_shape


def _flatten(data):
    """
    Flatten nested list to 1D list.

    Args:
        data: Nested list structure

    Returns:
        list: Flattened 1D list
    """
    result = []

    def _flatten_recursive(item):
        if isinstance(item, list):
            for sub_item in item:
                _flatten_recursive(sub_item)
        else:
            result.append(item)

    _flatten_recursive(data)
    return result


cdef class qarray:
    """
    Immutable quantum array with NumPy-style indexing.

    Stores quantum integer (qint) or quantum boolean (qbool) elements
    in a flattened representation with shape metadata.

    Implements Sequence protocol for iteration and indexing.

    Attributes:
        _elements (list): Flattened list of qint/qbool objects
        _shape (tuple): Shape tuple describing array dimensions
        _dtype (type): Element type (qint or qbool)
        _width (int): Bit width for qint elements
    """

    def __init__(self, data):
        """
        Initialize quantum array from nested list structure.

        Args:
            data: List of integers (can be nested for multi-dimensional arrays)

        Raises:
            ValueError: If array structure is jagged
        """
        # Detect shape from nested structure
        self._shape = _detect_shape(data)

        # Flatten data to 1D list
        flat_data = _flatten(data)

        # Infer width from max value
        self._width = _infer_width(flat_data)

        # Create qint objects for each value
        self._elements = []
        for value in flat_data:
            q = qint(self._width)
            q.value = value
            self._elements.append(q)

        # Store dtype reference
        self._dtype = qint

    @property
    def shape(self):
        """Return the shape tuple of the array."""
        return self._shape

    @property
    def width(self):
        """Return the bit width of array elements."""
        return self._width

    @property
    def dtype(self):
        """Return the element type (qint or qbool)."""
        return self._dtype

    def __len__(self):
        """Return the number of elements in the flattened array."""
        return len(self._elements)

    def __getitem__(self, index):
        """
        Get element by index.

        Args:
            index: Integer index into flattened array

        Returns:
            qint or qbool: Element at specified index

        Note: Multi-dimensional indexing will be added in Plan 02
        """
        if isinstance(index, int):
            # Handle negative indices
            if index < 0:
                index = len(self._elements) + index

            if index < 0 or index >= len(self._elements):
                raise IndexError(f"Index {index} out of bounds for array of length {len(self._elements)}")

            return self._elements[index]
        else:
            raise TypeError(f"Unsupported index type: {type(index).__name__}")


# Register qarray as a virtual subclass of Sequence
# This enables isinstance(qarray_instance, Sequence) checks
Sequence.register(qarray)
