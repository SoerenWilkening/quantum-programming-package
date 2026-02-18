# Phase 65: Infrastructure Prerequisites - Research

**Researched:** 2026-02-14
**Domain:** C backend bug fixes (circuit reversal, qubit allocator, ancilla verification)
**Confidence:** HIGH

## Summary

This phase fixes three infrastructure bugs in the C backend that would silently corrupt Toffoli-based circuits. All three are well-scoped, isolated changes to existing C files with clear before/after semantics. The codebase is mature and well-structured -- the fixes modify `execution.c` (reverse_circuit_range), `qubit_allocator.c` (block allocation/free), and `qubit_allocator.c` + `circuit_allocations.c` (ancilla lifecycle assertion at destroy time).

The primary risk is regression in the QFT arithmetic path. The existing test suite (`pytest tests/python/ -v`, 14 test files) provides strong coverage of QFT operations. The existing C tests (`tests/c/`) demonstrate the test pattern for new C-level tests. The Makefile in `tests/c/` already supports building standalone C test executables with the correct include paths and source dependencies.

**Primary recommendation:** Fix the three bugs in order of dependency -- (1) reverse_circuit_range first (no dependencies), (2) allocator block reuse (independent), (3) ancilla lifecycle assertion (depends on allocator tracking) -- then run full regression suite.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Whitelist self-inverse gates explicitly: X, Y, Z, H, M
- Inline check (switch/case) directly in `reverse_circuit_range()` -- no helper function
- For self-inverse gates, skip negation entirely (leave GateValue unchanged)
- All other gate types (P, Rx, Ry, Rz, R) continue to have GateValue negated as before
- `allocator_alloc(count > 1)` must return guaranteed contiguous qubit indices
- `allocator_free()` updated to accept block free: `allocator_free(alloc, start, count)`
- When no contiguous block available in free-list, always allocate fresh qubits (no defragmentation)
- Internal data structure for free-list tracking: Claude's discretion
- C structural assertion only (no Python-level state vector checks)
- Debug-only: compiled out in release builds (`#ifdef DEBUG`)
- On failure: `fprintf` diagnostic message identifying leaked ancilla qubit, then `assert(0)` to crash
- Check triggers at `allocator_destroy()` -- all ancilla allocated with `is_ancilla=true` must have been freed by then
- Full test suite: `pytest tests/python/ -v` must pass with zero regressions
- New dedicated C-level unit test for `reverse_circuit_range()` with X/CCX gates
- New C-level unit tests for allocator block alloc/free
- New Python integration test for end-to-end ancilla block lifecycle
- All new C tests in `tests/c/` directory

### Claude's Discretion
- Internal data structure for block free-list (sorted list, block pairs, or hybrid approach)
- Exact test case details and edge cases covered
- Any additional assertions or safety checks deemed necessary

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| gcc | System | C compilation | Already used in `tests/c/Makefile` |
| assert.h | C standard | Debug assertions | Already used in `execution.c` line 64 and all C tests |
| pytest | Installed | Python test runner | Already used: `pytest tests/python/ -v` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| valgrind | Optional | Memory leak detection | If available, verify allocator changes don't leak |

No new libraries needed. All changes use existing C standard library facilities.

## Architecture Patterns

### Files to Modify

```
c_backend/src/execution.c           # Fix reverse_circuit_range() GateValue negation
c_backend/src/qubit_allocator.c     # Fix block alloc reuse, add ancilla tracking
c_backend/include/qubit_allocator.h # Add ancilla tracking fields to struct
c_backend/src/circuit_allocations.c # Possibly: allocator_destroy ancilla check
tests/c/test_reverse_circuit.c      # NEW: C unit test for reverse_circuit_range
tests/c/test_allocator_block.c      # NEW: C unit test for block alloc/free
tests/c/Makefile                    # Add new test targets
tests/python/test_ancilla_lifecycle.py  # NEW: Python integration test
```

### Pattern 1: Self-Inverse Gate Check in reverse_circuit_range()

**What:** Add switch/case on `g.Gate` to skip GateValue negation for self-inverse gates.

**Where:** `c_backend/src/execution.c`, lines 79-84 of `reverse_circuit_range()`.

**Current code (buggy):**
```c
// Line 84 of execution.c
g.GateValue = -g.GateValue; // Micro-opt: pow(-1,1) is always -1 (Phase 61)
```

