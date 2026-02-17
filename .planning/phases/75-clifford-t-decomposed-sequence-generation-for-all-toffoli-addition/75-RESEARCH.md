# Phase 75: Clifford+T Decomposed Sequence Generation for All Toffoli Addition - Research

**Researched:** 2026-02-17
**Domain:** Hardcoded Clifford+T gate sequence generation for Toffoli addition circuits
**Confidence:** HIGH

## Summary

This phase extends the existing hardcoded Toffoli sequence infrastructure to generate pre-computed Clifford+T gate sequences for all addition variants (CDKM and BK CLA). Currently, when `toffoli_decompose=True`, the multiplication path dynamically decomposes CCX gates into Clifford+T at emission time (Phase 74-04), but the addition path uses pre-computed sequences containing CCX/MCX gates that are NOT decomposed. This phase closes that gap by generating hardcoded sequences where every CCX is already expanded into the 15-gate Clifford+T decomposition (H, CX, T, Tdg).

The codebase already has all necessary infrastructure: (1) the `emit_ccx_clifford_t_seq` function in `gate.c` that emits 15 Clifford+T gates per CCX into sequential layers; (2) two generation scripts (`generate_toffoli_seq.py` for QQ/cQQ CDKM, `generate_toffoli_decomp_seq.py` for MCX-decomposed cQQ); (3) the header/dispatch/build patterns in `toffoli_sequences.h`, dispatch files, and `setup.py`. The core work is: (a) implementing a Python-side CCX->Clifford+T expansion in the generation scripts, (b) producing new per-width C files for all 8 variant families (CDKM QQ/cQQ/CQ-inc/cCQ-inc + BK CLA QQ/cQQ/CQ-inc/cCQ-inc), (c) wiring dispatch functions and updating the header, (d) modifying the runtime to use these when `toffoli_decompose=True`.

**Primary recommendation:** Implement a shared `CliffordTGate` dataclass with `to_c_static()` support for H/T/Tdg/CX gates alongside the existing `ToffoliGate`. Build a `ccx_to_clifford_t(target, ctrl1, ctrl2)` expansion function that returns 15 `CliffordTGate` objects. Use this in all existing generation paths with a `--clifford-t` flag. Each CCX in the source sequence becomes 15 Clifford+T gates; each CX and X gate passes through unchanged.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All 4 CDKM variants: QQ, CQ, cQQ, cCQ
- All 4 BK CLA variants: QQ, CQ, cQQ, cCQ
- CQ/cCQ increment-only (value=1) sequences also get Clifford+T variants
- Multiplication and comparison stay on dynamic inline decomposition for now (defer hardcoded mul/cmp sequences to a future phase if needed)
- Widths 1-8 for all variants (CDKM and BK CLA alike)
- Matches existing hardcoded Toffoli sequence range
- Separate lookup tables/dispatch functions for Clifford+T sequences (e.g., `toffoli_decomp_clifft_QQ_add`)
- Same caching pattern as existing Toffoli sequences (first call: hardcoded -> cache, subsequent: cache hit)
- Widths 1-8 with `toffoli_decompose=True`: always use hardcoded Clifford+T sequence (no fallback to dynamic)
- Widths 9+: dynamic generators produce Clifford+T gates directly (skip CCX intermediate step)
- Extend existing generation scripts with Clifford+T mode (e.g., `--clifford-t` flag)
- One C file per width per variant (e.g., `toffoli_clifft_qq_1.c`, `toffoli_clifft_cla_qq_1.c`)
- BK CLA: script implements BK prefix tree logic in Python and emits Clifford+T gates directly (manual construction, not simulation-based)
- Correctness verified via pytest tests only (not in generation script)

### Claude's Discretion
- Exact naming conventions for generated files and dispatch functions
- Internal organization of generation script extensions
- Whether to share CCX->Clifford+T expansion logic between scripts or duplicate
- CLA width-1 handling (falls back to RCA, so Clifford+T sequence may mirror CDKM)

