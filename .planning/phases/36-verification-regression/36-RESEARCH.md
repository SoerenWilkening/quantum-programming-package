# Phase 36: Verification & Regression - Research

**Researched:** 2026-02-01
**Domain:** Pytest xfail marker cleanup, test suite regression verification
**Confidence:** HIGH

## Summary

Phase 36 verifies that all bugs fixed in Phases 34 and 35 remain fixed by converting xfail-marked tests to normal passing tests and running comprehensive regression verification. This is the final phase of the v1.6 milestone (Array & Comparison Fixes).

The primary technical work involves removing `@pytest.mark.xfail` decorators from tests that were marked as expected failures due to known bugs (BUG-ARRAY-INIT, BUG-CMP-01, BUG-CMP-02). According to pytest best practices with strict xfail, when a bug is fixed, the xfailing tests will show as XPASS (unexpectedly passing), signaling that the marker should be removed. The workflow is: fix bug → tests XPASS → remove marker → tests pass normally → regression protection active.

The test suite uses pytest 9.0.2 with strict markers enabled (`--strict-markers` in pytest.ini), which means XPASS(strict=True) tests show as "FAILED" in the output (pytest's safety mechanism). This is expected behavior, not actual failures. The phase must distinguish between real failures and XPASS "failures", then systematically remove xfail markers to convert XPASS tests into regular passing tests.

**Primary recommendation:** Use a systematic three-step approach: (1) identify all xfail markers referencing fixed bugs, (2) remove markers and verify tests pass, (3) run full regression suite to confirm no previously passing tests have regressed.

## Standard Stack

### Core Testing Tools

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test framework | De facto standard for Python testing, used throughout project |
| pytest markers | Built-in | Test categorization and xfail handling | Native pytest feature for managing test expectations |

### Supporting Tools

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| pytest --co | Built-in | Test collection without execution | Verify which tests will run before executing |
| pytest -v | Built-in | Verbose output | See individual test results during verification |
| pytest -x | Built-in | Stop on first failure | Quick failure identification during debugging |
| pytest --lf | Built-in | Last failed | Re-run previously failed tests |
| pytest --tb=short | Built-in | Short traceback format | Configured in pytest.ini for cleaner output |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual marker removal | pytest-regtest snapshots | Regression tests don't need snapshots, just xfail removal |
| Full suite runs | Targeted test selection | Full suite needed for comprehensive regression check |
| pytest-regressions plugin | Native pytest xfail workflow | xfail workflow is simpler and already in use |

**Configuration:**
```ini
# Already configured in pytest.ini
[pytest]
testpaths = tests/python
python_files = test_*.py
python_classes = Test*
python_functions = test_*
pythonpath = src
addopts = -v --tb=short --strict-markers
```

## Architecture Patterns

### Recommended Workflow Structure

Phase 36 follows a verification-before-cleanup pattern:

```
1. Pre-verification
   ├── Identify xfail markers for fixed bugs
   ├── Count XPASS tests (should match xfail count)
   └── Verify no unexpected failures

2. Marker Removal
   ├── Remove xfail markers for BUG-ARRAY-INIT (test_array_verify.py)
   ├── Remove xfail markers for BUG-CMP-01 (test_compare.py, test_uncomputation.py)
   ├── Remove xfail markers for BUG-CMP-02 (test_compare.py, test_uncomputation.py)
   └── Preserve unrelated xfail markers (BUG-COND-MUL-01, etc.)

3. Regression Verification
   ├── Run full test suite (all tests/)
   ├── Verify 0 failures, 0 unexpected failures
   ├── Compare pass counts before/after
   └── Document test coverage metrics
```

### Pattern 1: Strict Xfail as Bug-Fix Detector

**What:** Using `@pytest.mark.xfail(strict=True)` creates a "ratchet" that automatically detects when bugs are fixed.

**When to use:** Always use `strict=True` when marking tests for known bugs that will eventually be fixed.

**How it works:**
```python
# Before fix: test fails, shows as "xfailed" (expected, doesn't fail suite)
@pytest.mark.xfail(reason="BUG-CMP-01: eq returns inverted results", strict=True)
def test_eq_comparison():
    assert qint(3) == qint(3)  # Fails due to bug

# After fix: test passes, shows as "FAILED" with XPASS message
# This signals: remove the marker
@pytest.mark.xfail(reason="BUG-CMP-01: eq returns inverted results", strict=True)
def test_eq_comparison():
    assert qint(3) == qint(3)  # Now passes! Remove marker

# After marker removal: test passes normally
def test_eq_comparison():
    assert qint(3) == qint(3)  # Regular passing test, regression protection active
```

**Source:** [Paul Ganssle - How and why I use pytest's xfail](https://blog.ganssle.io/articles/2021/11/pytest-xfail.html)

### Pattern 2: XPASS Detection in Test Output

**What:** Distinguishing between real failures and XPASS "failures" in pytest output.

**Recognition patterns:**
```
FAILED test_compare.py::test_qq_cmp_exhaustive[3-3-3-eq] - XPASS(strict)
  → This is GOOD: test passed but has xfail marker (remove marker)

FAILED test_compare.py::test_qq_cmp_exhaustive[3-3-3-eq]
  → This is BAD: test actually failed (investigate)
```

**Counting tests:**
```bash
# Count XPASS tests (should match expected xfail removals)
pytest -v | grep "XPASS(strict)" | wc -l

# Count real failures (should be 0 after fixes)
pytest -v | grep "FAILED" | grep -v "XPASS" | wc -l
```

### Pattern 3: Incremental Marker Removal

**What:** Remove xfail markers incrementally by bug category, verifying at each step.

**Why:** Safer than bulk removal, easier to debug if issues arise.

**Example workflow:**
```bash
# Step 1: Remove BUG-ARRAY-INIT markers
# Edit test_array_verify.py, remove xfail decorators
pytest tests/test_array_verify.py -v
# Verify: all tests pass

# Step 2: Remove BUG-CMP-01 markers (eq/ne)
# Edit test_compare.py, test_uncomputation.py
pytest tests/test_compare.py tests/test_uncomputation.py -v -k "eq or ne"
# Verify: eq/ne tests pass

# Step 3: Remove BUG-CMP-02 markers (lt/gt)
# Edit same files for ordering comparisons
pytest tests/test_compare.py tests/test_uncomputation.py -v -k "lt or gt"
# Verify: lt/gt tests pass

# Step 4: Full regression check
pytest tests/ -v
# Verify: 0 failures, 0 unexpected failures
```

**Source:** [How to use skip and xfail - pytest documentation](https://docs.pytest.org/en/stable/how-to/skipping.html)

### Anti-Patterns to Avoid

- **Removing markers without verifying tests pass:** Always run tests before committing marker removals
- **Leaving outdated xfail markers:** Accumulation of obsolete markers hides test coverage and creates confusion
- **Over-relying on xfail:** Use only for documented known bugs, not for flaky tests or "works on my machine" issues
- **Removing markers for unrelated bugs:** Only remove markers for bugs fixed in Phases 34-35 (BUG-ARRAY-INIT, BUG-CMP-01, BUG-CMP-02)

**Source:** [Ultimate Guide To Pytest Markers](https://pytest-with-eric.com/pytest-best-practices/pytest-markers/)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Snapshot/baseline testing | Custom file comparison | pytest-regressions | Handles image, data, numeric regression testing with fixtures |
| Test result tracking | Parse pytest output manually | pytest --json-report or pytest-json-report plugin | Structured output for CI/CD integration |
| Flaky test retry | Custom retry decorator | pytest-rerunfailures | Standard plugin with configurable retry logic |
| Parallel test execution | Custom multiprocessing | pytest-xdist | Handles test distribution, fixture scoping, and result aggregation |

**Key insight:** Pytest's ecosystem has mature plugins for almost every testing pattern. For Phase 36, native xfail workflow is sufficient - no additional plugins needed.

## Common Pitfalls

### Pitfall 1: Misinterpreting XPASS as Failure

**What goes wrong:** Seeing "FAILED" in pytest output for XPASS(strict) tests and thinking the test suite is broken.

**Why it happens:** pytest's strict mode marks unexpected passes as failures to force attention. This is a safety mechanism, not an error.

**How to avoid:**
- Always check for "(strict)" in XPASS failure messages
- Use `grep "XPASS(strict)"` to count expected "failures"
- Understand that XPASS = "test passed, remove marker"

**Warning signs:**
```
# XPASS "failure" (good - remove marker):
FAILED [...] - XPASS(strict): BUG-CMP-01 fixed

# Real failure (bad - investigate):
FAILED [...] - AssertionError: expected 1, got 0
```

### Pitfall 2: Incomplete Marker Removal

**What goes wrong:** Removing xfail decorator from function but leaving it in parametrize marks, or vice versa.

**Why it happens:** Tests can have multiple xfail markers (function-level, parametrize-level, class-level).

**How to avoid:**
- Search for bug ID (e.g., "BUG-CMP-01") across entire file
- Check both `@pytest.mark.xfail()` function decorators and `marks=pytest.mark.xfail()` in parametrize
- Verify removal with `pytest --co -v` (markers shown in collection output)

**Example of multiple marker locations:**
```python
# Function-level marker
@pytest.mark.xfail(reason="BUG-CMP-01", strict=True)
def test_eq():
    ...

# Parametrize-level marker
@pytest.mark.parametrize("op", [
    pytest.param("eq", marks=pytest.mark.xfail(reason="BUG-CMP-01", strict=True)),
    "ne",
])
def test_comparison(op):
    ...
```

### Pitfall 3: Breaking Previously Passing Tests

**What goes wrong:** Removing xfail markers causes new failures due to test environment changes or incomplete bug fixes.

**Why it happens:**
- Test passes in isolation but fails when run with full suite (state pollution)
- Bug fix was incomplete or introduced regressions
- Test relies on fixtures or conftest.py changes

**How to avoid:**
1. Run individual test file first: `pytest tests/test_compare.py`
2. Then run related tests: `pytest tests/test_*.py`
3. Finally run full suite: `pytest tests/`
4. Compare total pass counts before/after (should increase, not decrease)

**Verification checklist:**
- [ ] Individual test file passes
- [ ] Related test files pass together
- [ ] Full test suite passes
- [ ] Pass count increased by number of xfail markers removed
- [ ] No new failures in previously passing tests

### Pitfall 4: Forgetting to Remove Markers

**What goes wrong:** Leaving xfail markers on tests that now pass, thinking XPASS is acceptable.

**Why it happens:** XPASS with `strict=False` doesn't fail the suite, so marker removal feels optional.

**How to avoid:**
- Phase 36 explicitly requires marker removal (success criteria)
- Regular marker audits: `grep -r "xfail.*BUG-" tests/`
- Document marker removal in commit messages

**Warning signs:**
- Tests showing XPASS in CI/CD for multiple releases
- xfail markers with "FIXED" or "RESOLVED" in reason text
- Test history shows test passing for months but still marked xfail

**Source:** [pytest tips and tricks](https://pythontest.com/pytest-tips-tricks/)

## Code Examples

Verified patterns from official sources:

### Example 1: Identifying Tests to Cleanup

```python
# File: tests/test_compare.py
# Current state (before Phase 36):

_XFAIL_EQ = pytest.mark.xfail(
    reason="BUG-CMP-01: eq returns inverted result (always 0 for equal values)",
    strict=True,
)
_XFAIL_NE = pytest.mark.xfail(
    reason="BUG-CMP-01: ne returns inverted result (always 0 for unequal values)",
    strict=True,
)
_XFAIL_ORDER = pytest.mark.xfail(
    reason="BUG-CMP-02: ordering comparison error for this (width, a, b) triple",
    strict=True,
)

# After Phase 36: Remove these marker definitions and all usages
```

### Example 2: Removing Parametrize-Level Markers

```python
# Before (from tests/test_uncomputation.py):
@pytest.mark.parametrize(
    "op_name,a,b,expected",
    [
        pytest.param("eq", 2, 2, 1, marks=pytest.mark.xfail(
            reason="BUG-CMP-01: eq/ne return inverted results",
            strict=False,
        )),
        ("lt", 1, 2, 1),  # This one passes
    ],
)
def test_uncomp_comparison(op_name, a, b, expected):
    # Test implementation
    pass

# After Phase 36:
@pytest.mark.parametrize(
    "op_name,a,b,expected",
    [
        ("eq", 2, 2, 1),  # Marker removed
        ("lt", 1, 2, 1),
    ],
)
def test_uncomp_comparison(op_name, a, b, expected):
    # Test implementation unchanged
    pass
```

### Example 3: Verification Commands

```bash
# Pre-verification: Count XPASS tests (should match expected removals)
pytest tests/test_compare.py -v 2>&1 | grep -c "XPASS(strict)"
# Expected: ~240 for BUG-CMP-01 + ~104 for BUG-CMP-02 = 344

# Run cleanup on one file at a time
pytest tests/test_array_verify.py -v
# Expected: All tests pass, no xfail markers remain

# Full regression check
pytest tests/ -v --tb=short
# Expected: 0 failures, 0 xfailed, increased pass count

# Compare before/after pass counts
pytest tests/ -v 2>&1 | grep "passed" | tail -1
# Before: e.g., "1200 passed, 344 xpassed"
# After:  e.g., "1544 passed" (1200 + 344)
```

**Source:** [pytest documentation - How to use skip and xfail](https://docs.pytest.org/en/stable/how-to/skipping.html)

### Example 4: Git Workflow for Marker Removal

```bash
# Create feature branch (if needed)
git checkout -b fix/remove-xfail-markers

# Edit test files to remove xfail markers
# - tests/test_array_verify.py (BUG-ARRAY-INIT)
# - tests/test_compare.py (BUG-CMP-01, BUG-CMP-02)
# - tests/test_uncomputation.py (BUG-CMP-01)

# Verify tests pass after each file
pytest tests/test_array_verify.py -v
pytest tests/test_compare.py -v
pytest tests/test_uncomputation.py -v

# Run full regression suite
pytest tests/ -v

# Commit with descriptive message
git add tests/test_array_verify.py tests/test_compare.py tests/test_uncomputation.py
git commit -m "test(36): remove xfail markers for fixed bugs

Phase 36: Verification & Regression
- Remove BUG-ARRAY-INIT markers (7 tests)
- Remove BUG-CMP-01 markers (488 tests)
- Remove BUG-CMP-02 markers (104 tests)
- All tests now pass as regular regression tests
- Full test suite passes with 0 failures

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual test skip | pytest xfail with strict mode | pytest 3.0+ (2016) | Automatic detection of fixed bugs via XPASS |
| Leave xfail markers indefinitely | Remove after bug fix | Community best practice (2020+) | Markers as temporary documentation, not permanent state |
| Comment out failing tests | Mark with xfail + reason | pytest 2.0+ (2011) | Tests stay in suite, document known issues |
| Global xfail_strict config | Per-marker strict parameter | pytest 5.4+ (2020) | Fine-grained control over strict behavior |

**Deprecated/outdated:**
- `pytest.mark.skipif` for known bugs: Use xfail instead, skip is for platform/environment conditions
- Leaving xfail markers after fixes: Best practice now is immediate removal upon XPASS

**Source:** [Paul Ganssle - How and why I use pytest's xfail](https://blog.ganssle.io/articles/2021/11/pytest-xfail.html)

## Phase-Specific Findings

### Fixed Bugs and Their Test Counts

Based on Phase 34 and 35 summaries:

**BUG-ARRAY-INIT (Phase 34):**
- Location: `tests/test_array_verify.py`
- Markers to remove: 7 xfail tests
- Test functions: `test_array_sum_2elem`, `test_array_sum_overflow`, `test_array_and_2elem`, `test_array_and_1elem`, `test_array_or_2elem`, `test_array_add_scalar`, `test_array_sub_scalar`

**BUG-CMP-01 (Phase 35-01):**
- Locations: `tests/test_compare.py`, `tests/test_uncomputation.py`
- Markers to remove: 488 xfail tests (240 showing XPASS in 35-03 summary)
- Operators affected: eq, ne
- Coverage: Exhaustive tests for widths 1-3, sampled tests for widths 4-5

**BUG-CMP-02 (Phase 35-02, 35-03):**
- Locations: `tests/test_compare.py`, `tests/test_uncomputation.py`
- Markers to remove: 104 xfail tests (60 lt + 44 gt from 35-03 summary)
- Operators affected: lt, gt, le, ge
- Specific cases: `_LT_GE_FAIL_PAIRS` and `_GT_LE_FAIL_PAIRS` tuples

**Markers to KEEP (not fixed in v1.6):**
- BUG-COND-MUL-01: Conditional multiplication bug (deferred to future milestone)
- Any other xfail markers not related to BUG-ARRAY-INIT, BUG-CMP-01, BUG-CMP-02

### Test Suite Configuration

From pytest.ini:
```ini
testpaths = tests/python
```

**Important:** Default testpath is `tests/python/`, but regression tests are also in `tests/` root (test_compare.py, test_array_verify.py, etc.). Full regression must run `pytest tests/` not just `pytest` (which would only run tests/python/).

### Expected Test Metrics

**Before Phase 36:**
- Total tests: ~1500+ (exhaustive comparison tests are numerous)
- Passing: ~1200
- XPASS(strict): ~600 (treated as "FAILED" by pytest)
- xfailed: ~0 (all expected failures now pass)

**After Phase 36:**
- Total tests: ~1500+ (same)
- Passing: ~1800+ (1200 + ~600 from XPASS → PASS conversion)
- XPASS(strict): 0
- xfailed: Remaining (BUG-COND-MUL-01, etc.)

## Open Questions

None. The phase scope is well-defined:
1. Remove xfail markers for fixed bugs (BUG-ARRAY-INIT, BUG-CMP-01, BUG-CMP-02)
2. Verify tests pass
3. Run full regression suite

All necessary information is available in Phase 34/35 summaries and test files.

## Sources

### Primary (HIGH confidence)
- [pytest official documentation - How to use skip and xfail](https://docs.pytest.org/en/stable/how-to/skipping.html) - xfail marker usage and strict mode
- pytest.ini in project root - Actual pytest configuration
- Phase 34-RESEARCH.md - BUG-ARRAY-INIT details and fix verification
- Phase 35-03-SUMMARY.md - BUG-CMP-01 and BUG-CMP-02 resolution details
- Phase 35-VERIFICATION-NEW.md - Verification status and test counts

### Secondary (MEDIUM confidence)
- [Paul Ganssle - How and why I use pytest's xfail](https://blog.ganssle.io/articles/2021/11/pytest-xfail.html) - Best practices for xfail workflow (2021, still current)
- [Ultimate Guide To Pytest Markers](https://pytest-with-eric.com/pytest-best-practices/pytest-markers/) - Marker management best practices
- [pytest tips and tricks](https://pythontest.com/pytest-tips-tricks/) - Practical pytest patterns

### Tertiary (LOW confidence)
- pytest-regressions documentation - Alternative regression testing approach (not needed for this phase)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest 9.0.2 confirmed in use, configuration verified
- Architecture: HIGH - xfail workflow well-documented, Phase 34/35 provide concrete examples
- Pitfalls: HIGH - Based on official pytest documentation and established best practices
- Phase-specific details: HIGH - Exact test counts and locations from Phase 35-03-SUMMARY.md

**Research date:** 2026-02-01
**Valid until:** 90 days (stable pytest features, no rapid changes expected)
