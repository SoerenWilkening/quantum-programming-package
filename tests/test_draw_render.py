"""Tests for the pixel-art circuit renderer (draw.py).

Uses synthetic draw_data dicts to avoid Cython build dependency.
"""

import os
import random
import time
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from quantum_language.draw import (
    BG_COLOR,
    CELL_H,
    CELL_W,
    CTRL_COLOR,
    CTRL_DOT_COLOR,
    DETAIL_CELL,
    GATE_COLORS,
    LABEL_MARGIN,
    WIRE_COLOR,
    draw_circuit,
    render,
    render_detail,
)


def make_draw_data(num_layers, num_qubits, gates=None):
    """Build a synthetic draw_data dict."""
    return {
        "num_layers": num_layers,
        "num_qubits": num_qubits,
        "gates": gates or [],
        "qubit_map": {},
    }


def make_gate(layer, target, gate_type, angle=0.0, controls=None):
    """Build a synthetic gate dict."""
    return {
        "layer": layer,
        "target": target,
        "type": gate_type,
        "angle": angle,
        "controls": controls or [],
    }


class TestEmptyCircuit:
    def test_empty_circuit(self):
        """Empty circuit (0 layers, 0 qubits) returns a 1x1 image."""
        dd = make_draw_data(0, 0)
        img = render(dd)
        assert img.size == (1, 1)
        arr = np.array(img)
        np.testing.assert_array_equal(arr[0, 0], BG_COLOR)


class TestCanvasDimensions:
    def test_canvas_dimensions(self):
        """Canvas size matches num_layers * CELL_W x num_qubits * CELL_H."""
        dd = make_draw_data(5, 3)
        img = render(dd)
        expected_w = 5 * CELL_W  # 15
        expected_h = 3 * CELL_H  # 9
        assert img.size == (expected_w, expected_h)


class TestBackgroundColor:
    def test_background_color(self):
        """Most pixels in a gate-free circuit are BG_COLOR."""
        dd = make_draw_data(5, 3)
        img = render(dd)
        arr = np.array(img)
        bg = np.array(BG_COLOR, dtype=np.uint8)
        bg_mask = np.all(arr == bg, axis=-1)
        # With 3 wires (1px each across 15 cols = 45 wire pixels)
        # Total pixels: 15*9 = 135; wire pixels = 45; BG = 90
        assert bg_mask.sum() > 0.5 * arr.shape[0] * arr.shape[1]


class TestWireRendering:
    def test_wire_rendering(self):
        """Wire lines appear at qubit row centers."""
        dd = make_draw_data(4, 2)
        img = render(dd)
        arr = np.array(img)
        wire_color = np.array(WIRE_COLOR, dtype=np.uint8)

        # Qubit 0 wire at y = CELL_H // 2 = 1
        wire_y0 = CELL_H // 2
        np.testing.assert_array_equal(arr[wire_y0, 0], wire_color)

        # Qubit 1 wire at y = CELL_H + CELL_H // 2 = 4
        wire_y1 = CELL_H + CELL_H // 2
        np.testing.assert_array_equal(arr[wire_y1, 0], wire_color)


class TestSingleQubitGatePosition:
    def test_single_qubit_gate_position(self):
        """H gate at layer=1, target=0 renders 2x2 block at correct position."""
        gate = make_gate(layer=1, target=0, gate_type=4)
        dd = make_draw_data(3, 2, [gate])
        img = render(dd)
        arr = np.array(img)
        expected = np.array(GATE_COLORS[4], dtype=np.uint8)

        gx = 1 * CELL_W  # 3
        gy = 0 * CELL_H  # 0

        # All 4 pixels of the 2x2 block should match
        np.testing.assert_array_equal(arr[gy, gx], expected)
        np.testing.assert_array_equal(arr[gy, gx + 1], expected)
        np.testing.assert_array_equal(arr[gy + 1, gx], expected)
        np.testing.assert_array_equal(arr[gy + 1, gx + 1], expected)


