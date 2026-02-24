# Requirements: Quantum Assembly

**Defined:** 2026-02-22
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v4.1 Requirements

Requirements for v4.1 Quality & Efficiency milestone. Each maps to roadmap phases.

### Bug Fixes

- [ ] **BUG-01**: Fix 32-bit multiplication segfault (buffer overflow in C backend)
- [ ] **BUG-02**: Fix qarray `*=` in-place multiplication segfault
- [x] **BUG-03**: Fix qiskit_aer undeclared dependency (add to pyproject.toml verification group, add friendly ImportError message)
- [ ] **BUG-04**: Fix mixed-width QFT addition off-by-one (BUG-WIDTH-ADD)
- [ ] **BUG-05**: Fix QFT controlled QQ addition CCP rotation errors at width 2+ (BUG-CQQ-QFT)
- [ ] **BUG-06**: Fix MSB comparison leak in division (BUG-DIV-02, 9 cases per div/mod test file)
- [ ] **BUG-07**: Fix controlled multiplication scope uncomputation corruption (BUG-COND-MUL-01)
- [ ] **BUG-08**: Fix QFT division/modulo pervasive failures at all tested widths (BUG-QFT-DIV)
- [-] **BUG-09**: Fix _reduce_mod result corruption (BUG-MOD-REDUCE) -- **Explicitly deferred**: requires Beauregard-style algorithm redesign (see rationale in Future Requirements)

### Tech Debt

- [x] **DEBT-01**: Remove dead QPU.c/QPU.h stubs and all references across C/Cython/Python layers
- [x] **DEBT-02**: Automate qint_preprocessed.pyx generation with build-time sync and CI drift check
- [x] **DEBT-03**: Remove duplicate/dead code identified by vulture scan (unused Python functions, unreachable code)
- [x] **DEBT-04**: Document hardcoded sequence generation process and regeneration instructions

### Security & Hardening

- [ ] **SEC-01**: Add circuit pointer validation at all Cython boundary entry points (prevent unsafe casts in _core.pyx)
- [ ] **SEC-02**: Add qubit_array bounds checking before writes to scratch buffer (prevent silent buffer overrun)
- [ ] **SEC-03**: Run cppcheck static analysis on C backend and fix all HIGH severity findings

### Performance

- [ ] **PERF-01**: Fix optimizer latent loop direction bug (++i should be --i in smallest_layer_below_comp)
- [ ] **PERF-02**: Replace optimizer linear scan with binary search for gate placement (O(L) to O(log L))
- [ ] **PERF-03**: Reduce @ql.compile replay overhead (profile gate injection, optimize dict iteration)

### Binary Size

- [x] **SIZE-01**: Apply section garbage collection compiler flags (-ffunction-sections, -fdata-sections, --gc-sections)
- [x] **SIZE-02**: Strip symbols from release builds (-s link flag or post-build strip)
- [x] **SIZE-03**: Evaluate -Os vs -O3 for sequence files with benchmark verification (no performance regression)

### Test Coverage

- [x] **TEST-01**: Add pytest-cov infrastructure with Cython coverage plugin and coverage config in pyproject.toml
- [x] **TEST-02**: Measure baseline coverage and identify critical untested paths
- [ ] **TEST-03**: Add tests for nested with-blocks (quantum conditionals within quantum conditionals)
- [ ] **TEST-04**: Add tests for circuit reset behavior (circuit state after reset_circuit)
- [ ] **TEST-05**: Integrate C backend tests (test_allocator_block, test_reverse_circuit) into pytest via subprocess wrapper
- [ ] **TEST-06**: Convert xfail markers to passing tests for all bugs fixed in this milestone

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Uncomputation Architecture Redesign
- **BUG-06**: Fix MSB comparison leak in division (BUG-DIV-02) — requires `__lt__`/`__gt__` to explicitly uncompute widened comparison temporaries, or redesigning comparison to avoid them entirely
- **BUG-08**: Fix QFT division/modulo pervasive failures (BUG-QFT-DIV) — likely resolves once BUG-06 ancilla leak is fixed; root cause: `>=` creates widened temps with `operation_type=None` and `creation_scope=0`, invisible to cascade uncomputation and lazy GC
- **BUG-09**: Fix _reduce_mod result corruption (BUG-MOD-REDUCE) — **Explicitly deferred**. Root cause: `_reduce_mod` uses iterative `>=` comparison and conditional subtraction; each comparison allocates temporary widened qints that entangle with the value register; across multiple iterations, un-uncomputed comparison qbools accumulate entanglement, corrupting the remainder (Phase 38 research, Phase 86-03 findings). A simple fix is insufficient because the uncomputation architecture cannot handle orphan temporaries from comparison operators (`operation_type=None`, `creation_scope=0`, `_start_layer=_end_layer=0`) — these temporaries are invisible to both cascade uncomputation and lazy GC cleanup. Required approach: Beauregard-style modular arithmetic (2003) using a fundamentally different circuit topology: `(a+b) mod N` implemented as add(a,b), sub(N), add(N) controlled by sign bit, sub(b) controlled by sign bit, requiring careful ancilla management and purpose-built circuit structure. No specific future phase assigned.

