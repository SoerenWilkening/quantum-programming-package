"""Tests for walk migration and exports [Quantum_Assembly-be5].

Verifies:
- walk and walk_diffusion are importable from quantum_language
- QWalkTree is no longer importable
- walk_diffusion is callable
- Skill file .claude/commands/quantum-walk.md exists
"""

from pathlib import Path

import pytest

import quantum_language as ql


class TestWalkExports:
    """walk and walk_diffusion are importable from quantum_language."""

    def test_walk_importable(self):
        from quantum_language import walk
        assert callable(walk)

    def test_walk_diffusion_importable(self):
        from quantum_language import walk_diffusion
        assert callable(walk_diffusion)

    def test_walk_in_all(self):
        assert "walk" in ql.__all__

    def test_walk_diffusion_in_all(self):
        assert "walk_diffusion" in ql.__all__

    def test_walk_is_function(self):
        assert hasattr(ql, "walk")
        assert callable(ql.walk)

    def test_walk_diffusion_is_function(self):
        assert hasattr(ql, "walk_diffusion")
        assert callable(ql.walk_diffusion)


class TestQWalkTreeRemoved:
    """QWalkTree is no longer importable after removal."""

    def test_qwalktree_not_in_namespace(self):
        assert not hasattr(ql, "QWalkTree")

    def test_qwalktree_not_in_all(self):
        assert "QWalkTree" not in ql.__all__

    def test_walk_module_not_importable(self):
        with pytest.raises(ImportError):
            from quantum_language.walk import QWalkTree  # noqa: F401


class TestFixedDiffusionRemoved:
    """walk_diffusion_fixed is no longer importable after removal."""

    def test_walk_diffusion_fixed_not_in_namespace(self):
        assert not hasattr(ql, "walk_diffusion_fixed")

    def test_walk_diffusion_fixed_not_in_all(self):
        assert "walk_diffusion_fixed" not in ql.__all__

    def test_walk_diffusion_fixed_not_importable_from_module(self):
        with pytest.raises(ImportError):
            from quantum_language.walk_diffusion import walk_diffusion_fixed  # noqa: F401

    def test_fixed_diffusion_not_importable_from_module(self):
        with pytest.raises(ImportError):
            from quantum_language.walk_diffusion import _fixed_diffusion  # noqa: F401

    def test_apply_fixed_diffusion_not_importable(self):
        with pytest.raises(ImportError):
            from quantum_language.walk_operators import _apply_fixed_diffusion  # noqa: F401


class TestNoEmitXInWalkModules:
    """Verify that walk modules do not use emit_x directly [Quantum_Assembly-rm9]."""

    def test_no_emit_x_in_walk_modules(self):
        """No walk_*.py source file should contain 'emit_x(' calls."""
        import os
        import re

        src_dir = Path(__file__).resolve().parent.parent.parent / "src" / "quantum_language"
        pattern = re.compile(r"emit_x\(")
        violations = []

        for fname in sorted(os.listdir(src_dir)):
            if fname.startswith("walk_") and fname.endswith(".py"):
                fpath = src_dir / fname
                content = fpath.read_text()
                for lineno, line in enumerate(content.splitlines(), 1):
                    if pattern.search(line):
                        violations.append(f"{fname}:{lineno}: {line.strip()}")

        assert not violations, (
            "walk_*.py files must not contain emit_x( calls:\n"
            + "\n".join(violations)
        )


class TestSkillFile:
    """Skill file .claude/commands/quantum-walk.md exists and covers all phases."""

    @pytest.fixture()
    def skill_path(self):
        repo_root = Path(__file__).resolve().parent.parent.parent
        return repo_root / ".claude" / "commands" / "quantum-walk.md"

    def test_skill_file_exists(self, skill_path):
        assert skill_path.exists(), f"Skill file not found: {skill_path}"

    def test_skill_file_covers_phase1(self, skill_path):
        content = skill_path.read_text()
        assert "Phase 1" in content

    def test_skill_file_covers_phase2(self, skill_path):
        content = skill_path.read_text()
        assert "Phase 2" in content

    def test_skill_file_covers_phase3(self, skill_path):
        content = skill_path.read_text()
        assert "Phase 3" in content

    def test_skill_file_covers_phase4(self, skill_path):
        content = skill_path.read_text()
        assert "Phase 4" in content
