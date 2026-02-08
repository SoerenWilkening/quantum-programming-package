---
phase: quick-015
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/quantum_language/qint_arithmetic.pxi
  - c_backend/src/IntegerAddition.c
  - scripts/generate_seq_1_4.py
  - scripts/generate_seq_5_8.py
  - c_backend/src/sequences/add_seq_1_4.c
  - c_backend/src/sequences/add_seq_5_8.c
autonomous: true

must_haves:
  truths:
    - "cQQ_add produces correct arithmetic results for widths 1-8"
    - "Python qubit layout matches C backend qubit layout for cQQ_add"
    - "Block 2 CP gates use b-register qubit (bits+bit) as control, not external control"
    - "Hardcoded sequences match the fixed dynamic algorithm output"
  artifacts:
    - path: "c_backend/src/IntegerAddition.c"
      provides: "Fixed Block 2 CP decomposition"
      contains: "cp(g, target_q, bits + bit, -value)"
    - path: "scripts/generate_seq_1_4.py"
      provides: "Fixed generation for widths 1-4"
      contains: 'Gate("P", target_q, bits + bit, -value)'
    - path: "scripts/generate_seq_5_8.py"
      provides: "Fixed generation for widths 5-8"
      contains: 'Gate("P", target_q, bits + bit, -value)'
    - path: "src/quantum_language/qint_arithmetic.pxi"
      provides: "Fixed Python qubit layout"
      contains: "qubit_array[2 * result_bits] = control_qubits[63]"
    - path: "c_backend/src/sequences/add_seq_1_4.c"
      provides: "Regenerated hardcoded sequences for widths 1-4"
    - path: "c_backend/src/sequences/add_seq_5_8.c"
      provides: "Regenerated hardcoded sequences for widths 5-8"
  key_links:
    - from: "IntegerAddition.c Block 2"
      to: "generate_seq_1_4.py Block 2"
      via: "identical algorithm logic"
      pattern: "bits \\+ bit.*-value"
    - from: "IntegerAddition.c Block 2"
      to: "generate_seq_5_8.py Block 2"
      via: "identical algorithm logic"
      pattern: "bits \\+ bit.*-value"
    - from: "qint_arithmetic.pxi control layout"
      to: "IntegerAddition.c control = 2 * bits"
      via: "qubit position agreement"
      pattern: "2 \\* (result_)?bits"
---

<objective>
Fix two bugs in the cQQ_add (controlled quantum-quantum addition) algorithm, then regenerate all hardcoded sequences.

Purpose: BUG-CQQ-ARITH causes incorrect arithmetic for controlled addition at widths 2+. The Python frontend places the control qubit at the wrong position (3*bits-1 instead of 2*bits), and the CCP decomposition in Block 2 uses the wrong control qubit for negative rotations (external control instead of b-register qubit).

Output: Fixed algorithm in C backend, both generation scripts, and Python frontend. Regenerated hardcoded .c files for widths 1-8.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/quantum_language/qint_arithmetic.pxi (lines 70-84)
@c_backend/src/IntegerAddition.c (lines 410-460)
@scripts/generate_seq_1_4.py (lines 109-160)
@scripts/generate_seq_5_8.py (lines 109-160)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix cQQ_add algorithm bugs in all 4 source files</name>
  <files>
    src/quantum_language/qint_arithmetic.pxi
    c_backend/src/IntegerAddition.c
    scripts/generate_seq_1_4.py
    scripts/generate_seq_5_8.py
  </files>
  <action>
    Apply two fixes across 4 files:

    **Bug 1 - Python qubit layout** (`src/quantum_language/qint_arithmetic.pxi`):
    - Line 72: Change comment from "cQQ_add expects control at position 3*bits-1 (with a gap for algorithm)" to "cQQ_add expects control at position 2*bits (immediately after both operands)"
    - Line 74: Change `qubit_array[3 * result_bits - 1] = control_qubits[63]` to `qubit_array[2 * result_bits] = control_qubits[63]`
    - Line 77: Change `qubit_array[3 * result_bits + i] = ancilla_arr[i]` to `qubit_array[2 * result_bits + 1 + i] = ancilla_arr[i]`

    Rationale: The C code at IntegerAddition.c:412 uses `int control = 2 * bits`, meaning the control qubit sits at index 2*bits (right after the a-register [0..bits-1] and b-register [bits..2*bits-1]). The Python side must place it there too. Ancillas follow immediately after.

    **Bug 2 - Block 2 CP control qubit** (3 files):

    In `c_backend/src/IntegerAddition.c` at line 439:
    - Change `cp(g, target_q, control, -value);` to `cp(g, target_q, bits + bit, -value);`

    In `scripts/generate_seq_1_4.py` at line 138:
    - Change `layers.append([Gate("P", target_q, control, -value)])` to `layers.append([Gate("P", target_q, bits + bit, -value)])`

    In `scripts/generate_seq_5_8.py` at line 138:
    - Change `layers.append([Gate("P", target_q, control, -value)])` to `layers.append([Gate("P", target_q, bits + bit, -value)])`

    Rationale: In the CCP(theta) decomposition `CP(t/2)_{c,t} . CNOT_{c,b} . CP(-t/2)_{b,t} . CNOT_{c,b} . CP(t/2)_{b,t}`, the negative rotation (step 3) must be controlled by the b-register qubit (`bits + bit`) that was just toggled by the preceding CNOT, NOT by the external control qubit. The CNOT at line 433/133 flips `bits + bit` conditioned on `control`, so the b-register qubit is now the active control for the negative half-rotation.
  </action>
  <verify>
    Confirm changes with grep:
    - `grep "2 \* result_bits\]" src/quantum_language/qint_arithmetic.pxi` shows the fixed control position
    - `grep "bits + bit, -value" c_backend/src/IntegerAddition.c` shows the fixed Block 2 control
    - `grep "bits + bit, -value" scripts/generate_seq_1_4.py` shows the fixed generator
    - `grep "bits + bit, -value" scripts/generate_seq_5_8.py` shows the fixed generator
  </verify>
  <done>
    All 4 files updated: Python places control at 2*bits, Block 2 CP uses bits+bit as control in C backend and both generators.
  </done>
