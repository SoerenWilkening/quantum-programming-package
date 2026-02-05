"""Tests for OpenQASM export functionality."""

import quantum_language as ql


def test_to_openqasm_returns_string(clean_circuit):
    """Test that to_openqasm() returns a non-empty string."""
    # Create a simple quantum integer
    _a = ql.qint(5, width=4)

    # Export to OpenQASM
    qasm = ql.to_openqasm()

    # Verify it's a string and non-empty
    assert isinstance(qasm, str)
    assert len(qasm) > 0


def test_to_openqasm_has_header(clean_circuit):
    """Test that exported QASM contains required OpenQASM 3.0 header."""
    # Create a quantum integer
    _a = ql.qint(5, width=4)

    # Export to OpenQASM
    qasm = ql.to_openqasm()

    # Verify OpenQASM 3.0 header is present
    assert "OPENQASM 3.0" in qasm
    assert 'include "stdgates.inc"' in qasm


def test_to_openqasm_has_qubit_declaration(clean_circuit):
    """Test that exported QASM contains qubit declarations."""
    # Create a quantum integer (requires 4 qubits)
    _a = ql.qint(5, width=4)

    # Export to OpenQASM
    qasm = ql.to_openqasm()

    # Verify qubit declaration is present
    # Don't hardcode exact count since ancilla qubits may vary
    assert "qubit[" in qasm


def test_to_openqasm_has_gates(clean_circuit):
    """Test that exported QASM contains gate operations."""
    # Create a quantum integer with value 5 (binary 0101)
    # This should create X gates on bits 0 and 2
    _a = ql.qint(5, width=4)

    # Export to OpenQASM
    qasm = ql.to_openqasm()

    # Verify X gates are present (for classical initialization)
    assert "x " in qasm


def test_to_openqasm_empty_circuit():
    """Test that to_openqasm() works with empty circuit (module auto-initializes)."""
    # Note: Module automatically initializes circuit at import time via circuit() call
    # at end of _core.pyx, so there's always a circuit available.
    # This test verifies the auto-initialized empty circuit exports valid QASM.
    qasm = ql.to_openqasm()

    # Even empty circuit should have valid OpenQASM structure
    assert isinstance(qasm, str)
    assert len(qasm) > 0
    assert "OPENQASM 3.0" in qasm
    assert "qubit[" in qasm  # Should have at least one qubit


def test_to_openqasm_in_all():
    """Test that to_openqasm is exported in __all__."""
    assert "to_openqasm" in ql.__all__
