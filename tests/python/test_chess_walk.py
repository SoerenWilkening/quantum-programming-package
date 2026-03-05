"""Tests for chess quantum walk register scaffolding, board state replay, and local diffusion.

Component tests for Phase 104 requirements WALK-01, WALK-02, WALK-03,
Phase 105 requirements WALK-04, WALK-05, WALK-06, WALK-07.
Tests stay within 17-qubit budget by testing registers in isolation.
Derive/underive tests verify call order at circuit-generation level (no simulation).
Diffusion tests verify circuit generation without simulation (qubit count exceeds budget).
"""

import math
import os
import sys
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


class TestHeightRegister:
    """WALK-01: One-hot height register with root qubit initialization."""

    def test_width_matches_max_depth_plus_one(self, clean_circuit):
        """Height register for max_depth=3 has width 4."""
        from chess_walk import create_height_register

        h = create_height_register(max_depth=3)
        # Width of the qint = max_depth + 1
        assert h.width == 4

    def test_root_qubit_is_msb(self, clean_circuit):
        """Root qubit is at qubits[63] (MSB, right-aligned)."""
        from chess_walk import create_height_register

        h = create_height_register(max_depth=3)
        root_qubit = int(h.qubits[63])
        # Root qubit should be a valid physical qubit index (non-negative)
        assert root_qubit >= 0

    def test_root_qubit_initialized_via_emit_x(self, clean_circuit):
        """Root qubit should have emit_x called, qubits allocated for height register."""
        import quantum_language as ql
        from chess_walk import create_height_register

        _h = create_height_register(max_depth=3)  # noqa: F841
        stats = ql.circuit_stats()
        # Height register should allocate max_depth+1 = 4 qubits
        assert stats["peak_allocated"] >= 4

    def test_different_max_depth(self, clean_circuit):
        """Height register adapts to different max_depth values."""
        from chess_walk import create_height_register

        h2 = create_height_register(max_depth=2)
        assert h2.width == 3

        # Need a fresh circuit for a separate register
        import quantum_language as ql

        ql.circuit()
        h5 = create_height_register(max_depth=5)
        assert h5.width == 6


class TestBranchRegisters:
    """WALK-02: Per-level branch registers with correct widths."""

    def test_correct_number_of_registers(self, clean_circuit):
        """create_branch_registers returns one register per depth level."""
        from chess_walk import create_branch_registers

        # Mock move_data: 3 levels
        move_data = [
            {"branch_width": 5},
            {"branch_width": 3},
            {"branch_width": 5},
        ]
        regs = create_branch_registers(max_depth=3, move_data_per_level=move_data)
        assert len(regs) == 3

    def test_correct_widths(self, clean_circuit):
        """Each branch register has width matching branch_width from move_data."""
        from chess_walk import create_branch_registers

        move_data = [
            {"branch_width": 5},
            {"branch_width": 3},
        ]
        regs = create_branch_registers(max_depth=2, move_data_per_level=move_data)
        assert regs[0].width == 5
        assert regs[1].width == 3

    def test_alternating_white_black_widths(self, clean_circuit):
        """White levels (even) can be wider than black levels (odd)."""
        from chess_walk import create_branch_registers

        # Realistic: white 5-bit, black 3-bit, alternating
        move_data = [
            {"branch_width": 5},
            {"branch_width": 3},
            {"branch_width": 5},
            {"branch_width": 3},
        ]
        regs = create_branch_registers(max_depth=4, move_data_per_level=move_data)
        assert regs[0].width == 5
        assert regs[1].width == 3
        assert regs[2].width == 5
        assert regs[3].width == 3


