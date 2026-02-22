# Phase 80: Oracle Auto-Synthesis & Adaptive Search - Research

**Researched:** 2026-02-22
**Domain:** Predicate-to-oracle synthesis, BBHT adaptive Grover search
**Confidence:** HIGH

## Summary

Phase 80 adds two capabilities on top of the existing Grover infrastructure (Phases 77-79): (1) predicate-to-oracle auto-synthesis, allowing users to pass Python callables (lambdas, functions, methods) directly to `ql.grover()` instead of writing decorated oracle functions, and (2) BBHT adaptive search for unknown solution count M.

The predicate synthesis uses a **tracing approach**: the predicate is called with real `qint` objects, and existing qint comparison/arithmetic operators capture gates into the circuit. The predicate's return value (a `qbool`) provides the phase-marking target. This reuses the entire `@ql.compile` + `GroverOracle` pipeline -- no AST parsing required. The existing `qint.__and__`, `qint.__or__`, `qint.__invert__` operators already support compound predicates like `(x > 5) & (x < 20)` because `qbool` inherits from `qint`.

The adaptive search implements the BBHT algorithm (Boyer-Brassard-Hoyer-Tapp, 1998): for each attempt `m`, choose random `j` uniformly from `[0, lambda^m)` where `lambda = 6/5`, apply `j` Grover iterations, measure, and classically verify. Expected query count is `O(sqrt(N))` even without knowing `M`.

**Primary recommendation:** Implement predicate-to-oracle synthesis as a wrapper that traces the predicate, extracts the result qbool, applies `with result: x.phase += math.pi`, and wraps the whole sequence with `@ql.compile` + `GroverOracle`. Implement BBHT as a loop around the existing `grover()` single-shot machinery. Both features integrate through the existing `ql.grover()` entry point.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Accept **any callable predicate** -- lambdas, named functions, methods -- not just lambda expressions
- Support **both** register passing styles: explicit register (`ql.grover(lambda x: x > 5, x)`) and width kwarg (`ql.grover(lambda x: x > 5, width=3)`)
- Support **multi-register predicates** (`lambda x, y: x + y == 10`) -- each parameter maps to a separate search register
- Support **closures capturing classical values** -- captured Python ints/floats become classical constants in the oracle circuit (`threshold = 5; lambda x: x > threshold`)
- Conversion uses **tracing approach** -- call predicate with real qint objects, let existing qint operators capture gates. Reuses @ql.compile machinery, no AST parsing.
- Errors surface at circuit-build time (natural consequence of tracing approach)
- **Cache lambda oracles** same as decorated oracles -- per source hash, width, arithmetic mode
- Use **bitwise operators** for composition: `&` (AND), `|` (OR), `~` (NOT)
- Support **arbitrary nesting depth**: `((x > 5) & (x < 20)) | (x == 0)` -- full expression tree from qbool operations
- Support **arithmetic in conditions**: `x * 2 > 10`, `x + y == 15` -- leverages existing qint arithmetic operators
- Support **cross-register comparisons**: `x > y`, `x + y == 10` -- full interaction between search registers
- **NOT/negation** supported via `~` operator on qbool
- qbool gets `__and__`, `__or__`, `__invert__` operators that return new qbool -- enables bitwise syntax naturally
- **Ancilla management fully automatic** -- auto-allocate and uncompute temporaries, user never sees them
- **Soft warning** (not hard error) when predicate + search register approaches qubit budget -- user might target hardware, not simulator
- Uses **BBHT algorithm** (Boyer-Brassard-Hoyer-Tapp) -- each attempt picks random k in [1, 2^j], theoretically optimal
- **Return None** when search exhausts all attempts without finding a solution
- User can set **max_attempts= parameter** with sensible default (e.g., log2(N) attempts)
- **Always verify** found results -- run predicate classically on measured value, retry if not a valid solution
- **Single entry point**: `ql.grover()` handles everything -- lambdas, decorated oracles, adaptive or exact
- **Default to adaptive search** when m= is omitted -- most user-friendly, just works without knowing M
- **Opt out of adaptive** by passing `m=N` explicitly -- providing m= disables adaptive and uses exact iteration count
- **Same return format**: `(value, iterations)` regardless of adaptive or not -- iterations = total across all attempts
- Backwards compatible: existing `ql.grover(oracle, width=3, m=1)` calls continue to work unchanged

