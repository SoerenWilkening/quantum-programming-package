# Phase 59: Hardcoded Sequences (9-16 bit) - Research

**Researched:** 2026-02-06
**Domain:** C static gate arrays, Draper QFT addition circuits, Python code generation
**Confidence:** HIGH

## Summary

This research covers extending pre-computed addition sequences from widths 1-8 (Phase 58) to widths 1-16, including restructuring files to one-per-width, adding CQ_add/cCQ_add coverage, and creating a unified generation script. Phase 58 established the foundational patterns: static `const gate_t` arrays, `SEQ_PI` compile-time constant, dispatch functions, and routing in `IntegerAddition.c`. Phase 59 builds on this directly.

The main new challenges are: (1) **scale** -- widths 9-16 produce much larger files (~45,000 lines of C for QQ/cQQ alone), making the unified Python generation script essential rather than optional; (2) **CQ_add/cCQ_add parametric sequences** -- these cannot be static const because rotation angles change per call, requiring a template-initialization approach where the structure is hardcoded but the sequence is dynamically allocated and cached; (3) **file restructuring** -- splitting existing `add_seq_1_4.c` and `add_seq_5_8.c` into 8 individual files and generating 8 new ones, plus updating the dispatch infrastructure; and (4) **testing constraints** -- QQ_add verification for widths 11+ requires 33+ qubits for out-of-place addition, exceeding practical statevector simulation limits, so testing must use in-place CQ_add or constrained QQ_add tests.

**Primary recommendation:** Build the unified generation script first (it becomes the single source of truth), use it to generate all 16 per-width C files, restructure dispatch to use preprocessor guards per width, and implement CQ_add/cCQ_add as template-initialization functions that allocate once and cache.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**File splitting strategy:**
- One C source file per bit width: `add_seq_1.c` through `add_seq_16.c`
- Retroactively split existing 1-8 bit files (replace `add_seq_1_4.c` and `add_seq_5_8.c`)
- Naming convention: `add_seq_N.c` (e.g., `add_seq_9.c`, `add_seq_16.c`)

**Operation coverage:**
- All four addition variants for all widths 1-16: QQ_add, cQQ_add, CQ_add, cCQ_add
- Backfill CQ_add and cCQ_add for widths 1-8 (currently only QQ_add/cQQ_add)
- CQ_add/cCQ_add use parametric approach: hardcode gate structure, inject classical rotation angles at runtime (one sequence per width)

**Generation approach:**
- Single unified Python script that generates all 16 width files (`add_seq_1.c` through `add_seq_16.c`)
- Script calls the C backend's dynamic generation as reference (guaranteed to match)
- Old generation scripts (`generate_seq_5_8.py`, etc.) kept as reference but marked deprecated
- No Makefile target -- standalone script only

**Fallback threshold:**
- `MAX_HARDCODED_WIDTH` compile-time constant in `sequences.h` (set to 16)
- Design allows extending beyond 16 in the future (door left open, not planned)
- Graceful fallback via preprocessor guards (`#ifdef SEQ_WIDTH_N`) -- allows partial builds
- Unavailable widths conditionally excluded at compile time, caller falls back to dynamic generation

### Claude's Discretion
- Internal function naming within generated files
- Exact preprocessor guard naming convention
- How to structure the unified generation script internally
- Whether to use a template approach or direct string generation

### Deferred Ideas (OUT OF SCOPE)
- Hardcoded subtraction sequences (QQ_sub, cQQ_sub, etc.) -- could be a future optimization phase
- Extending hardcoded sequences beyond 16-bit -- leave door open but no current plans
</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| C standard library | C23 | Static array initialization, math constants | Project standard (`-std=c23` not required for generated code but project uses it) |
| `types.h` | existing | `gate_t`, `sequence_t`, `qubit_t`, `num_t` | Project's core gate/sequence types |
| `sequences.h` | existing (Phase 58) | Dispatch function declarations, `HARDCODED_MAX_WIDTH` | Will be modified to support widths 1-16 |
| Python 3.11+ | existing | Unified generation script | Project standard, existing scripts use Python |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `gate.h` / `gate.c` | existing | Gate helper functions (`h()`, `cp()`, `p()`, `cx()`) | Reference for gate field population |
| `IntegerAddition.c` | existing (Phase 58) | Dynamic generation, routing to hardcoded | Modified to route widths 1-16 |
| `setup.py` | existing | Build configuration for Cython extensions | Add new source files to `c_sources` |
| `scripts/generate_seq_*.py` | existing (Phase 58) | Reference generation scripts | Templates for unified script |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 16 individual files | Multi-width groupings (e.g., 9-12, 13-16) | Individual files match CONTEXT.md decision; preprocessor guards give same partial-build flexibility |
| Python generation script | C preprocessor macros | Python script is more readable and maintainable for this complexity |
| Template-init for CQ/cCQ | Static const with memcpy | Template-init avoids full array copy; only angle fields need updating |