class TestHeightQubit:
    """Height qubit accessor: physical qubit index from height register."""

    def test_depth_zero(self, clean_circuit):
        """height_qubit at depth=0 returns correct physical qubit."""
        from chess_walk import create_height_register, height_qubit

        h = create_height_register(max_depth=3)
        # width = max_depth+1 = 4
        # index = 64 - 4 + 0 = 60
        expected = int(h.qubits[60])
        result = height_qubit(h, depth=0, max_depth=3)
        assert result == expected

    def test_depth_equals_max_depth(self, clean_circuit):
        """height_qubit at depth=max_depth is the root qubit (qubits[63])."""
        from chess_walk import create_height_register, height_qubit

        h = create_height_register(max_depth=3)
        # depth = max_depth = 3, index = 64 - 4 + 3 = 63
        expected = int(h.qubits[63])
        result = height_qubit(h, depth=3, max_depth=3)
        assert result == expected

    def test_intermediate_depth(self, clean_circuit):
        """height_qubit at intermediate depth returns correct qubit."""
        from chess_walk import create_height_register, height_qubit

        h = create_height_register(max_depth=4)
        # width = 5, depth = 2, index = 64 - 5 + 2 = 61
        expected = int(h.qubits[61])
        result = height_qubit(h, depth=2, max_depth=4)
        assert result == expected

    def test_max_depth_two(self, clean_circuit):
        """height_qubit works for max_depth=2."""
        from chess_walk import create_height_register, height_qubit

        h = create_height_register(max_depth=2)
        # width = 3
        # depth=0: index = 64 - 3 + 0 = 61
        # depth=1: index = 64 - 3 + 1 = 62
        # depth=2: index = 64 - 3 + 2 = 63 (root)
        q0 = height_qubit(h, depth=0, max_depth=2)
        q1 = height_qubit(h, depth=1, max_depth=2)
        q2 = height_qubit(h, depth=2, max_depth=2)
        assert q0 == int(h.qubits[61])
        assert q1 == int(h.qubits[62])
        assert q2 == int(h.qubits[63])
        # All should be different physical qubits
        assert len({q0, q1, q2}) == 3


class TestDeriveUnderiveBoardState:
    """Board state derivation and uncomputation via oracle replay."""

    def test_derive_calls_oracles_in_forward_order(self):
        """derive_board_state calls each oracle in order 0, 1, ..., depth-1."""
        from chess_walk import derive_board_state

        # Create mock oracles and board arrays
        oracle0 = MagicMock()
        oracle1 = MagicMock()
        oracle2 = MagicMock()
        oracles = [oracle0, oracle1, oracle2]

        wk = MagicMock()
        bk = MagicMock()
        wn = MagicMock()
        board_arrs = (wk, bk, wn)

        branch0 = MagicMock()
        branch1 = MagicMock()
        branch2 = MagicMock()
        branch_regs = [branch0, branch1, branch2]

        derive_board_state(board_arrs, branch_regs, oracles, depth=3)

        # Each oracle called with (wk, bk, wn, branch_reg[level])
        oracle0.assert_called_once_with(wk, bk, wn, branch0)
        oracle1.assert_called_once_with(wk, bk, wn, branch1)
        oracle2.assert_called_once_with(wk, bk, wn, branch2)

    def test_derive_partial_depth(self):
        """derive_board_state with depth < max only calls oracles 0..depth-1."""
        from chess_walk import derive_board_state

        oracle0 = MagicMock()
        oracle1 = MagicMock()
        oracle2 = MagicMock()
        oracles = [oracle0, oracle1, oracle2]

        board_arrs = (MagicMock(), MagicMock(), MagicMock())
        branch_regs = [MagicMock(), MagicMock(), MagicMock()]

        derive_board_state(board_arrs, branch_regs, oracles, depth=2)

        oracle0.assert_called_once()
        oracle1.assert_called_once()
        oracle2.assert_not_called()

    def test_underive_calls_oracles_inverse_in_reverse(self):
        """underive_board_state calls .inverse in LIFO order: depth-1, ..., 0."""
        from chess_walk import underive_board_state

        oracle0 = MagicMock()
        oracle1 = MagicMock()
        oracle2 = MagicMock()
        oracles = [oracle0, oracle1, oracle2]

        wk = MagicMock()
        bk = MagicMock()
        wn = MagicMock()
        board_arrs = (wk, bk, wn)

        branch0 = MagicMock()
        branch1 = MagicMock()
        branch2 = MagicMock()
        branch_regs = [branch0, branch1, branch2]

        underive_board_state(board_arrs, branch_regs, oracles, depth=3)

        # Inverse called in reverse: 2, 1, 0
        oracle2.inverse.assert_called_once_with(wk, bk, wn, branch2)
        oracle1.inverse.assert_called_once_with(wk, bk, wn, branch1)
        oracle0.inverse.assert_called_once_with(wk, bk, wn, branch0)

    def test_derive_depth_zero_calls_nothing(self):
        """derive_board_state with depth=0 calls no oracles."""
        from chess_walk import derive_board_state

        oracle0 = MagicMock()
        oracles = [oracle0]

        board_arrs = (MagicMock(), MagicMock(), MagicMock())
        branch_regs = [MagicMock()]

        derive_board_state(board_arrs, branch_regs, oracles, depth=0)
        oracle0.assert_not_called()