### Parametric Compilation
- **PAR-01**: Compile once for all classical values
- **PAR-02**: Parametric gate sequences

### Advanced Compilation
- **ADV-01**: Resource estimation for compiled functions
- **ADV-02**: Serialization of compiled functions to disk
- **ADV-03**: Compiled function composition

### Advanced Optimization
- **ADV-OPT-01**: Hardcoded sequences for multiplication (EVAL-01 recommends "investigate")
- **ADV-OPT-03**: SIMD vectorization for bulk gate operations
- **ADV-OPT-04**: Multi-threaded circuit building

### Fault-Tolerant Features
- **OPT-01**: Automatic depth/ancilla tradeoff (RCA vs CLA selection)
- **FTE-02**: Modular arithmetic via Toffoli gates (for Shor's algorithm)

### Grover/Search Extensions
- **GADV-01**: Quantum counting (`ql.count_solutions`) for exact M estimation
- **GADV-02**: Fixed-point amplitude amplification
- **GADV-03**: Custom state preparation (non-uniform initial superposition)
- **GSPEC-01**: SAT/3-SAT oracle auto-generation from CNF formulas
- **GSPEC-02**: Database search oracle from classical data structure

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Parallel test execution (pytest-xdist) | Global circuit state makes parallel tests produce corrupt circuits |
| Full type checking (mypy) | 60K lines of Cython unsupported by mypy; massive stub effort |
| Fuzz testing harness | Valuable but separate project; needs dedicated harness design |
| Refactoring global circuit state | Foundational architecture change; too large for quality milestone |
| Kogge-Stone CLA implementation | Stubs exist but feature addition, not quality work |
| Controlled bitwise operations | Feature addition, not quality work |
| GUI/interactive debugging | Complex infrastructure beyond quality scope |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 87 | Pending |
| BUG-02 | Phase 87 | Pending |
| BUG-03 | Phase 82 | Complete |
| BUG-04 | Phase 86 | Complete |
| BUG-05 | Phase 86 | Complete |
| BUG-06 | Future (uncomputation redesign) | Deferred |
| BUG-07 | Phase 87 | Pending |
| BUG-08 | Future (uncomputation redesign) | Deferred |
| BUG-09 | Future (Beauregard redesign) | Explicitly deferred |
| DEBT-01 | Phase 83 | Complete |
| DEBT-02 | Phase 83 | Complete |
| DEBT-03 | Phase 83 | Complete |
| DEBT-04 | Phase 83 | Complete |
| SEC-01 | Phase 84 | Pending |
| SEC-02 | Phase 84 | Pending |
| SEC-03 | Phase 84 | Pending |
| PERF-01 | Phase 85 | Pending |
| PERF-02 | Phase 85 | Pending |
| PERF-03 | Phase 85 | Pending |
| SIZE-01 | Phase 88 | Complete |
| SIZE-02 | Phase 88 | Complete |
| SIZE-03 | Phase 88 | Complete |
| TEST-01 | Phase 82 | Complete |
| TEST-02 | Phase 82 | Complete |
| TEST-03 | Phase 89 | Pending |
| TEST-04 | Phase 89 | Pending |
| TEST-05 | Phase 89 | Pending |
| TEST-06 | Phase 89 | Pending |

**Coverage:**
- v4.1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-02-22*
*Last updated: 2026-02-24 after Phase 87 BUG-09 deferral*
