# Phase 58: Hardcoded Sequences (1-8 bit) - Research

**Researched:** 2026-02-05
**Domain:** C static gate arrays, Draper QFT addition circuits
**Confidence:** HIGH

## Summary

This research covers the implementation of hardcoded (pre-computed) addition sequences for 1-8 bit widths, eliminating runtime QFT generation overhead for small quantum integers. The Draper QFT adder is the core algorithm used, and the existing dynamic implementation in `IntegerAddition.c` provides the reference for gate sequence generation.

The approach is straightforward: extract the gate sequences that the dynamic generator produces for each bit width, encode them as static const arrays in C, and route small-width addition calls through a dispatch function that returns pointers to these precomputed sequences. This eliminates all runtime computation (QFT construction, rotation angle calculation, memory allocation) for the most common addition widths.

**Primary recommendation:** Manually transcribe gate sequences from the dynamic generator output, organized as static const `gate_t` arrays. Use a dispatch table pattern with width indexing for O(1) lookup. The existing `sequence_t` struct format provides the template.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| C standard library | C23 | Static array initialization, math constants | Project standard (Makefile: `-std=c23`) |
| `<math.h>` | stdlib | M_PI for rotation angles | Already used throughout c_backend |
| gate_t struct | existing | Gate representation | Project's established gate format |
| sequence_t struct | existing | Sequence representation | Project's established sequence format |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `types.h` | existing | Type definitions (gate_t, sequence_t, qubit_t) | Required for all gate/sequence code |
| `gate.h` | existing | Gate helper functions (h, cp, p) | Reference for gate field population |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Static arrays | Code generation script | More automated, but adds build dependency; manual is simpler for 8 widths |
| Per-width source files | Single file | Per-width is more maintainable at scale; single file OK for 1-8 |
| switch dispatch | Function pointer table | Function pointers add indirection; switch compiles to jump table anyway |

**Installation:**
No new dependencies required. All code uses existing C infrastructure.

## Architecture Patterns

### Recommended Project Structure
```
c_backend/
├── include/
│   ├── sequences.h          # NEW: Dispatch function, constants
│   └── ...existing...
├── src/
│   ├── sequences/           # NEW: Subdirectory for sequence files
│   │   ├── add_seq_1_4.c    # 1-4 bit QQ_add and cQQ_add sequences
│   │   └── add_seq_5_8.c    # 5-8 bit QQ_add and cQQ_add sequences
│   └── IntegerAddition.c    # Modified: Routes to hardcoded when width <= 8
```

### Pattern 1: Static Gate Array with Layers
**What:** Hardcoded gates stored as static const arrays, with layer/gate-count metadata
**When to use:** Pre-computed sequences where gate order and structure are fixed
**Example:**
```c
// Source: Project pattern based on types.h gate_t struct
// 1-bit QQ_add: QFT(1) + addition(1) + IQFT(1) = 3 gates total
static const gate_t QQ_ADD_1_GATES[] = {
    // Layer 0: QFT - H on qubit 0
    {.Gate = H, .Target = 0, .NumControls = 0, .GateValue = 0},

    // Layer 1: Addition rotation - CP(pi) from control qubit 1 to target 0
    {.Gate = P, .Target = 0, .NumControls = 1, .Control = {1}, .GateValue = M_PI},

    // Layer 2: IQFT - H on qubit 0
    {.Gate = H, .Target = 0, .NumControls = 0, .GateValue = 0},
};

static const num_t QQ_ADD_1_GATES_PER_LAYER[] = {1, 1, 1};
static const num_t QQ_ADD_1_NUM_LAYERS = 3;
```

### Pattern 2: Dispatch Table Function
**What:** Single function with switch statement routing by width
**When to use:** Selecting between multiple pre-computed variants based on parameter
**Example:**
```c
// Source: Project pattern for width-parameterized operations
const sequence_t* get_hardcoded_QQ_add(int bits) {
    // Returns NULL for widths > 8, caller must fall back to dynamic
    switch (bits) {
        case 1: return &HARDCODED_QQ_ADD_1;
        case 2: return &HARDCODED_QQ_ADD_2;
        // ... cases 3-8
        default: return NULL;  // Caller falls back to dynamic
    }
}
```