### Claude's Discretion
- Exact BBHT implementation details (random seed handling, growth factor)
- Default value for max_attempts
- Internal structure of the predicate-to-oracle wrapper
- How classical verification callback is derived from the predicate
- Cache eviction strategy for lambda oracles

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SYNTH-01 | User can pass Python predicate lambda as oracle (`ql.grover(lambda x: x > 5, x)`) | Tracing approach: call predicate with real qint objects. `inspect.signature` extracts param names (empty annotations treated as quantum by existing `_get_quantum_params`). Wrap traced gates in GroverOracle. See "Predicate-to-Oracle Synthesis" pattern below. |
| SYNTH-02 | Compound predicates compile to valid oracles (`(x > 10) & (x < 50)`) | qbool already inherits `__and__`, `__or__`, `__invert__` from qint. These produce new qint/qbool results with proper gate capture and layer tracking. Compound expressions naturally chain via operator overloading. |
| SYNTH-03 | Predicate oracles work with existing qint comparison operators | All comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`) return qbool. Arithmetic operators (`+`, `-`, `*`) return qint. The tracing approach calls these operators directly, so full compatibility is automatic. |
| ADAPT-01 | When M is unknown, Grover uses exponential backoff strategy | BBHT algorithm: growth factor lambda=6/5, random j in [0, lambda^m), apply j Grover iterations per attempt. Expected O(sqrt(N)) queries. See "BBHT Adaptive Search" pattern below. |
| ADAPT-02 | Adaptive search terminates when solution found or search space exhausted | Classical verification after measurement: call predicate with measured value as Python int. Terminate on valid solution. max_attempts bound ensures termination. Return None if exhausted. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (internal) | current | qint, qbool, compile, oracle, grover | All infrastructure exists; this phase extends it |
| inspect (stdlib) | 3.13 | Lambda/function signature introspection | Already used in grover.py for `_get_quantum_params` |
| math (stdlib) | 3.13 | sqrt, log2, pi for iteration calculations | Already used in grover.py |
| random (stdlib) | 3.13 | BBHT random iteration selection | New dependency but stdlib, zero install |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib (stdlib) | 3.13 | Source hash for cache keys | Already used in oracle.py for `_compute_source_hash` |
| warnings (stdlib) | 3.13 | Soft warning for qubit budget | Already used in qint.pyx |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tracing approach | AST parsing | AST would be more fragile, breaks with closures, C extensions. Tracing reuses all existing operators. **Decision: tracing (locked)**. |
| BBHT | Simple doubling | BBHT has provably optimal O(sqrt(N)) expected queries. Simple doubling is suboptimal. **Decision: BBHT (locked)**. |

**Installation:** No new dependencies required. All from Python stdlib.

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
├── grover.py            # Extended with predicate detection + adaptive loop
├── oracle.py            # Extended with predicate-to-oracle wrapper
├── qint.pyx             # No changes needed (operators already work)
├── qbool.pyx            # No changes needed (inherits &, |, ~ from qint)
├── compile.py           # No changes needed (tracing uses existing capture)
└── __init__.py          # No API surface changes (ql.grover already exported)
```

### Pattern 1: Predicate-to-Oracle Synthesis (Tracing Approach)

**What:** Convert a Python predicate callable into a GroverOracle by calling it with real qint objects and capturing the gates.

**When to use:** When `ql.grover()` receives a callable that is NOT already a `GroverOracle` or `CompiledFunc`.

**Key insight:** The predicate `lambda x: x > 5` when called with a real `qint` argument automatically invokes `qint.__gt__(5)`, which returns a `qbool` and captures all comparison gates into the circuit. We then use that `qbool` for phase marking (`with result: x.phase += math.pi`), producing the complete oracle circuit.

**Example:**
```python
def _predicate_to_oracle(predicate, register_widths):
    """Convert a Python predicate into a GroverOracle.

    1. Introspect predicate to find parameter count
    2. Create a @ql.compile wrapper that:
       a. Accepts qint arguments
       b. Calls predicate(*qint_args) -> returns qbool
       c. Applies phase marking: with result: x.phase += math.pi
    3. Wrap in GroverOracle(validate=False)
    """
    import math
    from .compile import compile as ql_compile

    param_names = list(inspect.signature(predicate).parameters.keys())

    @ql_compile
    def oracle_func(*args):
        # Call predicate with qint args -- tracing captures gates
        result = predicate(*args)
        # Phase-mark the result
        with result:
            args[0].phase += math.pi

    return grover_oracle(oracle_func, validate=False)
```

