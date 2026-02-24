# Architecture Research: v5.0 Advanced Arithmetic & Compilation

**Domain:** Quantum programming framework -- modular Toffoli arithmetic, parametric compilation, depth/ancilla tradeoff, quantum counting
**Researched:** 2026-02-24
**Confidence:** HIGH (codebase-verified integration points, algorithm design from literature)

## System Overview: Current Architecture

```
+------------------------------------------------------------------+
|                    Python Frontend (ql.*)                          |
|  +-----------+  +----------+  +---------+  +---------+  +-------+ |
|  | qint      |  | qint_mod |  | compile |  | grover  |  | amp   | |
|  | qbool     |  | (v1.0)   |  | (v2.0)  |  | (v4.0)  |  | est   | |
|  | qarray    |  |          |  |         |  |         |  | (v4.0)| |
|  +-----------+  +----------+  +---------+  +---------+  +-------+ |
|       |              |             |            |            |     |
+-------+--------------+-------------+------------+------------+----+
|                    Cython Bindings                                 |
|  +----------+  +----------+  +---------+  +----------+            |
|  | _core.pyx|  | qint.pyx |  |_gates.pyx| |openqasm  |           |
|  | (circuit)|  | (arith)  |  |(emit_*)  | |(.pyx)    |           |
|  +----------+  +----------+  +---------+  +----------+            |
+-------------------------------------------------------------------+
|                    C Backend                                       |
|  +-------------+  +----------------+  +------------+  +----------+|
|  | hot_path_   |  | ToffoliAddition|  | circuit.h  |  | qubit_  ||
|  | add/mul/xor |  | CDKM/CLA/Mul  |  | (circuit_t)|  | allocator||
|  +-------------+  +----------------+  +------------+  +----------+|
|  +-------------+  +----------------+  +------------+              |
|  | arithmetic_ |  | execution.c    |  | sequences/ |              |
|  | ops.h (QFT) |  | run_instruction|  | (hardcoded)|              |
|  +-------------+  +----------------+  +------------+              |
+-------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Relevant to v5.0 |
|-----------|----------------|-------------------|
| `qint_mod.pyx` | Modular arithmetic via `_reduce_mod` conditional subtraction | **MODIFY**: Replace QFT-based modular ops with Toffoli-native C calls |
| `compile.py` | Gate capture/replay with cache keyed on `(classical_args, widths, control, qubit_saving)` | **MODIFY**: Add parametric placeholder support |
| `grover.py` | Grover search with BBHT adaptive and exact-M modes | **EXTEND**: Add `count_solutions` wrapper |
| `amplitude_estimation.py` | IQAE (Grinko et al.) with multi-shot simulation | **REUSE**: Core engine for quantum counting |
| `hot_path_add_toffoli.c` | CLA/RCA dispatch based on `cla_override`, `qubit_saving` fields | **MODIFY**: Add automatic tradeoff logic |
| `circuit.h` (`circuit_t`) | Circuit struct with `arithmetic_mode`, `cla_override`, `qubit_saving` | **EXTEND**: Add tradeoff policy field |
| `_core.pyx` | Global circuit state, option(), allocator access | **EXTEND**: Expose tradeoff option |

## New Components and Integration Points

### Feature 1: Modular Toffoli Arithmetic (FTE-02)

**What changes:** The current `qint_mod` class (v1.0) performs modular reduction via `_reduce_mod`, which uses the generic `__add__`/`__sub__`/`>=` operators. Those operators dispatch to QFT or Toffoli based on `circuit.arithmetic_mode`. The problem is that `_reduce_mod` is broken (BUG-MOD-REDUCE) -- the conditional subtraction loop creates orphan temporaries and result corruption.

**Architecture decision: Beauregard-style modular adder at C level.**

Instead of fixing `_reduce_mod` in Python (which stacks generic operations creating excessive ancilla), implement a dedicated Toffoli modular adder in C that uses the well-known Beauregard/VBE pattern:

```
modular_add(a, b, N):
  1. b += a                    (Toffoli QQ add)
  2. b -= N                    (Toffoli CQ sub -- N is classical)
  3. ancilla = MSB(b)          (borrow/carry flag -- already in result)
  4. if ancilla: b += N        (Toffoli cCQ add, controlled on MSB)
  5. b -= a                    (Toffoli QQ sub -- undo step 1)
  6. ancilla_restore = MSB(b)  (restore ancilla to |0> via CNOT)
  7. b += a                    (redo addition)
