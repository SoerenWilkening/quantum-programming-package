"""Thin simulation backend wrapper.

Abstracts the simulation backend (currently qiskit + qiskit-aer) behind a
generic interface.  Provides lazy import guards that produce a friendly
error message when the backend is not installed, and future-proofs for
potential backend swaps.

Usage from within quantum_language::

    from .sim_backend import load_qasm, simulate

    circuit = load_qasm(qasm_str)
    counts = simulate(circuit, shots=1)
"""

_QISKIT_AVAILABLE = None
_AER_AVAILABLE = None

_INSTALL_MSG = (
    "Simulation backend required. Install with: pip install quantum_language[verification]"
)


def _check_qiskit():
    """Check if qiskit is importable (cached)."""
    global _QISKIT_AVAILABLE
    if _QISKIT_AVAILABLE is None:
        try:
            import qiskit  # noqa: F401

            _QISKIT_AVAILABLE = True
        except ImportError:
            _QISKIT_AVAILABLE = False
    return _QISKIT_AVAILABLE


def _check_aer():
    """Check if qiskit-aer is importable (cached)."""
    global _AER_AVAILABLE
    if _AER_AVAILABLE is None:
        try:
            import qiskit_aer  # noqa: F401

            _AER_AVAILABLE = True
        except ImportError:
            _AER_AVAILABLE = False
    return _AER_AVAILABLE


def _require_backend():
    """Raise friendly error if the core backend (qiskit) is not available."""
    if not _check_qiskit():
        raise ImportError(_INSTALL_MSG)


def _require_simulator():
    """Raise friendly error if the simulator (qiskit-aer) is not available.

    Checks for the core backend first, then the simulator extension.
    """
    _require_backend()
    if not _check_aer():
        raise ImportError(_INSTALL_MSG)


def load_qasm(qasm_str):
    """Load an OpenQASM 3.0 string into a circuit object.

    Parameters
    ----------
    qasm_str : str
        OpenQASM 3.0 circuit string.

    Returns
    -------
    QuantumCircuit
        Parsed circuit object.
    """
    _require_backend()
    import qiskit.qasm3

    return qiskit.qasm3.loads(qasm_str)


def simulate(circuit, *, shots=1, max_parallel_threads=4):
    """Simulate a circuit and return measurement counts.

    If the circuit has no classical registers, ``measure_all()`` is
    called automatically before simulation.

    Parameters
    ----------
    circuit : QuantumCircuit
        The circuit to simulate.
    shots : int, optional
        Number of measurement shots (default 1).
    max_parallel_threads : int, optional
        Maximum parallel threads for the simulator (default 4).

    Returns
    -------
    dict
        Measurement counts dictionary ``{bitstring: count}``.
    """
    _require_simulator()
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    if not circuit.cregs:
        circuit.measure_all()
    sim = AerSimulator(max_parallel_threads=max_parallel_threads)
    # Use coupling_map=None to avoid the default 28-qubit coupling-map
    # constraint.  The statevector simulator supports arbitrary qubit
    # counts; the coupling-map check is only relevant for hardware.
    result = sim.run(transpile(circuit, coupling_map=None), shots=shots).result()
    return result.get_counts()
