"""Grover diffusion operator using X-MCZ-X pattern.

Provides ql.diffusion() convenience wrapper that applies the S_0 reflection
(phase flip on |0...0> state) using zero ancilla and O(n) gates.

Usage
-----
>>> import quantum_language as ql
>>> ql.circuit()
>>> x = ql.qint(0, width=3)
>>> x.branch()  # Equal superposition
>>> ql.diffusion(x)  # S_0 reflection
"""

from ._gates import emit_mcz, emit_x, emit_z
from .compile import compile as ql_compile
from .qarray import qarray
from .qint import qint


def _collect_qubits(*registers):
    """Collect qubit indices from quantum registers.

    Iterates over each register argument and extracts physical qubit
    indices. Supports qint, qbool, and qarray (flattened).

    Parameters
    ----------
    *registers : qint, qbool, or qarray
        Quantum registers to extract qubits from.

    Returns
    -------
    list[int]
        Flat list of physical qubit indices.
    """
    qubits = []
    for reg in registers:
        if isinstance(reg, qarray):
            for elem in reg:
                w = elem.width if hasattr(elem, "width") else elem.bits
                for i in range(w):
                    qubits.append(int(elem.qubits[64 - w + i]))
        elif isinstance(reg, qint):
            w = reg.width if hasattr(reg, "width") else reg.bits
            for i in range(w):
                qubits.append(int(reg.qubits[64 - w + i]))
        # Skip non-quantum args (defensive)
    return qubits


def _total_width(*args):
    """Compute total qubit width across all quantum arguments.

    Used as the cache key function for @ql.compile.

    Parameters
    ----------
    *args : qint, qbool, or qarray
        Quantum registers.

    Returns
    -------
    int
        Total number of qubits across all arguments.
    """
    total = 0
    for reg in args:
        if isinstance(reg, qarray):
            total += len(reg) * reg.width
        elif isinstance(reg, qint):
            total += reg.width if hasattr(reg, "width") else reg.bits
    return total


@ql_compile(key=_total_width)
def diffusion(*registers):
    """Apply Grover diffusion operator (X-MCZ-X pattern).

    Reflects amplitude about |0...0> state. Zero ancilla, O(n) gates.
    Works on qint, qbool, and qarray. Multiple registers are flattened.

    Parameters
    ----------
    *registers : qint, qbool, or qarray
        Quantum registers to apply diffusion to.

    Raises
    ------
    ValueError
        If no qubits provided (empty registers or zero-width).

    Examples
    --------
    >>> import quantum_language as ql
    >>> ql.circuit()
    >>> x = ql.qint(0, width=3)
    >>> x.branch()
    >>> ql.diffusion(x)
    """
    qubits = _collect_qubits(*registers)

    if not qubits:
        raise ValueError("diffusion() requires at least one qubit")

    # X on all qubits
    for q in qubits:
        emit_x(q)

    # MCZ: phase flip on |1...1> (which corresponds to |0...0> after X mapping)
    if len(qubits) == 1:
        emit_z(qubits[0])
    else:
        emit_mcz(qubits[-1], qubits[:-1])

    # X on all qubits (undo the mapping)
    for q in qubits:
        emit_x(q)