```

This is 5 additions/subtractions (3 QQ, 2 CQ) sharing the same ancilla qubit. The key advantage over the Python `_reduce_mod` approach: no comparison operator (which allocates temporary qbools and creates uncomputation nightmares), just MSB inspection of the subtraction result.

**New files:**
- `c_backend/src/ToffoliModularArithmetic.c` -- Beauregard modular add/sub/mul
- `c_backend/include/toffoli_modular_ops.h` -- API declarations

**Modified files:**
- `qint_mod.pyx` -- Replace `_reduce_mod` with C-level modular operations
- `qint_mod.pxd` -- Add cdef declarations for new Cython wrappers
- `setup.py` -- Add new C source to build

**Integration point:** The C modular adder calls `toffoli_QQ_add`/`toffoli_CQ_add`/`toffoli_cCQ_add` internally (already implemented in v3.0). It composes them into the Beauregard sequence. The Python `qint_mod` class calls through Cython to the C modular adder instead of stacking Python-level operations.

**Qubit layout for modular add (b += a mod N):**

```
[0..n-1]        = register a (source, preserved)
[n..2n-1]       = register b (target, gets a+b mod N)
[2n]            = carry/borrow ancilla (shared across all 5 sub-operations)
[2n+1..3n]      = temp register (for CQ operations that need temp)
```

Total ancilla: 1 carry + n temp = n+1 ancilla qubits for n-bit modular addition. Compare to the current Python approach which creates 4n+ qubits via intermediate temporaries.

**Why this works with existing architecture:** The existing Toffoli adder functions accept qubit arrays and width parameters. The modular adder calls them in sequence with different qubit array subsets. No changes to the adder functions themselves. The `allocator_alloc`/`allocator_free` pattern for ancilla is already used throughout `hot_path_add_toffoli.c`.

**Modular multiplication** builds on modular addition:

```
modular_mul(x, a, N):   // x *= a mod N (a is classical)
  result = |0>
  for bit j in binary(a):
    if bit j == 1:
      modular_add(x << j, result, N)
  swap(x, result)
  modular_add_inverse(result, ..., N)  // uncompute result register
```

This is the standard shift-and-add approach where each partial product is a modular addition. The existing `toffoli_mul_cq` uses the same shift-and-add pattern but without modular reduction.

**Controlled modular operations** (needed for Shor's modular exponentiation): Add an external control qubit to the Beauregard sequence. The CQ steps become cCQ, the QQ steps become cQQ. The existing controlled Toffoli adders (`toffoli_cQQ_add`, `toffoli_cCQ_add`) already support this.

### Feature 2: Parametric Compilation (PAR-01, PAR-02)

**What changes:** Currently, `@ql.compile` creates a separate cache entry for each distinct `classical_args` tuple. If you call `f(x, 5)` and then `f(x, 7)`, the second call triggers a full re-capture because the classical argument changed. For Shor's algorithm, modular exponentiation calls the modular multiplier with many different classical values -- re-capturing for each is expensive.

**Architecture decision: Deferred classical substitution in gate lists.**

The compile system captures gate sequences as Python dicts with virtual qubit indices. For parametric compilation, classical arguments are stored as symbolic placeholders in the captured gate list, and substitution happens during replay.

**How it works:**

1. During capture, the function is invoked once with a representative classical value (the first call's value). This produces the real gate sequence.
2. The captured sequence is analyzed: gates that originated from CQ operations are tagged with a `DeferredCQOp` marker recording the operation type, bit width, and which parameter provided the classical value.
3. On replay with a different classical value, normal gates are replayed as-is, but `DeferredCQOp` markers trigger fresh CQ sequence generation with the new value.
4. Cache key omits `classical_args`, so one capture serves all classical values of the same width.

**The challenge:** CQ (classical-quantum) operations in the C backend generate value-dependent gate sequences. A `CQ_add(bits=4, value=5)` produces a completely different Toffoli sequence than `CQ_add(bits=4, value=7)` (different X gates for different bit patterns). This means parametric compilation cannot simply cache gate dicts and substitute values.

**Solution approach: Two-level parametric.**

Level 1 (rotation parametric): For QFT-based CQ operations where the classical value only affects rotation angles, store the angle formula as a function of the parameter. On replay, compute angles from the new classical value. Each rotation's angle is `2*pi*value / 2^k` for position k.

Level 2 (operation-level parametric): For Toffoli CQ operations where the classical value determines which gates exist (X gates for bit initialization), store the operation as a "deferred CQ" node in the gate list. On replay, regenerate the CQ sequence fresh with the new value but skip all the overhead of capture (function re-execution, qubit mapping, optimization).

**Modified files:**
- `compile.py` -- Add `parametric=True` option, placeholder types, two-level replay
- No C changes needed -- the C functions already accept value parameters

**New classes in compile.py:**

```python
class ParametricPlaceholder:
    """Represents a deferred classical value in a compiled gate list."""
    def __init__(self, param_index: int, transform=None):
        self.param_index = param_index
        self.transform = transform  # e.g., lambda v: 2*pi*v/N for QFT angles

