---
phase: quick-013
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - c_backend/include/circuit.h
  - c_backend/src/optimizer.c
  - c_backend/src/circuit.c
  - src/quantum_language/_core.pxd
  - src/quantum_language/qint_comparison.pxi
  - src/quantum_language/qint_bitwise.pxi
  - src/quantum_language/qint_arithmetic.pxi
  - src/quantum_language/qint_division.pxi
  - tests/bugfix/test_bug_uncomp_optimizer_layer.py
autonomous: true

must_haves:
  truths:
    - "Uncomputation reverses ALL gates placed by an operation, including those placed in earlier layers by the optimizer"
    - "Comparison operations (==, <, >, etc.) with classical ints correctly uncompute X gates even when optimizer places them before start_layer"
    - "Bitwise and arithmetic operations also correctly track actual minimum layer"
  artifacts:
    - path: "c_backend/include/circuit.h"
      provides: "min_layer_used tracking field in circuit_t"
      contains: "min_layer_used"
    - path: "c_backend/src/optimizer.c"
      provides: "Updates min_layer_used in add_gate"
      contains: "min_layer_used"
    - path: "tests/bugfix/test_bug_uncomp_optimizer_layer.py"
      provides: "Regression test for the bug"
  key_links:
    - from: "c_backend/src/optimizer.c"
      to: "circuit_t.min_layer_used"
      via: "add_gate updates tracking field"
      pattern: "circ->min_layer_used"
    - from: "src/quantum_language/qint_comparison.pxi"
      to: "circuit_s.min_layer_used"
      via: "Python reads min_layer_used after run_instruction to set _start_layer"
      pattern: "min_layer_used"
---

<objective>
Fix uncomputation bug where gates placed in earlier layers by the circuit optimizer are missed during reverse_circuit_range.

Purpose: When the optimizer places gates (e.g., X gates from CQ_equal_width) in layers before `start_layer` (because target qubits have no prior gates), those gates are never reversed during uncomputation. This causes incorrect quantum state after with-block exits.

