"""Tests for comparison edge cases in compile mode (review feedback fixes).

Covers:
  (a) gt with value equal to max_val for the bit width
  (b) lt with value 0 or negative in compile mode
  (c) QQ comparisons with different-width operands in compile mode

All IR tests use QFT mode (fault_tolerant=False) because IR recording
for arithmetic/comparison operations is specific to QFT mode.
"""

import quantum_language as ql
from quantum_language.compile import CompiledBlock


def _make_block():
    """Create a fresh CompiledBlock for testing."""
    return CompiledBlock(
        gates=[],
        total_virtual_qubits=0,
        param_qubit_ranges=[],
        internal_qubit_count=0,
        return_qubit_range=None,
    )


# ---------------------------------------------------------------------------
# (a) gt with value == max_val in compile mode
# ---------------------------------------------------------------------------


class TestGtMaxValCompileMode:
    """gt with max_val returns qbool(False) without crash in compile mode."""

    def test_gt_max_val_4bit_returns_false(self):
        """4-bit qint > 15 should return qbool(False) immediately."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a > 15

        assert isinstance(result, ql.qbool)
        # No gt IR entry should be recorded (trivially false)
        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 0

    def test_gt_max_val_3bit_returns_false(self):
        """3-bit qint > 7 should return qbool(False) immediately."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a > 7

        assert isinstance(result, ql.qbool)
        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 0

    def test_gt_above_max_val_returns_false(self):
        """4-bit qint > 100 should return qbool(False)."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a > 100

        assert isinstance(result, ql.qbool)
        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 0

    def test_gt_negative_returns_true(self):
        """4-bit qint > -1 should return qbool(True) immediately."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a > -1

        assert isinstance(result, ql.qbool)
        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 0

    def test_gt_valid_value_records_ir(self):
        """4-bit qint > 5 should record a gt IR entry."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(10, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a > 5

        assert isinstance(result, ql.qbool)
        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 1
        assert gt_entries[0].uncontrolled_seq != 0


# ---------------------------------------------------------------------------
# (b) lt with value 0 or negative in compile mode
# ---------------------------------------------------------------------------


class TestLtEdgeCasesCompileMode:
    """lt overflow guards work correctly in compile mode."""

    def test_lt_zero_returns_false(self):
        """4-bit qint < 0 should return qbool(False) immediately."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a < 0

        assert isinstance(result, ql.qbool)
        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 0

    def test_lt_negative_returns_false(self):
        """4-bit qint < -5 should return qbool(False) immediately."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a < -5

        assert isinstance(result, ql.qbool)
        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 0

    def test_lt_above_max_val_returns_true(self):
        """4-bit qint < 100 should return qbool(True) immediately."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(5, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a < 100

        assert isinstance(result, ql.qbool)
        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 0

    def test_lt_valid_value_records_ir(self):
        """4-bit qint < 5 should record an lt IR entry."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a < 5

        assert isinstance(result, ql.qbool)
        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        assert lt_entries[0].uncontrolled_seq != 0


# ---------------------------------------------------------------------------
# (c) QQ comparisons with different-width operands in compile mode
# ---------------------------------------------------------------------------


class TestQQDifferentWidthCompileMode:
    """QQ lt/gt with different-width operands produce correct register sizes."""

    def test_lt_qq_different_widths_3_4(self):
        """QQ lt with 3-bit and 4-bit operands records valid IR."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=3)
        b = ql.qint(10, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a < b

        assert isinstance(result, ql.qbool)
        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        assert lt_entries[0].uncontrolled_seq != 0
        assert lt_entries[0].controlled_seq != 0
        # Register tuple should have 2*_comp_bits + 3 entries
        # _comp_bits = max(3,4) = 4, so 2*4+3 = 11
        assert len(lt_entries[0].registers) == 11

    def test_lt_qq_different_widths_4_3(self):
        """QQ lt with 4-bit and 3-bit operands (reversed) records valid IR."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(10, width=4)
        b = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a < b

        assert isinstance(result, ql.qbool)
        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        # _comp_bits = max(4,3) = 4, so 2*4+3 = 11
        assert len(lt_entries[0].registers) == 11

    def test_gt_qq_different_widths_3_4(self):
        """QQ gt with 3-bit and 4-bit operands records valid IR."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(10, width=4)
        b = ql.qint(3, width=3)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a > b

        assert isinstance(result, ql.qbool)
        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 1
        assert gt_entries[0].uncontrolled_seq != 0
        assert gt_entries[0].controlled_seq != 0
        # _comp_bits = max(4,3) = 4, so 2*4+3 = 11
        assert len(gt_entries[0].registers) == 11

    def test_lt_qq_same_width(self):
        """QQ lt with same-width operands still works correctly."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(3, width=4)
        b = ql.qint(10, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a < b

        assert isinstance(result, ql.qbool)
        lt_entries = [r for r in block._instruction_ir if r.name == "lt"]
        assert len(lt_entries) == 1
        # _comp_bits = 4, 2*4+3 = 11
        assert len(lt_entries[0].registers) == 11

    def test_gt_qq_different_widths_2_4(self):
        """QQ gt with 2-bit and 4-bit operands records valid IR."""
        ql.circuit()
        ql.option("fault_tolerant", False)
        a = ql.qint(2, width=2)
        b = ql.qint(1, width=4)

        @ql.compile
        def dummy(x):
            return x

        block = _make_block()
        with dummy.compile_mode(block):
            result = a > b

        assert isinstance(result, ql.qbool)
        gt_entries = [r for r in block._instruction_ir if r.name == "gt"]
        assert len(gt_entries) == 1
        # _comp_bits = max(2,4) = 4, so 2*4+3 = 11
        assert len(gt_entries[0].registers) == 11
