"""Global registry and utility helpers for CompiledFunc.

Contains the weak-reference registry for cache invalidation on circuit
reset, argument classification, and hierarchical gate count computation.
These are extracted from ``_func.py`` to reduce its size.
"""

import weakref

from .._core import (
    _register_cache_clear_hook,
    option,
)
from ..call_graph import _dag_builder_stack
from . import _block

# ---------------------------------------------------------------------------
# Global registry for cache invalidation on circuit reset
# ---------------------------------------------------------------------------
_compiled_funcs = []  # List of weakref.ref to CompiledFunc instances


def register_compiled_func(cf):
    """Add a CompiledFunc to the global registry (weak reference)."""
    _compiled_funcs.append(weakref.ref(cf))


def _clear_all_caches():
    """Clear compilation caches for all live CompiledFunc instances.

    Called automatically when a new circuit is created via ql.circuit().
    Dead weak references are pruned during iteration.

    Also enables simulate mode so gates are stored in the circuit.
    The C default is simulate=0 (tracking-only), but full simulation
    is required for QASM export, compiled function replay, and any
    operation that needs gate data in the circuit.

    Note: this means ql.circuit() forces simulate=True.  Users who
    want tracking-only mode should set ql.option('simulate', False)
    AFTER calling ql.circuit(), or avoid calling ql.circuit() entirely
    (the circuit initializes automatically).
    """
    _block._capture_depth = 0
    _dag_builder_stack.clear()
    option("simulate", True)
    alive = []
    for ref in _compiled_funcs:
        obj = ref()
        if obj is not None:
            obj._reset_for_circuit()
            alive.append(ref)
    _compiled_funcs[:] = alive


# Register the hook so circuit.__init__ calls us
_register_cache_clear_hook(_clear_all_caches)


# ---------------------------------------------------------------------------
# Argument classification
# ---------------------------------------------------------------------------
def classify_args(args, kwargs):
    """Separate quantum and classical arguments.

    Returns (quantum_args, classical_args, widths).
    quantum_args: list of qint/qbool/qarray in positional order.
    classical_args: list of non-quantum values.
    widths: list of int widths for qint, or ('arr', length) for qarray.
    """
    from ..qarray import qarray
    from ..qint import qint

    quantum_args = []
    classical_args = []
    widths = []

    for arg in args:
        if isinstance(arg, qarray):
            # Validate: empty qarray not supported
            if len(arg) == 0:
                raise ValueError("Empty qarray not supported as compiled function argument")
            # Validate: stale qarray elements
            for elem in arg:  # Use iteration protocol
                if getattr(elem, "_is_uncomputed", False) or not getattr(
                    elem, "allocated_qubits", True
                ):
                    raise ValueError("qarray contains deallocated qubits")
            quantum_args.append(arg)
            widths.append(("arr", len(arg)))
        elif isinstance(arg, qint):
            quantum_args.append(arg)
            widths.append(arg.width)
        else:
            classical_args.append(arg)

    # Also classify kwargs (sorted by key for determinism)
    for k in sorted(kwargs):
        val = kwargs[k]
        if isinstance(val, qarray):
            # Validate: empty qarray not supported
            if len(val) == 0:
                raise ValueError("Empty qarray not supported as compiled function argument")
            # Validate: stale qarray elements
            for elem in val:  # Use iteration protocol
                if getattr(elem, "_is_uncomputed", False) or not getattr(
                    elem, "allocated_qubits", True
                ):
                    raise ValueError("qarray contains deallocated qubits")
            quantum_args.append(val)
            widths.append(("arr", len(val)))
        elif isinstance(val, qint):
            quantum_args.append(val)
            widths.append(val.width)
        else:
            classical_args.append(val)

    return quantum_args, classical_args, widths


# ---------------------------------------------------------------------------
# Hierarchical gate count
# ---------------------------------------------------------------------------
def hierarchical_gate_count(cf, visited=None):
    """Compute hierarchical gate count, with cycle detection.

    Parameters
    ----------
    cf : CompiledFunc
        The compiled function instance.
    visited : set or None
        Set of ``id(CompiledFunc)`` already visited, to prevent infinite
        recursion from circular references.

    Returns
    -------
    dict
        ``{'own': int, 'referenced': int, 'total': int,
          'breakdown': list[dict]}``
    """
    if visited is None:
        visited = set()

    my_id = id(cf)
    if my_id in visited:
        return {"own": 0, "referenced": 0, "total": 0, "breakdown": []}
    visited.add(my_id)

    total_own = 0
    total_referenced = 0
    breakdown = []

    for _cache_key, block in cf._cache.items():
        own_gates = len(block.gates)
        total_own += own_gates

        call_records = getattr(block, "_call_records", None) or []
        for cr in call_records:
            inner_func = cr.compiled_func_ref
            if inner_func is not None and hasattr(inner_func, "_hierarchical_gate_count"):
                inner_counts = inner_func._hierarchical_gate_count(visited=set(visited))
                ref_total = inner_counts["total"]
                total_referenced += ref_total
                breakdown.append(
                    {
                        "func_name": getattr(inner_func, "__name__", str(inner_func)),
                        "cache_key": cr.cache_key,
                        "gate_count": ref_total,
                    }
                )

    return {
        "own": total_own,
        "referenced": total_referenced,
        "total": total_own + total_referenced,
        "breakdown": breakdown,
    }