### Pattern 2: BBHT Adaptive Search Loop

**What:** When M is unknown, run Grover with exponentially increasing iteration counts and random selection per the BBHT algorithm.

**When to use:** When `m=` parameter is NOT provided to `ql.grover()`.

**Reference:** Boyer, Brassard, Hoyer, Tapp. "Tight Bounds on Quantum Searching." 1998.

**Algorithm:**
```python
def _bbht_search(oracle, register_widths, max_attempts, predicate=None):
    """BBHT adaptive Grover search.

    lambda_ = 6/5 (growth factor from BBHT paper)
    For attempt m = 0, 1, 2, ...:
        upper = min(lambda_^m, sqrt(N))
        j = random.randint(0, int(upper) - 1)  # random in [0, upper)
        Run j Grover iterations
        Measure
        Verify classically (call predicate with measured int value)
        If valid: return (value, total_iterations)
    Return None if exhausted
    """
    LAMBDA = 6/5  # BBHT growth factor
    N = 1
    for w in register_widths:
        N *= 2**w
    sqrt_N = math.sqrt(N)

    total_iterations = 0
    for m in range(max_attempts):
        upper = min(LAMBDA ** m, sqrt_N)
        j = random.randint(0, max(1, int(upper)) - 1)

        # Build fresh circuit, run j Grover iterations, simulate
        value = _run_grover_attempt(oracle, register_widths, j)
        total_iterations += j

        # Classical verification
        if predicate is not None:
            if _verify_classically(predicate, value, register_widths):
                return (value, total_iterations)
        else:
            return (value, total_iterations)  # No predicate = trust measurement

    return None  # Exhausted
```

### Pattern 3: Predicate Detection in ql.grover()

**What:** Distinguish between GroverOracle/CompiledFunc (existing path) and raw callables (predicate path).

**When to use:** At the entry point of `ql.grover()`.

**Example:**
```python
def grover(oracle, *args, width=None, widths=None, m=None,
           iterations=None, max_attempts=None):
    # Detect if oracle is a predicate (raw callable, not GroverOracle/CompiledFunc)
    is_predicate = (not isinstance(oracle, (GroverOracle, CompiledFunc))
                    and callable(oracle))

    if is_predicate:
        # Predicate path: synthesize oracle from predicate
        predicate = oracle
        # ... resolve widths, synthesize oracle, possibly use adaptive
    else:
        # Existing path: decorated oracle
        predicate = None  # No classical verification available

    if m is not None:
        # Known M: use exact iteration count (existing path)
        return _exact_grover(oracle, register_widths, m, iterations)
    else:
        # Unknown M: adaptive BBHT search
        return _bbht_search(oracle, register_widths, max_attempts, predicate)
```

### Pattern 4: Classical Verification Derivation

**What:** Derive a classical verification callback from the predicate for post-measurement checking.

**When to use:** During BBHT adaptive search, after each measurement.

**Key insight:** The same predicate that generates the oracle circuit can be called with plain Python integers for classical verification. If `lambda x: x > 5` is the predicate, then `predicate(3)` returns `False` (classically) and `predicate(7)` returns `True`.

**Example:**
```python
def _verify_classically(predicate, measured_values, register_widths):
    """Call predicate with classical int values to verify measurement.

    For single-register: predicate(value) -> bool
    For multi-register: predicate(x_val, y_val) -> bool
    """
    if len(measured_values) == 1:
        return bool(predicate(measured_values[0]))
    return bool(predicate(*measured_values))
```

### Pattern 5: Lambda Oracle Caching

**What:** Cache traced predicate oracles using source hash + closure variable hash + width + arithmetic mode.

**When to use:** Every time a predicate oracle is built.

**Critical insight from research:** `inspect.getsource(lambda x: x > threshold)` returns `'lambda x: x > threshold\n'` regardless of `threshold`'s value. The source hash alone does NOT distinguish closures with different captured values. The cache key must include closure variable values.

