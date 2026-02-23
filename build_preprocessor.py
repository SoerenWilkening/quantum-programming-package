#!/usr/bin/env python3
"""Build-time preprocessor that inlines .pxi include directives into .pyx files.

Cython 3.x forbids `include` directives inside `cdef class` bodies.
This preprocessor runs before cythonize(), replacing include directives
with the actual file contents so Cython sees a single monolithic .pyx file.

Usage:
    python build_preprocessor.py                 # preprocess all .pyx with includes
    python build_preprocessor.py --check         # verify preprocessed output is current
    python build_preprocessor.py --sync-and-stage # regenerate if stale, auto-stage (pre-commit hook)
"""

import re
import subprocess
import sys
from pathlib import Path

INCLUDE_RE = re.compile(r'^(\s*)include\s+"([^"]+)"\s*$', re.MULTILINE)

SRC_DIR = Path(__file__).parent / "src" / "quantum_language"


def process_includes(source_file: Path, output_file: Path) -> bool:
    """Preprocess a .pyx file, inlining any include directives.

    Args:
        source_file: Path to the .pyx file with include directives.
        output_file: Path to write the preprocessed output.

    Returns:
        True if includes were found and processed, False if no includes.
    """
    source_dir = source_file.parent
    lines = source_file.read_text().splitlines(keepends=True)
    result = []
    found_includes = False

    for line in lines:
        m = INCLUDE_RE.match(line)
        if m:
            found_includes = True
            indent = m.group(1)
            include_path = source_dir / m.group(2)
            if not include_path.exists():
                raise FileNotFoundError(
                    f"Include file not found: {include_path} (referenced from {source_file})"
                )
            include_content = include_path.read_text()
            result.append(f'{indent}# BEGIN include "{m.group(2)}"\n')
            result.append(include_content)
            # Ensure trailing newline
            if include_content and not include_content.endswith("\n"):
                result.append("\n")
            result.append(f'{indent}# END include "{m.group(2)}"\n')
        else:
            result.append(line)

    if found_includes:
        output_file.write_text("".join(result))
    return found_includes


def preprocess_all(src_dir: Path = SRC_DIR) -> list[Path]:
    """Find all .pyx files with include directives and preprocess them.

    Preprocessed files are written as *_preprocessed.pyx alongside originals.

    Returns:
        List of (original, preprocessed) path tuples for files that were processed.
    """
    processed = []
    for pyx_file in sorted(src_dir.rglob("*.pyx")):
        # Skip already-preprocessed files
        if pyx_file.stem.endswith("_preprocessed"):
            continue
        # Check if file contains include directives
        content = pyx_file.read_text()
        if INCLUDE_RE.search(content):
            output = pyx_file.with_name(pyx_file.stem + "_preprocessed" + pyx_file.suffix)
            process_includes(pyx_file, output)
            processed.append((pyx_file, output))
            print(f"  Preprocessed: {pyx_file.name} -> {output.name}")
    return processed


def _generate_content(source_file: Path) -> str | None:
    """Regenerate preprocessed content from a source .pyx file.

    Returns:
        The preprocessed content as a string, or None if no includes found.
    """
    source_dir = source_file.parent
    lines = source_file.read_text().splitlines(keepends=True)
    result = []
    found_includes = False

    for line in lines:
        m = INCLUDE_RE.match(line)
        if m:
            found_includes = True
            indent = m.group(1)
            include_path = source_dir / m.group(2)
            if not include_path.exists():
                raise FileNotFoundError(
                    f"Include file not found: {include_path} (referenced from {source_file})"
                )
            include_content = include_path.read_text()
            result.append(f'{indent}# BEGIN include "{m.group(2)}"\n')
            result.append(include_content)
            if include_content and not include_content.endswith("\n"):
                result.append("\n")
            result.append(f'{indent}# END include "{m.group(2)}"\n')
        else:
            result.append(line)

    if found_includes:
        return "".join(result)
    return None


def sync_and_stage(src_dir: Path = SRC_DIR) -> int:
    """Regenerate preprocessed .pyx files if stale, and auto-stage them.

    Iterates over all .pyx files with include directives, regenerates the
    preprocessed output, compares with existing file, and if different,
    writes the new content and stages it with git add.

    Returns:
        0 always (auto-fix hook should not block commits after fixing).
    """
    for pyx_file in sorted(src_dir.rglob("*.pyx")):
        if pyx_file.stem.endswith("_preprocessed"):
            continue
        content = pyx_file.read_text()
        if not INCLUDE_RE.search(content):
            continue

        output = pyx_file.with_name(pyx_file.stem + "_preprocessed" + pyx_file.suffix)
        new_content = _generate_content(pyx_file)
        if new_content is None:
            continue

        # Compare with existing preprocessed file
        old_content = output.read_text() if output.exists() else ""
        if old_content != new_content:
            output.write_text(new_content)
            print(f"Drift detected: {output.name} -- regenerated and staging")
            subprocess.run(["git", "add", "-f", str(output)], check=True)
        # If same: no action needed

    return 0


def check_mode(src_dir: Path = SRC_DIR) -> int:
    """Verify preprocessed files are up to date without modifying them.

    Returns:
        0 if all files are current, 1 if any are stale.
    """
    stale = False
    for pyx_file in sorted(src_dir.rglob("*.pyx")):
        if pyx_file.stem.endswith("_preprocessed"):
            continue
        content = pyx_file.read_text()
        if not INCLUDE_RE.search(content):
            continue

        output = pyx_file.with_name(pyx_file.stem + "_preprocessed" + pyx_file.suffix)
        new_content = _generate_content(pyx_file)
        if new_content is None:
            continue

        old_content = output.read_text() if output.exists() else ""
        if old_content != new_content:
            print(f"STALE: {output.name} (regenerate with: python build_preprocessor.py)")
            stale = True
        else:
            print(f"OK: {output.name}")

    if stale:
        return 1
    print("All preprocessed files are current.")
    return 0


if __name__ == "__main__":
    if "--sync-and-stage" in sys.argv:
        sys.exit(sync_and_stage())
    elif "--check" in sys.argv:
        sys.exit(check_mode())
    else:
        results = preprocess_all()
        if not results:
            print("No .pyx files with include directives found.")
        else:
            print(f"Preprocessed {len(results)} file(s).")
            for orig, out in results:
                print(f"  {orig} -> {out}")