### Deferred Ideas (OUT OF SCOPE)
- Hardcoded Clifford+T sequences for multiplication -- future phase if performance warrants it
- Hardcoded Clifford+T sequences for comparison (AND/OR/equal) -- future phase
- Extending hardcoded width range beyond 8 -- future phase
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INF-03 | Hardcoded Toffoli gate sequences for common widths eliminate generation overhead | Clifford+T hardcoded sequences extend coverage to decomposed mode, eliminating dynamic CCX->Clifford+T expansion overhead for widths 1-8 |
| INF-04 | T-count reporting in circuit statistics | With fully Clifford+T sequences, T-count is exact (actual T/Tdg gates in output), not estimated. Each CCX in source = 4T + 3Tdg = 7 T/Tdg gates |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3 | 3.13+ | Generation scripts | Already used for all generation scripts |
| C23 | gcc/clang | Generated C files | Project standard (Makefile: `-std=c23`) |
| Cython | existing | Build bridge | Already wired in setup.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | existing | Correctness verification | Test generated sequences via Qiskit simulation |
| qiskit-aer | existing | Simulation backend | Verify Clifford+T sequences produce correct arithmetic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python-side CCX expansion | C-side runtime expansion via emit_ccx_clifford_t_seq | Python-side is simpler for code generation; runtime would duplicate the existing dynamic path |
| Separate generation script | Single unified script | Separate scripts match existing pattern (generate_toffoli_seq.py, generate_toffoli_decomp_seq.py) but unified avoids duplication |

**Installation:** No new dependencies needed.

## Architecture Patterns

### Recommended Project Structure
```
scripts/
  generate_toffoli_seq.py           # Extended: --clifford-t flag for CDKM QQ/cQQ
  generate_toffoli_decomp_seq.py    # Extended: --clifford-t flag for MCX-decomposed cQQ
  generate_toffoli_cq_clifft.py     # NEW: CQ/cCQ increment Clifford+T sequences
  generate_toffoli_cla_clifft.py    # NEW: BK CLA Clifford+T sequences (all 4 variants)
c_backend/src/sequences/
  toffoli_clifft_qq_1.c .. _8.c         # CDKM QQ Clifford+T (8 files)
  toffoli_clifft_cqq_1.c .. _8.c        # CDKM cQQ Clifford+T (8 files)
  toffoli_clifft_cq_inc_1.c .. _8.c     # CDKM CQ inc Clifford+T (8 files)
  toffoli_clifft_ccq_inc_1.c .. _8.c    # CDKM cCQ inc Clifford+T (8 files)
  toffoli_clifft_cla_qq_1.c .. _8.c     # BK CLA QQ Clifford+T (8 files)
  toffoli_clifft_cla_cqq_1.c .. _8.c    # BK CLA cQQ Clifford+T (8 files)
  toffoli_clifft_cla_cq_inc_1.c .. _8.c # BK CLA CQ inc Clifford+T (8 files)
  toffoli_clifft_cla_ccq_inc_1.c .. _8.c # BK CLA cCQ inc Clifford+T (8 files)
  toffoli_clifft_dispatch.c              # Unified dispatch for all Clifford+T variants
c_backend/include/
  toffoli_sequences.h               # Updated: new dispatch function declarations
```

