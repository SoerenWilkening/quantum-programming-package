"""Grover oracle decorator for quantum function oracle semantics.

Provides @ql.grover_oracle decorator that layers on top of @ql.compile,
adding oracle-specific validation and transformation:

- Compute-phase-uncompute pattern enforcement (ORCL-02)
- Ancilla allocation delta validation (ORCL-03)
- Bit-flip to phase-flip auto-wrapping (ORCL-04)
- Arithmetic-mode-aware caching (ORCL-05)

Usage
-----
>>> import quantum_language as ql
>>> ql.circuit()
>>> @ql.grover_oracle
... @ql.compile
... def mark_five(x: ql.qint):
...     flag = (x == 5)
...     with flag:
...         pass  # phase-flip via controlled context

>>> @ql.grover_oracle(bit_flip=True)
... @ql.compile
... def mark_five_bf(x: ql.qint):
...     flag = (x == 5)
...     with flag:
...         pass  # bit-flip auto-wrapped with X-H-[oracle]-H-X
"""

import collections
import functools
import hashlib
import inspect

from ._core import (
    _allocate_qubit,
    _deallocate_qubits,
    _get_control_bool,
    _get_controlled,
    _get_list_of_controls,
    _set_control_bool,
    _set_controlled,
    _set_list_of_controls,
    circuit_stats,
    extract_gate_range,
    get_current_layer,
    inject_remapped_gates,
    option,
)
from ._gates import emit_h, emit_x
from .compile import _Z, CompiledFunc, _gates_cancel, compile


# ---------------------------------------------------------------------------
# Source hashing for cache invalidation
# ---------------------------------------------------------------------------
def _compute_source_hash(func):
    """Compute a hash of the function's source code.

    Parameters
    ----------
    func : callable
        The original function (not a CompiledFunc wrapper).

    Returns
    -------
    str
        16-character hex string of the SHA-256 hash, or a fallback
        string based on the code object id.
    """
    try:
        source = inspect.getsource(func)
        return hashlib.sha256(source.encode()).hexdigest()[:16]
    except (OSError, TypeError):
        return str(id(func.__code__))


# ---------------------------------------------------------------------------
# Oracle cache key construction
# ---------------------------------------------------------------------------
def _oracle_cache_key(func, register_width):
    """Build an oracle cache key including source hash and arithmetic mode.

    Parameters
    ----------
    func : callable
        The original function (for source hashing).
    register_width : int
        Width of the search register in qubits.

    Returns
    -------
    tuple
        (source_hash, arithmetic_mode_int, register_width)
    """
    src_hash = _compute_source_hash(func)
    arithmetic_mode = 1 if option("fault_tolerant") else 0
    return (src_hash, arithmetic_mode, register_width)


# ---------------------------------------------------------------------------
# Ancilla delta validation
# ---------------------------------------------------------------------------
def _validate_ancilla_delta(pre_stats, post_stats):
    """Validate that ancilla allocation delta is zero.

    Parameters
    ----------
    pre_stats : dict
        circuit_stats() snapshot before oracle execution.
    post_stats : dict
        circuit_stats() snapshot after oracle execution.

    Raises
    ------
    ValueError
        If the delta is non-zero.
    """
    pre_use = pre_stats["current_in_use"]
    post_use = post_stats["current_in_use"]
    delta = post_use - pre_use
    if delta != 0:
        raise ValueError(
            f"Oracle ancilla delta is {delta} (must be 0). "
            f"Ensure all temporary qubits are uncomputed."
        )


# ---------------------------------------------------------------------------
# Compute-phase-uncompute validation
# ---------------------------------------------------------------------------
def _validate_compute_phase_uncompute(gates, param_qubit_count):
    """Validate compute-phase-uncompute structure of an oracle gate sequence.

    Performs post-hoc analysis of the captured gate sequence to verify
    the oracle follows the standard pattern:
      1. Compute (ancilla gates)
      2. Phase mark (Z-type gates on search register qubits)
      3. Uncompute (adjoint of compute)

    Parameters
    ----------
    gates : list of dict
        Gate dicts from the captured oracle execution.
    param_qubit_count : int
        Number of search register qubits (virtual indices 0..count-1).

    Raises
    ------
    ValueError
        If no phase gates are found, or if the uncompute section does
        not match the adjoint of the compute section.
    """
    if not gates:
        raise ValueError("Oracle has no phase-marking gates on search register qubits.")

    # Identify phase gates: Z-type gates (type == _Z) targeting param qubits.
    # Only Z gates whose target is within the param range count as phase marking.
    # Z gates targeting ancilla qubits are part of compute/uncompute, not marking.
    phase_gate_indices = []
    for i, g in enumerate(gates):
        if g["type"] == _Z and g["target"] < param_qubit_count:
            phase_gate_indices.append(i)

    if not phase_gate_indices:
        raise ValueError("Oracle has no phase-marking gates on search register qubits.")

    first_phase_idx = phase_gate_indices[0]
    last_phase_idx = phase_gate_indices[-1]

    before_phase = gates[:first_phase_idx]
    after_phase = gates[last_phase_idx + 1 :]

    # Verify after_phase is approximately the adjoint of before_phase:
    # reversed order, and each pair cancels.
    if len(before_phase) != len(after_phase):
        raise ValueError("Oracle does not follow compute-phase-uncompute pattern.")

    reversed_before = list(reversed(before_phase))
    for g_before, g_after in zip(reversed_before, after_phase, strict=False):
        if not _gates_cancel(g_before, g_after):
            raise ValueError("Oracle does not follow compute-phase-uncompute pattern.")


