# Project Research Summary

**Project:** Grover's Algorithm and Amplitude Estimation
**Domain:** Quantum search algorithms — oracle compilation, amplitude amplification, iterative amplitude estimation
**Researched:** 2026-02-19
**Confidence:** HIGH

## Executive Summary

Grover's algorithm integration into the Quantum Assembly framework is fundamentally an **API and pattern layer problem**, not a technology stack problem. All required gate primitives (H, Z, CZ, MCX) already exist in the C backend. The `@ql.compile` decorator already handles oracle capture, controlled-variant derivation, and adjoint generation. The `with` statement already implements controlled gate contexts. No new external dependencies are required. The primary implementation work is: exposing H and Z gates at the Python/Cython level, building the diffusion operator pattern (H-X-MCZ-X-H using the existing MCX decomposition path), creating an oracle wrapper that enforces correct phase-marking semantics, and composing these into a clean `ql.grover()` entry point.

The recommended approach is a strict bottom-up build order: gate primitive exposure first, then oracle infrastructure (the most critical and pitfall-dense phase), then diffusion operator, then the Grover loop, and finally amplitude estimation. This order is non-negotiable because the oracle infrastructure pitfalls (phase vs bit-flip confusion, premature uncomputation, garbage qubit entanglement, cache key incompleteness) must be solved before any higher-level components can be validated. The oracle phase is where the most silent failure modes live — circuits that run without error but return uniformly random results.

The key risk is oracle correctness. Four of the six critical pitfalls identified in research are oracle-specific and produce wrong results with no error signal. The mitigation is a dedicated `@ql.grover_oracle` decorator that enforces the compute-phase-uncompute structure, delays uncomputation until after phase kickback, includes `arithmetic_mode` in the cache key, and validates that ancilla qubit delta is zero on exit. Amplitude estimation is comparatively straightforward once the oracle infrastructure is solid, because the existing `_derive_controlled_gates` and `QFT_inverse` infrastructure in the C backend handles the QPE machinery. The recommended amplitude estimation variant is Iterative QAE (IQAE), which uses only Grover operator powers and avoids QFT entirely.

## Key Findings

### Recommended Stack

The existing stack (C backend via Cython bindings to Python) requires zero new dependencies. All required gate primitives exist in `c_backend/src/gate.c` and `c_backend/include/gate.h`. The only gap between the current stack and a working Grover implementation is that the H gate (`h()`) and Z gate (`z()`) need Python-level exposure via Cython bindings — they exist in C but have no Python API. The `@ql.compile` decorator, existing `qint` comparison operators, and the `with` conditional context together already provide the complete oracle compilation foundation.

For amplitude estimation, the IQAE variant is strongly preferred over canonical QPE-based QAE. IQAE uses only Grover operator powers with no QFT circuit, lower depth, fewer qubits, and published evidence for practical quantum advantage on NISQ devices. The framework already has QFT sequences in `IntegerAddition.c` for future use if full QPE is ever needed, but it is not required for the IQAE path.

**Core technologies:**
- `h()`, `z()`, `mcx()` in `gate.h/gate.c` — diffusion operator primitives — exist in C, need Python exposure via ~30 lines of Cython
- `@ql.compile` in `compile.py` — oracle capture, adjoint derivation, controlled variants — exists, reused directly without modification
- `qint.__eq__`, `__lt__`, etc. in `qint_comparison.pxi` — oracle predicate circuits — exist, unchanged
- `with qbool:` conditional context in `qint.pyx` — controlled gate generation — exists, reused directly
- `emit_ccx_clifford_t()` in `gate.c` — MCX decomposition for diffusion S_0 — exists, zero ancilla path
- NumPy, Qiskit (optional for verification) — no version changes or additions required

### Expected Features

**Must have (table stakes):**
- `ql.grover(oracle, register)` — single entry point returning measured Python value
- Diffusion operator built-in — H-X-MCZ-X-H using existing MCX decomposition, zero ancilla required
- Manual oracle mode — accept user-provided `@ql.compile`-decorated function
- Automatic iteration count for known M — `floor(pi/4 * sqrt(N/M) - 0.5)`
- Result measurement returning Python values, search register only (not oracle ancilla)
- Multiple-solution support — iteration formula accounts for M, same oracle marks multiple states
- OpenQASM export compatibility — existing export infrastructure, must work with Grover circuits