class TestAllGateTypesHaveColors:
    def test_all_gate_types_have_colors(self):
        """All 10 gate types (0-9) render with non-background color."""
        bg = np.array(BG_COLOR, dtype=np.uint8)
        gates = [make_gate(layer=i, target=0, gate_type=i) for i in range(10)]
        dd = make_draw_data(10, 1, gates)
        img = render(dd)
        arr = np.array(img)

        for gate_type in range(10):
            gx = gate_type * CELL_W
            gy = 0
            pixel = arr[gy, gx]
            # Gate pixel should NOT be background
            assert not np.array_equal(pixel, bg), (
                f"Gate type {gate_type} at ({gy},{gx}) is still BG_COLOR"
            )
            # Should match expected color
            expected = np.array(GATE_COLORS[gate_type], dtype=np.uint8)
            np.testing.assert_array_equal(pixel, expected)


class TestMeasurementCheckerboard:
    def test_measurement_checkerboard(self):
        """Measurement gate (type=9) renders checkerboard, not solid block."""
        gate = make_gate(layer=0, target=0, gate_type=9)
        dd = make_draw_data(1, 1, [gate])
        img = render(dd)
        arr = np.array(img)

        m_color = np.array(GATE_COLORS[9], dtype=np.uint8)
        bg = np.array(BG_COLOR, dtype=np.uint8)

        # Checkerboard: (0,0) and (1,1) are measurement color
        np.testing.assert_array_equal(arr[0, 0], m_color)
        np.testing.assert_array_equal(arr[1, 1], m_color)

        # (0,1) remains background; (1,0) may be wire color since
        # wire_y = CELL_H // 2 = 1 overlaps the gate area
        np.testing.assert_array_equal(arr[0, 1], bg)
        # Verify (1,0) is NOT measurement color (it's wire or bg)
        assert not np.array_equal(arr[1, 0], m_color)


class TestNumpyBulkOperations:
    def test_numpy_bulk_operations(self):
        """Render returns PIL Image in RGB mode with uint8 array."""
        dd = make_draw_data(2, 2)
        img = render(dd)

        assert img.mode == "RGB"
        arr = np.array(img)
        assert arr.dtype == np.uint8
        assert arr.shape == (2 * CELL_H, 2 * CELL_W, 3)


# ---------------------------------------------------------------------------
# Plan 02: Multi-qubit gate rendering tests
# ---------------------------------------------------------------------------


class TestCnotControlLine:
    def test_cnot_control_line(self):
        """CNOT: vertical control line spans from control qubit 0 to target qubit 2."""
        gate = make_gate(layer=0, target=2, gate_type=0, controls=[0])
        dd = make_draw_data(1, 3, [gate])
        img = render(dd)
        arr = np.array(img)
        ctrl_color = np.array(CTRL_COLOR, dtype=np.uint8)

        # Control at qubit 0: wire center y=1, target qubit 2: wire center y=7
        y_ctrl = 0 * CELL_H + CELL_H // 2  # 1
        y_tgt = 2 * CELL_H + CELL_H // 2  # 7
        gx = 0

        # Every pixel in the vertical line from y_ctrl to y_tgt at x=gx
        ctrl_dot_color = np.array(CTRL_DOT_COLOR, dtype=np.uint8)
        for y in range(y_ctrl, y_tgt + 1):
            # Some pixels may be overwritten by gate block or control dot,
            # but the column should have control/dot/gate color (not just wire/bg)
            pixel = arr[y, gx]
            is_ctrl = np.array_equal(pixel, ctrl_color)
            is_dot = np.array_equal(pixel, ctrl_dot_color)
            is_gate = np.array_equal(pixel, np.array(GATE_COLORS[0], dtype=np.uint8))
            assert is_ctrl or is_dot or is_gate, (
                f"Pixel at y={y} x={gx} is {tuple(pixel)}, expected CTRL, DOT or GATE color"
            )


