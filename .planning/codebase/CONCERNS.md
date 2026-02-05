# Codebase Concerns

**Analysis Date:** 2026-01-25

## Tech Debt

**Incomplete Memory Cleanup:**
- Issue: Allocated resources not fully freed in main execution path
- Files: `main.c` (line 29, 48), `Backend/src/Integer.c` (lines 7, 18, 31, 37, 43)
- Impact: Memory leaks accumulate as the program executes, potentially causing out-of-memory errors on long-running quantum circuits. The circuit structure allocated at line 35 in `main.c` is never freed.
- Fix approach: Implement complete cleanup in `main.c` - add `free_circuit(circ)` before return, and add corresponding free functions for all malloc'd sequences in `Backend/src/Integer.c`

**Hardcoded Constants in Dynamic Allocation:**
- Issue: Circuit layer and gate allocation uses fixed block sizes (LAYER_BLOCK=128, GATES_PER_LAYER_BLOCK=32) that don't adapt to problem size
- Files: `Backend/include/QPU.h` (lines 11-14), `Backend/src/circuit_allocations.c`
- Impact: Small quantum programs waste memory with oversized allocations; large programs fail when allocation limits are exceeded at MAXQUBITS=8000
- Fix approach: Make block sizes configurable or compute dynamically based on circuit requirements

**Variable Size Array (VLA) Usage:**
- Issue: `int width[count]` at line 47 in `Backend/src/gate.c` uses VLA that fails at runtime if array exceeds stack limits
- Files: `Backend/src/gate.c` (line 47)
- Impact: Large circuits (>300 layers) cause stack overflow when printing sequence
- Fix approach: Replace VLA with dynamically allocated array or pre-allocate fixed maximum

**Incorrect sizeof() Usage:**
- Issue: Lines 31 and 37 in `Backend/src/Integer.c` use `sizeof(integer)` instead of `sizeof(quantum_int_t)`, allocating wrong size
- Files: `Backend/src/Integer.c` (lines 31, 37)
- Impact: Memory corruption and undefined behavior when accessing fields of INT() and BOOL() returns
- Fix approach: Change `sizeof(integer)` to `sizeof(quantum_int_t)` in both functions

**Uninitialized Sequence Structure:**
- Issue: `sequence_t` structure in `IntegerAddition.c` functions (e.g., `cQQ_add()` at line 160) does not initialize all required fields before use
- Files: `Backend/src/IntegerAddition.c` (lines 230-250, 241-250), `Backend/src/IntegerComparison.c`
- Impact: Access to `seq->seq` and `seq->gates_per_layer` without allocation leads to segmentation fault
- Fix approach: Add full initialization of gates_per_layer and seq arrays in all sequence_t allocations, or create init_sequence() helper

## Known Bugs

**Incomplete Inverse Gate Detection:**
- Symptoms: Gate optimization for inverse gates only checks single layer (line 143 in `Backend/src/QPU.c` has loop `for (int i = 0; i < 1; ++i)`)
- Files: `Backend/src/QPU.c` (lines 143, 157)
- Trigger: Add any gate pair that are inverses - they won't be properly eliminated
- Workaround: None - circuit will contain unnecessary inverse pairs
- Impact: Increased circuit depth and gate count

**Logical Error in Uncompute Loop:**
- Symptoms: Test file increments counter during uncompute instead of decrementing
- Files: `python-backend/test.py` (lines 66, 68)
- Trigger: Run the tic-tac-toe example - counters will have wrong values
- Details: Lines 66-68 use `+=` instead of `-=`, leaving registers in incorrect state after uncomputation
- Workaround: Manually decrement in external code

**Missing Freed Array in AllocationFunctions:**
- Symptoms: `allocated_gates_per_layer` in `free_circuit()` may reference already-freed memory
- Files: `Backend/src/circuit_allocations.c` (line 60)
- Trigger: Allocate large circuits with many layers that trigger realloc
- Details: `gate_index_of_layer_and_qubits` is freed before `allocated_occupation_indices_per_qubit` is freed, but realloc operations may interleave pointer management
- Risk: Intermittent double-free or memory corruption

