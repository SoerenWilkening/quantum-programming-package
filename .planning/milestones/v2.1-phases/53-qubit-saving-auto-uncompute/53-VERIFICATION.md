---
phase: 53-qubit-saving-auto-uncompute
verified: 2026-02-04T23:05:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 53: Qubit-Saving Auto-Uncompute Verification Report

**Phase Goal:** When qubit-saving mode is active, compiled functions that return a qint automatically uncompute all ancillas except the return value's qubits after the forward call

**Verified:** 2026-02-04T23:05:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | With `ql.option("qubit_saving")` active, calling a compiled function that returns a qint automatically uncomputes internal ancillas after forward call completes | ✓ VERIFIED | `_auto_uncompute` method exists, is called from `CompiledFunc.__call__` when `qubit_saving=True`, test `test_auto_uncompute_basic` passes showing increased `total_deallocations` |
| 2 | Return value qubits are preserved (not uncomputed) and remain usable in subsequent operations | ✓ VERIFIED | `_partition_ancillas` separates return vs temp qubits using `block.return_qubit_range`, test `test_auto_uncompute_preserves_return_value` verifies return qint remains live and usable |
| 3 | Auto-uncomputed ancilla qubits are deallocated and available for reuse by later allocations | ✓ VERIFIED | `_auto_uncompute` calls `_deallocate_qubits` for each temp qubit, test `test_auto_uncompute_qubit_reuse` verifies `peak_allocated` doesn't grow on new allocation |
| 4 | Cache key includes qubit_saving mode so mode change triggers recompilation | ✓ VERIFIED | Cache key construction at lines 528-532 includes `qubit_saving`, test `test_auto_uncompute_cache_key_includes_qubit_saving` verifies separate cache entries |
| 5 | f.inverse(x) still works after auto-uncompute, undoing effect on return qubits only | ✓ VERIFIED | `_AncillaInverseProxy` checks `record._auto_uncomputed` flag and uses `record._return_only_gates` for reduced adjoint, test `test_auto_uncompute_inverse_after` passes |
| 6 | Functions that modify input qubits skip auto-uncompute | ✓ VERIFIED | `_function_modifies_inputs` helper exists and is checked at line 555 before triggering auto-uncompute, test `test_auto_uncompute_inplace_skips` passes |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/quantum_language/compile.py` | Auto-uncompute implementation | ✓ VERIFIED | 1244 lines, substantive implementation with all required methods and helpers |
| `_auto_uncompute` method | Method on CompiledFunc | ✓ VERIFIED | Lines 885-966, 82 lines, handles partitioning, adjoint generation, deallocation, record update |
| `_partition_ancillas` helper | Module-level function | ✓ VERIFIED | Lines 340-365, 26 lines, splits ancillas into return vs temp based on `block.return_qubit_range` |
| `_function_modifies_inputs` helper | Module-level function | ✓ VERIFIED | Lines 322-334, 13 lines, checks if gates target param qubits, caches result on block |
| `AncillaRecord._auto_uncomputed` | Slot on AncillaRecord | ✓ VERIFIED | Line 306 in `__slots__`, initialized to False at line 315 |
| `AncillaRecord._return_only_gates` | Slot on AncillaRecord | ✓ VERIFIED | Line 307 in `__slots__`, initialized to None at line 316 |
| `CompiledBlock._modifies_inputs` | Slot on CompiledBlock | ✓ VERIFIED | Line 266 in `__slots__`, initialized to None at line 292 |
| `tests/test_compile.py` | INV-07 test coverage | ✓ VERIFIED | 2636 lines, 10 new tests for auto-uncompute covering all scenarios |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| CompiledFunc.__call__ | _auto_uncompute | qubit_saving mode check | ✓ WIRED | Lines 552-559: checks `qubit_saving`, `internal_qubit_count > 0`, `!_function_modifies_inputs`, then calls `_auto_uncompute` |
| _auto_uncompute | _partition_ancillas | ancilla classification | ✓ WIRED | Lines 896-898: calls `_partition_ancillas` with block, virtual_to_real, ancilla_qubits |
| _auto_uncompute | _deallocate_qubits | temp qubit cleanup | ✓ WIRED | Line 893 imports `_deallocate_qubits`, lines 950-951 call it for each temp physical qubit |
| _auto_uncompute | AncillaRecord fields | record update | ✓ WIRED | Lines 960-961: sets `_auto_uncomputed=True`, `_return_only_gates=return_only_gates` |
| _AncillaInverseProxy.__call__ | _auto_uncomputed flag | reduced adjoint | ✓ WIRED | Lines 1132-1135: checks `record._auto_uncomputed` and uses `_return_only_gates` for inverse |
| Cache key construction | _get_qubit_saving_mode | mode inclusion | ✓ WIRED | Line 36 imports function, line 528 calls it, lines 530/532 include in cache key tuple |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| INV-07: When qubit-saving is active and function returns a qint, auto-uncompute all ancillas except return value's qubits after forward call | ✓ SATISFIED | None |

### Anti-Patterns Found

**None** - No TODOs, FIXMEs, placeholders, or stub patterns found in modified code.

One comment mentions "placeholder" (line 834) but is describing the control qubit mapping logic, not indicating incomplete code.

### Human Verification Required

No human verification required. All functionality is verifiable programmatically through:
- Automated tests (10 tests covering all scenarios)
- Circuit statistics (qubit counts, deallocations)
- Internal state inspection (AncillaRecord flags, forward_calls dict)

---

## Detailed Verification

### Level 1: Existence

All required artifacts exist:
- ✓ `src/quantum_language/compile.py` - 1244 lines
- ✓ `tests/test_compile.py` - 2636 lines with 10 new INV-07 tests
- ✓ `_auto_uncompute` method - lines 885-966
- ✓ `_partition_ancillas` helper - lines 340-365
- ✓ `_function_modifies_inputs` helper - lines 322-334
- ✓ All required slots added to AncillaRecord and CompiledBlock

### Level 2: Substantive

All artifacts have real implementation:

**_auto_uncompute (82 lines):**
- Imports `_deallocate_qubits` from `._core`
- Calls `_partition_ancillas` to split return vs temp
- Early return if no temp qubits
- Builds reverse real->virtual mapping
- Extracts temp-only gates from block.gates
- Generates adjoint via `_inverse_gate_list`
- Handles controlled context (derives controlled gates, updates virtual-to-real mapping)
- Injects adjoint gates with layer floor management
- Deallocates all temp physical qubits
- Updates AncillaRecord with return-only data or removes record if no return qubits

**_partition_ancillas (26 lines):**
- Handles None return and in-place return cases (all ancillas are temp)
- Extracts return virtual range from `block.return_qubit_range`
- Builds reverse real->virtual mapping
- Classifies each ancilla physical qubit as return or temp
- Returns two separate lists

**_function_modifies_inputs (13 lines):**
- Lazy evaluation with cached result on block
- Computes param qubit count from `param_qubit_ranges`
- Checks if any gate targets param qubit index
- Caches result in `block._modifies_inputs`

**Modified _AncillaInverseProxy (6 new lines):**
- Lines 1132-1135: checks `_auto_uncomputed` flag
- Uses `_return_only_gates` instead of full `block.gates` for adjoint when flag is set

**Cache key extension (5 locations):**
- Line 36: Import `_get_qubit_saving_mode`
- Line 528: Call `_get_qubit_saving_mode()` and store in `qubit_saving` variable
- Lines 530, 532: Include `qubit_saving` in cache key tuple (both key_func and default paths)
- Lines 752-769: Include `qubit_saving` in `_capture_and_cache_both` cache keys
- Lines 1057-1061: Include `qubit_saving` in `_InverseCompiledFunc` cache keys

### Level 3: Wired

All connections verified:

**CompiledFunc.__call__ → _auto_uncompute:**
```python
# Line 528: qubit_saving computed for cache key
qubit_saving = _get_qubit_saving_mode()

