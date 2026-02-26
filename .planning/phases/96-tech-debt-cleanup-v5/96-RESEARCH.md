# Phase 96: v5.0 Tech Debt Cleanup - Research

**Researched:** 2026-02-26
**Domain:** Cython/C codebase cleanup, test infrastructure, documentation
**Confidence:** HIGH

## Summary

Phase 96 is a focused tech debt cleanup addressing four items identified by the v5.0 milestone audit. The work is entirely internal to the existing codebase -- no new libraries, no new features, no algorithm changes. All tasks involve straightforward file edits to remove dead code, add a test, and document a known limitation.

The three plans map cleanly to the four success criteria: Plan 96-01 removes dead declarations/imports (SC1 + SC2), Plan 96-02 adds the qubit accounting test (SC3), and Plan 96-03 documents the QQ division ancilla leak (SC4). Each is independent and can be executed in any order.

**Primary recommendation:** Execute plans in order (01, 02, 03). Recompile after Plan 01 to verify Cython builds cleanly. Run `pytest tests/python/ -v` after Plan 02 to verify the new test passes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Remove all dead declarations and imports completely -- no stubs
- `toffoli_mod_reduce` declaration in `_core.pxd`: clean removal
- `toffoli_cdivmod_cq` and `toffoli_cdivmod_qq` imports: clean removal
- If needed later, recover from git history
- Test all modular operations, not just FIX-03 related ops
- Use no-leak check pattern: verify `circuit_stats()['current_in_use']` returns to expected value after each operation
- Avoid brittle exact-count assertions -- focus on regression detection
- Document QQ division ancilla leak in all three locations:
  - Inline code comment at the QQ division implementation
  - GitHub issue as tracking issue with details and potential fix approaches
  - Project-level known issues/limitations document

### Claude's Discretion
- Exact GitHub issue format and labels
- Which known issues doc to use or whether to create one
- Specific modular operations to include in qubit accounting tests (all that exist)
- Order of cleanup operations

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | existing | `.pxd`/`.pyx` compilation | Already in build system |
| pytest | existing | Test framework | Already used for all project tests |
| gh CLI | 2.46.0 | GitHub issue creation | Available on system, standard for issue tracking |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| quantum_language | project | Python API (`circuit_stats()`, `qint_mod`, `qint`) | Qubit accounting test |
| qiskit_aer | existing | Not needed for qubit accounting test | Only if simulation-level verification desired |

### Alternatives Considered
None -- this phase uses only existing project infrastructure.

## Architecture Patterns

### Plan 01: Dead Code Removal

**What:** Remove unused C function declarations from Cython `.pxd` file and unused imports from `.pyx` file.

**Files to modify:**
```
src/quantum_language/_core.pxd     # Remove toffoli_mod_reduce + toffoli_cmod_reduce declarations (lines 74-78)
src/quantum_language/qint.pyx      # Remove toffoli_cdivmod_cq, toffoli_cdivmod_qq from import (line 32)
```

**Pattern: Clean removal from `_core.pxd`**
Remove the entire "Toffoli Modular Reduction (Phase 91)" block (lines 74-78):
```
	# Toffoli Modular Reduction (Phase 91)
	void toffoli_mod_reduce(circuit_t *circ, const unsigned int *value_qubits,
	                        int value_bits, int64_t modulus)
	void toffoli_cmod_reduce(circuit_t *circ, const unsigned int *value_qubits,
	                         int value_bits, int64_t modulus, unsigned int ext_ctrl)
```

The C-level functions in `ToffoliModReduce.c` and the header declarations in `toffoli_arithmetic_ops.h` should remain -- they are valid C code, just unreachable from the Python layer. The audit identified only the `_core.pxd` declaration as dead code. The C functions may be useful if a future phase needs direct C-level modular reduction.

**Pattern: Clean removal from `qint.pyx`**
Remove `toffoli_cdivmod_cq, toffoli_cdivmod_qq,` from the cimport block at line 32. The remaining import on line 31 (`toffoli_divmod_cq, toffoli_divmod_qq,`) stays -- those ARE used for division dispatch.

**Verification:** Rebuild Cython extensions and ensure the project compiles. Run `pytest tests/python/ -v` to verify nothing breaks.

**Confidence:** HIGH -- verified by grepping the codebase that:
- `toffoli_mod_reduce` is declared in `_core.pxd` line 75 but never imported by any `.pyx` file (qint_mod.pyx uses Beauregard primitives directly)
- `toffoli_cmod_reduce` is declared in `_core.pxd` line 77 but never imported by any `.pyx` file
- `toffoli_cdivmod_cq` is imported in `qint.pyx` line 32 but never referenced in any function body
- `toffoli_cdivmod_qq` is imported in `qint.pyx` line 32 but never referenced in any function body