**Should have (competitive differentiators):**
- `@ql.grover_oracle` decorator — phase-marking wrapper around `@ql.compile`, enforces compute-phase-uncompute ordering
- Automatic oracle synthesis from Python predicates — `ql.grover(lambda x: x > 5, x)` without manual oracle construction
- Adaptive search for unknown M — exponential backoff when solution count not provided
- `qarray` integration — search over quantum array elements as search space

**Defer to v2+:**
- Quantum counting (`ql.count_solutions`) — requires phase estimation infrastructure, high complexity; adaptive search covers the practical case
- Full amplitude estimation with QPE — different use case than search, requires separate validation milestone
- Fixed-point amplitude amplification — advanced technique; standard Grover covers all near-term needs
- Custom state preparation — non-uniform initial superposition is an edge case not needed for MVP
- SAT/3-SAT oracle auto-generation — separate problem domain; document how to construct SAT oracles manually

### Architecture Approach

The architecture follows the existing three-layer pattern with no structural changes. New components live entirely in the Python layer (`src/quantum_language/grover.py`, optionally `amplitude_estimation.py`) with minimal Cython additions (~30 lines in `_core.pyx` to expose H and Z gates as `_apply_h_gate` and `_apply_z_gate`) and zero C backend changes. The oracle wraps `@ql.compile` rather than replacing it; the diffusion operator calls exposed H/Z/MCX primitives; the Grover loop orchestrates oracle and diffusion. The estimated file footprint is 4 new files and 4 small modifications to existing files.

The single most important architectural decision documented in research is the diffusion S_0 implementation: use the explicit X-MCZ-X pattern via existing MCX decomposition rather than `with x == 0`. The comparison-based approach unnecessarily allocates ancilla qubits and generates O(n^2) gates; the direct MCX pattern uses O(n) gates and zero ancilla.

**Major components:**
1. `OracleWrapper` (Python) — wraps `@ql.compile` output, enforces compute-phase-uncompute ordering, validates ancilla delta is zero on exit
2. `DiffusionOperator` (Python) — X-MCZ-X pattern using H/Z exposed via Cython, MCX from existing decomposition, zero ancilla
3. `GroverSearch` (Python) — main loop: initialize superposition, iterate oracle + diffusion `optimal_iterations(N, M)` times, measure search register
4. `grover_primitives.pxi` (Cython) — thin wrappers `hadamard_all(qarray)`, `apply_z(qbool)`, `multi_controlled_z(qarray, qbool)`
5. `AmplitudeEstimator` (Python, later phase) — IQAE using controlled Grover iterates, no QFT required

### Critical Pitfalls

1. **Phase oracle vs bit-flip oracle confusion** — Oracle sets a flag qubit (bit-flip) instead of multiplying marked state amplitude by -1 (phase). Algorithm runs without error but returns uniformly random results. Mitigation: `@ql.grover_oracle` decorator handles both types; auto-wraps bit-flip oracles with phase kickback (X-H-oracle-H-X on ancilla); user can specify `oracle_type='bitflip'` for automatic conversion. Address in Phase 2 (Oracle Infrastructure).

2. **Uncomputation destroys phase information** — The existing `qubit_saving_mode` eagerly uncomputes ancillas. Inside an oracle, phase kickback must occur before any uncomputation. If intermediate computation qubits are uncomputed before phase is kicked back to the search register, the phase mark is silently lost. Oracle appears correct but Grover does nothing. Mitigation: oracle decorator explicitly enforces compute-then-phase-then-uncompute ordering; defers all uncomputation to end of oracle scope. Address in Phase 2.

3. **Garbage qubits cause destructive interference** — Oracle intermediate results left un-uncomputed entangle with the search register. Diffusion then operates on the entangled state, destroying amplitude amplification. Output is maximally mixed. Mitigation: oracle decorator validates ancilla allocation delta is zero on exit; treat any leak as a hard error, not a warning. Address in Phase 2.

4. **Iteration count calculation error** — Formula is `floor(pi/4 * sqrt(N/M) - 0.5)`, not `floor(pi/4 * sqrt(N))`. Too many iterations oscillates probability back down; results are wrong but the circuit runs fine. Mitigation: `optimal_iterations(N, M)` helper is the only exposed API; warn loudly on manual iteration count that deviates more than 2x from optimal; validate against known-solution test cases. Address in Phase 4.

