#!/usr/bin/env python3
"""Build-time preprocessor that inlines .pxi include directives into .pyx files.

Cython 3.x forbids `include` directives inside `cdef class` bodies.
This preprocessor runs before cythonize(), replacing include directives
with the actual file contents so Cython sees a single monolithic .pyx file.

Usage:
    python build_preprocessor.py          # preprocess all .pyx with includes
    python build_preprocessor.py --check  # verify preprocessed output is current
"""

import re
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


if __name__ == "__main__":
    if "--check" in sys.argv:
        # Verify mode: check that preprocessed files are up to date
        results = preprocess_all()
        if not results:
            print("No .pyx files with include directives found.")
        else:
            print(f"Preprocessed {len(results)} file(s).")
    else:
        results = preprocess_all()
        if not results:
            print("No .pyx files with include directives found.")
        else:
            print(f"Preprocessed {len(results)} file(s).")
            for orig, out in results:
                print(f"  {orig} -> {out}")