# ---------------------------------------------------------------------------
# Bit-flip phase kickback wrapping
# ---------------------------------------------------------------------------
def _wrap_bitflip_oracle(oracle_callable, search_register):
    """Wrap a bit-flip oracle with X-H-[oracle]-H-X phase kickback pattern.

    Allocates an ancilla qubit, prepares it in the |-> state, runs the
    oracle, then undoes the preparation and deallocates the ancilla.

    Parameters
    ----------
    oracle_callable : CompiledFunc
        The compiled oracle function to wrap.
    search_register : qint or similar
        The search register argument to pass to the oracle.

    Raises
    ------
    ValueError
        If the oracle does not interact with the ancilla qubit.
    """
    # Record pre-ancilla layer for gate analysis
    pre_layer = get_current_layer()

    # Allocate ancilla qubit
    ancilla_q = _allocate_qubit()

    # Save and clear controlled context -- X and H on ancilla must be
    # unconditional even if called inside `with qbool:`
    saved_controlled = _get_controlled()
    saved_control_bool = _get_control_bool()
    saved_list_of_controls = list(_get_list_of_controls())
    _set_controlled(False)
    _set_control_bool(None)
    _set_list_of_controls([])

    # Prepare |-> state: X then H
    emit_x(ancilla_q)
    emit_h(ancilla_q)

    # Restore controlled context for oracle execution
    _set_controlled(saved_controlled)
    _set_control_bool(saved_control_bool)
    _set_list_of_controls(saved_list_of_controls)

    # Run the user oracle
    oracle_callable(search_register)

    # Save and clear controlled context again for cleanup
    saved_controlled = _get_controlled()
    saved_control_bool = _get_control_bool()
    saved_list_of_controls = list(_get_list_of_controls())
    _set_controlled(False)
    _set_control_bool(None)
    _set_list_of_controls([])

    # Undo |-> preparation: H then X
    emit_h(ancilla_q)
    emit_x(ancilla_q)

    # Restore controlled context
    _set_controlled(saved_controlled)
    _set_control_bool(saved_control_bool)
    _set_list_of_controls(saved_list_of_controls)

    # Deallocate ancilla (back to |0>, delta = 0)
    _deallocate_qubits(ancilla_q, 1)

    # Verify the oracle interacted with the ancilla qubit
    post_layer = get_current_layer()
    captured_gates = extract_gate_range(pre_layer, post_layer)
    # The X-H and H-X wrapping gates target the ancilla, so we need to check
    # if any gate OTHER than the wrapping gates targets the ancilla.
    # Wrapping gates: first 2 (X, H) and last 2 (H, X) in the captured range.
    # If the oracle emitted any gate targeting the ancilla, there will be more
    # than 4 gates targeting the ancilla.
    ancilla_gate_count = sum(
        1 for g in captured_gates if g["target"] == ancilla_q or ancilla_q in g.get("controls", [])
    )
    # 4 wrapping gates (X, H, H, X) always target the ancilla.
    # If the oracle didn't interact with the ancilla at all, count == 4.
    if ancilla_gate_count <= 4:
        raise ValueError(
            "bit_flip=True but oracle did not interact with ancilla target qubit. Mismatch."
        )