### Pattern 1: CCX -> Clifford+T Gate Expansion in Python
**What:** A Python function `ccx_to_clifford_t(target, ctrl1, ctrl2)` that returns a list of 15 gate objects, matching the exact decomposition in `gate.c:emit_ccx_clifford_t`.
**When to use:** Every time the generation script encounters a CCX gate in the source sequence.
**Example:**
```python
# Verified from c_backend/src/gate.c lines 546-623
# The exact 15-gate CCX -> Clifford+T decomposition:
def ccx_to_clifford_t(target, ctrl1, ctrl2):
    """Expand CCX(target, ctrl1, ctrl2) into 15 Clifford+T gates.

    Sequence (from gate.c emit_ccx_clifford_t):
      1.  H(target)
      2.  CX(target, ctrl2)
      3.  Tdg(target)
      4.  CX(target, ctrl1)
      5.  T(target)
      6.  CX(target, ctrl2)
      7.  Tdg(target)
      8.  CX(target, ctrl1)
      9.  T(target)
      10. T(ctrl2)
      11. H(target)
      12. CX(ctrl2, ctrl1)
      13. T(ctrl1)
      14. Tdg(ctrl2)
      15. CX(ctrl2, ctrl1)
    """
    return [
        CliffordTGate("H", target),
        CliffordTGate("CX", target, ctrl2),
        CliffordTGate("Tdg", target),
        CliffordTGate("CX", target, ctrl1),
        CliffordTGate("T", target),
        CliffordTGate("CX", target, ctrl2),
        CliffordTGate("Tdg", target),
        CliffordTGate("CX", target, ctrl1),
        CliffordTGate("T", target),
        CliffordTGate("T", ctrl2),
        CliffordTGate("H", target),
        CliffordTGate("CX", ctrl2, ctrl1),
        CliffordTGate("T", ctrl1),
        CliffordTGate("Tdg", ctrl2),
        CliffordTGate("CX", ctrl2, ctrl1),
    ]
```

### Pattern 2: CliffordTGate Dataclass for Static C Emission
**What:** A new gate dataclass that supports H, T, Tdg, CX, X gates (all max 1 control) for static const C emission.
**When to use:** All Clifford+T hardcoded sequences.
**Example:**
```python
@dataclass
class CliffordTGate:
    """Gate in Clifford+T basis: H, T, Tdg, X (0 controls), CX (1 control)."""
    gate_type: str   # "H", "T", "Tdg", "X", "CX"
    target: int
    control: int = -1  # Only for CX

    def to_c_static(self) -> str:
        """Generate C static const initializer."""
        gate_enum = {
            "H": "H",
            "T": "T_GATE",
            "Tdg": "TDG_GATE",
            "X": "X",
            "CX": "X",  # CX is X with 1 control
        }[self.gate_type]

        gate_value = {
            "H": "0",
            "T": "M_PI / 4.0",
            "Tdg": "-M_PI / 4.0",
            "X": "1",
            "CX": "1",
        }[self.gate_type]

        num_controls = 1 if self.gate_type == "CX" else 0
        ctrl_init = f"{{{self.control}}}" if num_controls == 1 else "{0}"

        return (
            f"{{.Gate = {gate_enum},\n"
            f"                                      .Target = {self.target},\n"
            f"                                      .NumControls = {num_controls},\n"
            f"                                      .Control = {ctrl_init},\n"
            f"                                      .large_control = NULL,\n"
            f"                                      .GateValue = {gate_value},\n"
            f"                                      .NumBasisGates = 0}}"
        )
```

### Pattern 3: Gate-Count Multiplication for Layer Calculation
**What:** Computing the total number of layers when expanding CCX->Clifford+T.
**When to use:** Allocating the correct number of layers in generated sequences.
**Key formulas:**
```
CDKM QQ (width N, N>=2):
  Source: 6*N layers (N MAJ + N UMA, 3 gates each)
  Gate types: N*2 CX + N*2 CCX (in MAJ) + N*2 CCX + N*2 CX (in UMA) = 4N CX + 4N CCX
  Clifford+T layers: 4N * 1 (CX pass-through) + 4N * 15 (CCX expansion) = 4N + 60N = 64N
  Width 1: 1 CX -> 1 layer

CDKM cQQ decomposed (width N, N>=2):
  Source: 10*N layers (N decomposed cMAJ + N decomposed cUMA, 5 gates each)
  Gate types: all CCX (max 2 controls)
  Clifford+T layers: 10N * 15 = 150N
  Width 1: 1 CCX -> 15 layers

BK CLA QQ (width N):
  Source: 7N - 4 + 4*num_merges layers
  Contains: CX and CCX gates
  Clifford+T: each CCX -> 15 layers, each CX -> 1 layer
  Must count CCX vs CX per sequence to compute total
```

