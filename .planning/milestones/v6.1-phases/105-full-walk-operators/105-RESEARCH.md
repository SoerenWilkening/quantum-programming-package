# Phase 105: Full Walk Operators - Research

**Researched:** 2026-03-05
**Domain:** Quantum walk operator composition (R_A, R_B, walk step U = R_B * R_A)
**Confidence:** HIGH

## Summary

Phase 105 composes the `apply_diffusion()` building block from Phase 104 into the full walk operators R_A, R_B, and walk step U = R_B * R_A. The implementation closely mirrors `walk.py`'s `QWalkTree.R_A()`, `R_B()`, and `walk_step()` methods but adapted to the purely functional chess_walk.py module style.

The key technical challenge is the mega-register construction for `@ql.compile`: unlike QWalkTree which only wraps height + branch registers, the chess walk must also include board_arrs qubits (wk, bk, wn qarrays) because `apply_diffusion` calls derive/underive which touch board state. The `_all_qubits_register` trick (wrapping all qubits into a single qint via `create_new=False, bit_list=arr`) prevents forward-call tracking from blocking repeated walk_step() invocations.

**Primary recommendation:** Implement r_a(), r_b(), all_walk_qubits(), and walk_step() as four standalone functions in chess_walk.py, following the reference walk.py patterns exactly but including board_arrs qubits in the mega-register.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Height-controlled diffusion cascade (WALK-04): `apply_diffusion()` already uses `h_qubit_idx` as control -- the "cascade" is looping over correct depth levels
- R_A operator (WALK-05): Loop `apply_diffusion()` over even depths (0, 2, 4, ...), excluding root; standalone function `r_a()` in chess_walk.py; computes depth sets internally from max_depth
- R_B operator (WALK-06): Loop `apply_diffusion()` over odd depths (1, 3, 5, ...) plus root; root always in R_B regardless of max_depth parity; standalone function `r_b()` in chess_walk.py
- Walk step compilation (WALK-07): Compile U = R_B * R_A via `@ql.compile` using `_all_qubits_register` trick; mega-register includes ALL qubits (height + branch + board_arrs); board array qubits extracted by iterating qarray elements; validity qbools are true ancillas (NOT in mega-register); cache key = total qubit count; `walk_step()` is module-level function with closure cache; inverse handled automatically by @ql.compile; `all_walk_qubits()` is a module-level public function
- Testing: Circuit-gen + structural tests; disjointness verification inline in test; use position (wk=4, bk=60, wn=[10], max_depth=1); test walk_step replay; no simulation tests
- No disjointness assertion inside r_a() -- tested externally
- Depth 0 (leaves) included in R_A for completeness even though it is a no-op

### Claude's Discretion
- Exact function signatures and parameter ordering for r_a(), r_b(), walk_step()
- Internal structure of the closure cache in walk_step()
- Test case depth/branching values beyond the specified position

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WALK-04 | Height-controlled diffusion cascade (D_x only activates at correct depth level) | Already built into apply_diffusion() via h_qubit_idx control; cascade = looping over depths |
| WALK-05 | R_A operator composing diffusion at even depths (excluding root) | Direct loop: `range(0, max_depth+1, 2)` skipping root; follows walk.py:1099-1113 |
| WALK-06 | R_B operator composing diffusion at odd depths plus root | Direct loop: `range(1, max_depth+1, 2)` + explicit root if max_depth is even; follows walk.py:1115-1130 |
| WALK-07 | Walk step U = R_B * R_A composed via `@ql.compile` | Mega-register wraps all qubits; @ql.compile with key=lambda; closure cache pattern |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language | project | Circuit compilation, qint, qbool, qarray, @ql.compile | Project framework |
| numpy | installed | bit_list array construction for qint wrapping | Required by qint(create_new=False, bit_list=...) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| quantum_language.compile | project | @ql.compile decorator for walk_step caching | Walk step compilation |
| quantum_language.walk | project | Internal helpers already imported by chess_walk.py | Reference patterns |

### Imports Needed (New for Phase 105)
```python
import numpy as np
from quantum_language.compile import compile as ql_compile
from quantum_language.qint import qint
```

Note: `numpy` and `qint` are already used in chess_walk.py. Only `ql_compile` is a new import.

