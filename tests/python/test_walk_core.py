"""Tests for walk_core: WalkConfig, Montanaro angles, register widths."""

import math

import pytest

from quantum_language.walk_core import (
    WalkConfig,
    branch_width,
    count_width,
    montanaro_angles,
    montanaro_cascade_angles,
    montanaro_phi,
    root_angle,
)


# ------------------------------------------------------------------
# branch_width
# ------------------------------------------------------------------


class TestBranchWidth:
    def test_binary(self):
        assert branch_width(2) == 1

    def test_ternary(self):
        assert branch_width(3) == 2

    def test_four(self):
        assert branch_width(4) == 2

    def test_five(self):
        assert branch_width(5) == 3

    def test_eight(self):
        assert branch_width(8) == 3

    def test_one(self):
        assert branch_width(1) == 1

    def test_sixteen(self):
        assert branch_width(16) == 4

    def test_invalid_zero(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            branch_width(0)

    def test_invalid_negative(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            branch_width(-1)

    def test_rejects_float(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            branch_width(2.5)

    def test_rejects_string(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            branch_width("2")

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            branch_width(None)


# ------------------------------------------------------------------
# count_width
# ------------------------------------------------------------------


class TestCountWidth:
    def test_binary(self):
        # Must store 0, 1, 2 -> 2 bits
        assert count_width(2) == 2

    def test_ternary(self):
        # Must store 0, 1, 2, 3 -> 2 bits
        assert count_width(3) == 2

    def test_four(self):
        # Must store 0..4 -> 3 bits
        assert count_width(4) == 3

    def test_seven(self):
        # Must store 0..7 -> 3 bits
        assert count_width(7) == 3

    def test_eight(self):
        # Must store 0..8 -> 4 bits
        assert count_width(8) == 4

    def test_one(self):
        # Must store 0, 1 -> 1 bit
        assert count_width(1) == 1

    def test_invalid_zero(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            count_width(0)

    def test_rejects_float(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            count_width(2.5)

    def test_rejects_string(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            count_width("3")


# ------------------------------------------------------------------
# Montanaro angle formulas
# ------------------------------------------------------------------


class TestMontanaroPhi:
    def test_d1(self):
        # phi(1) = 2 * arctan(1) = pi/2
        assert math.isclose(montanaro_phi(1), math.pi / 2, rel_tol=1e-12)

    def test_d2(self):
        # phi(2) = 2 * arctan(sqrt(2))
        expected = 2.0 * math.atan(math.sqrt(2))
        assert math.isclose(montanaro_phi(2), expected, rel_tol=1e-12)

    def test_d3(self):
        # phi(3) = 2 * arctan(sqrt(3))
        expected = 2.0 * math.atan(math.sqrt(3))
        assert math.isclose(montanaro_phi(3), expected, rel_tol=1e-12)

    def test_invalid(self):
        with pytest.raises(ValueError, match="d must be >= 1"):
            montanaro_phi(0)


class TestMontanaroCascade:
    def test_d1_empty(self):
        assert montanaro_cascade_angles(1) == []

    def test_d2_single_angle(self):
        # k=0: theta = 2*arctan(sqrt(1/1)) = 2*arctan(1) = pi/2
        angles = montanaro_cascade_angles(2)
        assert len(angles) == 1
        assert math.isclose(angles[0], math.pi / 2, rel_tol=1e-12)

    def test_d3_two_angles(self):
        angles = montanaro_cascade_angles(3)
        assert len(angles) == 2
        # k=0: 2*arctan(sqrt(1/2))
        assert math.isclose(
            angles[0], 2.0 * math.atan(math.sqrt(0.5)), rel_tol=1e-12
        )
        # k=1: 2*arctan(sqrt(1/1)) = pi/2
        assert math.isclose(angles[1], math.pi / 2, rel_tol=1e-12)

    def test_d4_three_angles(self):
        angles = montanaro_cascade_angles(4)
        assert len(angles) == 3
        # k=0: 2*arctan(sqrt(1/3))
        assert math.isclose(
            angles[0], 2.0 * math.atan(math.sqrt(1.0 / 3)), rel_tol=1e-12
        )
        # k=1: 2*arctan(sqrt(1/2))
        assert math.isclose(
            angles[1], 2.0 * math.atan(math.sqrt(0.5)), rel_tol=1e-12
        )
        # k=2: 2*arctan(1) = pi/2
        assert math.isclose(angles[2], math.pi / 2, rel_tol=1e-12)

    def test_invalid(self):
        with pytest.raises(ValueError, match="d must be >= 1"):
            montanaro_cascade_angles(0)


class TestMontanaroAngles:
    def test_d2(self):
        result = montanaro_angles(2)
        assert "phi" in result
        assert "cascade" in result
        assert math.isclose(
            result["phi"], 2.0 * math.atan(math.sqrt(2)), rel_tol=1e-12
        )
        assert len(result["cascade"]) == 1

    def test_d3(self):
        result = montanaro_angles(3)
        assert math.isclose(
            result["phi"], 2.0 * math.atan(math.sqrt(3)), rel_tol=1e-12
        )
        assert len(result["cascade"]) == 2


# ------------------------------------------------------------------
# Root angle
# ------------------------------------------------------------------


class TestRootAngle:
    def test_basic(self):
        # phi_root(d=2, n=3) = 2*arctan(sqrt(6))
        expected = 2.0 * math.atan(math.sqrt(6))
        assert math.isclose(root_angle(2, 3), expected, rel_tol=1e-12)

    def test_d1_n1(self):
        # phi_root(1, 1) = 2*arctan(1) = pi/2
        assert math.isclose(root_angle(1, 1), math.pi / 2, rel_tol=1e-12)

    def test_invalid_d(self):
        with pytest.raises(ValueError, match="d must be >= 1"):
            root_angle(0, 3)

    def test_invalid_n(self):
        with pytest.raises(ValueError, match="n.*must be >= 1"):
            root_angle(2, 0)


# ------------------------------------------------------------------
# WalkConfig
# ------------------------------------------------------------------


class TestWalkConfig:
    def test_basic_creation(self):
        cfg = WalkConfig(max_depth=3, num_moves=2)
        assert cfg.max_depth == 3
        assert cfg.num_moves == 2
        assert cfg.bw == 1
        assert cfg.cw == 2
        assert cfg.hw == 4

    def test_derived_widths_ternary(self):
        cfg = WalkConfig(max_depth=2, num_moves=3)
        assert cfg.bw == 2  # ceil(log2(3)) = 2
        assert cfg.cw == 2  # ceil(log2(4)) = 2
        assert cfg.hw == 3  # 2 + 1

    def test_derived_widths_four_moves(self):
        cfg = WalkConfig(max_depth=4, num_moves=4)
        assert cfg.bw == 2
        assert cfg.cw == 3  # ceil(log2(5)) = 3
        assert cfg.hw == 5

    def test_invalid_depth_zero(self):
        with pytest.raises(ValueError, match="max_depth must be >= 1"):
            WalkConfig(max_depth=0, num_moves=2)

    def test_invalid_depth_negative(self):
        with pytest.raises(ValueError, match="max_depth must be >= 1"):
            WalkConfig(max_depth=-1, num_moves=2)

    def test_invalid_moves_zero(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            WalkConfig(max_depth=3, num_moves=0)

    def test_invalid_moves_negative(self):
        with pytest.raises(ValueError, match="num_moves must be >= 1"):
            WalkConfig(max_depth=3, num_moves=-5)

    def test_rejects_float_depth(self):
        with pytest.raises(TypeError, match="max_depth must be an int"):
            WalkConfig(max_depth=2.5, num_moves=2)

    def test_rejects_float_moves(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            WalkConfig(max_depth=2, num_moves=3.0)

    def test_rejects_string_depth(self):
        with pytest.raises(TypeError, match="max_depth must be an int"):
            WalkConfig(max_depth="2", num_moves=2)

    def test_rejects_none_moves(self):
        with pytest.raises(TypeError, match="num_moves must be an int"):
            WalkConfig(max_depth=2, num_moves=None)

    def test_optional_callbacks_none(self):
        cfg = WalkConfig(max_depth=2, num_moves=2)
        assert cfg.make_move is None
        assert cfg.is_valid is None
        assert cfg.is_marked is None
        assert cfg.state is None

    def test_callbacks_stored(self):
        def mm(s, i):
            pass

        def iv(s):
            pass

        def im(s):
            pass

        cfg = WalkConfig(
            max_depth=2,
            num_moves=2,
            make_move=mm,
            is_valid=iv,
            is_marked=im,
        )
        assert cfg.make_move is mm
        assert cfg.is_valid is iv
        assert cfg.is_marked is im


class TestWalkConfigTotalQubits:
    def test_binary_depth2(self):
        # height=3, branch=1*2=2, count=2 -> total=7
        cfg = WalkConfig(max_depth=2, num_moves=2)
        assert cfg.total_walk_qubits() == 3 + 2 + 2

    def test_binary_depth3(self):
        # height=4, branch=1*3=3, count=2 -> total=9
        cfg = WalkConfig(max_depth=3, num_moves=2)
        assert cfg.total_walk_qubits() == 4 + 3 + 2

    def test_ternary_depth2(self):
        # height=3, branch=2*2=4, count=2 -> total=9
        cfg = WalkConfig(max_depth=2, num_moves=3)
        assert cfg.total_walk_qubits() == 3 + 4 + 2

    def test_manual_calculation(self):
        # 2 binary variables, ternary encoding (from implementation plan)
        # state = 2*2=4 (not counted), branch=2, height=3, count=2
        # Walk qubits only (no state): 3 + 2 + 2 = 7
        cfg = WalkConfig(max_depth=2, num_moves=2)
        hw = cfg.max_depth + 1
        bw_total = cfg.bw * cfg.max_depth
        cw = cfg.cw
        assert cfg.total_walk_qubits() == hw + bw_total + cw

    def test_excludes_state_register(self):
        cfg = WalkConfig(max_depth=2, num_moves=2, state="dummy")
        # total_walk_qubits should not depend on state
        cfg2 = WalkConfig(max_depth=2, num_moves=2)
        assert cfg.total_walk_qubits() == cfg2.total_walk_qubits()


class TestWalkConfigRootPhi:
    def test_matches_root_angle(self):
        cfg = WalkConfig(max_depth=3, num_moves=2)
        expected = root_angle(2, 3)
        assert math.isclose(cfg.root_phi(), expected, rel_tol=1e-12)

    def test_d1_n1(self):
        cfg = WalkConfig(max_depth=1, num_moves=1)
        assert math.isclose(cfg.root_phi(), math.pi / 2, rel_tol=1e-12)


class TestWalkConfigAnglesFor:
    def test_returns_dict(self):
        cfg = WalkConfig(max_depth=2, num_moves=3)
        result = cfg.angles_for(2)
        assert "phi" in result
        assert "cascade" in result

    def test_matches_standalone(self):
        cfg = WalkConfig(max_depth=2, num_moves=3)
        assert cfg.angles_for(3) == montanaro_angles(3)
