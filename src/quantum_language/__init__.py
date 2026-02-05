"""Quantum programming language with natural syntax.

Import as: import quantum_language as ql

Basic Usage
-----------
>>> import quantum_language as ql
>>> c = ql.circuit()
>>> a = ql.qint(5, width=8)
>>> b = ql.qint(3, width=8)
>>> result = a + b

Types
-----
qint : Quantum integer (arbitrary width 1-64 bits)
qbool : Quantum boolean (1-bit qint)
qint_mod : Quantum integer with modular arithmetic

Utilities
---------
circuit : Create/manage quantum circuits
array : Create arrays of quantum integers
option : Get/set language options

State Management
----------------
Access via quantum_language.state subpackage:
>>> from quantum_language.state import circuit_stats
>>> ql.state.get_current_layer()
"""

__version__ = "0.1.0"

# Import types from Cython modules
# Import state subpackage (makes ql.state accessible)
# from .quantum_language import state

# Import circuit and utilities from core
# Re-export state module-level functions for convenience
# (Users can also access via ql.state.X)
from ._core import (
    AVAILABLE_PASSES,
    circuit,
    circuit_stats,
    get_current_layer,
    option,
    reverse_instruction_range,
)
from .compile import compile
from .openqasm import to_openqasm
from .qarray import qarray
from .qbool import qbool
from .qint import qint
from .qint_mod import qint_mod


def array(data=None, *, width=None, dtype=None, dim=None):
    """Create array of quantum integers or booleans.

    Parameters
    ----------
    data : list, numpy.ndarray, optional
        Values to initialize array with.
    width : int, optional
        Bit width for qint elements (default 8).
    dtype : type, optional
        Element type: qint or qbool (default qint).
    dim : int or tuple, optional
        Array dimensions for zero-initialized array.

    Returns
    -------
    qarray
        Quantum array object.

    Examples
    --------
    >>> arr = array([1, 2, 3])           # From values
    >>> arr = array([1, 2], width=16)    # Explicit width
    >>> arr = array([[1,2],[3,4]])       # 2D array
    >>> arr = array(dim=(3, 3))          # Zero-initialized 3x3
    >>> arr = array(dim=5, dtype=qbool)  # 5 qbools
    """
    if dtype is None:
        dtype = qint
    return qarray(data, width=width, dtype=dtype, dim=dim)


def all(arr):
    """AND-reduce a quantum array.

    Parameters
    ----------
    arr : qarray
        Array to reduce.

    Returns
    -------
    qint or qbool
        AND reduction of all elements.
    """
    return arr.all()


def any(arr):
    """OR-reduce a quantum array.

    Parameters
    ----------
    arr : qarray
        Array to reduce.

    Returns
    -------
    qint or qbool
        OR reduction of all elements.
    """
    return arr.any()


def parity(arr):
    """XOR-reduce a quantum array.

    Parameters
    ----------
    arr : qarray
        Array to reduce.

    Returns
    -------
    qint or qbool
        XOR reduction of all elements.
    """
    return arr.parity()


def draw_circuit(circuit, *, mode=None, save=None):
    """Visualize a quantum circuit as a pixel-art image.

    Parameters
    ----------
    circuit : circuit
        A built quantum circuit object.
    mode : str, optional
        Zoom mode: "overview" (compact), "detail" (readable labels),
        or None for auto-selection based on circuit size.
    save : str, optional
        If provided, save the image to this file path.

    Returns
    -------
    PIL.Image.Image
        Rendered circuit image.

    Raises
    ------
    ImportError
        If Pillow is not installed.
    """
    try:
        from .draw import draw_circuit as _draw_circuit
    except ImportError as err:
        raise ImportError(
            "Pillow is required for circuit visualization. Install with: pip install Pillow"
        ) from err
    return _draw_circuit(circuit, mode=mode, save=save)


# Explicit public API
__all__ = [
    # Types
    "qint",
    "qbool",
    "qint_mod",
    "qarray",
    # Circuit
    "circuit",
    # Utilities
    "compile",
    "array",
    "option",
    "draw_circuit",
    "all",
    "any",
    "parity",
    # Constants
    "AVAILABLE_PASSES",
    # Export
    "to_openqasm",
    # State (also in ql.state subpackage)
    "circuit_stats",
    "get_current_layer",
    "reverse_instruction_range",
    # Subpackage
    "state",
    # Metadata
    "__version__",
]
