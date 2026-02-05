---
phase: 58-hardcoded-sequences-1-8
plan: 01
subsystem: c-backend
tags: [performance, sequences, static-allocation, QFT-addition]

dependency_graph:
  requires: []
  provides:
    - Static QQ_add sequences for widths 1-4
    - Static cQQ_add sequences for widths 1-4
    - Dispatch helper infrastructure
    - Build system integration
  affects:
    - 58-02 (5-8 bit sequences)
    - 58-03 (integration and testing)

tech_stack:
  added: []
  patterns:
    - Static gate array initialization
    - Compile-time constant angles (SEQ_PI)
    - Dispatch helper pattern for width-based lookup

file_tracking:
  key_files:
    created:
      - c_backend/include/sequences.h
      - c_backend/src/sequences/add_seq_1_4.c
    modified:
      - setup.py

decisions:
  - id: SEQ-01
    choice: Use SEQ_PI compile-time constant instead of M_PI
    reason: M_PI from math.h is not a constant expression in standard C, preventing static initialization
  - id: SEQ-02
    choice: Separate 1-4 and 5-8 bit widths into different source files
    reason: Keeps file sizes manageable and matches research recommendation of ~400 LOC per file
  - id: SEQ-03
    choice: Use const gate_t arrays with designated initializers
    reason: Enables compile-time initialization without runtime allocation

metrics:
  duration: 7m 4s
  completed: 2026-02-05
---

# Phase 58 Plan 01: Hardcoded Sequences 1-4 Bit Summary

**One-liner:** Static QQ_add and cQQ_add gate sequences for 1-4 bit widths with dispatch infrastructure.

## What Was Built

Created the foundational hardcoded sequences infrastructure for eliminating runtime allocation overhead in common arithmetic operations.

### Files Created

1. **c_backend/include/sequences.h** (53 lines)
   - Defines HARDCODED_MAX_WIDTH constant (8)
   - Declares public API: get_hardcoded_QQ_add(), get_hardcoded_cQQ_add()
   - Declares internal helpers for 1-4 and 5-8 bit dispatch

2. **c_backend/src/sequences/add_seq_1_4.c** (1504 lines after formatting)
   - QQ_add sequences for widths 1-4 (3, 8, 13, 18 layers respectively)
   - cQQ_add sequences for widths 1-4 (7, 17, 28, 40 layers respectively)
   - Dispatch helpers: get_hardcoded_QQ_add_1_4(), get_hardcoded_cQQ_add_1_4()

### Files Modified

1. **setup.py** (+1 line)
   - Added sequences/add_seq_1_4.c to c_sources list

## Technical Details

### QQ_add Sequence Structure
- **Width 1:** 3 layers (QFT: 1, Add: 1, IQFT: 1)
- **Width 2:** 8 layers (QFT: 3, Add: 2, IQFT: 3)
- **Width 3:** 13 layers (QFT: 5, Add: 3, IQFT: 5)
- **Width 4:** 18 layers (QFT: 7, Add: 4, IQFT: 7)

Formula: `num_layers = 5 * bits - 2`

### cQQ_add Sequence Structure
- **Width 1:** 7 layers (QFT + 3-block controlled addition + IQFT)
- **Width 2:** 17 layers
- **Width 3:** 28 layers
- **Width 4:** 40 layers

The cQQ_add sequences include:
1. Unconditional half-rotations
2. CNOT + negative half-rotations + CNOT (controlled toggle)
3. Controlled rotations from b register

### Gate Initialization Pattern
```c
{.Gate = P, .Target = 0, .NumControls = 1, .Control = {1},
 .large_control = NULL, .GateValue = SEQ_PI, .NumBasisGates = 0}
```

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| SEQ-01 | SEQ_PI compile-time constant | M_PI not usable in static initializers |
| SEQ-02 | Split 1-4 and 5-8 into separate files | Manageable file sizes |
| SEQ-03 | Designated initializers for gate arrays | Compile-time allocation |

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| f2cb9ec | feat | Create sequences.h header and sequences directory |
| 2175940 | feat | Implement QQ_add sequences for widths 1-4 |
| c226602 | feat | Implement cQQ_add sequences for widths 1-4 |
| 79a0f1a | chore | Add add_seq_1_4.c to build configuration |

## Verification Results

- [x] Header exists with dispatch function declarations
- [x] Sequences directory created
- [x] Source compiles standalone with gcc -std=c23
- [x] setup.py includes new source file
- [x] Both QQ_add and cQQ_add dispatch helpers implemented
- [x] File exceeds 250 line minimum (1504 lines)

## Next Phase Readiness

**Plan 02 Dependencies Met:**
- Dispatch infrastructure established
- Pattern validated for static sequence definition
- Build system integration complete

**For Plan 02:**
- Implement QQ_add sequences for widths 5-8
- Implement cQQ_add sequences for widths 5-8
- Add unified public dispatch functions
