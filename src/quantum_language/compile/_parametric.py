"""Parametric topology helpers for compiled function caching.

Provides functions to extract and compare gate sequence topology
(structure without angle values) for parametric compilation mode.
When a function's gate topology is invariant across different classical
argument values, only the rotation angles need updating on replay.
"""


def _extract_topology(gates):
    """Extract the structural topology of a gate sequence.

    Returns a tuple of (gate_type, target, controls_tuple, num_controls)
    for each gate, which captures the circuit structure without angle
    values. Two gate sequences with identical topology differ only in
    rotation angles -- safe for parametric replay.

    Parameters
    ----------
    gates : list[dict]
        Virtual gate dicts from a CompiledBlock.

    Returns
    -------
    tuple[tuple]
        Hashable topology signature.
    """
    return tuple((g["type"], g["target"], tuple(g["controls"]), g["num_controls"]) for g in gates)


def _extract_angles(gates):
    """Extract rotation angles from a gate sequence.

    Returns a list of angles (float or None for non-rotation gates)
    preserving gate order. Used to build the parametric replay template.

    Parameters
    ----------
    gates : list[dict]
        Virtual gate dicts from a CompiledBlock.

    Returns
    -------
    list[float | None]
        Angle per gate (None for non-rotation gates).
    """
    return [g.get("angle") for g in gates]


def _apply_angles(template_gates, new_angles):
    """Create fresh gate list by applying new angles to a topology template.

    Parameters
    ----------
    template_gates : list[dict]
        Gate dicts from the cached parametric block (used as template).
    new_angles : list[float | None]
        New angle values from a fresh capture.

    Returns
    -------
    list[dict]
        New gate dicts with updated angles. Non-rotation gates are
        unchanged. Each gate dict is a fresh copy (no mutation).
    """
    result = []
    for g, angle in zip(template_gates, new_angles, strict=False):
        ng = dict(g)
        if angle is not None:
            ng["angle"] = angle
        result.append(ng)
    return result
