# Phase 34: Array Fixes - Research

**Researched:** 2026-02-01
**Domain:** Quantum array constructor bug fixes, element-wise operation circuit verification
**Confidence:** HIGH

## Summary

This phase fixes two critical bugs in the quantum array implementation (qarray.pyx) that prevent correct array initialization and element-wise operations. BUG-ARRAY-INIT causes the array constructor to pass `self._width` as the VALUE parameter to `qint()` instead of the WIDTH parameter, resulting in all array elements having quantum value equal to the width specification and auto-inferred widths. This makes operations like `ql.array([3, 5, 7], width=4)` create three qints with value 4 instead of values 3, 5, and 7 at width 4.

The fix is straightforward: change lines 302, 306 in qarray.pyx from `qint(self._width)` to `qint(value, width=self._width)` (or `qint(value.value, width=self._width)` for qint wrapping). Additionally, the dim-based constructor at line 216 has the same issue and needs to be changed from `qint(width or INTEGERSIZE)` to `qint(0, width=(width or INTEGERSIZE))` to initialize with value 0 instead of value width.

7 verification tests are currently xfail'd due to this bug (test_array_verify.py). Once fixed, these tests will automatically pass, verifying that array operations (reductions like sum/all/any and element-wise operations like +/-) produce correct quantum circuits through the full pipeline (Python -> C backend -> OpenQASM -> Qiskit simulation).

**Key finding:** The bug is a simple parameter ordering mistake in the qint constructor calls. The qint signature is `qint(value=0, width=None, ...)` but the array constructor was calling `qint(width)` which interprets width as the value parameter.

## Bug Analysis

### BUG-ARRAY-INIT: Constructor Value/Width Parameter Swap

**Location:** `src/quantum_language/qarray.pyx`, lines 216, 302, 306

**Current buggy code:**
```python
# Line 216 (dim-based initialization)
self._elements = [qint(width or INTEGERSIZE) for _ in range(total)]

# Lines 302-308 (value-based initialization)
for value in flat_data:
    if isinstance(value, qint):
        q = qint(self._width)  # BUG: self._width treated as value
        q.value = value.value
        self._elements.append(q)
    else:
        q = qint(self._width)  # BUG: self._width treated as value
        q.value = value
        self._elements.append(q)
```

**What happens:**
1. User calls `ql.array([3, 5, 7], width=4)`
2. Array constructor sets `self._width = 4`
3. For each value [3, 5, 7], it calls `qint(self._width)` which becomes `qint(4)`
4. Due to qint's signature `qint(value=0, width=None, ...)`, this creates `qint(value=4, width=None)`
5. qint auto-infers width from value 4, which is 3 bits (since 4 = 0b100)
6. Result: Three 3-bit qints each with value 4, instead of three 4-bit qints with values 3, 5, 7

**Why q.value assignment doesn't work:**
After creating `q = qint(4)`, the code tries `q.value = 3` (for first element). However:
- The qint constructor has already applied X gates to initialize the quantum state to |4>
- Setting `.value` is a Python attribute assignment that only changes the classical tracking variable
- It does NOT modify the quantum state (qubits) or add new X gates
- The quantum circuit remains in state |4> regardless of `.value` assignments

**Empirical evidence from test_array_calibration_constructor:**
- `ql.array([1, 2], width=3)` creates 4 qubits (2 elements × 2 bits), not 6 (2 × 3 bits)
- Manual construction `qint(1, width=3); qint(2, width=3)` creates 6 qubits (2 × 3 bits)
- This proves elements are created with auto-width from value instead of specified width

### Element-wise Operation Impact

**How BUG-ARRAY-INIT breaks element-wise operations:**
1. Element widths don't match specified width, causing width mismatches in operations
2. Element values are wrong, so operations produce circuits for wrong computations
3. Example: `A = ql.array([3, 5], width=4); B = ql.array([1, 2], width=4); C = A + B`
   - Expected: 4-bit additions of (3+1) and (5+2)
   - Actual: 3-bit additions of (4+4) and (4+4) due to both arrays having value=4 elements

