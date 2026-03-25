"""Compile decorator for quantum function capture and replay.

Provides @ql.compile decorator that captures gate sequences on first call
and replays them with qubit remapping on subsequent calls.  When
``optimize=True`` (the default), adjacent inverse gates are cancelled and
consecutive rotations on the same qubit are merged before the sequence is
cached, so every replay benefits from the reduced gate count.

Usage
-----
>>> import quantum_language as ql
>>> @ql.compile
... def add_one(x):
...     x += 1
...     return x
>>> a = ql.qint(3, width=4)
>>> result = add_one(a)   # Capture + optimise
>>> b = ql.qint(5, width=4)
>>> result2 = add_one(b)  # Replay (optimised sequence)
"""

from .._core import (
    option,
)
from . import _block as _block  # noqa: F401 – re-exported
from ._block import _H as _H  # noqa: F401 – re-exported
from ._block import _M as _M  # noqa: F401 – re-exported
from ._block import _MAX_CAPTURE_DEPTH as _MAX_CAPTURE_DEPTH  # noqa: F401
from ._block import _P as _P  # noqa: F401 – re-exported
from ._block import _R as _R  # noqa: F401 – re-exported
from ._block import _X as _X  # noqa: F401 – re-exported
from ._block import _Y as _Y  # noqa: F401 – re-exported
from ._block import _Z as _Z  # noqa: F401 – re-exported
from ._block import AncillaRecord as AncillaRecord  # noqa: F401
from ._block import CompiledBlock as CompiledBlock  # noqa: F401
from ._block import _Rx as _Rx  # noqa: F401 – re-exported
from ._block import _Ry as _Ry  # noqa: F401 – re-exported
from ._block import _Rz as _Rz  # noqa: F401 – re-exported


# ---------------------------------------------------------------------------
# Mode flag helpers (FIX-04)
# ---------------------------------------------------------------------------
def _get_mode_flags():
    """Return current arithmetic mode flags for cache key inclusion.

    Returns a tuple of (arithmetic_mode, cla_override, tradeoff_policy)
    that uniquely identifies the arithmetic configuration.  Including these
    in the cache key ensures that switching modes between calls causes a
    clean cache miss rather than replaying stale gates (FIX-04).
    """
    arithmetic_mode = 1 if option("fault_tolerant") else 0
    cla_override = 0 if option("cla") else 1
    tradeoff_policy = option("tradeoff")
    return (arithmetic_mode, cla_override, tradeoff_policy)


# ---------------------------------------------------------------------------
# Parametric and inverse helpers (delegated to _parametric / _inverse modules)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# InstructionRecord & compile-mode global state (from _compile_state)
# ---------------------------------------------------------------------------
from .._compile_state import (  # noqa: E402 – after qint import is fine
    CallRecord,  # noqa: F401 – re-exported for tests
    InstructionRecord,  # noqa: F401 – re-exported for tests
    _record_call,  # noqa: F401 – re-exported for tests
)

# ---------------------------------------------------------------------------
# CompiledFunc, compile decorator, inverse classes
# ---------------------------------------------------------------------------
from ._func import CompiledFunc as CompiledFunc  # noqa: E402
from ._func import compile as compile  # noqa: E402
from ._inverse import _adjoint_gate as _adjoint_gate  # noqa: E402, F401
from ._inverse import _inverse_gate_list as _inverse_gate_list  # noqa: E402, F401
from ._inverse import _InverseProxy as _InverseProxy  # noqa: E402

# Backward-compatible aliases
_AncillaInverseProxy = _InverseProxy  # noqa: E402
_InverseCompiledFunc = _InverseProxy  # noqa: E402

# ---------------------------------------------------------------------------
# IR execution, DAG building, and call record replay (delegated to _ir module)
# ---------------------------------------------------------------------------
from ._ir import _build_dag_from_ir as _build_dag_from_ir  # noqa: E402, F401
from ._ir import _execute_ir as _execute_ir  # noqa: E402, F401
from ._ir import _replay_call_records as _replay_call_records  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Gate list optimisation helpers (delegated to _optimize module)
# ---------------------------------------------------------------------------
from ._optimize import _derive_controlled_gates as _derive_controlled_gates  # noqa: E402, F401
from ._optimize import _gates_cancel as _gates_cancel  # noqa: E402, F401
from ._optimize import _gates_merge as _gates_merge  # noqa: E402, F401
from ._optimize import _merge_and_optimize as _merge_and_optimize  # noqa: E402, F401
from ._optimize import _merged_gate as _merged_gate  # noqa: E402, F401
from ._optimize import _optimize_gate_list as _optimize_gate_list  # noqa: E402, F401
from ._optimize import _strip_control_qubit as _strip_control_qubit  # noqa: E402, F401
from ._parametric import _apply_angles as _apply_angles  # noqa: E402, F401
from ._parametric import _extract_angles as _extract_angles  # noqa: E402, F401
from ._parametric import _extract_topology as _extract_topology  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Cache registry (global weak-ref registry and clear hook)
# ---------------------------------------------------------------------------
from ._registry import _clear_all_caches as _clear_all_caches  # noqa: E402
from ._registry import _compiled_funcs as _compiled_funcs  # noqa: E402

# ---------------------------------------------------------------------------
# Virtual qubit mapping helpers (delegated to _virtual module)
# ---------------------------------------------------------------------------
from ._virtual import _build_qubit_set_numpy as _build_qubit_set_numpy  # noqa: E402, F401
from ._virtual import _build_return_qarray as _build_return_qarray  # noqa: E402, F401
from ._virtual import _build_return_qint as _build_return_qint  # noqa: E402, F401
from ._virtual import _build_virtual_mapping as _build_virtual_mapping  # noqa: E402, F401
from ._virtual import _get_qarray_qubit_indices as _get_qarray_qubit_indices  # noqa: E402, F401
from ._virtual import _get_qint_qubit_indices as _get_qint_qubit_indices  # noqa: E402, F401
from ._virtual import (  # noqa: E402
    _get_quantum_arg_qubit_indices as _get_quantum_arg_qubit_indices,  # noqa: F401
)
from ._virtual import _get_quantum_arg_width as _get_quantum_arg_width  # noqa: E402, F401
from ._virtual import _input_qubit_key as _input_qubit_key  # noqa: E402, F401
from ._virtual import _remap_gates as _remap_gates  # noqa: E402, F401