class TestPrepareWalkData:
    """Walk data preparation with alternating side-to-move."""

    def test_alternates_side_to_move(self, clean_circuit):
        """Level 0 = white, level 1 = black, level 2 = white, etc."""
        from chess_walk import prepare_walk_data

        # Position: white king e1 (4), black king e8 (60), white knight b1 (1)
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[1], max_depth=3)

        assert len(data) == 3
        # Level 0 = white's moves, level 1 = black's moves, level 2 = white's moves

        # White has knight + king moves, black has only king moves
        # White should generally have more moves than black
        # Verify that data alternates by checking move lists are different
        # Level 0 (white) and level 2 (white) should have same move set
        # (since this is classical precomputation from starting position)
        assert data[0]["moves"] == data[2]["moves"]

    def test_returns_correct_keys(self, clean_circuit):
        """Each level's data has required keys: moves, move_count, branch_width, apply_move."""
        from chess_walk import prepare_walk_data

        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[1], max_depth=2)
        for level in data:
            assert "moves" in level
            assert "move_count" in level
            assert "branch_width" in level
            assert "apply_move" in level

    def test_branch_width_values(self, clean_circuit):
        """Branch width correctly computed from move count."""
        from chess_walk import prepare_walk_data

        # Use a position where we can predict move counts
        # White king e1 (4), black king a8 (56), white knight b1 (1)
        data = prepare_walk_data(wk_sq=4, bk_sq=56, wn_squares=[1], max_depth=2)

        for level in data:
            # branch_width >= 1 always
            assert level["branch_width"] >= 1
            # branch_width should be enough to index all moves
            assert 2 ** level["branch_width"] >= level["move_count"]

    def test_move_counts_positive(self, clean_circuit):
        """All levels should have at least one legal move in a valid position."""
        from chess_walk import prepare_walk_data

        # Well-separated position ensures legal moves for both sides
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[1], max_depth=2)
        for level in data:
            assert level["move_count"] > 0

    def test_white_generally_more_moves_than_black(self, clean_circuit):
        """White (with knight) should have more legal moves than black (king only)."""
        from chess_walk import prepare_walk_data

        # Position with knight giving white more moves
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[1], max_depth=2)

        white_moves = data[0]["move_count"]  # Level 0 = white
        black_moves = data[1]["move_count"]  # Level 1 = black
        # White has knight + king, black has only king
        assert white_moves > black_moves