**Example:**
```python
def _lambda_cache_key(predicate, register_widths):
    """Build cache key including closure variables."""
    src_hash = _compute_source_hash(predicate)

    # Extract closure variable values
    closure_values = ()
    if hasattr(predicate, '__closure__') and predicate.__closure__:
        closure_values = tuple(
            cell.cell_contents for cell in predicate.__closure__
            if isinstance(cell.cell_contents, (int, float, str, bool))
        )

    arithmetic_mode = 1 if option("fault_tolerant") else 0
    return (src_hash, closure_values, arithmetic_mode, tuple(register_widths))
```

### Anti-Patterns to Avoid

- **AST parsing of predicates:** Do NOT parse the lambda's AST to synthesize gates. This is fragile, breaks with closures, fails with C-extension types, and duplicates existing operator logic. The tracing approach reuses all existing operators naturally.

- **Calling predicate multiple times per attempt:** Each BBHT attempt must build a fresh circuit. Do NOT reuse circuits across attempts -- the circuit state is not resettable mid-search.

- **Skipping classical verification:** BBHT can measure non-solutions (Grover amplification is probabilistic). Always verify with classical callback before returning.

- **Using `with flag: pass` for phase marking:** This is a no-op after compile optimization (compute+uncompute cancel out). Must use `with flag: x.phase += math.pi` for actual phase marking.

- **Modifying the grover() return type:** Existing code returns `(value, iterations)`. The adaptive path must return the same format. When adaptive search fails, return `None` (NOT an empty tuple or exception).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Predicate parameter introspection | Custom arg parser | `inspect.signature(predicate).parameters` | Already used in `_get_quantum_params`, handles lambdas, named functions, methods |
| Gate capture during tracing | Manual gate recording | `@ql.compile` decorator wrapping the traced call | Compile already handles capture, optimization, caching, controlled variants |
| Oracle validation | Custom gate analysis | `GroverOracle` wrapper with `validate=False` | Oracle class handles caching, replay, ancilla management |
| Random number generation for BBHT | Custom RNG | `random.randint()` from stdlib | Standard, seedable, well-tested |
| Ancilla allocation/deallocation | Manual qubit tracking | Existing `_allocate_qubit` / `_deallocate_qubits` + auto-uncomputation | The tracing approach produces qbools that auto-uncompute on scope exit |

**Key insight:** The tracing approach means nearly everything is handled by existing infrastructure. The new code is primarily glue: detecting predicates, wrapping them, and looping for BBHT.

## Common Pitfalls

### Pitfall 1: Closure Cache Key Collision
**What goes wrong:** Two predicate closures with different captured values produce the same cache key because `inspect.getsource()` returns identical source text for both.
**Why it happens:** Source hashing ignores runtime closure state.
**How to avoid:** Include closure variable values in the cache key (see Pattern 5 above). Extract `__closure__` cell contents and hash them alongside the source.
**Warning signs:** Predicate `lambda x: x > 5` and `lambda x: x > 10` (defined from same template) returning same results.

### Pitfall 2: Phase Marking on Wrong Qubit
**What goes wrong:** `with result: pass` is a no-op. The oracle does nothing.
**Why it happens:** `pass` inside a controlled block generates no gates. The comparison compute+uncompute cancel out.
**How to avoid:** Always use `with result: x.phase += math.pi` (or equivalent) for phase marking. This is the pattern established in Phase 79.
**Warning signs:** Grover search returns random values (no amplification).

### Pitfall 3: Circuit State Leaking Between BBHT Attempts
**What goes wrong:** Second BBHT attempt uses stale circuit state from previous attempt.
**Why it happens:** `ql.circuit()` creates a fresh circuit, but any Python-level state (compiled function caches) persists.
**How to avoid:** Call `ql.circuit()` at the start of each BBHT attempt to create a completely fresh circuit. CompiledFunc caches auto-clear via `_register_cache_clear_hook`.
**Warning signs:** Increasing qubit count across attempts, QASM export errors.

### Pitfall 4: BBHT Overrun Beyond sqrt(N)
**What goes wrong:** BBHT applies too many iterations (j > optimal), causing Grover "overrotation" where success probability drops.
**Why it happens:** The upper bound `lambda^m` grows without limit.
**How to avoid:** Cap `j` at `sqrt(N)` (the maximum useful number of Grover iterations). In the BBHT algorithm, `upper = min(lambda^m, sqrt(N))`.
**Warning signs:** Success rate drops after many attempts despite solution existing.