### Pattern 4: All-Static-Const Generation
**What:** Because Clifford+T sequences contain only H/T/Tdg/CX/X (max 1 control), ALL variants can be fully static const -- no dynamic allocation needed, even for cQQ.
**When to use:** All 8 variant families. This is a significant simplification over the original cQQ pattern which required dynamic allocation for MCX(3) gates.
**Impact:** Simpler generated code, faster dispatch, zero memory allocation at runtime.

### Pattern 5: Dispatch via toffoli_decompose Flag Check
**What:** Runtime dispatch selects Clifford+T hardcoded sequence when `circ->toffoli_decompose == 1` and width <= 8.
**When to use:** In `toffoli_QQ_add()`, `toffoli_cQQ_add()`, `toffoli_CQ_add()`, `toffoli_cCQ_add()` (CDKM) and `toffoli_QQ_add_bk()`, `toffoli_cQQ_add_bk()`, `toffoli_CQ_add_bk()`, `toffoli_cCQ_add_bk()` (BK CLA).
**Key issue:** The current sequence generators don't have access to `circ->toffoli_decompose`. The functions `toffoli_QQ_add(bits)` and similar return cached sequences and don't take a circuit parameter. The dispatch must either:
  - (a) Add separate entry points: `toffoli_QQ_add_clifft(bits)` that returns Clifford+T sequences, OR
  - (b) Have the caller (hot_path_add_toffoli.c) check the flag and call the Clifford+T dispatch directly.

**Recommendation:** Option (b) -- modify `hot_path_add_toffoli.c` to check `circ->toffoli_decompose` and call separate Clifford+T dispatch functions. This follows the same pattern as how MCX-decomposed cQQ dispatch already works separately from the original cQQ dispatch.

### Anti-Patterns to Avoid
- **Runtime CCX expansion at execution time:** Do not modify `run_instruction()` to decompose CCX gates on the fly. The whole point is pre-computed sequences.
- **Mixing Clifford+T gates with CCX/MCX in one sequence:** Each sequence should be purely Clifford+T (H/T/Tdg/CX/X) or purely Toffoli (X/CX/CCX/MCX). No mixing.
- **Generating BK CLA Clifford+T via simulation:** The user specifically said "manual construction, not simulation-based". Implement the BK prefix tree logic in Python, then expand each gate to Clifford+T.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CCX decomposition | Custom 15-gate sequence | Exact copy of `gate.c:emit_ccx_clifford_t` | Must match runtime decomposition exactly for correctness |
| BK merge computation | New Python BK tree | Port `bk_compute_merges()` from `ToffoliAdditionCLA.c` | Merge order must match C implementation exactly |
| Gate encoding | New gate_t format | Existing `gate_t` struct fields (Gate, Target, NumControls, Control, GateValue) | Compatibility with existing execution engine |
| Static const C generation | Manual string formatting | Adapt existing `to_c_static()` pattern from ToffoliGate | Consistent formatting, proven correct |

**Key insight:** The Clifford+T decomposition is a mechanical transformation of existing sequences. The algorithm logic (CDKM, BK CLA) is unchanged -- only the gate-level representation changes. Reuse all existing algorithmic logic.

## Common Pitfalls

### Pitfall 1: GateValue Mismatch for T/Tdg Gates
**What goes wrong:** Generated T/Tdg gates use wrong GateValue (e.g., `1` instead of `M_PI/4.0`).
**Why it happens:** The existing `ToffoliGate.to_c_static()` always uses `.GateValue = 1` because all Toffoli gates are X-type. T and Tdg need floating-point GateValue.
**How to avoid:** Use `M_PI / 4.0` for T_GATE and `-M_PI / 4.0` for TDG_GATE in `to_c_static()`. Include `<math.h>` in generated files.
**Warning signs:** Tests pass with `.measure()` (which returns initial values) but fail with Qiskit simulation.