## Memory Management Risks

**Missing Allocation Checks:**
- Issue: No error handling after malloc/calloc operations
- Files: `Backend/src/*.c` throughout (estimated 50+ malloc calls)
- Impact: NULL pointer dereference if memory allocation fails
- Fix approach: Add error checking pattern: `if ((ptr = malloc(...)) == NULL) { handle_error(); }`

**Resource Leak in Error Paths:**
- Issue: `colliding_gates()` in `Backend/src/QPU.c` allocates memory that's freed (lines 170, 176) but cleanup may fail if gates_are_inverse() crashes
- Files: `Backend/src/QPU.c` (lines 109-132)
- Impact: Memory leak if error occurs between allocation and free
- Fix approach: Use goto-based cleanup pattern or wrapper function

**Precompiled Gate Cache Memory:**
- Issue: Global static precompiled sequences never freed (`precompiled_QQ_add`, `precompiled_cQQ_add`, arrays at lines 9-12 in `Backend/src/IntegerAddition.c`)
- Files: `Backend/src/IntegerAddition.c` (lines 9-12)
- Impact: Memory leak - cache persists for entire program lifetime with no cleanup mechanism
- Fix approach: Add cleanup_precompiled() function to be called at program exit

## Performance Bottlenecks

**Linear Search Instead of Binary Search:**
- Issue: `smallest_layer_below_comp()` in `Backend/src/QPU.c` uses linear O(n) search with TODO comment
- Files: `Backend/src/QPU.c` (lines 11-22)
- Current implementation: Simple for loop checking each layer
- Improvement path: Implement binary search (O(log n)) since occupied_layers_of_qubit is ordered

**Repeated Power Calculations:**
- Issue: `pow(2, i + 1)` and similar expressions recalculated in tight loops
- Files: `Backend/src/IntegerAddition.c` (lines 29, 92, 120, 185, 200, 215), `Backend/src/IntegerMultiplication.c` (line 19)
- Impact: Unnecessary floating-point operations (10-100+ times per circuit)
- Fix approach: Pre-compute powers of 2 table or use bit shifts (1 << (i+1))

**Inefficient Memory Reallocation Pattern:**
- Issue: Block-based allocation with memset initialization can be slow for large allocations
- Files: `Backend/src/circuit_allocations.c` (lines 113-132)
- Example: Line 114 initializes new layer entries with memset
- Improvement: Use calloc (which zeroes) instead of malloc + memset for new allocations

**Double Array Access:**
- Issue: `gate_index_of_layer_and_qubits` uses double indirection for every gate lookup (requires two pointer dereferences per lookup in tight loops)
- Files: `Backend/src/QPU.c` (lines 46, 48, 102-103, 115, 123)
- Impact: Cache misses and pointer chasing slow down gate operations
- Fix approach: Consider flattened 1D array with manual indexing

## Fragile Areas

**Circuit Allocation State Machine:**
- Files: `Backend/src/circuit_allocations.c` (full file), `Backend/src/QPU.c` (lines 74-106)
- Why fragile: Complex state tracking across multiple parallel allocation arrays (`occupied_layers_of_qubit`, `used_occupation_indices_per_qubit`, `gate_index_of_layer_and_qubits`). Realloc operations must maintain consistency across all arrays.
- Safe modification: Any change to allocation strategy requires updating all four realloc calls in `allocate_more_qubits()` (lines 83, 89-90, 98-102) and `allocate_more_layer()` (lines 113-129) in lockstep
- Test coverage: No unit tests visible for allocation edge cases
- High risk: Off-by-one errors in any array index calculation propagate to segfaults