### Pitfall 5: Predicate Returns Non-qbool
**What goes wrong:** User's predicate returns `True`/`False` (Python bool) instead of qbool.
**Why it happens:** Predicate like `lambda x: True` or uses Python-only comparison.
**How to avoid:** Validate that the predicate return is a `qbool` (or at minimum a `qint`) after tracing. Raise clear error if not.
**Warning signs:** TypeError when entering `with result:` context manager.

### Pitfall 6: Multi-Register Predicate Width Mismatch
**What goes wrong:** Predicate has 2 params but user provides 1 width.
**Why it happens:** `width=3` broadcasts to all params. User expected `widths=[3, 4]`.
**How to avoid:** `_resolve_widths` already handles this validation (raises ValueError). No change needed.
**Warning signs:** ValueError at circuit build time (existing behavior).

### Pitfall 7: Qubit Budget Exceeded by Predicate
**What goes wrong:** Complex predicate (e.g., `x * y > 100`) allocates many ancilla qubits, exceeding simulator capacity (17 qubit limit).
**Why it happens:** Multiplication is O(n^2) qubits for ancillas. With two 4-bit registers + multiplication + comparison, qubit count explodes.
**How to avoid:** Emit soft warning (via `warnings.warn`) when total qubit count after predicate tracing approaches budget. Calculate estimated qubit cost: `sum(widths) + predicate_ancilla_estimate`.
**Warning signs:** MemoryError from qubit allocator, simulation hangs.

## Code Examples

Verified patterns from codebase analysis:

### Existing Oracle Pattern (Phase 79)
```python
# Source: src/quantum_language/grover.py, tests/python/test_grover.py
@ql.grover_oracle(validate=False)
@ql.compile
def mark_five(x: ql.qint):
    flag = x == 5
    with flag:
        x.phase += math.pi

value, iters = ql.grover(mark_five, width=3)
```

### Target Lambda Pattern (Phase 80 - SYNTH-01)
```python
# User writes:
value, iters = ql.grover(lambda x: x > 5, width=3)

# Internally becomes:
@ql.compile
def _traced_oracle(x: ql.qint):
    result = (lambda x: x > 5)(x)  # qint.__gt__(5) -> qbool
    with result:
        x.phase += math.pi

oracle = GroverOracle(_traced_oracle, validate=False)
```

### Target Compound Predicate Pattern (Phase 80 - SYNTH-02)
```python
# User writes:
value, iters = ql.grover(lambda x: (x > 10) & (x < 50), width=6)

# Internally traces:
# (x > 10)   -> qbool via qint.__gt__(10)
# (x < 50)   -> qbool via qint.__lt__(50)
# & operator -> qint.__and__  (qbool inherits from qint)
# Final result is a qbool -- used for phase marking
```

### Target Multi-Register Pattern (Phase 80 - SYNTH-01)
```python
# User writes:
x_val, y_val, iters = ql.grover(lambda x, y: x + y == 10, widths=[4, 4])

# Internally:
# inspect.signature extracts param names: ['x', 'y']
# Creates qint(0, width=4) for each
# Traces: x + y -> qint, == 10 -> qbool
# Phase marks with qbool
```

### Target Adaptive Search Pattern (Phase 80 - ADAPT-01, ADAPT-02)
```python
# User writes (no m= parameter):
result = ql.grover(lambda x: x == 42, width=8)
# result is (42, total_iterations) or None

# User can limit attempts:
result = ql.grover(lambda x: x > 100, width=8, max_attempts=20)

# User can opt out of adaptive:
value, iters = ql.grover(lambda x: x > 5, width=3, m=1)
# Uses exact iteration count, no BBHT
```

