"""Pixel-art quantum circuit renderer.

Converts a draw_data dict (from _core.draw_data()) into a PIL Image
using NumPy bulk array operations for efficient rendering.

Usage
-----
>>> from quantum_language.draw import render
>>> img = render(draw_data_dict)
>>> img.save("circuit.png")
"""

import numpy as np
from PIL import Image

# Layout constants (pixels per cell: 2px gate + 1px gap)
CELL_W = 3
CELL_H = 3

# Colors (RGB tuples)
BG_COLOR = (20, 20, 30)
WIRE_COLOR = (60, 60, 80)
CTRL_COLOR = (255, 255, 100)  # Used in plan 02 for control lines

# Gate type -> RGB color mapping
# 0=X, 1=Y, 2=Z, 3=R, 4=H, 5=Rx, 6=Ry, 7=Rz, 8=P, 9=M
GATE_COLORS = {
    0: (180, 130, 200),  # X  - Pauli purple
    1: (180, 130, 200),  # Y  - Pauli purple
    2: (180, 130, 200),  # Z  - Pauli purple
    3: (130, 180, 200),  # R  - rotation cyan
    4: (200, 180, 100),  # H  - Hadamard warm yellow
    5: (130, 180, 200),  # Rx - rotation cyan
    6: (130, 180, 200),  # Ry - rotation cyan
    7: (130, 180, 200),  # Rz - rotation cyan
    8: (100, 200, 150),  # P  - phase green
    9: (200, 100, 100),  # M  - measurement red
}

# Default color for unknown gate types
_DEFAULT_GATE_COLOR = (150, 150, 150)


def render(draw_data, cell_size=3):
    """Render a draw_data dict into a PIL Image.

    Parameters
    ----------
    draw_data : dict
        Dictionary with keys:
        - num_layers : int
        - num_qubits : int
        - gates : list of gate dicts (layer, target, type, angle, controls)
        - qubit_map : dict
    cell_size : int, optional
        Pixels per cell dimension (default 3). Both width and height
        use this value.

    Returns
    -------
    PIL.Image.Image
        RGB image of the rendered circuit.
    """
    num_layers = draw_data.get("num_layers", 0)
    num_qubits = draw_data.get("num_qubits", 0)

    # Handle empty circuit
    if num_layers == 0 or num_qubits == 0:
        return Image.fromarray(np.full((1, 1, 3), BG_COLOR, dtype=np.uint8), "RGB")

    cell_w = cell_size
    cell_h = cell_size
    width = num_layers * cell_w
    height = num_qubits * cell_h

    # Allocate canvas with background color
    canvas = np.full((height, width, 3), BG_COLOR, dtype=np.uint8)

    # --- Draw horizontal wires ---
    for q in range(num_qubits):
        wire_y = q * cell_h + cell_h // 2
        canvas[wire_y, :] = WIRE_COLOR

    # --- Draw control lines (plan 02) ---
    # Placeholder for multi-qubit control line rendering

    # --- Draw gate blocks ---
    for gate in draw_data.get("gates", []):
        gx = gate["layer"] * cell_w
        gy = gate["target"] * cell_h
        gate_type = gate["type"]
        color = GATE_COLORS.get(gate_type, _DEFAULT_GATE_COLOR)

        if gate_type == 9:
            # Measurement: checkerboard pattern (2x2 with alternating pixels)
            canvas[gy, gx] = color
            canvas[gy + 1, gx + 1] = color
            # (gy, gx+1) and (gy+1, gx) remain BG_COLOR
        else:
            # Standard gate: solid 2x2 block
            canvas[gy : gy + 2, gx : gx + 2] = color

    # --- Draw control dots (plan 02) ---
    # Placeholder for control dot rendering

    return Image.fromarray(canvas, "RGB")
