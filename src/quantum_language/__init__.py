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
from quantum_language import state

# Import circuit and utilities from core
# Re-export state module-level functions for convenience
# (Users can also access via ql.state.X)
from quantum_language._core import (
    AVAILABLE_PASSES,
    circuit,
    circuit_stats,
    get_current_layer,
    option,
    reverse_instruction_range,
)
from quantum_language._core import array as _array_impl
from quantum_language.qbool import qbool
from quantum_language.qint import qint
from quantum_language.qint_mod import qint_mod


def array(dim, dtype=None):
    """Create array of quantum integers or booleans.

    Parameters
    ----------
    dim : int, tuple of int, or list of int
        Array dimensions:
        - int: 1D array of length dim
        - tuple (rows, cols): 2D array
        - list of int: 1D array with specified initial values
    dtype : type, optional
        Element type: qint or qbool (default qint).

    Returns
    -------
    list or list of list
        Array of quantum integers/booleans.

    Examples
    --------
    >>> arr = array(5)              # [qint(), qint(), qint(), qint(), qint()]
    >>> arr = array([1, 2, 3])      # [qint(1), qint(2), qint(3)]
    >>> arr = array((2, 3))         # 2x3 2D array
    >>> arr = array(3, dtype=qbool) # [qbool(), qbool(), qbool()]
    """
    if dtype is None:
        dtype = qint
    return _array_impl(dim, dtype)


# Explicit public API
__all__ = [
    # Types
    "qint",
    "qbool",
    "qint_mod",
    # Circuit
    "circuit",
    # Utilities
    "array",
    "option",
    # Constants
    "AVAILABLE_PASSES",
    # State (also in ql.state subpackage)
    "circuit_stats",
    "get_current_layer",
    "reverse_instruction_range",
    # Subpackage
    "state",
    # Metadata
    "__version__",
]
