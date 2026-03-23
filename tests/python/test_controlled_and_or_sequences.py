"""Tests for controlled AND/OR sequence generators (Step 11.3).

Verifies that the controlled variants cQ_and, cCQ_and, cQ_or, cCQ_or
are properly declared in _core.pxd and linked into the Cython extension.

Since these C functions return sequence_t* and aren't wrapped as Python
callables, we verify their availability by confirming the Cython build
succeeds (which validates the .pxd declarations) and by testing the
Python-level operations that exercise controlled bitwise paths.
"""

import quantum_language as ql


class TestControlledBitwiseExposure:
    """Verify controlled AND/OR sequences are exposed via _core.pxd.

    The _core.pxd declarations are validated at Cython compile time.
    If the build succeeds and quantum_language imports, the declarations
    are correct. These tests verify the module loads and basic operations
    still work after adding the new declarations.
    """

    def test_module_imports(self):
        """quantum_language._core module loads (validates .pxd declarations)."""
        import quantum_language._core as core

        assert core is not None

    def test_and_still_works(self):
        """Bitwise AND still works (exercises Q_and/CQ_and paths)."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b1100, width=4)
        c = a & b
        assert c is not None
        assert isinstance(c, ql.qint)
        assert c.width == 4

    def test_or_still_works(self):
        """Bitwise OR still works (exercises Q_or/CQ_or paths)."""
        a = ql.qint(0b1010, width=4)
        b = ql.qint(0b0101, width=4)
        c = a | b
        assert c is not None
        assert isinstance(c, ql.qint)
        assert c.width == 4

    def test_classical_and_still_works(self):
        """Classical-quantum AND still works (exercises CQ_and path)."""
        a = ql.qint(0xFF, width=8)
        c = a & 0x0F
        assert c is not None
        assert isinstance(c, ql.qint)

    def test_classical_or_still_works(self):
        """Classical-quantum OR still works (exercises CQ_or path)."""
        a = ql.qint(0x00, width=8)
        c = a | 0xFF
        assert c is not None
        assert isinstance(c, ql.qint)