class TestCnotControlDot:
    def test_cnot_control_dot(self):
        """CNOT: control dot at control qubit position has CTRL_DOT_COLOR."""
        gate = make_gate(layer=0, target=2, gate_type=0, controls=[0])
        dd = make_draw_data(1, 3, [gate])
        img = render(dd)
        arr = np.array(img)
        ctrl_dot_color = np.array(CTRL_DOT_COLOR, dtype=np.uint8)

        # Control dot at qubit 0 wire center
        cy = 0 * CELL_H + CELL_H // 2  # 1
        cx = 0
        np.testing.assert_array_equal(arr[cy, cx], ctrl_dot_color)

        # Target qubit should have gate color, not control dot
        ty = 2 * CELL_H  # gate block top-left
        tx = 0
        gate_color = np.array(GATE_COLORS[0], dtype=np.uint8)
        np.testing.assert_array_equal(arr[ty, tx], gate_color)


class TestCcxTwoControls:
    def test_ccx_two_controls(self):
        """CCX: control line spans qubit 0 to qubit 2, dots at qubits 0 and 1."""
        gate = make_gate(layer=0, target=2, gate_type=0, controls=[0, 1])
        dd = make_draw_data(1, 3, [gate])
        img = render(dd)
        arr = np.array(img)
        ctrl_dot_color = np.array(CTRL_DOT_COLOR, dtype=np.uint8)

        # Control dots at qubit 0 and qubit 1
        for q in [0, 1]:
            cy = q * CELL_H + CELL_H // 2
            np.testing.assert_array_equal(arr[cy, 0], ctrl_dot_color)

        # Control line spans from qubit 0 (y=1) to qubit 2 (y=7)
        ctrl_color = np.array(CTRL_COLOR, dtype=np.uint8)
        y_min = 0 * CELL_H + CELL_H // 2
        # Check an intermediate pixel (between qubit 0 and 1 wire centers)
        mid_y = y_min + 1
        pixel = arr[mid_y, 0]
        is_ctrl = np.array_equal(pixel, ctrl_color)
        is_dot = np.array_equal(pixel, ctrl_dot_color)
        is_gate = np.array_equal(pixel, np.array(GATE_COLORS[0], dtype=np.uint8))
        assert is_ctrl or is_dot or is_gate, f"Mid-line pixel at y={mid_y} is {tuple(pixel)}"


class TestControlLineColorDistinct:
    def test_control_line_color_distinct_from_wire(self):
        """CTRL_COLOR must be different from WIRE_COLOR."""
        assert CTRL_COLOR != WIRE_COLOR


class TestRenderingOrderGateOverControlLine:
    def test_rendering_order_gate_over_control_line(self):
        """Gate block pixels overlay control line (gates render after control lines)."""
        # CNOT: X gate at target=1, control=0
        gate = make_gate(layer=0, target=1, gate_type=0, controls=[0])
        dd = make_draw_data(1, 2, [gate])
        img = render(dd)
        arr = np.array(img)

        gate_color = np.array(GATE_COLORS[0], dtype=np.uint8)

        # Gate block at target qubit 1: top-left is (gy=3, gx=0)
        gy = 1 * CELL_H  # 3
        gx = 0
        # The 2x2 gate block should show gate color, not control line color
        np.testing.assert_array_equal(arr[gy, gx], gate_color)
        np.testing.assert_array_equal(arr[gy + 1, gx], gate_color)


class TestRenderingOrderDotOverGate:
    def test_rendering_order_dot_over_gate(self):
        """Control dot renders on top of everything (rendered last)."""
        # CNOT with control at qubit 0, target at qubit 1
        gate = make_gate(layer=0, target=1, gate_type=0, controls=[0])
        dd = make_draw_data(1, 2, [gate])
        img = render(dd)
        arr = np.array(img)
        ctrl_dot_color = np.array(CTRL_DOT_COLOR, dtype=np.uint8)

        # Control dot at qubit 0 wire center
        cy = 0 * CELL_H + CELL_H // 2  # 1
        np.testing.assert_array_equal(arr[cy, 0], ctrl_dot_color)


