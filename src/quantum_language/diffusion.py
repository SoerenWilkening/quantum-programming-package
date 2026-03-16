"""Grover diffusion operator using DSL operations.

Provides ql.diffusion() convenience wrapper that applies the S_0 reflection
(phase flip on |0...0> state).  Uses ``~register`` for bit-flipping and
``qbool & chain`` + ``phase += pi`` for the multi-controlled phase flip,
avoiding raw ``emit_*`` calls.

Usage
-----
>>> import quantum_language as ql
>>> ql.circuit()
>>> x = ql.qint(0, width=3)
>>> x.branch()  # Equal superposition
>>> ql.diffusion(x)  # S_0 reflection
"""

import math

from ._core import _set_layer_floor, get_current_layer, option
from .compile import compile as ql_compile
from .qarray import qarray
from .qint import qint


def _qubit_index(q):
    """Return the physical qubit index for a single-qubit (qbool) register.

    Parameters
    ----------
    q : qbool
        A 1-bit quantum register.

    Returns
    -------
    int
        Physical qubit index.
    """
    return int(q.qubits[63])


def _register_indices(reg):
    """Return the physical qubit indices for a quantum register.

    Parameters
    ----------
    reg : qint
        Quantum register.

    Returns
    -------
    list[int]
        Physical qubit indices, MSB-first order.
    """
    w = reg.width if hasattr(reg, "width") else reg.bits
    return [int(reg.qubits[64 - w + i]) for i in range(w)]


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


def _flip_all(*registers):
    """Apply X gate to every qubit in the given registers.

    DSL-level helper that accepts qint, qbool, or qarray objects and
    applies ``~register`` (bitwise NOT) to each.  Handles controlled
    context automatically via the DSL ``__invert__`` implementation.

    Temporarily enables ``simulate`` mode so that the underlying
    ``run_instruction`` path stores gates in the circuit.

    Parameters
    ----------
    *registers : qint, qbool, or qarray
        Quantum registers whose qubits should be flipped.
    """
    was_simulating = option('simulate')
    if not was_simulating:
        option('simulate', True)
    try:
        for reg in registers:
            if isinstance(reg, qarray):
                for elem in reg:
                    ~elem
            elif isinstance(reg, qint):
                ~reg
    finally:
        if not was_simulating:
            option('simulate', False)


def _extract_qbools(*registers):
    """Extract individual qubits as qbool objects from registers.

    Parameters
    ----------
    *registers : qint, qbool, or qarray
        Quantum registers to extract qubits from.

    Returns
    -------
    list[qbool]
        Flat list of single-qubit qbool wrappers.
    """
    bits = []
    for reg in registers:
        if isinstance(reg, qarray):
            for elem in reg:
                for i in range(elem.width):
                    bits.append(elem[i])
        elif isinstance(reg, qint):
            for i in range(reg.width):
                bits.append(reg[i])
    return bits


def _nested_phase_flip(bits, target_register):
    """Apply phase flip controlled on all qubits in *bits* being |1>.

    Recursively nests ``with`` blocks so that the innermost level
    applies ``target_register.phase += pi``.  The ``with`` block
    ``__exit__`` automatically uncomputes AND-ancillas in the correct
    order, avoiding gate-reordering issues.

    Parameters
    ----------
    bits : list[qbool]
        Qubits that must all be |1> for the phase flip to apply.
    target_register : qint
        Register used for the ``phase += pi`` call.
    """
    def _recurse(idx):
        if idx == len(bits):
            target_register.phase += math.pi
        else:
            with bits[idx]:
                _recurse(idx + 1)

    _recurse(0)


@ql_compile(key=_total_width)
def _diffusion_impl(*registers):
    """Inner implementation of diffusion (compiled for gate caching)."""
    bits = _extract_qbools(*registers)

    if not bits:
        raise ValueError("diffusion() requires at least one qubit")

    # X on all qubits (map |0...0> to |1...1>)
    _flip_all(*registers)

    # Phase flip on |1...1> (which corresponds to |0...0> after X mapping)
    # Uses nested ``with`` blocks: each level adds a control qubit,
    # and the innermost block applies the phase flip.  The ``with``
    # block __exit__ handles AND-ancilla uncomputation in the correct
    # order automatically.
    _nested_phase_flip(bits, registers[0])

    # Prevent the optimizer from merging the second X gates with the
    # first (they are separated by the phase-flip block).
    _set_layer_floor(get_current_layer())

    # X on all qubits (undo the mapping)
    _flip_all(*registers)


def diffusion(*registers):
    """Apply Grover diffusion operator.

    Reflects amplitude about |0...0> state using DSL operations:
    ``~register`` for bit-flip and ``qbool & chain`` + ``phase += pi``
    for the multi-controlled phase flip.
    Works on qint, qbool, and qarray. Multiple registers are flattened.

    Enables ``simulate`` mode so that DSL operations produce gates in
    the circuit.  The inner implementation is ``@ql.compile``-cached so
    that repeated calls replay the captured gate sequence.

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
    was_simulating = option('simulate')
    if not was_simulating:
        option('simulate', True)
    try:
        _diffusion_impl(*registers)
    finally:
        if not was_simulating:
            option('simulate', False)