### Plan 02: Qubit Accounting Test

**What:** Add a test that explicitly verifies `circuit_stats()['current_in_use']` returns to expected values after modular operations, closing the FIX-03 gap identified by the audit.

**Target file:** New test class in existing `tests/test_modular.py` (or a new `tests/test_modular_accounting.py`). The existing `tests/test_modular.py` already tests modular arithmetic correctness with 2500+ simulation tests. Adding qubit accounting tests to the same file or a companion file is natural.

**Modular operations to test (all that exist in `qint_mod.pyx`):**
1. `qint_mod.__add__` -- CQ modular addition (`qint_mod + int`)
2. `qint_mod.__add__` -- QQ modular addition (`qint_mod + qint_mod`)
3. `qint_mod.__sub__` -- CQ modular subtraction (`qint_mod - int`)
4. `qint_mod.__sub__` -- QQ modular subtraction (`qint_mod - qint_mod`)
5. `qint_mod.__mul__` -- CQ modular multiplication (`qint_mod * int`)
6. `qint_mod.__neg__` -- Negation (`-qint_mod`)

QQ multiplication (`qint_mod * qint_mod`) also exists but uses a result register; include it if feasible.

**Pattern: No-leak check (from existing codebase)**
```python
# Pattern from tests/test_toffoli_addition.py::test_ancilla_freed_after_qq_addition
def test_modular_add_cq_no_qubit_leak():
    """CQ modular addition does not leak qubits."""
    ql.circuit()
    ql.option("fault_tolerant", True)

    a = ql.qint_mod(3, N=7)
    stats_before = ql.circuit_stats()
    in_use_before = stats_before["current_in_use"]

    result = a + 5  # CQ modular addition

    stats_after = ql.circuit_stats()
    in_use_after = stats_after["current_in_use"]

    # Result register is the only expected increase
    expected_increase = result.width
    actual_increase = in_use_after - in_use_before
    assert actual_increase == expected_increase, (
        f"Expected current_in_use to increase by {expected_increase} "
        f"(result register only), but increased by {actual_increase}. "
        f"Possible ancilla leak."
    )
```

**Key design decisions from CONTEXT.md:**
- Test ALL modular operations, not just the FIX-03 related ops
- Use no-leak check pattern: verify `current_in_use` returns to expected value
- Avoid brittle exact-count assertions -- focus on regression detection
- The "expected value" is: `in_use_before + result_register_width` for operations that create a new result register

**Special case: QQ operations** may use temporary ancilla internally (Beauregard sequence). The Beauregard primitives in `ToffoliModAdd.c` are designed to allocate and free all ancillae within the function. Verify that `current_in_use` after the operation equals `in_use_before + result_width`.

**No simulation needed:** These tests check allocator state, not circuit correctness. No Qiskit/QASM needed. Tests will be fast (<1s each).

**Confidence:** HIGH -- the `circuit_stats()` API is well-established (Phase 3), and the pattern is already used in `test_toffoli_addition.py` and `test_compile.py`.

### Plan 03: QQ Division Ancilla Leak Documentation

**What:** Document the QQ division ancilla leak as a known limitation in three locations per CONTEXT.md.

**Location 1: Inline code comment**
File: `c_backend/src/ToffoliDivision.c`
The QQ division function `toffoli_divmod_qq` (line 470) already has extensive inline comments (lines 605-828) explaining why comparison ancillae cannot be uncomputed. The existing comments at lines 792-828 explicitly document the issue. Enhance with a structured "KNOWN LIMITATION" banner comment at the function entry point.

**Location 2: GitHub issue**
Create via `gh issue create` on `SoerenWilkening/speed-oriented-quantum-circuit-backend`.