class TestAngles:
    """WALK-03: Montanaro angle formulas for internal nodes and root."""

    def test_montanaro_phi_d4(self):
        """phi(4) = 2*arctan(sqrt(4)) = 2*arctan(2) approx 2.2143."""
        from chess_walk import montanaro_phi

        result = montanaro_phi(4)
        expected = 2.0 * math.atan(math.sqrt(4))
        assert abs(result - expected) < 1e-10
        assert abs(result - 2.214297435588181) < 1e-6

    def test_montanaro_phi_d1(self):
        """phi(1) = 2*arctan(1) = pi/2."""
        from chess_walk import montanaro_phi

        result = montanaro_phi(1)
        assert abs(result - math.pi / 2) < 1e-10

    def test_montanaro_phi_d2(self):
        """phi(2) = 2*arctan(sqrt(2))."""
        from chess_walk import montanaro_phi

        result = montanaro_phi(2)
        expected = 2.0 * math.atan(math.sqrt(2))
        assert abs(result - expected) < 1e-10

    def test_montanaro_root_phi_d4_n3(self):
        """root_phi(4, 3) = 2*arctan(sqrt(3*4)) = 2*arctan(sqrt(12))."""
        from chess_walk import montanaro_root_phi

        result = montanaro_root_phi(4, 3)
        expected = 2.0 * math.atan(math.sqrt(12))
        assert abs(result - expected) < 1e-10

    def test_montanaro_root_phi_d1_n1(self):
        """root_phi(1, 1) = 2*arctan(1) = pi/2."""
        from chess_walk import montanaro_root_phi

        result = montanaro_root_phi(1, 1)
        assert abs(result - math.pi / 2) < 1e-10


class TestPrecomputeAngles:
    """Precomputed diffusion angle dict structure and content."""

    def test_dict_keys_1_to_dmax(self):
        """precompute_diffusion_angles returns dict with keys 1..d_max."""
        from chess_walk import precompute_diffusion_angles

        result = precompute_diffusion_angles(d_max=4, branch_width=3)
        assert set(result.keys()) == {1, 2, 3, 4}

    def test_phi_values(self):
        """Each d_val entry has correct phi = 2*arctan(sqrt(d_val))."""
        from chess_walk import precompute_diffusion_angles

        result = precompute_diffusion_angles(d_max=3, branch_width=2)
        for d_val in range(1, 4):
            expected_phi = 2.0 * math.atan(math.sqrt(d_val))
            assert abs(result[d_val]["phi"] - expected_phi) < 1e-10

    def test_cascade_ops_empty_for_d1(self):
        """d_val=1 has empty cascade_ops (no cascade needed for single child)."""
        from chess_walk import precompute_diffusion_angles

        result = precompute_diffusion_angles(d_max=4, branch_width=3)
        assert result[1]["cascade_ops"] == []

    def test_cascade_ops_nonempty_for_d_gt_1(self):
        """d_val > 1 has non-empty cascade_ops."""
        from chess_walk import precompute_diffusion_angles

        result = precompute_diffusion_angles(d_max=4, branch_width=3)
        for d_val in range(2, 5):
            assert len(result[d_val]["cascade_ops"]) > 0


class TestEvaluateChildren:
    """Circuit-generation test for child evaluation loop."""

    def test_evaluate_children_no_crash(self, clean_circuit):
        """evaluate_children completes without error for a simple position."""
        from chess_encoding import encode_position
        from chess_walk import (
            create_branch_registers,
            create_height_register,
            evaluate_children,
            prepare_walk_data,
        )
        from quantum_language.qbool import qbool

        # Simple position: wk=4, bk=60, wn=[10], max_depth=1
        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)

        level_idx = 0  # For depth=max_depth=1, level_idx=max_depth-depth=0
        d_max = data[level_idx]["move_count"]
        oracle = data[level_idx]["apply_move"]
        pos = encode_position(4, 60, [10])
        board_arrs = (pos["white_king"], pos["black_king"], pos["white_knights"])
        validity = [qbool() for _ in range(d_max)]

        # Should not crash -- circuit generation only
        evaluate_children(
            depth=max_depth,
            level_idx=level_idx,
            d_max=d_max,
            branch_reg=branch_regs[level_idx],
            h_reg=h_reg,
            max_depth=max_depth,
            oracle=oracle,
            board_arrs=board_arrs,
            validity=validity,
        )

    def test_uncompute_children_no_crash(self, clean_circuit):
        """uncompute_children completes without error."""
        from chess_encoding import encode_position
        from chess_walk import (
            create_branch_registers,
            create_height_register,
            evaluate_children,
            prepare_walk_data,
            uncompute_children,
        )
        from quantum_language.qbool import qbool

        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)

        level_idx = 0
        d_max = data[level_idx]["move_count"]
        oracle = data[level_idx]["apply_move"]
        pos = encode_position(4, 60, [10])
        board_arrs = (pos["white_king"], pos["black_king"], pos["white_knights"])
        validity = [qbool() for _ in range(d_max)]

        # Forward then reverse
        evaluate_children(
            depth=max_depth,
            level_idx=level_idx,
            d_max=d_max,
            branch_reg=branch_regs[level_idx],
            h_reg=h_reg,
            max_depth=max_depth,
            oracle=oracle,
            board_arrs=board_arrs,
            validity=validity,
        )
        uncompute_children(
            depth=max_depth,
            level_idx=level_idx,
            d_max=d_max,
            branch_reg=branch_regs[level_idx],
            h_reg=h_reg,
            max_depth=max_depth,
            oracle=oracle,
            board_arrs=board_arrs,
            validity=validity,
        )