**Fixed code:**
```c
// Invert gate value only for non-self-inverse gates
switch (g.Gate) {
    case X:
    case Y:
    case Z:
    case H:
    case M:
        // Self-inverse gates: GateValue unchanged
        break;
    default:
        // Phase gates (P, Rx, Ry, Rz, R): negate for inversion
        g.GateValue = -g.GateValue;
        break;
}
```

**Confidence:** HIGH -- The gate enum is `{X, Y, Z, R, H, Rx, Ry, Rz, P, M}` (types.h line 64). The self-inverse set {X, Y, Z, H, M} is mathematically correct (all are involutory: applying twice yields identity). The non-self-inverse set {R, Rx, Ry, Rz, P} are all rotation gates parameterized by angle, where inversion requires angle negation.

**IMPORTANT NOTE:** `run_instruction()` (line 48 of execution.c) has the SAME bug: `g.GateValue *= (invert ? -1.0 : 1.0)`. This also negates GateValue for self-inverse gates when `invert=1`. However, the CONTEXT.md scope only mentions `reverse_circuit_range()`. The `run_instruction()` bug should be noted as a related finding but the planner should decide whether to include it. Currently, `run_instruction()` with `invert=1` is only used for QFT subtraction (where all gates are P or H), so the bug is latent. It will become critical when Toffoli sequences are inverted via `run_instruction()`.

### Pattern 2: Block Free-List for Contiguous Allocation

**What:** Replace the simple freed-qubit stack with a data structure that tracks contiguous blocks, enabling reuse for multi-qubit allocations.

**Recommendation for free-list data structure:** Sorted array of `(start, count)` pairs with coalescing on free.

**Rationale:**
- The allocator is not performance-critical (called once per operation, not per gate)
- A sorted array allows binary search for best-fit block finding
- Coalescing adjacent freed blocks prevents fragmentation without defragmentation passes
- Simple to implement and debug (no tree structures needed)

**Struct changes to `qubit_allocator.h`:**
```c
// Block descriptor for contiguous qubit ranges
typedef struct {
    qubit_t start;
    num_t count;
} qubit_block_t;

typedef struct {
    qubit_t *indices;
    num_t capacity;
    num_t next_qubit;

    // Block-based free list (replaces freed_stack)
    qubit_block_t *freed_blocks;   // Sorted by start index
    num_t freed_block_count;
    num_t freed_block_capacity;

    // Ancilla tracking for lifecycle verification
    num_t ancilla_outstanding;     // Allocated but not freed ancilla count

    allocator_stats_t stats;

#ifdef DEBUG_OWNERSHIP
    char **owner_tags;
    num_t owner_capacity;
#endif
} qubit_allocator_t;
```

**Allocation algorithm for count > 1:**
```c
// 1. Search freed_blocks for block with count >= requested
// 2. If found: split block (use first `count` qubits, keep remainder)
// 3. If not found: allocate fresh from next_qubit (no defragmentation)
```

**Free algorithm with coalescing:**
```c
// 1. Insert (start, count) into freed_blocks maintaining sort order
// 2. Check if new block is adjacent to previous block -> merge
// 3. Check if new block is adjacent to next block -> merge
```

**Migration concern:** The existing `freed_stack` / `freed_count` / `freed_capacity` fields are used in the current allocator. The migration replaces these with `freed_blocks` / `freed_block_count` / `freed_block_capacity`. Single-qubit allocations (count=1) continue to work -- they just become block allocations with count=1.

**Confidence:** HIGH -- This is standard memory allocator design. The "no defragmentation" constraint from CONTEXT.md simplifies implementation significantly.

### Pattern 3: Ancilla Lifecycle Assertion at Destroy Time

**What:** Track ancilla allocations and verify all are freed before allocator destruction.

**Where:** `allocator_alloc()` increments `ancilla_outstanding` when `is_ancilla=true`, `allocator_free()` decrements it, `allocator_destroy()` checks it equals zero.

**Implementation:**
```c
// In allocator_alloc():
if (is_ancilla) {
    alloc->stats.ancilla_allocations += count;
#ifdef DEBUG
    alloc->ancilla_outstanding += count;
#endif
}

// In allocator_free():
// Note: allocator_free doesn't know if qubits were ancilla.
// Option A: Track per-qubit ancilla flag (requires bitmap)
// Option B: Track total allocated vs freed ancilla count
// Recommendation: Option B is simpler and sufficient for the assertion
```

**Problem:** `allocator_free()` does not know whether the freed qubits were originally allocated as ancilla. Two approaches:

