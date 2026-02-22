# Project Research Summary

**Project:** Quantum Assembly v4.1 Quality & Efficiency
**Domain:** Bug fixes, tech debt cleanup, security hardening, performance optimization, binary size reduction, and test coverage for a C/Cython/Python quantum programming framework
**Researched:** 2026-02-22
**Confidence:** HIGH

## Executive Summary

The v4.1 milestone is a consolidation milestone that addresses 9 known bugs, accumulated tech debt, security vulnerabilities, and test coverage gaps in the Quantum Assembly framework. Research across four domains (stack, features, architecture, pitfalls) confirms that the existing tool stack (Python 3.11+, Cython 3.x, C23 backend, pytest, ASan, Valgrind, py-spy, memray) is comprehensive — only 3 pip packages (pytest-cov, coverage, vulture) and 1 system tool (cppcheck) need to be added. The existing architecture is sound and does not change: all v4.1 work operates within the established three-layer design (C backend -> Cython bridge -> Python frontend), fixing from the bottom up and validating from the top down.

The dominant risk is regression cascade from arithmetic bug fixes. The 7 carry-forward bugs all touch shared C backend code paths (IntegerAddition.c, IntegerComparison.c, ToffoliAddition*.c). The `sequence_t` cache and qubit offset mapping create non-obvious couplings: fixing `CQ_add` affects every operation that internally calls it (multiplication, division, comparisons). One additional critical finding emerged from direct code inspection: the optimizer's `smallest_layer_below_comp()` function contains a latent infinite-loop bug (`++i` where `--i` was intended) that works by accident in the common case but could cause buffer overreads under specific gate placement patterns. This bug must be fixed as part of the optimizer binary-search improvement, not separately.

The binary size opportunity is significant and low-risk. Seven compiled `.so` extension modules total approximately 134 MB because every module statically links all 105 hardcoded sequence C files (~344K lines). Compiler flags (`-ffunction-sections`, `-fdata-sections`, `-Wl,--gc-sections`, strip) can reduce this by 30-50% with zero code changes. A more impactful structural change — factoring the repeated 15-gate Clifford+T CCX decomposition into a shared helper — could reduce C source from 344K to ~200K lines and further reduce binary size. BUG-MOD-REDUCE is the most complex carry-forward bug: it requires a fundamentally different circuit topology (Beauregard-style modular reduction) rather than an incremental patch and is a strong candidate for deferral again.

## Key Findings

### Recommended Stack

The existing stack requires minimal additions. Three pip packages close specific gaps: `pytest-cov>=6.0` + `coverage[toml]>=7.4` for coverage measurement (enabling the Cython.Coverage plugin via the existing `QUANTUM_PROFILE=1` env var), and `vulture>=2.12` for dead code detection beyond what ruff F401/F841 catches. One system tool — `cppcheck>=2.14` — provides C static analysis that catches the specific buffer overrun and null dereference risks identified in the codebase audit. All other tooling (profiling, debugging, C testing) already exists. For binary size reduction no new tools are needed — the changes are compiler flags in `setup.py`.

**Core technologies (additions only):**
- `pytest-cov>=6.0` + `coverage[toml]>=7.4`: Coverage measurement — enables data-driven test writing; Cython.Coverage plugin maps lines back to `.pyx` files via the existing `QUANTUM_PROFILE=1` build mode
- `vulture>=2.12`: Dead code detection — finds unused functions, methods, and classes that ruff F401/F841 does not detect; confidence scoring (60-100%) reduces false positives
- `cppcheck>=2.14`: C static analysis — detects buffer overruns, null dereference, and array bounds issues in `c_backend/src/` without running code; runs locally with no cloud upload
- `qiskit-aer>=0.14` in `[verification]` optional extras: Declares the currently undeclared dependency; fixes bare `ModuleNotFoundError` for all users

**What NOT to add:** pytest-xdist (global circuit state makes parallel tests corrupt), mypy (Cython `.pyx` unsupported), gcov/lcov (C code compiled into Cython extensions, not standalone), fuzz testing harness (out of scope), full LTO (previously disabled due to GCC bug — evaluate ThinLTO for Clang only with empirical testing).

### Expected Features