## Architecture Patterns

### New Functions Added to chess_walk.py

```
chess_walk.py (existing module)
    existing: create_height_register, create_branch_registers, height_qubit,
              derive_board_state, underive_board_state, prepare_walk_data,
              montanaro_phi, montanaro_root_phi, precompute_diffusion_angles,
              evaluate_children, uncompute_children, apply_diffusion
    new:      r_a, r_b, all_walk_qubits, walk_step
```

### Pattern 1: R_A / R_B as Simple Loops
**What:** r_a() and r_b() are thin loops calling apply_diffusion() at the correct depth levels
**When to use:** Always -- this is the only pattern for composing diffusion operators

Reference (walk.py lines 1099-1130):
```python
def r_a(h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth):
    """Apply R_A: diffusion at even depths, excluding root."""
    for depth in range(0, max_depth + 1, 2):
        if depth == max_depth:
            continue  # Root always belongs to R_B
        apply_diffusion(depth, h_reg, branch_regs, board_arrs,
                       oracle_per_level, move_data_per_level, max_depth)

def r_b(h_reg, branch_regs, board_arrs, oracle_per_level, move_data_per_level, max_depth):
    """Apply R_B: diffusion at odd depths plus root."""
    for depth in range(1, max_depth + 1, 2):
        apply_diffusion(depth, h_reg, branch_regs, board_arrs,
                       oracle_per_level, move_data_per_level, max_depth)
    # Root always in R_B; add if not already covered (even max_depth)
    if max_depth % 2 == 0:
        apply_diffusion(max_depth, h_reg, branch_regs, board_arrs,
                       oracle_per_level, move_data_per_level, max_depth)
```

### Pattern 2: Mega-Register Construction (all_walk_qubits)
**What:** Wraps ALL walk qubits into a single qint for @ql.compile argument
**When to use:** Before walk_step compilation

Key difference from walk.py: Must include board_arrs qubits (3 qarrays x 64 qbools = 192 qubits) because apply_diffusion touches board state via derive/underive.

Reference (walk.py lines 1184-1210, extended for board_arrs):
```python
def all_walk_qubits(h_reg, branch_regs, board_arrs, max_depth):
    """Create qint wrapping all walk qubits (height + branch + board)."""
    all_indices = []
    # Height register qubits
    w = max_depth + 1
    for i in range(w):
        all_indices.append(int(h_reg.qubits[64 - w + i]))
    # Branch register qubits
    for br in branch_regs:
        bw = br.width
        for i in range(bw):
            all_indices.append(int(br.qubits[64 - bw + i]))
    # Board array qubits (wk, bk, wn qarrays -- each is 8x8 qbool)
    for arr in board_arrs:
        for elem in arr:  # iterates over qbool elements
            all_indices.append(int(elem.qubits[63]))

    arr = np.zeros(64, dtype=np.uint32)
    total = len(all_indices)
    for i, idx in enumerate(all_indices):
        arr[64 - total + i] = idx
    return qint(0, create_new=False, bit_list=arr, width=total)
```

### Pattern 3: Closure Cache for walk_step
**What:** Module-level function that compiles on first call, replays on subsequent calls
**When to use:** The walk_step function

Reference (walk.py lines 1212-1249, adapted to functional style):
```python
_walk_compiled = None

def walk_step(h_reg, branch_regs, board_arrs, oracle_per_level,
              move_data_per_level, max_depth):
    """Apply walk step U = R_B * R_A. Compiles on first call."""
    global _walk_compiled
    if _walk_compiled is None:
        # Capture references for closure
        _h = h_reg
        _br = branch_regs
        _ba = board_arrs
        _opl = oracle_per_level
        _mdpl = move_data_per_level
        _md = max_depth

        def _walk_body(all_qubits_reg):
            r_a(_h, _br, _ba, _opl, _mdpl, _md)
            r_b(_h, _br, _ba, _opl, _mdpl, _md)

        total = len(...)  # total qubit count
        _walk_compiled = ql_compile(key=lambda r: total)(_walk_body)

    mega_reg = all_walk_qubits(h_reg, branch_regs, board_arrs, max_depth)
    _walk_compiled(mega_reg)
```

