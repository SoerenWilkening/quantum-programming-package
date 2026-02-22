# Research Summary: v4.1 Quality & Efficiency

**Domain:** Bug fixes, tech debt cleanup, security hardening, performance optimization, binary size reduction, and test coverage for a quantum programming framework
**Researched:** 2026-02-22
**Overall confidence:** HIGH

## Executive Summary

The v4.1 milestone is a consolidation milestone focused on fixing 9 known bugs, reducing tech debt, hardening security, optimizing performance, reducing binary size, and improving test coverage. Research confirms that the existing tool stack (Python 3.11+, Cython 3.x, C23 backend, pytest, cProfile, memray, py-spy, ASan, Valgrind) covers most needs. Only 3 pip packages (pytest-cov, coverage, vulture) and 1 system tool (cppcheck) need to be added.

The critical finding is that this milestone's biggest risk is not missing tools -- it is regression cascades from bug fixes. The 7 carry-forward bugs all touch shared C backend code paths (IntegerAddition.c, IntegerComparison.c, ToffoliAddition*.c). Fixing one operation (e.g., mixed-width addition) can break another operation (e.g., comparison) that depends on it. The exhaustive test suite (8,365+ tests) provides protection, but only if run completely after each fix. The recommended phase structure below reflects this: fix one bug at a time, verify exhaustively, then move to the next.

The binary size opportunity is significant. The 7 compiled `.so` extension modules total ~75MB (Linux x86_64) because every module links ALL 107 hardcoded sequence C files (~344K lines, 22MB source) even when most sequences are unused by that module. Compiler flags (`-ffunction-sections`, `-fdata-sections`, `-Wl,--gc-sections`, `-s` strip) can reduce this by 30-50% with zero code changes. ThinLTO could provide additional savings but requires testing since full LTO was previously disabled due to a GCC bug.

The test coverage gap is real but the existing test count (8,365+) means most code paths are likely exercised -- what is missing is measurement. Adding pytest-cov will reveal which areas are actually uncovered, enabling data-driven test writing rather than guesswork.

## Key Findings

**Stack:** Add pytest-cov + coverage (test coverage), vulture (dead code), cppcheck (C static analysis). Fix qiskit-aer undeclared dependency. Apply binary size compiler flags. Everything else already exists.

**Architecture:** No changes. Patterns for safe modification within existing 3-layer architecture (defensive C entry, bounds-checked scratch buffer, binary search for sorted arrays, coverage-guided test writing, bug-fix-with-regression-test).

**Critical pitfall:** Regression cascades from arithmetic bug fixes. The C backend's sequence cache and qubit offset mapping create non-obvious couplings. Fixing CQ_add affects every operation that internally calls CQ_add (multiplication, division, comparisons). Fix one bug per commit, run full exhaustive suite after each.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Infrastructure Setup** - Add tooling first
   - Addresses: pytest-cov, coverage config, vulture, cppcheck Makefile target, qiskit-aer dependency declaration
   - Avoids: Pitfall 6 (false coverage confidence) by establishing measurement before writing tests

2. **Tech Debt Cleanup** - Remove dead code, automate preprocessor
   - Addresses: QPU.c/QPU.h removal, qint_preprocessed.pyx automation, dead code scan
   - Avoids: Pitfall 2 (dead code removal breaking build) and Pitfall 7 (preprocessed file drift)

3. **Bug Fixes (Low-Level C)** - Fix C backend bugs first
   - Addresses: 32-bit segfault, qarray `*=` segfault, BUG-WIDTH-ADD, BUG-CQQ-QFT
   - Avoids: Pitfall 1 (regression cascade) by fixing lowest level first and running full suite after each

4. **Bug Fixes (High-Level)** - Fix Python/Cython-level bugs
   - Addresses: BUG-MOD-REDUCE, BUG-COND-MUL-01, BUG-DIV-02, BUG-QFT-DIV
   - Avoids: Pitfall 5 (fixing one bug introduces another) by fixing after C-level bugs are stable

5. **Security Hardening** - Add bounds checks and pointer validation
   - Addresses: Circuit pointer validation, qubit_array bounds checking
   - Avoids: Pitfall 3 (bounds checking kills hot paths) by using assert() for hot paths and runtime checks for entry points

6. **Performance Optimization** - Optimizer binary search, compile replay
   - Addresses: O(log L) layer search, compile replay overhead
   - Avoids: Pitfall 4 (optimizer refactoring changing semantics) by capturing golden-master snapshots first

7. **Binary Size Reduction** - Compiler flag changes
   - Addresses: Section GC, strip, -Os evaluation
   - Avoids: Pitfall 5 (dispatch breakage) by verifying with `--print-gc-sections` before committing

8. **Test Coverage** - Data-driven gap filling
   - Addresses: Coverage measurement, targeted test writing, C test integration into pytest
   - Avoids: Pitfall 6 (false coverage) by requiring Qiskit verification in every new test

