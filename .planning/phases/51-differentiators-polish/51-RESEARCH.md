# Phase 51: Differentiators & Polish - Research

**Researched:** 2026-02-04
**Domain:** Inverse generation, debug introspection, nested compilation for quantum compiled functions
**Confidence:** HIGH

## Summary

Phase 51 adds three features to the existing `@ql.compile` decorator plus a comprehensive test suite. The existing `CompiledFunc` and `CompiledBlock` classes in `src/quantum_language/compile.py` already store virtualised gate lists with full gate metadata (type, target, angle, controls). All three features operate purely at the Python level on the cached gate list data structures -- no C backend changes are required.

**Inverse generation** reverses a `CompiledBlock.gates` list and negates rotation angles. The C-level `reverse_circuit_range()` in `execution.c` already implements this exact transformation (LIFO order, `GateValue *= -1`) for circuit-level uncomputation; Phase 51 replicates this at the Python gate-dict level. Self-adjoint gates (X, Y, Z, H -- type indices 0-4) are their own inverses; rotation gates (R, Rx, Ry, Rz, P -- type indices 3, 5, 6, 7, 8) have angles negated; measurement gates (M -- type 9) are non-reversible. The constants `_SELF_ADJOINT` and `_ROTATION_GATES` already exist in `compile.py`.

**Debug mode** adds a `debug=True` parameter to the decorator that prints statistics to stderr on each call (matching the existing pattern: `print(..., file=sys.stderr)` used in `qint.pyx` for uncomputation warnings). A `.stats` property returns a dict when debug is active, `None` otherwise.

**Nesting** requires detecting when a `CompiledFunc.__call__` occurs inside another `CompiledFunc._capture()` and inlining the inner function's cached gates into the outer capture. The key mechanism: inner calls during capture already emit gates to the circuit (either via normal execution or replay), so they are naturally captured by the outer function's `extract_gate_range()`. The main work is ensuring replayed (cached) gates from the inner function are correctly included and that a recursion depth limit prevents infinite loops.