**Installation:**
No new dependencies required. All code uses existing C and Python infrastructure.

## Architecture Patterns

### Recommended Project Structure

```
c_backend/
├── include/
│   └── sequences.h          # MODIFIED: 16-width dispatch, preprocessor guards
├── src/
│   ├── sequences/
│   │   ├── add_seq_1.c       # NEW: Replaces part of add_seq_1_4.c
│   │   ├── add_seq_2.c       # NEW: Replaces part of add_seq_1_4.c
│   │   ├── ...
│   │   ├── add_seq_8.c       # NEW: Replaces part of add_seq_5_8.c
│   │   ├── add_seq_9.c       # NEW: Width 9
│   │   ├── ...
│   │   └── add_seq_16.c      # NEW: Width 16
│   └── IntegerAddition.c     # MODIFIED: Route widths 1-16, CQ_add/cCQ_add
scripts/
├── generate_seq_all.py       # NEW: Unified generation script
├── generate_seq_1_4.py       # DEPRECATED (kept as reference)
└── generate_seq_5_8.py       # DEPRECATED (kept as reference)
```

### Pattern 1: Per-Width File Structure (QQ_add + cQQ_add)

**What:** Each `add_seq_N.c` contains static const QQ_add and cQQ_add gate arrays, plus a per-width dispatch helper.

**When to use:** For QQ_add and cQQ_add which have fully deterministic gate sequences.

**Example structure for `add_seq_N.c`:**
```c
// add_seq_N.c - Hardcoded sequences for N-bit width
// Generated by scripts/generate_seq_all.py - DO NOT EDIT MANUALLY

#include "sequences.h"

#ifndef SEQ_PI
#define SEQ_PI 3.14159265358979323846
#endif

#ifdef SEQ_WIDTH_N

// === QQ_ADD WIDTH N ===
static const gate_t QQ_ADD_N_L0[] = { ... };
// ... layers ...
static const gate_t *QQ_ADD_N_LAYERS[] = { ... };
static const num_t QQ_ADD_N_GPL[] = { ... };
static const sequence_t HARDCODED_QQ_ADD_N = { ... };

// === cQQ_ADD WIDTH N ===
static const gate_t cQQ_ADD_N_L0[] = { ... };
// ... layers ...
static const sequence_t HARDCODED_cQQ_ADD_N = { ... };

// === CQ_ADD WIDTH N (parametric template) ===
sequence_t *init_hardcoded_CQ_add_N(void) { ... }

// === cCQ_ADD WIDTH N (parametric template) ===
sequence_t *init_hardcoded_cCQ_add_N(void) { ... }

// === DISPATCH ===
const sequence_t *get_hardcoded_QQ_add_N(void) { return &HARDCODED_QQ_ADD_N; }
const sequence_t *get_hardcoded_cQQ_add_N(void) { return &HARDCODED_cQQ_ADD_N; }
sequence_t *get_hardcoded_CQ_add_N(void) { ... }   // returns cached mutable
sequence_t *get_hardcoded_cCQ_add_N(void) { ... }   // returns cached mutable

#endif // SEQ_WIDTH_N
```

### Pattern 2: CQ_add/cCQ_add Parametric Template

**What:** Dynamically-allocated sequence with hardcoded gate structure, where only rotation angle fields are mutable. Built once on first call, cached for reuse.

**When to use:** For operations where gate structure is fixed but some parameter values change per call.