class TestMcxMultipleControls:
    def test_mcx_multiple_controls(self):
        """MCX: gate at target=4, controls=[0,1,3]. Dots at 0,1,3 but NOT at 2."""
        gate = make_gate(layer=0, target=4, gate_type=0, controls=[0, 1, 3])
        dd = make_draw_data(1, 5, [gate])
        img = render(dd)
        arr = np.array(img)
        ctrl_dot_color = np.array(CTRL_DOT_COLOR, dtype=np.uint8)

        # Control dots at qubits 0, 1, 3
        for q in [0, 1, 3]:
            cy = q * CELL_H + CELL_H // 2
            np.testing.assert_array_equal(
                arr[cy, 0],
                ctrl_dot_color,
                err_msg=f"Control dot missing at qubit {q}",
            )

        # Verify the control line spans the full range
        ctrl_color = np.array(CTRL_COLOR, dtype=np.uint8)
        y_min = 0 * CELL_H + CELL_H // 2
        y_max = 4 * CELL_H + CELL_H // 2
        for y in range(y_min, y_max + 1):
            pixel = arr[y, 0]
            is_ctrl = np.array_equal(pixel, ctrl_color)
            is_dot = np.array_equal(pixel, ctrl_dot_color)
            is_gate = np.array_equal(pixel, np.array(GATE_COLORS[0], dtype=np.uint8))
            assert is_ctrl or is_dot or is_gate, (
                f"Pixel at y={y} should be CTRL, DOT or GATE color, got {tuple(pixel)}"
            )


# ---------------------------------------------------------------------------
# Plan 03: Scale tests and integration test
# ---------------------------------------------------------------------------


def _make_scale_draw_data(
    num_qubits=200,
    num_layers=10000,
    num_gates=10000,
    include_controls=False,
    num_controlled=0,
    seed=42,
):
    """Build a large synthetic draw_data dict for scale testing."""
    random.seed(seed)
    gates = []
    for i in range(num_gates):
        layer = random.randint(0, num_layers - 1)
        target = random.randint(0, num_qubits - 1)
        gate_type = random.randint(0, 9)
        controls = []
        if include_controls and i < num_controlled:
            # Pick a control qubit different from target
            ctrl = random.randint(0, num_qubits - 2)
            if ctrl >= target:
                ctrl += 1
            controls = [ctrl]
        gates.append(make_gate(layer=layer, target=target, gate_type=gate_type, controls=controls))
    return make_draw_data(num_layers, num_qubits, gates)


class TestScale200Qubits10kGates:
    def test_scale_200_qubits_10k_gates(self):
        """200 qubits x 10,000 gates renders successfully with correct dimensions."""
        data = _make_scale_draw_data()
        img = render(data)
        assert img is not None
        expected_w = 10000 * CELL_W  # 30000
        expected_h = 200 * CELL_H  # 600
        assert img.size == (expected_w, expected_h)
        assert img.mode == "RGB"


class TestScale200QubitsWithControls:
    def test_scale_200_qubits_with_controls(self):
        """200 qubits x 10,000 gates with 1000 CNOTs renders correctly."""
        data = _make_scale_draw_data(include_controls=True, num_controlled=1000)
        img = render(data)
        assert img is not None
        expected_w = 10000 * CELL_W
        expected_h = 200 * CELL_H
        assert img.size == (expected_w, expected_h)
        assert img.mode == "RGB"


class TestScaleMemoryReasonable:
    def test_scale_memory_reasonable(self):
        """Rendered image memory is ~54 MB (no bloat from temporaries)."""
        data = _make_scale_draw_data()
        img = render(data)
        arr = np.array(img)
        actual_bytes = arr.nbytes
        expected_bytes = 30000 * 600 * 3  # 54,000,000
        # Allow 10% tolerance
        assert abs(actual_bytes - expected_bytes) < expected_bytes * 0.10, (
            f"Memory {actual_bytes} bytes deviates >10% from expected {expected_bytes}"
        )