# ---------------------------------------------------------------------------
# GroverOracle class
# ---------------------------------------------------------------------------
class GroverOracle:
    """Wrapper for @ql.grover_oracle decorated functions.

    Wraps a CompiledFunc instance, adding oracle-specific validation
    (ancilla delta, compute-phase-uncompute pattern) and optional
    bit-flip phase kickback auto-wrapping.

    Parameters
    ----------
    compiled_func : CompiledFunc
        The compiled quantum function to wrap as an oracle.
    bit_flip : bool
        If True, auto-wrap with X-H-[oracle]-H-X phase kickback pattern.
    validate : bool
        If True, validate ancilla delta and compute-phase-uncompute pattern.
    """

    def __init__(self, compiled_func, bit_flip=False, validate=True):
        self._compiled_func = compiled_func
        self._bit_flip = bit_flip
        self._validate = validate
        self._original_func = compiled_func._func
        self._cache = collections.OrderedDict()
        self._max_cache = 128
        functools.update_wrapper(self, compiled_func._func)

    def __call__(self, *args, **kwargs):
        """Execute the oracle, with validation and optional bit-flip wrapping."""
        # Extract search register (first quantum arg) to get width
        from .qint import qint

        search_register = None
        width = 0
        for arg in args:
            if isinstance(arg, qint):
                search_register = arg
                width = arg.width
                break
        if search_register is None:
            for k in sorted(kwargs):
                if isinstance(kwargs[k], qint):
                    search_register = kwargs[k]
                    width = kwargs[k].width
                    break

        # Build oracle cache key
        cache_key = _oracle_cache_key(self._original_func, width)

        # Cache hit: replay cached oracle block
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            cached_data = self._cache[cache_key]
            gates = cached_data["gates"]
            # Build virtual-to-real mapping from current args
            virtual_to_real = {}
            if search_register is not None:
                for i in range(width):
                    virtual_to_real[i] = int(search_register.qubits[64 - width + i])
            # Allocate fresh ancilla qubits for virtual indices beyond the
            # search register (these were ancilla/temp qubits during capture)
            max_virtual = max(
                (max(g["target"], max(g["controls"]) if g["controls"] else -1) for g in gates),
                default=-1,
            )
            ancilla_allocated = []
            for v in range(width, max_virtual + 1):
                if v not in virtual_to_real:
                    real_q = _allocate_qubit()
                    virtual_to_real[v] = real_q
                    ancilla_allocated.append(real_q)
            inject_remapped_gates(gates, virtual_to_real)
            # Deallocate ancilla qubits (oracle must have zero ancilla delta)
            for real_q in ancilla_allocated:
                _deallocate_qubits(real_q, 1)
            return cached_data.get("result")

        # Cache miss: execute oracle
        pre_stats = circuit_stats()
        start_layer = get_current_layer()

        if self._bit_flip:
            _wrap_bitflip_oracle(self._compiled_func, search_register)
            result = None
        else:
            result = self._compiled_func(*args, **kwargs)

        post_stats = circuit_stats()
        end_layer = get_current_layer()

        # Validation
        if self._validate:
            _validate_ancilla_delta(pre_stats, post_stats)

            # Extract gates for compute-phase-uncompute analysis
            captured_gates = extract_gate_range(start_layer, end_layer)
            if captured_gates and width > 0:
                try:
                    _validate_compute_phase_uncompute(captured_gates, width)
                except ValueError:
                    # Re-raise validation errors
                    raise

        # Cache the result (store gate range for potential replay)
        captured_gates = extract_gate_range(start_layer, end_layer)
        if search_register is not None and captured_gates:
            # Build real-to-virtual mapping for caching
            real_to_virtual = {}
            for i in range(width):
                real_q = int(search_register.qubits[64 - width + i])
                real_to_virtual[real_q] = i

            # Remap remaining qubits encountered in gates
            next_virtual = width
            for g in captured_gates:
                for q in [g["target"]] + g.get("controls", []):
                    if q not in real_to_virtual:
                        real_to_virtual[q] = next_virtual
                        next_virtual += 1

            # Virtualise gates for caching
            virtual_gates = []
            for g in captured_gates:
                vg = dict(g)
                vg["target"] = real_to_virtual[g["target"]]
                vg["controls"] = [real_to_virtual[c] for c in g.get("controls", [])]
                virtual_gates.append(vg)

            # Build virtual-to-real for replay reference
            virtual_to_real = {v: r for r, v in real_to_virtual.items()}

            self._cache[cache_key] = {
                "gates": virtual_gates,
                "qubit_map": virtual_to_real,
                "result": result,
            }

            # Evict oldest if over capacity
            while len(self._cache) > self._max_cache:
                self._cache.popitem(last=False)

        return result

    def __repr__(self):
        return f"<GroverOracle {self._original_func.__name__}>"


# ---------------------------------------------------------------------------
# Public decorator API
# ---------------------------------------------------------------------------
def grover_oracle(func=None, *, bit_flip=False, validate=True):
    """Decorator for Grover oracle functions.

    Layers on top of @ql.compile, adding oracle-specific validation
    and optional bit-flip phase kickback auto-wrapping.

    Supports three forms:
      @ql.grover_oracle
      @ql.grover_oracle()
      @ql.grover_oracle(bit_flip=True, validate=False)

    Parameters
    ----------
    func : callable or CompiledFunc, optional
        When used as bare @ql.grover_oracle (no parens).
    bit_flip : bool
        If True, auto-wrap with X-H-[oracle]-H-X phase kickback.
    validate : bool
        If True (default), validate ancilla delta and oracle structure.

    Returns
    -------
    GroverOracle or decorator
        GroverOracle wrapper or decorator function.

    Examples
    --------
    >>> @ql.grover_oracle
    ... @ql.compile
    ... def mark_five(x: ql.qint):
    ...     flag = (x == 5)
    ...     with flag:
    ...         pass

    >>> @ql.grover_oracle(bit_flip=True)
    ... @ql.compile
    ... def mark_bf(x: ql.qint):
    ...     flag = (x == 5)
    ...     with flag:
    ...         pass
    """

    def decorator(fn):
        if not isinstance(fn, CompiledFunc):
            fn = compile(fn)
        return GroverOracle(fn, bit_flip=bit_flip, validate=validate)

    if func is not None:
        if isinstance(func, CompiledFunc):
            return GroverOracle(func, bit_flip=bit_flip, validate=validate)
        return GroverOracle(compile(func), bit_flip=bit_flip, validate=validate)
    return decorator
