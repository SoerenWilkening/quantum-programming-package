"""Pixel-art quantum circuit renderer.

Converts a draw_data dict (from _core.draw_data()) into a PIL Image
using NumPy bulk array operations for efficient rendering.

Three entry points:
- render()        : Overview mode (3px cells, pixel-art, scales to 200+ qubits)
- render_detail() : Detail mode (12px cells, text labels, for <= 30 qubits)
- draw_circuit()  : Public API with auto-zoom, mode override, and save parameter

Usage
-----
>>> from quantum_language.draw import render, render_detail, draw_circuit
>>> img = render(draw_data_dict)          # overview
>>> img = render_detail(draw_data_dict)   # detail with labels
>>> img = draw_circuit(circuit_obj)       # auto-zoom with smart defaults
>>> img.save("circuit.png")
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Layout constants (pixels per cell: 2px gate + 1px gap)
CELL_W = 3
CELL_H = 3

# Auto-zoom thresholds: overview only when BOTH exceeded
AUTO_DETAIL_MAX_QUBITS = 30
AUTO_DETAIL_MAX_LAYERS = 200

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

    # --- Draw control lines ---
    for gate in draw_data.get("gates", []):
        controls = gate.get("controls", [])
        if not controls:
            continue
        gx = gate["layer"] * cell_w
        all_qubits = [gate["target"]] + list(controls)
        y_min = min(all_qubits) * cell_h + cell_h // 2
        y_max = max(all_qubits) * cell_h + cell_h // 2
        canvas[y_min : y_max + 1, gx] = CTRL_COLOR

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

    # --- Draw control dots (rendered last so always visible) ---
    for gate in draw_data.get("gates", []):
        controls = gate.get("controls", [])
        if not controls:
            continue
        gx = gate["layer"] * cell_w
        for ctrl in controls:
            cy = ctrl * cell_h + cell_h // 2
            canvas[cy, gx] = CTRL_COLOR

    return Image.fromarray(canvas, "RGB")


# ---------------------------------------------------------------------------
# Detail mode constants (12px cells with text labels)
# ---------------------------------------------------------------------------

DETAIL_CELL = 12
LABEL_MARGIN = 40

# Gate type integer -> text label (measurement excluded: uses checkerboard)
GATE_LABELS = {
    0: "X",
    1: "Y",
    2: "Z",
    3: "R",
    4: "H",
    5: "Rx",
    6: "Ry",
    7: "Rz",
    8: "P",
}

BORDER_COLOR = (80, 80, 100)


def render_detail(draw_data):
    """Render a draw_data dict into a PIL Image at detail zoom level.

    Detail mode uses 12px cells with readable text labels for gate types,
    qubit labels on the left margin, gate box borders, scaled-up measurement
    checkerboard icons, larger control dots, and wire termination after
    measurement gates.

    Parameters
    ----------
    draw_data : dict
        Dictionary with keys: num_layers, num_qubits, gates, qubit_map.

    Returns
    -------
    PIL.Image.Image
        RGB image of the rendered circuit at detail scale.
    """
    num_layers = draw_data.get("num_layers", 0)
    num_qubits = draw_data.get("num_qubits", 0)

    # Handle empty circuit
    if num_layers == 0 or num_qubits == 0:
        return Image.fromarray(np.full((1, 1, 3), BG_COLOR, dtype=np.uint8), "RGB")

    width = LABEL_MARGIN + num_layers * DETAIL_CELL
    height = num_qubits * DETAIL_CELL

    # Create canvas and drawing context
    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=8)

    gates = draw_data.get("gates", [])

    # --- Pre-compute measurement positions ---
    # earliest_meas[qubit] = earliest layer index with a measurement gate
    earliest_meas = {}
    for gate in gates:
        if gate["type"] == 9:
            q = gate["target"]
            layer = gate["layer"]
            if q not in earliest_meas or layer < earliest_meas[q]:
                earliest_meas[q] = layer

    # --- Step 1: Qubit labels ---
    label_color = (200, 200, 200)
    for q in range(num_qubits):
        label = f"q{q}"
        bbox = font.getbbox(label)
        text_h = bbox[3] - bbox[1]
        ty = q * DETAIL_CELL + (DETAIL_CELL - text_h) // 2
        draw.text((2, ty), label, fill=label_color, font=font)

    # --- Step 2: Horizontal wires ---
    for q in range(num_qubits):
        wire_y = q * DETAIL_CELL + DETAIL_CELL // 2
        wire_x_start = LABEL_MARGIN
        if q in earliest_meas:
            # Wire ends at the right edge of the measurement cell
            wire_x_end = LABEL_MARGIN + earliest_meas[q] * DETAIL_CELL + DETAIL_CELL - 1
        else:
            wire_x_end = width - 1
        draw.line([(wire_x_start, wire_y), (wire_x_end, wire_y)], fill=WIRE_COLOR)

    # --- Step 3: Control lines ---
    for gate in gates:
        controls = gate.get("controls", [])
        if not controls:
            continue
        x_center = LABEL_MARGIN + gate["layer"] * DETAIL_CELL + DETAIL_CELL // 2
        all_qubits = [gate["target"]] + list(controls)
        y_min = min(all_qubits) * DETAIL_CELL + DETAIL_CELL // 2
        y_max = max(all_qubits) * DETAIL_CELL + DETAIL_CELL // 2
        draw.line([(x_center, y_min), (x_center, y_max)], fill=CTRL_COLOR)

    # --- Step 4: Gate blocks ---
    for gate in gates:
        gx = LABEL_MARGIN + gate["layer"] * DETAIL_CELL
        gy = gate["target"] * DETAIL_CELL
        gate_type = gate["type"]
        color = GATE_COLORS.get(gate_type, _DEFAULT_GATE_COLOR)

        if gate_type == 9:
            # Measurement: scaled-up checkerboard (2x2 pixel blocks)
            for py in range(DETAIL_CELL):
                for px in range(DETAIL_CELL):
                    # 2x2 block checkerboard
                    block_row = py // 2
                    block_col = px // 2
                    if (block_row + block_col) % 2 == 0:
                        img.putpixel((gx + px, gy + py), color)
                    # else: leave as BG_COLOR
        else:
            # Standard gate: filled rectangle with border
            draw.rectangle(
                [gx + 1, gy + 1, gx + DETAIL_CELL - 2, gy + DETAIL_CELL - 2],
                fill=color,
                outline=BORDER_COLOR,
            )
            # Center text label
            label = GATE_LABELS.get(gate_type, "?")
            bbox = font.getbbox(label)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = gx + (DETAIL_CELL - tw) // 2
            ty = gy + (DETAIL_CELL - th) // 2
            draw.text((tx, ty), label, fill=(255, 255, 255), font=font)

    # --- Step 5: Control dots (filled circles, rendered last) ---
    for gate in gates:
        controls = gate.get("controls", [])
        if not controls:
            continue
        x_center = LABEL_MARGIN + gate["layer"] * DETAIL_CELL + DETAIL_CELL // 2
        for ctrl in controls:
            cy = ctrl * DETAIL_CELL + DETAIL_CELL // 2
            radius = 3
            draw.ellipse(
                [
                    x_center - radius,
                    cy - radius,
                    x_center + radius,
                    cy + radius,
                ],
                fill=CTRL_COLOR,
            )

    return img


# ---------------------------------------------------------------------------
# Public API: draw_circuit() with auto-zoom
# ---------------------------------------------------------------------------


def draw_circuit(circuit, *, mode=None, save=None):
    """Visualize a quantum circuit as a pixel-art image.

    Automatically selects detail or overview mode based on circuit size,
    or allows explicit mode override.

    Parameters
    ----------
    circuit : circuit
        A built quantum circuit object (must have .draw_data() method).
    mode : str, optional
        Zoom mode: ``"overview"`` (compact), ``"detail"`` (readable labels),
        or ``None`` for auto-selection based on circuit size.
    save : str, optional
        If provided, save the image to this file path.

    Returns
    -------
    PIL.Image.Image
        Rendered circuit image.

    Raises
    ------
    ValueError
        If *mode* is not ``"overview"``, ``"detail"``, or ``None``.
    """
    draw_data = circuit.draw_data()
    num_qubits = draw_data.get("num_qubits", 0)
    num_layers = draw_data.get("num_layers", 0)

    if mode is not None:
        # Validate mode
        if mode not in ("overview", "detail"):
            raise ValueError(f"mode must be 'overview' or 'detail', got '{mode}'")
        use_detail = mode == "detail"
        if use_detail and (
            num_qubits > AUTO_DETAIL_MAX_QUBITS or num_layers > AUTO_DETAIL_MAX_LAYERS
        ):
            print(
                f"Warning: detail mode requested for large circuit "
                f"({num_qubits} qubits, {num_layers} layers). "
                f"Rendering may be slow."
            )
    else:
        # Auto-zoom: detail when circuit is small enough on BOTH axes
        use_detail = num_qubits <= AUTO_DETAIL_MAX_QUBITS and num_layers <= AUTO_DETAIL_MAX_LAYERS
        if use_detail:
            print(f"Auto-selected detail mode ({num_qubits} qubits, {num_layers} layers)")
        else:
            print(f"Auto-selected overview mode ({num_qubits} qubits, {num_layers} layers)")

    if use_detail:
        img = render_detail(draw_data)
    else:
        img = render(draw_data)

    if save is not None:
        img.save(save)

    return img
