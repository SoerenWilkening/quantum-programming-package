# Phase 94: Parametric Compilation - Research

**Researched:** 2026-02-25
**Domain:** Quantum function compilation / caching / parametric replay
**Confidence:** HIGH

## Summary

Phase 94 adds parametric compilation to the existing `@ql.compile` decorator. The current compile infrastructure (`src/quantum_language/compile.py`) already captures gate sequences and replays them with qubit remapping. The cache key currently includes `(classical_args, widths, control_count, qubit_saving)` -- meaning different classical argument values produce separate cache entries. Parametric compilation changes this: when `parametric=True`, classical arguments that only affect gate *parameters* (angles, rotation values) but not gate *topology* (which gates exist, their target/control qubits) should be treated as "parametric" -- the cached gate sequence is reused with substituted parameter values.

The key technical challenge is distinguishing "classical" parameters (which affect only gate angles/values) from "structural" parameters (which affect which gates are emitted, e.g., Toffoli CQ operations where the classical value determines gate topology). The CONTEXT.md decisions specify automatic detection of classical vs structural parameters, with ambiguous cases falling back to per-value caching for correctness.

**Primary recommendation:** Implement parametric mode as an extension to `CompiledFunc`, adding a `parametric=True` flag that changes cache key construction (excluding classical args) and stores a gate template with placeholder angle values that are substituted during replay. The cache key must also include `arithmetic_mode`, `cla_override`, and `tradeoff_policy` for FIX-04.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Parametric mode activated via flag on existing decorator: `@ql.compile(parametric=True)`
- When combined with `@ql.grover_oracle`, oracle wins -- forces per-value caching silently (oracle parameters are structural by nature)
- Minimal introspection: only `.is_parametric` property exposed on compiled functions
- If function has no classical arguments, `parametric=True` is a silent no-op -- behaves as normal compile
- Silent invalidation: cache key includes `arithmetic_mode`, `cla_override`, `tradeoff_policy` -- switching modes causes a cache miss and transparent re-capture
- In-memory only cache, no disk persistence
- Unbounded cache size within session (circuits are typically few, sessions are finite)
- Toffoli CQ fallback documented in `@ql.compile` docstring only (no separate design doc)
- Automatic detection of classical vs structural parameters -- compiler analyzes which params affect gate structure vs just gate arguments
- Fresh circuit returned each replay (no mutation of cached circuit objects)
- Toffoli CQ fallback to per-value caching is silent -- user gets correct results, documented in docstring
- Fixed-shape inputs only -- changing argument count/types is structural, triggers re-capture
- Ambiguous parameters fall back to per-value caching (correctness over speed)
- Type changes between calls (e.g., int then float) trigger re-capture and cache both versions
- `.clear_cache()` method exposed on compiled functions for manual cache invalidation
- Replay correctness verification is test-time only -- no runtime overhead for users

### Claude's Discretion
- Internal cache data structure and key hashing approach
- Exact algorithm for detecting classical vs structural parameters
- How fresh circuits are constructed from cached gate sequences
- Test structure and specific test cases for verification

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PAR-01 | User can decorate with @ql.compile(parametric=True) to enable parametric mode | Extend `compile()` API to accept `parametric` kwarg, pass to `CompiledFunc.__init__` |
| PAR-02 | Parametric functions replay with different classical values without re-capture | Gate template storage with angle substitution during replay; structural detection on first capture |
| PAR-03 | Toffoli CQ operations fall back to per-value caching with documentation | Detect structural parameters during capture by comparing gate topology across trial values |
| PAR-04 | Oracle decorator forces per-value caching for structural parameters | `grover_oracle` decorator sets a flag that forces `parametric=False` behavior |
| FIX-04 | Compile cache key includes arithmetic_mode, cla_override, and tradeoff_policy | Add mode flags to cache key tuple in `CompiledFunc.__call__` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (this project) | current | Compile decorator infrastructure | Existing `compile.py` is the foundation |
| numpy | existing | Qubit array construction | Already used by compile.py for `np.zeros(64, dtype=np.uint32)` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Qiskit AerSimulator | existing | Test verification via simulation | Verify parametric replay produces correct results |

### Alternatives Considered
None -- this is entirely an extension of the existing compile infrastructure.

## Architecture Patterns

### Current Compile Architecture (compile.py)

```
@ql.compile decorator
    -> CompiledFunc.__init__(func, max_cache, key, verify, optimize, inverse, debug)
    -> CompiledFunc.__call__(*args, **kwargs)
        1. _classify_args() -> (quantum_args, classical_args, widths)
        2. Build cache_key = (classical_args, widths, control_count, qubit_saving)
        3. Cache hit? -> _replay(cached_block, quantum_args)
        4. Cache miss? -> _capture_and_cache_both(...)
            a. _capture() -> CompiledBlock with virtual gate sequence
            b. _optimize_gate_list() -> cancel/merge adjacent gates
            c. _derive_controlled_block() -> controlled variant
            d. Store both in self._cache[key]
```

### Pattern 1: Parametric Cache Key Strategy