**Example for CQ_add template initialization:**
```c
// CQ_add for width N: QFT(N) + P(rotation) * N + IQFT(N)
// Total layers: 5*N - 2
// Rotation angles at layers [2*N-1 .. 3*N-2], one P gate per layer

static sequence_t *cached_CQ_add_N = NULL;

sequence_t *get_hardcoded_CQ_add_N(void) {
    if (cached_CQ_add_N != NULL)
        return cached_CQ_add_N;

    int bits = N;
    int total_layers = 5 * bits - 2;

    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->num_layer = total_layers;
    seq->used_layer = total_layers;
    seq->gates_per_layer = calloc(total_layers, sizeof(num_t));
    seq->seq = calloc(total_layers, sizeof(gate_t *));
    for (int i = 0; i < total_layers; i++) {
        seq->seq[i] = calloc(/* max gates in layer */, sizeof(gate_t));
    }

    // QFT gates (hardcoded positions and angles)
    // Layer 0: H on qubit N-1
    seq->seq[0][0] = (gate_t){.Gate = H, .Target = N-1, ...};
    seq->gates_per_layer[0] = 1;
    // ... all QFT/IQFT gates with known positions ...

    // Rotation layers: structure set, angles = 0 (placeholder)
    for (int i = 0; i < bits; i++) {
        int layer = 2 * bits - 1 + i;
        seq->seq[layer][0] = (gate_t){.Gate = P, .Target = i, .GateValue = 0, ...};
        seq->gates_per_layer[layer] = 1;
    }

    // IQFT gates (hardcoded)
    // ...

    cached_CQ_add_N = seq;
    return seq;
}
```

**The caller (CQ_add in IntegerAddition.c) then injects rotation angles:**
```c
sequence_t *CQ_add(int bits, int64_t value) {
    // compute rotations[]...
    int start_layer = 2 * bits - 1;

    if (bits <= HARDCODED_MAX_WIDTH) {
        sequence_t *seq = get_hardcoded_CQ_add_dispatch(bits);
        if (seq != NULL) {
            for (int i = 0; i < bits; i++) {
                seq->seq[start_layer + i][seq->gates_per_layer[start_layer + i] - 1].GateValue = rotations[i];
            }
            return seq;
        }
    }
    // ... dynamic fallback ...
}
```

### Pattern 3: Preprocessor Guard Pattern

**What:** Each per-width file is wrapped in `#ifdef SEQ_WIDTH_N` / `#endif`, enabled by default via `sequences.h`.

**When to use:** For enabling partial builds during development or testing.

**Example in `sequences.h`:**
```c
// Enable all widths by default. Disable individual widths by
// defining SEQ_NO_WIDTH_N before including this header.
#ifndef SEQ_NO_WIDTH_1
#define SEQ_WIDTH_1
#endif
#ifndef SEQ_NO_WIDTH_2
#define SEQ_WIDTH_2
#endif
// ... through 16 ...

#define HARDCODED_MAX_WIDTH 16
```

### Pattern 4: Unified Dispatch Function

**What:** Single dispatch function using switch/if-else chain across all 16 widths, with preprocessor guards for unavailable widths.

**Example:**
```c
const sequence_t *get_hardcoded_QQ_add(int bits) {
    switch (bits) {
#ifdef SEQ_WIDTH_1
        case 1: return get_hardcoded_QQ_add_1();
#endif
#ifdef SEQ_WIDTH_2
        case 2: return get_hardcoded_QQ_add_2();
#endif
        // ... through 16 ...
        default: return NULL;
    }
}
```

### Anti-Patterns to Avoid
- **Static const for CQ_add/cCQ_add sequences:** These need mutable angle fields; use template-init pattern instead
- **Unified dispatch in one of the per-width files:** Place dispatch in a dedicated file or in sequences.h to avoid coupling
- **Manual editing of generated files:** All `add_seq_N.c` files should be generated by the script; mark with "DO NOT EDIT MANUALLY" header
- **Testing large widths with out-of-place QQ_add:** Width 11+ out-of-place requires 33+ qubits, exceeding simulation limits

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate sequence generation | Manual transcription | Python generation script | 45,000+ lines of C; manual editing is error-prone |
| QFT/IQFT gate structure | Re-derive from theory | Copy from existing `generate_seq_5_8.py` functions | Already verified and tested in Phase 58 |
| cQQ_add 3-block structure | Re-derive from IntegerAddition.c | Copy from existing `generate_cqq_add()` function | Complex block structure; already correctly implemented after quick-015 fix |
| Rotation angle formatting | Float literals | `format_angle()` function using SEQ_PI expressions | Ensures exact M_PI fractions, no precision loss |
| Layer optimization | Flatten all layers | `optimize_layers()` function from existing scripts | Correctly merges non-overlapping gates while preserving parallelism |