5. **Diffusion operator applied to wrong qubit subset** — Applying diffusion to ancilla or oracle output qubits destroys superposition without amplifying the search register. Mitigation: `ql.grover(search_space=x, oracle=f)` makes search register explicit; diffusion operator takes explicit qubit list validated against search register width; assertion before every diffusion application. Address in Phase 3 and 4.

6. **Arithmetic mode not in oracle cache key** — `compile.py` cache key includes `qubit_saving` mode but NOT `arithmetic_mode` (QFT vs Toffoli). Oracle compiled in QFT mode replayed in Toffoli mode produces wrong gate sequences with no error. Mitigation: add `ql.option('fault_tolerant')` to oracle cache key before any oracle caching is deployed. Must be fixed in Phase 2 before any other oracle work.

## Implications for Roadmap

Based on combined research, the implementation follows a strict dependency chain. Oracle infrastructure is the critical path — it is the most pitfall-dense phase, must be validated before Grover integration, and is a prerequisite for amplitude estimation. The suggested phase structure is:

### Phase 1: Gate Primitive Exposure
**Rationale:** H and Z gates exist in C but have no Python API. All higher-level components require them. This is the only gap between the current framework and a working Grover implementation. Zero risk, zero new dependencies, unblocks everything.
**Delivers:** `_apply_h_gate()`, `_apply_z_gate()`, `_apply_cz_gate()` in `_core.pyx`; `hadamard_all(qarray)` in `grover_primitives.pxi`; unit tests verifying gate emission at the circuit level.
**Uses:** Existing `h()`, `z()`, `cz()` C functions; existing Cython binding pattern from `_core.pyx`.
**Avoids:** Nothing directly, but establishes the tested primitive layer that phases 2-5 depend on.
**Research flag:** Standard patterns — no deeper research needed. Gate exposure is mechanical Cython work following existing patterns in `_core.pyx`.

### Phase 2: Oracle Infrastructure
**Rationale:** The most pitfall-dense phase in the project. Four of six critical pitfalls live here, all producing silent wrong results. Must be done before Grover loop work so that oracle correctness can be validated independently. Getting oracle semantics right first means the Grover loop can be tested by varying oracles rather than debugging oracle and loop simultaneously.
**Delivers:** `@ql.grover_oracle` decorator enforcing compute-phase-uncompute structure; phase kickback wrapper for bit-flip oracles; `arithmetic_mode` added to compile.py cache key; ancilla delta validation on oracle exit; tests with equality, range, and compound predicates; tests verifying phase marks survive uncomputation.
**Addresses:** Manual oracle mode (table stakes); `@ql.compile` integration (table stakes).
**Avoids:** Phase vs bit-flip confusion (Pitfall 1), uncomputation destroying phase (Pitfall 2), garbage qubit interference (Pitfall 3), cache key incompleteness (Pitfall 6), external state capture.
**Research flag:** Flag for design review before coding — the interaction between oracle scoping and the existing dependency tracking (`_start_layer`, `_end_layer`, `dependency_parents` in `qint.pyx`) needs explicit design before implementation. If that interaction proves complex, escalate to `/gsd:research-phase`.

### Phase 3: Diffusion Operator
**Rationale:** Self-contained implementation requiring only Phase 1 primitives. Low risk, textbook circuit pattern, zero ancilla. No interaction with oracle pitfalls.
**Delivers:** `DiffusionOperator` using X-MCZ-X pattern (zero ancilla, O(n) gates via existing MCX decomposition); explicit search qubit list parameter; validation assertion before every application; tests verifying phase flip on |0...0> state across widths 1-8.
**Addresses:** Diffusion operator (table stakes P1).
**Avoids:** Diffusion on wrong qubit subset (Pitfall 5 partial); comparison-based S_0 anti-pattern (O(n^2) gates, unnecessary ancilla).
**Research flag:** Standard patterns — no deeper research needed. X-MCZ-X is documented across IBM, Azure Quantum, and Qiskit sources.

