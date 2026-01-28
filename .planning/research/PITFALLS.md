# Domain Pitfalls: Automatic Uncomputation

**Domain:** Adding automatic uncomputation to existing quantum circuit framework
**Researched:** 2026-01-28
**Confidence:** HIGH (based on recent academic research 2024-2025 and existing codebase analysis)

## Executive Summary

Implementing automatic uncomputation in quantum programming frameworks is deceptively complex. While the concept is simple — automatically reverse intermediate computations to free qubits — the implementation requires solving several hard problems: finding correct uncomputation positions in circuit flow, managing complex dependency graphs, integrating with existing circuit constructs (especially conditional operations), and avoiding exponential cost blowups. The existing framework's stateless C backend, `with` statement conditionals, and circuit-building architecture create specific integration challenges that must be addressed carefully.

## Critical Pitfalls

These mistakes cause rewrites, incorrect quantum states, or exponential resource usage.

### Pitfall 1: Incorrect Uncomputation Position in Circuit Flow

**What goes wrong:** Placing uncomputation (inverse gates) at the wrong circuit position produces incorrect quantum states. An intermediate qubit cannot be uncomputed if:
- Its computed value is still needed downstream for other operations
- The qubits needed for its uncomputation have been modified or deallocated
- It would interfere with entangled qubits still in use

**Why it happens:**
- Dependency analysis misses indirect dependencies (value used in control of conditional)
- Graph traversal doesn't respect layer ordering in the existing circuit structure
- Interaction between lifetime-based uncomputation and layer-based circuit building
- `with` statement conditional contexts create nested scopes where dependency analysis breaks down

**Consequences:**
- Silent quantum state corruption (ancilla not returned to |0⟩)
- Downstream operations receive wrong quantum state
- Circuit violates reversibility requirements
- Results appear random due to garbage amplification
- **This is the #1 source of incorrect circuits in automatic uncomputation implementations**