class TestScaleRenderingTime:
    def test_scale_rendering_time(self):
        """200 qubits x 10,000 gates renders in under 30 seconds."""
        data = _make_scale_draw_data()
        start = time.time()
        img = render(data)
        elapsed = time.time() - start
        assert img is not None
        assert elapsed < 30.0, f"Rendering took {elapsed:.1f}s, expected < 30s"


class TestScalePngSave:
    def test_scale_png_save(self):
        """Large rendered image saves to PNG file with non-zero size."""
        tmp_path = "/tmp/test_scale_circuit.png"
        try:
            data = _make_scale_draw_data()
            img = render(data)
            img.save(tmp_path)
            assert os.path.exists(tmp_path)
            assert os.path.getsize(tmp_path) > 0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestIntegrationRealCircuit:
    @pytest.mark.integration
    def test_integration_real_circuit(self):
        """Real circuit via draw_data() integration produces valid image."""
        try:
            import quantum_language as ql
        except ImportError:
            pytest.skip("quantum_language package not available")
        try:
            # Verify Cython extension is available
            from quantum_language import _core  # noqa: F401
        except ImportError:
            pytest.skip("Cython _core extension not built")

        tmp_path = "/tmp/test_integration_circuit.png"
        try:
            c = ql.circuit()
            a = ql.qint(0, width=3)
            b = ql.qint(0, width=3)
            a += b
            data = c.draw_data()
            img = render(data)
            assert img is not None
            assert img.size[0] > 0
            assert img.size[1] > 0
            assert img.mode == "RGB"
            img.save(tmp_path)
            assert os.path.exists(tmp_path)
            assert os.path.getsize(tmp_path) > 0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# ---------------------------------------------------------------------------
# Plan 47-01: Detail mode rendering tests
# ---------------------------------------------------------------------------


class TestDetailCanvasDimensions:
    def test_detail_canvas_dimensions(self):
        """Canvas size is LABEL_MARGIN + num_layers * DETAIL_CELL wide, num_qubits * DETAIL_CELL tall."""
        dd = make_draw_data(5, 3)
        img = render_detail(dd)
        expected_w = LABEL_MARGIN + 5 * DETAIL_CELL
        expected_h = 3 * DETAIL_CELL
        assert img.size == (expected_w, expected_h)


class TestDetailGateBlockPresent:
    def test_detail_gate_block_present(self):
        """H gate at layer=1, target=0 renders visible content at gate center."""
        gate = make_gate(layer=1, target=0, gate_type=4)
        dd = make_draw_data(3, 2, [gate])
        img = render_detail(dd)

        # Gate center pixel
        gx = LABEL_MARGIN + 1 * DETAIL_CELL + DETAIL_CELL // 2
        gy = 0 * DETAIL_CELL + DETAIL_CELL // 2
        pixel = img.getpixel((gx, gy))
        assert pixel != BG_COLOR, f"Gate center pixel is BG_COLOR: {pixel}"


class TestDetailMeasurementNotText:
    def test_detail_measurement_not_text(self):
        """Measurement gate renders checkerboard, not white text."""
        gate = make_gate(layer=0, target=0, gate_type=9)
        dd = make_draw_data(1, 1, [gate])
        img = render_detail(dd)

        # Check center of measurement cell - should be checkerboard pattern
        gx = LABEL_MARGIN + DETAIL_CELL // 2
        gy = DETAIL_CELL // 2
        pixel = img.getpixel((gx, gy))
        # Should be either GATE_COLORS[9] or BG_COLOR (checkerboard), NOT white text
        assert pixel != (255, 255, 255), f"Measurement center has white text color: {pixel}"
        assert pixel == GATE_COLORS[9] or pixel == BG_COLOR, (
            f"Measurement center unexpected color: {pixel}"
        )


