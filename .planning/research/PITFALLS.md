# Domain Pitfalls: Quantum Circuit Generation Framework

**Domain:** Quantum programming framework (C backend with Python bindings)
**Researched:** 2026-01-25
**Confidence:** HIGH for C/Python binding issues, MEDIUM for quantum-specific patterns

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or major architectural issues.

### Pitfall 1: Mixing C and Python Memory Allocators

**What goes wrong:** Memory allocated in C (via malloc) is freed using Python's garbage collector, or vice versa. This creates memory corruption, double-free errors, and segmentation faults.

**Why it happens:** When C backend allocates quantum circuit structures and Python bindings expose them as Python objects, developers forget which side owns the memory. Cython makes it easy to pass pointers between worlds without clear ownership transfer.

**Consequences:**
- Immediate: Segmentation faults when Python GC tries to free C-allocated memory
- Delayed: Memory leaks when C allocates but Python never frees
- Catastrophic: Memory corruption when both sides try to manage the same object

**Prevention:**
1. Establish ownership rules: Document which side allocates and which side frees for each data structure
2. Use Cython's memory management helpers: `PyMem_Malloc` for Python-managed memory, standard malloc for C-only memory
3. Implement capsule destructors: For C structures exposed to Python, use PyCapsule with proper destructor
4. Never use C library functions (malloc, free, realloc) on Python objects
5. Add comments at every allocation: `/* Python-owned */` or `/* C-owned, freed in cleanup() */`

**Detection:**
- Valgrind reports "Invalid free()" or "Source and destination overlap"
- Crashes occur during Python GC cycles (not at operation time)
- Memory usage grows even when circuits are deleted on Python side
- Errors appear non-deterministically (GC timing dependent)

**Phase mapping:** Must be addressed in Phase 1 (Memory Architecture) before any feature work.