class DeferredCQOp:
    """Represents a Toffoli CQ operation with deferred classical value."""
    def __init__(self, op_type, bits, param_index, qubit_mapping):
        self.op_type = op_type  # 'add', 'sub', 'mul'
        self.bits = bits
        self.param_index = param_index
        self.qubit_mapping = qubit_mapping
```

**Cache key change:**

```python
# Current: re-captures for each classical value
cache_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving)

# Parametric: one capture for all classical values of same width
cache_key = (tuple(widths), control_count, qubit_saving, True)  # True = parametric
```

**Integration with existing compile system:** The parametric mode is opt-in via `@ql.compile(parametric=True)`. The existing non-parametric mode remains unchanged. During `_capture`, when `parametric=True`, the system records which gates correspond to CQ operations involving classical parameters. The `_replay` method checks for deferred nodes and resolves them against actual classical arguments.

**Key constraint:** Parametric compilation requires that the circuit topology (which operations, in which order, on which qubits) is identical across all classical values. This holds for modular arithmetic where the structure is always "5 adder calls in Beauregard sequence" regardless of N, but would NOT hold for operations where classical values affect control flow (e.g., variable-length loops). The decorator should validate this assumption or document it clearly.

### Feature 3: Automatic Depth/Ancilla Tradeoff (OPT-01)

**What changes:** Currently, the CLA/RCA selection is controlled by two circuit-level flags:
- `circuit.cla_override = 0` (auto) or `1` (force RCA)
- `circuit.qubit_saving = 0` (prefer KS CLA, more ancilla, lower depth) or `1` (prefer BK CLA, fewer ancilla)

The threshold `CLA_THRESHOLD = 2` is hardcoded in `hot_path_add_toffoli.c`. There is no automatic selection based on actual resource constraints.

**Architecture decision: Policy-based dispatch at C level.**

Add a tradeoff policy to `circuit_t` that the dispatch logic in `hot_path_add_toffoli.c` consults:

```c
typedef enum {
    TRADEOFF_AUTO = 0,      // Select based on available qubits and width
    TRADEOFF_MIN_DEPTH = 1, // Always prefer CLA (more ancilla, lower depth)
    TRADEOFF_MIN_QUBITS = 2 // Always prefer RCA (fewer ancilla, higher depth)
} tradeoff_policy_t;
```

**Decision logic for TRADEOFF_AUTO:**

```c
// In hot_path_add_toffoli.c, replacing hardcoded CLA dispatch:
if (policy == TRADEOFF_AUTO) {
    int cla_ancilla = compute_cla_ancilla_count(circ, result_bits);
    int rca_ancilla = 1;  // CDKM uses 1 ancilla

    // CLA depth is O(log n), RCA depth is O(n)
    // CLA is worth it when: width >= threshold AND ancilla available
    int available = allocator_available(circ->allocator);
    if (result_bits >= CLA_THRESHOLD && cla_ancilla <= available) {
        // Use CLA (try BK, which is the only implemented variant)
    } else {
        // Fall back to RCA
    }
} else if (policy == TRADEOFF_MIN_DEPTH) {
    // Try CLA unconditionally (fail to RCA only if allocation fails)
} else {  // TRADEOFF_MIN_QUBITS
    // Force RCA, skip CLA entirely
}
```

**Modified files:**
- `c_backend/include/circuit.h` -- Add `tradeoff_policy_t` enum and field to `circuit_t`
- `c_backend/src/hot_path_add_toffoli.c` -- Replace hardcoded CLA dispatch with policy-based
- `c_backend/include/qubit_allocator.h` -- Add `allocator_available()` query if not present
- `c_backend/src/qubit_allocator.c` -- Implement `allocator_available()`
- `_core.pyx` -- Expose `ql.option('tradeoff', 'auto'|'min_depth'|'min_qubits')`
- `c_backend/src/circuit_allocations.c` -- Initialize new field in `init_circuit()`

**Integration:** This is a minimal change. The existing dispatch in `hot_path_add_toffoli.c` already has the CLA-try-then-RCA-fallback pattern. The tradeoff policy makes the decision criteria configurable rather than hardcoded. The `allocator_available()` function simply returns `allocator->capacity - allocator->next_free` (or equivalent), which is O(1).

**Why this is the right abstraction level:** Users should not need to understand BK vs KS vs CDKM. They care about "minimize depth" vs "minimize qubits" vs "let the system decide." The policy maps cleanly to the existing dispatch:

| Policy | BK CLA | KS CLA | CDKM RCA |
|--------|--------|--------|----------|
| AUTO | Try if ancilla available | Try if available (stub today) | Fallback |
| MIN_DEPTH | Prefer KS then BK (lowest depth) | Primary choice when implemented | Last resort |
| MIN_QUBITS | Skip | Skip | Always |

Note: KS CLA is currently a stub (returns NULL). AUTO and MIN_DEPTH currently degrade to BK CLA, then RCA. When KS is implemented, the policy layer naturally routes to it without API changes.

### Feature 4: Quantum Counting (GADV-01)

**What changes:** The system already has `ql.grover()` (search for solutions) and `ql.amplitude_estimate()` (estimate probability). Quantum counting answers: "How many solutions exist?" This is the standard Brassard-Hoyer-Tapp quantum counting algorithm, which uses amplitude estimation to determine M from the estimated amplitude.

**Architecture decision: Thin wrapper over `amplitude_estimate()`.**

Quantum counting is mathematically: `M = N * sin^2(theta)` where `theta` comes from amplitude estimation. The existing IQAE implementation already estimates `a = sin^2(theta)` (the success probability). Quantum counting simply multiplies by N.

**New files:**
- `src/quantum_language/counting.py` -- `count_solutions()` function and `CountResult` class

**Implementation sketch:**

```python
class CountResult:
    """Result of quantum counting with integer count and metadata."""
    def __init__(self, count, estimate, confidence_interval, num_oracle_calls):
        self.count = count                       # int: rounded M estimate
        self.estimate = estimate                 # float: raw fraction M/N
        self.confidence_interval = confidence_interval  # (low_count, high_count)
        self.num_oracle_calls = num_oracle_calls # int: total queries used