class TestDetailControlDotCircle:
    def test_detail_control_dot_circle(self):
        """CNOT control dot at control qubit wire center is CTRL_DOT_COLOR."""
        gate = make_gate(layer=1, target=2, gate_type=0, controls=[0])
        dd = make_draw_data(3, 3, [gate])
        img = render_detail(dd)

        # Control dot center at qubit 0 wire center
        cx = LABEL_MARGIN + 1 * DETAIL_CELL + DETAIL_CELL // 2
        cy = 0 * DETAIL_CELL + DETAIL_CELL // 2
        pixel = img.getpixel((cx, cy))
        assert pixel == CTRL_DOT_COLOR, f"Control dot pixel is {pixel}, expected {CTRL_DOT_COLOR}"


class TestDetailQubitLabels:
    def test_detail_qubit_labels(self):
        """Qubit labels render non-BG pixels in left margin for each qubit row."""
        dd = make_draw_data(3, 3)
        img = render_detail(dd)

        for q in range(3):
            # Check a strip in the label area for this qubit row
            row_y_start = q * DETAIL_CELL
            row_y_end = (q + 1) * DETAIL_CELL
            found_label_pixel = False
            for y in range(row_y_start, row_y_end):
                for x in range(LABEL_MARGIN):
                    if img.getpixel((x, y)) != BG_COLOR:
                        found_label_pixel = True
                        break
                if found_label_pixel:
                    break
            assert found_label_pixel, f"No label pixels found for qubit {q}"


class TestDetailWireTerminationAfterMeasurement:
    def test_detail_wire_termination_after_measurement(self):
        """Wire stops after measurement gate - pixel well past measurement is BG."""
        gate = make_gate(layer=2, target=0, gate_type=9)
        dd = make_draw_data(5, 1, [gate])
        img = render_detail(dd)

        # Wire y center for qubit 0
        wire_y = DETAIL_CELL // 2
        # Check pixel at layer 4 (well past measurement at layer 2)
        wire_x = LABEL_MARGIN + 4 * DETAIL_CELL + DETAIL_CELL // 2
        pixel = img.getpixel((wire_x, wire_y))
        assert pixel == BG_COLOR, (
            f"Wire pixel after measurement is {pixel}, expected BG_COLOR {BG_COLOR}"
        )


class TestDetailGateBorder:
    def test_detail_gate_border(self):
        """H gate box edge pixel is not BG_COLOR (border or fill present)."""
        gate = make_gate(layer=0, target=0, gate_type=4)
        dd = make_draw_data(1, 1, [gate])
        img = render_detail(dd)

        # Edge of gate box (gx+1, gy+1 is the top-left of the rectangle)
        gx = LABEL_MARGIN + 1
        gy = 1
        pixel = img.getpixel((gx, gy))
        assert pixel != BG_COLOR, f"Gate border/fill pixel at ({gx},{gy}) is BG_COLOR: {pixel}"


class TestDetailEmptyCircuit:
    def test_detail_empty_circuit(self):
        """Empty circuit in detail mode returns 1x1 image."""
        dd = make_draw_data(0, 0)
        img = render_detail(dd)
        assert img.size == (1, 1)


# ---------------------------------------------------------------------------
# Plan 47-02: Auto-zoom and public API tests
# ---------------------------------------------------------------------------


def _mock_circuit(num_layers, num_qubits, gates=None):
    """Create a mock circuit object with draw_data() method."""
    mock = MagicMock()
    mock.draw_data.return_value = make_draw_data(num_layers, num_qubits, gates)
    return mock


class TestAutoZoomSelectsDetail:
    def test_auto_zoom_selects_detail(self):
        """Small circuit (10 qubits, 50 layers) auto-selects detail mode."""
        circuit = _mock_circuit(50, 10)
        img = draw_circuit(circuit)
        expected_w = LABEL_MARGIN + 50 * DETAIL_CELL
        expected_h = 10 * DETAIL_CELL
        assert img.size == (expected_w, expected_h)


class TestAutoZoomSelectsOverview:
    def test_auto_zoom_selects_overview(self):
        """Large circuit (50 qubits, 500 layers) auto-selects overview mode."""
        circuit = _mock_circuit(500, 50)
        img = draw_circuit(circuit)
        expected_w = 500 * CELL_W
        expected_h = 50 * CELL_H
        assert img.size == (expected_w, expected_h)


