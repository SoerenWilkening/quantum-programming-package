"""Inverse (adjoint) helpers for compiled functions.

Contains ``_InverseProxy`` — a unified inverse callable that auto-dispatches:
when a forward-call record exists, it reuses the original ancilla qubits and
deallocates them; otherwise it does a standalone adjoint replay with fresh
ancillas.

Also provides gate-level adjoint helpers ``_adjoint_gate`` and
``_inverse_gate_list``.
"""

import functools

from .._core import (
    _get_control_bool,
    _get_control_stack,
    _get_controlled,
    _get_layer_floor,
    _get_qubit_saving_mode,
    _set_control_stack,
    _set_layer_floor,
    get_current_layer,
    inject_remapped_gates,
)
from ._block import (
    _NON_REVERSIBLE,
    _ROTATION_GATES,
    CompiledBlock,
)


# ---------------------------------------------------------------------------
# Gate-level adjoint helpers
# ---------------------------------------------------------------------------
def _adjoint_gate(gate):
    """Return the adjoint of *gate*.

    Self-adjoint gates (X, Y, Z, H) are unchanged.  Rotation gates have
    their angle negated.  Measurement gates cannot be inverted.
    """
    if gate["type"] in _NON_REVERSIBLE:
        raise ValueError("Cannot invert compiled function containing measurement gates")
    adj = dict(gate)
    if gate["type"] in _ROTATION_GATES:
        adj["angle"] = -gate["angle"]
    return adj


def _inverse_gate_list(gates):
    """Return the adjoint of a gate list (reversed order, adjoint gates)."""
    return [_adjoint_gate(g) for g in reversed(gates)]