def count_solutions(oracle, *, width=None, widths=None, epsilon=0.5,
                    confidence_level=0.95, max_iterations=None):
    """Estimate the number of solutions to a search problem.

    Uses IQAE to estimate the fraction of marked states,
    then multiplies by the search space size N.
    """
    # Resolve register widths (reuse grover.py helpers)
    register_widths = _resolve_register_widths(oracle, width, widths)
    N = 1
    for w in register_widths:
        N *= 2 ** w

    # Convert count-space epsilon to probability-space epsilon
    prob_epsilon = epsilon / N

    # Run existing IQAE
    result = amplitude_estimate(
        oracle, width=width, widths=widths,
        epsilon=prob_epsilon,
        confidence_level=confidence_level,
        max_iterations=max_iterations
    )

    # Convert probability to count
    count = round(result.estimate * N)
    ci_low = round(result.confidence_interval[0] * N)
    ci_high = round(result.confidence_interval[1] * N)

    return CountResult(count, result.estimate, (ci_low, ci_high),
                       result.num_oracle_calls)
```

**Modified files:**
- `src/quantum_language/__init__.py` -- Add `count_solutions` to imports and `__all__`

**Integration:** This is the simplest of the four features. It adds no new C code, no new Cython bindings, and no modifications to existing components. It wraps the existing amplitude estimation infrastructure with a count-oriented API.

## Data Flow Changes

### Current Data Flow (arithmetic)

```
Python: x += 5
  |
  v
qint.__iadd__(self, 5)
  |
  v
qint.addition_inplace(self, 5)  [qint_arithmetic.pxi]
  |
  v (C call via nogil)
hot_path_add_cq(circ, qubits, bits, value=5, ...)  [hot_path_add.c]
  |
  v (dispatch)
circ->arithmetic_mode == ARITH_TOFFOLI?
  YES --> toffoli_dispatch_cq(...)  [hot_path_add_toffoli.c]
          |
          v
          CLA or RCA based on width/cla_override
  NO  --> CQ_add(bits, value)  [QFT path]
```

### New Data Flow (modular Toffoli arithmetic)

```
Python: x += y  (where x, y are qint_mod)
  |
  v