**Prevention:**
1. **Build dependency graph BEFORE inserting uncomputation gates** — analyze the complete circuit to understand what depends on what
2. **Layer-aware scheduling:** Uncomputation must respect existing circuit layer structure; insert inverse gates only after the layer containing the last use
3. **Validate uncomputation availability:** Before uncomputing qubit q using qubits {a, b, c}, verify that {a, b, c} still hold the required quantum state (haven't been modified since q was computed)
4. **Explicit scope tracking:** Track `with` statement boundaries and prevent uncomputation from crossing conditional scope boundaries inappropriately
5. **Add validation pass:** After generating uncomputation, verify that each uncomputed qubit ends in |0⟩ state (requires symbolic state tracking or test verification)

**Detection (warning signs):**
- Test circuits produce inconsistent results across runs
- Qubits show unexpected entanglement after uncomputation
- Circuit simulation shows ancilla in non-zero states
- allocator_get_stats() shows qubit count not decreasing despite uncomputation

**Which phase:** Phase 1 (Dependency Graph) must get this architecture right; Phase 2 (Basic Uncomputation) validates with tests

**Sources:**
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits](https://files.sri.inf.ethz.ch/website/papers/pldi21-unqomp.pdf)
- [Modular Synthesis of Efficient Quantum Uncomputation](https://www.researchgate.net/publication/381580072_Modular_Synthesis_of_Efficient_Quantum_Uncomputation)

---

### Pitfall 2: Circular Dependencies and Memory Leaks in Dependency Tracking

**What goes wrong:** Dependency tracking creates reference cycles that prevent cleanup:
- Qubit A depends on qubits {B, C}
- Qubit B depends on qubits {A, D}
- Both A and B maintain references to each other
- Python/Cython reference counting never reaches zero
- Memory leak grows with circuit size

**Why it happens:**
- Each qbool/intermediate tracks what created it (parent references)
- Parents may track children for reverse traversal (child references)
- Bidirectional references create cycles that garbage collection doesn't handle
- C backend has no built-in cycle detection (manual memory management)
- Cython wrapper between Python and C complicates ownership

**Consequences:**
- Memory usage grows unbounded for large circuits
- Segfaults when freeing circuit (double-free or use-after-free)
- Dependency graph becomes unreachable but not freed
- Performance degradation as memory fills
- **This is especially dangerous because it only manifests at scale**

**Prevention:**
1. **Single ownership model:** Each dependency node owned by exactly one parent (circuit or parent node)
2. **Weak references for parent pointers:** Use indices or weak pointers to avoid cycles
3. **Graph stored in circuit structure:** Centralize dependency graph in circuit_t, not distributed across qbool objects
4. **Explicit cleanup protocol:** Walk dependency graph in topological order to free nodes (similar to qubit_allocator cleanup)
5. **Reference counting audit:** Track all alloc/free pairs in C backend; use valgrind to detect leaks

**Detection (warning signs):**
- Memory usage grows faster than circuit size would suggest
- valgrind reports "definitely lost" memory blocks
- Segfaults in free_circuit() or when Python objects are garbage collected
- RSS memory never decreases even after circuit operations complete

**Which phase:** Phase 1 (Dependency Graph) must design ownership model carefully; Phase 3 (Integration Testing) validates with memory profiling

**Sources:**
- [Rust reference cycles](https://doc.rust-lang.org/book/ch15-06-reference-cycles.html) (similar ownership challenges)
- Codebase: qubit_allocator.h demonstrates successful single-ownership pattern

---

### Pitfall 3: Exponential Cost Blowup with Recursive/Nested Uncomputation

**What goes wrong:** Naive uncomputation in nested contexts causes exponential recomputation:
- Function A calls function B which computes intermediate X
- A's uncomputation reverses B, which includes reversing X
- But B's logic already included uncomputing X
- Result: X is recomputed at every nesting level
- For ℓ levels of nesting, cost multiplies by 2^ℓ

**Why it happens:**
- Delayed uncomputation: intermediate values kept alive through entire operation scope
- Nested operations (qint comparison inside qbool expression inside `with` statement)
- Each scope uncomputes its intermediates, but those intermediates themselves had intermediates
- Hierarchical recomputation cascades down the call stack
- **The existing framework's operator overloading creates implicit nesting that's invisible to users**

**Consequences:**
- Gate count explodes exponentially with expression complexity
- O(n) algorithm becomes O(2^n) in gate count
- Circuit generation becomes impossibly slow for moderate complexity
- Quantum advantage lost due to excessive gate overhead
- Users cannot understand why simple expressions produce huge circuits

**Prevention:**
1. **Immediate uncomputation mode (qubit-saving):** Uncompute intermediates as soon as possible, not at scope exit
2. **Memoization:** Track what's already been uncomputed; don't uncompute twice
3. **Flatten dependency graph:** Identify shared intermediate values and uncompute at highest common ancestor
4. **Cost model:** Estimate gate count impact before applying uncomputation; refuse if cost exceeds threshold
5. **Explicit vs implicit scope:** Distinguish between explicit `with` blocks (user-controlled scope) and implicit intermediate creation (operator overloading)

**Detection (warning signs):**
- Gate count grows much faster than expected for expression complexity
- circuit_gate_count() shows 2x, 4x, 8x jumps between similar operations
- Circuit generation time increases exponentially (not linearly) with nested operations
- Profiling shows repeated inverse gate sequences for same qubit patterns

**Which phase:** Phase 2 (Basic Uncomputation) must detect this in tests; Phase 4 (Qubit-Saving Mode) implements mitigation strategy

**Sources:**
- [Modular Synthesis of Efficient Quantum Uncomputation](https://www.researchgate.net/publication/381580072_Modular_Synthesis_of_Efficient_Quantum_Uncomputation) - documents exponential blowup
- [SQUARE: Strategic Quantum Ancilla Reuse](https://arxiv.org/abs/2004.08539) - recursive recomputation challenges

---

### Pitfall 4: Incorrect Reversal of Multi-Controlled and Conditional Gates

**What goes wrong:** Reversing complex gates incorrectly:
- Multi-controlled gates (large_control with n controls) have subtle inverse rules
- Conditional gates (inside `with` statement) may have different controls when reversed
- Parametrized gates (phase rotations) require negating parameters, not just reordering
- Composite gates built from primitives need careful decomposition reversal
- **Control and target qubit roles confused during reversal**

**Why it happens:**
- Inverse of multi-controlled X(q0, q1, q2 → target) is same gate, but logic assumes gate sequence reversal
- Phase gates P(θ) reverse to P(-θ), not just reversed position
- `with condition:` blocks add implicit controls; reversing these requires understanding condition lifetime
- Existing `_controlled` and `_list_of_controls` global state (quantum_language.pyx) creates hidden dependencies
- Gate representation (gate_t) may not preserve all metadata needed for correct inversion

**Consequences:**
- Uncomputation fails silently — circuit runs but produces wrong results
- Controlled operations apply to wrong qubits
- Phase accumulation errors in algorithms using phase gates
- Conditional uncomputation inside `with` blocks corrupts state
- **Especially dangerous because basic tests may pass (single gate) but complex circuits fail**

**Prevention:**
1. **Gate-type-specific inversion:** Switch on gate type; implement custom inverse logic for each (X, CNOT, CCX, P, CP, custom multi-control)
2. **Test inverse correctness:** For every gate type, verify Gate(args) followed by Inverse(args) produces identity
3. **Preserve gate metadata:** Extend gate_t structure to store inversion hints (e.g., rotation angle, control pattern)
4. **Adjoint operator validation:** Verify U†U = I for all generated uncomputation sequences
5. **Interaction with `with` statement:** Explicitly track conditional scope; uncomputation inside `with` must respect that the condition might not hold when reversing

**Detection (warning signs):**
- Test circuits with controlled operations fail after uncomputation
- Circuit produces correct results for simple cases but fails with conditionals
- Phase-based algorithms (QFT, phase estimation) show incorrect phase accumulation
- Statevector simulation shows non-unitary evolution (norm not preserved)

**Which phase:** Phase 1 (Dependency Graph) must represent gate types richly; Phase 2 (Basic Uncomputation) must implement type-specific inversion; Phase 3 (Integration) tests interaction with `with` statement

**Sources:**
- [Quantum logic gates](https://en.wikipedia.org/wiki/Quantum_logic_gate) - fundamental inversion rules
- [A Metamodel-Based Approach for Describing Quantum Gates](https://onlinelibrary.wiley.com/doi/10.1002/spe.70023) - gate representation challenges (2025)

---

### Pitfall 5: Integration with `with` Statement Conditional Scoping

**What goes wrong:** The existing `with` statement creates quantum conditionals by setting global `_controlled` flag and `_control_bool`:
```python
with condition_qbool:
    result = a + b  # All gates get condition as control
```
When automatic uncomputation is added:
- Intermediate qbools created inside `with` block are controlled by condition
- Uncomputation happens outside `with` block (at scope exit)
- Uncomputation gates lack the original control, or have wrong control
- Qubit state left entangled with condition in ways user didn't expect

**Why it happens:**
- `with` statement uses global state (`_controlled`, `_list_of_controls` in quantum_language.pyx)
- Uncomputation may run after `with` block exits (global state reset)
- Dependency graph doesn't capture that intermediate was created in conditional scope
- Lifetime-based uncomputation (Python scope exit) doesn't align with quantum conditional scope

**Consequences:**
- Qubits that should be uncomputed inside conditional are leaked outside
- Uncomputation applied without control creates incorrect state superposition
- User expects intermediate cleanup but qubits remain allocated
- Conditional + uncomputation interaction produces exponential ancilla growth

**Prevention:**
1. **Scope-aware dependency tracking:** Tag each dependency node with its conditional scope (which `with` block it was created in)
2. **Uncomputation inherits control:** If intermediate was created under control C, its uncomputation must also be under control C
3. **Explicit conditional boundaries:** Modify `with` statement exit handler to trigger uncomputation of intermediates created in that scope
4. **Test: conditional + uncomputation:** Create comprehensive tests with nested `with` blocks and verify qubit cleanup
5. **Document interaction:** Make it clear in docs/examples how automatic uncomputation interacts with conditionals

**Detection (warning signs):**
- Qubit count grows inside `with` blocks and doesn't decrease after block exit
- allocator_stats show ancilla_allocations increasing without corresponding deallocations
- Tests pass for unconditional code but fail when same operation is inside `with` block
- Users report "memory leaks" specifically when using conditionals

**Which phase:** Phase 3 (Integration Testing) must address this; may require changes to `with` statement implementation from Phase 2

**Sources:**
- Codebase analysis: quantum_language.pyx lines 26-29 show global conditional state
- [Silq: Safe Uncomputation](https://files.sri.inf.ethz.ch/website/papers/pldi20-silq.pdf) - discusses scope-aware uncomputation

---

## Moderate Pitfalls

These cause delays, technical debt, or user confusion but are fixable without major rewrites.

### Pitfall 6: Partial Uncomputation Correctness

**What goes wrong:** Only some intermediates get uncomputed:
- Dependency graph analysis identifies 5 intermediates
- Only 3 can be safely uncomputed (others still in use)
- Partial uncomputation leaves system in mixed state
- User assumes all intermediates are cleaned up but qubit count doesn't decrease as expected

**Why it happens:**
- Conservative dependency analysis: when unsure, skip uncomputation
- Some code paths share intermediates, others don't (branching ambiguity)
- Qubit reuse: same physical qubit used for value A then value B; uncomputing A would corrupt B

**Prevention:**
1. **All-or-nothing for expression:** Either uncompute all intermediates of an expression or none
2. **Explicit user control:** Let user mark expressions with `uncompute=True/False` flag
3. **Warning messages:** When partial uncomputation occurs, warn user which qubits couldn't be cleaned
4. **Documentation:** Explain under what conditions uncomputation can/cannot occur

**Detection (warning signs):**
- Qubit count decreases less than expected
- Some test cases show full cleanup, others don't (inconsistent behavior)
- Users confused about when uncomputation happens

**Which phase:** Phase 2 (Basic Uncomputation) should define policy; Phase 5 (User Control) adds explicit flags

**Sources:**
- [Reqomp: Space-constrained Uncomputation](https://quantum-journal.org/papers/q-2024-02-19-1258/) - discusses partial uncomputation strategies

---

### Pitfall 7: Performance Overhead of Dependency Tracking

**What goes wrong:** Dependency tracking adds runtime cost to every operation:
- Every qbool creation allocates dependency node
- Every gate added requires updating dependency graph
- Graph traversal for uncomputation analysis takes O(V+E) time
- For large circuits, overhead dominates actual gate generation time

**Why it happens:**
- Dependency tracking runs for ALL operations, even when uncomputation isn't used
- Python/Cython call overhead for each dependency node creation
- Graph stored in Python objects (slower than C structures)

**Prevention:**
1. **Lazy dependency tracking:** Only build graph when user enables uncomputation feature
2. **C-level graph storage:** Store dependency graph in C (circuit_t extension) not Python objects
3. **Batch updates:** Update dependency graph in batches, not per-gate
4. **Profiling:** Measure overhead and set performance budget (e.g., <5% overhead when disabled)

**Detection (warning signs):**
- Circuit generation significantly slower after adding dependency tracking
- Profiling shows dependency_node_create() as hot path
- Users complain about performance regression

**Which phase:** Phase 1 (Dependency Graph) must be performance-conscious; Phase 6 (Testing & Documentation) validates benchmarks

**Sources:**
- Codebase: existing performance benchmarks in circuit-gen-results/ provide baseline

---

### Pitfall 8: Edge Case: Qubit Reuse During Uncomputation

**What goes wrong:** Qubit reuse pattern corrupts uncomputation:
```c
temp = allocator_alloc(alloc, 1, True)  // Qubit 10
// ... compute something using qubit 10
allocator_free(alloc, 10, 1)
temp2 = allocator_alloc(alloc, 1, True)  // Reuses qubit 10!
// Now uncomputation tries to reverse operations on qubit 10
// But qubit 10 is being used for temp2, not temp anymore
```

**Why it happens:**
- qubit_allocator reuses freed qubits (by design, for memory efficiency)
- Dependency graph records qubit indices, not qubit identities
- Uncomputation happens later when qubit has been reallocated
- Temporal qubit reuse not visible to dependency analysis

**Prevention:**
1. **Qubit generation counter:** Assign each qubit a unique ID (not just index); dependency graph uses ID
2. **Deferred reuse:** Don't reuse qubit until its uncomputation is complete
3. **Uncomputation-aware allocator:** Allocator checks if qubit has pending uncomputation before reuse
4. **Test case:** Explicitly test allocate → free → reallocate → uncompute pattern

**Detection (warning signs):**
- Uncomputation corrupts state in ways that seem random
- Tests pass individually but fail when run in sequence (state pollution)
- Qubit reuse pattern in allocator_get_stats() correlates with test failures

**Which phase:** Phase 2 (Basic Uncomputation) must consider this; may require Phase 1 (Dependency Graph) redesign if caught late

**Sources:**
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) - qubit reuse challenges (2025)
- [CaQR: Compiler-Assisted Approach for Qubit Reuse](https://people.cs.rutgers.edu/zz124/assets/pdf/asplos23.pdf)

---

### Pitfall 9: Type System Mismatch (qbool vs qint Comparison Results)

**What goes wrong:** qint comparisons return qbool:
```python
a = qint(5)
b = qint(3)
result = a > b  # Returns qbool (intermediate ancilla)
```
Automatic uncomputation must handle:
- qbool created by qint operations (involves multiple qubits)
- Different uncomputation strategy than qbool logic operations
- Comparison uses in-place subtraction/addition pattern (from v1.1)
- Dependency graph must represent qint → qbool edge

**Why it happens:**
- Type boundary: dependency tracking designed for qbool operations
- Comparison implementation uses temporary qint, then reduces to qbool result
- Width-varying qint makes dependency tracking complex (different qubits per instance)

**Prevention:**
1. **Unified intermediate representation:** Represent both qbool and qint intermediates in same graph structure
2. **Type-aware uncomputation:** Different uncomputation logic for qbool-from-logic vs qbool-from-comparison
3. **Test across type boundary:** Extensively test `(a > b) AND (c < d)` patterns
4. **Review comparison_ops.h:** Understand exact qubit usage in existing comparison implementation

**Detection (warning signs):**
- Uncomputation works for `a AND b` but fails for `(x > y) AND (a > b)`
- Type-related segfaults when freeing qint-derived qbool
- Qubit count doesn't decrease for comparison intermediates

**Which phase:** Phase 2 (Basic Uncomputation) must handle both types; Phase 3 (Integration) validates cross-type cases

**Sources:**
- Codebase: comparison_ops.h implements qint → qbool conversions
- [Qurts: Affine Types with Lifetime](https://arxiv.org/abs/2411.10835) - type system challenges

---

## Minor Pitfalls

These cause annoyance, user confusion, or minor inefficiencies but are easily fixed.

### Pitfall 10: Uncomputation Order Ambiguity

**What goes wrong:** Multiple valid uncomputation orders exist; chosen order affects performance:
- Intermediates {A, B, C} all can be uncomputed
- Order ABC vs CBA produces different gate counts (due to layer packing)
- User cannot predict or control order

**Prevention:**
1. **Deterministic ordering:** Always use topological sort with tiebreaker (e.g., creation order)
2. **Document order:** Explain in docs what order is used
3. **Optimization pass:** Choose order that minimizes gate count (NP-hard, use heuristic)

**Which phase:** Phase 2 (Basic Uncomputation) chooses policy; Phase 4 (Qubit-Saving Mode) may optimize

---

### Pitfall 11: Debugging Difficulty When Uncomputation Breaks

**What goes wrong:** When uncomputation produces wrong circuit:
- User doesn't see dependency graph (internal representation)
- Error manifests as wrong quantum state (hard to diagnose)
- No visibility into what got uncomputed when
- Existing circuit_visualize() doesn't mark uncomputation gates

**Prevention:**
1. **Visualization enhancement:** Mark uncomputation gates in circuit_visualize() (e.g., with ^ symbol)
2. **Debug mode:** `ql.option("debug_uncomputation")` prints dependency graph and uncomputation decisions
3. **Explicit uncomputation gates:** Tag gates with is_uncomputation flag for easier debugging
4. **Test utilities:** Provide validate_uncomputation() function that checks circuit correctness

**Which phase:** Phase 6 (Testing & Documentation) adds debug tooling

---

### Pitfall 12: Documentation of Uncomputation Semantics

**What goes wrong:** User expectations mismatch implementation:
- User expects immediate cleanup (like C++ RAII destructors)
- Implementation does deferred cleanup (at scope exit)
- User doesn't understand when qubit-saving mode should be used
- Interaction with `with` statement not explained

**Prevention:**
1. **Comprehensive examples:** Show when uncomputation happens (with qubit count output)
2. **Mode comparison:** Document default vs qubit-saving with performance trade-offs
3. **Conditional interaction:** Dedicated section on `with` + automatic uncomputation
4. **API reference:** Clearly document lifetime/scope rules

**Which phase:** Phase 6 (Testing & Documentation)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dependency Graph Design | Circular references (Pitfall 2) | Single ownership model in circuit_t; use indices not pointers |
| Dependency Graph Design | Incorrect position analysis (Pitfall 1) | Layer-aware graph; validate against circuit structure |
| Basic Uncomputation | Incorrect gate reversal (Pitfall 4) | Gate-type-specific inversion; comprehensive test suite |
| Basic Uncomputation | Type boundary issues (Pitfall 9) | Unified intermediate representation for qbool and qint |
| Integration with `with` | Conditional scope leakage (Pitfall 5) | Scope-aware dependency tracking; test nested conditionals |
| Integration Testing | Qubit reuse corruption (Pitfall 8) | Qubit generation counter; deferred reuse |
| Qubit-Saving Mode | Exponential cost blowup (Pitfall 3) | Cost model with threshold; memoization; warn user |
| User Control & Options | Documentation mismatch (Pitfall 12) | Examples-first documentation; visual qubit count demos |
| Testing & Documentation | Debugging difficulty (Pitfall 11) | Debug mode with graph visualization; uncomputation markers |

---

## Integration with Existing Codebase

Specific risks given the current architecture:

### Stateless C Backend Interaction
**Challenge:** C backend has no global state (v1.1 design). Dependency tracking adds state.
**Risk:** Mixing stateful dependency graph with stateless gate operations.
**Mitigation:** Store dependency graph in circuit_t structure (not global). Pass circuit pointer to all dependency functions.

### Qubit Allocator Interaction
**Challenge:** qubit_allocator.h manages qubit lifecycle; dependency tracking must coordinate.
**Risk:** Allocator frees qubit while dependency graph still references it (use-after-free).
**Mitigation:**
- Allocator queries dependency graph before allowing reuse
- Dependency graph uses qubit generation ID not index
- Uncomputation triggers allocator_free() only after inverse gates applied

### Global State in Cython Layer
**Challenge:** `_controlled`, `_control_bool`, `_list_of_controls` are global in quantum_language.pyx.
**Risk:** Dependency tracking misses conditional context when these globals change.
**Mitigation:**
- Capture control state when creating dependency node (snapshot at creation time)
- Consider refactoring globals to circuit-level state (larger change)
- Test with rapidly changing control state (nested `with` blocks)

### Circuit Layer Structure
**Challenge:** Circuit uses layer-based scheduling (gate_index_of_layer_and_qubits).
**Risk:** Uncomputation gate insertion invalidates layer indices; O(n²) reindexing.
**Mitigation:**
- Build uncomputation gates in separate buffer, append to circuit in one batch
- Use add_gate() API (already handles layer scheduling) rather than direct manipulation
- Test performance with large circuits (>10K gates)

---

## Research Confidence Assessment

| Category | Confidence | Rationale |
|----------|-----------|-----------|
| General uncomputation theory | HIGH | Multiple 2024-2025 academic papers (Qurts, Unqomp, Reqomp, SQUARE) document pitfalls |
| Gate reversal correctness | HIGH | Quantum computing fundamentals; well-understood (U†U = I) |
| Exponential cost blowup | HIGH | Documented in Modular Synthesis paper; known issue in recursive contexts |
| Integration with existing code | MEDIUM-HIGH | Based on codebase reading; actual integration may reveal more issues |
| `with` statement interaction | MEDIUM | Identified from codebase structure; needs validation with actual implementation |
| Performance overhead | MEDIUM | Estimated from similar systems; actual overhead TBD |
| Qubit reuse edge cases | MEDIUM | Logical inference from allocator design; needs testing |

---

## Sources

### Academic Research (HIGH confidence)
- [Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime](https://arxiv.org/abs/2411.10835) - Lifetime management, type system challenges (2025)
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits](https://files.sri.inf.ethz.ch/website/papers/pldi21-unqomp.pdf) - Dependency analysis, positioning challenges (2021, still relevant)
- [Reqomp: Space-constrained Uncomputation for Quantum Circuits](https://quantum-journal.org/papers/q-2024-02-19-1258/) - Time-space trade-offs (2024)
- [Modular Synthesis of Efficient Quantum Uncomputation](https://www.researchgate.net/publication/381580072_Modular_Synthesis_of_Efficient_Quantum_Uncomputation) - Recursion, exponential cost (2024)
- [Uncomputation in the Qrisp High-Level Quantum Programming Framework](https://arxiv.org/abs/2307.11417) - Implementation in high-level framework (2023)
- [Silq: A High-Level Quantum Language with Safe Uncomputation](https://files.sri.inf.ethz.ch/website/papers/pldi20-silq.pdf) - Qfree requirements, safety constraints (2020, foundational)

### Quantum Circuit Implementation (HIGH confidence)
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) - Memory management, qubit reuse (2025)
- [SQUARE: Strategic Quantum Ancilla Reuse](https://arxiv.org/abs/2004.08539) - Qubit reuse strategies (2020)
- [Rise of conditionally clean ancillae](https://quantum-journal.org/papers/q-2025-05-21-1752/pdf/) - Conditional uncomputation (2025)
- [CaQR: A Compiler-Assisted Approach for Qubit Reuse](https://people.cs.rutgers.edu/zz124/assets/pdf/asplos23.pdf) - Dynamic circuit qubit reuse

### General Quantum Computing (MEDIUM confidence for specific pitfalls)
- [Quantum Error Correction Update 2024](https://www.oreilly.com/radar/quantum-error-correction-update-2024/) - Error propagation context
- [A Metamodel-Based Approach for Describing Quantum Gates](https://onlinelibrary.wiley.com/doi/10.1002/spe.70023) - Gate representation challenges (2025)

### Codebase-Specific (HIGH confidence for this project)
- PROJECT.md - Framework architecture and constraints
- circuit.h, qubit_allocator.h - Existing qubit management
- quantum_language.pyx - Cython layer, global state management
- comparison_ops.h - qint → qbool conversion patterns

---

*Automatic uncomputation pitfalls research completed: 2026-01-28*
*This document focuses specifically on v1.2 milestone challenges and complements the general PITFALLS.md*
