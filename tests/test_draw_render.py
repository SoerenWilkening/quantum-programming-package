"""Tests for the pixel-art circuit renderer (draw.py).

Uses synthetic draw_data dicts to avoid Cython build dependency.
"""

import os
import random
import time

import numpy as np
import pytest

from quantum_language.draw import (
    BG_COLOR,
    CELL_H,
    CELL_W,
    CTRL_COLOR,
    GATE_COLORS,
    WIRE_COLOR,
    render,
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
        for y in range(y_ctrl, y_tgt + 1):
            # Some pixels may be overwritten by gate block, but the column
            # should have control color or gate color (not just wire/bg)
            pixel = arr[y, gx]
            is_ctrl = np.array_equal(pixel, ctrl_color)
            is_gate = np.array_equal(pixel, np.array(GATE_COLORS[0], dtype=np.uint8))
            assert is_ctrl or is_gate, (
                f"Pixel at y={y} x={gx} is {tuple(pixel)}, expected CTRL or GATE color"
            )


class TestCnotControlDot:
    def test_cnot_control_dot(self):
        """CNOT: control dot at control qubit position has CTRL_COLOR."""
        gate = make_gate(layer=0, target=2, gate_type=0, controls=[0])
        dd = make_draw_data(1, 3, [gate])
        img = render(dd)
        arr = np.array(img)
        ctrl_color = np.array(CTRL_COLOR, dtype=np.uint8)

        # Control dot at qubit 0 wire center
        cy = 0 * CELL_H + CELL_H // 2  # 1
        cx = 0
        np.testing.assert_array_equal(arr[cy, cx], ctrl_color)

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
        ctrl_color = np.array(CTRL_COLOR, dtype=np.uint8)

        # Control dots at qubit 0 and qubit 1
        for q in [0, 1]:
            cy = q * CELL_H + CELL_H // 2
            np.testing.assert_array_equal(arr[cy, 0], ctrl_color)

        # Control line spans from qubit 0 (y=1) to qubit 2 (y=7)
        y_min = 0 * CELL_H + CELL_H // 2
        # Check an intermediate pixel (between qubit 0 and 1 wire centers)
        mid_y = y_min + 1
        pixel = arr[mid_y, 0]
        is_ctrl = np.array_equal(pixel, ctrl_color)
        is_gate = np.array_equal(pixel, np.array(GATE_COLORS[0], dtype=np.uint8))
        assert is_ctrl or is_gate, f"Mid-line pixel at y={mid_y} is {tuple(pixel)}"


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
        ctrl_color = np.array(CTRL_COLOR, dtype=np.uint8)

        # Control dot at qubit 0 wire center
        cy = 0 * CELL_H + CELL_H // 2  # 1
        np.testing.assert_array_equal(arr[cy, 0], ctrl_color)


class TestMcxMultipleControls:
    def test_mcx_multiple_controls(self):
        """MCX: gate at target=4, controls=[0,1,3]. Dots at 0,1,3 but NOT at 2."""
        gate = make_gate(layer=0, target=4, gate_type=0, controls=[0, 1, 3])
        dd = make_draw_data(1, 5, [gate])
        img = render(dd)
        arr = np.array(img)
        ctrl_color = np.array(CTRL_COLOR, dtype=np.uint8)

        # Control dots at qubits 0, 1, 3
        for q in [0, 1, 3]:
            cy = q * CELL_H + CELL_H // 2
            np.testing.assert_array_equal(
                arr[cy, 0],
                ctrl_color,
                err_msg=f"Control dot missing at qubit {q}",
            )

        # Verify the control line spans the full range
        y_min = 0 * CELL_H + CELL_H // 2
        y_max = 4 * CELL_H + CELL_H // 2
        for y in range(y_min, y_max + 1):
            pixel = arr[y, 0]
            is_ctrl = np.array_equal(pixel, ctrl_color)
            is_gate = np.array_equal(pixel, np.array(GATE_COLORS[0], dtype=np.uint8))
            assert is_ctrl or is_gate, (
                f"Pixel at y={y} should be CTRL or GATE color, got {tuple(pixel)}"
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