### Pattern 3: sequence_t Wrapper Struct
**What:** Static sequence_t struct wrapping the gate arrays
**When to use:** Providing sequence_t* interface to hardcoded data
**Example:**
```c
// Source: Project types.h sequence_t definition
static const sequence_t HARDCODED_QQ_ADD_1 = {
    .seq = (gate_t**)QQ_ADD_1_LAYER_PTRS,  // Array of layer pointers
    .num_layer = QQ_ADD_1_NUM_LAYERS,
    .used_layer = QQ_ADD_1_NUM_LAYERS,
    .gates_per_layer = (num_t*)QQ_ADD_1_GATES_PER_LAYER,
};
```

### Anti-Patterns to Avoid
- **Runtime allocation for hardcoded data:** Don't malloc/calloc for static sequences; use static const arrays
- **Deriving controlled from uncontrolled at runtime:** CONTEXT.md specifies both variants are fully hardcoded separately
- **Hardcoding qubit indices for specific circuits:** Indices must be canonical (0-based), mapped at runtime
- **Including initialization gates (X, CX) in sequences:** The sequence contains only QFT + addition + IQFT, not value initialization

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rotation angle calculation | Compute at runtime | Pre-computed exact values (M_PI/2, M_PI/4, etc.) | Eliminates runtime math |
| Layer structure | Flatten to single array | Preserve layer grouping | Matches existing `sequence_t` interface |
| Gate initialization | New gate struct design | Existing `gate_t` fields | Consistency with runtime paths |
| Width validation | Inline checks everywhere | Single dispatch function | Centralized validation |

**Key insight:** The hardcoded sequences must produce identical results to dynamic generation. Maintaining the same `sequence_t`/`gate_t` structure ensures compatibility and simplifies testing.

## Common Pitfalls

### Pitfall 1: Gate Angle Precision
**What goes wrong:** Using approximate float values instead of exact M_PI expressions
**Why it happens:** Tempting to copy-paste numeric values from debug output
**How to avoid:** Always use M_PI/2, M_PI/4, M_PI/8, etc. directly
**Warning signs:** Subtle numerical differences in gate-by-gate comparison tests

### Pitfall 2: Layer vs. Gate Ordering Confusion
**What goes wrong:** Gates placed in wrong layers, breaking parallelism assumptions
**Why it happens:** Dynamic generator has complex layer indexing logic
**How to avoid:** Trace through QFT()/QQ_add/QFT_inverse() gate-by-gate, document layer boundaries
**Warning signs:** Different gate counts per layer than dynamic generator

### Pitfall 3: Qubit Index Mapping Errors
**What goes wrong:** Hardcoded sequences use absolute qubit indices instead of canonical
**Why it happens:** Copying from specific circuit output without understanding mapping
**How to avoid:** Use canonical indices (0 = target LSB, bits = control LSB, etc.)
**Warning signs:** Tests pass for specific widths but fail when qubits are remapped

### Pitfall 4: Control Qubit Array Initialization
**What goes wrong:** `Control` array not fully initialized, contains garbage
**Why it happens:** `gate_t` has `Control[MAXCONTROLS]` but partial initialization
**How to avoid:** Use designated initializers: `.Control = {ctrl_qubit}` for single control
**Warning signs:** Valgrind/ASan reports, inconsistent behavior

### Pitfall 5: Static Pointer Arrays
**What goes wrong:** Trying to make `seq` field point to static arrays
**Why it happens:** `sequence_t.seq` is `gate_t**` (array of layer pointers)
**How to avoid:** Create static `gate_t*[]` arrays pointing to each layer's gate array
**Warning signs:** Compile errors, segfaults on access

## Code Examples

### Gate Counts by Width (QQ_add)

From dynamic generator analysis:

```
Width | Total Gates | Formula: 3 * bits * (bits+1) / 2
------+-------------+----------------------------------
  1   |      3      | QFT(1) + Add(1) + IQFT(1)
  2   |      9      | QFT(3) + Add(3) + IQFT(3)
  3   |     18      | QFT(6) + Add(6) + IQFT(6)
  4   |     30      | QFT(10) + Add(10) + IQFT(10)
  5   |     45      | QFT(15) + Add(15) + IQFT(15)
  6   |     63      | QFT(21) + Add(21) + IQFT(21)
  7   |     84      | QFT(28) + Add(28) + IQFT(28)
  8   |    108      | QFT(36) + Add(36) + IQFT(36)
```

### 1-bit QQ_add Gate Sequence (Reference)
```c
// Qubit layout: [0] = target, [1] = control (b operand)
// QFT on target qubit 0:
//   Layer 0: H(0)
// Addition in Fourier domain:
//   Layer 1: CP(pi, target=0, control=1)
// IQFT on target qubit 0:
//   Layer 2: H(0)

static const gate_t QQ_ADD_1_L0[] = {
    {.Gate = H, .Target = 0, .NumControls = 0, .GateValue = 0}
};
static const gate_t QQ_ADD_1_L1[] = {
    {.Gate = P, .Target = 0, .NumControls = 1, .Control = {1}, .GateValue = M_PI}
};
static const gate_t QQ_ADD_1_L2[] = {
    {.Gate = H, .Target = 0, .NumControls = 0, .GateValue = 0}
};
```

### 2-bit QQ_add Gate Sequence Structure
```
// Qubit layout: [0,1] = target (LSB,MSB), [2,3] = control b (LSB,MSB)
//
// QFT (textbook, MSB-first processing):
//   Layer 0: H(1)                         -- MSB hadamard
//   Layer 1: CP(pi/2, target=1, ctrl=0)   -- MSB-LSB controlled phase
//   Layer 2: H(0)                         -- LSB hadamard
//
// Addition rotations (from b register to Fourier-domain a):
//   Layer 3: CP(pi, target=0, ctrl=2)     -- b[0] to Fourier(a)[0]
//            CP(pi/2, target=1, ctrl=2)   -- b[0] to Fourier(a)[1] (note: same layer)
//   Layer 4: CP(pi, target=1, ctrl=3)     -- b[1] to Fourier(a)[1]
//
// IQFT (reverse of QFT):
//   Layer 5: H(0)
//   Layer 6: CP(-pi/2, target=1, ctrl=0)
//   Layer 7: H(1)
```

### Integration with Existing API
```c
// In IntegerAddition.c, modify QQ_add():
sequence_t *QQ_add(int bits) {
    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // NEW: Try hardcoded for small widths
    if (bits <= 8) {
        const sequence_t* hardcoded = get_hardcoded_QQ_add(bits);
        if (hardcoded != NULL) {
            return (sequence_t*)hardcoded;  // Cast away const for API compat
        }
    }

    // Check cache for dynamically generated
    if (precompiled_QQ_add_width[bits] != NULL)
        return precompiled_QQ_add_width[bits];

    // ... existing dynamic generation code ...
}
```