qint_mod.__add__(self, y)  [qint_mod.pyx -- MODIFIED]
  |
  v (Cython call to C)
toffoli_mod_add_qq(circ, a_qubits, b_qubits, bits, N)  [NEW: ToffoliModularArithmetic.c]
  |
  v (internally calls existing Toffoli adders 5x in Beauregard sequence)
  1. toffoli_QQ_add(...)    -- b += a
  2. toffoli_CQ_add(...)    -- b -= N (classical, inverted)
  3. [CNOT to extract MSB borrow flag]
  4. toffoli_cCQ_add(...)   -- if MSB: b += N (controlled)
  5. toffoli_QQ_add(...)    -- b -= a (inverted, undo step 1)
  6. [CNOT to restore ancilla to |0>]
  7. toffoli_QQ_add(...)    -- b += a (redo)
```

### New Data Flow (parametric compilation)

```
Python: @ql.compile(parametric=True)
        def mod_mul(x, classical_val):
            x *= classical_val

        mod_mul(reg, 5)   # First call: capture (classical_val=5)
        mod_mul(reg, 7)   # Second call: parametric replay (substitute 7)
  |
  v
CompiledFunc.__call__(reg, 7)
  |
  v
cache_key = (widths=(8,), control=0, qubit_saving=0, parametric=True)
  |
  v (cache HIT -- same widths, parametric ignores classical value)
_parametric_replay(cached_block, quantum_args=[reg], classical_args=[7])
  |
  v (for each node in cached_block.gates)
  - Normal gate dict: remap qubits, inject into circuit (as today)
  - DeferredCQOp node: call C-level CQ function with value=7, inject result
  - ParametricPlaceholder: compute angle from value=7, emit rotation gate
```

### New Data Flow (tradeoff policy)

```
Python: ql.option('tradeoff', 'min_depth')
  |
  v
circuit_t.tradeoff_policy = TRADEOFF_MIN_DEPTH
  |
  v (during any Toffoli addition)
hot_path_add_toffoli.c toffoli_qq_uncont():
  policy == TRADEOFF_MIN_DEPTH?
    --> allocator_available(circ->allocator) >= cla_ancilla_count?
        YES: Use BK CLA (O(log n) depth)
        NO:  Fall back to RCA (O(n) depth, 1 ancilla)
```

## Recommended Project Structure (new/modified files only)

```
c_backend/
  include/
    toffoli_modular_ops.h       # NEW: modular add/sub/mul declarations
    circuit.h                    # MODIFY: add tradeoff_policy_t enum + field
    qubit_allocator.h            # MODIFY: add allocator_available()
  src/
    ToffoliModularArithmetic.c   # NEW: Beauregard modular adder implementation
    hot_path_add_toffoli.c       # MODIFY: policy-based CLA/RCA dispatch
    qubit_allocator.c            # MODIFY: add allocator_available()
    circuit_allocations.c        # MODIFY: init tradeoff_policy in init_circuit()

src/quantum_language/
    compile.py                   # MODIFY: parametric=True, DeferredCQOp, ParametricPlaceholder
    counting.py                  # NEW: count_solutions(), CountResult
    qint_mod.pyx                 # MODIFY: C-level modular ops instead of _reduce_mod
    qint_mod.pxd                 # MODIFY: cdef declarations for new wrappers
    __init__.py                  # MODIFY: import count_solutions

setup.py                         # MODIFY: add ToffoliModularArithmetic.c to c_sources

tests/python/
    test_modular_toffoli.py      # NEW: Beauregard modular adder verification
    test_parametric_compile.py   # NEW: parametric compilation tests
    test_tradeoff.py             # NEW: policy-based dispatch tests
    test_counting.py             # NEW: quantum counting tests