**Gate Merging Logic:**
- Files: `Backend/src/QPU.c` (lines 40-76, 109-187)
- Why fragile: `merge_gates()` shuffles gates in layer array and updates multiple tracking arrays simultaneously (lines 46-68). Array index adjustments are interleaved with memory updates.
- Safe modification: Must verify that `gate_index_of_layer_and_qubits` updates match actual gate positions after swap
- Test coverage: No visible tests for merge behavior
- Risk: Incorrect gate ordering leads to wrong quantum computation

**Precompiled Sequence Caching:**
- Files: `Backend/src/IntegerAddition.c` (lines 36-44, 127-135, 161), `Backend/src/IntegerMultiplication.c`
- Why fragile: Cache validity depends on QPU_state register values being static (assumed but not enforced). If R0 changes between calls, cached sequences become invalid.
- Safe modification: Must add comments documenting cache invalidation requirements or refactor to take parameters
- Risk: Using cached sequence with different operand size leads to wrong computation

## Scaling Limits

**Qubit Capacity:**
- Current capacity: MAXQUBITS = 8000 (line 15 in `Backend/include/QPU.h`)
- Limit: Fixed compile-time array allocation for `qubit_indices[MAXQUBITS]` (line 41)
- Scaling path: Dynamically allocate based on circuit requirements, or increase MAXQUBITS and recompile

**Circuit Depth:**
- Current capacity: Layers allocated in blocks of LAYER_BLOCK=128 (grows as needed)
- Limit: `used_occupation_indices_per_qubit` array size allocates QUBIT_INDEX_BLOCK=128 per qubit (line 14). For 64-bit integers, this limits depth to ~8000 layers before reallocation needed for each qubit
- Scaling path: Increase QUBIT_INDEX_BLOCK or implement dynamic sizing

**Gate Count Per Layer:**
- Current capacity: GATES_PER_LAYER_BLOCK = 32 (line 13)
- Limit: Highly parallel quantum gates could exceed 32 gates per layer
- Scaling path: Increase block size or implement adaptive sizing

## Uninitialized Variables and Logic Errors

**Unused Loop Variable:**
- Issue: Line 143-157 in `Backend/src/QPU.c` has loop `for (int i = 0; i < 1; ++i)` - loop executes exactly once, making it effectively dead code
- Files: `Backend/src/QPU.c` (lines 143, 157)
- Impact: Suggests incomplete implementation of multi-gate collision checking
- Risk: Only first colliding gate is checked; subsequent gates ignored

**Commented-Out Debug Code:**
- Issue: Multiple commented print statements and debug logic throughout codebase
- Files: `Backend/src/QPU.c` (lines 145, 151, 162, 164, 178-182), `Backend/src/gate.c` (line 10), `Backend/src/IntegerAddition.c` (lines 68-72, 98-106)
- Impact: Makes code harder to follow; suggests incomplete debugging sessions
- Fix approach: Remove commented code or convert to proper debug logging

## Test Coverage Gaps

**No Unit Tests for Core Backend:**
- What's not tested: QPU circuit construction, gate merging, allocation reallocation triggers
- Files: All `Backend/src/*.c` files - no corresponding `test_*.c` or `*_test.c` found
- Risk: Logic errors in critical functions discovered only at runtime with full circuits
- Priority: High - core functionality is untested

**No Validation Tests for Integer Operations:**
- What's not tested: Correctness of QQ_add, CQ_add, QQ_mul operations
- Files: `Backend/src/IntegerAddition.c`, `Backend/src/IntegerMultiplication.c`
- Risk: Mathematical correctness unknown - circuits may compute wrong results
- Priority: High - semantic correctness is critical

**No Memory Leak Tests:**
- What's not tested: Long-running circuit execution to detect memory leaks
- Files: All allocation code
- Risk: Memory leaks only discovered in production/long runs
- Priority: Medium - valgrind should be automated

**No Test for Python Backend:**
- What's not tested: Python quantum language parsing and compilation
- Files: `python-backend/test.py` appears to be an example, not a test suite
- Risk: Python → C compilation pipeline untested
- Priority: Medium

---

*Concerns audit: 2026-01-25*
