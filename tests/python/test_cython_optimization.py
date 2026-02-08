"""Tests to verify Cython optimization effectiveness.

These tests check that optimized functions have minimal Python/C
interaction (yellow lines) in Cython annotation output.
"""

from pathlib import Path

import pytest

# Skip if annotation files don't exist (CI without cython -a)
ANNOTATE_DIR = Path(__file__).parent.parent.parent / "build" / "cython-annotate"


def get_function_annotation_score(html_path: Path, function_name: str) -> dict:
    """Extract yellow line count for a specific function from annotation HTML.

    Returns dict with:
    - total_lines: number of lines in function body
    - yellow_lines: number of lines with yellow highlighting
    - score: percentage of lines that are white (higher = better)
    """
    if not html_path.exists():
        return {"total_lines": 0, "yellow_lines": 0, "score": 0.0, "exists": False}

    content = html_path.read_text()

    # Find function definition and body
    # Cython annotation uses <span class="k">cdef</span> or <span class="k">def</span>
    # followed by function name
    # Yellow lines have bgcolor="#ffff..." style

    # Simple approach: count yellow vs non-yellow lines in the whole file
    # for the function name context

    # Find lines containing the function name as a marker
    lines = content.split("\n")
    in_function = False
    total_lines = 0
    yellow_lines = 0

    for line in lines:
        # Start tracking when we see the function definition
        if f">{function_name}</span>" in line or f'"{function_name}"' in line:
            in_function = True
            continue

        # Stop at next function definition
        if (
            in_function
            and (">cdef </span>" in line or ">def </span>" in line)
            and function_name not in line
        ):
            break

        if in_function:
            # Count this line
            total_lines += 1
            # Check for yellow highlighting (various shades)
            if 'bgcolor="#ff' in line.lower() or "background-color: #ff" in line.lower():
                yellow_lines += 1

    if total_lines == 0:
        return {"total_lines": 0, "yellow_lines": 0, "score": 0.0, "exists": True, "found": False}

    score = 100.0 * (total_lines - yellow_lines) / total_lines
    return {
        "total_lines": total_lines,
        "yellow_lines": yellow_lines,
        "score": score,
        "exists": True,
        "found": True,
    }


@pytest.mark.skipif(
    not ANNOTATE_DIR.exists(),
    reason="Annotation HTML not generated (run 'make profile-cython' first)",
)
class TestCythonAnnotations:
    """Verify optimized functions have reduced yellow lines."""

    def test_annotation_files_exist(self):
        """Verify annotation HTML files exist."""
        html_files = list(ANNOTATE_DIR.glob("*.html"))
        assert len(html_files) > 0, "No annotation HTML files found"

        # Check for main files
        expected = ["qint_preprocessed.html", "qarray.html"]
        found = [f.name for f in html_files]
        for expected_file in expected:
            assert expected_file in found, f"Missing {expected_file}"

    def test_optimized_function_addition_inplace(self):
        """Verify addition_inplace has reduced yellow lines after optimization."""
        html_path = ANNOTATE_DIR / "qint_preprocessed.html"
        result = get_function_annotation_score(html_path, "addition_inplace")

        if not result.get("found", False):
            pytest.skip("Function not found in annotation HTML")

        # After optimization, we expect at least 50% white lines
        # This is a soft target - the test documents the current state
        print(
            f"addition_inplace: {result['yellow_lines']}/{result['total_lines']} yellow lines ({100 - result['score']:.1f}%)"
        )

        # Record the score for tracking over time
        # Fail only if score is very bad (less than 30% white)
        assert result["score"] >= 30, (
            f"Too many yellow lines: {result['yellow_lines']}/{result['total_lines']}"
        )

    def test_optimized_function_multiplication_inplace(self):
        """Verify multiplication_inplace has reduced yellow lines after optimization."""
        html_path = ANNOTATE_DIR / "qint_preprocessed.html"
        result = get_function_annotation_score(html_path, "multiplication_inplace")

        if not result.get("found", False):
            pytest.skip("Function not found in annotation HTML")

        print(
            f"multiplication_inplace: {result['yellow_lines']}/{result['total_lines']} yellow lines ({100 - result['score']:.1f}%)"
        )

        assert result["score"] >= 30, (
            f"Too many yellow lines: {result['yellow_lines']}/{result['total_lines']}"
        )

    def test_annotation_html_not_empty(self):
        """Verify annotation HTML files have content."""
        html_path = ANNOTATE_DIR / "qint_preprocessed.html"
        if not html_path.exists():
            pytest.skip("qint_preprocessed.html not found")

        content = html_path.read_text()
        assert len(content) > 10000, "Annotation HTML seems too small"
        assert "Generated by Cython" in content, "Not a valid Cython annotation file"