### Pitfall 2: Gate Enum Name Mismatch
**What goes wrong:** Generated C uses `T` or `Tdg` instead of `T_GATE` / `TDG_GATE`.
**Why it happens:** Python gate_type strings don't match C enum names.
**How to avoid:** Explicit mapping: `"T" -> "T_GATE"`, `"Tdg" -> "TDG_GATE"`, `"H" -> "H"`, `"X" -> "X"`. Verified from `types.h` line 64: `typedef enum { X, Y, Z, R, H, Rx, Ry, Rz, P, M, T_GATE, TDG_GATE } Standardgate_t;`
**Warning signs:** Compilation errors in generated .c files.

### Pitfall 3: H Gate GateValue
**What goes wrong:** H gate initialized with `.GateValue = 1` but H gate uses `.GateValue = 0`.
**Why it happens:** Copying from X gate pattern.
**How to avoid:** Verify from `gate.c` line 184-189: `void h(gate_t *g, qubit_t target) { g->Gate = H; g->Target = target; g->NumControls = 0; g->GateValue = 0; }`. H gates have GateValue = 0.
**Warning signs:** Wrong gate values in QASM output.

### Pitfall 4: Missing `#include <math.h>` for M_PI
**What goes wrong:** `M_PI` undefined in generated C files.
**Why it happens:** Existing Toffoli sequence files don't need `<math.h>` because they only use integer GateValue.
**How to avoid:** Add `#include <math.h>` to all Clifford+T generated files that use T/Tdg gates.
**Warning signs:** Compilation errors.

### Pitfall 5: Layer Count Miscalculation for BK CLA
**What goes wrong:** Allocated sequence has wrong number of layers, causing buffer overflow or unused layers.
**Why it happens:** BK CLA layer count depends on `num_merges` which varies with width and is not a simple formula.
**How to avoid:** Count the exact number of CCX and CX gates in the source BK CLA sequence, then compute: `total_clifft_layers = num_CX * 1 + num_CCX * 15 + num_X * 1`.
**Warning signs:** Layer mismatch assertions (existing pattern: `#ifdef DEBUG` layer count checks).

### Pitfall 6: CQ/cCQ Sequences Are Value-Dependent
**What goes wrong:** Attempting to hardcode CQ_add for arbitrary values, generating exponentially many sequences.
**Why it happens:** CQ_add takes a classical value parameter; the gate sequence depends on which bits are 0 or 1.
**How to avoid:** Only hardcode increment (value=1) sequences. General CQ_add uses the dynamic generator. This is the locked decision: "CQ/cCQ increment-only (value=1) sequences also get Clifford+T variants."
**Warning signs:** Attempting to generate value-parameterized hardcoded sequences.

### Pitfall 7: Sequence Inversion for Subtraction
**What goes wrong:** Clifford+T sequences don't properly support subtraction (invert=1 in run_instruction).
**Why it happens:** T and Tdg gates need GateValue negation when inverted. The existing `run_instruction` already handles this (line 50-62: non-self-inverse gates get negated GateValue).
**How to avoid:** Verify that T_GATE and TDG_GATE are NOT in the self-inverse list. From execution.c: X, Y, Z, H, M are self-inverse; default (including T, Tdg, P, R) gets negated. This means T becomes Tdg and Tdg becomes T when inverted, which is correct for sequence reversal.
**Warning signs:** Subtraction tests fail.

### Pitfall 8: Forgetting to Update setup.py
**What goes wrong:** New .c files exist but aren't compiled into the extension.
**Why it happens:** setup.py explicitly lists every C source file (no glob).
**How to avoid:** Add all new sequence files to the `c_sources` list in `setup.py`. Pattern: list comprehension `*[os.path.join(PROJECT_ROOT, "c_backend", "src", "sequences", f"toffoli_clifft_qq_{i}.c") for i in range(1, 9)]`.
**Warning signs:** Linker errors for undefined symbols.