**Approach A (per-qubit bitmap):** Add `bool *is_ancilla_map` to the allocator, set on alloc, check on free. Requires O(max_qubits) memory but gives precise tracking.

**Approach B (count-based):** Track `ancilla_allocated_count` and `ancilla_freed_count`. At destroy, assert they match. Simpler but doesn't identify WHICH qubit leaked.

**Recommendation:** Use Approach A (bitmap). The CONTEXT.md says the diagnostic should identify the leaked ancilla qubit. This requires per-qubit tracking. The memory overhead is tiny (1 byte per qubit, max 8192 = 8KB).

```c
// In qubit_allocator_t (under #ifdef DEBUG):
#ifdef DEBUG
    bool *is_ancilla_map;       // [qubit] -> was allocated as ancilla
    num_t ancilla_outstanding;  // count of allocated-but-not-freed ancilla qubits
#endif

// In allocator_destroy() (under #ifdef DEBUG):
#ifdef DEBUG
    if (alloc->ancilla_outstanding > 0) {
        fprintf(stderr, "ANCILLA LEAK: %u ancilla qubits not freed before destroy\n",
                alloc->ancilla_outstanding);
        for (num_t i = 0; i < alloc->next_qubit; i++) {
            if (alloc->is_ancilla_map[i]) {
                // Check if qubit i is still in the freed list
                bool found_freed = false;
                for (num_t j = 0; j < alloc->freed_block_count; j++) {
                    if (i >= alloc->freed_blocks[j].start &&
                        i < alloc->freed_blocks[j].start + alloc->freed_blocks[j].count) {
                        found_freed = true;
                        break;
                    }
                }
                if (!found_freed) {
                    fprintf(stderr, "  Leaked ancilla qubit: %u\n", i);
                }
            }
        }
        assert(0);
    }
#endif
```

**Confidence:** HIGH -- Standard debug-assertion pattern. The `#ifdef DEBUG` guard matches the CONTEXT.md decision. Note: the codebase currently uses `DEBUG_OWNERSHIP` not `DEBUG` for its existing debug guards. Using a different guard (`DEBUG`) is fine -- it allows the ancilla assertion to be enabled independently from ownership tracking.

### Anti-Patterns to Avoid

- **Fixing run_instruction() inversion in this phase:** While it has the same bug, the CONTEXT.md scoped the fix to `reverse_circuit_range()` only. Fixing both simultaneously risks regression in the QFT subtraction path (`invert=1` for QFT). Note the bug for the planner to flag.
- **Adding defragmentation to the allocator:** Explicitly excluded by CONTEXT.md. When no contiguous block is in the free-list, allocate fresh.
- **State vector checks for ancilla:** Explicitly excluded. The assertion is structural (count-based), not quantum-state-based.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sorted block insertion | Custom tree | Sorted array with memmove | Max 8192/min_block_size entries; linear scan + memmove is fast enough for the allocator's call frequency |
| Per-qubit ancilla tracking | Hash map | Simple boolean array | Fixed max size (ALLOCATOR_MAX_QUBITS = 8192), indexed by qubit ID |

## Common Pitfalls

### Pitfall 1: Forgetting to Update Cython Declarations

**What goes wrong:** If `qubit_allocator_t` struct changes (new fields for block tracking), the Cython `.pxd` declaration in `_core.pxd` (line 128) must also be updated. Otherwise, struct layout mismatch causes memory corruption at runtime.

**Why it happens:** The Cython `ctypedef struct qubit_allocator_t` in `_core.pxd` only declares fields it accesses (`stats`). As long as new fields are appended (not inserted), and Cython never `sizeof`s the struct directly, this MIGHT work. But it is fragile.

**How to avoid:** After modifying `qubit_allocator.h`, verify that the Cython declaration in `_core.pxd` remains compatible. If Cython accesses the struct through pointers only (which it does -- `qubit_allocator_t *alloc`), field additions at the end are safe without Cython changes. But if `#ifdef DEBUG` fields are conditionally compiled, the struct layout changes between debug and release builds, which can cause subtle issues if the Cython extension is built without `-DDEBUG`.

**Mitigation:** Place all `#ifdef DEBUG` fields at the END of the struct, after all non-conditional fields. This ensures the struct prefix is identical regardless of build mode. The Cython side only accesses `stats` (via `allocator_get_stats()` accessor function), so it never dereferences struct offsets that depend on debug fields.

### Pitfall 2: Breaking the Freed Stack -> Block List Migration

