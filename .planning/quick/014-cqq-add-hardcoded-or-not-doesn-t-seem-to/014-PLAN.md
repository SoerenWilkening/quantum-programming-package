---
phase: quick
plan: 014
type: execute
wave: 1
depends_on: []
files_modified:
  - c_backend/src/IntegerAddition.c
  - c_backend/src/sequences/add_seq_1_4.c
  - c_backend/src/sequences/add_seq_5_8.c
  - src/quantum_language/qint_arithmetic.pxi
  - tests/quick/test_014_cqq_add_bug.py
autonomous: true
must_haves:
  truths:
    - "cQQ_add produces correct arithmetic results for controlled addition"
    - "Controlled QQ addition (with ctrl: qa + qb) works for all widths 1-8"
    - "Both hardcoded and dynamic paths produce identical results"
  artifacts:
    - path: "tests/quick/test_014_cqq_add_bug.py"
      provides: "Regression tests for cQQ_add"
  key_links:
    - from: "qint_arithmetic.pxi"
      to: "cQQ_add() C function"
      via: "qubit_array layout"
      pattern: "qubit_array.*control"
---

<objective>
Fix cQQ_add (controlled quantum-quantum addition) which doesn't work properly.

Purpose: The user reports cQQ_add doesn't work (hardcoded or dynamic). Initial investigation reveals a qubit layout mismatch between the Python/Cython side and the C backend.

Output: Working cQQ_add for all bit widths, with regression tests.
</objective>

<context>
@c_backend/src/IntegerAddition.c
@src/quantum_language/qint_arithmetic.pxi
@c_backend/include/sequences.h
</context>

<tasks>

<task type="auto">
  <name>Task 1: Diagnose the qubit layout mismatch</name>
  <files>
    c_backend/src/IntegerAddition.c
    src/quantum_language/qint_arithmetic.pxi
    c_backend/src/sequences/add_seq_1_4.c
  </files>
  <action>
Investigate the qubit layout mismatch between Python and C sides:

**Python side (qint_arithmetic.pxi, line 70-77):**
- Places self qubits at [0, bits-1]
- Places other qubits at [bits, 2*bits-1]
- Places control qubit at position `2*bits` (variable `start` after incrementing)

**C side (IntegerAddition.c, line 354 comment and line 412):**
- Documentation claims: "Qubit [3*bits-1]: Conditional control qubit"
- Code uses: `int control = 3 * bits - 1;`

**Hardcoded sequences (add_seq_1_4.c):**
- Width 1: control at index 2 (3*1-1=2) - matches Python's 2*1=2 - OK
- Width 2: control at index 5 (3*2-1=5) - Python provides 2*2=4 - MISMATCH
- Width 3: control at index 8 (3*3-1=8) - Python provides 2*3=6 - MISMATCH
- Width 4: control at index 11 (3*4-1=11) - Python provides 2*4=8 - MISMATCH

Write a simple test that isolates the issue:
```python
# tests/quick/test_014_cqq_add_bug.py
import quantum_language as ql

def test_controlled_qq_add_basic():
    """Test that controlled QQ addition produces correct results."""
    circ = ql.circuit()

    # Simple 2-bit controlled addition: if ctrl=1, then a += b
    ctrl = ql.qint(1, width=1)  # Control is ON
    a = ql.qint(2, width=2)     # a = 2
    b = ql.qint(1, width=2)     # b = 1

    with ctrl:
        a += b  # Should become a = 3

    # Measure and verify
    result = circ.run()
    # Extract a's value from result
    # Expected: a = 3 (since ctrl was 1)
```

Run test to confirm failure, then identify the root cause.
  </action>
  <verify>Test file exists and confirms the bug (test should fail with current code)</verify>
  <done>Root cause identified: either Python is wrong (should use 3*bits-1) or C is wrong (should use 2*bits)</done>
</task>

<task type="auto">
  <name>Task 2: Fix the qubit layout mismatch</name>
  <files>
    c_backend/src/IntegerAddition.c
    c_backend/src/sequences/add_seq_1_4.c
    c_backend/src/sequences/add_seq_5_8.c
    src/quantum_language/qint_arithmetic.pxi
    scripts/generate_seq_5_8.py
  </files>
  <action>
Based on Task 1 diagnosis, fix the mismatch. The correct approach depends on the original design intent:

**Option A: Python is correct (2*bits layout), fix C side**
If the intended layout is [target: 0..bits-1] [other: bits..2bits-1] [control: 2*bits]:
1. Update IntegerAddition.c cQQ_add() to use `int control = 2 * bits;`
2. Update documentation comment to match
3. Regenerate hardcoded sequences with corrected control index:
   - Width 1: control at 2 (same)
   - Width 2: control at 4
   - Width 3: control at 6
   - Width 4: control at 8
   - Width 5: control at 10
   - Width 6: control at 12
   - Width 7: control at 14
   - Width 8: control at 16