### Header File Structure
```c
// sequences.h
#ifndef QUANTUM_SEQUENCES_H
#define QUANTUM_SEQUENCES_H

#include "types.h"

// Dispatch functions - return NULL if width not hardcoded
const sequence_t* get_hardcoded_QQ_add(int bits);   // Plain QQ addition
const sequence_t* get_hardcoded_cQQ_add(int bits);  // Controlled QQ addition

// Subtraction: caller reverses the addition sequence at runtime
// (reverse gate order, negate phase rotation angles)

// Width limits
#define HARDCODED_MAX_WIDTH 8

#endif // QUANTUM_SEQUENCES_H
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Always compute QFT at runtime | Cache after first use (precompiled_*) | Existing | Faster repeated calls |
| Single fixed width | Width-parameterized (Phase 5) | Phase 5 | Support for 1-64 bit integers |
| Global state for parameters | Explicit parameters | Phase 11 | Thread-safe, cleaner API |

**This phase adds:**
- Static compile-time sequences (zero runtime computation for widths 1-8)
- Eliminates malloc/calloc for common widths
- True O(1) lookup with no computation

## Open Questions

None critical. All decisions from CONTEXT.md are clear and implementable.

**Clarifications discovered during research:**

1. **Controlled variants (cQQ_add) have different structure than QQ_add**
   - What we know: cQQ_add uses more complex half-rotation technique with CNOTs
   - What's unclear: Exact layer structure differs significantly from simple QQ_add
   - Recommendation: Trace through `cQQ_add()` in IntegerAddition.c for each width separately

2. **CQ_add has parameterized rotation angles**
   - What we know: CQ_add/cCQ_add depend on classical value parameter
   - What's unclear: Whether these should be hardcoded (template with angle slots?)
   - Recommendation: Per CONTEXT.md, focus on QQ_add and cQQ_add; CQ_add uses cache-and-update pattern which already works well

## Sources

### Primary (HIGH confidence)
- `/c_backend/src/IntegerAddition.c` - Dynamic QQ_add, cQQ_add implementation (lines 138-448)
- `/c_backend/include/types.h` - gate_t, sequence_t struct definitions (lines 64-82)
- `/c_backend/src/gate.c` - QFT, QFT_inverse, gate helper implementations (lines 304-443)
- `/c_backend/include/arithmetic_ops.h` - API documentation for addition functions

### Secondary (MEDIUM confidence)
- `.planning/phases/58-hardcoded-sequences-1-8/58-CONTEXT.md` - User decisions on format, organization, validation
- `/tests/test_add.py` - Existing addition verification tests covering widths 1-8
- `/Makefile`, `/CMakeLists.txt`, `/setup.py` - Build system references for adding new source files

### Tertiary (LOW confidence)
- OpenQASM output analysis (dynamic execution) - Gate structure confirmation
- `.planning/phases/57-cython-optimization/57-CONTEXT.md` - Related optimization context

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All code uses existing project infrastructure
- Architecture: HIGH - Patterns derived directly from existing codebase
- Pitfalls: HIGH - Based on analysis of actual `gate_t`/`sequence_t` usage

**Research date:** 2026-02-05
**Valid until:** 2026-03-07 (30 days - stable domain, internal project code)

---

## Implementation Checklist for Planner

Based on this research, Phase 58 implementation should include:

1. **HCS-01: Pre-computed addition sequences for 1-4 bit widths**
   - Create `c_backend/src/sequences/` directory
   - Create `add_seq_1_4.c` with QQ_add sequences for widths 1, 2, 3, 4
   - Include cQQ_add sequences for widths 1, 2, 3, 4
   - Estimated: ~240 LOC for gates + ~60 LOC for layer/wrapper structs = ~300 LOC

2. **HCS-02: Pre-computed addition sequences for 5-8 bit widths**
   - Create `add_seq_5_8.c` with QQ_add sequences for widths 5, 6, 7, 8
   - Include cQQ_add sequences for widths 5, 6, 7, 8
   - Estimated: ~600 LOC for gates + ~80 LOC for layer/wrapper structs = ~680 LOC

3. **Create sequences.h header**
   - Dispatch function declarations
   - HARDCODED_MAX_WIDTH constant
   - Include guards and documentation

4. **Modify IntegerAddition.c for routing**
   - Add `#include "sequences.h"`
   - Modify `QQ_add()` to check hardcoded first for widths 1-8
   - Modify `cQQ_add()` similarly
   - Fallback to dynamic generation for width > 8

5. **Update build system**
   - Add new source files to `setup.py` c_sources list
   - Add to `CMakeLists.txt` if used
   - Verify Makefile glob pattern (`c_backend/src/*.c`) captures subdirectory

6. **HCS-05: Validation tests comparing hardcoded vs dynamic**
   - Create `tests/test_hardcoded_sequences.py`
   - Gate-by-gate comparison for widths 1-8
   - One-time verification (not in regular CI per CONTEXT.md)

7. **HCS-06: Automatic fallback for widths > 8**
   - Already handled by dispatch returning NULL
   - Verify existing dynamic code path still works for widths 9+
   - Add explicit tests for widths 9, 16, 32 to confirm fallback