**Test failures:**
- `test_array_sum_2elem`: Expects sum([1, 2], width=3) = 3, gets wrong circuit
- `test_array_add_scalar`: Expects [1, 2] + 1 = [2, 3], gets wrong values
- All 7 xfail tests rely on correct array initialization to verify operations

## Implementation Structure

### File Locations

**Source files:**
- `/src/quantum_language/qarray.pyx` - Array class implementation (lines 216, 302, 306 need fixes)
- `/src/quantum_language/qint.pyx` - Quantum integer class (signature at line 86)

**Test files:**
- `/tests/test_array_verify.py` - VADV-03 verification tests (7 xfail tests to un-xfail)
- `/tests/test_qarray_elementwise.py` - Element-wise operation unit tests (currently pass)
- `/tests/test_qarray.py` - Basic array functionality tests

**Configuration:**
- `pyproject.toml` - Cython build configuration (no changes needed)
- `setup.py` - Build script (no changes needed, but may need rebuild after fix)

### Constructor Signature Analysis

**qint constructor signature (from qint.pyx:86):**
```python
def __init__(self, value=0, width=None, bits=None, classical=False, create_new=True, bit_list=None):
```

**Parameter semantics:**
- `value`: Initial quantum value (default 0), encoded as |value⟩
- `width`: Bit width (default None = auto-infer from value or use INTEGERSIZE=8)
- When `width=None` and `value != 0`: auto-determines width from `value.bit_length()`
- When `width=None` and `value == 0`: uses default `INTEGERSIZE` (8 bits)

**Correct calling patterns:**
- `qint(5, width=8)` → 8-bit qint with value 5
- `qint(0, width=4)` → 4-bit qint with value 0
- `qint(5)` → auto-width (3-bit) qint with value 5
- `qint(width=8)` → **WRONG**: Creates 4-bit qint with value 8 (auto-width)

### Array Constructor Flow

**Data-based initialization (lines 179-311):**
1. Detect shape from nested list structure via `_detect_shape()`
2. Flatten to 1D list via `_flatten()`
3. Determine width (explicit or inferred from max value)
4. Create qint objects for each value (BUGGY SECTION)
5. Store in `_elements` list with `_shape` metadata

**Dimension-based initialization (lines 194-221):**
1. Parse `dim` parameter (int or tuple)
2. Calculate total elements
3. Create zero-initialized qints or qbools (BUGGY SECTION at line 216)
4. Store with shape tuple

## Fix Strategy

### Required Changes

**Fix 1: Data-based initialization (lines 302-308)**

**Before:**
```python
for value in flat_data:
    if isinstance(value, qint):
        q = qint(self._width)
        q.value = value.value
        self._elements.append(q)
    else:
        q = qint(self._width)
        q.value = value
        self._elements.append(q)
```

**After:**
```python
for value in flat_data:
    if isinstance(value, qint):
        # Create qint with correct width, then copy quantum state via XOR
        q = qint(value.value, width=self._width)
        self._elements.append(q)
    else:
        # Create qint with user value and specified width
        q = qint(value, width=self._width)
        self._elements.append(q)
```

