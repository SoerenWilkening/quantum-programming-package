"""Inverse (adjoint) helpers and wrapper classes for compiled functions.

Contains ``_InverseCompiledFunc`` (standalone adjoint replay) and
``_AncillaInverseProxy`` (uncomputing a prior forward call's ancillas),
plus the gate-level adjoint helpers ``_adjoint_gate`` and
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
# _InverseCompiledFunc -- lightweight wrapper for adjoint replay
# ---------------------------------------------------------------------------
class _InverseCompiledFunc:
    """Wrapper that replays the adjoint (inverse) gate sequence of a ``CompiledFunc``.

    Does NOT inherit from ``CompiledFunc``.  Reuses the original's
    ``_classify_args``, ``_replay``, and cache, but maintains its own
    cache of inverted ``CompiledBlock`` objects.
    """

    def __init__(self, original):
        self._original = original
        self._opt = original._opt
        self._inv_cache = {}
        functools.update_wrapper(self, original._func)

    def __call__(self, *args, **kwargs):
        """Call the inverse compiled function."""
        from . import (
            _get_mode_flags,
            _input_qubit_key,
        )

        quantum_args, classical_args, widths = self._original._classify_args(args, kwargs)

        # Build cache key for the inverse cache.  The inverse inverts the
        # uncontrolled block, so we use control_count=0 for looking up
        # the original's cache.
        qubit_saving = _get_qubit_saving_mode()
        mode_flags = _get_mode_flags()
        if self._original._key_func:
            base_key = (
                self._original._key_func(*args, **kwargs),
                qubit_saving,
            )
        else:
            base_key = (
                tuple(classical_args),
                tuple(widths),
                qubit_saving,
            )
        # Key for the original's uncontrolled cache entry
        original_key = base_key + (0,) + mode_flags
        # Key for the inverse cache (includes current control state)
        cache_key = base_key + (0,) + mode_flags

        # Check inverse cache
        if cache_key not in self._inv_cache:
            # Ensure original has the uncontrolled block cached
            if original_key not in self._original._cache:
                # Trigger uncontrolled capture by calling the original.
                # Temporarily clear the control stack so the capture
                # produces an uncontrolled entry (control_count=0),
                # matching original_key.
                saved_stack = list(_get_control_stack())
                _set_control_stack([])
                try:
                    self._original(*args, **kwargs)
                finally:
                    _set_control_stack(saved_stack)
                # Remove any forward call record created as side-effect
                input_key = _input_qubit_key(quantum_args)
                self._original._forward_calls.pop(input_key, None)

            block = self._original._cache[original_key]
            # Invert uncontrolled gates
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
        # _replay selects controlled/uncontrolled variant at runtime
        return self._original._replay(
            inv_block, quantum_args, track_forward=False, kind="compiled_fn_inv"
        )

    def inverse(self):
        """Return the original ``CompiledFunc`` (round-trip)."""
        return self._original

    def _reset_for_circuit(self):
        """Reset for circuit change (same as clear_cache for inverse)."""
        self._inv_cache.clear()

    def clear_cache(self):
        """Clear the inverse cache."""
        self._inv_cache.clear()

    def __repr__(self):
        return f"<InverseCompiledFunc {self._original._func.__name__}>"


# ---------------------------------------------------------------------------
# _AncillaInverseProxy -- uncomputes a prior forward call's ancillas
# ---------------------------------------------------------------------------
class _AncillaInverseProxy:
    """Callable proxy that uncomputes a prior forward call's ancillas.

    Returned by CompiledFunc.inverse (as a property). When called as
    f.inverse(x), looks up the forward call record by input qubit identity,
    replays adjoint gates on the original physical ancilla qubits, deallocates
    them, and invalidates the return qint.
    """

    def __init__(self, compiled_func):
        self._cf = compiled_func

    def __call__(self, *args, **kwargs):
        from .._core import _deallocate_qubits
        from . import (
            _derive_controlled_gates,
            _get_quantum_arg_qubit_indices,
            _input_qubit_key,
        )

        quantum_args, _, _ = self._cf._classify_args(args, kwargs)
        input_key = _input_qubit_key(quantum_args)

        record = self._cf._forward_calls.get(input_key)
        if record is None:
            raise ValueError(
                f"No prior forward call of '{self._cf._func.__name__}' found "
                f"for these input qubits. Call the function forward first."
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

        # Remove forward call record
        del self._cf._forward_calls[input_key]

        return None

    def __repr__(self):
        return f"<AncillaInverseProxy {self._cf._func.__name__}>"
