"""Internal gate primitives for Grover's algorithm.

This module provides low-level gate emission functions used by:
- qint.branch() / qbool.branch() for Ry rotations
- Diffusion operator (Phase 78) for MCZ pattern

Not part of public API - users should use branch() method instead.
"""

cimport cython
from libc.string cimport memset
from libc.stdlib cimport malloc, free

from ._core cimport (
    circuit_t, circuit_s, gate_t,
    add_gate,
)
from ._core import (
    _get_circuit, _get_controlled, _get_control_bool,
)

# C declarations from gate.h
cdef extern from "gate.h":
    void h(gate_t *g, unsigned int target)
    void z(gate_t *g, unsigned int target)
    void ry(gate_t *g, unsigned int target, double angle)
    void x(gate_t *g, unsigned int target)
    void cx(gate_t *g, unsigned int target, unsigned int control)
    void ch(gate_t *g, unsigned int target, unsigned int control)
    void cz(gate_t *g, unsigned int target, unsigned int control)
    void cry(gate_t *g, unsigned int target, unsigned int control, double angle)
    void mcz(gate_t *g, unsigned int target, unsigned int *controls, int n_controls)
    void p(gate_t *g, unsigned int target, double angle)
    void cp(gate_t *g, unsigned int target, unsigned int control, double angle)
    void ccx(gate_t *g, unsigned int target, unsigned int control1, unsigned int control2)


cpdef void emit_ry(unsigned int target, double angle):
    """Emit Ry gate to circuit (internal use only).

    Handles controlled context automatically - if inside a `with qbool:` block,
    emits CRy instead of Ry.
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()

    memset(&g, 0, sizeof(gate_t))

    if _get_controlled():
        # Inside controlled context - emit CRy
        ctrl = _get_control_bool()
        # qint stores qubits right-aligned, control qubit is at qubits[63]
        # Use Python-level attribute access (no C-level cast needed)
        cry(&g, target, ctrl.qubits[63], angle)
    else:
        ry(&g, target, angle)

    add_gate(circ, &g)


cpdef void emit_x(unsigned int target):
    """Emit X gate to circuit (internal use only).

    Handles controlled context automatically - if inside a `with qbool:` block,
    emits CX instead of X.
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()

    memset(&g, 0, sizeof(gate_t))

    if _get_controlled():
        ctrl = _get_control_bool()
        cx(&g, target, ctrl.qubits[63])
    else:
        x(&g, target)

    add_gate(circ, &g)


cpdef void emit_h(unsigned int target):
    """Emit H gate to circuit (internal use only)."""
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()

    memset(&g, 0, sizeof(gate_t))

    if _get_controlled():
        ctrl = _get_control_bool()
        # Use Python-level attribute access (no C-level cast needed)
        ch(&g, target, ctrl.qubits[63])
    else:
        h(&g, target)

    add_gate(circ, &g)


cpdef void emit_z(unsigned int target):
    """Emit Z gate to circuit (internal use only)."""
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()

    memset(&g, 0, sizeof(gate_t))

    if _get_controlled():
        ctrl = _get_control_bool()
        # Use Python-level attribute access (no C-level cast needed)
        cz(&g, target, ctrl.qubits[63])
    else:
        z(&g, target)

    add_gate(circ, &g)


cpdef void emit_mcz(unsigned int target, list controls):
    """Emit multi-controlled Z gate to circuit (internal use only).

    Used by diffusion operator in Phase 78. Applies Z to target when
    all control qubits are |1>.

    Parameters
    ----------
    target : unsigned int
        Target qubit index for Z gate
    controls : list
        List of control qubit indices (unsigned int)

    Notes
    -----
    For n_controls > 2 (MAXCONTROLS), uses heap-allocated control array in C.
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    cdef int n_controls = len(controls)
    cdef unsigned int* ctrl_array
    cdef int i

    memset(&g, 0, sizeof(gate_t))

    if n_controls == 0:
        # No controls - just emit Z
        z(&g, target)
    elif n_controls == 1:
        # Single control - emit CZ
        cz(&g, target, controls[0])
    else:
        # Multi-control - use mcz
        ctrl_array = <unsigned int*>malloc(n_controls * sizeof(unsigned int))
        if ctrl_array == NULL:
            raise MemoryError("Failed to allocate control array for MCZ")
        for i in range(n_controls):
            ctrl_array[i] = controls[i]
        mcz(&g, target, ctrl_array, n_controls)
        # mcz copies controls into gate_t, so we can free here
        free(ctrl_array)

    add_gate(circ, &g)


cpdef void emit_p_raw(unsigned int target, double angle):
    """Emit P(angle) gate to circuit WITHOUT auto-control context.

    Unlike emit_p, this does NOT check _get_controlled() and always
    emits a plain P gate. Used by _PhaseProxy.__iadd__ which handles
    the controlled context itself -- calling emit_p from inside a
    controlled context would double-apply the control, producing
    cp(q[n], q[n]) instead of p(q[n]).

    Parameters
    ----------
    target : unsigned int
        Target qubit index for P gate
    angle : double
        Phase angle in radians
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()

    memset(&g, 0, sizeof(gate_t))
    p(&g, target, angle)
    add_gate(circ, &g)


