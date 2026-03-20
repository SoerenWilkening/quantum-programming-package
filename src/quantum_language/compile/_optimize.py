"""Gate list optimisation and controlled-variant helpers.

Pure functions for adjacent gate cancellation, rotation merging, and
controlled gate derivation.  No dependency on ``CompiledFunc``.
"""

from ._block import _M, _ROTATION_GATES, _SELF_ADJOINT


# ---------------------------------------------------------------------------
# Gate list optimisation helpers
# ---------------------------------------------------------------------------
def _gates_cancel(g1, g2):
    """Return True if *g1* followed by *g2* is identity (they cancel).

    Rules
    -----
    * Must have identical target, num_controls, controls and type.
    * Self-adjoint gates (X, Y, Z, H) always cancel with themselves.
    * Rotation gates (P, Rx, Ry, Rz, R) cancel when their angles sum to
      zero within floating-point tolerance.
    * Measurement gates never cancel.
    """
    if g1["type"] != g2["type"]:
        return False
    if g1["target"] != g2["target"]:
        return False
    if g1["num_controls"] != g2["num_controls"]:
        return False
    if g1["controls"] != g2["controls"]:
        return False

    gt = g1["type"]
    if gt == _M:
        return False
    if gt in _SELF_ADJOINT:
        return True
    if gt in _ROTATION_GATES:
        return abs(g1["angle"] + g2["angle"]) < 1e-12
    return False


def _gates_merge(g1, g2):
    """Return True if *g1* and *g2* can be merged into a single gate.

    Only rotation gates on the same qubit (same target, controls, type) are
    mergeable.  Self-adjoint and measurement gates cannot merge (they would
    cancel, not merge).
    """
    if g1["type"] != g2["type"]:
        return False
    if g1["target"] != g2["target"]:
        return False
    if g1["num_controls"] != g2["num_controls"]:
        return False
    if g1["controls"] != g2["controls"]:
        return False

    gt = g1["type"]
    if gt in _ROTATION_GATES:
        # Cancellation is handled by _gates_cancel; here we only say
        # "yes these can be combined".  The caller uses _merged_gate
        # which may still return None when the sum is zero.
        return True
    return False


def _merged_gate(g1, g2):
    """Return a new gate dict with merged angle, or *None* if result is zero.

    Copies all fields from *g1* and replaces the angle with the sum.
    """
    new_angle = g1["angle"] + g2["angle"]
    if abs(new_angle) < 1e-12:
        return None  # gate disappears
    merged = dict(g1)
    merged["angle"] = new_angle
    return merged


def _optimize_gate_list(gates):
    """Optimise a gate list with multi-pass adjacent cancellation / merge.

    Each pass scans left-to-right, cancelling adjacent inverse pairs and
    merging consecutive rotations on the same qubit.  Passes repeat until
    the list stops shrinking or *max_passes* is reached.
    """
    prev_count = len(gates) + 1
    optimized = list(gates)
    max_passes = 10  # safety limit
    passes = 0
    while len(optimized) < prev_count and passes < max_passes:
        prev_count = len(optimized)
        passes += 1
        result = []
        for gate in optimized:
            if result and _gates_cancel(result[-1], gate):
                result.pop()  # Adjacent inverse cancellation
            elif result and _gates_merge(result[-1], gate):
                merged = _merged_gate(result[-1], gate)
                if merged is None:
                    result.pop()  # Merged to zero
                else:
                    result[-1] = merged
            else:
                result.append(gate)
        optimized = result
    return optimized


# ---------------------------------------------------------------------------
# Merge-and-optimize (selective sequence merging helper)
# ---------------------------------------------------------------------------


def _merge_and_optimize(blocks_with_mappings, optimize=True):
    """Concatenate gate lists from multiple blocks in physical qubit space and optimize.

    Parameters
    ----------
    blocks_with_mappings : list of (CompiledBlock, dict)
        Each tuple is (block, virtual_to_real_mapping) in temporal call order.
    optimize : bool
        Whether to run _optimize_gate_list on the concatenated result.

    Returns
    -------
    tuple of (list[dict], int)
        (optimized_gates, original_gate_count)
    """
    merged_gates = []
    for block, v2r in blocks_with_mappings:
        for g in block.gates:
            pg = dict(g)
            pg["target"] = v2r[g["target"]]
            if g.get("num_controls", 0) > 0 and "controls" in g:
                pg["controls"] = [v2r[c] for c in g["controls"]]
            merged_gates.append(pg)
    original_count = len(merged_gates)
    if optimize and merged_gates:
        try:
            merged_gates = _optimize_gate_list(merged_gates)
        except Exception:
            pass
    return merged_gates, original_count


# ---------------------------------------------------------------------------
# Controlled variant derivation
# ---------------------------------------------------------------------------
def _derive_controlled_gates(gates):
    """Add virtual index 0 as a control qubit to every gate.

    Each gate's ``num_controls`` is incremented by 1 and index 0
    (the reserved control slot) is prepended to the ``controls`` list.
    """
    controlled = []
    for g in gates:
        cg = dict(g)
        cg["num_controls"] = g["num_controls"] + 1
        cg["controls"] = [0] + list(g["controls"])
        controlled.append(cg)
    return controlled


def _strip_control_qubit(gates, control_qubit):
    """Remove a physical control qubit from each gate's controls list.

    Used to normalise controlled gates back to uncontrolled form for
    the gate-level cache.  Each gate's ``num_controls`` is decremented
    by 1 and *control_qubit* is removed from ``controls``.  Gates that
    do not reference *control_qubit* in their controls are left unchanged.

    Parameters
    ----------
    gates : list[dict]
        Raw gate dicts from ``extract_gate_range`` (physical qubit indices).
    control_qubit : int
        Physical qubit index of the control to strip.

    Returns
    -------
    list[dict]
        Gate dicts with the control qubit removed.
    """
    stripped = []
    for g in gates:
        if control_qubit in g.get("controls", []):
            sg = dict(g)
            new_controls = [c for c in g["controls"] if c != control_qubit]
            sg["controls"] = new_controls
            sg["num_controls"] = len(new_controls)
            stripped.append(sg)
        else:
            stripped.append(g)
    return stripped