**Must have (table stakes — milestone incomplete without these):**
- Fix BUG-CQQ-QFT — QFT controlled QQ addition emits incorrect CCP rotations at width 2+; blocks all controlled QFT arithmetic
- Fix BUG-QFT-DIV — QFT division pervasively broken; cascades from BUG-CQQ-QFT and BUG-WIDTH-ADD
- Fix BUG-COND-MUL-01 — Controlled multiplication corrupts result register via scope uncomputation; blocks oracle-based algorithms
- Fix BUG-WIDTH-ADD — Off-by-one in mixed-width QFT addition; qubit offset calculation error in IntegerAddition.c
- Fix BUG-DIV-02 — MSB comparison ancilla not cleaned up between division loop iterations; 9 failures per test file
- Fix 32-bit multiplication segfault — `MAXLAYERINSEQUENCE` constant insufficient for 32-bit QFT multiply in IntegerMultiplication.c
- Fix qarray `*=` segfault — In-place multiply on array elements crashes the process
- Declare `qiskit-aer` dependency — Removes bare `ModuleNotFoundError` for all users (trivial, low-risk fix)
- Test coverage measurement setup — Cannot improve coverage without measuring it first (pytest-cov + coverage config)

**Should have (meaningful quality improvement):**
- Fix BUG-MOD-REDUCE — Requires Beauregard-style circuit redesign; HIGH complexity; strong candidate for deferral
- Optimizer binary search — O(log L) vs O(L) per gate; also fixes the latent infinite-loop bug in `smallest_layer_below_comp()`
- Binary size reduction via compiler flags — 30-50% reduction with zero code changes
- Clifford+T sequence factoring — ~150K line source reduction, ~5-10 MB binary reduction
- Dead code removal (QPU.c/QPU.h stubs) — Empty files since v1.1; mechanical removal
- Automate `qint_preprocessed.pyx` generation — Enforce via `.gitignore` and pre-commit check
- Circuit pointer validation — Add `_get_validated_circuit()` at all 15-20 raw cast sites in `_core.pyx`
- `qubit_array` bounds checking — Validate slot count before writing into the 384-element scratch buffer
- C test integration into pytest — Subprocess wrapper around existing C Makefile targets

**Defer to v4.2+:**
- Full DAG-based circuit IR rewrite — Architectural change touching every layer; v5.0+ effort
- BUG-MOD-REDUCE (if not feasible) — Document as requiring Beauregard redesign; track for dedicated milestone
- Comprehensive mutation testing — Computationally prohibitive (millions of Qiskit simulation runs)
- Coverage target enforcement (e.g., 90% line coverage) — Misleading metric for quantum circuit libraries; behavioral verification matters more
- PyPy compatibility — `__del__`-based uncomputation depends on CPython GC ordering

### Architecture Approach

The v4.1 milestone does not change the architecture. The three-layer design (C backend -> Cython bridge -> Python frontend) is validated and stays. All changes are in-place modifications within existing layers, following the "fix from the bottom up, validate from the top down" principle. The bug dependency graph is clear: BUG-WIDTH-ADD and BUG-CQQ-QFT are root causes; BUG-QFT-DIV is a compound bug that resolves when those are fixed; BUG-COND-MUL-01 is independent (scope/lifecycle issue in Cython); BUG-MOD-REDUCE requires algorithm redesign. The 32-bit segfault traces to `MAXLAYERINSEQUENCE` being a compile-time constant insufficient for wide multiplication.

**Components modified in v4.1 (no new components):**
1. **C backend (`c_backend/src/`)** — Bug fixes in IntegerAddition.c, IntegerMultiplication.c, IntegerComparison.c; optimizer binary search in optimizer.c; Clifford+T sequence factoring; no module structure changes
2. **Cython bridge (`*.pyx`, `*.pxi`)** — Pointer validation, bounds checking, scope fix for BUG-COND-MUL-01 in qint_arithmetic.pxi; no API surface changes
3. **Build system (`setup.py`, `pyproject.toml`)** — Compiler flag changes for binary size; new dependency groups; coverage config
4. **Tests (`tests/python/`)** — One regression test per bug fix; C test subprocess integration; coverage-guided gap filling

### Critical Pitfalls

