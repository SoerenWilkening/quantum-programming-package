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

    def __init__(self, data=None, *, width=None, dtype=None, dim=None):
        """
        Initialize quantum array from nested list structure.

        Args:
            data: List of integers (can be nested for multi-dimensional arrays)
            width: Explicit bit width for elements (overrides auto-inference)
            dtype: Element type (qint or qbool)
            dim: Create array from dimensions (int or tuple)

        Raises:
            ValueError: If array structure is jagged or contains mixed types
            TypeError: If dtype is not qint or qbool
        """
        # Handle dimension-based construction first
        if dim is not None:
            if data is not None:
                raise ValueError("Cannot specify both data and dim")
            if dtype is None:
                dtype = qint  # Default to qint

            # Handle int or tuple
            if isinstance(dim, int):
                shape = (dim,)
            else:
                shape = tuple(dim)

            # Calculate total elements
            total = 1
            for d in shape:
                total *= d

            # Create elements (default value 0)
            if dtype == qbool:
                self._elements = [qbool() for _ in range(total)]
                self._width = 1
            else:
                self._elements = [qint(width or INTEGERSIZE) for _ in range(total)]
                self._width = width or INTEGERSIZE

            self._shape = shape
            self._dtype = dtype
            return  # Skip normal data processing

        # Handle NumPy array input
        if isinstance(data, np.ndarray):
            # Use NumPy dtype to determine width
            if width is None:
                width = data.dtype.itemsize * 8  # bytes to bits
            # Convert to nested Python list for shape detection
            data = data.tolist()

        # Validate dtype parameter if provided
        if dtype is not None and dtype not in (qint, qbool):
            raise TypeError(f"dtype must be qint or qbool, got {dtype}")

        # Detect shape from nested structure
        self._shape = _detect_shape(data)

        # Flatten data to 1D list
        flat_data = _flatten(data)

        # Check for mixed qint/qbool objects
        has_qint = any(isinstance(v, qint) for v in flat_data)
        has_qbool = any(isinstance(v, qbool) for v in flat_data)
        if has_qint and has_qbool:
            raise ValueError("Array must be homogeneous: cannot mix qint and qbool")

        # Determine dtype from data if not explicitly provided
        if dtype is None:
            if has_qbool:
                dtype = qbool
            elif has_qint:
                dtype = qint
            else:
                dtype = qint  # Default to qint for raw integer data

        # For qbool arrays, width is always 1
        if dtype == qbool:
            self._width = 1
            # Create qbool objects for each value
            self._elements = []
            for value in flat_data:
                if isinstance(value, qbool):
                    self._elements.append(value)
                else:
                    # Convert to bool then to qbool
                    self._elements.append(qbool(bool(value)))
        else:
            # qint array
            # Determine width
            if width is not None:
                # Explicit width provided - check if values fit
                numeric_values = []
                for v in flat_data:
                    if isinstance(v, qint):
                        numeric_values.append(v.value)
                    else:
                        numeric_values.append(v)

                if numeric_values:
                    max_val = max(abs(v) for v in numeric_values)
                    if max_val > 0 and max_val.bit_length() > width:
                        warnings.warn(
                            f"Values exceed {width}-bit range, will be truncated",
                            UserWarning
                        )
                self._width = width
            else:
                # Infer width from max value
                numeric_values = []
                for v in flat_data:
                    if isinstance(v, qint):
                        numeric_values.append(v.value)
                    else:
                        numeric_values.append(v)
                self._width = _infer_width(numeric_values)

            # Create qint objects for each value
            self._elements = []
            for value in flat_data:
                if isinstance(value, qint):
                    # Use existing qint but ensure correct width
                    q = qint(self._width)
                    q.value = value.value
                    self._elements.append(q)
                else:
                    q = qint(self._width)
                    q.value = value
                    self._elements.append(q)

        # Store dtype reference
        self._dtype = dtype

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

    def __getitem__(self, key):
        """
        Get element or slice by index with NumPy-style indexing.

        Supports:
        - Integer index: arr[5] returns single element
        - Negative index: arr[-1] returns last element
        - Slice: arr[1:3] returns view
        - Tuple (multi-dimensional): arr[0,1] or arr[:, 0]

        Args:
            key: int, slice, or tuple of ints/slices

        Returns:
            qint/qbool or qarray: Single element or view

        Raises:
            IndexError: If index out of bounds
            TypeError: If key type is unsupported
        """
        # Single integer index
        if isinstance(key, int):
            # For multi-dimensional arrays, treat single index as selecting from first dimension
            if len(self._shape) > 1:
                # arr[0] on 2D array returns first row
                # Convert to tuple indexing: arr[0] -> arr[0, :]
                return self._handle_multi_index((key, slice(None)))
            else:
                # 1D array - direct element access
                if key < 0:
                    key += len(self._elements)
                if not 0 <= key < len(self._elements):
                    raise IndexError(f"Index {key} out of bounds for array with {len(self._elements)} elements")
                return self._elements[key]

        # Slice (returns view)
        elif isinstance(key, slice):
            start, stop, step = key.indices(len(self._elements))
            indices = range(start, stop, step)
            view_elements = [self._elements[i] for i in indices]
            return self._create_view(view_elements, shape=(len(view_elements),))

        # Tuple (multi-dimensional indexing)
        elif isinstance(key, tuple):
            return self._handle_multi_index(key)

        else:
            raise TypeError(f"Unsupported index type: {type(key).__name__}")

    def _multi_to_flat(self, indices):
        """
        Convert multi-dimensional indices to flat index for row-major storage.

        Args:
            indices: Tuple of integer indices

        Returns:
            int: Flat index

        Example:
            shape (2, 3), index (1, 2) -> 1*3 + 2 = 5
        """
        if len(indices) != len(self._shape):
            raise IndexError(f"Expected {len(self._shape)} indices, got {len(indices)}")

        flat = 0
        stride = 1

        # Process dimensions in reverse (rightmost first for row-major)
        for dim in reversed(range(len(self._shape))):
            idx = indices[dim]

            # Handle negative indices
            if idx < 0:
                idx += self._shape[dim]

            # Bounds check
            if not 0 <= idx < self._shape[dim]:
                raise IndexError(f"Index {idx} out of bounds for dimension {dim} with size {self._shape[dim]}")

            flat += idx * stride
            stride *= self._shape[dim]

        return flat

    def _handle_multi_index(self, key):
        """
        Handle tuple-based multi-dimensional indexing.

        Supports:
        - All ints: arr[0, 1] returns single element
        - Mixed int/slice: arr[0, :] returns row view
        - Column slice: arr[:, 0] returns column view

        Args:
            key: Tuple of ints and/or slices

        Returns:
            qint/qbool or qarray: Single element or view
        """
        # Check if all elements are integers (single element access)
        if all(isinstance(k, int) for k in key):
            flat_idx = self._multi_to_flat(key)
            return self._elements[flat_idx]

        # Handle mixed int/slice indexing
        # This is complex - need to handle cases like arr[0, :] or arr[:, 0]

        # For now, handle the common case: arr[:, col_idx]
        if len(key) == 2 and isinstance(key[0], slice) and isinstance(key[1], int):
            # Column slice: arr[:, col_idx]
            row_slice = key[0]
            col_idx = key[1]

            # Handle negative column index
            if col_idx < 0:
                col_idx += self._shape[1]
            if not 0 <= col_idx < self._shape[1]:
                raise IndexError(f"Column index {col_idx} out of bounds")

            # Get row range
            start, stop, step = row_slice.indices(self._shape[0])
            row_indices = range(start, stop, step)

            # Collect elements from column
            view_elements = []
            for row_idx in row_indices:
                flat_idx = self._multi_to_flat((row_idx, col_idx))
                view_elements.append(self._elements[flat_idx])

            return self._create_view(view_elements, shape=(len(view_elements),))

        # Handle row slice: arr[row_idx, :]
        elif len(key) == 2 and isinstance(key[0], int) and isinstance(key[1], slice):
            row_idx = key[0]
            col_slice = key[1]

            # Handle negative row index
            if row_idx < 0:
                row_idx += self._shape[0]
            if not 0 <= row_idx < self._shape[0]:
                raise IndexError(f"Row index {row_idx} out of bounds")

            # Get column range
            start, stop, step = col_slice.indices(self._shape[1])
            col_indices = range(start, stop, step)

            # Collect elements from row
            view_elements = []
            for col_idx in col_indices:
                flat_idx = self._multi_to_flat((row_idx, col_idx))
                view_elements.append(self._elements[flat_idx])

            return self._create_view(view_elements, shape=(len(view_elements),))

        # Handle simple 1D slice of first dimension: arr[row_slice]
        elif len(key) == 1 and isinstance(key[0], slice):
            # This is just regular slicing
            return self.__getitem__(key[0])

        else:
            raise NotImplementedError(f"Complex slicing pattern not yet supported: {key}")

    @classmethod
    def _create_view(cls, elements, shape):
        """
        Create a view array sharing element references.

        Args:
            elements: List of qint/qbool objects to include in view
            shape: Shape tuple for the view

        Returns:
            qarray: View sharing underlying qint/qbool objects
        """
        # Create new instance without calling __init__
        arr = cls.__new__(cls)
        arr._elements = elements  # Shared reference (view semantics)
        arr._shape = shape

        # Infer dtype and width from elements
        if elements:
            first = elements[0]
            arr._dtype = type(first)
            if hasattr(first, 'bits'):
                arr._width = first.bits
            else:
                arr._width = 1  # qbool
        else:
            # Empty view
            arr._dtype = qint
            arr._width = 8

        return arr


# Register qarray as a virtual subclass of Sequence
# This enables isinstance(qarray_instance, Sequence) checks
Sequence.register(qarray)