class TestAutoZoomBoundary:
    def test_one_threshold_exceeded_qubits_only(self):
        """31 qubits but 100 layers -> detail (only one threshold exceeded)."""
        circuit = _mock_circuit(100, 31)
        img = draw_circuit(circuit)
        expected_w = LABEL_MARGIN + 100 * DETAIL_CELL
        expected_h = 31 * DETAIL_CELL
        assert img.size == (expected_w, expected_h)

    def test_one_threshold_exceeded_layers_only(self):
        """20 qubits but 300 layers -> detail (only one threshold exceeded)."""
        circuit = _mock_circuit(300, 20)
        img = draw_circuit(circuit)
        expected_w = LABEL_MARGIN + 300 * DETAIL_CELL
        expected_h = 20 * DETAIL_CELL
        assert img.size == (expected_w, expected_h)

    def test_both_thresholds_exceeded(self):
        """31 qubits AND 201 layers -> overview (both exceeded)."""
        circuit = _mock_circuit(201, 31)
        img = draw_circuit(circuit)
        expected_w = 201 * CELL_W
        expected_h = 31 * CELL_H
        assert img.size == (expected_w, expected_h)


class TestModeOverrideOverview:
    def test_mode_override_overview(self):
        """Small circuit with mode='overview' uses overview mode."""
        circuit = _mock_circuit(50, 10)
        img = draw_circuit(circuit, mode="overview")
        expected_w = 50 * CELL_W
        expected_h = 10 * CELL_H
        assert img.size == (expected_w, expected_h)


class TestModeOverrideDetail:
    def test_mode_override_detail_large(self):
        """Large circuit with mode='detail' uses detail mode (with warning)."""
        circuit = _mock_circuit(500, 50)
        img = draw_circuit(circuit, mode="detail")
        expected_w = LABEL_MARGIN + 500 * DETAIL_CELL
        expected_h = 50 * DETAIL_CELL
        assert img.size == (expected_w, expected_h)


class TestModeInvalidRaisesError:
    def test_mode_invalid_raises_error(self):
        """Invalid mode raises ValueError."""
        circuit = _mock_circuit(10, 5)
        with pytest.raises(ValueError, match="mode must be 'overview' or 'detail'"):
            draw_circuit(circuit, mode="invalid")


class TestSaveParameter:
    def test_save_parameter(self):
        """save parameter writes image to disk."""
        tmp_path = "/tmp/test_draw_api.png"
        try:
            circuit = _mock_circuit(10, 5)
            img = draw_circuit(circuit, save=tmp_path)
            assert img is not None
            assert os.path.exists(tmp_path)
            assert os.path.getsize(tmp_path) > 0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestDrawCircuitReturnsPilImage:
    def test_draw_circuit_returns_pil_image(self):
        """draw_circuit() returns a PIL Image instance."""
        circuit = _mock_circuit(10, 5)
        img = draw_circuit(circuit)
        assert isinstance(img, Image.Image)


# ---------------------------------------------------------------------------
# Quick-012: Control dot color distinction tests
# ---------------------------------------------------------------------------