1. **Arithmetic bug fix introduces regression cascade** — Fixing one shared code path breaks operations that internally call it. Fix one bug per commit; run the full exhaustive suite (test_add, test_sub, test_mul, test_div, test_mod, test_compare, test_bitwise) after each fix. Check all four variants (QQ, CQ, cQQ, cCQ) for every arithmetic change. The project history confirms this: v1.5 fix triggered BUG-CMP-01 in v1.6.

2. **Optimizer loop direction bug must be fixed before binary search** — `smallest_layer_below_comp()` at optimizer.c line 32 has `++i` where `--i` was intended. The function works in the common case only because the last occupied layer is typically less than `compar`. Fix the loop direction in a separate commit before implementing binary search. Do NOT combine these into one commit.

3. **Dead code removal breaking build or silently removing live code** — QPU.h is included by optimizer.c and 4 other files. KS CLA stubs that return NULL are intentionally called by the dispatch layer as the fallback to RCA. Grep for function names across all `.pxd`, `.pyx`, `.c`, `.h`, and `setup.py` before any removal. Rebuild and run full tests after each individual removal.

4. **BUG-MOD-REDUCE is an algorithm redesign, not a patch** — Current `_reduce_mod` hits duplicate-qubit errors at larger moduli because the circuit topology is wrong. Beauregard-style reduction requires ordered additions, comparisons, and conditional re-additions with careful ancilla management. Do NOT attempt an incremental patch. Either redesign from scratch or defer with clear documentation.

5. **False test coverage masking real bugs** — Tests that verify "runs without error" provide no confidence in quantum correctness. Every new test for quantum operations must include Qiskit simulation verification (the `verify_circuit` fixture) or cross-backend differential testing. Do not convert xfail markers to skip — they represent the active bug backlog.

6. **qint_preprocessed.pyx drift during refactoring** — Any edit to a `.pxi` file without regenerating the preprocessed version leaves a stale artifact. Run `python build_preprocessor.py` after every commit touching `.pyx` or `.pxi` files. Add `build_preprocessor.py --check` as a pre-commit hook. Never edit `qint_preprocessed.pyx` directly.

7. **Binary size reduction breaking sequence dispatch** — Dispatch functions use width-indexed function calls into the sequence files. Removing a sequence file without updating dispatch causes linker failure. Start with strip and section GC (safe, no code changes); only then consider structural factoring. Always verify `import quantum_language` succeeds after each change, not just that the build completes.

## Implications for Roadmap

Based on combined research, suggested phase structure (8 phases):

### Phase 1: Infrastructure & Quick Wins
**Rationale:** Add measurement tooling before measuring anything; declare the qiskit-aer dependency before touching user-facing code; add C static analysis tool to catch bugs during subsequent fix work. None of these changes touch quantum logic.
**Delivers:** pytest-cov + coverage config with Cython plugin; vulture installed and added to dev extras; cppcheck Makefile target; qiskit-aer declared in pyproject.toml with friendly ImportError wrappers in grover.py and amplitude_estimation.py.
**Addresses:** qiskit-aer undeclared dependency, test coverage measurement setup, dead code scanner availability.
**Avoids:** Pitfall 6 (false coverage confidence) — establishes measurement infrastructure before writing any tests; avoids discovering tooling gaps mid-milestone.
**Standard patterns:** All items are installation and configuration tasks with official documentation. No phase-specific research needed.

### Phase 2: Tech Debt Cleanup
**Rationale:** Remove dead code and enforce preprocessor automation before bug fixes touch the same files. A simpler codebase is easier to debug and the preprocessor automation prevents drift from the start of the milestone.
**Delivers:** QPU.c/QPU.h removed and replaced with direct `circuit.h` includes in 5 files; `qint_preprocessed.pyx` added to `.gitignore`; `build_preprocessor.py --check` pre-commit hook added; vulture scan results documented (dead code candidates identified for follow-up).
**Addresses:** QPU.c/QPU.h dead stubs, qint_preprocessed.pyx automation, initial dead code inventory.
**Avoids:** Pitfall 2 (dead code removal breaking build) — remove one item at a time, rebuild and run full tests after each. Pitfall 7 (preprocessed drift) — automation removes the manual sync requirement going forward.
**Standard patterns:** Mechanical removal and build system enforcement. The QPU.h dependency chain is fully traced (5 files). No phase-specific research needed.

