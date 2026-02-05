"""Helper functions for verification test framework.

Provides input generation strategies (exhaustive for small widths, sampled for large)
and result formatting utilities for clear failure diagnostics.
"""

import itertools
import random


def generate_exhaustive_values(width):
    """Generate all possible values for a given bit width.

    Args:
        width: Bit width (1-4 recommended for exhaustive testing)

    Returns:
        List of all integers from 0 to 2^width - 1

    Example:
        >>> generate_exhaustive_values(3)
        [0, 1, 2, 3, 4, 5, 6, 7]
    """
    return list(range(2**width))


def generate_exhaustive_pairs(width):
    """Generate all possible (a, b) pairs for a given bit width.

    Args:
        width: Bit width (1-4 recommended for exhaustive testing)

    Returns:
        List of all (a, b) tuples where both a and b are in [0, 2^width - 1]

    Example:
        >>> len(generate_exhaustive_pairs(2))
        16
    """
    values = range(2**width)
    return list(itertools.product(values, repeat=2))


def generate_sampled_values(width, sample_size=50):
    """Generate representative sample of values for larger bit widths.

    Includes edge cases (0, 1, max, max-1) plus random samples for coverage.
    Uses deterministic seed for reproducibility.

    Args:
        width: Bit width (5+ recommended for sampled testing)
        sample_size: Number of random samples to include (default: 50)

    Returns:
        List of representative integer values, deduplicated

    Example:
        >>> vals = generate_sampled_values(8, sample_size=10)
        >>> 0 in vals and 255 in vals  # Edge cases included
        True
    """
    max_val = (2**width) - 1

    # Start with edge cases
    edge_cases = {0, 1, max_val, max_val - 1}

    # Add random samples with deterministic seed
    random.seed(42)
    samples = {random.randint(0, max_val) for _ in range(sample_size)}

    # Combine and return as sorted list
    return sorted(edge_cases | samples)


def generate_sampled_pairs(width, sample_size=50):
    """Generate representative sample of (a, b) pairs for larger bit widths.

    Includes all edge case pairs plus random pairs for coverage.
    Uses deterministic seed for reproducibility.

    Args:
        width: Bit width (5+ recommended for sampled testing)
        sample_size: Number of random pairs to include (default: 50)

    Returns:
        List of representative (a, b) tuples, deduplicated

    Example:
        >>> pairs = generate_sampled_pairs(8, sample_size=10)
        >>> (0, 0) in pairs and (255, 255) in pairs  # Edge case pairs included
        True
    """
    max_val = (2**width) - 1

    # Start with all edge case pairs
    edge_values = [0, 1, max_val, max_val - 1]
    edge_pairs = set(itertools.product(edge_values, repeat=2))

    # Add random pairs with deterministic seed
    random.seed(42)
    random_pairs = {
        (random.randint(0, max_val), random.randint(0, max_val)) for _ in range(sample_size)
    }

    # Combine and return as sorted list
    return sorted(edge_pairs | random_pairs)


def format_failure_message(op_name, operands, width, expected, actual):
    """Format a compact one-line failure message for test assertions.

    Args:
        op_name: Operation name (e.g., 'init', 'add', 'mul')
        operands: List of operand values (single value for init, pair for binary ops)
        width: Bit width of the operation
        expected: Expected result value
        actual: Actual result value from simulation

    Returns:
        Formatted failure message string

    Example:
        >>> format_failure_message('init', [5], 4, 5, 3)
        'FAIL: init(5) 4-bit: expected=5, got=3'
        >>> format_failure_message('add', [3, 5], 4, 8, 6)
        'FAIL: add(3,5) 4-bit: expected=8, got=6'
    """
    # Format operands as comma-separated list
    operands_str = ",".join(str(op) for op in operands)

    return f"FAIL: {op_name}({operands_str}) {width}-bit: expected={expected}, got={actual}"
