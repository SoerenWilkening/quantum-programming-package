# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v5.0 — Advanced Arithmetic & Compilation

**Shipped:** 2026-02-26
**Phases:** 7 | **Plans:** 19

### What Was Built
- Quantum counting API (`ql.count_solutions()`) wrapping IQAE for exact solution count estimation
- C-level restoring divmod replacing broken QFT division; Beauregard modular reduction replacing orphan-qubit `_reduce_mod`
- Beauregard modular Toffoli arithmetic (12 C functions: add/sub/mul mod N with CQ/QQ/controlled variants)
- Depth/ancilla tradeoff with runtime CLA/CDKM dispatch via `ql.option('tradeoff', ...)`
- Parametric compilation (`@ql.compile(parametric=True)`) with topology-safe probe/detect/replay
- Full requirements closure: 20/20 satisfied, milestone audit PASSED

### What Worked
- Milestone audit process caught 7 procedural gaps (missing VERIFICATION.md files, unchecked requirements) before completion — gap closure phases 95-96 addressed all of them cleanly
- C-level arithmetic implementation pattern (established in v3.0) scaled well to modular Beauregard sequence — 12 functions implemented efficiently
- Exhaustive verification (statevector widths 2-4, MPS widths 5-8) caught the CDKM register ordering bug early
- Parametric compilation's defensive topology check prevents silent correctness errors

### What Was Inefficient
- First milestone audit found gaps that could have been prevented by writing VERIFICATION.md during execution (not after)
- QQ division ancilla leak is a fundamental algorithmic limitation — investigating the repeated-subtraction approach consumed time that could have been spent accepting the limitation earlier
- Phase 95 (verification closure) and Phase 96 (tech debt cleanup) were reactive; building verification into execution phases would have eliminated them

### Patterns Established
- Beauregard 8-step pattern for modular addition: add a, sub N, copy sign, cond add N, sub a, flip, copy sign, add a
- Set-once enforcement pattern: module-level flag frozen after first arithmetic operation
- _get_mode_flags() centralized cache key construction pattern
- Parametric probe/detect/replay lifecycle for compile-once semantics

### Key Lessons
1. **Run milestone audit early**: Audit before all phases are complete to catch procedural gaps while context is fresh
2. **Write VERIFICATION.md during execution, not after**: Verification should be part of phase execution, not a separate gap-closure phase
3. **Accept algorithmic limitations early**: The QQ division ancilla leak is fundamental — documenting and moving on was the right call
4. **Modular arithmetic forces RCA**: CLA subtraction limitation means all modular ops must bypass the tradeoff system — encode constraints in code, not documentation

### Cost Observations
- Model mix: ~90% opus, ~10% haiku (research agents)
- 80 commits across 3 days
- Notable: Phases 90-94 (5 implementation phases) completed in 2 days; Phases 95-96 (closure) took 1 additional day

---

## Milestone: v6.0 — Quantum Walk Primitives

**Shipped:** 2026-03-03
**Phases:** 6 | **Plans:** 11

### What Was Built
- QWalkTree class with one-hot height register, per-level branch registers, predicate interface with mutual exclusion validation
- D_x local diffusion with Ry cascade and correct amplitude angles per Montanaro 2015, statevector-verified for d=2..5
- Walk operators R_A/R_B with compiled walk step U = R_B * R_A, qubit disjointness verification
- Variable branching with predicate-driven child counting, conditional Ry rotation, multi-controlled V-gate decomposition
- Iterative power-method detection algorithm with 3/8 threshold and SAT demo within 17-qubit budget
- Full requirements closure: 18/18 satisfied, 130 walk tests all pass

### What Worked
- Pure Python implementation strategy: walk module is compositional (composing existing framework primitives), so no new C code was needed — fast iteration
- Milestone audit before completion caught 4 verification gaps (missing VERIFICATION.md) which were cleanly resolved by Phase 102 — lesson from v5.0 applied
- Statevector verification at every phase caught the height-controlled dispatch bug (Phase 98) and compile forward-call tracking conflict (Phase 99) immediately
- V-gate CCRy decomposition pattern cleanly worked around the nested `with qbool:` framework limitation without requiring framework changes

### What Was Inefficient
- Phase 102 (gap closure) was still needed despite v5.0 lesson — VERIFICATION.md was not written during Phase 100/101 execution
- Raw predicate qubit allocation limits practical demos to depth=1 trees — compiled predicate support would have been more impactful than raw predicates for SAT instances
- Detection algorithm simplified to threshold-only (removed reference comparison and marked_leaves approaches) — earlier scoping would have saved the iteration time in Phase 101

