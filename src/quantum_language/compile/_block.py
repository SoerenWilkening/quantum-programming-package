"""Data classes and constants for compiled quantum function blocks.

Contains ``CompiledBlock``, ``AncillaRecord``, gate type constants, and
the nesting depth limit used during function capture.
"""

# ---------------------------------------------------------------------------
# Gate type constants (from c_backend/include/types.h  Standardgate_t)
# ---------------------------------------------------------------------------
_X, _Y, _Z, _R, _H, _Rx, _Ry, _Rz, _P, _M = range(10)
_SELF_ADJOINT = frozenset({_X, _Y, _Z, _H})
_ROTATION_GATES = frozenset({_P, _Rx, _Ry, _Rz, _R})
_NON_REVERSIBLE = frozenset({_M})


# ---------------------------------------------------------------------------
# Nesting depth limit for compiled function capture
# ---------------------------------------------------------------------------
_capture_depth = 0
_MAX_CAPTURE_DEPTH = 16


# ---------------------------------------------------------------------------
# CompiledBlock -- stores a captured and virtualised gate sequence
# ---------------------------------------------------------------------------
class CompiledBlock:
    """A captured and virtualised gate sequence from a single function call.

    Attributes
    ----------
    gates : list[dict]
        Gate dicts with virtual qubit indices.
    total_virtual_qubits : int
        Total count of virtual qubits (params + ancillas).
    param_qubit_ranges : list[tuple[int, int]]
        (start_virtual_idx, end_virtual_idx) per quantum argument.
    internal_qubit_count : int
        Number of ancilla/temporary virtual qubits.
    return_qubit_range : tuple[int, int] or None
        (start_virtual_idx, width) of the return value, or None.
    return_is_param_index : int or None
        Index of the input parameter if the return value IS one of them.
    """

    __slots__ = (
        "gates",
        "total_virtual_qubits",
        "param_qubit_ranges",
        "internal_qubit_count",
        "return_qubit_range",
        "return_is_param_index",
        "original_gate_count",
        "control_virtual_idx",
        "_first_call_result",
        "_capture_ancilla_qubits",
        "_capture_virtual_to_real",
        "return_type",  # 'qint', 'qarray', or None
        "_return_qarray_element_widths",  # List of element widths for qarray return
        "controlled_block",  # Derived controlled CompiledBlock (Phase 5)
        "_captured_controlled",  # Whether capture was inside control context
        "_instruction_ir",  # list[InstructionRecord] – compile-mode IR
        "_call_records",  # list[CallRecord] – nested compiled function calls
        "_dag_built",  # bool – DAG nodes already built from IR (no duplication on replay)
        "transient_virtual_indices",  # frozenset[int] – virtual indices freed during capture (Phase 8)
    )

    def __init__(
        self,
        gates,
        total_virtual_qubits,
        param_qubit_ranges,
        internal_qubit_count,
        return_qubit_range,
        return_is_param_index=None,
        original_gate_count=None,
    ):
        self.gates = gates
        self.total_virtual_qubits = total_virtual_qubits
        self.param_qubit_ranges = param_qubit_ranges
        self.internal_qubit_count = internal_qubit_count
        self.return_qubit_range = return_qubit_range
        self.return_is_param_index = return_is_param_index
        self.original_gate_count = (
            original_gate_count if original_gate_count is not None else len(gates)
        )
        self.control_virtual_idx = None
        self._first_call_result = None
        self._capture_ancilla_qubits = None
        self._capture_virtual_to_real = None
        self.return_type = None
        self._return_qarray_element_widths = None
        self.controlled_block = None
        self._captured_controlled = False
        self._instruction_ir = []
        self._call_records = []
        self._dag_built = False
        self.transient_virtual_indices = frozenset()


# ---------------------------------------------------------------------------
# Ancilla tracking record
# ---------------------------------------------------------------------------
class AncillaRecord:
    """Record of a single forward call's ancilla allocations."""

    __slots__ = (
        "ancilla_qubits",
        "virtual_to_real",
        "block",
        "return_qint",
    )

    def __init__(self, ancilla_qubits, virtual_to_real, block, return_qint):
        self.ancilla_qubits = ancilla_qubits
        self.virtual_to_real = virtual_to_real
        self.block = block
        self.return_qint = return_qint
