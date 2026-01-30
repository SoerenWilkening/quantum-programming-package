#!/usr/bin/env python3
"""Demo script showcasing quantum_language package functionality.

Run after compiling with: python setup.py build_ext --inplace
"""

import sys
from pathlib import Path

# Add src/ to path for development use (without pip install)
sys.path.insert(0, str(Path(__file__).parent / "src"))

import quantum_language as ql

# Create a quantum circuit context
c = ql.circuit()

# Create quantum integers
print("Creating quantum integers...")
a = ql.qint(5, width=8)  # 8-bit qint initialized to 5
b = ql.qint(3, width=8)  # 8-bit qint initialized to 3

# Perform arithmetic
print("Computing a + b...")
result = a + b  # Quantum addition circuit

# Create a quantum boolean
print("Creating quantum boolean...")
condition = ql.qbool(True)

# Create a quantum array
print("Creating quantum array...")
arr = ql.array([1, 2, 3], width=8)  # Array of three 8-bit qints

# Access array elements
first_elem = arr[0]

# Print circuit statistics
print("\nCircuit Statistics:")
print("=" * 50)
stats = ql.circuit_stats()
print(stats)
