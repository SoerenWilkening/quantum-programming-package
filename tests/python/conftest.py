"""Pytest configuration and fixtures for quantum language testing."""

import re

import pytest

# Clean import - package installed via pip install -e .
import quantum_language as ql


@pytest.fixture
def clean_circuit():
    """Provides a fresh circuit for each test.

    Initializes a new circuit via quantum_language.circuit().
    Cleanup happens automatically via Python GC.
    """
    circ = ql.circuit()
    yield circ
    # Cleanup happens automatically via Python GC


@pytest.fixture
def sample_qints():
    """Provides sample quantum integers for testing.

    Returns:
        dict: Dictionary with 'small', 'medium', and 'large' qint samples
    """
    return {
        "small": ql.qint(value=5, bits=4),
        "medium": ql.qint(value=100, bits=8),
        "large": ql.qint(value=5000, bits=16),
    }


def normalize_circuit_output(output: str) -> str:
    """Remove non-deterministic elements from circuit output.

    Removes memory addresses (0x...) and timing information to enable
    deterministic comparisons in characterization tests.

    Args:
        output: Raw circuit output string

    Returns:
        str: Normalized output with addresses and timing removed
    """
    # Remove memory addresses (0x...)
    output = re.sub(r"0x[0-9a-fA-F]+", "0xADDRESS", output)
    # Remove timing information (e.g., "1.23s")
    output = re.sub(r"\d+\.\d+s", "TIME", output)
    return output