```

### Structure Rationale

- **C modular ops:** Placed alongside existing `ToffoliAdditionCDKM.c`, `ToffoliAdditionCLA.c`, `ToffoliMultiplication.c` -- follows the established pattern of one C file per algorithm family.
- **counting.py:** Standalone Python module like `amplitude_estimation.py` and `grover.py` -- follows the pattern of one file per algorithm.
- **compile.py modifications:** Parametric features are in the same file because they share the `CompiledFunc` class, cache management, and gate replay infrastructure.

## Architectural Patterns

### Pattern 1: Composition of Existing Primitives (Modular Arithmetic)

**What:** Build higher-level operations by composing calls to existing lower-level C functions rather than implementing new gate sequences from scratch.

**When to use:** When the algorithm is a well-defined sequence of existing operations (e.g., Beauregard modular adder = 5 calls to existing adders).

**Trade-offs:**
- PRO: Reuses tested, optimized, hardcoded-sequence-accelerated code
- PRO: Automatically benefits from CLA/RCA dispatch in each sub-call
- PRO: Significantly less new code to write (hundreds of lines vs thousands)
- CON: Cannot optimize across sub-operation boundaries (e.g., cancel gates between step 2 and step 3)
- CON: Ancilla allocation happens per-sub-call, not globally optimized

**Example:**
```c
void toffoli_mod_add_qq(circuit_t *circ,
                        const unsigned int *a_qubits,
                        const unsigned int *b_qubits,
                        int bits, int64_t N) {
    // Allocate shared ancilla for entire modular add sequence
    qubit_t temp_start = allocator_alloc(circ->allocator, bits + 1, true);
    if (temp_start == (qubit_t)-1) return;

    unsigned int qa[256];

    // Step 1: b += a (reuse existing QQ adder via toffoli_dispatch_qq)
    build_qq_layout(qa, a_qubits, b_qubits, bits, temp_start);
    sequence_t *seq = toffoli_QQ_add(bits);
    if (seq) run_instruction(seq, qa, /*invert=*/0, circ);

    // Step 2: b -= N (reuse existing CQ adder)
    build_cq_layout(qa, b_qubits, bits, temp_start);
    seq = toffoli_CQ_add(bits, N);
    if (seq) { run_instruction(seq, qa, /*invert=*/1, circ); toffoli_sequence_free(seq); }

    // Steps 3-7: MSB check, conditional add-back, undo, redo ...

    allocator_free(circ->allocator, temp_start, bits + 1);
}
```

### Pattern 2: Opt-In Enhancement (Parametric Compilation)

**What:** Add optional behavior to existing systems via flags/parameters rather than changing default behavior.

**When to use:** When the new feature changes semantics (parametric caching is fundamentally different from exact caching) and must not break existing code.

**Trade-offs:**
- PRO: Zero regression risk for existing users
- PRO: Can be adopted incrementally
- CON: Two code paths to maintain
- CON: Users must know to opt in

**Example:**
```python
# Existing behavior unchanged:
@ql.compile
def add_one(x):
    x += 1

# New parametric behavior (opt-in):
@ql.compile(parametric=True)
def mod_mul(x, classical_val):
    x *= classical_val
    # On first call, captures gate structure
    # On subsequent calls with different classical_val,
    # replays structure but regenerates CQ sequences
```

### Pattern 3: Policy Abstraction (Depth/Ancilla Tradeoff)

**What:** Replace hardcoded thresholds with named policies that users select, while the system maps policies to implementation details.

**When to use:** When there are multiple valid strategies and the "best" one depends on user context (hardware constraints, optimization goals).

**Trade-offs:**
- PRO: Clean user API (`ql.option('tradeoff', 'min_depth')`)
- PRO: System can evolve internally (add new adder variants) without API changes
- CON: "auto" policy requires heuristics that may not be optimal for all cases
- CON: Policy selection is circuit-global, not per-operation

### Pattern 4: Thin API Wrapper (Quantum Counting)

**What:** Expose a new user-facing API that is a thin mathematical transformation layer over existing infrastructure.

**When to use:** When the underlying algorithm is already implemented and the new feature is a straightforward conversion of its output.

**Trade-offs:**
- PRO: Minimal code, minimal risk, fast to implement
- PRO: Automatically benefits from improvements to the underlying system
- CON: Limited optimization opportunities (cannot specialize IQAE for counting)
- CON: Epsilon conversion from count-space to probability-space may surprise users

## Recommended Build Order

The four features have the following dependency structure:

```
Bug fixes (BUG-DIV-02, BUG-QFT-DIV, BUG-MOD-REDUCE)
    |  (BUG-MOD-REDUCE is superseded by Beauregard C implementation)
    v
1. Quantum Counting (GADV-01) -- independent, simplest
    |
2. Modular Toffoli Arithmetic (FTE-02) -- core C work
    |
3. Depth/Ancilla Tradeoff (OPT-01) -- enhances modular perf
    |