Recommended format:
- **Title:** "QQ division: comparison ancilla leak in repeated-subtraction path"
- **Labels:** `bug`, `known-limitation`, `tech-debt` (or whatever labels exist)
- **Body:** Description of the leak, affected functions, workaround (use CQ division), and potential fix approaches (Bennett's trick full uncomputation, alternative QQ division algorithms)

**Location 3: Project-level known issues document**
No existing `KNOWN-ISSUES.md` or `LIMITATIONS.md` exists in the project. Options:
- **Recommended:** Create `docs/KNOWN-ISSUES.md` at project root `docs/` directory (directory already exists with `optimizer_benchmark_results.md`)
- Alternative: Add a section to `README.md` or `docs/` subfolder

The document should catalog known limitations with:
- Issue ID and description
- Affected functions/APIs
- Impact and workaround
- Link to GitHub tracking issue
- Potential fix approaches

**The ancilla leak explained:**
- `toffoli_divmod_qq` uses repeated subtraction (2^n iterations for n-bit dividend)
- Each iteration allocates a comparison ancilla (`cmp_anc`) to determine if remainder >= divisor
- After the conditional subtraction/quotient-increment, `cmp_anc` is entangled with the computation state
- There is no known efficient uncomputation for `cmp_anc` without doubling the circuit (full Bennett's trick)
- Result: each QQ division call leaks 2^n comparison ancillae that remain allocated
- CQ division (classical divisor) does NOT have this issue -- it uses a different algorithm with proper Bennett's trick uncomputation
- Already tracked in test xfails: `KNOWN_TOFFOLI_QDIV_FAILURES` in `tests/test_toffoli_division.py`

**Confidence:** HIGH -- the leak is well-documented in code comments and planning docs. The documentation task is straightforward.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Qubit accounting assertions | Custom qubit tracking | `ql.circuit_stats()['current_in_use']` | Already tracks allocations precisely at C level |
| GitHub issue creation | Manual web UI | `gh issue create` CLI | Scriptable, consistent format |
| Cython rebuild | Manual gcc/cython | `python setup.py build_ext --inplace` or existing build system | Already configured |

**Key insight:** All infrastructure for this phase already exists. No new tools or libraries needed.

## Common Pitfalls

### Pitfall 1: Removing declarations that ARE used
**What goes wrong:** Removing a declaration from `_core.pxd` that is cimported by another `.pyx` file causes a compile error.
**Why it happens:** The `.pxd` file is the Cython equivalent of a C header -- any `.pyx` that cimports from it depends on the declarations.
**How to avoid:** Before removing, grep ALL `.pyx` and `.pxd` files for the function name. Verified:
- `toffoli_mod_reduce`: not imported by any `.pyx` (only declared in `_core.pxd`). `qint_mod.pyx` uses Beauregard primitives directly.
- `toffoli_cmod_reduce`: not imported by any `.pyx` (only declared in `_core.pxd`).
- `toffoli_cdivmod_cq/qq`: imported in `qint.pyx` line 32 but never called in function bodies.
**Warning signs:** Compile error after removal.

### Pitfall 2: Breaking the C header / C implementation
**What goes wrong:** Removing the C-level function or header declaration causes link errors.
**Why it happens:** The Cython `.pxd` declaration is independent of the C header. Only the `.pxd` and `.pyx` references are dead.
**How to avoid:** Only remove from `.pxd` and `.pyx` files. Keep `toffoli_arithmetic_ops.h` and `ToffoliModReduce.c` / `ToffoliDivision.c` intact.
**Warning signs:** Link errors mentioning undefined symbols.

### Pitfall 3: Qubit accounting test counts wrong for operations that create result registers
**What goes wrong:** Test expects `current_in_use` to return to pre-operation value, but the operation allocates a new result register.
**Why it happens:** Modular operations create a new `qint` result register (e.g., `result = a + 5` creates a new register). The `current_in_use` increases by the result width.
**How to avoid:** Assert that the increase equals exactly the result register width. Don't assert that `current_in_use` returns to the pre-op value.
**Warning signs:** Tests failing with "increased by N" where N = result width.

### Pitfall 4: QQ modular multiplication uses extra result register
**What goes wrong:** QQ multiplication (`qint_mod * qint_mod`) allocates an intermediate result register in addition to the output, causing `current_in_use` to increase by more than the output width.
**Why it happens:** The C function `toffoli_mod_mul_qq` takes separate `a_qubits`, `b_qubits`, and `result_qubits` arrays.
**How to avoid:** Check the `qint_mod.__mul__` implementation to see how many registers it allocates. May need to account for intermediate registers. If uncertain, use a softer assertion (increase <= expected_max).
**Warning signs:** Test failing specifically for QQ multiplication.

### Pitfall 5: gh issue create fails without authentication
**What goes wrong:** `gh issue create` fails because the CLI is not authenticated to the repo.
**Why it happens:** The `gh` CLI needs to be authenticated to create issues.
**How to avoid:** Check `gh auth status` before attempting issue creation. If not authenticated, provide the issue content as a markdown file that the user can create manually.
**Warning signs:** `gh: authentication required` error.

## Code Examples

### Dead code removal from `_core.pxd`

```python
# BEFORE (lines 73-78 of _core.pxd):
	# Toffoli Modular Reduction (Phase 91)
	void toffoli_mod_reduce(circuit_t *circ, const unsigned int *value_qubits,
	                        int value_bits, int64_t modulus)
	void toffoli_cmod_reduce(circuit_t *circ, const unsigned int *value_qubits,
	                         int value_bits, int64_t modulus, unsigned int ext_ctrl)

# AFTER: Lines 73-78 removed entirely. The "Toffoli Modular CQ Addition" block
# (currently line 80) becomes the next block after "Toffoli Division (Phase 91)".
```

### Dead import removal from `qint.pyx`

```python
# BEFORE (lines 31-32 of qint.pyx):
    toffoli_divmod_cq, toffoli_divmod_qq,
    toffoli_cdivmod_cq, toffoli_cdivmod_qq,

# AFTER:
    toffoli_divmod_cq, toffoli_divmod_qq,
```

### Qubit accounting test pattern

```python
import quantum_language as ql

def test_modular_add_cq_qubit_accounting():
    """CQ modular addition creates only the result register, no ancilla leak."""
    ql.circuit()
    ql.option("fault_tolerant", True)

    a = ql.qint_mod(3, N=7)  # 3-bit register (7.bit_length() = 3)
    stats_before = ql.circuit_stats()
    in_use_before = stats_before["current_in_use"]

    result = a + 5  # CQ modular addition: (3+5) mod 7 = 1

    stats_after = ql.circuit_stats()
    in_use_after = stats_after["current_in_use"]

    increase = in_use_after - in_use_before
    assert increase == result.width, (
        f"CQ mod add: expected current_in_use increase of {result.width} "
        f"(result register), got {increase}. Possible ancilla leak."
    )
```

### Known limitation documentation pattern

```markdown
## QQ Division Ancilla Leak

**Status:** Known limitation
**Tracking:** #NNN (GitHub issue)
**Affected:** `toffoli_divmod_qq` in `c_backend/src/ToffoliDivision.c`
**Impact:** QQ division leaks 2^n comparison ancillae per call (n = dividend width)

### Description
The quantum-divisor variant of Toffoli division uses repeated subtraction
(2^n iterations). Each iteration requires a comparison ancilla to determine
if remainder >= divisor. After the conditional subtraction, the ancilla is
entangled with the computation state and cannot be efficiently uncomputed.

### Workaround
Use CQ division (classical divisor) when possible. CQ division uses
bit-serial restoring division with proper Bennett's trick uncomputation
and has zero ancilla leak.

### Potential Fix Approaches
1. Full Bennett's trick at iteration level (doubles circuit size)
2. Alternative QQ division algorithms (e.g., Newton-Raphson quantum division)
3. Logarithmic-depth comparison with reversible uncomputation
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python `_reduce_mod` with persistent ancilla leak | C-level Beauregard modular primitives | Phase 92 | Clean ancilla uncomputation for all modular ops |
| `toffoli_mod_reduce` general reduction | Operation-specific Beauregard sequences | Phase 92 | `toffoli_mod_reduce` is dead code at Python layer |

**Deprecated/outdated:**
- `toffoli_mod_reduce` / `toffoli_cmod_reduce`: superseded by Beauregard primitives in Phase 92. C code remains valid but unreachable from Python.
- `toffoli_cdivmod_cq` / `toffoli_cdivmod_qq`: C code exists and compiles, but Python dispatch never calls them (controlled division not wired).

## Open Questions

1. **QQ multiplication intermediate registers**
   - What we know: `toffoli_mod_mul_qq` takes separate a, b, and result qubit arrays. The Python `__mul__` method allocates a result register.
   - What's unclear: Whether the C function internally allocates additional ancilla that persists after the call.
   - Recommendation: During Plan 02 implementation, test QQ multiplication empirically. If current_in_use increase exceeds result_width, investigate and document.

2. **GitHub issue labels**
   - What we know: `gh` CLI is available and repo is `SoerenWilkening/speed-oriented-quantum-circuit-backend`.
   - What's unclear: What labels exist on the repo.
   - Recommendation: Check with `gh label list` during Plan 03 execution. Use standard labels like `bug`, `enhancement`, or create `known-limitation` if it doesn't exist.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `_core.pxd`, `qint.pyx`, `qint_mod.pyx`, `ToffoliDivision.c`
- `v5.0-MILESTONE-AUDIT.md`: Identified all four tech debt items
- `tests/test_toffoli_addition.py`: Existing qubit accounting test pattern (lines 424-476)
- `tests/test_toffoli_division.py`: QQ division xfail documentation (lines 43-56)

### Secondary (MEDIUM confidence)
- Phase 91 SUMMARYs and VERIFICATION: Confirm toffoli_mod_reduce is superseded
- Phase 92 RESEARCH and code: Confirm Beauregard primitives replaced modular reduction

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all tools already in project
- Architecture: HIGH - straightforward file edits with verified targets
- Pitfalls: HIGH - verified all dead code claims by grepping entire codebase

**Research date:** 2026-02-26
**Valid until:** indefinite (internal codebase cleanup, not dependent on external library versions)