**Key insight:** The existing `generate_seq_1_4.py` and `generate_seq_5_8.py` scripts contain 100% of the logic needed to generate all widths 1-16. The unified script should refactor and extend these, not rewrite from scratch.

## Common Pitfalls

### Pitfall 1: CQ_add/cCQ_add Cannot Be Static Const

**What goes wrong:** Attempting to make CQ_add/cCQ_add sequences static const like QQ_add/cQQ_add
**Why it happens:** CQ_add takes a `value` parameter; rotation angles change per call; `seq->seq[layer][gate].GateValue` must be mutable
**How to avoid:** Use template-initialization pattern: allocate once, cache, update angles on each call
**Warning signs:** Compile errors about assigning to const, or wrong results because angles aren't updated

### Pitfall 2: File Restructuring Breaks Dispatch

**What goes wrong:** Removing `add_seq_1_4.c` and `add_seq_5_8.c` before per-width files are ready; dispatch functions reference deleted symbols
**Why it happens:** The unified dispatch functions (`get_hardcoded_QQ_add`, `get_hardcoded_cQQ_add`) are currently in `add_seq_5_8.c`
**How to avoid:** Create all 16 per-width files and new dispatch file first, then remove old files, then update build system atomically
**Warning signs:** Linker errors for undefined symbols `get_hardcoded_QQ_add_1_4`, `get_hardcoded_QQ_add_5_8`

### Pitfall 3: Testing Simulation Limits

**What goes wrong:** Tests for widths 11+ using out-of-place QQ_add (`a + b` creates result register) hit memory limits
**Why it happens:** Out-of-place QQ_add uses 3*N qubits; width 11 = 33 qubits = 2^33 states = 8 GB statevector
**How to avoid:** For widths 11-16, test CQ_add (in-place, N qubits) or use in-place `__iadd__` (2*N qubits, feasible up to width 15). For width 16 QQ, test only gate count/structure, not simulation.
**Warning signs:** Tests hang or OOM-kill; Qiskit AerSimulator throws memory errors

### Pitfall 4: Build System Multiple Compilation

**What goes wrong:** Adding 16 source files to `c_sources` in setup.py; each Cython extension re-compiles them
**Why it happens:** `setup.py` lists c_sources per extension; 6 extensions * 16 files = 96 compilation units
**How to avoid:** Setuptools/Cython caches `.o` files between extensions. Each C file is compiled only once. The ~10 seconds extra build time is acceptable. No workaround needed.
**Warning signs:** Build times increase from ~30s to ~45s (acceptable)

### Pitfall 5: cQQ_add Algorithm Bugs (Lesson from Quick-015)

**What goes wrong:** Block 2 of cQQ_add uses wrong control qubit for negative CP gates
**Why it happens:** CCP(theta) decomposition has specific requirements for which qubit controls the negative half-rotation
**How to avoid:** The generation script already has the fix from quick-015: `Gate("P", target_q, bits + bit, -value)` (b-register qubit as control, not external control). Ensure the unified script preserves this.
**Warning signs:** Controlled addition produces wrong results; arithmetic tests fail for cQQ_add

### Pitfall 6: Dispatch Function Location

**What goes wrong:** Unified dispatch functions have circular dependencies or missing symbols
**Why it happens:** Currently dispatch lives in `add_seq_5_8.c` which calls `get_hardcoded_QQ_add_1_4()` from `add_seq_1_4.c`. With 16 files, a dedicated dispatch file is cleaner.
**How to avoid:** Create a dedicated `add_seq_dispatch.c` (or place dispatch in `sequences.c`) that includes forward declarations for all 16 per-width helpers
**Warning signs:** Linker errors, multiply-defined symbols

## Code Examples

### Gate/Layer Counts for Widths 9-16

```
=== QQ_add ===
Width | Layers | Total Gates
   9  |   43   |    135
  10  |   48   |    165
  11  |   53   |    198
  12  |   58   |    234
  13  |   63   |    273
  14  |   68   |    315
  15  |   73   |    360
  16  |   78   |    408

=== cQQ_add ===
Width | Layers | Total Gates
   9  |  209   |    207
  10  |  253   |    250
  11  |  301   |    297
  12  |  349   |    348
  13  |  405   |    403
  14  |  465   |    462
  15  |  529   |    525
  16  |  593   |    592

=== CQ_add / cCQ_add ===
Width | Layers (both)
   9  |   43
  10  |   48
  11  |   53
  12  |   58
  13  |   63
  14  |   68
  15  |   73
  16  |   78
```