**Rationale:**
- Pass value as first positional argument, width as keyword argument
- Remove `q.value = ...` assignments (they don't affect quantum state)
- For qint wrapping, directly use `value.value` to extract classical value
- Let qint constructor handle X gate initialization to create correct quantum state

**Fix 2: Dimension-based initialization (line 216)**

**Before:**
```python
self._elements = [qint(width or INTEGERSIZE) for _ in range(total)]
```

**After:**
```python
self._elements = [qint(0, width=(width or INTEGERSIZE)) for _ in range(total)]
```

**Rationale:**
- Explicitly pass 0 as value for zero-initialized arrays
- Pass width as keyword argument to avoid ambiguity

### Testing Strategy

**Verification approach:**
1. Make the three-line fix in qarray.pyx
2. Rebuild Cython extensions: `python setup.py build_ext --inplace`
3. Run array verification tests: `pytest tests/test_array_verify.py -v`
4. Expected: 7 xfail tests should PASS (un-xfail automatically)
5. Run full test suite to ensure no regressions

**Test coverage:**
- Lines 216, 302, 306 are all executed by existing tests
- test_array_verify.py exercises both initialization paths
- test_qarray_elementwise.py verifies operations work with correct initialization
- Manual sanity tests (test_manual_sum, etc.) already pass, confirming operations themselves work

**Xfail tests that will pass after fix:**
1. `test_array_sum_2elem` - Sum of [1, 2] with width=3
2. `test_array_sum_overflow` - Sum with overflow wrapping
3. `test_array_and_2elem` - AND reduction of [3, 1]
4. `test_array_and_1elem` - Single element AND (identity)
5. `test_array_or_2elem` - OR reduction of [1, 2]
6. `test_array_add_scalar` - Element-wise [1, 2] + 1
7. `test_array_sub_scalar` - Element-wise [3, 2] - 1

**Note:** Two tests marked xfail are actually xpass (accidentally pass) due to width==value coincidence. These will change to normal pass after fix.

## Dependencies and Integration

### No External Dependencies

All fixes are internal to qarray.pyx. No new imports or libraries needed.

### Integration Points

**qint dependency:**
- qarray relies on qint constructor for element creation
- Fix requires understanding qint signature (already analyzed above)
- No changes to qint itself needed

**Test framework:**
- Uses pytest fixtures from tests/conftest.py (`verify_circuit`)
- Verification pipeline: Python API → C backend → OpenQASM → Qiskit simulation
- Fixture handles circuit reset, QASM export, simulation, result extraction

**Build system:**
- Cython compilation via setup.py or pyproject.toml
- After editing .pyx files, must rebuild: `python setup.py build_ext --inplace`
- Or use `pip install -e .` for development mode

### Element-wise Operations (No Changes Needed)

**Why element-wise ops don't need fixes:**
- Operations (`__add__`, `__sub__`, etc.) are correctly implemented
- They rely on qint operations which work correctly
- Bug is solely in constructor initialization
- Once elements have correct values/widths, operations automatically work

**Evidence from manual tests:**
- `test_manual_sum` passes: manual `qint(1) + qint(2)` works through pipeline
- `test_manual_and` passes: manual `qint(3) & qint(1)` works through pipeline
- This proves operations themselves are correct, only initialization is broken

## Key Decisions for Planning

### Decision 1: Single-plan vs Two-plan Approach

**Recommendation:** Single plan (34-01)

**Rationale:**
- All fixes are in one file (qarray.pyx), three lines total
- Constructor and operations are tightly coupled (can't test ops without working constructor)
- Verification tests exercise both aspects together
- Splitting would create artificial dependency (34-02 would block on 34-01)

**Plan structure:**
1. Fix constructor lines 216, 302, 306
2. Rebuild Cython extension
3. Run test_array_verify.py to verify xfail tests pass
4. Run full test suite for regression check
5. Update xfail markers if needed (or remove them)

### Decision 2: Remove or Keep xfail Markers

**Recommendation:** Remove xfail markers after verifying tests pass

**Rationale:**
- xfail markers document BUG-ARRAY-INIT which will be fixed
- Once fix is verified, markers should be removed (tests are no longer expected to fail)
- Keeping strict=False markers can hide regressions (test failure wouldn't cause CI failure)

**Alternative:** Could keep markers with reason="BUG-ARRAY-INIT fixed in v1.6" for documentation, but standard practice is to remove.

### Decision 3: Additional Verification Tests

**Recommendation:** Use existing tests, no new tests needed

**Rationale:**
- 7 xfail tests already cover constructor and element-wise operations
- Manual sanity tests verify operations work through full pipeline
- Calibration tests document bug empirically
- test_qarray_elementwise.py has extensive unit test coverage (116 tests)
- Adding more tests would be redundant

**Future consideration:** After fix, could add explicit tests for qint wrapping (`ql.array([qint(3), qint(5)])`) if that use case is important, but current tests are sufficient for this phase.

## Architecture Notes

### Array Storage Design

**Current implementation:**
- Flattened storage: 1D list of qint/qbool objects in `_elements`
- Shape metadata: tuple describing dimensions in `_shape`
- Row-major ordering: `arr[i,j]` maps to `_elements[i * cols + j]`
- View semantics: slicing creates new qarray sharing element references

**This design is correct and doesn't need changes.** The bug is only in initialization, not in the overall architecture.

### Width Inference Logic

**Current implementation (lines 269-295):**
```python
if width is not None:
    # Explicit width - check if values fit, warn if truncation needed
    self._width = width
else:
    # Infer width from max value using bit_length()
    numeric_values = [v.value if isinstance(v, qint) else v for v in flat_data]
    self._width = _infer_width(numeric_values)
```

**_infer_width function (lines 17-37):**
- Finds max absolute value
- Uses `max_val.bit_length()` for width
- Floors at `INTEGERSIZE` (8) minimum
- Returns default 8 for all-zero arrays

**This logic is correct.** The bug is that after determining `self._width`, the constructor passes it as value instead of width to qint().

### qint State Initialization

**How qint creates quantum state (from qint.pyx:248-263):**
1. Allocate qubits via circuit allocator
2. Mask value to width: `masked_value = value & ((1 << width) - 1)`
3. For each bit position where value has 1-bit, apply X gate to corresponding qubit
4. This creates quantum state |value⟩ in computational basis

**Why .value assignment doesn't work:**
- X gates are applied during `__init__` based on initial value parameter
- After construction, changing `.value` attribute only affects classical tracking
- No mechanism to retroactively modify quantum state based on `.value` changes
- Would need to apply additional X gates, but constructor doesn't provide that interface

**This is why fix must pass correct value to constructor,** not try to fix it afterward.

## Planning Checklist

For 34-01 plan creation, ensure:
- [ ] Identify exact lines to change (216, 302, 306 in qarray.pyx)
- [ ] Specify exact before/after code for each line
- [ ] Include rebuild command: `python setup.py build_ext --inplace`
- [ ] Specify test command: `pytest tests/test_array_verify.py -v`
- [ ] Document expected outcome: 7 xfail → pass, 5 existing pass stay pass
- [ ] Include regression test: `pytest tests/test_qarray*.py -v` (all should pass)
- [ ] Decide whether to remove xfail markers or leave for documentation
- [ ] Note that no changes to test code are required (tests already written correctly)

## Risk Assessment

**Low risk fixes:**
- Three-line change, very localized
- Fix matches intended design (tests document expected behavior)
- No architectural changes, no new features
- Extensive test coverage already exists

**Potential issues:**
- Cython rebuild might fail if syntax error (unlikely, changes are simple)
- Tests might reveal other issues once initialization works (but manual tests suggest operations are fine)
- Width mismatch warnings might appear if values exceed specified width (but tests use valid ranges)

**Mitigation:**
- Test incrementally: fix one line, rebuild, test, repeat
- Run manual sanity tests first to confirm operations still work
- Check for any new warnings in test output

## References

**Source files analyzed:**
- `/src/quantum_language/qarray.pyx` - Array implementation (lines 1-1049)
- `/src/quantum_language/qint.pyx` - Quantum integer (lines 86-2456, signature analysis)
- `/tests/test_array_verify.py` - Verification tests (lines 1-360, bug documentation)
- `/tests/test_qarray_elementwise.py` - Element-wise operation tests (lines 1-706)
- `/tests/conftest.py` - Test fixtures (verify_circuit pipeline)

**Prior research:**
- Phase 22 Research (array architecture design)
- Phase 24 Research (element-wise operations)
- Phase 33-03 Verification (BUG-ARRAY-INIT discovery and documentation)

**Bug tracking:**
- BUG-ARRAY-INIT first documented in Phase 33 (Advanced Feature Verification)
- 7 xfail tests added to document expected behavior
- Calibration tests prove bug empirically
- v1.6 milestone created specifically to fix this bug

---

**Research complete.** Ready to create 34-01 plan with exact fix specifications.