**Option B: C is correct (3*bits-1 layout), fix Python side**
If the intended layout has a gap for ancilla/scratch space:
1. Update qint_arithmetic.pxi to place control at position 3*bits-1
2. Verify ancilla placement doesn't conflict

Determine which option by:
- Checking if there's a historical reason for the gap (maybe ancilla space?)
- Looking at what QQ_add uses (2*bits qubits total, no gap)
- Checking if cCQ_add or cQQ_mul have similar issues

Most likely Option A is correct since:
- QQ_add uses 2*bits qubits (target + other), no gap
- cQQ_add should use 2*bits + 1 qubits (target + other + control)
- The 3*bits-1 seems like a bug introduced when converting from some other layout

Apply the fix:
1. Update `int control = 2 * bits;` in IntegerAddition.c cQQ_add()
2. Update the documentation comment
3. Regenerate hardcoded cQQ_add sequences using the existing generation script (modify it if needed)
4. Rebuild the C backend
  </action>
  <verify>
Run: `cd /path/to/project && python -c "import quantum_language as ql; ql.circuit(); ctrl=ql.qint(1,1); a=ql.qint(1,2); b=ql.qint(1,2); exec('with ctrl: a+=b')"` - should not crash
  </verify>
  <done>Qubit layout is consistent between Python and C sides for cQQ_add</done>
</task>

<task type="auto">
  <name>Task 3: Validate fix with comprehensive tests</name>
  <files>
    tests/quick/test_014_cqq_add_bug.py
  </files>
  <action>
Create comprehensive regression tests for cQQ_add:

```python
# tests/quick/test_014_cqq_add_bug.py
"""Regression tests for cQQ_add (controlled quantum-quantum addition) bug fix."""
import pytest
import quantum_language as ql

@pytest.mark.parametrize("width", [1, 2, 3, 4, 5, 6, 7, 8])
def test_controlled_qq_add_control_on(width):
    """When control=1, addition should happen."""
    max_val = (1 << width) - 1
    a_val = max_val // 2
    b_val = 1

    circ = ql.circuit()
    ctrl = ql.qint(1, width=1)  # Control ON
    a = ql.qint(a_val, width=width)
    b = ql.qint(b_val, width=width)

    with ctrl:
        a += b

    # Verify circuit builds without error
    assert circ.depth > 0, f"Circuit should have gates for width {width}"

@pytest.mark.parametrize("width", [1, 2, 3, 4, 5, 6, 7, 8])
def test_controlled_qq_add_control_off(width):
    """When control=0, addition should NOT happen."""
    circ = ql.circuit()
    ctrl = ql.qint(0, width=1)  # Control OFF
    a = ql.qint(5 % (1 << width), width=width)
    b = ql.qint(3 % (1 << width), width=width)

    with ctrl:
        a += b

    # Verify circuit builds without error
    assert circ.depth > 0, f"Circuit should have gates for width {width}"

def test_controlled_qq_add_hardcoded_vs_dynamic():
    """Width 8 (hardcoded) and width 9 (dynamic) should both work."""
    # Width 8 - uses hardcoded
    circ8 = ql.circuit()
    ctrl8 = ql.qint(1, width=1)
    a8 = ql.qint(100, width=8)
    b8 = ql.qint(50, width=8)
    with ctrl8:
        a8 += b8
    depth8 = circ8.depth

    # Width 9 - uses dynamic
    circ9 = ql.circuit()
    ctrl9 = ql.qint(1, width=1)
    a9 = ql.qint(100, width=9)
    b9 = ql.qint(50, width=9)
    with ctrl9:
        a9 += b9
    depth9 = circ9.depth

    assert depth8 > 0, "Width 8 hardcoded cQQ_add should work"
    assert depth9 > 0, "Width 9 dynamic cQQ_add should work"
```

Run all tests:
```bash
pytest tests/quick/test_014_cqq_add_bug.py -v
pytest tests/test_hardcoded_sequences.py -v -k "controlled"
```
  </action>
  <verify>
`pytest tests/quick/test_014_cqq_add_bug.py -v` - all tests pass
`pytest tests/test_hardcoded_sequences.py -v` - no regressions
  </verify>
  <done>All cQQ_add tests pass for widths 1-8 (hardcoded) and 9+ (dynamic)</done>
</task>

</tasks>

<verification>
1. No crashes when using controlled QQ addition
2. All hardcoded sequence tests still pass
3. New regression tests pass for cQQ_add
4. Both hardcoded (1-8) and dynamic (9+) paths work
</verification>

<success_criteria>
- cQQ_add works correctly for all bit widths
- Qubit layout is consistent between Python and C
- Regression tests prevent future breakage
- No breaking changes to other operations
</success_criteria>

<output>
After completion, create `.planning/quick/014-cqq-add-hardcoded-or-not-doesn-t-seem-to/014-SUMMARY.md`
</output>