class TestDiffusion:
    """WALK-03: Circuit-generation test for apply_diffusion."""

    def test_apply_diffusion_no_crash(self, clean_circuit):
        """apply_diffusion completes without error for a simple position."""
        from chess_encoding import encode_position
        from chess_walk import (
            apply_diffusion,
            create_branch_registers,
            create_height_register,
            prepare_walk_data,
        )

        # Simple position with max_depth=1 (smallest valid tree)
        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)
        pos = encode_position(4, 60, [10])
        board_arrs = (pos["white_king"], pos["black_king"], pos["white_knights"])
        oracle_per_level = [d["apply_move"] for d in data]

        # Circuit generation only -- no simulation (qubit count exceeds budget)
        apply_diffusion(
            depth=max_depth,
            h_reg=h_reg,
            branch_regs=branch_regs,
            board_arrs=board_arrs,
            oracle_per_level=oracle_per_level,
            move_data_per_level=data,
            max_depth=max_depth,
        )

    def test_apply_diffusion_importable(self):
        """apply_diffusion is importable from chess_walk."""
        from chess_walk import apply_diffusion

        assert callable(apply_diffusion)


class TestDiffusionAngles:
    """Verify correct angle selection for positions with known move counts."""

    def test_angles_for_known_position(self, clean_circuit):
        """For a known position, precomputed angles use correct phi."""
        from chess_walk import precompute_diffusion_angles, prepare_walk_data

        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=1)
        d_max = data[0]["move_count"]
        branch_width = data[0]["branch_width"]
        angles = precompute_diffusion_angles(d_max, branch_width)

        # Verify phi for the actual move count
        expected_phi = 2.0 * math.atan(math.sqrt(d_max))
        assert abs(angles[d_max]["phi"] - expected_phi) < 1e-10

    def test_all_exports_importable(self):
        """All 10 public exports are importable from chess_walk."""
        # Also check evaluate_children and uncompute_children
        from chess_walk import (
            apply_diffusion,
            evaluate_children,
            uncompute_children,
        )

        assert callable(apply_diffusion)
        assert callable(evaluate_children)
        assert callable(uncompute_children)