### Phase 4: Grover Search Integration
**Rationale:** Composes Phases 2 and 3 into the complete algorithm. With oracle and diffusion independently validated, integration testing focuses on the iteration loop, measurement, and API surface.
**Delivers:** `GroverSearch` class; `optimal_iterations(N, M)` with correct formula including -0.5 term; `ql.grover(oracle, register, iterations=None, num_solutions=1, measure=True)` public API; end-to-end tests with known-solution oracles verifying peak probability at calculated iteration count; warning when user-specified iteration count deviates significantly from optimal.
**Addresses:** Basic `ql.grover()` (P1), automatic iteration count (P1), result measurement (P1), multiple solutions (P1), initial superposition auto-applied (eliminates Pitfall 12 from PITFALLS_GROVER.md).
**Avoids:** Iteration count errors (Pitfall 4), measuring oracle output instead of search register (Pitfall 5), hardcoded iterations (technical debt).
**Research flag:** Standard patterns — orchestration of validated components. No external research needed.

### Phase 5: Oracle Auto-Synthesis and Adaptive Search
**Rationale:** Primary differentiator vs Qiskit/Cirq/PennyLane. Enables `ql.grover(lambda x: x > 5, x)` instead of manual oracle construction. Depends on Phase 2 oracle infrastructure being proven. Separated from Phase 4 because compound predicate synthesis has uncertain implementation complexity.
**Delivers:** Predicate-to-oracle compilation for `qint` comparisons and compound conditions (`(x > 10) & (x < 50)`); adaptive search with exponential backoff for unknown M; `qarray` integration.
**Addresses:** Automatic oracle synthesis (P2 differentiator), adaptive search for unknown M (P2), `qarray` integration (P2).
**Avoids:** Multiple solutions unknown leading to wrong iteration count (Pitfall 9) — adaptive search handles this via exponential backoff.
**Research flag:** Needs `/gsd:research-phase` — compound predicate oracle synthesis (how `@ql.compile` tracks which qubit represents the combined condition output of `(x > 10) & (x < 50)`) is not fully characterized from research alone and is the primary unknown in this phase.

### Phase 6: Amplitude Estimation (IQAE)
**Rationale:** Different use case from search (probability estimation vs value finding). Depends on validated Grover iterate from Phase 4. IQAE avoids QFT entirely, keeping circuit depth and implementation complexity low. The controlled-oracle semantics pitfall (Pitfall 7: only the phase part should be controlled, not compute/uncompute) is easier to address correctly after oracle infrastructure is battle-tested.
**Delivers:** `AmplitudeEstimator` using IQAE variant; `ql.amplitude_estimate(oracle, register, epsilon=0.01, confidence=0.95)` API; validation that oracle inverse access works; tests comparing estimated vs known amplitudes across precision settings.
**Addresses:** Amplitude estimation (P3, after core validation).
**Avoids:** No inverse access breaking amplitude estimation (Pitfall 5), wrong controlled-oracle semantics (Pitfall 7), QPE exponential depth trap.
**Research flag:** IQAE algorithm is standard patterns (no research needed). However, controlled-oracle semantics design (Pitfall 7) needs explicit planning — only the phase part of the oracle should be controlled, not compute/uncompute — before coding begins.

### Phase Ordering Rationale

- Phases 1 through 4 form a strict dependency chain: primitives enable oracle enables diffusion enables integration. No phase can be meaningfully tested without its predecessors.
- Phase 5 (auto-synthesis) is separated from Phase 4 (core Grover) because compound predicate synthesis has uncertain implementation complexity. Core Grover ships and delivers real value while Phase 5 is in progress.
- Phase 6 (amplitude estimation) is last because it is a genuinely different feature, requires all previous phases, and controlled-oracle semantics (Pitfall 7) is easiest to address correctly after oracle infrastructure is proven in production.
- All oracle pitfalls are concentrated in Phase 2, so Phase 4 integration testing is clean and debuggable.
- The pitfall-to-phase mapping from PITFALLS_GROVER.md confirms this ordering: Phase 1 pitfalls map to Phase 2, Phase 2 pitfalls map to Phase 4, Phase 3 pitfalls map to Phase 6.

### Research Flags