### Pitfall 9: BK CLA Width-1 Fallback
**What goes wrong:** BK CLA functions return NULL for width 1 (bits < 2), so Clifford+T CLA sequences for width 1 don't exist.
**Why it happens:** BK CLA requires bits >= 2 (single-bit addition is just CX, no carry lookahead needed). Width 1 falls back to CDKM (RCA).
**How to avoid:** For CLA Clifford+T, only generate widths 2-8. Width 1 uses the CDKM Clifford+T sequence. Document this clearly.
**Warning signs:** NULL pointer returns for CLA width 1.

## Code Examples

### Verified: Exact 15-Gate CCX -> Clifford+T Decomposition
```c
// Source: c_backend/src/gate.c lines 546-623
// Gate sequence: H, CX, Tdg, CX, T, CX, Tdg, CX, T, T, H, CX, T, Tdg, CX
// Per-gate breakdown:
//   H(target)              -- Gate=H, Target=t, NumControls=0, GateValue=0
//   CX(target, ctrl2)      -- Gate=X, Target=t, NumControls=1, Control={ctrl2}, GateValue=1
//   Tdg(target)            -- Gate=TDG_GATE, Target=t, NumControls=0, GateValue=-pi/4
//   CX(target, ctrl1)      -- Gate=X, Target=t, NumControls=1, Control={ctrl1}, GateValue=1
//   T(target)              -- Gate=T_GATE, Target=t, NumControls=0, GateValue=pi/4
//   CX(target, ctrl2)      -- same as gate 2
//   Tdg(target)            -- same as gate 3
//   CX(target, ctrl1)      -- same as gate 4
//   T(target)              -- same as gate 5
//   T(ctrl2)               -- Gate=T_GATE, Target=ctrl2, NumControls=0, GateValue=pi/4
//   H(target)              -- same as gate 1
//   CX(ctrl2, ctrl1)       -- Gate=X, Target=ctrl2, NumControls=1, Control={ctrl1}, GateValue=1
//   T(ctrl1)               -- Gate=T_GATE, Target=ctrl1, NumControls=0, GateValue=pi/4
//   Tdg(ctrl2)             -- Gate=TDG_GATE, Target=ctrl2, NumControls=0, GateValue=-pi/4
//   CX(ctrl2, ctrl1)       -- same as gate 12
```

### Verified: CDKM QQ Width-1 Clifford+T (trivial)
```c
// Width 1: single CX(target=0, control=1) -- no CCX, no expansion needed
// Source: generate_toffoli_seq.py line 147
// Clifford+T: identical to Toffoli version (1 layer, 1 CX gate)
```

### Verified: CDKM QQ Width-2 Gate Count Expansion
```
// Source: generate_toffoli_seq.py validation, width 2: 12 layers (6*2)
// Gate type breakdown (from algorithm):
//   MAJ(4,2,0): CX(2,0), CX(4,0), CCX(0,4,2)         -- 2 CX + 1 CCX
//   MAJ(0,3,1): CX(3,1), CX(0,1), CCX(1,0,3)         -- 2 CX + 1 CCX
//   UMA(0,3,1): CCX(1,0,3), CX(0,1), CX(3,0)         -- 1 CCX + 2 CX
//   UMA(4,2,0): CCX(0,4,2), CX(4,0), CX(2,4)         -- 1 CCX + 2 CX
// Total: 8 CX + 4 CCX = 12 layers
// Clifford+T: 8 * 1 + 4 * 15 = 8 + 60 = 68 layers
```