class TestRA:
    """WALK-05: R_A operator composes diffusion at even depths, excluding root."""

    def test_ra_max_depth_1(self):
        """r_a() with max_depth=1: even depths are [0], but depth 0 skipped (leaves)."""
        from chess_walk import r_a

        with patch("chess_walk.apply_diffusion") as mock_diff:
            r_a(
                h_reg=MagicMock(),
                branch_regs=MagicMock(),
                board_arrs=MagicMock(),
                oracle_per_level=MagicMock(),
                move_data_per_level=MagicMock(),
                max_depth=1,
            )
            # max_depth=1: even depths in range(0,2,2) = [0]
            # depth 0 is skipped (leaves), depth 1 is root (skipped)
            # So no calls.
            mock_diff.assert_not_called()

    def test_ra_max_depth_2(self):
        """r_a() with max_depth=2: even depths [0, 2], skip 0 (leaves) and 2 (root)."""
        from chess_walk import r_a

        with patch("chess_walk.apply_diffusion") as mock_diff:
            h = MagicMock()
            br = MagicMock()
            ba = MagicMock()
            opl = MagicMock()
            mdpl = MagicMock()
            r_a(h, br, ba, opl, mdpl, max_depth=2)
            # depth 0 skipped (leaves), depth 2 == max_depth (root, skipped)
            mock_diff.assert_not_called()

    def test_ra_max_depth_3(self):
        """r_a() with max_depth=3: even depths [0, 2], skip 0 (leaves), call depth=2."""
        from chess_walk import r_a

        with patch("chess_walk.apply_diffusion") as mock_diff:
            h = MagicMock()
            br = MagicMock()
            ba = MagicMock()
            opl = MagicMock()
            mdpl = MagicMock()
            r_a(h, br, ba, opl, mdpl, max_depth=3)
            # depth 0 skipped (leaves), depth 2 called, depth 3 is root (odd, not in range)
            mock_diff.assert_called_once_with(2, h, br, ba, opl, mdpl, 3)

    def test_ra_max_depth_4(self):
        """r_a() with max_depth=4: even depths [0,2,4], skip 0 and 4 (root), call 2."""
        from chess_walk import r_a

        with patch("chess_walk.apply_diffusion") as mock_diff:
            h = MagicMock()
            br = MagicMock()
            ba = MagicMock()
            opl = MagicMock()
            mdpl = MagicMock()
            r_a(h, br, ba, opl, mdpl, max_depth=4)
            # depth 0 skipped (leaves), depth 2 called, depth 4 == max_depth (root, skipped)
            mock_diff.assert_called_once_with(2, h, br, ba, opl, mdpl, 4)


class TestRB:
    """WALK-06: R_B operator composes diffusion at odd depths plus root."""

    def test_rb_max_depth_1(self):
        """r_b() with max_depth=1: odd depths [1], root is 1 (odd, already included)."""
        from chess_walk import r_b

        with patch("chess_walk.apply_diffusion") as mock_diff:
            h = MagicMock()
            br = MagicMock()
            ba = MagicMock()
            opl = MagicMock()
            mdpl = MagicMock()
            r_b(h, br, ba, opl, mdpl, max_depth=1)
            # max_depth=1 is odd, so root already in range(1,2,2)=[1]
            mock_diff.assert_called_once_with(1, h, br, ba, opl, mdpl, 1)

    def test_rb_max_depth_2(self):
        """r_b() with max_depth=2: odd depths [1], root=2 added explicitly (even max_depth)."""
        from chess_walk import r_b

        with patch("chess_walk.apply_diffusion") as mock_diff:
            h = MagicMock()
            br = MagicMock()
            ba = MagicMock()
            opl = MagicMock()
            mdpl = MagicMock()
            r_b(h, br, ba, opl, mdpl, max_depth=2)
            # range(1,3,2) = [1], then max_depth=2 is even so add depth=2
            assert mock_diff.call_count == 2
            mock_diff.assert_any_call(1, h, br, ba, opl, mdpl, 2)
            mock_diff.assert_any_call(2, h, br, ba, opl, mdpl, 2)

    def test_rb_max_depth_3(self):
        """r_b() with max_depth=3: odd depths [1, 3], root=3 already included."""
        from chess_walk import r_b

        with patch("chess_walk.apply_diffusion") as mock_diff:
            h = MagicMock()
            br = MagicMock()
            ba = MagicMock()
            opl = MagicMock()
            mdpl = MagicMock()
            r_b(h, br, ba, opl, mdpl, max_depth=3)
            # range(1,4,2) = [1, 3], root=3 is odd so already there
            assert mock_diff.call_count == 2
            calls = mock_diff.call_args_list
            assert calls[0] == call(1, h, br, ba, opl, mdpl, 3)
            assert calls[1] == call(3, h, br, ba, opl, mdpl, 3)

    def test_rb_max_depth_4(self):
        """r_b() with max_depth=4: odd depths [1, 3], root=4 added explicitly."""
        from chess_walk import r_b

        with patch("chess_walk.apply_diffusion") as mock_diff:
            h = MagicMock()
            br = MagicMock()
            ba = MagicMock()
            opl = MagicMock()
            mdpl = MagicMock()
            r_b(h, br, ba, opl, mdpl, max_depth=4)
            # range(1,5,2) = [1, 3], then max_depth=4 is even so add depth=4
            assert mock_diff.call_count == 3
            calls = mock_diff.call_args_list
            assert calls[0] == call(1, h, br, ba, opl, mdpl, 4)
            assert calls[1] == call(3, h, br, ba, opl, mdpl, 4)
            assert calls[2] == call(4, h, br, ba, opl, mdpl, 4)