### Patterns Established
- One-hot height encoding for tree depth tracking with single-qubit control per level
- Flat cascade gate planning: pre-plan ops at construction, compile via @ql.compile, replay in controlled context
- _make_qbool_wrapper(qubit_idx) for wrapping existing physical qubits without allocation
- _all_qubits_register() for @ql.compile wrapping to prevent forward-call tracking conflicts
- Norm-based unitarity verification when qubit count grows between operations (raw predicate expansion)

### Key Lessons
1. **Pure Python when compositional**: Walk module composes existing qint/qbool/compile primitives — no C code needed. Future modules should assess whether they're computational (needs C) or compositional (Python only)
2. **Write VERIFICATION.md during phase execution**: v5.0 lesson still not internalized — Phase 102 gap closure was avoidable
3. **Framework limitations are design constraints**: The nested `with qbool:` limitation shaped the entire diffusion architecture (V-gate decomposition, flat cascade planning) — document limitations in CLAUDE.md for faster future reference
4. **Qubit budget shapes algorithm design**: The 17-qubit simulation ceiling forced predicate=None in measurement, threshold-only detection, and depth=1 demos — budget constraints should be explicit in requirements

### Cost Observations
- Model mix: ~90% opus, ~10% haiku (research agents)
- 31 commits across 2 days
- Notable: Phases 97-100 (4 implementation phases) completed in 1 day; Phase 101 (detection) took ~1 hour; Phase 102 (closure) took ~10 min

---

## Milestone: v6.1 — Quantum Chess Demo

**Shipped:** 2026-03-05
**Phases:** 4 | **Plans:** 8

### What Was Built
- Chess board encoding module with knight/king attack patterns, legal move filtering, and deterministic sorted move enumeration
- Compiled move oracle via `@ql.compile(inverse=True)` with factory pattern for quantum state manipulation
- Walk register scaffolding: one-hot height register, per-level branch registers, forward/reverse oracle replay for board state derivation
- Local diffusion D_x with Montanaro angles and variable branching with cascade fallback
- Full walk operators R_A/R_B with height-controlled diffusion cascade and compiled walk step U = R_B * R_A
- Demo scripts with manual walk circuit stats and side-by-side QWalkTree comparison

### What Worked
- v6.0's pure Python approach carried forward perfectly — chess_encoding.py and chess_walk.py compose existing framework primitives with zero new C code
- Oracle factory pattern (`_make_apply_move()`) cleanly encapsulates classical move specs in @ql.compile closures — inverse support works correctly
- Milestone audit ran before completion and PASSED on first try (14/14 requirements, 4/4 phases, 14/14 integration, 2/2 E2E flows) — first clean audit without gap closure phases
- Separate qarray args pattern (wk_arr, bk_arr, wn_arr) solved the 64-qubit qint limit for compile cache keys
- 122+ tests across 4 test files, all passing — comprehensive coverage without verification gaps

### What Was Inefficient
- Nyquist validation only partial for Phases 104-106 (draft VALIDATION.md with nyquist_compliant: false) — validation infrastructure gap persists from v6.0
- Demo smoke tests require patched walk_step to avoid OOM in CI — real compilation needs 8GB+ RAM, limiting automated verification
- QWalkTree cascade fallback bug found during Phase 106-02 (comparison script) — integration bug that should have been caught by QWalkTree's own test suite

### Patterns Established
- Oracle factory pattern: `_make_apply_move()` creates @ql.compile function with classical move_specs baked into closure
- Separate qarray args per piece type for compile cache key + inverse support
- Forward/reverse oracle replay for deriving board state at any tree node from branch register history
- Cascade fallback for large branching factors (NotImplementedError -> empty ops)
- Dual-patch test pattern for CI safety (mock both manual and API walk_step)

### Key Lessons
1. **First clean milestone audit**: v6.1 passed audit without gap closure phases — writing VERIFICATION.md during execution (from v5.0/v6.0 lessons) finally internalized
2. **Demo-focused milestones are fast**: 4 phases in 3 days — composing existing primitives into a domain demo is much faster than building new framework infrastructure
3. **Comparison scripts reveal integration bugs**: chess_comparison.py found QWalkTree cascade fallback bug — always include a comparison/reference implementation
4. **OOM in CI is a testing ceiling**: Manual walk compilation exceeds CI memory — future demos should plan for mock-based testing from the start

### Cost Observations
- Model mix: ~90% opus, ~10% haiku (research agents)
- 52 commits across 3 days
- Notable: Phases 103-104 completed in 1 day, Phase 105-106 in 2 days (walk_step compilation complexity)

---

## Milestone: v7.0 — Compile Infrastructure

**Shipped:** 2026-03-08
**Phases:** 5 | **Plans:** 10