### Phase 3: Security Hardening
**Rationale:** Add safety nets before making algorithmic changes. Pointer validation and bounds checking convert opaque segfaults into clear Python exceptions during the subsequent bug fix phases. The performance cost is ~3 branch instructions per arithmetic operation — negligible against the 15% regression tolerance established in v2.3.
**Delivers:** `_get_validated_circuit()` validated accessor replacing all ~15-20 raw pointer casts; `qubit_array` slot count validation before C calls; C allocator return-code propagation changed from void to int with error checking in optimizer.c.
**Addresses:** Circuit pointer validation, qubit_array bounds checking, allocator error propagation.
**Avoids:** Pitfall 3 (bounds checking killing hot paths) — validate once at Cython operation entry, never per-gate inside the inner loop. The `@cython.boundscheck(False)` decorators on hot-path functions remain untouched.
**Standard patterns:** Well-understood defensive programming with explicit performance budget analysis. No phase-specific research needed.

### Phase 4: Optimizer Fix & Improvement
**Rationale:** Fix the latent optimizer bug and convert to binary search before the heavy QFT bug fix work. Faster test execution improves iteration speed during Phase 5-6. The optimizer bug fix also removes a correctness hazard that could interfere with circuit layout verification.
**Delivers:** Loop direction bug fixed in optimizer.c (one commit, separate from binary search); binary search replacing the buggy linear scan (second commit); `_optimize_gate_list` max_passes cap removed (unbounded iteration until stable); golden-master circuit snapshots captured before any change and verified identical after.
**Addresses:** Latent optimizer infinite-loop bug, O(log L) gate placement, Python optimizer convergence.
**Avoids:** Pitfall 4 (optimizer refactoring changing circuit semantics) — golden-master snapshots captured before any code change; binary search implemented alongside the linear scan with assertion of identical results before replacing.
**Research flag:** MEDIUM risk. Needs investigation of how often the `++i` bug's common-case bypass fails (does ASan catch it in existing `make asan-test` runs?). Capture golden-master snapshots BEFORE any code change — if snapshots cannot be captured cleanly, escalate to phase-specific research.

### Phase 5: QFT Bug Fixes (Root Causes First)
**Rationale:** Fix the three root-cause bugs in dependency order; BUG-QFT-DIV should resolve as a side effect. Regenerate hardcoded sequences only after the C code is correct. C-level fixes precede the scope fix (Phase 6) because BUG-COND-MUL-01 internally uses controlled QFT addition.
**Delivers:** Correct mixed-width QFT addition (BUG-WIDTH-ADD); correct controlled QFT addition (BUG-CQQ-QFT); correct MSB comparison cleanup in division (BUG-DIV-02); verified BUG-QFT-DIV resolution; regenerated QFT hardcoded sequences for widths 1-16; one regression test per bug fix.
**Addresses:** BUG-WIDTH-ADD in IntegerAddition.c, BUG-CQQ-QFT in IntegerAddition.c, BUG-DIV-02 in IntegerComparison.c, BUG-QFT-DIV verification.
**Avoids:** Pitfall 1 (regression cascade) — one bug per commit; full exhaustive suite after each (test_add, test_sub, test_mul, test_div, test_mod, test_compare, test_bitwise); cross-backend verification after each. Sequence regeneration happens AFTER C bugs are verified correct, never before.
**Research flag:** HIGH risk. BUG-CQQ-QFT requires auditing the Draper QFT adder CCP decomposition against the Ruiz-Perez & Garcia-Escartin paper. BUG-WIDTH-ADD requires careful audit of the qubit offset formula for the mixed-width case. BUG-QFT-DIV may have independent bugs beyond the cascading effects. Phase-specific research is strongly recommended before implementation planning.