### Estimated Lines of Generated C Code

```
Width  9: ~3,008 lines (QQ+cQQ only)
Width 10: ~3,641 lines
Width 11: ~4,334 lines
Width 12: ~5,083 lines
Width 13: ~5,896 lines
Width 14: ~6,769 lines
Width 15: ~7,702 lines
Width 16: ~8,691 lines
Total widths 9-16 (QQ+cQQ): ~45,124 lines
Total widths 1-16 (QQ+cQQ): ~53,640 lines
With CQ/cCQ template-init: add ~200 lines per width = +3,200 lines
Grand total estimate: ~57,000 lines of generated C
```

### Unified Generation Script Structure

```python
#!/usr/bin/env python3
"""Generate add_seq_N.c files for all hardcoded sequence widths.

Single source of truth for all hardcoded addition sequences.
Generates one C file per bit width containing:
- QQ_add: Static const gate arrays
- cQQ_add: Static const gate arrays
- CQ_add: Template-init function (parametric)
- cCQ_add: Template-init function (parametric)

Usage:
    python scripts/generate_seq_all.py              # Generate all 16 files
    python scripts/generate_seq_all.py --width 9    # Generate single width
    python scripts/generate_seq_all.py --dry-run    # Print without writing
"""

# Core gate generation functions (from existing scripts):
# - generate_qq_add(bits) -> list[list[Gate]]
# - generate_cqq_add(bits) -> list[list[Gate]]
# - generate_cq_add_template(bits) -> list[list[Gate]]
# - generate_ccq_add_template(bits) -> list[list[Gate]]
# - optimize_layers(layers) -> list[list[Gate]]
# - generate_c_sequence(name, layers, width) -> str

# Also generates:
# - CQ_add template-init function
# - cCQ_add template-init function
# - Per-width dispatch helpers
# - Preprocessor guard wrappers
```

### CQ_add Template Generation (Python)

```python
def generate_cq_add_template(bits: int) -> list[list[Gate]]:
    """Generate CQ_add gate structure (angles are placeholders).

    Structure: QFT(bits) + P(0) * bits + IQFT(bits)
    Rotation angles are 0 (placeholder) - injected at runtime.
    """
    layers = []

    # QFT on target register [0, bits-1] (same as QQ_add)
    for target in range(bits - 1, -1, -1):
        layers.append([Gate("H", target, None, 0)])
        for ctrl in range(target - 1, -1, -1):
            angle = math.pi / (2 ** (target - ctrl))
            layers.append([Gate("P", target, ctrl, angle)])

    # Rotation gates (placeholder angles = 0)
    for i in range(bits):
        layers.append([Gate("P", i, None, 0)])  # Single-qubit P, angle TBD

    # Inverse QFT
    for target in range(bits):
        for ctrl in range(target):
            angle = -math.pi / (2 ** (target - ctrl))
            layers.append([Gate("P", target, ctrl, angle)])
        layers.append([Gate("H", target, None, 0)])

    return layers
```

### CQ_add Template Init Function (Generated C)

```c
// Generated by scripts/generate_seq_all.py - DO NOT EDIT MANUALLY

static sequence_t *cached_CQ_add_9 = NULL;

sequence_t *init_hardcoded_CQ_add_9(void) {
    if (cached_CQ_add_9 != NULL)
        return cached_CQ_add_9;

    int total_layers = 43; // 5*9 - 2
    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->num_layer = total_layers;
    seq->used_layer = total_layers;
    seq->gates_per_layer = calloc(total_layers, sizeof(num_t));
    seq->seq = calloc(total_layers, sizeof(gate_t *));

    // Allocate each layer
    for (int i = 0; i < total_layers; i++) {
        seq->seq[i] = calloc(2, sizeof(gate_t)); // max 2 gates per layer
    }

    // Layer 0: H(8)
    seq->seq[0][0] = (gate_t){.Gate = H, .Target = 8, .NumControls = 0,
                               .Control = {0}, .large_control = NULL,
                               .GateValue = 0, .NumBasisGates = 0};
    seq->gates_per_layer[0] = 1;

    // ... all gates with exact positions and fixed angles ...

    // Rotation layers 17-25: P(i) with placeholder angle 0
    seq->seq[17][0] = (gate_t){.Gate = P, .Target = 0, .NumControls = 0,
                                .Control = {0}, .large_control = NULL,
                                .GateValue = 0, .NumBasisGates = 0};
    seq->gates_per_layer[17] = 1;
    // ... etc ...

    cached_CQ_add_9 = seq;
    return seq;
}
```