**Primary recommendation:** All three features are pure Python additions to `CompiledFunc` and `CompiledBlock` in `compile.py`. No Cython or C changes needed. Inverse operates on the cached gate list. Debug wraps `__call__`. Nesting works via the existing capture mechanism (inner replayed gates flow through `inject_remapped_gates` which calls `add_gate`, captured by outer's layer range).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `compile.py` (existing) | Phase 48-50 | `CompiledFunc`, `CompiledBlock`, `_optimize_gate_list` | All three features extend these existing classes |
| `sys.stderr` | stdlib | Debug output destination | Decision: print to stderr, matching existing pattern in `qint.pyx` |
| `_SELF_ADJOINT`, `_ROTATION_GATES` constants | existing in compile.py | Gate classification for adjoint transformation | Already define which gates are self-adjoint vs rotation |
| `extract_gate_range()` | existing in `_core.pyx` | Outer capture reads inner replay gates | Already captures all gates emitted in a layer range |
| `inject_remapped_gates()` | existing in `_core.pyx` | Inner replay emits gates into circuit during outer capture | Existing replay mechanism; gates become visible to outer capture |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `collections.OrderedDict` | stdlib (existing) | Cache management | Already used in `CompiledFunc._cache` |
| `threading.local` | stdlib | Nesting depth tracking | Track recursion depth for compiled function calls |
| `dataclasses` or plain dict | stdlib | Stats container | For `.stats` property return value |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python-level gate reversal | C-level `reverse_circuit_range()` | C function operates on emitted circuit, not cached lists; Python-level is needed for cached virtual gates |
| `threading.local` for depth | Module-level global counter | Thread safety; but project appears single-threaded, so global is acceptable |
| `dataclass` for stats | Plain dict | Dict is simpler, no import needed, sufficient for a debugging aid |

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
  compile.py               # MODIFY: Add inverse, debug, nesting features to CompiledFunc/CompiledBlock
  __init__.py              # No changes expected (compile already exported)
tests/
  test_compile.py          # MODIFY: Add comprehensive tests for inverse, debug, nesting, composition
```

### Pattern 1: Adjoint Gate Transformation (from C `reverse_circuit_range`)
**What:** Reverse gate list order and negate rotation angles to produce adjoint/inverse
**When to use:** When `.inverse()` is called on a compiled function
**Example:**
```python
# Source: c_backend/src/execution.c lines 57-84 (reverse_circuit_range)
# The C function does: iterate LIFO, copy gate, g->GateValue *= pow(-1, 1)
# Python equivalent for cached gate dicts:

_NON_REVERSIBLE = frozenset({_M})  # Measurement gates cannot be inverted

def _adjoint_gate(gate):
    """Return the adjoint of a single gate dict."""
    if gate["type"] in _NON_REVERSIBLE:
        raise ValueError(f"Gate type {gate['type']} is not reversible")
    adj = dict(gate)
    if gate["type"] in _ROTATION_GATES:
        adj["angle"] = -gate["angle"]
    # Self-adjoint gates (X, Y, Z, H) are unchanged
    return adj

def _inverse_gate_list(gates):
    """Return adjoint of gate sequence: reversed order, adjoint each gate."""
    return [_adjoint_gate(g) for g in reversed(gates)]
```

### Pattern 2: Debug Wrapper in `__call__`
**What:** Wrap the existing `__call__` with statistics tracking when `debug=True`
**When to use:** When `@ql.compile(debug=True)` is specified
**Example:**
```python
# Existing pattern in qint.pyx: print(..., file=sys.stderr)
import sys

def __call__(self, *args, **kwargs):
    if not self._debug:
        return self._call_impl(*args, **kwargs)

    # Determine if this will be a cache hit before calling
    cache_key = self._build_cache_key(args, kwargs)
    is_hit = cache_key in self._cache

    result = self._call_impl(*args, **kwargs)

    block = self._cache.get(cache_key)
    if block:
        print(f"[ql.compile] {self._func.__name__}: "
              f"{'cache hit' if is_hit else 'cache miss'} | "
              f"original={block.original_gate_count} → "
              f"optimized={len(block.gates)} gates",
              file=sys.stderr)

    # Update stats
    self._stats = {
        "cache_hit": is_hit,
        "original_gate_count": block.original_gate_count if block else 0,
        "optimized_gate_count": len(block.gates) if block else 0,
        "cache_size": len(self._cache),
    }
    return result
```

### Pattern 3: Nesting via Natural Capture
**What:** Inner compiled function's replay gates are captured by outer function's layer-range extraction
**When to use:** When a compiled function calls another compiled function
**How it works:**
```
Outer capture starts: start_layer = get_current_layer()
  → Inner function called
    → If cached: inject_remapped_gates() → add_gate() → gates land in circuit
    → If not cached: normal execution → gates land in circuit
Outer capture ends: end_layer = get_current_layer()
extract_gate_range(start_layer, end_layer)  # Captures ALL gates including inner's
```
This is the "naturally works" pattern -- inner gates land in the circuit during outer capture, so they are automatically included. The key implementation work is:
1. Depth limit tracking to prevent infinite recursion
2. Ensuring the flat gate list is optimized across inner/outer boundaries

### Anti-Patterns to Avoid
- **Separate inverse cache:** Do NOT maintain a separate cache for inverse blocks. Generate on demand from the existing cached block, optionally cache the result lazily.
- **Re-executing function for inverse:** Do NOT re-run the function body to get the inverse. The inverse is a pure transformation of the cached gate list.
- **Debug overhead when disabled:** Do NOT track stats when `debug=False`. The `.stats` property returns `None` and no tracking code runs.
- **Modifying original block for inverse:** Do NOT mutate the original `CompiledBlock.gates`. Always create a new list for the inverse.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Adjoint gate angle negation | Custom per-gate-type logic | Simple `angle = -angle` for rotation gates, identity for self-adjoint | The C backend already uses this exact approach: `g->GateValue *= pow(-1, 1)` (execution.c:84) |
| Cache hit/miss detection | Separate tracking structure | Check `cache_key in self._cache` before the call | Already have OrderedDict with O(1) lookup |
| Nesting capture | Special capture mode for nested functions | Let inner gates flow through existing `add_gate()` → `extract_gate_range()` | The circuit already captures all gates in a layer range regardless of source |

**Key insight:** The existing capture-replay infrastructure already handles nesting naturally because `inject_remapped_gates()` calls `add_gate()` which puts gates into the circuit, and `extract_gate_range()` reads all gates from the circuit regardless of how they were added.

## Common Pitfalls

### Pitfall 1: Inverse of Controlled Block
**What goes wrong:** Generating inverse of a controlled block without preserving the control qubit mapping
**Why it happens:** The controlled block has a `control_virtual_idx` that must be preserved in the inverse
**How to avoid:** When inverting a controlled block, copy `control_virtual_idx`, `param_qubit_ranges`, `total_virtual_qubits` etc. from the source block. Only transform the `gates` list.
**Warning signs:** Inverse of controlled block fails or produces gates with wrong controls

### Pitfall 2: Measurement Gates in Inverse
**What goes wrong:** Attempting to invert a gate sequence containing measurement gates
**Why it happens:** Measurement is irreversible in quantum computing
**How to avoid:** Check for `_M` (type 9) in gate list before generating inverse. Raise a clear error: "Cannot invert compiled function containing measurement gates"
**Warning signs:** Silent incorrect results if measurement gates are "inverted"

### Pitfall 3: Infinite Recursion in Nested Compilation
**What goes wrong:** Compiled function A calls compiled function B which calls A, causing infinite recursion
**Why it happens:** No depth limit on nested compiled function calls
**How to avoid:** Track nesting depth with a module-level counter. Increment on entry to `_capture()`, decrement on exit. Raise error when depth exceeds limit (e.g., 16).
**Warning signs:** Python stack overflow, extremely long execution times

### Pitfall 4: Double Optimization in Nesting
**What goes wrong:** Inner function's gates were already optimized, but outer function re-optimizes, potentially changing semantics
**Why it happens:** Inner replay injects optimized gates; outer capture optimizes the full flat list again
**How to avoid:** This is actually desired behavior per context decisions: "Optimizer runs on the full flattened gate list -- can optimize across inner/outer function boundaries." No issue here, but be aware that optimization is applied to the combined sequence.
**Warning signs:** None -- this is intentional and correct

### Pitfall 5: Stats Overhead When Debug is Off
**What goes wrong:** Performance degradation from stats tracking even when `debug=False`
**Why it happens:** Checking debug flag on every call adds a branch
**How to avoid:** The debug flag check is a single boolean test -- negligible cost. Do NOT precompute stats or maintain tracking structures when debug is off. `.stats` returns `None` immediately.
**Warning signs:** Measurable overhead in benchmarks when debug=False

### Pitfall 6: Inverse-of-Inverse Round-Trip
**What goes wrong:** `fn.inverse().inverse()` does not equal original
**Why it happens:** Creating a wrapper around a wrapper that accumulates state
**How to avoid:** Track whether a compiled function is already inverted. If `.inverse()` is called on an already-inverted function, return the original. Alternatively, if `.inverse()` produces a new `CompiledFunc`-like object, its `.inverse()` should reverse the reversal.
**Warning signs:** Gate counts differ between original and double-inverse

## Code Examples

### Inverse Generation
```python
# Source: Pattern from c_backend/src/execution.c:57-84

_NON_REVERSIBLE = frozenset({_M})

def _adjoint_gate(gate):
    """Return adjoint of a single gate dict."""
    if gate["type"] in _NON_REVERSIBLE:
        raise ValueError("Cannot invert sequence containing measurement gates")
    adj = dict(gate)
    if gate["type"] in _ROTATION_GATES:
        adj["angle"] = -gate["angle"]
    return adj

def _inverse_gate_list(gates):
    """Adjoint of gate sequence: reverse order, adjoint each gate."""
    return [_adjoint_gate(g) for g in reversed(gates)]
```

### Inverse Method on CompiledFunc
```python
# Returns a callable that replays the inverse sequence
def inverse(self):
    """Return a callable that applies the adjoint of this compiled function."""
    if self._inverse_func is not None:
        return self._inverse_func
    # Lazy: generate on first call
    inv = _InverseCompiledFunc(self)
    self._inverse_func = inv
    return inv
```

### Debug Output
```python
# Pattern from qint.pyx: print(..., file=sys.stderr)
import sys

# In __call__ when debug=True:
print(f"[ql.compile] {self._func.__name__}: "
      f"{'HIT' if is_hit else 'MISS'} | "
      f"original={block.original_gate_count} → "
      f"optimized={len(block.gates)} gates | "
      f"cache_entries={len(self._cache)}",
      file=sys.stderr)
```

### Nesting Depth Tracking
```python
# Module-level counter
_capture_depth = 0
_MAX_CAPTURE_DEPTH = 16

def _capture(self, args, kwargs, quantum_args):
    global _capture_depth
    if _capture_depth >= _MAX_CAPTURE_DEPTH:
        raise RecursionError(
            f"Compiled function nesting depth exceeded {_MAX_CAPTURE_DEPTH}. "
            "Possible circular compiled function calls."
        )
    _capture_depth += 1
    try:
        # ... existing capture logic ...
        pass
    finally:
        _capture_depth -= 1
```

### Comprehensive Test Structure
```python
# Test categories for INF-03:
# 1. Basic capture/replay (existing, Phase 48)
# 2. Different widths/classical args (existing, Phase 48)
# 3. Cache invalidation (existing, Phase 48)
# 4. Optimization (existing, Phase 49)
# 5. Controlled context (existing, Phase 50)
# 6. Inverse generation (NEW)
#    - inverse reverses gate order
#    - inverse negates rotation angles
#    - inverse of self-adjoint gates unchanged
#    - inverse of inverse == original
#    - inverse with controlled context
#    - inverse of empty function
#    - error on measurement gates
# 7. Debug mode (NEW)
#    - debug=True prints to stderr
#    - cache hit/miss reporting
#    - original vs optimized gate counts
#    - .stats property populated when debug=True
#    - .stats returns None when debug=False
# 8. Nesting (NEW)
#    - inner compiled function gates in outer capture
#    - depth limit enforced
#    - nested + inverse composition
#    - nested + controlled composition
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| C-level `reverse_circuit_range` for uncomputation | Python-level gate list reversal for compiled function inverse | Phase 51 | Inverse operates on cached virtual gate lists, not the live circuit |
| No debug introspection | `debug=True` with stderr output + `.stats` property | Phase 51 | Users can inspect compilation behavior without modifying code |
| Flat compilation (no nesting) | Nested compiled functions with depth limit | Phase 51 | Inner compiled function gates inlined into outer capture |

## Open Questions

1. **`.inverse()` return type**
   - What we know: Must return a callable that applies the adjoint sequence. Context says "Claude's discretion on whether `.inverse()` returns a new callable or uses another pattern."
   - Recommendation: Return a lightweight `_InverseCompiledFunc` wrapper that holds a reference to the original `CompiledFunc` and replays the inverted gate list. This avoids duplicating the cache and allows `.inverse().inverse()` to return the original. Could also be a `CompiledFunc` subclass.

2. **`@ql.compile(inverse=True)` eager generation**
   - What we know: Decorator parameter triggers eager inverse generation at capture time.
   - Recommendation: When `inverse=True`, generate the inverse block immediately after capture (inside `_capture_and_cache_both`). Store it as `self._eager_inverse_block`. The `.inverse()` method checks this first.

3. **Nesting: inner function's return value**
   - What we know: Inner compiled function may return a qint that the outer function uses further.
   - What's unclear: If the inner function returns a new qint (not in-place), the outer capture includes those gates and the return qint's physical qubits are valid. This should work naturally since all gate emission goes through `add_gate`.
   - Recommendation: Verify with a test that `outer_fn` calling `inner_fn` where `inner_fn` returns a new qint works correctly.

4. **Debug stats accumulation across calls**
   - What we know: `.stats` exposed for programmatic access.
   - What's unclear: Should `.stats` reflect only the most recent call, or accumulate across calls?
   - Recommendation: Most recent call only (simpler, more useful for debugging). Add `total_hits` and `total_misses` counters for cumulative tracking.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` -- Full implementation of CompiledFunc, CompiledBlock, _optimize_gate_list (731 lines, read in full)
- `c_backend/src/execution.c` -- `reverse_circuit_range()` implementation showing exact adjoint transformation pattern (lines 57-100)
- `src/quantum_language/_core.pyx` -- `extract_gate_range()`, `inject_remapped_gates()`, `reverse_instruction_range()` implementations
- `src/quantum_language/_core.pxd` -- Gate type definitions: `Standardgate_t` enum (X=0, Y=1, Z=2, R=3, H=4, Rx=5, Ry=6, Rz=7, P=8, M=9)
- `tests/test_compile.py` -- Existing 43 tests covering phases 48-50 (1335 lines, read in full)
- `.planning/phases/51-differentiators-polish/51-CONTEXT.md` -- All decisions locked

### Secondary (MEDIUM confidence)
- `src/quantum_language/qint.pyx` lines 414-415, 444-449, 490-492 -- Pattern for `print(..., file=sys.stderr)` usage in the codebase

### Tertiary (LOW confidence)
- None -- all findings based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components are existing codebase elements, no new dependencies
- Architecture: HIGH -- patterns directly derived from existing C and Python implementations
- Pitfalls: HIGH -- identified from concrete code analysis (gate types, recursion paths, cache structure)

**Research date:** 2026-02-04
**Valid until:** 2026-03-06 (30 days -- stable domain, no external dependencies)
