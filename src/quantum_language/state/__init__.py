"""State management and uncomputation for quantum circuits.

Access via: from quantum_language.state import ...
Or: import quantum_language as ql; ql.state.circuit_stats()
"""

from quantum_language._core import circuit_stats, get_current_layer, reverse_instruction_range

__all__ = [
    "circuit_stats",
    "get_current_layer",
    "reverse_instruction_range",
]