### Verified: Static Const C Generation for Clifford+T Gates
```c
// H gate static const:
static const gate_t TOFFOLI_CLIFFT_QQ_2_L2[] = {{.Gate = H,
                                      .Target = 0,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

// T gate static const:
static const gate_t TOFFOLI_CLIFFT_QQ_2_L8[] = {{.Gate = T_GATE,
                                      .Target = 0,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = M_PI / 4.0,
                                      .NumBasisGates = 0}};

// CX gate static const (same as existing):
static const gate_t TOFFOLI_CLIFFT_QQ_2_L1[] = {{.Gate = X,
                                      .Target = 0,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = 1,
                                      .NumBasisGates = 0}};
```

### Verified: Dispatch Function Pattern
```c
// Source: toffoli_add_seq_dispatch.c pattern (existing)
// New Clifford+T dispatch follows same pattern:
const sequence_t *get_hardcoded_toffoli_clifft_QQ_add(int bits) {
    switch (bits) {
#ifdef TOFFOLI_SEQ_WIDTH_1
    case 1: return get_hardcoded_toffoli_clifft_QQ_add_1(bits);
#endif
#ifdef TOFFOLI_SEQ_WIDTH_2
    case 2: return get_hardcoded_toffoli_clifft_QQ_add_2(bits);
#endif
    // ... widths 3-8
    default: return NULL;
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dynamic CCX emission for all addition | Hardcoded Toffoli sequences (widths 1-8) | Phase 72 | Eliminates runtime generation for common widths |
| MCX(3) with dynamic allocation in cQQ | AND-ancilla decomposition -> static const CCX | Phase 74-05 | Zero malloc for cQQ hardcoded paths |
| CCX in output, estimate T-count as 7*CCX | Inline Clifford+T emission for multiplication | Phase 74-04 | Exact T-count for mul path, but addition still uses CCX sequences |
| **Status quo (addition path)** | **CCX sequences with toffoli_decompose flag ignored** | **Current** | **Addition uses pre-computed CCX sequences even when toffoli_decompose=True** |

**What this phase changes:**
- Addition path gets Clifford+T hardcoded sequences selected when `toffoli_decompose=True`
- T-count becomes exact for ALL Toffoli arithmetic (addition + multiplication), not just multiplication

## Sequence Size Estimates

### CDKM Variants

| Width | QQ Toffoli | QQ Clifford+T | cQQ Decomp Toffoli | cQQ Decomp Clifford+T |
|-------|-----------|---------------|--------------------|-----------------------|
| 1 | 1 CX | 1 CX | 1 CCX | 15 gates |
| 2 | 12 layers | 68 layers | 20 layers | 300 layers |
| 4 | 24 layers | 136 layers | 40 layers | 600 layers |
| 8 | 48 layers | 272 layers | 80 layers | 1200 layers |

**Formula (N >= 2):**
- QQ Clifford+T: `4N + 60N = 64N` layers (4N CX + 4N*15 CCX)
- cQQ Clifford+T: `150N` layers (10N CCX * 15 each, all gates are CCX)

### BK CLA Variants

| Width | QQ BK Toffoli layers | Approx QQ BK Clifford+T |
|-------|---------------------|--------------------------|
| 2 | 7*2-4+4*0 = 10 | ~100 (depends on CX/CCX ratio) |
| 4 | 7*4-4+4*2 = 32 | ~320 |
| 8 | 7*8-4+4*6 = 76 | ~760 |

BK CLA exact Clifford+T counts depend on `num_merges` and the CX vs CCX breakdown in each phase. The generation script must count accurately.

### CQ/cCQ Increment (value=1)

CQ increment gate counts are width-dependent and require counting which bits of `value=1` are set (only LSB=1). For width N >= 2, the CQ increment (value=1) has fewer gates than general QQ because classical-bit simplification eliminates gates at bit=0 positions.

## Open Questions

1. **BK CLA CQ/cCQ Increment Clifford+T via Python**
   - What we know: BK CLA CQ/cCQ for general values is dynamically generated in C (ToffoliAdditionCLA.c). The user wants increment (value=1) hardcoded.
   - What's unclear: Whether to port the full BK CLA CQ generation logic to Python or to generate the BK CLA QQ Clifford+T sequence and then apply classical-bit simplification in Python.
   - Recommendation: Port the BK CLA QQ Clifford+T generation to Python (already needed for QQ variant), then apply the same classical-bit simplification logic (eliminate gates at bit=0 positions) to derive CQ/cCQ increment variants. This avoids duplicating the full CQ/cCQ generation logic from C.

2. **Dynamic Clifford+T for Widths 9+ (addition path)**
   - What we know: The user decision says "Widths 9+: dynamic generators produce Clifford+T gates directly (skip CCX intermediate step)."
   - What's unclear: The current dynamic generators (toffoli_QQ_add for width 9+) emit CCX gates into sequences via `ccx()` helper. Changing them to emit Clifford+T directly when `toffoli_decompose=True` requires modifying `ToffoliAdditionCDKM.c` and `ToffoliAdditionCLA.c`.
   - Recommendation: This is a larger change. For phase 75, focus on hardcoded widths 1-8. Widths 9+ dynamic Clifford+T can be addressed by having `run_instruction` or the caller decompose CCX at playback time, or by adding a `toffoli_decompose` parameter to the dynamic generators. Defer the 9+ dynamic change to implementation time if scope is too large.

3. **Number of new C files vs. manageable scope**
   - What we know: 8 variants * 8 widths = 64 per-width files + dispatch files. This is a lot of generated code.
   - What's unclear: Whether all 8 BK CLA variants actually need separate generation or can share more code.
   - Recommendation: The generation scripts produce the files automatically, so the count doesn't affect implementation effort much. The BK CLA QQ Clifford+T generation is the most complex part; CQ/cCQ are derived from QQ. Focus effort on getting QQ right, then derive variants.

## Sources

### Primary (HIGH confidence)
- `c_backend/src/gate.c` lines 546-686: `emit_ccx_clifford_t()` and `emit_ccx_clifford_t_seq()` -- exact 15-gate decomposition verified
- `c_backend/include/types.h` line 64: Gate enum `{ X, Y, Z, R, H, Rx, Ry, Rz, P, M, T_GATE, TDG_GATE }`
- `c_backend/src/gate.c` lines 184-271: Gate helper functions (h, t_gate, tdg_gate) -- GateValue verification
- `scripts/generate_toffoli_seq.py`: Complete CDKM QQ/cQQ generation pattern (856 lines)
- `scripts/generate_toffoli_decomp_seq.py`: MCX-decomposed cQQ generation pattern (614 lines)
- `c_backend/src/ToffoliAdditionCLA.c`: Full BK CLA implementation (1034 lines)
- `c_backend/src/ToffoliAdditionCDKM.c`: CDKM addition with hardcoded dispatch
- `c_backend/src/hot_path_add_toffoli.c`: Runtime dispatch logic
- `c_backend/include/toffoli_sequences.h`: Header with all dispatch declarations
- `setup.py` lines 21-68: Build configuration with explicit C source listing
- `c_backend/src/execution.c`: `run_instruction()` -- gate inversion logic for T/Tdg

### Secondary (MEDIUM confidence)
- `c_backend/src/sequences/toffoli_cq_inc_seq_*.c`: CQ/cCQ increment sequence patterns
- `tests/python/test_clifford_t_decomposition.py`: Existing test patterns for Clifford+T verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - exact same stack as existing generation scripts
- Architecture: HIGH - all patterns verified from existing codebase
- Gate decomposition: HIGH - verified against actual C implementation in gate.c
- Pitfalls: HIGH - derived from actual codebase analysis and verified gate encodings
- BK CLA Clifford+T generation: MEDIUM - BK CLA logic in C is well-understood, but Python port needs care to match exactly

**Research date:** 2026-02-17
**Valid until:** Indefinite (project-specific codebase research, not dependent on external library versions)