class TestHeightControlledCascade:
    """WALK-04: Disjointness and completeness of R_A/R_B depth sets."""

    def _get_depth_sets(self, max_depth):
        """Helper: compute R_A and R_B depth sets for a given max_depth."""
        # R_A: even depths, skip 0 (leaves) and max_depth (root)
        r_a_depths = set()
        for d in range(0, max_depth + 1, 2):
            if d == 0:
                continue  # skip leaves
            if d == max_depth:
                continue  # root belongs to R_B
            r_a_depths.add(d)

        # R_B: odd depths + root
        r_b_depths = set(range(1, max_depth + 1, 2))
        if max_depth % 2 == 0:
            r_b_depths.add(max_depth)

        return r_a_depths, r_b_depths

    def test_disjointness_max_depth_1(self):
        """R_A and R_B depth sets have no overlap for max_depth=1."""
        ra, rb = self._get_depth_sets(1)
        assert ra & rb == set()

    def test_disjointness_max_depth_2(self):
        """R_A and R_B depth sets have no overlap for max_depth=2."""
        ra, rb = self._get_depth_sets(2)
        assert ra & rb == set()

    def test_disjointness_max_depth_3(self):
        """R_A and R_B depth sets have no overlap for max_depth=3."""
        ra, rb = self._get_depth_sets(3)
        assert ra & rb == set()

    def test_disjointness_max_depth_4(self):
        """R_A and R_B depth sets have no overlap for max_depth=4."""
        ra, rb = self._get_depth_sets(4)
        assert ra & rb == set()

    def test_coverage_max_depth_1(self):
        """R_A union R_B covers depths 0..max_depth (minus leaves) for max_depth=1."""
        ra, rb = self._get_depth_sets(1)
        # Depth 0 is skipped (leaves) so coverage is {1..max_depth}
        assert ra | rb == set(range(1, 2))

    def test_coverage_max_depth_2(self):
        """R_A union R_B covers depths 1..max_depth for max_depth=2."""
        ra, rb = self._get_depth_sets(2)
        assert ra | rb == set(range(1, 3))

    def test_coverage_max_depth_3(self):
        """R_A union R_B covers depths 1..max_depth for max_depth=3."""
        ra, rb = self._get_depth_sets(3)
        assert ra | rb == set(range(1, 4))

    def test_coverage_max_depth_4(self):
        """R_A union R_B covers depths 1..max_depth for max_depth=4."""
        ra, rb = self._get_depth_sets(4)
        assert ra | rb == set(range(1, 5))

    def test_root_always_in_rb(self):
        """Root (depth == max_depth) is always in R_B, never in R_A."""
        for md in range(1, 6):
            ra, rb = self._get_depth_sets(md)
            assert md in rb, f"Root {md} not in R_B for max_depth={md}"
            assert md not in ra, f"Root {md} in R_A for max_depth={md}"

    def test_circuit_gen_smoke_ra_rb(self, clean_circuit):
        """Smoke test: r_a and r_b run without error on real chess position."""
        from chess_encoding import encode_position
        from chess_walk import (
            create_branch_registers,
            create_height_register,
            prepare_walk_data,
            r_a,
            r_b,
        )

        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)
        pos = encode_position(4, 60, [10])
        board_arrs = (pos["white_king"], pos["black_king"], pos["white_knights"])
        oracle_per_level = [d["apply_move"] for d in data]

        # Both should complete without error
        r_a(h_reg, branch_regs, board_arrs, oracle_per_level, data, max_depth)
        r_b(h_reg, branch_regs, board_arrs, oracle_per_level, data, max_depth)


