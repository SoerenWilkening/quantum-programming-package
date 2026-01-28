# Feature Landscape: Automatic Uncomputation

**Domain:** Quantum programming language with automatic memory cleanup
**Researched:** 2026-01-28
**Context:** Adding automatic uncomputation to existing quantum programming framework with qbool operations and qint comparisons

## Executive Summary

Automatic uncomputation is a critical feature for quantum programming languages, preventing "garbage" qubits from accumulating and consuming quantum memory. Research shows two dominant approaches: **type-system-based** (Silq's qfree/const annotations, Qurts' affine types with lifetime) and **scope-based** (Q#'s within/apply, Qrisp's auto_uncompute decorator). The user's `with` statement pattern aligns naturally with scope-based cleanup, similar to Q# conjugations and Python's context managers.

Key finding: Most frameworks support **two uncomputation strategies** — deferred/lazy (cleanup at scope exit) and eager/immediate (cleanup as soon as safe) — with configuration options to choose based on circuit constraints (qubit count vs gate count tradeoffs).

## Table Stakes

Features users expect from automatic uncomputation. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Scope-triggered cleanup** | Industry standard (Q#, Qrisp, Silq all use scopes) | Medium | `with` statement exit is natural trigger |
| **Dependency tracking** | Cannot uncompute value still in use | Medium | Track what intermediates created final result |
| **Reverse-order uncomputation** | Mathematical requirement (U†VU pattern) | Low | LIFO cleanup through dependency graph |
| **Safety verification** | Prevent uncomputation of entangled values | High | Type system or runtime checks needed |
| **Support for nested expressions** | Real code has `~a & b \| ~c` patterns | Medium | Track tree of intermediate allocations |
| **Both qbool and comparison results** | Already have both in framework | Low | qint comparisons produce qbool results |
| **Explicit opt-out** | Sometimes manual control needed | Low | `.keep()` or similar to prevent cleanup |
| **Clear error messages** | When uncomputation unsafe | Low | Better than silent incorrectness |

**MVP Priority:** Scope-triggered cleanup, dependency tracking, reverse-order uncomputation, nested expression support. Safety verification can start simple (track if value used in with-block).

## Differentiators

Features that set this implementation apart. Not expected, but highly valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Dual-mode strategy** | Optimize for either qubits or gates | Medium | Like SQUARE's eager vs lazy |
| **Automatic strategy selection** | Smart defaults based on expression depth | High | Analyze nesting to pick strategy |
| **Recompute-on-demand** | Uncompute early, recompute if needed later | High | Qrisp's `recompute=True` feature |
| **Visual uncomputation markers** | Circuit output shows what gets cleaned up | Low | Annotate OpenQASM with uncompute blocks |
| **Statistics tracking** | Report qubits saved via uncomputation | Low | Add to existing circuit statistics |
| **Conditional uncomputation analysis** | Detect when uncomputation saves most | Medium | `with` blocks with many intermediates benefit most |
| **Integration with circuit optimizer** | Uncomputation + optimization synergy | Medium | Optimizer can simplify U†U patterns |
| **Zero-configuration default mode** | Works automatically without any setup | Low | Most users shouldn't need `option()` calls |

**Recommended for v1.2:** Dual-mode strategy (user chooses), visual markers, statistics tracking, zero-config default. Defer automatic selection and recompute-on-demand to later versions.

**Standout opportunity:** The existing circuit statistics and visualization infrastructure makes "show me what uncomputation did" trivial to add, setting this apart from research tools.

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Automatic cloning** | Violates no-cloning theorem | Error message: "Cannot uncompute value still in use. Use .keep() if intentional" |
| **Measurement-based uncomputation** | Changes semantics (collapses superposition) | Only support reversible unitary uncomputation |
| **Global uncomputation at circuit end** | Defeats purpose (memory already consumed) | Scope-based cleanup during execution |
| **Implicit uncomputation without tracking** | Can uncompute values still needed | Explicit dependency graph required |
| **Per-gate uncomputation hooks** | Too fine-grained, complex API | Scope-level control sufficient |
| **Automatic mid-scope cleanup** | Surprising behavior, hard to debug | Only uncompute at scope boundaries |
| **Uncompute-by-default-with-opt-in-keeping** | Backwards (hard to preserve values) | Keep-by-default-with-opt-in-cleanup |

**Critical:** Do NOT measurement-based uncomputation (several papers emphasize this distinction). Only reversible unitary operations preserve quantum information.

## Feature Dependencies

```
Foundation (must have first):
  Dependency Tracking
    ├─> Tracks intermediate qbool allocations
    └─> Records parent-child relationships

Scope-Based Cleanup (requires dependency tracking)
  ├─> Triggered on `with` block exit
  ├─> Reverse-order uncomputation (LIFO)
  └─> Safety checks (value not used elsewhere)

Advanced Modes (require scope-based cleanup):
  ├─> Eager mode (immediate cleanup of unused intermediates)
  ├─> Lazy mode (defer until scope exit)
  └─> Recompute-on-demand (uncompute early, recompute if needed)

Integration Features (independent):
  ├─> Visual markers in circuit output
  ├─> Statistics tracking (qubits saved)
  └─> Circuit optimizer integration
```

**Critical path:** Dependency tracking → Scope-based cleanup → Basic safety checks. Everything else can be added incrementally.

**Existing infrastructure leverage:**
- `with` statement already controls gate generation → natural scope trigger
- Circuit statistics already track qubits → easy to add "qubits saved"
- OpenQASM output already formats nicely → add comment annotations

## Uncomputation Modes

Based on research (SQUARE eager/lazy, Qrisp recompute, Reqomp space-constrained):

### Mode 1: Lazy/Deferred (DEFAULT)

**When:** Sufficient qubits available, minimize gate count
**Behavior:**
- Keep all intermediates until `with` block exits
- Uncompute in reverse order (LIFO)
- Reuses same qubits for uncomputation operations

**Example:**
```python
with ~a & b | ~c:  # Creates intermediates: ~a, ~c, (~a & b), final
    count += 1
# On exit: uncompute final, (~a & b), ~c, ~a
```

**Pros:** Minimal gates (no redundant compute/uncompute cycles)
**Cons:** Maximum qubit usage during scope

### Mode 2: Eager/Immediate

**When:** Limited qubits, can afford more gates
**Behavior:**
- Uncompute intermediates as soon as no longer needed
- May recompute if needed later in same scope
- Minimizes peak qubit count

**Example:**
```python
# Expression: ~a & b | ~c
# 1. Compute ~a (allocate tmp1)
# 2. Compute ~a & b (allocate tmp2, can uncompute tmp1 now)
# 3. Uncompute tmp1 (frees qubit)
# 4. Compute ~c (allocate tmp3, reuses freed qubit)
# 5. Compute tmp2 | tmp3 (allocate final)
# 6. Uncompute tmp2, tmp3 at scope exit
```

**Pros:** Minimal qubit usage
**Cons:** More gates (extra uncomputation operations mid-expression)

### Mode 3: Hybrid (FUTURE)

**When:** Balance qubits and gates
**Behavior:**
- Analyze expression tree depth
- Keep shallow branches, uncompute deep branches
- Adaptive based on circuit statistics

**Not for v1.2** (too complex, need real-world usage data first)

## Mode Selection API

```python
# Zero-config default (lazy mode, works automatically)
with ~a & b | ~c:
    count += 1

# Explicit mode selection (global option)
ql.option("uncomputation", "eager")  # or "lazy"
with ~a & b | ~c:
    count += 1

# Per-scope override (future enhancement)
with (~a & b | ~c).eager():
    count += 1
```

**Recommendation:** Lazy as default (matches Q# and Qrisp defaults), global option for eager.

## Safety Requirements

| Requirement | How to Verify | Error Behavior |
|-------------|---------------|----------------|
| Value not used after uncompute | Track all references to qbool | RuntimeError with clear message |
| Value not entangled elsewhere | Check if used in other active scopes | RuntimeError or mark `.keep()` |
| Uncomputation is reversible | Only allow qfree operations (no measurement) | Type/API restriction |
| Correct dependency order | Topological sort of dependency graph | Automatic (no user action needed) |

**Implementation note:** Start with simple "was this value used in the with-block" check. Can enhance with full entanglement tracking later.

## Nested Scope Behavior

```python
# Nested with blocks
with ~a:
    with ~b:
        count += 1
    # Inner scope exits: uncompute ~b (but NOT ~a, still in use)
# Outer scope exits: uncompute ~a
```

**Rule:** Only uncompute variables created in the exiting scope, not parent scopes.

## Integration with Existing Features

| Existing Feature | Uncomputation Interaction | Implementation Note |
|------------------|---------------------------|---------------------|
| `with qbool:` conditionals | Trigger for cleanup on block exit | Add `__exit__` to qbool context manager |
| qint comparisons | Return qbool that can be uncomputed | Same code path as qbool operations |
| Circuit statistics | Add "qubits saved" metric | Extend existing `get_statistics()` |
| OpenQASM output | Annotate uncomputation sections | Add `// uncompute start/end` comments |
| Circuit optimizer | Can optimize U†U patterns | Run optimizer after uncomputation synthesis |

## Edge Cases

| Case | Expected Behavior | Rationale |
|------|-------------------|-----------|
| `qb = ~a; with qb:` | Uncompute `~a` when `qb` scope ends | Track that qb references ~a intermediate |
| Multiple uses: `with ~a: ... with ~a:` | ERROR or second `~a` creates new qubit | Safer to error (prevents confusion) |
| Break/return in with-block | Still uncompute on exit | Python `__exit__` always called |
| Exception in with-block | Still uncompute on exit | Python guarantees cleanup |
| `.keep()` called on intermediate | Skip uncomputation for that value | Explicit user override |

## Research Confidence

| Area | Confidence | Sources |
|------|------------|---------|
| Scope-based pattern | HIGH | Q#, Qrisp, Silq all use scopes |
| Eager vs lazy modes | HIGH | SQUARE paper explicit comparison |
| Safety via type systems | MEDIUM | Silq uses qfree/const, but complex |
| Recompute-on-demand | MEDIUM | Qrisp implements, benefits unclear |
| Nested expression handling | HIGH | All frameworks handle this |

**Gap:** Limited documentation on when eager vs lazy performs better. Will need benchmarking with real algorithms.

## Sources

Research findings from academic papers and production quantum programming frameworks:

**Core Papers:**
- [Silq: A High-Level Quantum Language with Safe Uncomputation and Intuitive Semantics](https://dl.acm.org/doi/abs/10.1145/3385412.3386007) (PLDI 2020)
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits](https://dl.acm.org/doi/10.1145/3453483.3454040) (PLDI 2021)
- [SQUARE: Strategic Quantum Ancilla Reuse for Modular Quantum Programs](https://arxiv.org/abs/2004.08539)
- [Modular Synthesis of Efficient Quantum Uncomputation](https://dl.acm.org/doi/10.1145/3689785) (2024)
- [Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime](https://dl.acm.org/doi/abs/10.1145/3704842) (2025)
- [Reqomp: Space-constrained Uncomputation for Quantum Circuits](https://quantum-journal.org/papers/q-2024-02-19-1258/) (Quantum 2024)

**Framework Documentation:**
- [Q# Conjugations](https://learn.microsoft.com/en-us/azure/quantum/user-guide/language/expressions/conjugations) (Microsoft)
- [Qrisp Uncomputation](https://qrisp.eu/reference/Core/Uncomputation.html)
- [Silq Overview](https://silq.ethz.ch/overview)

**Conference Proceedings:**
- [Uncomputation in the Qrisp High-Level Quantum Programming Framework](https://link.springer.com/chapter/10.1007/978-3-031-38100-3_11) (RC 2023)

**Key Insights:**
- **Eager vs Lazy**: SQUARE demonstrates same algorithm needs different strategies for different hardware topologies
- **Qfree annotation**: Silq's approach to safety — functions that preserve superposition structure
- **Within/Apply**: Q# pattern for automatic adjoint generation (U†VU conjugation)
- **Scope management**: All modern frameworks use scope-based cleanup rather than global cleanup
- **Reversibility requirement**: All sources emphasize uncomputation must be reversible (no measurement)