Output: A `min_layer_used` tracking field in `circuit_t` that `add_gate` updates, allowing Python-side code to capture the actual minimum layer used by an operation rather than relying on `used_layer` (which only grows monotonically).
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@c_backend/include/circuit.h
@c_backend/src/optimizer.c
@c_backend/src/execution.c
@src/quantum_language/_core.pxd
@src/quantum_language/qint_comparison.pxi
@src/quantum_language/qint.pyx (lines 242-266, 359-417)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add min_layer_used tracking to C backend</name>
  <files>
    c_backend/include/circuit.h
    c_backend/src/optimizer.c
    c_backend/src/circuit.c
  </files>
  <action>
    1. In `circuit.h`, add a new field to `circuit_t` struct:
       ```c
       num_t min_layer_used;  // Tracks lowest layer touched by add_gate (reset before run_instruction)
       ```
       Place it after the `used` field (around line 70).

    2. In `circuit.c` (or wherever `init_circuit` is defined), initialize `min_layer_used` to `UINT32_MAX` (or the max value of `num_t`) in the circuit initialization function.

    3. In `optimizer.c`, in `add_gate()` function, after the call to `append_gate(circ, g, min_possible_layer)` (line 218), add:
       ```c
       if (min_possible_layer < circ->min_layer_used) {
           circ->min_layer_used = min_possible_layer;
       }
       ```
       This tracks the earliest layer any gate was placed into during a sequence of add_gate calls.

    4. Also handle the merge_gates early-return path in add_gate (line 202-204): when gates cancel via merge, the layer that was modified could also be relevant, so update min_layer_used there too:
       ```c
       if (min_possible_layer - 1 < circ->min_layer_used) {
           circ->min_layer_used = min_possible_layer - 1;
       }
       ```
       Actually, on reflection: if gates are merged (cancelled), the operation is removing a gate, not adding one. The merge case means the new gate cancelled an existing inverse gate. This does NOT need min_layer_used tracking because those cancelled gates should not be uncomputed either. So skip the merge path -- only track in the append path.
  </action>
  <verify>
    Build the C backend: `cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly && make` (or the project's build command). Verify no compilation errors.
  </verify>
  <done>
    `circuit_t` has `min_layer_used` field, initialized to max value, updated by `add_gate` on the append path.
  </done>
</task>

<task type="auto">
  <name>Task 2: Expose min_layer_used to Python and fix all start_layer captures</name>
  <files>
    src/quantum_language/_core.pxd
    src/quantum_language/qint_comparison.pxi
    src/quantum_language/qint_bitwise.pxi
    src/quantum_language/qint_arithmetic.pxi
    src/quantum_language/qint_division.pxi
  </files>
  <action>
    1. In `_core.pxd`, find the `circuit_s` forward declaration (around line 101-103) which currently only exposes `used_layer` and `used_qubits`. Add `min_layer_used`:
       ```
       cdef struct circuit_s:
           unsigned int used_layer
           unsigned int used_qubits
           unsigned int min_layer_used
       ```

    2. In ALL operation files, change the pattern for setting `_start_layer`. The current pattern everywhere is:
       ```python
       # Before run_instruction:
       start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       # ... run_instruction ...
       # After:
       result._start_layer = start_layer
       result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       ```

       Change to: BEFORE calling `run_instruction`, reset `min_layer_used` to a sentinel (e.g., `(<circuit_s*>_circuit).used_layer`). AFTER calling `run_instruction`, use `min(start_layer, (<circuit_s*>_circuit).min_layer_used)` for `_start_layer`.

       Actually, simpler approach: just reset `min_layer_used` to UINT32_MAX before `run_instruction`, then after, set `_start_layer = min(start_layer, (<circuit_s*>_circuit).min_layer_used)`. But we need to be careful -- `min_layer_used` is a layer INDEX (0-based), and `used_layer` is a count. The `_start_layer` and `_end_layer` are both used in `reverse_circuit_range(circuit, start_layer, end_layer)` where they represent layer indices as counts (0-based index range).

       Looking at `reverse_circuit_range`: it iterates `layer_index = end_layer - 1` down to `start_layer`. So `_start_layer` is inclusive start index and `_end_layer` is exclusive end (same as `used_layer` count). The `min_possible_layer` in `add_gate`/`append_gate` is a 0-based layer index. So `min_layer_used` is already in the right coordinate system.

       The fix pattern for EVERY occurrence:

       BEFORE `run_instruction` call, add:
       ```python
       if _circuit_initialized:
           (<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF  # Reset sentinel
       ```

       AFTER `run_instruction` call, when setting `_start_layer`:
       ```python
       if _circuit_initialized:
           actual_min = (<circuit_s*>_circuit).min_layer_used
           if actual_min != 0xFFFFFFFF and actual_min < start_layer:
               result._start_layer = actual_min
           else:
               result._start_layer = start_layer
       ```

       Apply this pattern to ALL files that have `start_layer = (<circuit_s*>...).used_layer`:
       - qint_comparison.pxi: lines ~51, 77, 133, 206, 257, 313, 359
       - qint_bitwise.pxi: lines ~43, 113, 188, 257, 332, 392, 551, 566
       - qint_arithmetic.pxi: lines ~95, 107, 141, 153, 212, 224, 274, 279, 309, 318, 357, 364, 410, 417, 534, 551, 585, 598
       - qint_division.pxi: lines ~45, 75-76, 86-87, 155, 174-175, 184-185, 242, 264-265, 268-269, 279-280, 284-285

       IMPORTANT: For operations that call `run_instruction` multiple times (like `qint == qint` which does subtraction, comparison, then addition), each sub-operation may have its own start/end tracking. The reset should happen before the FIRST `run_instruction` of the operation, and the min_layer_used should be read AFTER the LAST `run_instruction`.

       IMPORTANT: For the `qint == qint` case (line 54-80 of qint_comparison.pxi), it calls `self -= other`, `self == 0` (recursive), then `self += other`. The start_layer is captured before ALL of these. The recursive `self == 0` will reset min_layer_used internally. So for compound operations, we need to:
       - Reset min_layer_used before the first sub-operation
       - NOT reset it again in sub-operations (but we can't easily prevent the recursive call from resetting it)

       Actually, a cleaner approach: Just reset min_layer_used right before EVERY run_instruction call, and track the running minimum in a local Python variable. Change the pattern to:

       ```python
       # Before operation block:
       start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       actual_start = start_layer  # Will track actual minimum

       # Before each run_instruction:
       if _circuit_initialized:
           (<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF
       run_instruction(...)
       if _circuit_initialized:
           ml = (<circuit_s*>_circuit).min_layer_used
           if ml != 0xFFFFFFFF and ml < actual_start:
               actual_start = ml

       # At the end:
       result._start_layer = actual_start
       ```

       For simple operations (single run_instruction), the pattern simplifies to:
       ```python
       start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       if _circuit_initialized:
           (<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF
       run_instruction(...)
       if _circuit_initialized:
           ml = (<circuit_s*>_circuit).min_layer_used
           if ml != 0xFFFFFFFF and ml < start_layer:
               start_layer = ml
       result._start_layer = start_layer
       ```

       For the `qint == qint` path in qint_comparison.pxi (lines 54-80): This delegates to `self -= other`, `self == 0`, `self += other`. These are Python-level operator calls that internally do their own layer tracking. The overall start_layer for the compound result should be the minimum of all sub-operations. Since `self -= other` and `self += other` are in-place (no result tracking needed for those), and `self == 0` returns a result with its own _start_layer, the compound operation should just use `start_layer` captured before the first call, and min_layer_used after the last. But since sub-operations reset min_layer_used, we need to handle this differently.

       SIMPLEST CORRECT APPROACH: For compound operations (qint == qint, qint < qint, etc.), the start_layer captured BEFORE the operation block is already correct as a ceiling. The sub-operations will each set their own _start_layer correctly (if we fix them). The compound result just needs `result._start_layer = start_layer` (the one captured before everything). This is because `reverse_circuit_range(start_layer, end_layer)` will reverse ALL layers in that range, which covers all sub-operations. The bug only occurs when a SINGLE run_instruction places gates before start_layer. So fixing the simple (single run_instruction) paths fixes the compound paths too, since compound paths capture start_layer before any sub-operation runs.

       WAIT - re-reading the compound path more carefully: For `qint == qint`, `start_layer` is captured at line 51 before `self -= other` (line 61). The `-=` operation does NOT create a result with _start_layer tracking (it's in-place). The recursive `self == 0` at line 64 WILL capture its own start_layer and return a result. Then `self += other` at line 67 is also in-place. At lines 77-78, the compound result uses the original start_layer and current used_layer. This is actually fine IF the in-place operations (-= and +=) don't have the optimizer-layer bug. But they could! If `-=` calls run_instruction and gates get placed before start_layer...

       OK, let me look at what -= does. It would call __isub__ which calls run_instruction. If those gates get placed early, the compound start_layer (captured before -=) is STILL correct because it was captured BEFORE everything. The compound result's _start_layer = start_layer (line 77) would be the used_layer before any sub-operation, so reverse_circuit_range would cover everything. The compound case is actually safe because start_layer is the used_layer BEFORE anything runs -- gates can't be placed before the pre-existing used_layer boundary.

       WAIT -- they CAN be placed before! That's the whole bug! If qubits used by the comparison have no prior gates, add_gate will place them at layer 0, even if used_layer was 5 at the time.

       So the fix IS needed for compound operations too. For compound operations: capture start_layer before, reset min_layer_used before FIRST run_instruction, and after ALL sub-operations complete, use min(start_layer, min_layer_used) as _start_layer. But sub-operations reset min_layer_used...

       Actually, sub-operations like `-=` and `+=` are Python operator calls that go through __isub__ and __iadd__. These in-place operations set `self._start_layer` and `self._end_layer` on the SAME object (self). Then the compound operation overwrites result._start_layer at line 77. So the sub-operation layer tracking is independent.

       The issue is that `min_layer_used` on the circuit struct gets overwritten by each sub-operation. So for compound ops, we can't rely on min_layer_used after all sub-ops -- it only reflects the LAST sub-op.

       CORRECT FIX FOR COMPOUND OPERATIONS: Track a local `actual_start` that takes the minimum across all sub-operations:

       ```python
       start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       actual_start = start_layer

       # Before -= :
       if _circuit_initialized:
           (<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF
       self -= other
       if _circuit_initialized:
           ml = (<circuit_s*>_circuit).min_layer_used
           if ml != 0xFFFFFFFF and ml < actual_start:
               actual_start = ml

       # self == 0 recursive call will handle its own tracking
       result = self == 0

       # Before += :
       if _circuit_initialized:
           (<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF
       self += other
       if _circuit_initialized:
           ml = (<circuit_s*>_circuit).min_layer_used
           if ml != 0xFFFFFFFF and ml < actual_start:
               actual_start = ml

       result._start_layer = actual_start
       ```

       Hmm, but `self -= other` is a Python-level call. It will ITSELF reset and use min_layer_used if we patch __isub__. So after `self -= other` returns, min_layer_used reflects only the += restoration inside __isub__. We'd need to read min_layer_used INSIDE the -= call.

       ACTUALLY: The -= operator (__isub__) does NOT track _start_layer for uncomputation purposes in the compound case. The in-place operations modify self's _start_layer and _end_layer, but the compound operation then OVERWRITES the result's start/end. So the key is: the compound operation needs to know the ACTUAL first layer touched by ANY of its sub-operations.

       SIMPLER APPROACH: Instead of resetting min_layer_used to MAX before each operation, make min_layer_used accumulate (never reset by Python, only grows smaller). Then at the compound level:
       1. Save current min_layer_used
       2. Reset to MAX
       3. Run all sub-operations (each might reset and update min_layer_used, but the last one's value would be lost for earlier ones)

       This doesn't work either because sub-operations reset it.

       CLEANEST APPROACH: Don't reset min_layer_used in the Python layer at all. Instead, add a C function `circuit_reset_min_layer(circuit_t *circ)` that resets it. Then the Python code does:

       For SIMPLE operations (single run_instruction):
       ```python
       start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       (<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF  # reset
       run_instruction(...)
       # Use min of start_layer and min_layer_used
       ml = (<circuit_s*>_circuit).min_layer_used
       actual_start = ml if (ml != 0xFFFFFFFF and ml < start_layer) else start_layer
       result._start_layer = actual_start
       ```

       For COMPOUND operations (like qint == qint):
       No change needed! Here's why: The compound operation captures `start_layer = used_layer` BEFORE any sub-operation. Sub-operations like `-=` call run_instruction which may place gates at layers < start_layer. But the COMPOUND's start_layer was captured before -= ran, and those early-placed gates are at layers >= 0. The compound's `result._start_layer = start_layer` (original, before any sub-op) would be correct IF no gates from sub-ops landed before it. But they can!

       Wait, actually think about this more carefully:
       - Before compound op: used_layer = 5, so start_layer = 5
       - -= calls run_instruction. Optimizer places X gate at layer 0 (empty qubit). After -=, used_layer might still be 5 (or higher).
       - == 0 recursive call: captures start_layer = current used_layer (say 5 or more). Places more gates. After ==0, used_layer = say 10.
       - += calls run_instruction, more gates.
       - Compound result: _start_layer = 5, _end_layer = used_layer (say 15)
       - Uncomputation: reverse_circuit_range(5, 15) -- misses the X gate at layer 0!

       So compound operations DO have the bug. And the -= sub-operation's own _start_layer tracking (if fixed) would catch layer 0 for self, but the compound result OVERWRITES that.

       THE FIX FOR COMPOUND: After all sub-operations, also check the sub-results' _start_layer values. But -= is in-place and modifies self...

       OK ACTUALLY THE REAL SIMPLEST FIX: Don't reset min_layer_used per-operation. Instead, only reset it once at the top level of each Python operation that tracks layers. Then all nested run_instruction calls accumulate into the same min_layer_used. Since compound operations don't themselves call run_instruction directly (they call other Python operators), and those inner operators will each reset min_layer_used...

       I think the cleanest fix is actually: ONLY reset min_layer_used at the point where start_layer is captured, and ONLY read it at the point where _start_layer is assigned. For compound operations that delegate to other Python operators:

       For `qint == qint`:
       ```python
       start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       (<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF  # reset once

       self -= other  # May internally reset min_layer_used, but that's fine
       # After -=, self._start_layer is set (with fix). Save it.
       sub_start = self._start_layer if _circuit_initialized else start_layer

       result = self == 0  # Recursive, will set result._start_layer correctly

       self += other  # In-place, sets self._start_layer

       # Compound result: use minimum of all sub-operation starts
       result._start_layer = min(start_layer, sub_start, result._start_layer, self._start_layer)
       result._end_layer = ...
       ```

       Actually this is getting complicated. Let me think about what ACTUALLY matters:

       The compound `qint == qint` does: subtract, compare-to-zero, add-back. ALL of these gates need to be reversed. The start_layer should be the minimum layer touched by ANY of these. The end_layer should be the maximum (= current used_layer after all).

       Since the inner operations (after our fix) will each correctly track their own _start_layer using min_layer_used, we can just take the min of all sub-results:

       ```python
       start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

       self -= other
       sub1_start = self._start_layer

       result = self == 0
       sub2_start = result._start_layer

       self += other
       sub3_start = self._start_layer

       result._start_layer = min(start_layer, sub1_start, sub2_start, sub3_start)
       result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
       ```

       This is clean, correct, and doesn't rely on min_layer_used surviving across sub-operations.

       Apply this approach to ALL compound operations in the comparison/arithmetic/bitwise/division files. For simple operations (single run_instruction), use the reset-and-read pattern.

       SUMMARY OF CHANGES per file:

       For each SIMPLE operation (single run_instruction call, e.g., qint == int):
       - Before run_instruction: `(<circuit_s*>_circuit).min_layer_used = 0xFFFFFFFF`
       - After run_instruction, when setting _start_layer:
         ```python
         ml = (<circuit_s*>_circuit).min_layer_used
         result._start_layer = ml if (_circuit_initialized and ml != 0xFFFFFFFF and ml < start_layer) else start_layer
         ```

       For each COMPOUND operation (delegates to other Python operators, e.g., qint == qint):
       - After each sub-operation, capture the sub-result's `_start_layer`
       - Set `result._start_layer = min(start_layer, sub1_start, sub2_start, ...)`
       - Keep `result._end_layer` as current `used_layer` (unchanged)
  </action>
  <verify>
    Build the full project (Cython + C): Run the project's build command. Verify no compilation errors. Run existing test suite: `cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly && python -m pytest tests/ -x -q`
  </verify>
  <done>
    All operation files correctly track actual minimum layer used by the optimizer, rather than relying on monotonically-increasing used_layer.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add regression test for the uncomputation bug</name>
  <files>
    tests/bugfix/test_bug_uncomp_optimizer_layer.py
  </files>
  <action>
    Create a regression test that reproduces the exact scenario from the bug report:

    1. Initialize a qint with a non-zero value (to occupy layer 0 on some qubits)
    2. Create a comparison (e.g., `cr == 1`) where the comparison's X gates target qubits with NO prior gates
    3. Use the comparison result in a `with` block
    4. After the with block exits (uncomputation), verify that ALL gates from the comparison are reversed

    The test should:
    - Create a circuit
    - Initialize `cr = qint(1, 3)` (3-bit, value 1 -- uses layer 0 for qubit with bit 0)
    - Create `board = qint(0, 9)` or similar to occupy layer 0 on other qubits
    - Do `result = (cr == 1)` which calls CQ_equal_width(3, 1)
    - Check that `result._start_layer` is 0 (or whatever the actual minimum layer is), NOT 1
    - Verify that after `result._do_uncompute()`, the X gates placed at layer 0 are properly reversed

    Alternative simpler test: Check gate count before and after uncomputation to verify all gates are reversed.

    ```python
    import pytest
    from quantum_language import qint, qbool, circuit

    def test_comparison_uncompute_with_early_layer_gates():
        """Regression test: optimizer places comparison X gates in layers before start_layer."""
        c = circuit()

        # Initialize values to occupy layer 0 on some qubits
        board = qint(5, 4)  # 4-bit value, occupies layer 0 on some qubits

        # This comparison generates X gates on fresh qubits.
        # Optimizer places them at layer 0 (earliest available).
        # Bug: start_layer was captured as used_layer (>= 1), missing layer 0 gates.
        result = (board == 5)

        # After fix: _start_layer should account for optimizer placement
        # The key assertion: start_layer must be <= the layer where X gates landed
        start = result._start_layer
        end = result._end_layer

        # Uncompute should reverse ALL gates in [start, end)
        result._do_uncompute()

        # Verify: result is marked uncomputed
        assert result._is_uncomputed

        # The real verification: run the circuit and check no residual gates
        # from the comparison remain (board should be unchanged)
    ```

    Also consider a test using `with` blocks if the project supports `with result:` syntax for automatic uncomputation scope.

    Look at existing tests in `tests/test_uncomputation.py` and `tests/bugfix/test_bug02_comparison.py` for test patterns and imports to follow.
  </action>
  <verify>
    `cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly && python -m pytest tests/bugfix/test_bug_uncomp_optimizer_layer.py -v`
  </verify>
  <done>
    Regression test exists and passes, confirming that comparison uncomputation correctly handles optimizer-placed gates in earlier layers.
  </done>
</task>

</tasks>

<verification>
1. C backend compiles without errors
2. Cython extension builds without errors
3. All existing tests pass: `python -m pytest tests/ -x -q`
4. New regression test passes: `python -m pytest tests/bugfix/test_bug_uncomp_optimizer_layer.py -v`
5. Manual verification: Create a small program with comparison in a with block, draw the circuit, confirm X gates are properly reversed
</verification>

<success_criteria>
- `circuit_t.min_layer_used` field exists and is updated by `add_gate`
- All `.pxi` files use `min_layer_used` to correctly set `_start_layer` after `run_instruction`
- Compound operations (qint == qint, etc.) take min of sub-operation start layers
- `reverse_circuit_range` now covers the full range of gates placed by an operation
- Regression test demonstrates the fix works
- All existing tests continue to pass
</success_criteria>

<output>
After completion, create `.planning/quick/013-fix-bool-expr-uncomp-with-block/013-SUMMARY.md`
</output>