**What goes wrong:** The current `freed_stack` stores individual qubit indices. Replacing it with `freed_blocks` changes the semantics. If any code path still pushes individual qubits to `freed_stack` (e.g., a code path we missed), it will segfault or corrupt memory.

**How to avoid:** Search all callers of `allocator_free()` before changing the internal data structure. Current callers:
- `c_backend/src/Integer.c:134` -- `allocator_free(circ->allocator, start, width)` (frees block of `width` qubits)
- `src/quantum_language/qint.pyx:410` -- `allocator_free(alloc, self.allocated_start, self.bits)` (frees block)
- `src/quantum_language/_core.pyx:845` -- `allocator_free(alloc, start, count)` (Python wrapper)

All three already pass `(start, count)` -- no code path pushes individual indices outside of `allocator_free()`. The migration is contained within `qubit_allocator.c`.

### Pitfall 3: Coalescing Edge Cases

**What goes wrong:** Block coalescing on free can fail if:
- Two adjacent blocks are freed in non-adjacent order (e.g., free block [10,3] then free block [5,5] -- should coalesce to [5,8])
- A freed block is exactly at `next_qubit` boundary -- could coalesce by reducing `next_qubit`
- Empty free list after coalescing all blocks

**How to avoid:** Write explicit unit tests for each coalescing scenario:
1. Free [5,3] then [8,2] -> coalesce to [5,5]
2. Free [8,2] then [5,3] -> coalesce to [5,5] (reverse order)
3. Free [5,3] then [10,2] then [8,2] -> coalesce all to [5,7]
4. Allocate [0,5], free [0,5], allocate [0,5] -> reuse works

### Pitfall 4: Regression in QFT Path from reverse_circuit_range Fix

**What goes wrong:** The current `reverse_circuit_range()` negates GateValue for ALL gates. QFT circuits contain only P and H gates. For P gates, negation is correct (P(theta) -> P(-theta)). For H gates, GateValue is 0 (set in `gate.c` line 173: `g->GateValue = 0`), so negating 0 gives 0 -- no behavior change. The fix adds a switch/case that skips negation for H gates. Since H.GateValue = 0, `0 == -0` in IEEE 754, so the fix is a no-op for H gates. **No regression risk for QFT path.**

However, if any existing code relies on the (incorrect) negated GateValue of X-type gates in reversed circuits, the fix could change behavior. Search for code that reads GateValue after `reverse_circuit_range()`:
- The optimizer's `gates_are_inverse()` checks `GateValue` -- for non-P gates, it compares `G1->GateValue != G2->GateValue` (line 457-458 of gate.c). If a reversed X gate had GateValue=-1, the optimizer would NOT identify it as inverse of the original X gate (GateValue=1), meaning the optimizer would not cancel X-X pairs created by uncomputation. Fixing GateValue to remain 1 means the optimizer WILL now correctly cancel X-X pairs. This is the desired behavior.

**Confidence:** HIGH -- The fix strictly improves correctness for both QFT and Toffoli paths.

### Pitfall 5: `run_instruction()` Has the Same Bug

**What goes wrong:** `run_instruction()` line 48: `g.GateValue *= (invert ? -1.0 : 1.0)` also negates GateValue for self-inverse gates. Currently this only matters for QFT subtraction where `invert=1` is passed, and QFT sequences only contain P and H gates. P gates need negation (correct). H gates have GateValue=0 (-0.0 == 0.0, no effect). So the bug is latent for QFT.

**When it becomes critical:** When Toffoli sequences are passed to `run_instruction()` with `invert=1` for subtraction. This is a Phase 66+ concern but should be flagged.

**Recommendation for planner:** Consider adding the same switch/case fix to `run_instruction()` in this phase, since it is the exact same 6-line patch and prevents a future bug. OR explicitly document it as a known issue for the next phase.

## Code Examples

### Example 1: C Unit Test for reverse_circuit_range (test_reverse_circuit.c)

