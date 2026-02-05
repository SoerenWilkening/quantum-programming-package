---
type: quick
wave: 1
files_modified:
  - Backend/include/Integer.h
  - Backend/src/IntegerAddition.c
  - Backend/src/IntegerMultiplication.c
  - python-backend/quantum_language.pxd
  - python-backend/quantum_language.pyx
autonomous: true

must_haves:
  truths:
    - "CQ_add, cCQ_add, CQ_mul, cCQ_mul take classical value as int64_t parameter"
    - "Functions no longer read from QPU_state->R0"
    - "Python bindings pass value directly instead of setting QPU_state[0].R0[0]"
    - "All existing tests pass unchanged"
  artifacts:
    - path: "Backend/include/Integer.h"
      provides: "Updated function signatures"
      contains: "int64_t value"
    - path: "Backend/src/IntegerAddition.c"
      provides: "Refactored CQ_add and cCQ_add"
    - path: "Backend/src/IntegerMultiplication.c"
      provides: "Refactored CQ_mul and cCQ_mul"
    - path: "python-backend/quantum_language.pxd"
      provides: "Updated extern declarations"
    - path: "python-backend/quantum_language.pyx"
      provides: "Updated call sites"
  key_links:
    - from: "python-backend/quantum_language.pyx"
      to: "Backend/src/IntegerAddition.c"
      via: "Function call with value parameter"
---

<objective>
Refactor CQ_add, cCQ_add, CQ_mul, cCQ_mul to take classical value as explicit parameter

Purpose: Remove dependency on global QPU_state->R0 for these functions, making them pure functions that are easier to test and reason about.

Output: Four functions with explicit int64_t value parameters, updated Python bindings
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
Current state:
- CQ_add(int bits) reads value from QPU_state->R0
- cCQ_add(int bits) reads value from QPU_state->R0
- CQ_mul() reads value from QPU_state->R0
- cCQ_mul() reads value from QPU_state->R0

Python callers set `QPU_state[0].R0[0] = other` before calling these functions.

Note: CQ_div and cCQ_div do not exist in this codebase.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update C function signatures and implementations</name>
  <files>
    Backend/include/Integer.h
    Backend/src/IntegerAddition.c
    Backend/src/IntegerMultiplication.c
  </files>
  <action>
1. In Backend/include/Integer.h, update function declarations:
   - `sequence_t *CQ_add(int bits);` -> `sequence_t *CQ_add(int bits, int64_t value);`
   - `sequence_t *cCQ_add(int bits);` -> `sequence_t *cCQ_add(int bits, int64_t value);`
   - `sequence_t *CQ_mul();` -> `sequence_t *CQ_mul(int64_t value);`
   - `sequence_t *cCQ_mul();` -> `sequence_t *cCQ_mul(int64_t value);`

2. In Backend/src/IntegerAddition.c:
   - Update CQ_add signature to `sequence_t *CQ_add(int bits, int64_t value)`
   - Replace `*(QPU_state->R0)` with `value` (line 42 and similar)
   - Update ownership comment to remove "READS: QPU_state->R0"
   - Update cCQ_add signature to `sequence_t *cCQ_add(int bits, int64_t value)`
   - Replace `*(QPU_state->R0)` with `value` (line 224 and similar)
   - Update ownership comment to remove "READS: QPU_state->R0"

3. In Backend/src/IntegerMultiplication.c:
   - Update CQ_mul signature to `sequence_t *CQ_mul(int64_t value)`
   - Replace `*(QPU_state->R0)` with `value` (line 73)
   - Update ownership comment to remove "READS: QPU_state->R0"
   - Update cCQ_mul signature to `sequence_t *cCQ_mul(int64_t value)`
   - Replace `*(QPU_state->R0)` with `value` (line 226)
   - Update ownership comment to remove "READS: QPU_state->R0"

Note: QQ_add, cQQ_add, QQ_mul, cQQ_mul do NOT need changes - they operate on quantum values only.
Note: CC_add, CC_mul operate on R0/R1/R2 for classical-classical ops, leave those alone.
  </action>
  <verify>
    cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum\ Programming\ Language/Quantum_Assembly && make clean && make
    Build should succeed with no warnings about implicit declarations.
  </verify>
  <done>
    All four functions take int64_t value as parameter, no longer read from QPU_state->R0.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update Python bindings</name>
  <files>
    python-backend/quantum_language.pxd
    python-backend/quantum_language.pyx
  </files>
  <action>
1. In python-backend/quantum_language.pxd, update extern declarations:
   - `sequence_t *CQ_add(int bits);` -> `sequence_t *CQ_add(int bits, long long value);`
   - `sequence_t *cCQ_add(int bits);` -> `sequence_t *cCQ_add(int bits, long long value);`
   - `sequence_t *CQ_mul();` -> `sequence_t *CQ_mul(long long value);`
   - `sequence_t *cCQ_mul();` -> `sequence_t *cCQ_mul(long long value);`

   Note: Use `long long` for Cython which maps to int64_t in C.

2. In python-backend/quantum_language.pyx, update call sites:

   In addition_inplace (around line 236-246):
   - Remove: `QPU_state[0].R0[0] = other`
   - Change: `seq = cCQ_add(self.bits)` -> `seq = cCQ_add(self.bits, other)`
   - Change: `seq = CQ_add(self.bits)` -> `seq = CQ_add(self.bits, other)`

   In multiplication_inplace (around line 342-352):
   - Remove: `QPU_state[0].R0[0] = other`
   - Change: `seq = cCQ_mul()` -> `seq = cCQ_mul(other)`
   - Change: `seq = CQ_mul()` -> `seq = CQ_mul(other)`
  </action>
  <verify>
    cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum\ Programming\ Language/Quantum_Assembly/python-backend && python setup.py build_ext --inplace
    Cython compilation should succeed.
  </verify>
  <done>
    Python bindings pass value directly to C functions instead of setting global state.
  </done>
</task>

<task type="auto">
  <name>Task 3: Run tests to verify correctness</name>
  <files>tests/python/</files>
  <action>
Run the existing Python test suite to verify that the refactoring doesn't change behavior:
- All arithmetic operations should produce the same results
- Focus on tests involving classical-quantum operations (qint + int, qint * int)
  </action>
  <verify>
    cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum\ Programming\ Language/Quantum_Assembly && python -m pytest tests/python/ -v
  </verify>
  <done>
    All existing tests pass, confirming the refactoring is behavior-preserving.
  </done>
</task>

</tasks>

<verification>
- C build succeeds: `make clean && make` in project root
- Python build succeeds: `python setup.py build_ext --inplace` in python-backend/
- Tests pass: `python -m pytest tests/python/ -v`
- grep confirms no remaining `QPU_state->R0` reads in CQ_add/cCQ_add/CQ_mul/cCQ_mul
</verification>

<success_criteria>
- CQ_add, cCQ_add signatures include `int64_t value` parameter
- CQ_mul, cCQ_mul signatures include `int64_t value` parameter
- No references to `QPU_state->R0` in these four functions
- Python bindings updated to pass value directly
- All existing tests pass
</success_criteria>

<output>
After completion, report:
- Files modified with summary of changes
- Test results
- Any issues encountered
</output>