### Classical Verification Pattern
```python
# After measurement, verify classically:
predicate = lambda x: x > 5
measured_value = 7
assert predicate(measured_value) == True   # Valid solution
measured_value = 3
assert predicate(measured_value) == False  # Invalid, retry
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual oracle decoration required | Lambda predicate auto-synthesis | Phase 80 | Users write `lambda x: x > 5` instead of 10-line decorated function |
| Must know M for ql.grover() | Adaptive BBHT when M unknown | Phase 80 | `ql.grover(oracle, width=3)` just works without specifying m= |
| Phase 79: `with flag: pass` was common but is no-op | Phase 79-02 fix: `with flag: x.phase += math.pi` | Phase 79-02 | Critical for correct oracle synthesis |

**Deprecated/outdated:**
- `with flag: pass` pattern for phase marking -- produces no observable phase flip after compile optimization. Use `with flag: x.phase += math.pi` instead.

## Open Questions

1. **What should max_attempts default to?**
   - What we know: BBHT paper suggests O(sqrt(N)) total iterations. For N=2^n, about n+1 attempts each with up to sqrt(N) iterations.
   - What's unclear: Whether `ceil(log2(N))` or `2*ceil(log2(N))` is the right default.
   - Recommendation: Default to `ceil(2 * log2(N))` -- generous enough to find solutions with high probability, bounded enough to terminate promptly. Claude's discretion per CONTEXT.md.

2. **Should adaptive search be the default when m= is omitted?**
   - What we know: CONTEXT.md says "Default to adaptive search when m= is omitted." This is a locked decision.
   - Impact: This is a **backwards-incompatible change**. Current `ql.grover(oracle, width=3)` assumes `m=1`. New behavior would use adaptive.
   - Recommendation: Since CONTEXT.md locks "Default to adaptive search when m= is omitted", implement this. Existing tests use `m=1` or explicit `iterations=`. The Phase 79 tests already pass `width=3` and get `m=1` from `_grover_iterations(8, 1)` -- but the current `grover()` signature has `m=1` as default. Changing to `m=None` (triggering adaptive) is the intent. Tests that depend on exact iteration count should use explicit `m=` or `iterations=`.

3. **How to handle the `*args` positional register passing?**
   - What we know: CONTEXT.md says support `ql.grover(lambda x: x > 5, x)` with explicit register.
   - What's unclear: The current `grover()` signature is `grover(oracle, *, width=None, ...)` -- keyword-only after oracle. The new signature needs to accept positional qint args after the oracle.
   - Recommendation: Change signature to `grover(oracle, *registers, width=None, widths=None, m=None, ...)`. If `registers` are provided, extract widths from them. If not, use `width=`/`widths=` kwargs.

4. **Closure variable serialization for cache key**
   - What we know: `inspect.getsource` doesn't include closure values. Cache key needs closure variable values.
   - What's unclear: What types of closure variables to include (only primitives? objects?)
   - Recommendation: Include `int`, `float`, `str`, `bool` closure values in cache key. Ignore complex objects (they don't affect the circuit anyway since tracing evaluates them).

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/quantum_language/grover.py` -- existing `ql.grover()` implementation (lines 268-362)
- Codebase analysis: `src/quantum_language/oracle.py` -- existing `GroverOracle` class and caching
- Codebase analysis: `src/quantum_language/compile.py` -- `CompiledFunc` capture/replay machinery
- Codebase analysis: `src/quantum_language/qint_comparison.pxi` -- comparison operators returning qbool
- Codebase analysis: `src/quantum_language/qint_bitwise.pxi` -- `__and__`, `__or__`, `__invert__` operators
- Codebase analysis: `src/quantum_language/qbool.pyx` -- qbool inherits from qint (has all operators)
- Python stdlib `inspect` module: `inspect.signature()` works with lambdas (verified experimentally)

### Secondary (MEDIUM confidence)
- [Boyer, Brassard, Hoyer, Tapp. "Tight Bounds on Quantum Searching." arXiv:quant-ph/9605034 (1998)](https://arxiv.org/abs/quant-ph/9605034) -- BBHT algorithm: lambda=6/5 growth factor, random j in [0, lambda^m), O(sqrt(N/t)) expected queries
- [Grover's algorithm - Wikipedia](https://en.wikipedia.org/wiki/Grover's_algorithm) -- general reference for iteration formulas

### Tertiary (LOW confidence)
- Lambda source hashing behavior: experimentally verified that `inspect.getsource()` returns identical text for closures with different captured values. This is a critical finding for cache key design.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist in codebase, no new dependencies
- Architecture: HIGH -- tracing approach is natural extension of existing @ql.compile machinery; BBHT is well-documented algorithm
- Pitfalls: HIGH -- identified from direct codebase analysis (closure caching, pass no-op, circuit state leaking)
- BBHT algorithm details: MEDIUM -- lambda=6/5 from paper abstract/secondary sources; full paper not parsed

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain, no external dependency changes expected)