# ---------------------------------------------------------------------------
# _InverseProxy — unified inverse for compiled functions
# ---------------------------------------------------------------------------
class _InverseProxy:
    """Unified inverse callable for a ``CompiledFunc``.

    Auto-dispatches at call time:

    * **Ancilla path** — if a forward-call record exists for the input
      qubits, replay the adjoint on the *original* physical ancilla
      qubits, deallocate them, and remove the record.  This is the
      compute-uncompute pattern (``f(x); ...; f.inverse(x)``).

    * **Standalone path** — if no forward-call record exists, build
      (and cache) an inverted ``CompiledBlock`` from the original's
      uncontrolled cache entry and replay it with fresh ancillas.
      Works without any prior forward call.

    Returned by ``CompiledFunc.inverse`` (property).
    """

    def __init__(self, compiled_func):
        self._cf = compiled_func
        self._inv_cache = {}
        functools.update_wrapper(self, compiled_func._func)

    # ---- call dispatch ----------------------------------------------------

    def __call__(self, *args, **kwargs):
        from . import (
            _input_qubit_key,
        )

        quantum_args, _, _ = self._cf._classify_args(args, kwargs)
        input_key = _input_qubit_key(quantum_args)

        records = self._cf._forward_calls.get(input_key)
        if records:
            record = records[-1]  # LIFO: most recent forward call
            return self._ancilla_path(quantum_args, input_key, record)
        else:
            return self._standalone_path(args, kwargs, quantum_args)

    # ---- ancilla path (reuse original qubits) -----------------------------

    def _ancilla_path(self, quantum_args, input_key, record):
        """Undo a prior forward call: adjoint on original ancillas, then free."""
        from .._core import _deallocate_qubits
        from . import (
            _derive_controlled_gates,
            _get_quantum_arg_qubit_indices,
        )

        # Generate adjoint gates
        adjoint_gates = _inverse_gate_list(record.block.gates)

        # Handle controlled context
        is_controlled = _get_controlled()
        if is_controlled:
            control_bool = _get_control_bool()
            ctrl_qubit = int(control_bool.qubits[63])
            adjoint_gates = _derive_controlled_gates(adjoint_gates)
            vtr = dict(record.virtual_to_real)
            vtr[0] = ctrl_qubit  # control at reserved index 0
        else:
            vtr = record.virtual_to_real

        # Inject adjoint gates with original qubit mapping
        saved_floor = _get_layer_floor()
        _set_layer_floor(get_current_layer())
        inject_remapped_gates(adjoint_gates, vtr)
        _set_layer_floor(saved_floor)

        # Record compiled-function inverse history entry for cancellation
        if quantum_args:
            _qm = tuple(q for qa in quantum_args for q in _get_quantum_arg_qubit_indices(qa))
            target = quantum_args[0]
            if hasattr(target, "history"):
                target.history.append(
                    id(self._cf),
                    _qm,
                    len(record.ancilla_qubits),
                    kind="compiled_fn_inv",
                )

        # Deallocate ancilla qubits (one at a time, may be non-contiguous)
        for qubit_idx in record.ancilla_qubits:
            _deallocate_qubits(qubit_idx, 1)

        # Invalidate return qint
        if record.return_qint is not None:
            record.return_qint._is_uncomputed = True
            record.return_qint.allocated_qubits = False

        # Remove forward call record (pop from stack)
        records = self._cf._forward_calls.get(input_key)
        if records:
            records.pop()
            if not records:
                del self._cf._forward_calls[input_key]

        return None

    # ---- standalone path (fresh ancillas) ---------------------------------

    def _standalone_path(self, args, kwargs, quantum_args):
        """Replay inverted gates with fresh ancilla allocation."""
        from . import (
            _get_mode_flags,
            _input_qubit_key,
        )

        quantum_args, classical_args, widths = self._cf._classify_args(args, kwargs)

        # Build cache key for the inverse cache.
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._cf._key_func:
            base_key = (
                self._cf._key_func(*args, **kwargs),
                qubit_saving,
            )
        else:
            base_key = (
                tuple(classical_args),
                tuple(widths),
                qubit_saving,
            )
        original_key = base_key + (0,) + mode_flags
        cache_key = base_key + (0,) + mode_flags

        # Ensure inverted block is cached
        if cache_key not in self._inv_cache:
            # Ensure original has the uncontrolled block cached
            if original_key not in self._cf._cache:
                saved_stack = list(_get_control_stack())
                _set_control_stack([])
                try:
                    self._cf(*args, **kwargs)
                finally:
                    _set_control_stack(saved_stack)
                # Remove any forward call record created as side-effect
                input_key = _input_qubit_key(quantum_args)
                records = self._cf._forward_calls.get(input_key)
                if records:
                    records.pop()
                    if not records:
                        del self._cf._forward_calls[input_key]

            block = self._cf._cache[original_key]
            inverted_gates = _inverse_gate_list(block.gates)
            inverted_block = CompiledBlock(
                gates=inverted_gates,
                total_virtual_qubits=block.total_virtual_qubits,
                param_qubit_ranges=list(block.param_qubit_ranges),
                internal_qubit_count=block.internal_qubit_count,
                return_qubit_range=block.return_qubit_range,
                return_is_param_index=block.return_is_param_index,
                original_gate_count=block.original_gate_count,
            )
            inverted_block.return_type = block.return_type
            inverted_block._return_qarray_element_widths = block._return_qarray_element_widths
            self._inv_cache[cache_key] = inverted_block

        inv_block = self._inv_cache[cache_key]
        result = self._cf._replay(
            inv_block, quantum_args, track_forward=False, kind="compiled_fn_inv"
        )

        # Clear any stale forward-call record (e.g. from a prior forward
        # call whose ancillas were already freed by qubit saving).
        input_key = _input_qubit_key(quantum_args)
        records = self._cf._forward_calls.get(input_key)
        if records:
            records.pop()
            if not records:
                del self._cf._forward_calls[input_key]

        return result

    # ---- round-trip & lifecycle -------------------------------------------

    def inverse(self):
        """Return the original ``CompiledFunc`` (round-trip)."""
        return self._cf

    def _reset_for_circuit(self):
        """Reset for circuit change."""
        self._inv_cache.clear()

    def clear_cache(self):
        """Clear the inverse cache."""
        self._inv_cache.clear()

    def __repr__(self):
        return f"<InverseProxy {self._cf._func.__name__}>"


# ---------------------------------------------------------------------------
# Backward-compatible aliases (referenced in tests)
# ---------------------------------------------------------------------------
_InverseCompiledFunc = _InverseProxy
_AncillaInverseProxy = _InverseProxy