### Phase 6: Scope & Segfault Fixes
**Rationale:** Fix remaining bugs after the QFT foundation is stable. BUG-COND-MUL-01 interacts with QFT addition internally — fixing QFT first isolates scope issues. 32-bit segfault and qarray `*=` are independent but complete the "no crashes at valid widths" guarantee.
**Delivers:** Correct controlled multiplication (BUG-COND-MUL-01 — scope lifecycle fix in qint_arithmetic.pxi); no segfault at 32-bit multiplication (MAXLAYERINSEQUENCE fix in types.h); no segfault for qarray `*=` (fix in qarray.pyx); regression tests for all three. Explicit decision documented for BUG-MOD-REDUCE (fix or defer with Beauregard redesign documentation).
**Addresses:** BUG-COND-MUL-01, 32-bit segfault, qarray `*=` segfault. BUG-MOD-REDUCE: fix if Beauregard redesign is feasible, else defer with documentation.
**Avoids:** Pitfall 1 (regression cascade) — BUG-COND-MUL-01 touches `_scope_stack` in `_core.pyx` and `__exit__`/`__del__` in `qint.pyx`; must run all controlled operation tests after the fix.
**Research flag:** MEDIUM risk for BUG-COND-MUL-01 (scope/GC interaction with two fix options — mark result as non-uncomputable vs restructure multiply). HIGH risk for BUG-MOD-REDUCE if attempted (needs Beauregard circuit topology research before any code is written).

### Phase 7: Binary Size Reduction
**Rationale:** Last code-change phase. All bug fixes and sequence regeneration from Phases 5-6 must be complete before applying size optimizations — earlier size work would be invalidated by sequence regeneration. Compiler flag changes should reflect the final code state.
**Delivers:** `.so` files reduced by 30-50% via `-ffunction-sections`, `-fdata-sections`, `-Wl,--gc-sections`, and strip flags in setup.py; Clifford+T sequences factored from ~207K to ~60-80K lines via `emit_clifft_ccx()` shared helper; optional shared library investigation if size target is not met by flags alone.
**Addresses:** Compiler flag changes, Clifford+T sequence source factoring, ThinLTO evaluation.
**Avoids:** Pitfall 5 (dispatch breakage) — verify with `-Wl,--print-gc-sections` to confirm only dead sections are removed; never remove Toffoli CDKM sequences (no runtime fallback); verify `import quantum_language` baseline timing unchanged after each flag addition. ThinLTO must be tested on both macOS and Linux before committing.
**Research flag:** MEDIUM risk for ThinLTO. Full LTO was disabled due to a GCC bug; ThinLTO (Clang-only) may avoid the same issue but needs empirical confirmation. If ThinLTO causes build failures, drop it — the section GC flags alone achieve significant reduction.

### Phase 8: Test Coverage
**Rationale:** Final phase validates all previous work. xfail conversions are only meaningful after bugs are fixed. Coverage measurement will now reveal the remaining gaps after organically adding regression tests in each previous phase.
**Delivers:** pytest-cov HTML report showing current coverage baseline; C allocator tests integrated into pytest via subprocess; regression tests promoted from xfail to passing for all fixed bugs; targeted tests for nested `with`-blocks, circuit reset with live qints, `qiskit-aer` import failure, width-64 boundary conditions.
**Addresses:** C test integration, nested with-block tests, circuit reset tests, qiskit-aer import tests, xfail-to-passing conversions, coverage-guided gap identification.
**Avoids:** Pitfall 6 (false coverage) — every new test for quantum operations must include Qiskit simulation verification (the `verify_circuit` fixture) or cross-backend differential testing; no "runs without error" assertions; do not convert xfail to skip.
**Standard patterns:** Well-understood pytest patterns. The `verify_circuit` fixture and cross-backend differential pattern are established in the existing test suite. No phase-specific research needed.

### Phase Ordering Rationale

- Infrastructure first because measurement tools and dependency fixes enable everything that follows without blocking anything
- Tech debt before bug fixes because removing dead code simplifies the codebase that will be debugged
- Security hardening before algorithmic bug fixes because pointer validation converts opaque segfaults to clear exceptions during Phase 5-6 work
- Optimizer fix before QFT bug fixes because faster tests improve iteration speed during the heavy arithmetic debugging; also eliminates a latent correctness hazard from circuit layout verification
- C-level QFT root causes (Phase 5) before scope/segfault fixes (Phase 6) because BUG-COND-MUL-01 uses controlled QFT addition internally — fixing QFT first isolates what is a scope issue vs a QFT issue
- Binary size after all code changes because sequence regeneration in Phase 5 invalidates earlier size work; compiler flags should reflect the final code state
- Test coverage last because it validates all previous work and xfail conversions are only meaningful once the corresponding bugs are fixed