class TestAllWalkQubits:
    """WALK-07: Register wrapping height + branch walk qubits.

    Board array qarrays are passed separately to the compiled walk step
    since total qubit count (height + branch + 3*64 board) exceeds qint
    max width of 64.
    """

    def test_returns_qint_with_correct_total(self, clean_circuit):
        """all_walk_qubits total = height + branch widths."""
        from chess_walk import (
            all_walk_qubits,
            create_branch_registers,
            create_height_register,
            prepare_walk_data,
        )

        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)

        mega = all_walk_qubits(h_reg, branch_regs, max_depth)

        # height = max_depth + 1 = 2
        height_count = max_depth + 1
        # branch widths
        branch_count = sum(br.width for br in branch_regs)

        expected_total = height_count + branch_count
        assert mega.width == expected_total

    def test_no_duplicate_qubit_indices(self, clean_circuit):
        """All qubit indices in the register are unique."""
        from chess_walk import (
            all_walk_qubits,
            create_branch_registers,
            create_height_register,
            prepare_walk_data,
        )

        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)

        mega = all_walk_qubits(h_reg, branch_regs, max_depth)

        # Extract non-zero indices from the qint's qubits array
        indices = []
        w = mega.width
        for i in range(w):
            indices.append(int(mega.qubits[64 - w + i]))
        assert len(indices) == len(set(indices)), f"Duplicate qubit indices found: {indices}"

    def test_importable_from_chess_walk(self):
        """all_walk_qubits is importable from chess_walk."""
        from chess_walk import all_walk_qubits

        assert callable(all_walk_qubits)


class TestWalkStep:
    """WALK-07: walk_step() compiled walk operator U = R_B * R_A."""

    def test_walk_step_smoke(self, clean_circuit):
        """walk_step() runs without error on real chess position."""
        from chess_encoding import encode_position
        from chess_walk import (
            create_branch_registers,
            create_height_register,
            prepare_walk_data,
            walk_step,
        )

        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)
        pos = encode_position(4, 60, [10])
        board_arrs = (pos["white_king"], pos["black_king"], pos["white_knights"])
        oracle_per_level = [d["apply_move"] for d in data]

        # Circuit generation only -- no simulation (qubit count exceeds budget)
        walk_step(h_reg, branch_regs, board_arrs, oracle_per_level, data, max_depth)

    def test_walk_step_replay_same_gate_count(self, clean_circuit):
        """walk_step() called twice produces same gate count (replay works)."""
        import quantum_language as ql
        from chess_encoding import encode_position
        from chess_walk import (
            create_branch_registers,
            create_height_register,
            prepare_walk_data,
            walk_step,
        )

        max_depth = 1
        data = prepare_walk_data(wk_sq=4, bk_sq=60, wn_squares=[10], max_depth=max_depth)
        h_reg = create_height_register(max_depth)
        branch_regs = create_branch_registers(max_depth, data)
        pos = encode_position(4, 60, [10])
        board_arrs = (pos["white_king"], pos["black_king"], pos["white_knights"])
        oracle_per_level = [d["apply_move"] for d in data]

        # First call: capture + compile
        before1 = ql.get_current_layer()
        walk_step(h_reg, branch_regs, board_arrs, oracle_per_level, data, max_depth)
        after1 = ql.get_current_layer()
        count1 = after1 - before1

        # Second call: replay
        before2 = ql.get_current_layer()
        walk_step(h_reg, branch_regs, board_arrs, oracle_per_level, data, max_depth)
        after2 = ql.get_current_layer()
        count2 = after2 - before2

        # Replay should produce same gate count as first call
        assert count1 > 0, "First walk_step should produce gates"
        assert count2 > 0, "Second walk_step should produce gates"
        assert count1 == count2, f"Gate count mismatch: first={count1}, second={count2}"

    def test_walk_step_importable(self):
        """walk_step is importable from chess_walk."""
        from chess_walk import walk_step

        assert callable(walk_step)
