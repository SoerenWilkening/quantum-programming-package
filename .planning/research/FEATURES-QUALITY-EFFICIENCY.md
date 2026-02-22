# Feature Landscape: v4.1 Quality & Efficiency

**Domain:** Bug fixes, tech debt, security hardening, binary size, performance, test coverage
**Researched:** 2026-02-22

## Table Stakes

Features that MUST be completed for this milestone to be meaningful. Missing any of these means the milestone is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fix BUG-MOD-REDUCE (_reduce_mod corruption) | Carry-forward bug since v1.5; modular arithmetic is broken for larger moduli | High | Needs fundamentally different circuit structure; may require Beauregard-style modular reduction |
| Fix BUG-COND-MUL-01 (controlled multiplication scope) | Controlled multiplication corrupts result register; workaround active | High | Root-caused in Phase 69-02; uncomputation ordering issue in scope exit |
| Fix BUG-DIV-02 (MSB comparison leak in division) | 9 failures per div/mod test file; division results unreliable at boundary | Medium | MSB handling in comparison circuit leaks state |
| Fix BUG-WIDTH-ADD (mixed-width QFT addition) | Off-by-one in width handling; affects any mixed-width arithmetic | Medium | Discovered in v1.8; likely qubit offset calculation error |
| Fix 32-bit multiplication segfault | Buffer overflow in C backend; crashes the process | High | Discovered in v2.2; needs C-level bounds analysis with ASan |
| Fix BUG-CQQ-QFT (controlled QQ addition rotations) | CCP rotation errors at width 2+; QFT controlled operations broken | Medium | Discovered in v3.0; rotation angle or qubit index error |
| Fix BUG-QFT-DIV (QFT division/modulo failures) | QFT division pervasively broken at all widths; entire QFT division path unusable | High | Discovered in v3.0; likely cascading from QFT addition bugs |
| Fix qarray `*=` segfault | In-place multiplication on array elements crashes | Medium | C backend segfault; currently pytest.skip'd |
| Fix qiskit_aer undeclared dependency | Users get bare ModuleNotFoundError with no guidance | Low | Add to pyproject.toml verification group; add friendly ImportError |
| Test coverage measurement setup | Cannot improve coverage without measuring it first | Low | Add pytest-cov + coverage config |

## Differentiators

Features that go beyond bug fixing and make the project significantly better.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Optimizer binary search | O(log L) instead of O(L) per gate placement; accelerates deep circuit building | Low | The `occupied_layers_of_qubit` array is already sorted; replace linear scan with bsearch() |
| Binary size reduction (compiler flags) | Reduce 75MB of .so files by 30-50%; faster pip install, less disk usage | Low | Compiler flag changes in setup.py; no code changes |
| C static analysis integration | Catch memory safety bugs proactively; prevent future segfaults | Medium | Add cppcheck to pre-commit or Makefile target |
| Automated qint_preprocessed.pyx generation | Eliminate dual-maintenance burden; prevent drift between source and preprocessed | Low | build_preprocessor.py already exists; add CI check |
| Remove dead QPU.c/QPU.h stubs | Reduce confusion for contributors; simplify build | Low | Empty files with no active code |
| Dead code detection (vulture) | Identify and remove unused functions/variables across 395K Python lines | Low | One-time scan + periodic re-runs |
| C test integration into pytest | C allocator regressions visible in standard test run | Low | subprocess wrapper around existing C Makefile targets |
| Circuit pointer validation | Prevent exploitable unsafe casts in _core.pyx | Medium | Audit all circuit pointer dereference sites |
| qubit_array bounds checking | Prevent silent buffer overrun in scratch buffer | Low | Add size validation before writing to qubit_array |

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Parallel test execution (pytest-xdist) | Global circuit state makes parallel tests produce corrupt circuits | Keep sequential execution; parallelize only at CI matrix level |
| Full type checking (mypy) | 60K lines of Cython are unsupported by mypy; massive stub effort | Keep using ruff's type-related rules (UP, B) |
| Fuzz testing harness | Valuable but separate project; needs dedicated harness design | Focus on deterministic bug reproduction |
| Refactoring global circuit state | Foundational architecture change that would touch every file | Address in a dedicated milestone; hardening existing globals is sufficient |
| Kogge-Stone CLA implementation | Stubs exist but returning NULL; full implementation is a feature milestone | Keep BK CLA; document KS as future work |
| Controlled bitwise operations | NotImplementedError gaps exist but are feature additions, not quality fixes | Defer to feature milestone |
| Multi-circuit / reentrant support | Fundamental architecture redesign | Document as limitation; add tests for the "circuit reset with live qints" failure case |

## Feature Dependencies

```
Test coverage measurement -> Coverage gap identification -> Targeted test writing
C static analysis (cppcheck) -> Security findings -> Circuit pointer validation
C static analysis (cppcheck) -> Security findings -> qubit_array bounds checking
ASan (already exists) -> 32-bit multiplication segfault diagnosis -> Fix
ASan (already exists) -> qarray *= segfault diagnosis -> Fix
BUG-WIDTH-ADD fix -> BUG-QFT-DIV investigation (may share root cause)
BUG-CQQ-QFT fix -> BUG-QFT-DIV investigation (controlled addition is used by division)
Binary size flags (-Os, gc-sections) -> Benchmark verification (no perf regression) -> Commit
vulture scan -> Dead code identification -> Removal PRs
build_preprocessor.py CI check -> qint_preprocessed.pyx automation -> Remove manual copy
```

## MVP Recommendation

Prioritize (highest impact, addressing the most severe concerns):

1. **Fix all 7 carry-forward bugs** -- these are the core reason for this milestone; each represents a broken user-facing feature
2. **Fix qiskit_aer undeclared dependency** -- trivial fix, removes a paper-cut for every user
3. **Test coverage measurement** -- enables all subsequent coverage improvement work
4. **Binary size reduction** -- compiler flag changes only, no code changes, big user-visible improvement
5. **Optimizer binary search** -- small code change, measurable performance improvement for deep circuits

Defer:
- Dead code detection: valuable but not urgent; can run vulture at any time
- C static analysis: important for long-term health but does not fix current bugs
- Circuit pointer validation: important but requires careful audit; lower probability of user-facing failure than the known bugs

## Sources

- `.planning/PROJECT.md` -- carry-forward bug list and milestone goals
- `.planning/codebase/CONCERNS.md` -- tech debt, security, fragility inventory
- `.planning/codebase/TESTING.md` -- test coverage gaps
- `.planning/codebase/STACK.md` -- existing tool inventory

---
*Feature landscape for: v4.1 Quality & Efficiency*
*Researched: 2026-02-22*