**Sources:**
- [Python Memory Management Documentation](https://docs.python.org/3/c-api/memory.html)
- [Real Python: Python Bindings Overview](https://realpython.com/python-bindings-overview/)

---

### Pitfall 2: Incorrect sizeof() Usage with Pointer Types

**What goes wrong:** Using `sizeof(pointer)` instead of `sizeof(*pointer)` or `sizeof(actual_type)` when allocating memory. This allocates wrong-sized memory blocks (typically 8 bytes instead of struct size).

**Why it happens:** C's sizeof() returns pointer size (8 bytes on 64-bit) when given a pointer variable. Developers write `sizeof(integer)` where `integer` is a pointer to `quantum_int_t`, allocating 8 bytes instead of the full struct size.

**Consequences:**
- Memory corruption when accessing fields beyond the 8-byte boundary
- Undefined behavior - may appear to work, then crash randomly
- Heap corruption leading to crashes far from the actual bug
- Nearly impossible to debug without careful code review

**Prevention:**
1. Always use `sizeof(type_name)` not `sizeof(variable_name)` for allocations
2. Pattern: `ptr = malloc(sizeof(*ptr))` ensures correct size even if type changes
3. Static analysis: Enable `-Wsizeof-pointer-memaccess` compiler warning
4. Code review checklist: Flag every `sizeof()` in malloc/calloc calls
5. Consider typedef'ing struct types to avoid pointer confusion

**Detection:**
- Valgrind shows "Invalid write of size N" with N larger than 8
- Fields of allocated structs contain garbage values
- Crashes occur when accessing struct members (especially later fields)
- Memory corruption appears in unrelated parts of the program
- Heisenbug behavior (works in debug, crashes in release)

**Current instances in codebase:**
- `Backend/src/Integer.c` lines 31, 37: Uses `sizeof(integer)` instead of `sizeof(quantum_int_t)`

**Phase mapping:** Phase 1 (C Layer Cleanup) - critical fix before building features.

**Sources:**
- [GeeksforGeeks: sizeof operator in C](https://www.geeksforgeeks.org/c/sizeof-operator-c/)
- [Common Memory Bugs in C](https://www.geeksforgeeks.org/c/common-memory-pointer-related-bug-in-c-programs/)

---

### Pitfall 3: Uninitialized Structure Fields Leading to Segfaults

**What goes wrong:** Allocating a struct but only initializing some fields, leaving pointers and arrays uninitialized. Accessing uninitialized pointers causes immediate segmentation faults.

**Why it happens:** C doesn't zero-initialize allocated memory. Developers allocate `sequence_t` structures and set some fields (like `num_layer`) but forget to initialize pointer fields (`seq`, `gates_per_layer`), which contain garbage addresses.

**Consequences:**
- Immediate segfault when dereferencing uninitialized pointer
- Works sometimes (when garbage happens to be NULL) creating Heisenbugs
- Cannot recover - program terminates
- Appears in production if not caught in testing

**Prevention:**
1. Always use calloc() instead of malloc() for structures (zeroes memory)
2. Create init functions: `init_sequence(sequence_t *s)` that initializes all fields
3. Use designated initializers: `sequence_t s = {.num_layer = 0, .seq = NULL, ...}`
4. Enable compiler warnings: `-Wuninitialized` catches some cases
5. Valgrind/ASan in CI: Catches uninitialized reads before production

**Detection:**
- Immediate segfault at first access to structure field
- Valgrind: "Conditional jump or move depends on uninitialized value"
- ASan: "use-of-uninitialized-value"
- Crash location: Always at pointer dereference, not allocation
- Stack trace shows access to struct field that was never set

**Current instances:**
- `Backend/src/IntegerAddition.c` lines 230-250: sequence_t allocated but seq/gates_per_layer not initialized
- `Backend/src/IntegerComparison.c`: Similar pattern

**Phase mapping:** Phase 1 (C Layer Cleanup) - must fix before these functions are used.

**Sources:**
- [15 Mistakes with Memory Allocation in C](https://aticleworld.com/mistakes-with-memory-allocation/)
- [Cornell CS3410: Memory Allocation](https://www.cs.cornell.edu/courses/cs3410/2025fa/notes/mem.html)

---

### Pitfall 4: Global State in C Library with Multiple Python Contexts

**What goes wrong:** C library uses global variables (like `circuit`, `QPU_state`, `R0-R3` registers) that are shared across all Python threads/processes. Multiple Python users of the library interfere with each other's quantum circuits.

**Why it happens:** C naturally encourages global state for "singleton" resources. When wrapped in Python, users expect isolation (like separate Python objects), but the C backend is shared.

**Consequences:**
- Thread safety: Two threads building circuits corrupt each other's state
- Testability: Tests cannot run in parallel, must serialize
- API confusion: Python users create multiple circuit objects but they all share C global state
- Production bugs: Concurrent requests to web service corrupt circuits

**Prevention:**
1. Context objects: Pass `circuit_t*` context to all functions instead of using global
2. Thread-local storage: Use `__thread` for per-thread state (not per-object)
3. Opaque handles: Python objects hold pointers to unique C structs
4. Document limitations: If globals are necessary, document "single-circuit only" in API
5. Python GIL: For Cython, leverage GIL to prevent concurrent access (temporary solution)

**Detection:**
- Intermittent failures when running tests in parallel (pytest -n)
- Different results when same code runs twice
- State "bleeds" between Python objects that should be independent
- Works in single-threaded mode, fails with multiprocessing
- Race conditions appear under load testing

**Current instances:**
- `Backend/include/QPU.h`: Global `circuit`, `QPU_state`, `Q0-Q3`, `R0-R3`
- `Backend/src/IntegerAddition.c` lines 9-12: Global precompiled sequence cache

**Phase mapping:**
- Phase 2 (Memory Management): Design context object architecture
- Phase 4 (API Stabilization): Migrate globals to context

**Sources:**
- [State Management Anti-Patterns](https://www.sourceallies.com/2020/11/state-management-anti-patterns/)
- [Redux Anti-Patterns: Global State](https://blog.mgechev.com/2017/12/07/redux-anti-patterns-race-conditions-state-management-duplication/)

---

### Pitfall 5: Hardcoded Integer Sizes Breaking Variable-Width Operations

**What goes wrong:** Quantum integer operations assume fixed bit-width (via INTEGERSIZE constant). When extending to variable-width integers, hardcoded array sizes cause buffer overflows or truncated results.

**Why it happens:** Early prototypes use constants for simplicity. As features expand (arbitrary-precision integers, mixed-width arithmetic), constants baked into loops and allocations break.

**Consequences:**
- Buffer overflow: 32-bit result stored in 16-bit buffer
- Silent truncation: High bits dropped, computation produces wrong answer
- Incompatible operations: Cannot add 8-bit and 32-bit quantum integers
- Architecture limit: Entire system locked to fixed width

**Prevention:**
1. Parameterize early: All functions take `width` parameter from day one
2. Dynamic allocation: Size arrays based on runtime width, not compile-time constant
3. Width validation: Check operand widths match before arithmetic operations
4. Use runtime constants: Store INTEGERSIZE in circuit context, not #define
5. Test mixed widths: Include test cases with different bit-widths from start

**Detection:**
- Assertion failures when width exceeds INTEGERSIZE
- Quantum arithmetic produces mathematically wrong results (detected via simulation)
- Crashes when allocating qints wider than hardcoded size
- Compilation errors when changing INTEGERSIZE (shows hardcoded dependencies)

**Current instances:**
- `Backend/include/QPU.h` line 18: `#define INTEGERSIZE 8`
- All integer arithmetic operations assume this width
- `quantum_int_t.q_address[INTEGERSIZE]` is fixed-size array

**Phase mapping:**
- Phase 2 (Variable Integer Support): Core requirement to unlock this feature
- Must refactor before implementing Phase 3 (Extended Arithmetic)

**Sources:**
- [C Data Types: Integer Benefits and Pitfalls](https://www.gnu.org/software/gnuastro/manual/html_node/Integer-benefits-and-pitfalls.html)
- [INT18-C: Evaluate Integer Expressions in Larger Size](https://wiki.sei.cmu.edu/confluence/display/c/INT18-C.+Evaluate+integer+expressions+in+a+larger+size+before+comparing+or+assigning+to+that+size)

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or require refactoring.

### Pitfall 6: Missing Memory Allocation Failure Checks

**What goes wrong:** malloc/calloc/realloc return NULL when memory exhausted, but code doesn't check. Dereferencing NULL pointer causes immediate crash with no error message.

**Why it happens:** malloc failures are rare in development (plenty of RAM), so developers forget to check. In production (large circuits, memory limits), failures happen.

**Consequences:**
- Crash with no helpful error message ("Segmentation fault")
- User loses work (circuit in progress destroyed)
- Cannot diagnose issue without core dump

**Prevention:**
1. Standard pattern: `if ((ptr = malloc(size)) == NULL) { perror("malloc"); exit(1); }`
2. Wrapper functions: `safe_malloc()` that checks and exits with error
3. Static analysis: Clang analyzer detects unchecked returns
4. Consistent policy: Document whether library aborts or returns error codes

**Detection:**
- Crashes only under memory pressure (large circuits, low RAM systems)
- Valgrind: "Invalid write" immediately after allocation
- No line number in crash (NULL dereference location, not allocation failure site)

**Phase mapping:** Phase 1 (C Layer Cleanup) - add checks to all allocations.

**Sources:**
- [5 Deadly Mistakes in C Programming](https://www.techbuddies.io/2024/01/22/5-deadly-mistakes-to-avoid-in-c-programming/)
- [Memory Leak in C: Find and Fix](https://unstop.com/blog/memory-leak-in-c)

---

### Pitfall 7: Memory Leaks in Error Paths

**What goes wrong:** Function allocates memory, then encounters error before reaching cleanup code. Allocated memory is never freed.

**Why it happens:** C requires explicit free() at every exit path. Early returns or error branches bypass cleanup code.

**Consequences:**
- Memory usage grows over time
- Long-running programs eventually run out of memory
- Difficult to trace (leak only occurs on error path)

**Prevention:**
1. RAII pattern via goto: Single cleanup label at end, all exits goto cleanup
2. Early validation: Check error conditions before allocating
3. Defer allocation: Allocate only after validation succeeds
4. Valgrind regularly: Catch leaks in CI/CD pipeline

**Detection:**
- Valgrind: "definitely lost" or "still reachable" blocks
- Memory usage grows when triggering errors repeatedly
- Production monitoring shows increasing RSS

**Current instances:**
- `Backend/src/QPU.c` lines 109-132: colliding_gates() leaks if gates_are_inverse() errors

**Phase mapping:** Phase 1 (C Layer Cleanup) - refactor error handling.

---

### Pitfall 8: Precompiled Cache Invalidation Bugs

**What goes wrong:** System caches precompiled quantum gate sequences globally, assuming operand sizes never change. When sizes do change, cached sequences apply wrong operations.

**Why it happens:** Performance optimization (precompiling common operations) introduces hidden dependencies. Cache doesn't track invalidation conditions.

**Consequences:**
- Wrong quantum computation results (cache applied to wrong-sized operands)
- Difficult to debug (works first time, breaks on second call with different size)
- Non-deterministic (depends on call order)

**Prevention:**
1. Cache key includes all parameters: Hash operand sizes into cache key
2. Explicit invalidation: Provide clear_cache() function or document when to invalidate
3. Assertion checking: Verify cached sequence matches current operand sizes
4. Avoid caching during development: Only enable optimization after API stabilizes

**Detection:**
- Quantum circuit produces mathematically incorrect results
- Same operation works first time, fails on subsequent calls
- Changing operand order changes results
- Assertions fail: "cached sequence width != actual width"

**Current instances:**
- `Backend/src/IntegerAddition.c` lines 36-44, 127-135: Caches depend on R0 register value
- No cache invalidation mechanism exists

**Phase mapping:** Phase 2 (Variable Integer Support) - must fix when adding variable widths.

**Sources:**
- Research finding: common pattern in quantum circuit optimizers

---

### Pitfall 9: Cython Memory View Leaks with Multi-Dimensional Arrays

**What goes wrong:** Using Cython typed memory views (`np.ndarray[type, ndim=2]`) can leak memory when the array is not used in the function or has zero-size dimensions.

**Why it happens:** Cython generates reference counting code for memory views that has bugs in edge cases, especially with dimension >= 2 or unused parameters.

**Consequences:**
- Memory leak grows over time
- Affects long-running programs
- Difficult to trace (Cython-generated C code, not user code)

**Prevention:**
1. Avoid typed memory views where possible: Use Python-level numpy arrays
2. Always use function arguments: Don't pass ndarray just to satisfy signature
3. Test with dimension checks: Ensure second dimension > 0 if using 2D arrays
4. Valgrind testing: Catch Cython-generated leaks in CI
5. Update Cython: Some leaks fixed in newer versions (check release notes)

**Detection:**
- Valgrind shows memoryview objects not freed
- Memory usage grows with repeated calls to Cython functions
- Leak location in generated .c file (not .pyx source)

**Phase mapping:** Phase 4 (Python API Stabilization) - review all Cython bindings.

**Sources:**
- [Cython Issue #1638: Memory Leak with Typed Memory Views](https://github.com/cython/cython/issues/1638)
- [Cython Issue #2828: Memory Leak with ndarray and Memory Views](https://github.com/cython/cython/issues/2828)
- [Cython Issue #3046: Memory Leak with ndarray as Function Arg](https://github.com/cython/cython/issues/3046)

---

### Pitfall 10: Quantum Circuit Depth Explosion from Naive Integer Operations

**What goes wrong:** Implementing quantum integer arithmetic naively (without optimization) produces circuits with depth proportional to O(n²) or worse. Large integers create unusably deep circuits.

**Why it happens:** Classical algorithms don't translate directly to quantum. Ripple-carry adders have sequential dependencies that prevent parallelization.

**Consequences:**
- Circuit depth grows quadratically with integer width
- Quantum decoherence increases with depth, making circuits unusable on real hardware
- Compilation time becomes prohibitive
- Users cannot build practical quantum algorithms

**Prevention:**
1. Use optimal quantum algorithms: Implement carry-lookahead or quantum Fourier addition (O(n log n) or O(n))
2. Benchmark depth metrics: Track circuit depth in tests, set depth budgets
3. Literature review: Survey quantum arithmetic papers before implementing
4. Uncomputation strategies: Apply measurement-based techniques to reduce ancilla overhead
5. Qubit-depth tradeoffs: Document when to use more qubits for shallower circuits

**Detection:**
- Circuit depth grows faster than linearly with integer width
- Benchmark comparisons show dramatically worse depth than Qiskit/Cirq
- Quantum simulator takes exponentially longer for marginally larger integers
- Literature shows better algorithms exist

**Phase mapping:** Phase 3 (Extended Arithmetic) - research optimal algorithms before implementing.

**Sources:**
- [Quantum Circuit Design using Monte Carlo Tree Search](https://advanced.onlinelibrary.wiley.com/doi/10.1002/qute.202500093)
- [Memory Management Strategies for Quantum Simulators](https://www.mdpi.com/2624-960X/7/3/41)

---

## Minor Pitfalls

Mistakes that cause annoyance, code smell, or minor bugs.

### Pitfall 11: Commented-Out Debug Code Cluttering Codebase

**What goes wrong:** Large blocks of commented printf statements and debug logic remain in source files, making code harder to read and maintain.

**Why it happens:** Developers comment out debug code instead of removing it, "just in case." Code review doesn't catch it as a problem.

**Consequences:**
- Reduced readability
- Confusion: Is this code supposed to run?
- Merge conflicts in commented sections
- Makes actual comments harder to find

**Prevention:**
1. Remove, don't comment: Delete debug code when done debugging
2. Proper logging framework: Use debug logging levels instead of commented prints
3. Version control mindset: "I can always get it back from git history"
4. Pre-commit hooks: Flag files with high ratio of commented code

**Detection:**
- Grep for `//.*printf` or `/*.*printf.**/` patterns
- Code review: Commented blocks larger than 3 lines

**Current instances:**
- `Backend/src/QPU.c` lines 145, 151, 162, 164, 178-182
- `Backend/src/gate.c` line 10
- `Backend/src/IntegerAddition.c` lines 68-72, 98-106

**Phase mapping:** Phase 1 (C Layer Cleanup) - remove during code review.

---

### Pitfall 12: Using Variable-Length Arrays (VLA) on Stack

**What goes wrong:** Declaring arrays with runtime-determined size (e.g., `int array[count]`) allocates on stack. Large `count` values exceed stack limits, causing stack overflow.

**Why it happens:** VLAs are convenient and look like normal arrays. Developers forget they consume stack space.

**Consequences:**
- Stack overflow crash for large inputs
- No error message (just segfault)
- Platform-dependent (stack size varies by OS)

**Prevention:**
1. Dynamic allocation: Use malloc for runtime-sized arrays
2. Stack size analysis: Calculate worst-case stack usage
3. Maximum size checks: Assert `count < MAX_SAFE_SIZE` before VLA
4. Compiler warnings: Some compilers warn about VLAs with `-Wvla`

**Detection:**
- Crash on large inputs (stack overflow)
- Valgrind: "Stack overflow in thread"
- Works for small circuits, crashes for large circuits

**Current instances:**
- `Backend/src/gate.c` line 47: `int width[count]` VLA

**Phase mapping:** Phase 1 (C Layer Cleanup) - replace with malloc.

**Sources:**
- [Common Memory Bugs in C](https://www.geeksforgeeks.org/c/common-memory-pointer-related-bug-in-c-programs/)

---

### Pitfall 13: Inefficient Power-of-Two Calculations in Tight Loops

**What goes wrong:** Calling `pow(2, i)` in inner loops performs expensive floating-point operations instead of fast bit shifts.

**Why it happens:** pow() is familiar from mathematics. Developers don't realize it's slow or that bit shifts are equivalent.

**Consequences:**
- 10-100x slower than necessary for power-of-2 calculations
- Accumulates in tight loops (major bottleneck)
- Floating-point rounding errors possible

**Prevention:**
1. Use bit shifts: `1 << i` instead of `pow(2, i)`
2. Precompute table: `int pow2[32] = {1, 2, 4, 8, ...}` for repeated lookups
3. Profile first: Identify hot loops before optimizing
4. Code review: Flag any pow() calls in arithmetic code

**Detection:**
- Profiler shows significant time in pow() or math library
- Performance comparison shows unexpectedly slow arithmetic

**Current instances:**
- `Backend/src/IntegerAddition.c` lines 29, 92, 120, 185, 200, 215
- `Backend/src/IntegerMultiplication.c` line 19

**Phase mapping:** Phase 5 (Performance Optimization) - replace after correctness established.

**Sources:**
- Performance best practice (standard C optimization)

---

### Pitfall 14: Loop That Executes Exactly Once (Dead Code Pattern)

**What goes wrong:** Loop written as `for (int i = 0; i < 1; ++i)` executes exactly once, making the loop construct pointless.

**Why it happens:** Placeholder for future multi-iteration logic that was never completed. Developer meant to check multiple gates but only implemented first.

**Consequences:**
- Misleading code (looks like it loops, doesn't)
- Incomplete feature (only first element processed)
- Future bugs when someone assumes loop iterates

**Prevention:**
1. Code review: Question any loop with constant bound = 1
2. TODO comments: If temporary, mark with TODO explaining intent
3. Remove loop: If only one iteration needed, remove loop syntax
4. Static analysis: Linters can flag constant-bound loops

**Detection:**
- Grep for `for.*< 1` or `for.*<= 0`
- Code review: Loop variable unused beyond first iteration

**Current instances:**
- `Backend/src/QPU.c` lines 143-157: `for (int i = 0; i < 1; ++i)`

**Phase mapping:** Phase 1 (C Layer Cleanup) - clarify intent or complete implementation.

---

### Pitfall 15: No Test Coverage for Core Backend Logic

**What goes wrong:** Critical quantum circuit construction and arithmetic operations have no unit tests. Bugs are only caught during full integration testing or in production.

**Why it happens:** C code is harder to test than Python (no built-in test framework). Developers prioritize features over testing. Assumes integration tests are sufficient.

**Consequences:**
- Regression bugs slip through
- Refactoring is risky (can't verify correctness)
- Mathematical errors go undetected (circuit computes wrong answer)
- Debugging is difficult (no isolated test cases)

**Prevention:**
1. Choose C test framework: Check, Unity, or CMocka
2. TDD for new features: Write test first, then implementation
3. Coverage measurement: Use gcov/lcov to track coverage
4. CI enforcement: Require tests for all new functions
5. Example-based testing: Convert examples to regression tests

**Detection:**
- No test_*.c files in Backend/src
- Code coverage reports show 0% for backend
- Bugs found manually that should have been caught by tests

**Phase mapping:**
- Phase 1 (Testing Infrastructure): Set up framework and basic tests
- Ongoing: Add tests for each feature/fix

**Sources:**
- General software engineering best practice
- [Testing C Code](https://www.geeksforgeeks.org/python/best-python-testing-frameworks/) (principles apply to C)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| C Layer Cleanup (Phase 1) | Breaking API compatibility while fixing bugs | Create comprehensive integration tests BEFORE refactoring; maintain compatibility shim layer |
| Memory Architecture (Phase 2) | Fixing one memory issue creates new leak elsewhere | Use Valgrind systematically; track all allocation/free pairs in documentation |
| Variable Integer Support (Phase 2) | Buffer overflows when switching to dynamic sizing | Fuzz testing with random integer widths; assertions on buffer sizes |
| Extended Arithmetic (Phase 3) | Copy-paste bugs when implementing similar operations | Extract common gate sequence patterns into reusable functions |
| Python API Stabilization (Phase 4) | Breaking changes frustrate early users | Deprecation warnings before removals; semantic versioning |
| Documentation (Phase 5) | Documentation drifts from implementation | Doc tests that execute code examples; CI checks for broken links |
| Open Source Release (Phase 6) | Security issues in example code (e.g., buffer overflows in demos) | Security audit of all public examples; fuzzing harness |

---

## Quantum-Specific Pitfalls

### Pitfall 16: Ancilla Qubit Leakage (Not Uncomputing)

**What goes wrong:** Quantum operations allocate ancilla (temporary) qubits but don't uncompute them, leaving them entangled with result. This "leaks" quantum information and corrupts subsequent operations.

**Why it happens:** Classical thinking - temporary variables can be forgotten. In quantum computing, temporary qubits must be returned to |0⟩ state (uncomputed) or they pollute results.

**Consequences:**
- Wrong quantum computation results (entanglement with garbage)
- Exponentially growing qubit requirements
- Cannot measure final result without measuring ancillas
- Real quantum hardware performance degrades

**Prevention:**
1. Uncomputation pattern: For every allocation, add symmetric uncomputation
2. Assertion checks: Verify ancillas return to |0⟩ in simulation
3. Automatic uncomputation: Build framework support for RAII-style cleanup
4. Code review: Flag any ancilla allocation without matching uncomputation

**Detection:**
- Quantum state purity checks fail
- Circuit simulator shows unexpected entanglement
- Measurement results have wrong probability distribution
- Test file shows increment without decrement (as noted in bugs)

**Current instances:**
- `python-backend/test.py` lines 66-68: Increment instead of decrement in uncompute

**Phase mapping:** Phase 3 (Extended Arithmetic) - implement uncomputation tracking.

**Sources:**
- [Scalable Memory Recycling for Large Quantum Programs](https://arxiv.org/abs/2503.00822)
- [Putting Qubits to Work: Quantum Memory Management](https://www.sigarch.org/putting-qubits-to-work-quantum-memory-management/)

---

### Pitfall 17: Ignoring Quantum Gate Error Rates When Optimizing

**What goes wrong:** Circuit optimization focuses on gate count or depth but ignores error rates of different gates. Replacing expensive gates with cheaper gates that have higher error rates makes circuit worse for real hardware.

**Why it happens:** Focus on theoretical metrics (gate count, depth) without considering physical implementation. Different quantum gates have very different error rates.

**Consequences:**
- "Optimized" circuit performs worse on real quantum hardware
- Cannot run circuits on current quantum computers
- Users get incorrect results due to accumulated errors

**Prevention:**
1. Error-aware metrics: Track expected error rate, not just gate count
2. Hardware-specific optimization: Let users specify target hardware error model
3. Configurable priorities: Allow choosing depth vs error-rate tradeoffs
4. Benchmark on simulators with noise: Test with realistic error models

**Detection:**
- Circuit works in ideal simulator but fails on real hardware
- Optimization improves depth but decreases fidelity
- Literature shows better error-aware circuits exist

**Phase mapping:** Phase 5 (Performance Optimization) - consider during optimization work.

**Sources:**
- [Quantum Error Correction: 2025 Trends](https://www.riverlane.com/blog/quantum-error-correction-our-2025-trends-and-2026-predictions)
- [IBM: Fault-Tolerant Quantum Computing](https://www.ibm.com/quantum/blog/large-scale-ftqc)

---

## Restructuring-Specific Pitfalls

### Pitfall 18: Big Bang Refactoring Instead of Incremental

**What goes wrong:** Attempting to fix all memory bugs, remove all globals, and add all features simultaneously in one massive refactoring. Changes become unmergeable, unstable, and impossible to debug.

**Why it happens:** Seeing all the problems creates urge to "fix everything at once." Underestimating the combinatorial complexity of interacting changes.

**Consequences:**
- Multi-month branches that never merge
- Regression bugs impossible to isolate
- Team paralyzed (can't work on unstable branch)
- May need to abandon work and start over

**Prevention:**
1. Strangler pattern: Build new alongside old, migrate incrementally
2. Feature flags: Make changes toggleable for gradual rollout
3. Test-first: Ensure tests pass after each small change
4. Time-box refactorings: If change takes >1 week, break it smaller
5. Frequent integration: Merge to main at least weekly

**Detection:**
- Branch diverges >100 commits from main
- Cannot explain what single change broke tests
- Pull request has >2000 lines changed
- Reviewer says "I don't know where to start"

**Phase mapping:** ALL PHASES - enforce incremental approach throughout.

**Sources:**
- [7 Techniques to Regain Control of Legacy Codebase](https://understandlegacycode.com/blog/7-techniques-to-regain-control-of-legacy/)
- [Legacy Code Refactoring: Best Practices](https://modlogix.com/blog/legacy-code-refactoring-tips-steps-and-best-practices/)

---

### Pitfall 19: Refactoring Without Characterization Tests

**What goes wrong:** Changing legacy code without first writing tests that document current behavior. Changes break functionality but there's no way to detect it.

**Why it happens:** "The code is clearly wrong, we need to fix it" mindset. Skipping tests to move faster. Assuming code is well-understood.

**Consequences:**
- Silent regressions (working features break)
- Cannot verify refactoring correctness
- Users encounter bugs that "worked before"
- Lose trust in releases

**Prevention:**
1. Characterization tests first: Write tests that capture current behavior, bugs and all
2. Approval testing: Record outputs, then detect any change
3. Golden master testing: Save "known good" circuit outputs
4. Test the bug: If fixing bug, write test that reproduces it first
5. No refactor without green tests: Policy enforcement

**Detection:**
- Refactoring PR has no new tests
- Bugs reported that "worked in previous version"
- Cannot answer "does this behavior match original?"

**Phase mapping:**
- Phase 1 (Testing Infrastructure): Create characterization test suite FIRST
- Then proceed to refactoring phases

**Sources:**
- [Legacy Code Refactoring: Before, During, and After](https://swimm.io/learn/legacy-code/legacy-code-refactoring-before-during-and-after-refactoring)
- [Understand Legacy Code](https://understandlegacycode.com/)

---

### Pitfall 20: Prematurely Removing "Dead" Code That's Actually Used

**What goes wrong:** Removing code that appears unused (no visible calls) but is actually called via function pointers, macros, or external bindings. Library breaks for users.

**Why it happens:** Static analysis only finds direct calls, misses indirect calls. Assumption that "I don't see it used" means "nobody uses it."

**Consequences:**
- API breakage for users
- Mysterious crashes (calling removed function)
- Cannot rollback (users depend on new version)

**Prevention:**
1. Deprecation period: Mark as deprecated, warn for one release, then remove
2. Search broadly: Grep for function name as string (catches dynamic calls)
3. Symbol visibility: Check if function is exported (public API)
4. Ask maintainers: Consult original authors before removing
5. Feature flag removal: Make it optional first, observe usage

**Detection:**
- User bug reports: "Function X is missing"
- Linking errors in downstream projects
- CI breaks in projects that depend on library

**Phase mapping:** Phase 1 (C Layer Cleanup) - be conservative about removals.

**Sources:**
- [From Legacy to Legendary: Modernize Without Breaking](https://ait.inc/tech-stuffs/from-legacy-to-legendary-how-to-modernize-old-code-without-breaking-everything/)

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|-----------|--------|
| C/Python Memory Issues | HIGH | Official Python docs, established patterns, codebase audit |
| C Memory Bugs | HIGH | Industry-standard patterns, verified by static analysis tools |
| Quantum Circuit Pitfalls | MEDIUM | Recent research papers (2025), but less standardized |
| Refactoring Pitfalls | HIGH | Software engineering best practices, legacy code literature |
| Cython-Specific Issues | HIGH | GitHub issue tracker shows reported bugs, community knowledge |

---

## Sources

### C/Python Bindings
- [Python Memory Management Documentation](https://docs.python.org/3/c-api/memory.html) - HIGH confidence
- [Real Python: Python Bindings Overview](https://realpython.com/python-bindings-overview/) - HIGH confidence
- [Cython Memory Allocation Docs](https://cython.readthedocs.io/en/latest/src/tutorial/memory_allocation.html) - HIGH confidence

### Cython Memory Leaks
- [Cython Issue #6850: Objects Leak Memory](https://github.com/cython/cython/issues/6850) - HIGH confidence
- [Cython Issue #1638: Memory Leak with Typed Memory Views](https://github.com/cython/cython/issues/1638) - HIGH confidence
- [Cython Issue #3046: Memory Leak with ndarray as Function Arg](https://github.com/cython/cython/issues/3046) - HIGH confidence

### C Memory Bugs
- [GeeksforGeeks: Common Memory/Pointer Bugs in C](https://www.geeksforgeeks.org/c/common-memory-pointer-related-bug-in-c-programs/) - MEDIUM confidence
- [15 Mistakes with Memory Allocation in C](https://aticleworld.com/mistakes-with-memory-allocation/) - MEDIUM confidence
- [5 Deadly Mistakes in C Programming](https://www.techbuddies.io/2024/01/22/5-deadly-mistakes-to-avoid-in-c-programming/) - MEDIUM confidence
- [Cornell CS3410: Memory Management](https://www.cs.cornell.edu/courses/cs3410/2025fa/notes/mem.html) - HIGH confidence

### Quantum Circuit Management
- [Memory Management Strategies for Quantum Simulators](https://www.mdpi.com/2624-960X/7/3/41) - HIGH confidence
- [Scalable Memory Recycling for Large Quantum Programs](https://arxiv.org/abs/2503.00822) - HIGH confidence
- [Putting Qubits to Work: Quantum Memory Management](https://www.sigarch.org/putting-qubits-to-work-quantum-memory-management/) - HIGH confidence
- [Quantum Error Correction: 2025 Trends](https://www.riverlane.com/blog/quantum-error-correction-our-2025-trends-and-2026-predictions) - MEDIUM confidence

### Legacy Code Refactoring
- [7 Techniques to Regain Control of Legacy Codebase](https://understandlegacycode.com/blog/7-techniques-to-regain-control-of-legacy/) - HIGH confidence
- [Legacy Code Refactoring: Tips and Best Practices](https://modlogix.com/blog/legacy-code-refactoring-tips-steps-and-best-practices/) - MEDIUM confidence
- [Legacy Code Refactoring: Before, During, After](https://swimm.io/learn/legacy-code/legacy-code-refactoring-before-during-and-after-refactoring) - MEDIUM confidence

---

*Pitfalls research completed: 2026-01-25*
*This document should be consulted during each phase to avoid known mistakes.*