4. Parametric Compilation (PAR-01, PAR-02) -- most complex
```

**Detailed rationale:**

1. **Quantum Counting first** -- zero dependencies on other v5.0 features, wraps existing `amplitude_estimate()`, can ship independently. Provides immediate user value.

2. **Modular Toffoli Arithmetic second** -- the core feature. Requires C implementation but reuses all existing Toffoli adders. BUG-MOD-REDUCE is resolved as a side effect (the Python `_reduce_mod` is replaced by correct C implementation). Bug fixes BUG-DIV-02 and BUG-QFT-DIV can be addressed in parallel or before, as they affect the non-Toffoli paths.

3. **Depth/Ancilla Tradeoff third** -- enhances all Toffoli operations including the new modular arithmetic. The tradeoff is meaningful only after modular arithmetic creates real demand for ancilla optimization. Small, contained change to `hot_path_add_toffoli.c`.

4. **Parametric Compilation last** -- the most complex feature, touching compile.py's cache and replay system. Benefits from modular arithmetic being stable (it is the primary use case for parametric compilation). Needs careful testing against both QFT and Toffoli backends.

## Anti-Patterns

### Anti-Pattern 1: Python-Level Modular Reduction

**What people do:** Implement modular arithmetic by stacking Python-level `qint` operations (add, compare, conditional subtract) as the current `_reduce_mod` does.

**Why it is wrong:** Each Python-level operation allocates its own temporaries and ancilla independently. A 4-bit modular add via `_reduce_mod` creates ~8 temporary qint objects, each with their own qubit allocation, layer tracking, and uncomputation chains. This causes:
- Excessive qubit consumption (30+ qubits for a 4-bit mod add vs ~13 with C-level Beauregard)
- BUG-MOD-REDUCE: Orphan temporaries from intermediate comparisons corrupt results
- Uncomputation chains that are impossible to reverse correctly

**Do this instead:** Implement the Beauregard modular adder at the C level where ancilla allocation is explicit, shared across sub-operations, and correctly lifecycle-managed via `allocator_alloc`/`allocator_free`.

### Anti-Pattern 2: Separate Cache for Each Classical Value

**What people do:** In parametric compilation, create a new `CompiledBlock` for every unique classical argument value (the current default behavior).

**Why it is wrong:** For Shor's modular exponentiation, the classical multiplier changes at every step. With a 10-bit modulus, that is up to 1024 unique classical values, each requiring a full capture pass (function execution, gate extraction, virtual mapping, optimization). This defeats the purpose of compilation.

**Do this instead:** Capture once with deferred CQ operations, replay many times with value substitution. The circuit topology is identical across classical values -- only CQ sequence contents and rotation angles differ.

### Anti-Pattern 3: Exposing Internal Adder Selection to Users

**What people do:** Add API options like `ql.option('adder', 'cdkm')` or `ql.option('adder', 'brent_kung')` that force specific internal algorithms.

**Why it is wrong:** Users should not need quantum circuit design expertise to get good performance. Internal adder choice should be an implementation detail that can change between versions.

**Do this instead:** Expose a policy-level option (`'tradeoff': 'auto'|'min_depth'|'min_qubits'`) that maps to implementation choices internally. The system can add Kogge-Stone, Draper CLA, or other adder variants without API changes.

### Anti-Pattern 4: Monolithic Modular Arithmetic Function

**What people do:** Implement the entire Beauregard modular add as one large function that manually emits CCX/CX/X gates.

**Why it is wrong:** Duplicates the CDKM/CLA logic already in `ToffoliAdditionCDKM.c` and `ToffoliAdditionCLA.c`. Does not benefit from hardcoded sequences. Harder to maintain and verify.

**Do this instead:** The modular adder should call the existing `toffoli_QQ_add()`, `toffoli_CQ_add()`, etc. as subroutines. These already handle CLA/RCA dispatch, hardcoded sequence lookup, and Clifford+T decomposition. The modular adder only needs to orchestrate the Beauregard sequence of calls.

## Integration Points Summary

### Internal Boundaries

| Boundary | Communication | Changes in v5.0 |
|----------|---------------|------------------|
| Python `qint_mod` <-> C modular ops | New Cython `cdef extern` block wrapping `toffoli_mod_*` | NEW: declarations in `qint_mod.pyx` extern block |
| `compile.py` <-> `_core.pyx` | `extract_gate_range`, `inject_remapped_gates` | MODIFY: parametric replay may call `inject_remapped_gates` multiple times per deferred op |
| `compile.py` cache key <-> `_classify_args` | Determines cache hit/miss | MODIFY: parametric mode omits classical args from key |
| `circuit_t` <-> `hot_path_add_toffoli.c` | `circ->cla_override`, `circ->qubit_saving` fields | EXTEND: Add `circ->tradeoff_policy` read in dispatch |
| `counting.py` <-> `amplitude_estimation.py` | Direct function call to `amplitude_estimate()` | NEW: thin wrapper, no changes to callee |
| `__init__.py` <-> `counting.py` | Import and re-export `count_solutions` | EXTEND: one new import line |
| `option()` <-> `circuit_t` | Mapping string options to C struct fields | EXTEND: map `'tradeoff'` -> `circ->tradeoff_policy` |

### Verification Points

| Feature | Verification Method | Qubit Budget |
|---------|---------------------|--------------|
| Modular Toffoli add (4-bit) | Qiskit simulation, exhaustive N=3..15 | ~13 qubits (within 17-qubit limit) |
| Modular Toffoli add (8-bit) | matrix_product_state simulator | ~25 qubits (exceeds statevector limit) |
| Modular Toffoli mul (4-bit) | Qiskit simulation, selected N values | ~17 qubits (borderline) |
| Parametric compile | Gate-count comparison: parametric vs non-parametric | N/A (structural verification) |
| Tradeoff policy | Depth/ancilla metrics comparison across policies | N/A (metric verification) |
| Quantum counting | Known-M oracles with classical verification | Same as amplitude_estimate |

## Scaling Considerations

| Concern | 4-bit modulus | 16-bit modulus | 64-bit modulus |
|---------|---------------|----------------|----------------|
| Modular add qubits | ~13 (2*4+4+1) | ~49 (2*16+16+1) | ~193 (2*64+64+1) |
| Modular add depth (RCA) | ~40 gates | ~160 gates | ~640 gates |
| Modular add depth (CLA) | ~20 gates | ~64 gates | ~256 gates |
| Parametric cache entries | 1 per width | 1 per width | 1 per width |
| Parametric replay cost | ~0.1ms | ~1ms | ~10ms |
| Modular exponentiation (full) | ~260 mod-muls | ~4K mod-muls | ~64K mod-muls |

The critical scalability concern is qubit count for modular arithmetic. A complete Shor's factoring of an n-bit number requires ~5n qubits for the Beauregard approach. At 64 bits, that is ~320 qubits -- well within the circuit generation capability (tested to 2000+ variables for QFT) but far beyond the 17-qubit simulation limit. Verification of large modular circuits must use `matrix_product_state` simulator or purely classical validation.

For parametric compilation, the scalability advantage is most dramatic for Shor's: without parametric mode, an n-bit factoring requires n^2 separate cache entries (one per classical multiplier in the exponentiation). With parametric mode, it requires 1 cache entry total.

## Sources

- Beauregard, "Circuit for Shor's algorithm using 2n+3 qubits" (2003): [ResearchGate](https://www.researchgate.net/publication/2188063_Circuit_for_Shor's_algorithm_using_2n3_qubits)
- Haner, Roetteler, Svore, "Factoring using 2n+2 qubits with Toffoli based modular multiplication" (2016): [arXiv 1611.07995](https://arxiv.org/pdf/1611.07995)
- Cuccaro, Draper, Kutin, Moulton, "A new quantum ripple-carry addition circuit" (CDKM): [arXiv quant-ph/0410184](https://arxiv.org/abs/quant-ph/0410184)
- Grinko, Gacon, Zoufal, Woerner, "Iterative quantum amplitude estimation" (2021): used by existing `amplitude_estimation.py`
- Brassard, Hoyer, Tapp, "Quantum Counting" (1998): [arXiv quant-ph/9805082](https://arxiv.org/abs/quant-ph/9805082)
- Optimal compilation of parametrised quantum circuits (2024): [arXiv 2401.12877](https://arxiv.org/abs/2401.12877)
- Efficient control modular adder on CLA using relative-phase Toffoli gates: [arXiv 2010.00255](https://arxiv.org/abs/2010.00255)
- Quantum counting via IQAE: [Classiq documentation](https://docs.classiq.io/latest/explore/algorithms/amplitude_estimation/quantum_counting/quantum_counting/)
- Comprehensive study of quantum arithmetic circuits: [arXiv 2406.03867](https://arxiv.org/html/2406.03867v1)
- Windowed modular arithmetic optimizations (2025): [arXiv 2502.17325](https://arxiv.org/pdf/2502.17325)

---
*Architecture research for: Quantum Assembly v5.0 Advanced Arithmetic & Compilation*
*Researched: 2026-02-24*
