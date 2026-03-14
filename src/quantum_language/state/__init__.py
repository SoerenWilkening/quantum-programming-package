"""State management and uncomputation for quantum circuits.

Access via: from quantum_language.state import ...
Or: import quantum_language as ql; ql.state.circuit_stats()
"""

from .._core import (
    circuit_stats,
    get_current_layer,
    get_gate_count,
    reset_gate_count,
    reverse_instruction_range,
)

__all__ = [
    "circuit_stats",
    "get_current_layer",
    "get_gate_count",
    "reset_gate_count",
    "reverse_instruction_range",
]