Phases needing deeper research or design review during planning:
- **Phase 2:** Interaction between oracle scoping and the existing `_start_layer`/`_end_layer`/`dependency_parents` dependency tracking in `qint.pyx`. Design before coding; escalate to `/gsd:research-phase` if interaction is complex.
- **Phase 5:** Compound predicate oracle synthesis — how `@ql.compile` tracks multi-condition qubit outputs into a single phase-markable result. Likely needs `/gsd:research-phase`.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Mechanical Cython gate exposure following existing patterns in `_core.pyx`.
- **Phase 3:** X-MCZ-X diffusion is textbook, documented across IBM/Azure/Qiskit sources.
- **Phase 4:** Orchestration of validated components; iteration formula is mathematically settled.
- **Phase 6 (IQAE algorithm):** Published and well-documented. Only the controlled-oracle design needs a planning step, not external research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Direct codebase analysis confirms `h()`, `z()`, `mcx()`, `cz()` in `gate.h/gate.c`; `@ql.compile` adjoint/controlled derivation in `compile.py`; zero new dependencies confirmed |
| Features | HIGH | Table stakes derived from Qiskit/Cirq/PennyLane/Qrisp gap analysis; differentiators (auto-synthesis) validated against competitor APIs; IQAE vs QPE decision backed by published literature |
| Architecture | HIGH | Three-layer integration pattern follows existing codebase conventions; new/modified file inventory explicit; MCX-based S_0 design decision backed by gate-count analysis |
| Pitfalls | HIGH | Critical pitfalls verified from quantum computing literature (Tang & Wright 2025 for inverse requirement; Wikipedia/Azure Quantum for iteration formula); cache key gap verified from `compile.py` source code inspection |

**Overall confidence:** HIGH

### Gaps to Address

- **Dependency tracking interaction:** How `_start_layer`/`_end_layer`/`dependency_parents` in `qint.pyx` interacts with oracle-scoped operations is not fully characterized from research alone. Address during Phase 2 planning by reading those sections of `qint.pyx` before designing the oracle decorator. May require explicit oracle epoch tracking.
- **Compound predicate qubit tracking:** For auto-synthesis of `(x > 10) & (x < 50)` predicates, it is unclear how the framework currently tracks which final qubit represents the combined condition result. Address during Phase 5 planning; likely requires reading `@ql.compile` gate capture internals.
- **IQAE circuit interface design:** IQAE algorithm is algorithmically clear, but the specific interface for repeated controlled Grover operator application within the framework's gate capture model has not been prototyped. Low risk — IQAE avoids the more complex QPE circuit — but needs a design pass before Phase 6 coding begins.

## Sources

### Primary (HIGH confidence)
- `c_backend/include/gate.h`, `c_backend/src/gate.c` — confirmed existence of `h()`, `z()`, `cz()`, `mcx()`, `emit_ccx_clifford_t()`
- `src/quantum_language/compile.py` — confirmed `_derive_controlled_gates()`, `_InverseCompiledFunc`, cache key structure (missing `arithmetic_mode`)
- `src/quantum_language/qint.pyx` lines 584-679 — confirmed `with` conditional context implementation
- [Grover's Algorithm - IBM Quantum Documentation](https://quantum.cloud.ibm.com/docs/en/tutorials/grovers-algorithm) — standard implementation pattern
- [Grover's Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Grover's_algorithm) — iteration formula
- [Azure Quantum - Grover Theory](https://learn.microsoft.com/en-us/azure/quantum/concepts-grovers) — mathematical foundations and iteration formula with -0.5 term
- [Iterative QAE - npj Quantum Information](https://www.nature.com/articles/s41534-021-00379-1) — IQAE as preferred variant for NISQ
- [Tang & Wright 2025, arXiv:2507.23787](https://arxiv.org/abs/2507.23787) — amplitude amplification and estimation require oracle inverse access

### Secondary (MEDIUM confidence)
- [Qiskit Grover Tutorial](https://qiskit-community.github.io/qiskit-algorithms/tutorials/06_grover.html) — phase kickback technique, oracle type classification
- [Qrisp Uncomputation Documentation](https://qrisp.eu/reference/Core/Uncomputation.html) — uncomputation timing semantics in oracle context
- [Iterative QAE arXiv:1912.05559](https://arxiv.org/abs/1912.05559) — IQAE without phase estimation, algorithm details
- [Automated Oracle Synthesis arXiv:2304.03829](https://arxiv.org/abs/2304.03829) — oracle synthesis methods relevant to Phase 5

### Tertiary (LOW confidence)
- [PennyLane Amplitude Amplification Demo](https://pennylane.ai/qml/demos/tutorial_intro_amplitude_amplification) — alternative framework API design for comparison
- [QRISP Quantum Counting Documentation](https://qrisp.eu/reference/Algorithms/quantum_counting.html) — API design patterns for quantum counting (deferred feature)

---
*Research completed: 2026-02-19*
*Ready for roadmap: yes*
