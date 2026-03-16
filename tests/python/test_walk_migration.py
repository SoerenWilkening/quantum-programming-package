"""Tests for walk migration and exports [Quantum_Assembly-be5].

Verifies:
- walk and walk_diffusion are importable from quantum_language
- QWalkTree raises DeprecationWarning on instantiation
- walk_diffusion is callable
- Skill file .claude/commands/quantum-walk.md exists
"""

import warnings
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


class TestQWalkTreeDeprecation:
    """QWalkTree raises DeprecationWarning on instantiation."""

    def test_deprecation_warning_raised(self):
        ql.circuit()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ql.QWalkTree(max_depth=2, branching=2)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_deprecation_message_content(self):
        ql.circuit()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ql.QWalkTree(max_depth=1, branching=2)
            assert "walk()" in str(w[0].message)
            assert "walk_diffusion()" in str(w[0].message)

    def test_qwalktree_still_works(self):
        """QWalkTree still functions despite deprecation."""
        ql.circuit()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            tree = ql.QWalkTree(max_depth=2, branching=2)
            assert tree.max_depth == 2
            assert tree.total_qubits == 5


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
