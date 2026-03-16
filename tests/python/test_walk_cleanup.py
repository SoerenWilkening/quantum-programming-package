"""Tests for final walk module cleanup [Quantum_Assembly-zoe].

Verifies:
- No emit_* references remain in walk modules.
- No raw .qubits[ extraction remains in walk modules.
- No _collect_qubits usage remains in walk modules.
- No from ._gates import lines remain in walk modules.
"""

import os
import re
from pathlib import Path


def _walk_module_sources():
    """Return list of (filename, content) for all walk_*.py modules."""
    src_dir = Path(__file__).resolve().parent.parent.parent / "src" / "quantum_language"
    results = []
    for fname in sorted(os.listdir(src_dir)):
        if fname.startswith("walk_") and fname.endswith(".py"):
            fpath = src_dir / fname
            results.append((fname, fpath.read_text()))
    return results


class TestNoEmitImports:
    """Walk modules must not contain any emit_* references."""

    def test_no_emit_imports(self):
        """No walk_*.py source file should reference 'emit_'."""
        pattern = re.compile(r"emit_")
        violations = []

        for fname, content in _walk_module_sources():
            for lineno, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{fname}:{lineno}: {line.strip()}")

        assert not violations, (
            "walk_*.py files must not contain 'emit_' references:\n"
            + "\n".join(violations)
        )


class TestNoRawQubitExtraction:
    """Walk modules must not use raw .qubits[ extraction."""

    def test_no_raw_qubit_extraction(self):
        r"""No walk_*.py source file should contain '.qubits[' patterns."""
        pattern = re.compile(r"\.qubits\[")
        violations = []

        for fname, content in _walk_module_sources():
            for lineno, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{fname}:{lineno}: {line.strip()}")

        assert not violations, (
            "walk_*.py files must not contain '.qubits[' extraction:\n"
            + "\n".join(violations)
        )


class TestNoCollectQubits:
    """Walk modules must not import or use _collect_qubits."""

    def test_no_collect_qubits(self):
        """No walk_*.py source file should reference '_collect_qubits'."""
        pattern = re.compile(r"_collect_qubits")
        violations = []

        for fname, content in _walk_module_sources():
            for lineno, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{fname}:{lineno}: {line.strip()}")

        assert not violations, (
            "walk_*.py files must not reference '_collect_qubits':\n"
            + "\n".join(violations)
        )


class TestNoGatesImport:
    """Walk modules must not import from ._gates."""

    def test_no_gates_import(self):
        """No walk_*.py source file should contain 'from ._gates import'."""
        pattern = re.compile(r"from \._gates import")
        violations = []

        for fname, content in _walk_module_sources():
            for lineno, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{fname}:{lineno}: {line.strip()}")

        assert not violations, (
            "walk_*.py files must not contain 'from ._gates import':\n"
            + "\n".join(violations)
        )