# Lines 552-559: Trigger auto-uncompute
if qubit_saving:
    cached_block = self._cache.get(cache_key)
    if cached_block is not None and cached_block.internal_qubit_count > 0:
        if not _function_modifies_inputs(cached_block):
            input_key = _input_qubit_key(quantum_args)
            record = self._forward_calls.get(input_key)
            if record is not None:
                self._auto_uncompute(record, quantum_args, is_controlled)
```

**_auto_uncompute → System:**
- Calls `_partition_ancillas` (line 896-898)
- Calls `_inverse_gate_list` (line 931)
- Calls `_derive_controlled_gates` if controlled (line 939)
- Calls `inject_remapped_gates` (line 946)
- Calls `_deallocate_qubits` for each temp qubit (lines 950-951)
- Updates `record._auto_uncomputed` and `record._return_only_gates` (lines 960-961)

**_AncillaInverseProxy → _auto_uncomputed:**
```python
# Lines 1132-1135
if record._auto_uncomputed and record._return_only_gates is not None:
    adjoint_gates = _inverse_gate_list(record._return_only_gates)
else:
    adjoint_gates = _inverse_gate_list(record.block.gates)
```

### Test Coverage

10 comprehensive tests covering all INV-07 scenarios:

1. **test_auto_uncompute_basic** - Verifies auto-uncompute fires, deallocations increase, record marked
2. **test_auto_uncompute_preserves_return_value** - Return qint remains live and usable after auto-uncompute
3. **test_auto_uncompute_qubit_reuse** - Deallocated qubits reused (peak_allocated unchanged)
4. **test_auto_uncompute_inverse_after** - f.inverse(x) works with reduced gate set after auto-uncompute
5. **test_auto_uncompute_none_return** - Functions returning None auto-uncompute all ancillas, record removed
6. **test_auto_uncompute_inplace_skips** - In-place functions skip auto-uncompute
7. **test_auto_uncompute_off_no_effect** - qubit_saving=False means no auto-uncompute
8. **test_auto_uncompute_cache_key_includes_qubit_saving** - Mode change creates separate cache entries
9. **test_auto_uncompute_replay_path** - Auto-uncompute works on replay (second call with same widths)
10. **test_auto_uncompute_controlled_context** - Auto-uncompute fires inside `with ctrl:` block

All 10 tests pass. All 92 compile tests pass (82 existing + 10 new).

### Implementation Quality

**Strengths:**
- Clean separation of concerns (_partition_ancillas, _function_modifies_inputs as reusable helpers)
- Lazy caching pattern for _modifies_inputs avoids repeated computation
- Controlled context handling mirrors existing patterns in _AncillaInverseProxy
- No regression - existing 82 tests pass unchanged
- Comprehensive edge case handling (None return, in-place functions, controlled context)

**No weaknesses identified:**
- All edge cases covered
- Error handling appropriate (early returns for no-op cases)
- Resource cleanup complete (deallocate + record update/removal)
- Cache key extension applied consistently across all cache key construction sites

---

_Verified: 2026-02-04T23:05:00Z_
_Verifier: Claude (gsd-verifier)_