### What Was Built
- CallGraphDAG module with rustworkx PyDAG backend, numpy bitmask overlap computation, and parallel group detection
- Multi-level compilation: opt=1 (call graph DAG only), opt=2 (selective merge), opt=3 (full expansion, backward compat)
- Per-node gate count, depth, T-count extraction with aggregate metrics, DOT export, and formatted compilation reports
- Selective sequence merging with overlapping-qubit merge candidates and cross-boundary gate optimization
- Statevector equivalence verification proving merged circuits correct at all opt levels
- Full regression at all opt levels with GC-based OOM prevention and selective parametrization

### What Worked
- Milestone audit identified 6 orphaned Phase 107 requirements (missing VERIFICATION.md) — gap closure Phase 111 resolved all cleanly in 1 plan
- Statevector.from_instruction() for equivalence testing avoided AerSimulator overhead and gave exact comparisons
- GC autouse fixture in Phase 110-03 solved persistent OOM from qint.__del__ stale gate injection — pattern reusable across future test suites
- Selective opt_level parametrization (@opt_safe marker) avoided 3x test explosion while still verifying behavioral correctness at all opt levels
- rustworkx PyDAG and numpy bitmask overlap gave clean, fast graph primitives without reinventing graph algorithms

### What Was Inefficient
- Phase 111 (verification closure) was still needed — VERIFICATION.md not written during Phase 107 execution (recurring pattern from v5.0, v6.0)
- Phase 110-03 (OOM fix) was reactive — the gc.collect() need could have been anticipated from qint.__del__ behavior in earlier milestones
- Bare `except Exception: pass` in _merge_and_optimize shipped as tech debt — could have been caught by a stricter review during Phase 109

### Patterns Established
- numpy bitmask overlap for qubit set intersection (uint64 AND + popcount)
- Builder stack context for tracking nested compiled function calls
- opt parameter NOT in cache key (DAG building is observational, doesn't change semantics)
- gc.collect() autouse fixture pattern for test suites with qint memory lifecycle
- Selective parametrization via @opt_safe marker for opt-level regression testing

### Key Lessons
1. **VERIFICATION.md during execution still not automatic**: Phase 111 gap closure for Phase 107 — 4th milestone with this pattern (v5.0, v6.0, v6.1 fixed it, v7.0 regressed)
2. **GC matters for quantum objects**: qint.__del__ triggers gate injection that causes OOM across test boundaries — gc.collect() between tests is now mandatory
3. **Observational DAG is the right abstraction**: opt parameter doesn't change circuit semantics, just adds metadata — keeping it out of cache key was the correct design
4. **Statevector comparison needs global phase normalization**: Two equivalent circuits may differ by a global phase factor — first-nonzero-amplitude alignment handles this cleanly

### Cost Observations
- Model mix: ~90% opus, ~10% haiku (research agents)
- 104 commits across 4 days
- Notable: Phases 107-109 (3 implementation phases) completed in 2 days; Phase 110 (verification) took 1.5 days due to OOM debugging; Phase 111 (closure) took <1 hour

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v3.0 | 11 | 35 | Established C-level Toffoli arithmetic pattern |
| v4.0 | 6 | 18 | Oracle infrastructure with validation-at-build-time |
| v4.1 | 8 | 21 | Quality-focused: security, coverage, size reduction |
| v5.0 | 7 | 19 | Milestone audit process; gap closure phases |
| v6.0 | 6 | 11 | Pure Python compositional module; V-gate workarounds |
| v6.1 | 4 | 8 | Domain demo composing framework primitives; first clean audit |
| v7.0 | 5 | 10 | Multi-level compilation; observational DAG; gc autouse for test OOM |

### Cumulative Quality

| Milestone | Requirements | Audit Score | Tech Debt Items |
|-----------|-------------|-------------|-----------------|
| v4.0 | 16 satisfied | N/A | 3 deferred bugs |
| v4.1 | N/A (quality) | N/A | 3 deferred bugs |
| v5.0 | 20/20 | PASSED (20/20 + 7/7 + 20/20 + 8/8) | 12 non-blocking |
| v6.0 | 18/18 | gaps_found → CLOSED (Phase 102) | 3 non-blocking |
| v6.1 | 14/14 | PASSED (first try, no gaps) | 0 |
| v7.0 | 15/15 | PASSED (after Phase 111 gap closure) | 1 (bare except) |

### Top Lessons (Verified Across Milestones)

1. **C-level implementation scales well**: Pattern from v3.0 CDKM → v5.0 Beauregard confirms that implementing at C level first, then wiring through Cython, is the right approach
2. **Exhaustive verification catches real bugs**: CDKM register ordering (v5.0), QFT qubit mapping (v3.0), comparison MSB (v4.0), height-controlled dispatch (v6.0) — all caught by systematic testing
3. **Profile before optimizing**: v2.2 principle continues to pay off — data-driven tradeoff threshold (width 4) in v5.0
4. **Compositional modules stay in Python**: Walk module (v6.0) composes existing primitives without C code — assess compute vs compose before choosing implementation language
