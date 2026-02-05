"""
Pure-Python helper functions for qarray.

Extracted from qarray.pyx to separate concerns. These functions contain
no Cython types (cdef/cimport) and can live in a standard .py module.
"""

# INTEGERSIZE is declared as `cdef int` in _core.pxd, making it C-level only.
# Mirror the value here for pure-Python usage. Must stay in sync with _core.pyx.
INTEGERSIZE = 8


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