### Dispatch File Structure

```c
// add_seq_dispatch.c - Unified dispatch for all hardcoded widths
#include "sequences.h"

// Forward declarations for per-width helpers
#ifdef SEQ_WIDTH_1
extern const sequence_t *get_hardcoded_QQ_add_1(void);
extern const sequence_t *get_hardcoded_cQQ_add_1(void);
extern sequence_t *get_hardcoded_CQ_add_1(void);
extern sequence_t *get_hardcoded_cCQ_add_1(void);
#endif
// ... through 16 ...

const sequence_t *get_hardcoded_QQ_add(int bits) {
    switch (bits) {
#ifdef SEQ_WIDTH_1
    case 1: return get_hardcoded_QQ_add_1();
#endif
#ifdef SEQ_WIDTH_2
    case 2: return get_hardcoded_QQ_add_2();
#endif
    // ... through 16 ...
    default: return NULL;
    }
}

// Similarly for cQQ_add, CQ_add, cCQ_add dispatch
```

### Testing Strategy for Large Widths

```python
# For widths 9-10: Full QQ_add + CQ_add verification
# For widths 11-15: In-place iadd (2*N qubits) or CQ_add only
# For width 16: CQ_add (16 qubits) + structural verification

@pytest.mark.parametrize("width", [9, 10])
def test_qq_add_small_widths(verify_circuit, width):
    """QQ_add feasible for simulation (27-30 qubits)."""
    ...

@pytest.mark.parametrize("width", [11, 12, 13, 14, 15])
def test_cq_add_medium_widths(verify_circuit, width):
    """CQ_add feasible for all widths (N qubits only)."""
    ...

@pytest.mark.parametrize("width", range(9, 17))
def test_cq_add_all_widths(verify_circuit, width):
    """CQ_add (in-place, N qubits) for all new widths."""
    ...
```

### Qubit Simulation Limits

```
Width  9: QQ out-of-place = 27 qubits (OK, ~134M states)
Width 10: QQ out-of-place = 30 qubits (borderline, ~1B states)
Width 11: QQ out-of-place = 33 qubits (TOO LARGE, ~8B states)
Width 16: QQ out-of-place = 48 qubits (WAY TOO LARGE)

Width  9-16: CQ in-place = 9-16 qubits (ALL OK)
Width  9-15: QQ in-place = 18-30 qubits (ALL OK except 15 borderline)
Width 16: QQ in-place = 32 qubits (borderline/too large)
```

## State of the Art

| Old Approach (Phase 58) | New Approach (Phase 59) | Impact |
|------------------------|------------------------|--------|
| 2 multi-width files (1-4, 5-8) | 16 per-width files | Better maintainability, partial builds |
| Only QQ_add + cQQ_add hardcoded | All 4 variants hardcoded | Complete coverage |
| Two separate generation scripts | Unified generation script | Single source of truth |
| `HARDCODED_MAX_WIDTH = 8` | `HARDCODED_MAX_WIDTH = 16` | Covers 16-bit default width |
| ~7,855 lines of static C | ~57,000 lines of generated C | 7x increase from scale |
| Manual for 1-4, script for 5-8 | Script for all 1-16 | Full reproducibility |

**Key Phase 58 decisions still valid:**
- SEQ-01: `SEQ_PI` compile-time constant (still needed)
- SEQ-03: `const gate_t` arrays with designated initializers (still the pattern for QQ/cQQ)
- SEQ-04: Python code generation (now the standard for all widths)
- SEQ-05: Const cast in IntegerAddition.c (extends to all 16 widths for QQ/cQQ)

## Open Questions

### 1. CQ_add/cCQ_add Integration Point

**What we know:** CQ_add currently builds sequence dynamically then caches. The hardcoded approach would pre-build the structure on first call, matching the existing cache pattern exactly. The modification needed in `CQ_add()` is minimal -- just call `init_hardcoded_CQ_add_N()` instead of the dynamic allocation + QFT() + QFT_inverse() path.

