"""OpenQASM export functionality for quantum circuits."""

from libc.stdlib cimport free
from .openqasm cimport circuit_t, circuit_to_qasm_string
from ._core import _get_circuit, _get_circuit_initialized


def to_openqasm():
    """Export current circuit to OpenQASM 3.0 string.

    Returns
    -------
    str
        Valid OpenQASM 3.0 representation of the circuit.

    Raises
    ------
    RuntimeError
        If no circuit is initialized or export fails.

    Examples
    --------
    >>> import quantum_language as ql
    >>> c = ql.circuit()
    >>> a = ql.qint(5, width=4)
    >>> b = ql.qint(3, width=4)
    >>> result = a + b
    >>> qasm = ql.to_openqasm()
    >>> print(qasm)
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[12] q;
    bit[12] c;
    ...
    """
    # Check if circuit is initialized
    if not _get_circuit_initialized():
        raise RuntimeError("No circuit initialized")

    # Get circuit pointer (cast from Python int to C pointer)
    cdef circuit_t* circ = <circuit_t*><unsigned long long>_get_circuit()
    cdef char* c_str = NULL

    try:
        # Call C function to generate OpenQASM string
        c_str = circuit_to_qasm_string(circ)

        # Check for NULL return (indicates failure)
        if c_str == NULL:
            raise RuntimeError("Failed to export circuit to OpenQASM")

        # Convert C string to Python string
        return c_str.decode('utf-8')

    finally:
        # Always free the C string to prevent memory leak
        if c_str != NULL:
            free(c_str)
