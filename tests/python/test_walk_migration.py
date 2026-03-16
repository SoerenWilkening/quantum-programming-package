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