**What:** The parametric cache key excludes classical args but includes mode flags.

**Current key:** `(tuple(classical_args), tuple(widths), control_count, qubit_saving)`

**Parametric key (proposed):** `(tuple(widths), control_count, qubit_saving, arithmetic_mode, cla_override, tradeoff_policy)`

The classical args are excluded from the key. Instead, a "gate template" is stored that records which gate angles depend on which classical argument indices.

**FIX-04 key (non-parametric, also needed):** `(tuple(classical_args), tuple(widths), control_count, qubit_saving, arithmetic_mode, cla_override, tradeoff_policy)`

### Pattern 2: Structural Parameter Detection

**What:** On first capture, determine if classical parameters affect only gate angles (parametric-safe) or gate topology (structural).

**Algorithm:**
1. First call: capture gate sequence normally, recording which classical args produced which gate angles
2. For each gate in captured sequence, record: gate type, target qubit, control qubits (topology) and angle values (parameters)
3. Build a "gate template" where angles that came from classical args are marked as "parametric slots"
4. On second call with different classical args: capture again, compare topology (gate types, targets, controls, gate count)
5. If topology matches: the classical args are parametric -- store the template, enable fast replay
6. If topology differs: the classical args are structural -- fall back to per-value caching

**Simpler alternative (recommended):** Since the current cache already stores virtual gate sequences as dicts, we can:
1. On first parametric call: capture normally, store the gate sequence
2. On second parametric call with different classical values: capture again, compare gate count + types + targets + controls
3. If they match: the function is parametric -- future calls substitute angles only
4. If they don't match: the function is structural -- disable parametric mode for this function, fall back to per-value caching

This "two-capture probe" approach is simple, reliable, and handles all edge cases including Toffoli CQ.

### Pattern 3: Mode Flag Cache Key (FIX-04)

**What:** Include `arithmetic_mode`, `cla_override`, and `tradeoff_policy` in ALL compile cache keys.

**Why:** Currently the compile cache key does NOT include these flags. If a user changes `ql.option('fault_tolerant', True)` or `ql.option('tradeoff', 'min_depth')` between calls to the same compiled function, the stale cached gates would be replayed incorrectly.

**How:** In `CompiledFunc.__call__`, read the current mode flags from the circuit struct (via `option()`) and include them in the cache key tuple.

### Anti-Patterns to Avoid
- **Don't try to statically analyze function source for parametric detection** -- functions may call other functions, use conditionals on classical values, etc. Runtime probing (two-capture) is the only reliable approach.
- **Don't mutate cached gate dicts** -- always create fresh copies when substituting angles during parametric replay.
- **Don't assume all rotation angles come from classical args** -- some may be constants (pi, pi/2, etc.) hardcoded in the function.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate sequence storage | New data structure | Existing `CompiledBlock` | Already handles virtual qubits, ancilla tracking, controlled variants |
| Cache invalidation | Custom invalidation | Extend existing `_clear_all_caches` | Already hooked into `ql.circuit()` reset |
| Oracle caching | Separate oracle parametric cache | `GroverOracle._cache` + force per-value key | Oracle already has its own cache with source hash + arithmetic_mode |

## Common Pitfalls

### Pitfall 1: Toffoli CQ Gate Topology Depends on Classical Value
**What goes wrong:** CQ (classical-quantum) operations like `x += 5` vs `x += 7` produce different gate sequences because Toffoli CQ encodes the classical value into the gate topology (which bits get X gates).
**Why it happens:** The C backend's `_add_toffoli_cq()` emits different gates depending on which bits of the classical value are set.
**How to avoid:** The two-capture probe detects this automatically -- different topology on second capture triggers structural fallback.
**Warning signs:** Test with Toffoli CQ operations (e.g., `x += classical_val`) to verify fallback works.

### Pitfall 2: Mode Flag Change Between Captures
**What goes wrong:** If `arithmetic_mode` changes between the first and second parametric capture, the topology comparison fails spuriously.
**Why it happens:** Different arithmetic modes produce completely different gate sequences (QFT vs Toffoli).
**How to avoid:** Include mode flags in the parametric cache key so mode changes cause a clean cache miss, not a topology mismatch.
**Warning signs:** Tests that change `ql.option('fault_tolerant', ...)` between calls to parametric functions.

### Pitfall 3: Controlled Context Interaction
**What goes wrong:** Parametric function called inside `with qbool:` (controlled context) has different gate count than uncontrolled.
**Why it happens:** Current code derives controlled variant by adding control to each gate, changing gate count.
**How to avoid:** The controlled variant is derived from the uncontrolled block, not captured separately. Parametric mode should only probe the uncontrolled path for topology comparison.
**Warning signs:** Controlled parametric calls failing to match topology.

### Pitfall 4: Oracle Decorator Must Override Parametric
**What goes wrong:** `@ql.grover_oracle` combined with `@ql.compile(parametric=True)` uses parametric caching, but oracle parameters (like the search target) are structural.
**Why it happens:** Oracle auto-synthesis (predicate tracing) produces different gate topology for different predicates.
**How to avoid:** `grover_oracle` decorator should force `parametric=False` on the underlying `CompiledFunc`, or bypass parametric logic entirely.
**Warning signs:** Oracle returning wrong results when called with different search targets.