```c
#include <assert.h>
#include <stdio.h>
#include "circuit.h"
#include "execution.h"

static void test_reverse_x_gate_preserves_value(void) {
    printf("test_reverse_x_gate_preserves_value... ");
    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    // Add an X gate (GateValue=1)
    gate_t g;
    x(&g, 0);
    add_gate(circ, &g);
    int start_layer = 0;
    int end_layer = circ->used_layer;

    // Reverse the circuit range
    reverse_circuit_range(circ, start_layer, end_layer);

    // The reversed X gate should also have GateValue=1 (not -1)
    // It was added after end_layer
    int found = 0;
    for (int lay = end_layer; lay < (int)circ->used_layer; lay++) {
        for (int gi = 0; gi < (int)circ->used_gates_per_layer[lay]; gi++) {
            gate_t *reversed = &circ->sequence[lay][gi];
            if (reversed->Gate == X && reversed->Target == 0) {
                assert(reversed->GateValue == 1.0 &&
                       "Reversed X gate must have GateValue=1, not -1");
                found = 1;
            }
        }
    }
    assert(found && "Should find reversed X gate");
    printf("PASS\n");
    free_circuit(circ);
}

static void test_reverse_ccx_gate_preserves_value(void) {
    printf("test_reverse_ccx_gate_preserves_value... ");
    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    gate_t g;
    ccx(&g, 0, 1, 2);
    add_gate(circ, &g);
    int start_layer = 0;
    int end_layer = circ->used_layer;

    reverse_circuit_range(circ, start_layer, end_layer);

    int found = 0;
    for (int lay = end_layer; lay < (int)circ->used_layer; lay++) {
        for (int gi = 0; gi < (int)circ->used_gates_per_layer[lay]; gi++) {
            gate_t *reversed = &circ->sequence[lay][gi];
            if (reversed->Gate == X && reversed->NumControls == 2) {
                assert(reversed->GateValue == 1.0 &&
                       "Reversed CCX gate must have GateValue=1");
                found = 1;
            }
        }
    }
    assert(found && "Should find reversed CCX gate");
    printf("PASS\n");
    free_circuit(circ);
}

static void test_reverse_p_gate_negates_value(void) {
    printf("test_reverse_p_gate_negates_value... ");
    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    gate_t g;
    p(&g, 0, 1.5);
    add_gate(circ, &g);
    int start_layer = 0;
    int end_layer = circ->used_layer;

    reverse_circuit_range(circ, start_layer, end_layer);

    int found = 0;
    for (int lay = end_layer; lay < (int)circ->used_layer; lay++) {
        for (int gi = 0; gi < (int)circ->used_gates_per_layer[lay]; gi++) {
            gate_t *reversed = &circ->sequence[lay][gi];
            if (reversed->Gate == P) {
                assert(reversed->GateValue == -1.5 &&
                       "Reversed P gate must have negated GateValue");
                found = 1;
            }
        }
    }
    assert(found && "Should find reversed P gate");
    printf("PASS\n");
    free_circuit(circ);
}
```

### Example 2: C Unit Test for Allocator Block Alloc/Free

```c
#include <assert.h>
#include <stdio.h>
#include "qubit_allocator.h"

static void test_block_alloc_contiguous(void) {
    printf("test_block_alloc_contiguous... ");
    qubit_allocator_t *alloc = allocator_create(128);
    assert(alloc != NULL);

    qubit_t start = allocator_alloc(alloc, 4, false);
    assert(start != (qubit_t)-1);
    // Qubits should be contiguous: start, start+1, start+2, start+3
    // (Verified implicitly: allocator_alloc returns start index,
    //  caller uses start..start+count-1)

    allocator_destroy(alloc);
    printf("PASS\n");
}

static void test_block_reuse_after_free(void) {
    printf("test_block_reuse_after_free... ");
    qubit_allocator_t *alloc = allocator_create(128);

    qubit_t first = allocator_alloc(alloc, 4, false);
    allocator_free(alloc, first, 4);

    qubit_t second = allocator_alloc(alloc, 4, false);
    assert(second == first && "Should reuse freed 4-qubit block");

    allocator_destroy(alloc);
    printf("PASS\n");
}

static void test_block_alloc_fresh_when_no_fit(void) {
    printf("test_block_alloc_fresh_when_no_fit... ");
    qubit_allocator_t *alloc = allocator_create(128);

    qubit_t first = allocator_alloc(alloc, 3, false);  // [0,1,2]
    allocator_free(alloc, first, 3);                    // Free [0,1,2]

    qubit_t second = allocator_alloc(alloc, 5, false);  // Need 5, only 3 free
    assert(second == 3 && "Should allocate fresh when freed block too small");

    allocator_destroy(alloc);
    printf("PASS\n");
}
```

### Example 3: Makefile Target Pattern

