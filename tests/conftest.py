"""Pytest configuration and fixtures for verification testing.

This conftest.py serves the root tests/ directory for verification tests.
It is separate from tests/python/conftest.py which serves unit tests.

Provides the verify_circuit fixture that encapsulates the full verification pipeline:
Python quantum_language API -> C backend circuit -> OpenQASM 3.0 export ->
Qiskit simulation -> result extraction and validation.
"""

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql


@pytest.fixture
def verify_circuit():
    """Fixture providing full verification pipeline for quantum circuits.

    Returns a callable _verify(circuit_builder, width, in_place=False) that:
    1. Resets circuit state via ql.circuit()
    2. Builds circuit using circuit_builder() function
    3. Exports to OpenQASM 3.0 via ql.to_openqasm()
    4. Loads into Qiskit and simulates with AerSimulator
    5. Extracts result from measurement counts
    6. Returns (actual, expected) tuple for assertion

    Args:
        circuit_builder: Callable that builds circuit and returns expected result
        width: Bit width of result register to extract
        in_place: If True, result uses full bitstring (for NOT operations).
                 If False (default), result uses first `width` chars of bitstring.

    Returns:
        Callable that returns (actual, expected) tuple

    Example:
        def test_init_value(verify_circuit):
            def build():
                a = ql.qint(5, width=4)
                return 5  # Expected value

            actual, expected = verify_circuit(build, width=4)
            assert actual == expected, f"Expected {expected}, got {actual}"
    """

    def _verify(circuit_builder, width, in_place=False):
        """Execute verification pipeline.

        Args:
            circuit_builder: Function that builds circuit and returns expected value
            width: Bit width of result register
            in_place: Whether operation is in-place (affects result extraction)

        Returns:
            Tuple of (actual, expected) where actual is extracted from simulation
            and expected is returned from circuit_builder

        Raises:
            Exception: If simulation fails, includes QASM in error for debugging
        """
        # Reset circuit state
        ql.circuit()

        # Build circuit and get expected value
        expected = circuit_builder()

        # Export to OpenQASM 3.0
        qasm_str = ql.to_openqasm()

        try:
            # Load QASM into Qiskit
            circuit = qiskit.qasm3.loads(qasm_str)

            # Add measurements if circuit has no classical registers
            if not circuit.cregs:
                circuit.measure_all()

            # Simulate with statevector method for deterministic results
            simulator = AerSimulator(method="statevector")
            job = simulator.run(circuit, shots=1)
            result = job.result()
            counts = result.get_counts()

            # Extract result bitstring
            bitstring = list(counts.keys())[0]

            # Handle result extraction based on operation type
            if in_place:
                # In-place operations (NOT): use full bitstring
                result_bits = bitstring
            else:
                # Standard operations: result register is at highest indices (first chars)
                result_bits = bitstring[:width]

            # Convert to integer
            actual = int(result_bits, 2)

            return (actual, expected)

        except Exception as e:
            # Include QASM in error message for debugging
            error_msg = f"Simulation failed: {str(e)}\n\nOpenQASM 3.0:\n{qasm_str}"
            raise Exception(error_msg) from e

    return _verify


@pytest.fixture
def clean_circuit():
    """Provides a fresh circuit for each test.

    Simple fixture that resets circuit state via quantum_language.circuit().
    For tests that need circuit reset without the full verification pipeline.

    Yields:
        Circuit instance from quantum_language
    """
    circ = ql.circuit()
    yield circ
    # Cleanup happens automatically via Python GC