</task>

<task type="auto">
  <name>Task 2: Regenerate hardcoded sequences and validate</name>
  <files>
    c_backend/src/sequences/add_seq_1_4.c
    c_backend/src/sequences/add_seq_5_8.c
  </files>
  <action>
    1. Regenerate the hardcoded sequence files using the fixed generation scripts:
       ```
       cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly
       python3 scripts/generate_seq_1_4.py > c_backend/src/sequences/add_seq_1_4.c
       python3 scripts/generate_seq_5_8.py > c_backend/src/sequences/add_seq_5_8.c
       ```

    2. Rebuild the project:
       ```
       pip install -e .
       ```

    3. Run the hardcoded sequence tests to validate correctness:
       ```
       pytest tests/test_hardcoded_sequences.py -v
       ```

    4. Run the full addition test suite to confirm no regressions:
       ```
       pytest tests/python/ -v -k "add"
       ```

    The regenerated sequences will have different gate parameters in Block 2 (the CP gates will reference b-register qubits instead of the external control). Layer counts should remain the same since the fix only changes which qubit controls the rotation, not the structure.
  </action>
  <verify>
    - `pytest tests/test_hardcoded_sequences.py -v` -- all 61 tests pass
    - `pytest tests/python/ -v -k "add"` -- all addition tests pass (888+ tests)
    - Spot-check the regenerated C files: `grep -c "Control = {" c_backend/src/sequences/add_seq_1_4.c` produces same count as before (structure unchanged, only control qubit indices differ in Block 2)
  </verify>
  <done>
    Both hardcoded sequence files regenerated from fixed algorithm. All 61 hardcoded tests and all 888+ addition tests pass. cQQ_add produces correct arithmetic for widths 1-8.
  </done>
</task>

</tasks>

<verification>
1. `pytest tests/test_hardcoded_sequences.py -v` -- all tests pass (confirms hardcoded matches dynamic)
2. `pytest tests/python/ -v -k "add"` -- all addition tests pass (confirms no regressions)
3. Block 2 CP gates in all 3 algorithm files use `bits + bit` as control (not `control`)
4. Python qubit layout uses `2 * result_bits` for control position (not `3 * result_bits - 1`)
</verification>

<success_criteria>
- Bug 1 fixed: Python control qubit at position 2*bits, ancillas at 2*bits+1+i
- Bug 2 fixed: Block 2 negative rotations controlled by b-register qubit in C, gen_1_4, gen_5_8
- Hardcoded sequences regenerated for widths 1-8
- All 61 hardcoded sequence tests pass
- All addition tests pass (no regressions)
</success_criteria>

<output>
After completion, create `.planning/quick/015-fix-cqq-add-algorithm-bugs/015-SUMMARY.md`

Update `.planning/STATE.md`:
- Add quick task 015 to the table
- Update BUG-CQQ-ARITH in Blockers/Concerns to mark as FIXED
- Update last activity date
</output>