**What's unclear:** Whether to modify `CQ_add()` and `cCQ_add()` in `IntegerAddition.c` to call per-width init functions (like QQ_add does with `get_hardcoded_QQ_add`), or whether the existing caching pattern is sufficient and the "hardcoded" benefit is minimal for parametric operations.

**Recommendation:** Implement the template-init approach. While the runtime benefit is modest (eliminates QFT/IQFT loop overhead on first call only), it provides consistency with the QQ/cQQ hardcoded approach and the user explicitly requested all four variants. The template-init function is trivially generated by the same script.

### 2. Dispatch Architecture

**What we know:** With 16 widths and 4 operation types (QQ, cQQ, CQ, cCQ), there are 64 dispatch entries. The current 2-level dispatch (unified -> per-range) works but doesn't scale well to 16 widths.

**What's unclear:** Best approach for the unified dispatch file. Options:
- (A) Dedicated `add_seq_dispatch.c` with all dispatch functions
- (B) Dispatch logic in `sequences.h` as inline functions
- (C) Dispatch logic generated by the Python script into a separate file

**Recommendation:** Option (A) -- dedicated `add_seq_dispatch.c` generated by the script. Keeps dispatch logic separate from per-width data, avoids header bloat, and the script generates it consistently.

### 3. IntegerAddition.c Modification Scope for CQ/cCQ

**What we know:** Currently only `QQ_add()` and `cQQ_add()` route to hardcoded. Adding `CQ_add()` and `cCQ_add()` routing requires modifying those functions to check hardcoded first.

**What's unclear:** The CQ_add cached path already works well (allocate once, update angles). The "hardcoded" benefit is only eliminating the first-call allocation overhead. Whether this is worth the code complexity.

**Recommendation:** Keep it simple. For CQ_add/cCQ_add, the template-init function replaces the dynamic allocation + QFT() + QFT_inverse() path on first call. On subsequent calls, behavior is identical to current cache path. The modification in `CQ_add()` is: check if `bits <= HARDCODED_MAX_WIDTH`, if so call `init_hardcoded_CQ_add_dispatch(bits)` to get the cached sequence, then inject angles as before.

## Sources

### Primary (HIGH confidence)
- `c_backend/src/IntegerAddition.c` -- Dynamic QQ_add, cQQ_add, CQ_add, cCQ_add implementations (current codebase)
- `c_backend/include/types.h` -- gate_t, sequence_t struct definitions (lines 66-82)
- `c_backend/include/sequences.h` -- Current dispatch architecture (53 lines)
- `c_backend/src/sequences/add_seq_1_4.c` -- Existing 1-4 bit sequences (1508 lines)
- `c_backend/src/sequences/add_seq_5_8.c` -- Existing 5-8 bit sequences (6351 lines)
- `scripts/generate_seq_1_4.py` -- Existing generation script with verified gate algorithms (354 lines)
- `scripts/generate_seq_5_8.py` -- Existing generation script with verified gate algorithms (376 lines)
- `.planning/phases/58-hardcoded-sequences-1-8/` -- All Phase 58 plans, summaries, and verification
- `.planning/quick/015-fix-cqq-add-algorithm-bugs/015-SUMMARY.md` -- Recent cQQ_add bug fix context

### Secondary (MEDIUM confidence)
- `c_backend/src/gate.c` (lines 304-443) -- QFT/QFT_inverse implementation details
- `src/quantum_language/qint_arithmetic.pxi` -- Python-side qubit layout for all addition operations
- `c_backend/include/arithmetic_ops.h` -- API documentation for CQ_add, cCQ_add
- `setup.py` -- Build configuration (c_sources list, extension compilation)
- `tests/test_hardcoded_sequences.py` -- Existing validation tests (221 lines)

### Tertiary (LOW confidence)
- Estimated C code line counts (calculated from gate count formulas, not measured from actual generation)
- Build time impact estimates (extrapolated from current build behavior)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All code uses existing project infrastructure established in Phase 58
- Architecture: HIGH -- Patterns derived from existing codebase and Phase 58 proven patterns
- Pitfalls: HIGH -- Based on actual Phase 58 experience, quick-014/015 bug fixes, and direct code analysis
- CQ/cCQ approach: MEDIUM -- Template-init pattern is sound but hasn't been implemented in this project yet

**Research date:** 2026-02-06
**Valid until:** 2026-03-08 (30 days -- stable domain, internal project code)