**Phase ordering rationale:**
- Infrastructure first because tools enable everything else
- Tech debt before bug fixes because dead code removal simplifies the codebase being debugged
- C-level bug fixes before Python-level because Python operations compose on top of C operations
- Security hardening after bug fixes because bounds checks should protect the fixed code paths
- Performance after correctness because premature optimization is the root of all evil
- Binary size after everything else because compiler flag changes should not mask bugs
- Test coverage last because it validates all the other work and xfail conversions only make sense after bugs are fixed

**Research flags for phases:**
- Phase 3-4 (Bug Fixes): HIGH risk -- needs exhaustive verification after each fix; BUG-QFT-DIV may be unfixable without a rewrite
- Phase 7 (Binary Size): MEDIUM risk -- ThinLTO needs careful testing; section GC may remove function-pointer targets
- All other phases: LOW risk -- well-understood tools and patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack additions | HIGH | All recommended tools are well-established, actively maintained, version-verified on PyPI |
| Bug fix approach | HIGH | ASan + exhaustive test suite + one-at-a-time methodology is proven in project history |
| Binary size reduction | MEDIUM | Compiler flags are well-documented but LTO was previously disabled for a reason; needs testing |
| Test coverage tooling | HIGH | pytest-cov + coverage.py is the standard Python ecosystem approach |
| C static analysis | HIGH | cppcheck is the standard open-source C analysis tool |
| Performance optimization | MEDIUM | Binary search is theoretically sound but the optimizer loop may have a latent direction bug |
| Security hardening | HIGH | Defensive patterns are well-understood; the concerns were clearly identified in codebase audit |

## Gaps to Address

- **BUG-QFT-DIV root cause**: Marked as "pervasively broken at all tested widths." May be a fundamental QFT rotation formula issue rather than an isolated bug. Phase-specific research needed before attempting a fix. Consider whether "won't fix" (QFT division unsupported, Toffoli division recommended) is the pragmatic answer.
- **BUG-MOD-REDUCE circuit structure**: Needs a fundamentally different approach (Beauregard-style modular reduction). Phase-specific research needed on the circuit design before implementation.
- **Cython coverage accuracy**: The Cython.Coverage plugin maps `.pyx` lines but cannot measure which C code paths are taken. Coverage numbers will undercount the true uncovered surface. Need to supplement with ASan and C-level testing.
- **ThinLTO compatibility**: Full LTO was disabled due to a GCC bug. ThinLTO (Clang-only) may not have the same issue, but this needs empirical testing on both macOS and Linux.
- **optimizer.c loop direction**: Line 32 has `++i` where `--i` appears intended. This needs investigation before the binary search optimization can proceed.

## Files Created

| File | Purpose |
|------|---------|
| `.planning/research/SUMMARY-QUALITY-EFFICIENCY.md` | This file -- executive summary with roadmap implications |
| `.planning/research/STACK-QUALITY-EFFICIENCY.md` | Technology recommendations: pytest-cov, vulture, cppcheck, compiler flags |
| `.planning/research/FEATURES-QUALITY-EFFICIENCY.md` | Feature landscape: 10 table stakes, 9 differentiators, 7 anti-features |
| `.planning/research/ARCHITECTURE-QUALITY-EFFICIENCY.md` | Architecture patterns for safe modification within existing layers |
| `.planning/research/PITFALLS-QUALITY-EFFICIENCY.md` | 7 critical + 4 moderate + 3 minor pitfalls with phase-specific warnings |

## Sources

- Project codebase analysis: `.planning/codebase/CONCERNS.md`, `STACK.md`, `ARCHITECTURE.md`, `TESTING.md`, `STRUCTURE.md`
- Project history: `.planning/PROJECT.md` (requirements, decisions, known bugs)
- [pytest-cov on PyPI](https://pypi.org/project/pytest-cov/) -- v7.0.0 verified
- [coverage.py docs](https://coverage.readthedocs.io/) -- v7.13.4, Cython plugin
- [vulture on PyPI](https://pypi.org/project/vulture/) -- v2.14 verified
- [cppcheck releases](https://github.com/danmar/cppcheck/releases) -- v2.19.0 verified
- [GCC section GC](https://www.vidarholen.net/contents/blog/?p=729) -- `-ffunction-sections` + `--gc-sections`
- [LTO techniques](https://markaicode.com/link-time-optimization-cpp26/) -- ThinLTO comparison
- [C unit tests with pytest](https://p403n1x87.github.io/running-c-unit-tests-with-pytest.html) -- subprocess pattern
- [Cython coverage plugin](https://github.com/cython/cython/blob/master/Cython/Coverage.py) -- implementation details
- [Cython coverage issues](https://github.com/cython/cython/issues/6186) -- known limitations

---
*Research summary for: Quantum Assembly v4.1 Quality & Efficiency*
*Researched: 2026-02-22*