### Anti-Patterns to Avoid
- **Putting board_arrs qubits in validity ancillae category:** Board qubits are NOT ancillae -- they exist across walk_step calls. Only validity qbools are true ancillae.
- **Including validity qbools in mega-register:** These are allocated/uncomputed inside apply_diffusion and must NOT be in the parameter register.
- **Making r_a/r_b methods of a class:** The chess_walk.py module is purely functional (no class). Keep it that way.
- **Passing explicit depth lists to r_a/r_b:** Functions compute depth sets internally from max_depth per locked decision.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Compile/cache infrastructure | Custom memoization | @ql.compile with key= | Handles inverse, controlled variants, cache invalidation |
| Qubit wrapping for compile | Manual qubit tracking | qint(0, create_new=False, bit_list=arr, width=total) | Proper framework integration, no allocation |
| Height control logic | Separate control infrastructure | apply_diffusion's built-in h_qubit_idx control | Already implemented in Phase 104 |

## Common Pitfalls

### Pitfall 1: Missing Board Array Qubits in Mega-Register
**What goes wrong:** walk_step compiles but the compiled function treats board qubits as internal ancillae, breaking replay on second call
**Why it happens:** walk.py's QWalkTree doesn't have external board state, so its _all_qubits_register only includes height + branch. Chess walk is different.
**How to avoid:** Iterate all three qarrays in board_arrs and collect every qbool's physical qubit index
**Warning signs:** Second call to walk_step() crashes or produces different gate count

### Pitfall 2: Root Depth Classification Error
**What goes wrong:** Root appears in both R_A and R_B, or in neither
**Why it happens:** When max_depth is even, root depth is even -- without the explicit exclusion in R_A and explicit inclusion in R_B, root gets double-counted
**How to avoid:** R_A skips depth==max_depth; R_B adds max_depth explicitly if max_depth%2==0
**Warning signs:** Disjointness test fails (overlap in height qubits)

### Pitfall 3: qint bit_list Array Size
**What goes wrong:** qint constructor fails or produces incorrect wrapping
**Why it happens:** bit_list must be exactly 64 elements (np.uint32), with physical qubit indices right-aligned
**How to avoid:** Always create `np.zeros(64, dtype=np.uint32)` and fill from index `64 - total`
**Warning signs:** ValueError or incorrect qubit mapping

### Pitfall 4: Depth 0 in R_A (Leaf No-Op)
**What goes wrong:** Nothing functionally -- apply_diffusion at depth 0 tries to derive 0 levels and process leaf nodes
**Why it happens:** Leaves have no children; the diffusion is a no-op but the function still runs
**How to avoid:** Include depth 0 per convention (matches QWalkTree) but be aware it adds minimal circuit overhead. If depth 0 causes issues (e.g., d_max=0), guard with `if depth == 0: continue` -- but check QWalkTree behavior first.
**Warning signs:** Error in apply_diffusion when d_max=0 at leaf level

### Pitfall 5: Global State for Closure Cache
**What goes wrong:** Module-level `_walk_compiled` persists across test cases
**Why it happens:** Python module globals are not reset between pytest tests
**How to avoid:** Either use a dict keyed by total qubit count (natural cache invalidation), or provide a cache-clearing mechanism for tests. The key=lambda approach in @ql.compile handles this naturally since the compiled function itself has internal caching.
**Warning signs:** Test ordering dependencies

## Code Examples

### Extracting Physical Qubit Indices from qarray
```python
# Source: chess_encoding.py + qarray.pyx analysis
# Each qarray element is a qbool; physical qubit at .qubits[63]
def _collect_qarray_qubits(arr):
    """Collect physical qubit indices from a qarray of qbools."""
    indices = []
    for elem in arr:  # iterates _elements (qbool objects)
        indices.append(int(elem.qubits[63]))
    return indices
```

### @ql.compile with Custom Key
```python
# Source: walk.py line 1247, compile.py line 1665
from quantum_language.compile import compile as ql_compile

# Compile with integer cache key
compiled_fn = ql_compile(key=lambda r: total_qubits)(_walk_body)
# Call with mega-register
compiled_fn(mega_register)
# Inverse is automatic:
compiled_fn.inverse(mega_register)
```