### Research Flags

Phases requiring deeper research or design review before implementation:
- **Phase 5 (QFT Bug Fixes):** HIGH risk. BUG-CQQ-QFT requires auditing the Draper QFT adder CCP gate decomposition against the Ruiz-Perez & Garcia-Escartin 2017 paper. BUG-WIDTH-ADD requires mapping the qubit offset formula for the mixed-width asymmetric case. BUG-QFT-DIV may have independent bugs beyond cascading effects from its dependencies. Phase-specific research is strongly recommended before implementation planning begins.
- **Phase 6 (BUG-COND-MUL-01):** MEDIUM risk. Two fix options (mark result as non-uncomputable vs restructure multiply circuit) have different trade-offs. The option evaluation should happen before the phase is planned.
- **Phase 6 (BUG-MOD-REDUCE, if attempted):** HIGH risk. Beauregard-style circuit topology is substantially different from the current implementation. Needs circuit design research before any code is written. Deferral is the lower-risk option.
- **Phase 7 (ThinLTO):** MEDIUM risk. Needs empirical testing on both macOS and Linux. Should be last flag tried, not first.

Phases with standard patterns (skip additional research):
- **Phase 1 (Infrastructure):** Tool installation and configuration; all documentation is official and current.
- **Phase 2 (Tech Debt):** Mechanical removal with fully traced dependency chain. No algorithmic decisions.
- **Phase 3 (Security Hardening):** Defensive programming patterns are well-established; specific sites identified; performance cost bounded.
- **Phase 4 (Optimizer Fix):** Binary search algorithm is textbook; primary risk is procedural (golden-master capture before changes), not algorithmic.
- **Phase 8 (Test Coverage):** Standard pytest patterns; the `verify_circuit` fixture and cross-backend differential pattern are established.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack additions | HIGH | All tools verified on PyPI with release history; Cython.Coverage plugin documented in official Cython source; version constraints validated for compatibility |
| Bug root causes | HIGH | All 9 bugs traced to specific files and line ranges via direct codebase inspection; fix pattern classified (A: buffer bounds, B: qubit mapping, C: scope lifecycle, D: algorithm redesign, E: compound bug) |
| Bug fix complexity | MEDIUM | BUG-CQQ-QFT and BUG-MOD-REDUCE involve non-obvious quantum arithmetic circuit design; root causes are confirmed but fix implementation needs phase-specific research |
| Optimizer latent bug | HIGH | The `++i` vs `--i` issue in optimizer.c line 32 confirmed via direct code review; common-case bypass mechanism documented; binary search fix design is complete |
| Binary size reduction | MEDIUM | Compiler flags are well-documented and GCC/Clang standard; ThinLTO needs empirical testing because full LTO was previously disabled for a reason; sequence factoring is mechanically clear but needs generator script changes |
| Security hardening | HIGH | All vulnerable sites identified; validation patterns are well-understood; performance impact bounded at ~3 branches per arithmetic operation, well within v2.3 regression tolerance |
| Test coverage tooling | HIGH | pytest-cov + coverage.py is the standard Python ecosystem approach; Cython plugin support confirmed in official Cython source |
| Phase ordering | HIGH | Each ordering decision has explicit dependency justification backed by project history (v1.5-v3.0 regression patterns) and dependency graph analysis |

**Overall confidence:** HIGH

### Gaps to Address