```makefile
# Sources for reverse_circuit tests
REVERSE_SRCS = $(BACKEND_SRC)/execution.c \
               $(BACKEND_SRC)/optimizer.c \
               $(BACKEND_SRC)/gate.c \
               $(BACKEND_SRC)/qubit_allocator.c \
               $(BACKEND_SRC)/circuit_allocations.c \
               $(BACKEND_SRC)/circuit_output.c \
               $(BACKEND_SRC)/circuit_stats.c \
               $(BACKEND_SRC)/circuit_optimizer.c

# Sources for allocator block tests (minimal)
ALLOC_SRCS = $(BACKEND_SRC)/qubit_allocator.c

test_reverse_circuit: test_reverse_circuit.c $(REVERSE_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_allocator_block: test_allocator_block.c $(ALLOC_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Debug build for ancilla assertions
test_allocator_block_debug: test_allocator_block.c $(ALLOC_SRCS)
	$(CC) $(CFLAGS) -DDEBUG -o $@ $^ $(LDFLAGS)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Negate all GateValues in reversal | Skip negation for self-inverse gates | This phase | Enables Toffoli uncomputation |
| Single-qubit free-list (stack) | Block-based free-list with coalescing | This phase | Enables O(n) ancilla reuse |
| No ancilla lifecycle verification | Debug assertion at destroy time | This phase | Catches leaked ancilla early |

**Note:** The existing `freed_stack` in `qubit_allocator.c` has been in place since Phase 61. It was designed for QFT operations which only allocate/free individual qubits. Toffoli operations will be the first to require multi-qubit block allocation.

## Open Questions

1. **Should `run_instruction()` also be fixed in this phase?**
   - What we know: It has the identical GateValue negation bug on line 48. Currently harmless for QFT (P and H gates only). Will become critical when Toffoli sequences are inverted.
   - Recommendation: Fix it now (same 6-line patch, zero risk for QFT since H.GateValue=0 and P needs negation). Flag to planner for decision.

2. **Build system for `-DDEBUG` flag**
   - What we know: The `setup.py` does not pass `-DDEBUG` to the C compiler. There is `CYTHON_DEBUG` env var for Cython-level checks but no mechanism for C-level `#ifdef DEBUG`.
   - What's unclear: Whether the planner wants a new env var (e.g., `QUANTUM_DEBUG=1`) or just rely on the C test Makefile passing `-DDEBUG`.
   - Recommendation: For C tests, the Makefile can pass `-DDEBUG`. For the Python build, add `-DDEBUG` when `CYTHON_DEBUG` env var is set (piggyback on existing mechanism). This way, `CYTHON_DEBUG=1 pip install -e .` enables both Cython and C debug checks.

3. **Backward compatibility of freed_stack removal**
   - What we know: No external code accesses `freed_stack`, `freed_count`, or `freed_capacity` directly. These are internal to `qubit_allocator.c`. The Cython declaration in `_core.pxd` does not expose these fields.
   - Recommendation: Safe to replace. No backward compatibility concern.

## Sources

### Primary (HIGH confidence)
- `c_backend/src/execution.c` -- `reverse_circuit_range()` at line 62, `run_instruction()` at line 14
- `c_backend/src/qubit_allocator.c` -- `allocator_alloc()` at line 86, `allocator_free()` at line 155
- `c_backend/include/qubit_allocator.h` -- struct definition, API declarations
- `c_backend/include/types.h` -- Gate enum: `{X, Y, Z, R, H, Rx, Ry, Rz, P, M}` at line 64
- `c_backend/src/gate.c` -- Gate constructors: `x()` sets GateValue=1 (line 190), `h()` sets GateValue=0 (line 173)
- `c_backend/src/Integer.c` -- `free_element()` calls `allocator_free(circ->allocator, start, width)` (line 134)
- `tests/c/Makefile` -- Existing C test build pattern
- `tests/c/test_hot_path_add.c` -- Existing C test code pattern
- `setup.py` -- Build system, compiler flags at line 48
- `.planning/research/PITFALLS-TOFFOLI-ARITHMETIC.md` -- Pitfalls 3 and 7 identify these exact bugs

### Secondary (MEDIUM confidence)
- Quantum gate mathematics: X, Y, Z, H, M are all involutory (self-inverse) -- standard quantum computing textbook knowledge, verified against gate constructor code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all changes to existing files
- Architecture: HIGH -- codebase fully inspected, all affected files identified, all callers traced
- Pitfalls: HIGH -- exhaustive search of callers, struct layout analysis, Cython compatibility checked

**Research date:** 2026-02-14
**Valid until:** Indefinite (codebase-specific findings, no external dependency versioning)