### Depth Set Computation
```python
# R_A depths (even, excluding root)
r_a_depths = [d for d in range(0, max_depth + 1, 2) if d != max_depth]

# R_B depths (odd + root)
r_b_depths = list(range(1, max_depth + 1, 2))
if max_depth % 2 == 0:
    r_b_depths.append(max_depth)

# Verification: all depths covered exactly once
assert set(r_a_depths) | set(r_b_depths) == set(range(0, max_depth + 1))
assert set(r_a_depths) & set(r_b_depths) == set()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QWalkTree class (walk.py) | Purely functional chess_walk.py | Phase 104 | No class, standalone functions, board_arrs as tuple |
| Height+branch only in mega-reg | Height+branch+board_arrs in mega-reg | Phase 105 design | Chess walk touches external board state |

## Open Questions

1. **Depth 0 behavior in apply_diffusion**
   - What we know: apply_diffusion takes depth=1..max_depth normally. Depth 0 means leaves with no children.
   - What's unclear: Does apply_diffusion handle depth=0 gracefully? level_idx = max_depth - 0 = max_depth, which is outside oracle_per_level range (0..max_depth-1). Also move_data_per_level only has max_depth entries.
   - Recommendation: R_A should skip depth=0 (leaves are no-ops anyway). The loop `range(0, max_depth+1, 2)` with `if depth == max_depth: continue` already skips root. Add `if depth == 0: continue` to skip leaves too. This matches the practical behavior -- walk.py R_A starts at depth 0 but local_diffusion at depth 0 is a no-op because there are no children at leaf level. Verify walk.py's local_diffusion handles depth=0.

2. **walk_step cache clearing for tests**
   - What we know: Module-level `_walk_compiled` will persist. @ql.compile has internal caching keyed by the key function.
   - What's unclear: Whether the closure approach or dict approach is cleaner for testing.
   - Recommendation: Use the @ql.compile built-in caching (key=lambda). The compiled function handles cache internally. For the module-level variable, a simple `_walk_compiled = None` reset or making walk_step return the compiled function reference should suffice.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | tests/python/conftest.py |
| Quick run command | `pytest tests/python/test_chess_walk.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WALK-04 | Height-controlled diffusion cascade activates D_x at correct depth | unit (structural) | `pytest tests/python/test_chess_walk.py::TestHeightControlledCascade -x` | Wave 0 |
| WALK-05 | R_A composes diffusion at even depths excluding root | unit (structural) | `pytest tests/python/test_chess_walk.py::TestRA -x` | Wave 0 |
| WALK-06 | R_B composes diffusion at odd depths plus root | unit (structural) | `pytest tests/python/test_chess_walk.py::TestRB -x` | Wave 0 |
| WALK-07 | Walk step U = R_B * R_A compiles and replays | integration | `pytest tests/python/test_chess_walk.py::TestWalkStep -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_chess_walk.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `TestHeightControlledCascade` class in test_chess_walk.py -- covers WALK-04 (disjointness verification)
- [ ] `TestRA` class in test_chess_walk.py -- covers WALK-05 (circuit gen, depth coverage)
- [ ] `TestRB` class in test_chess_walk.py -- covers WALK-06 (circuit gen, root inclusion)
- [ ] `TestWalkStep` class in test_chess_walk.py -- covers WALK-07 (compile, replay, all_walk_qubits)
- [ ] `TestAllWalkQubits` class in test_chess_walk.py -- covers mega-register construction

## Sources

### Primary (HIGH confidence)
- walk.py lines 1099-1249 -- R_A, R_B, _all_qubits_register, walk_step reference implementation
- chess_walk.py -- Phase 104 implementation (apply_diffusion and all dependencies)
- compile.py line 1665 -- @ql.compile decorator API
- qarray.pyx -- _elements iteration for qubit extraction
- chess_encoding.py -- qarray(wk, dtype=ql.qbool) structure (8x8 qbool arrays)

### Secondary (MEDIUM confidence)
- 105-CONTEXT.md -- locked decisions from user discussion

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use from Phase 104
- Architecture: HIGH - direct adaptation of proven walk.py patterns with well-understood chess extension
- Pitfalls: HIGH - board_arrs mega-register difference is well-documented in CONTEXT.md; depth classification logic verified against walk.py source

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- internal project patterns)
