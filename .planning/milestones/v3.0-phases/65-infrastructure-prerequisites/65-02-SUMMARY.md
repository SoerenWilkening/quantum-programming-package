---
phase: 65-infrastructure-prerequisites
plan: 02
subsystem: infra
tags: [qubit-allocator, block-allocation, free-list, coalescing, c-backend]

# Dependency graph
requires:
  - phase: none
    provides: existing qubit_allocator.h/.c with single-qubit freed stack
provides:
  - block-based qubit free-list with contiguous multi-qubit allocation
  - adjacent-block coalescing on free
  - backward-compatible single-qubit alloc/free (treated as block of size 1)
  - 10 C unit tests validating block allocator behavior
affects: [66-toffoli-adder, 67-toffoli-subtractor, 68-toffoli-comparator, 69-toffoli-multiplier]

# Tech tracking
tech-stack:
  added: []
  patterns: [block-based-free-list, first-fit-allocation, sorted-insertion-coalescing]

key-files:
  created:
    - tests/c/test_allocator_block.c
  modified:
    - c_backend/include/qubit_allocator.h
    - c_backend/src/qubit_allocator.c
    - tests/c/Makefile

key-decisions:
  - "Block free-list uses sorted array (not linked list) for simplicity and cache locality"
  - "First-fit allocation strategy (not best-fit) for speed -- freed_block_count is small"
  - "No defragmentation -- when no contiguous block fits, allocate fresh from next_qubit"
  - "Single-qubit ops are just blocks of size 1 -- no special case needed"

patterns-established:
  - "qubit_block_t: contiguous qubit block struct with start/count fields"
  - "Sorted insertion with memmove for block free-list maintenance"
  - "Adjacent-block coalescing: merge with prev and next on every free"

# Metrics
duration: 24min
completed: 2026-02-14
---

# Phase 65 Plan 02: Block-Based Qubit Allocator Summary

**Block-based free-list replacing single-qubit freed stack, with first-fit contiguous allocation, sorted insertion, and adjacent-block coalescing**

## Performance

- **Duration:** 24 min
- **Started:** 2026-02-14T18:15:50Z
- **Completed:** 2026-02-14T18:39:53Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Replaced freed_stack (single-qubit reuse only) with freed_blocks array supporting any block size
- Implemented first-fit block search in allocator_alloc() for contiguous multi-qubit allocation
- Implemented sorted insertion with bidirectional coalescing in allocator_free()
- Added 10 comprehensive C unit tests covering all block allocator behaviors
- Verified backward compatibility: all existing Python tests pass (pre-existing failures unchanged)

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace freed stack with block-based free-list** - `11fb70d` (feat)
2. **Task 2: Add C unit tests for block allocator** - `bb8e2ad` (test)

## Files Created/Modified
- `c_backend/include/qubit_allocator.h` - Added qubit_block_t struct, replaced freed_stack fields with freed_blocks/freed_block_count/freed_block_capacity
- `c_backend/src/qubit_allocator.c` - Block-based alloc (first-fit search), block-based free (sorted insertion + coalescing)
- `tests/c/test_allocator_block.c` - 10 unit tests for block allocator operations
- `tests/c/Makefile` - Added test_allocator_block target and ALLOC_SRCS, run_alloc convenience target

## Decisions Made
- Used sorted array (not linked list) for freed_blocks -- simpler, better cache locality, freed_block_count is always small
- First-fit strategy chosen over best-fit for speed -- allocator is not hot path, simplicity wins
- No defragmentation: if no contiguous freed block fits, fresh qubits are allocated from next_qubit
- Single-qubit operations use the same code path as multi-qubit (block of size 1)
- Test links only qubit_allocator.c (no QPU.c dependency needed since circuit_get_allocator is not called from test)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing segfault in test_array_creates_list_of_qint and test_array_2d (confirmed pre-existing by testing with original code before changes). Not caused by allocator changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Block-based allocator is ready for Toffoli arithmetic phases (66-69) which require multi-qubit ancilla blocks
- allocator_alloc(count > 1) now searches freed blocks for reuse instead of always allocating fresh
- allocator_free() correctly coalesces adjacent blocks, preventing free-list fragmentation
- All 10 C unit tests pass, Python test suite has zero regressions from this change

## Self-Check: PASSED

All files verified present, all commits verified in git log, all key content patterns found.

---
*Phase: 65-infrastructure-prerequisites*
*Completed: 2026-02-14*