- **BUG-QFT-DIV independence:** May have bugs beyond the cascading effects of BUG-CQQ-QFT and BUG-WIDTH-ADD. After fixing root causes, if division still fails, the QFT subtraction-in-loop structure has independent bugs. Phase 5 research should investigate this before assuming automatic resolution.
- **BUG-MOD-REDUCE scope decision:** Whether to attempt Beauregard redesign in v4.1 or defer definitively needs a decision at the start of Phase 6 planning. If deferred, document the specific circuit topology required so future work can begin without re-research.
- **optimizer.c `++i` full impact analysis:** Need to determine how often the common-case bypass fails in practice. Does ASan catch it in existing `make asan-test` runs? This determines whether it has been silently corrupting results or is genuinely safe in all current test scenarios.
- **Cython coverage accuracy:** The Cython.Coverage plugin maps `.pyx` lines but cannot measure which C code paths are taken. Coverage numbers will undercount the true uncovered surface. Supplement with ASan in CI and targeted C-level testing for security-critical paths.
- **ThinLTO macOS/Linux compatibility:** Full LTO was disabled due to a GCC-specific bug. ThinLTO is Clang-only and may not have the same issue, but this requires empirical confirmation on both platforms before committing the flag.

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `.planning/codebase/CONCERNS.md` — Security vulnerabilities, performance bottlenecks, tech debt inventory
- `.planning/codebase/ARCHITECTURE.md` — Three-layer architecture, component boundaries
- `.planning/codebase/TESTING.md` — Test coverage gaps, xfail patterns, 8,365+ test inventory
- `.planning/codebase/STACK.md` — Existing tool inventory (profiling, debugging, analysis)
- `.planning/PROJECT.md` — Carry-forward bugs, milestone goals, key decisions
- `c_backend/src/optimizer.c` — Linear scan bug and binary search opportunity (direct code review)
- `c_backend/src/IntegerAddition.c` — QFT rotation mapping, controlled addition code paths
- `c_backend/include/types.h` — `MAXLAYERINSEQUENCE` constant (32-bit segfault root cause)
- `src/quantum_language/_core.pyx` — Circuit pointer casts, qubit_array scratch buffer
- `setup.py` — Static C linking, compiler flags, LTO history

### Secondary (MEDIUM confidence — verified external sources)
- [pytest-cov 7.0.0 on PyPI](https://pypi.org/project/pytest-cov/) — version and compatibility verified
- [coverage.py 7.13.4 documentation](https://coverage.readthedocs.io/) — Cython plugin configuration
- [Cython.Coverage plugin source](https://github.com/cython/cython/blob/master/Cython/Coverage.py) — implementation details and `linetrace=True` requirement
- [vulture 2.14 on PyPI](https://pypi.org/project/vulture/) — feature set and confidence scoring verified
- [cppcheck 2.19.0 releases](https://github.com/danmar/cppcheck/releases) — C23 support confirmed
- [GCC section GC](https://www.vidarholen.net/contents/blog/?p=729) — `-ffunction-sections` + `--gc-sections` effectiveness
- [Link-Time Optimization techniques](https://markaicode.com/link-time-optimization-cpp26/) — ThinLTO vs full LTO comparison
- [Running C unit tests with pytest](https://p403n1x87.github.io/running-c-unit-tests-with-pytest.html) — subprocess integration pattern
- [Draper QFT adder (Ruiz-Perez & Garcia-Escartin 2017)](https://arxiv.org/pdf/1411.5949) — CCP rotation angles for BUG-CQQ-QFT analysis
- [VOQC verified optimizer](https://www.cs.umd.edu/~mwh/papers/voqc.pdf) — commutation-aware optimization and circuit correctness patterns

### Tertiary (MEDIUM confidence — general domain research)
- [D-Linker: Shared library debloating](https://dl.acm.org/doi/10.1109/TCAD.2024.3446712) — binary size reduction techniques
- [Cython memory safety limitations](https://pythonspeed.com/articles/cython-limitations/) — Cython-specific pitfalls and `boundscheck(False)` trade-offs
- [Test coverage false confidence](https://hackernoon.com/misleading-test-coverage-and-how-to-avoid-false-confidence) — general testing practices
- [QuteFuzz: Fuzzing Quantum Compilers](https://popl25.sigplan.org/details/planqc-2025-papers/12/QuteFuzz-Fuzzing-quantum-compilers-using-randomly-generated-circuits-with-control-fl) — quantum testing approaches and differential testing patterns
- [Bounds checking performance overhead](https://chandlerc.blog/posts/2024/11/story-time-bounds-checking/) — 0.3% overhead characterization

---
*Research completed: 2026-02-22*
*Ready for roadmap: yes*