## Code Examples

### Current Cache Key Construction (compile.py line 603-608)
```python
# Current implementation
qubit_saving = _get_qubit_saving_mode()
if self._key_func:
    cache_key = (self._key_func(*args, **kwargs), control_count, qubit_saving)
else:
    cache_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving)
```

### Proposed Mode-Aware Cache Key (FIX-04)
```python
from ._core import option

# Read current mode flags
arithmetic_mode = 1 if option("fault_tolerant") else 0
cla_override = 1 if not option("cla") else 0
tradeoff_policy = option("tradeoff")

mode_flags = (arithmetic_mode, cla_override, tradeoff_policy)

if self._key_func:
    cache_key = (self._key_func(*args, **kwargs), control_count, qubit_saving) + mode_flags
else:
    cache_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving) + mode_flags
```

### Proposed Parametric Cache Key
```python
if self._parametric:
    # Exclude classical_args from key -- topology should be identical
    parametric_key = (tuple(widths), control_count, qubit_saving) + mode_flags
else:
    parametric_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving) + mode_flags
```

### Two-Capture Probe for Structural Detection
```python
def _probe_parametric(self, first_block, args, kwargs, quantum_args, classical_args):
    """Compare two captures to detect if classical args are structural."""
    # first_block already captured with first set of classical args
    # Now we need a second capture with the SAME quantum args but
    # the function body may reference classical args differently.
    #
    # Compare: gate count, gate types, gate targets, gate controls
    # If all match -> parametric safe
    # If any differ -> structural, fall back to per-value caching

    first_topology = [(g["type"], g["target"], tuple(g["controls"])) for g in first_block.gates]
    # second capture would produce second_topology
    # return first_topology == second_topology
```

### Parametric Replay with Angle Substitution
```python
def _parametric_replay(self, template_block, classical_args, quantum_args):
    """Replay parametric template with new angle values."""
    # Template block stores gate sequence with angle slots
    # For non-rotation gates (X, Y, Z, H): no angles to substitute
    # For rotation gates (P, Rx, Ry, Rz, R): substitute angle from new capture
    #
    # Simple approach: re-capture to get new angles, then inject template
    # topology with new angles. This avoids needing to track which args
    # map to which angles.
```

## Open Questions

1. **Two-capture probe cost**
   - What we know: First call always captures normally. Second call needs to capture again to compare topology.
   - What's unclear: After the probe succeeds, should we store only the topology template, or keep both captured blocks?
   - Recommendation: Keep the template from first capture. On probe success, mark function as parametric. Future calls build gate list by re-executing function body to get new angles, then verify topology matches and use the new gate list directly. This avoids needing a separate "angle substitution" mechanism -- just capture and skip the optimization step since topology is known-good.

2. **Alternative to two-capture: single-capture with angle tracking**
   - What we know: During capture, we could track which gate angles came from classical args by comparing angle values to classical arg values.
   - What's unclear: Classical args may undergo arithmetic before becoming angles (e.g., `angle = 2 * pi / n`), making direct value comparison unreliable.
   - Recommendation: Use two-capture probe (simpler, more robust). The re-capture cost is acceptable since parametric benefits only manifest after the probe phase.

3. **Optimal approach: always re-capture but skip cache key classical args**
   - What we know: The simplest parametric implementation is: use a topology-only cache key, always re-capture on miss, but on hit check if stored topology matches current topology. If yes, use current capture's gates directly.
   - What's unclear: This doesn't actually save the capture cost -- it only saves the cache lookup.
   - Recommendation: Actually, the real benefit of parametric is NOT skipping capture -- it's having a single cache entry for all classical values instead of N entries. Combined with FIX-04 mode flags, this prevents stale cache hits. The "skip re-capture" optimization can come later.

   **REVISED understanding:** Re-reading CONTEXT.md: "replay with different classical values without re-capture". So the explicit goal IS to skip re-capture. This means we need the angle substitution approach or a fast-path that reconstructs gates from the template. The two-capture probe establishes safety, then future calls use the template with angle substitution.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` -- Full compile infrastructure, CompiledFunc, CompiledBlock, cache key construction
- `src/quantum_language/oracle.py` -- GroverOracle with arithmetic_mode-aware caching
- `src/quantum_language/_core.pyx` -- option() API, arithmetic_mode, cla_override, tradeoff_policy state
- `src/quantum_language/_core.pxd` -- C struct fields: arithmetic_mode, cla_override, tradeoff_auto_threshold, tradeoff_min_depth

### Secondary (MEDIUM confidence)
- `tests/test_compile.py` -- Existing compile tests showing cache behavior patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- this is entirely within the existing codebase
- Architecture: HIGH -- compile.py structure is well-understood, extension points are clear
- Pitfalls: HIGH -- Toffoli CQ topology dependence is documented in STATE.md and verified in codebase

**Research date:** 2026-02-25
**Valid until:** N/A (internal codebase research)