cpdef void emit_p(unsigned int target, double angle):
    """Emit P(angle) gate to circuit (internal use only).

    Handles controlled context automatically - if inside a `with qbool:` block,
    emits CP instead of P.

    Parameters
    ----------
    target : unsigned int
        Target qubit index for P gate
    angle : double
        Phase angle in radians
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()

    memset(&g, 0, sizeof(gate_t))

    if _get_controlled():
        ctrl = _get_control_bool()
        cp(&g, target, ctrl.qubits[63], angle)
    else:
        p(&g, target, angle)

    add_gate(circ, &g)


cpdef void emit_ccx(unsigned int target, unsigned int ctrl1, unsigned int ctrl2):
    """Emit Toffoli (CCX) gate directly to circuit.

    Does NOT check controlled context -- raw gate for internal control stack use.

    Parameters
    ----------
    target : unsigned int
        Target qubit index
    ctrl1 : unsigned int
        First control qubit index
    ctrl2 : unsigned int
        Second control qubit index
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    memset(&g, 0, sizeof(gate_t))
    ccx(&g, target, ctrl1, ctrl2)
    add_gate(circ, &g)


def _toffoli_and(ctrl1_qubit, ctrl2_qubit):
    """Compute AND of two control qubits into a fresh ancilla.

    Allocates a qbool for the AND result and applies CCX(ctrl1, ctrl2, ancilla).
    Returns the qbool ancilla.

    Parameters
    ----------
    ctrl1_qubit : int
        First control qubit index
    ctrl2_qubit : int
        Second control qubit index

    Returns
    -------
    qbool
        Freshly allocated AND-ancilla qbool with CCX applied.
    """
    from .qbool import qbool as _qbool
    from .call_graph import record_operation as _record_op
    ancilla = _qbool()
    ancilla_qubit = ancilla.qubits[63]
    emit_ccx(ancilla_qubit, ctrl1_qubit, ctrl2_qubit)
    # AND = 1 CCX (Toffoli) = 1 gate, 1 depth, 7 T-gates.
    # emit_ccx uses add_gate (not run_instruction) so get_gate_count()
    # does not see it — hardcode the known cost.
    _record_op(
        "and",
        (ancilla_qubit, ctrl1_qubit, ctrl2_qubit),
        gate_count=1,
        controlled=False,
        depth=1,
        t_count=7,
    )
    return ancilla


def _uncompute_toffoli_and(ancilla, ctrl1_qubit, ctrl2_qubit):
    """Uncompute AND-ancilla via reverse CCX and deallocate.

    Parameters
    ----------
    ancilla : qbool
        The AND-ancilla to uncompute (from _toffoli_and).
    ctrl1_qubit : int
        First control qubit index
    ctrl2_qubit : int
        Second control qubit index
    """
    from .call_graph import record_operation as _record_op
    ancilla_qubit = ancilla.qubits[63]
    emit_ccx(ancilla_qubit, ctrl1_qubit, ctrl2_qubit)  # CCX is self-adjoint
    _record_op(
        "and",
        (ancilla_qubit, ctrl1_qubit, ctrl2_qubit),
        gate_count=1,
        controlled=False,
        invert=True,
        depth=1,
        t_count=7,
    )
    ancilla._is_uncomputed = True  # Prevent __del__ double-uncomputation
    from ._core import _deallocate_qubits
    _deallocate_qubits(ancilla.allocated_start, 1)
    ancilla.allocated_qubits = False