class TestControlDotColorDistinct:
    def test_ctrl_dot_color_differs_from_ctrl_color(self):
        """CTRL_DOT_COLOR must differ from CTRL_COLOR."""
        assert CTRL_DOT_COLOR != CTRL_COLOR

    def test_overview_dot_uses_dot_color(self):
        """Overview mode: control dot pixel uses CTRL_DOT_COLOR, line uses CTRL_COLOR."""
        gate = make_gate(layer=0, target=2, gate_type=0, controls=[0])
        dd = make_draw_data(1, 3, [gate])
        img = render(dd)
        arr = np.array(img)

        # Control dot at qubit 0 wire center (y=1, x=0)
        cy = 0 * CELL_H + CELL_H // 2
        np.testing.assert_array_equal(arr[cy, 0], np.array(CTRL_DOT_COLOR, dtype=np.uint8))

        # A pixel on the control line between control and target (e.g. y=2)
        # should be CTRL_COLOR (not dot color)
        line_y = cy + 1
        np.testing.assert_array_equal(arr[line_y, 0], np.array(CTRL_COLOR, dtype=np.uint8))

    def test_detail_dot_uses_dot_color(self):
        """Detail mode: control dot center pixel uses CTRL_DOT_COLOR."""
        gate = make_gate(layer=1, target=2, gate_type=0, controls=[0])
        dd = make_draw_data(3, 3, [gate])
        img = render_detail(dd)

        # Control dot center at qubit 0 wire center
        cx = LABEL_MARGIN + 1 * DETAIL_CELL + DETAIL_CELL // 2
        cy = 0 * DETAIL_CELL + DETAIL_CELL // 2
        pixel = img.getpixel((cx, cy))
        assert pixel == CTRL_DOT_COLOR, f"Detail dot pixel is {pixel}, expected {CTRL_DOT_COLOR}"


# ---------------------------------------------------------------------------
# Quick-012: Non-overlapping mode tests
# ---------------------------------------------------------------------------


class TestNonOverlappingMode:
    def test_no_overlap_expands_layers(self):
        """Overlapping gates in same layer expand to wider image with overlap=False."""
        # Gate A: target=0, controls=[2] -> span [0,2]
        # Gate B: target=1, no controls -> span [1,1] (within A's span)
        gate_a = make_gate(layer=0, target=0, gate_type=0, controls=[2])
        gate_b = make_gate(layer=0, target=1, gate_type=4, controls=[])
        dd = make_draw_data(1, 3, [gate_a, gate_b])
        img = render(dd, overlap=False)
        # Should be wider than 1 layer since overlap forced expansion
        assert img.size[0] > 1 * CELL_W, (
            f"Image width {img.size[0]} should be > {1 * CELL_W} after expansion"
        )

    def test_no_overlap_no_change_when_no_conflicts(self):
        """Non-conflicting gates in same layer: no expansion needed."""
        gate_a = make_gate(layer=0, target=0, gate_type=0, controls=[])
        gate_b = make_gate(layer=0, target=3, gate_type=4, controls=[])
        dd = make_draw_data(1, 4, [gate_a, gate_b])
        img_overlap = render(dd, overlap=True)
        img_no_overlap = render(dd, overlap=False)
        # Width should be the same (1 layer, no expansion)
        assert img_no_overlap.size[0] == img_overlap.size[0]

    def test_overlap_true_is_default(self):
        """Default overlap=True: overlapping gates stay in same layer (no expansion)."""
        gate_a = make_gate(layer=0, target=0, gate_type=0, controls=[2])
        gate_b = make_gate(layer=0, target=1, gate_type=4, controls=[])
        dd = make_draw_data(1, 3, [gate_a, gate_b])
        img = render(dd)  # default overlap=True
        # Should be exactly 1 layer wide (no expansion)
        assert img.size[0] == 1 * CELL_W

    def test_draw_circuit_passes_overlap(self):
        """draw_circuit(overlap=False) produces wider image than overlap=True."""
        gate_a = make_gate(layer=0, target=0, gate_type=0, controls=[2])
        gate_b = make_gate(layer=0, target=1, gate_type=4, controls=[])
        gates = [gate_a, gate_b]
        circuit_overlap = _mock_circuit(1, 3, gates)
        circuit_no_overlap = _mock_circuit(1, 3, gates)
        img_overlap = draw_circuit(circuit_overlap, mode="overview", overlap=True)
        img_no_overlap = draw_circuit(circuit_no_overlap, mode="overview", overlap=False)
        assert img_no_overlap.size[0] > img_overlap.size[0], (
            f"overlap=False width {img_no_overlap.size[0]} should be > "
            f"overlap=True width {img_overlap.size[0]}"
        )
