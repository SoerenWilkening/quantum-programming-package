"""
Quantum array implementation with NumPy-style indexing.

Provides immutable quantum arrays that store qint/qbool elements
in a flattened representation with shape metadata.
"""

from collections.abc import Sequence
import warnings
import numpy as np
from .qint cimport qint
from .qbool cimport qbool
from ._core cimport INTEGERSIZE
from ._core import _get_qubit_saving_mode


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


def _reduce_tree(elements, op):
    """
    Reduce elements using pairwise tree algorithm.

    Args:
        elements: List of quantum elements (qint or qbool)
        op: Binary operator function (e.g., lambda a, b: a & b)

    Returns:
        Single element after tree reduction

    Note:
        Assumes elements list has >= 2 items.
        Circuit depth is O(log n).
    """
    current_level = list(elements)  # Copy to avoid mutation

    while len(current_level) > 1:
        next_level = []

        # Process pairs
        for i in range(0, len(current_level), 2):
            if i + 1 < len(current_level):
                # Pair available - apply operator
                result = op(current_level[i], current_level[i + 1])
                next_level.append(result)
            else:
                # Odd element - carry forward unpaired
                next_level.append(current_level[i])

        current_level = next_level

    return current_level[0]


def _reduce_linear(elements, op):
    """
    Reduce elements using linear chain algorithm.

    Args:
        elements: List of quantum elements (qint or qbool)
        op: Binary operator function (e.g., lambda a, b: a & b)

    Returns:
        Single element after linear reduction

    Note:
        Assumes elements list has >= 2 items.
        Circuit depth is O(n), but uses minimal qubits.
    """
    result = elements[0]

    for i in range(1, len(elements)):
        result = op(result, elements[i])

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

    # Tell NumPy to defer arithmetic to qarray's operators
    __array_ufunc__ = None

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
                self._elements = [qint(0, width=(width or INTEGERSIZE)) for _ in range(total)]
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
                    q = qint(value.value, width=self._width)
                    self._elements.append(q)
                else:
                    q = qint(value, width=self._width)
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

    def __iter__(self):
        """
        Iterate over flattened elements.

        Yields
        ------
        qint or qbool
            Each element in row-major order.

        Examples
        --------
        >>> arr = qarray([1, 2, 3])
        >>> for x in arr:
        ...     print(x)
        """
        return iter(self._elements)

    def __contains__(self, item):
        """
        Check if element in array.

        Args:
            item: Element to search for

        Returns:
            bool: True if item is in array
        """
        return item in self._elements

    def __setitem__(self, key, value):
        """
        Prevent mutation - arrays are immutable.

        Raises
        ------
        TypeError
            Always (arrays cannot be modified after creation).
        """
        raise TypeError("'qarray' object does not support item assignment")

    def __delitem__(self, key):
        """
        Prevent deletion - arrays are immutable.

        Raises
        ------
        TypeError
            Always (arrays cannot be deleted from).
        """
        raise TypeError("'qarray' object does not support item deletion")

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

    def __repr__(self):
        """
        Compact format: ql.array<qint:8, shape=(3,)>[1, 2, 3]

        Truncates large arrays with ellipsis (...) NumPy-style.

        Returns:
            str: Formatted representation
        """
        dtype_name = self._dtype.__name__  # "qint" or "qbool"

        # Format type info
        if dtype_name == "qint":
            type_info = f"<qint:{self._width}, shape={self._shape}>"
        else:
            type_info = f"<qbool, shape={self._shape}>"

        # Format elements
        if len(self._shape) == 1:
            elem_str = self._format_1d()
        else:
            elem_str = self._format_nested(self._elements, self._shape, 0)

        return f"ql.array{type_info}[{elem_str}]"

    def __str__(self):
        """String representation (same as __repr__)."""
        return self.__repr__()

    def _format_1d(self):
        """
        Format 1D array with truncation.

        Returns:
            str: Formatted element string
        """
        threshold = 6  # Show first 3 and last 3 if > threshold

        if len(self._elements) <= threshold:
            return ", ".join(self._get_element_str(e) for e in self._elements)
        else:
            first = ", ".join(self._get_element_str(e) for e in self._elements[:3])
            last = ", ".join(self._get_element_str(e) for e in self._elements[-3:])
            return f"{first}, ..., {last}"

    def _format_nested(self, elements, shape, depth):
        """
        Format multi-dimensional array with nested brackets.

        Args:
            elements: List of elements to format
            shape: Shape tuple for this level
            depth: Current nesting depth

        Returns:
            str: Formatted nested string
        """
        if len(shape) == 1:
            # Base case: format this dimension
            if len(elements) <= 6:
                return ", ".join(self._get_element_str(e) for e in elements)
            else:
                first = ", ".join(self._get_element_str(e) for e in elements[:3])
                last = ", ".join(self._get_element_str(e) for e in elements[-3:])
                return f"{first}, ..., {last}"

        # Recursive case
        stride = 1
        for s in shape[1:]:
            stride *= s

        chunks = []
        num_chunks = len(elements) // stride

        # Apply truncation if too many chunks
        if num_chunks > 6:
            # Show first 3 and last 3 chunks
            for i in range(3):
                start = i * stride
                chunk = elements[start:start+stride]
                chunks.append("[" + self._format_nested(chunk, shape[1:], depth+1) + "]")
            chunks.append("...")
            for i in range(num_chunks - 3, num_chunks):
                start = i * stride
                chunk = elements[start:start+stride]
                chunks.append("[" + self._format_nested(chunk, shape[1:], depth+1) + "]")
        else:
            # Show all chunks
            for i in range(0, len(elements), stride):
                chunk = elements[i:i+stride]
                chunks.append("[" + self._format_nested(chunk, shape[1:], depth+1) + "]")

        return ", ".join(chunks)

    def _get_element_str(self, elem):
        """
        Get string representation of an element.

        Args:
            elem: qint or qbool element

        Returns:
            str: String representation of element's value
        """
        # Cast to appropriate type and access cdef value attribute
        if isinstance(elem, qint):
            return str((<qint>elem).value)
        elif isinstance(elem, qbool):
            return str((<qbool>elem).value)
        else:
            return str(elem)

    def all(self):
        """
        Reduce array with AND. Returns single element (bitwise AND for qint, logical AND for qbool).

        Returns:
            qint or qbool: Result of AND reduction across all elements

        Raises:
            ValueError: If array is empty

        Examples:
            >>> arr = qarray([1, 2, 3])
            >>> result = arr.all()  # 1 & 2 & 3
        """
        if len(self._elements) == 0:
            raise ValueError("cannot reduce empty array")

        if len(self._elements) == 1:
            return self._elements[0]

        elems = list(self._elements)  # Copy to avoid mutation

        if _get_qubit_saving_mode():
            return _reduce_linear(elems, lambda a, b: a & b)
        else:
            return _reduce_tree(elems, lambda a, b: a & b)

    def any(self):
        """
        Reduce array with OR. Returns single element (bitwise OR for qint, logical OR for qbool).

        Returns:
            qint or qbool: Result of OR reduction across all elements

        Raises:
            ValueError: If array is empty

        Examples:
            >>> arr = qarray([1, 2, 3])
            >>> result = arr.any()  # 1 | 2 | 3
        """
        if len(self._elements) == 0:
            raise ValueError("cannot reduce empty array")

        if len(self._elements) == 1:
            return self._elements[0]

        elems = list(self._elements)  # Copy to avoid mutation

        if _get_qubit_saving_mode():
            return _reduce_linear(elems, lambda a, b: a | b)
        else:
            return _reduce_tree(elems, lambda a, b: a | b)

    def parity(self):
        """
        Reduce array with XOR. Returns single element (bitwise XOR for qint, logical XOR for qbool).

        Returns:
            qint or qbool: Result of XOR reduction across all elements

        Raises:
            ValueError: If array is empty

        Examples:
            >>> arr = qarray([1, 2, 3])
            >>> result = arr.parity()  # 1 ^ 2 ^ 3
        """
        if len(self._elements) == 0:
            raise ValueError("cannot reduce empty array")

        if len(self._elements) == 1:
            return self._elements[0]

        elems = list(self._elements)  # Copy to avoid mutation

        if _get_qubit_saving_mode():
            return _reduce_linear(elems, lambda a, b: a ^ b)
        else:
            return _reduce_tree(elems, lambda a, b: a ^ b)

    def sum(self, *, width=None):
        """
        Sum all elements. Returns qint. For qbool arrays, returns popcount. Use width= to override result width.

        Parameters:
            width: Optional bit width for result (overrides default)

        Returns:
            qint or qbool: Sum of all elements

        Raises:
            ValueError: If array is empty

        Examples:
            >>> arr = qarray([1, 2, 3])
            >>> result = arr.sum()  # 1 + 2 + 3
            >>> arr = qarray([True, True, False], dtype=qbool)
            >>> popcount = arr.sum()  # Count of True values
        """
        if len(self._elements) == 0:
            raise ValueError("cannot reduce empty array")

        if len(self._elements) == 1:
            return self._elements[0]

        elems = list(self._elements)  # Copy to avoid mutation
        op = lambda a, b: a + b

        if _get_qubit_saving_mode():
            result = _reduce_linear(elems, op)
        else:
            result = _reduce_tree(elems, op)

        return result

    # ============ Helper Methods for Operators ============

    def _validate_shape(self, other):
        """Validate that shapes match for element-wise operations."""
        if self._shape != other.shape:
            raise ValueError(
                f"Shape mismatch for element-wise operation: cannot operate on arrays with shapes {self._shape} and {other.shape}"
            )

    def _coerce_sequence(self, other):
        """
        Coerce a list or numpy array to flat integer values with shape validation.

        Args:
            other: list or np.ndarray

        Returns:
            list: Flattened list of integer values

        Raises:
            ValueError: If shape doesn't match self._shape
        """
        if isinstance(other, np.ndarray):
            other = other.tolist()

        shape = _detect_shape(other)
        if shape != self._shape:
            raise ValueError(
                f"Shape mismatch for element-wise operation: cannot operate on arrays with shapes {self._shape} and {shape}"
            )
        return _flatten(other)

    def _elementwise_binary_op(self, other, op_func, result_dtype=None):
        """
        Generic element-wise binary operation.

        Args:
            other: int, qint, qarray, list, or np.ndarray
            op_func: Binary operation function (e.g., lambda a, b: a + b)
            result_dtype: Optional dtype for result (e.g., qbool for comparisons)

        Returns:
            qarray: Result of element-wise operation
        """
        cdef qarray other_arr
        cdef qarray result

        # Scalar broadcast
        if type(other) == int or isinstance(other, qint):
            result_elements = [op_func(elem, other) for elem in self._elements]
            result = self._create_view(result_elements, self._shape)
            if result_dtype is not None:
                result._dtype = result_dtype
                result._width = 1
            return result

        # Array-array operation
        elif isinstance(other, qarray):
            self._validate_shape(other)
            other_arr = <qarray>other
            result_elements = [op_func(self._elements[i], other_arr._elements[i]) for i in range(len(self._elements))]
            result = self._create_view(result_elements, self._shape)
            if result_dtype is not None:
                result._dtype = result_dtype
                result._width = 1
            return result

        # List or numpy array - element-wise with classical values
        elif isinstance(other, (list, np.ndarray)):
            flat_values = self._coerce_sequence(other)
            result_elements = [op_func(self._elements[i], flat_values[i]) for i in range(len(self._elements))]
            result = self._create_view(result_elements, self._shape)
            if result_dtype is not None:
                result._dtype = result_dtype
                result._width = 1
            return result

        else:
            return NotImplemented

    def _inplace_binary_op(self, other, iop_name):
        """
        Generic in-place binary operation.

        Args:
            other: int, qint, qarray, list, or np.ndarray
            iop_name: Name of in-place operation (e.g., "__iadd__")

        Returns:
            self: Modified array
        """
        cdef qarray other_arr

        # Scalar broadcast (int passed directly - qint operators handle int natively via CQ_*)
        if type(other) == int or isinstance(other, qint):
            for i in range(len(self._elements)):
                self._elements[i] = getattr(self._elements[i], iop_name)(other)
            return self

        # Array-array operation
        elif isinstance(other, qarray):
            self._validate_shape(other)
            other_arr = <qarray>other
            for i in range(len(self._elements)):
                self._elements[i] = getattr(self._elements[i], iop_name)(other_arr._elements[i])
            return self

        # List or numpy array - element-wise with classical values
        # (values passed directly - qint operators handle int natively via CQ_*)
        elif isinstance(other, (list, np.ndarray)):
            flat_values = self._coerce_sequence(other)
            for i in range(len(self._elements)):
                self._elements[i] = getattr(self._elements[i], iop_name)(flat_values[i])
            return self

        else:
            return NotImplemented

    # ============ Arithmetic Operators ============

    def __add__(self, other):
        """Element-wise addition."""
        return self._elementwise_binary_op(other, lambda a, b: a + b)

    def __radd__(self, other):
        """Element-wise addition (reversed)."""
        return self._elementwise_binary_op(other, lambda a, b: a + b)

    def __iadd__(self, other):
        """In-place element-wise addition."""
        return self._inplace_binary_op(other, "__iadd__")

    def __sub__(self, other):
        """Element-wise subtraction."""
        return self._elementwise_binary_op(other, lambda a, b: a - b)

    def __rsub__(self, other):
        """Element-wise subtraction (reversed)."""
        # NOT commutative: other - self
        if isinstance(other, (int, qint)):
            if isinstance(other, int):
                other = qint(other, width=self._width)
            result_elements = [other - elem for elem in self._elements]
            return self._create_view(result_elements, self._shape)
        elif isinstance(other, (list, np.ndarray)):
            flat_values = self._coerce_sequence(other)
            result_elements = []
            for i in range(len(self._elements)):
                v = flat_values[i]
                if type(v) == int:
                    v = qint(v, width=self._width)
                result_elements.append(v - self._elements[i])
            return self._create_view(result_elements, self._shape)
        return NotImplemented

    def __isub__(self, other):
        """In-place element-wise subtraction."""
        return self._inplace_binary_op(other, "__isub__")

    def __mul__(self, other):
        """Element-wise multiplication."""
        return self._elementwise_binary_op(other, lambda a, b: a * b)

    def __rmul__(self, other):
        """Element-wise multiplication (reversed)."""
        return self._elementwise_binary_op(other, lambda a, b: a * b)

    def __imul__(self, other):
        """In-place element-wise multiplication."""
        return self._inplace_binary_op(other, "__imul__")

    # ============ Bitwise Operators ============

    def __and__(self, other):
        """Element-wise bitwise AND."""
        return self._elementwise_binary_op(other, lambda a, b: a & b)

    def __rand__(self, other):
        """Element-wise bitwise AND (reversed)."""
        return self._elementwise_binary_op(other, lambda a, b: a & b)

    def __iand__(self, other):
        """In-place element-wise bitwise AND."""
        return self._inplace_binary_op(other, "__iand__")

    def __or__(self, other):
        """Element-wise bitwise OR."""
        return self._elementwise_binary_op(other, lambda a, b: a | b)

    def __ror__(self, other):
        """Element-wise bitwise OR (reversed)."""
        return self._elementwise_binary_op(other, lambda a, b: a | b)

    def __ior__(self, other):
        """In-place element-wise bitwise OR."""
        return self._inplace_binary_op(other, "__ior__")

    def __xor__(self, other):
        """Element-wise bitwise XOR."""
        return self._elementwise_binary_op(other, lambda a, b: a ^ b)

    def __rxor__(self, other):
        """Element-wise bitwise XOR (reversed)."""
        return self._elementwise_binary_op(other, lambda a, b: a ^ b)

    def __ixor__(self, other):
        """In-place element-wise bitwise XOR."""
        return self._inplace_binary_op(other, "__ixor__")

    # ============ Comparison Operators ============

    def __lt__(self, other):
        """Element-wise less than comparison."""
        return self._elementwise_binary_op(other, lambda a, b: a < b, result_dtype=qbool)

    def __le__(self, other):
        """Element-wise less than or equal comparison."""
        return self._elementwise_binary_op(other, lambda a, b: a <= b, result_dtype=qbool)

    def __gt__(self, other):
        """Element-wise greater than comparison."""
        return self._elementwise_binary_op(other, lambda a, b: a > b, result_dtype=qbool)

    def __ge__(self, other):
        """Element-wise greater than or equal comparison."""
        return self._elementwise_binary_op(other, lambda a, b: a >= b, result_dtype=qbool)

    def __eq__(self, other):
        """Element-wise equality comparison."""
        return self._elementwise_binary_op(other, lambda a, b: a == b, result_dtype=qbool)

    def __ne__(self, other):
        """Element-wise inequality comparison."""
        return self._elementwise_binary_op(other, lambda a, b: a != b, result_dtype=qbool)

    @staticmethod
    def _create_view(elements, shape):
        """
        Create a view array sharing element references.

        Args:
            elements: List of qint/qbool objects to include in view
            shape: Shape tuple for the view

        Returns:
            qarray: View sharing underlying qint/qbool objects
        """
        # Create new instance by calling __new__ directly
        cdef qarray arr = qarray.__new__(qarray)

        # Manually initialize the cdef attributes
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
