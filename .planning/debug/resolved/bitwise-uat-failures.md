---
status: resolved
trigger: "Investigate why Phase 32 bitwise tests are failing despite fixes being committed"
created: 2026-02-01T13:30:00Z
updated: 2026-02-01T13:45:00Z
---

## Current Focus

hypothesis: CONFIRMED -- Stale .so in site-packages shadowed the rebuilt extensions in src/
test: Removed stale .so, rebuilt with setup.py build_ext --inplace, ran full test suites
expecting: All tests pass
next_action: Done -- archive session

## Symptoms

expected: Bitwise operations produce correct results (e.g., qint(5,w=3) & 3 = 1)
actual: qint(5,w=3) & 3 returns 4 (bits reversed); 754/1176 CQ tests fail, 585/630 QQ tests fail
errors: Wrong bitwise results (bit reversal pattern)
reproduction: Run tests/test_bitwise.py and tests/test_bitwise_mixed.py
started: After Phase 32-03 fixes were committed but .so was not rebuilt

## Eliminated

(none needed -- root cause confirmed on first hypothesis)

## Evidence

- timestamp: 2026-02-01T13:30:00Z
  checked: Site-packages quantum_language .so timestamp
  found: /home/agent/.local/lib/python3.13/site-packages/quantum_language.cpython-313-x86_64-linux-gnu.so dated Jan 26 22:11
  implication: This .so predates ALL Phase 32 fixes (committed Feb 1)

- timestamp: 2026-02-01T13:30:00Z
  checked: Local src/ .so timestamps
  found: src/quantum_language/qint.cpython-313-x86_64-linux-gnu.so dated Feb 1 12:32
  implication: Local build ran but Python doesn't use these files -- imports monolithic .so from site-packages

- timestamp: 2026-02-01T13:30:00Z
  checked: Python import resolution
  found: `import quantum_language` resolves to /home/agent/.local/lib/python3.13/site-packages/quantum_language.cpython-313-x86_64-linux-gnu.so (monolithic, stale)
  implication: The editable install is broken -- pip install -e . did not update the compiled extension in site-packages

- timestamp: 2026-02-01T13:30:00Z
  checked: LogicOperations.c source code
  found: bin[bits - 1 - i] fix IS present in source at lines 1134 and 1298 (CQ_and and CQ_or)
  implication: Source fix is correct but was never compiled into the running .so

- timestamp: 2026-02-01T13:35:00Z
  checked: pip install -e . attempt
  found: Fails with "setup script specifies an absolute path" error in setup.py (package_dir uses absolute SRC_DIR)
  implication: Editable install is broken -- explains why previous executor's build didn't actually update site-packages

- timestamp: 2026-02-01T13:36:00Z
  checked: .pth file in site-packages
  found: __editable__.quantum_assembly-0.1.0.pth exists, pointing to src/ directory
  implication: Once stale monolithic .so removed, Python falls through to .pth -> src/ -> correct per-module .so files

- timestamp: 2026-02-01T13:38:00Z
  checked: Removed stale .so, rebuilt with setup.py build_ext --inplace, ran tests
  found: test_bitwise.py: 2418/2418 passed. test_bitwise_mixed.py: 1266 passed, 292 xfailed, 50 xpassed
  implication: All fixes are correct. The ONLY problem was the stale binary.

## Resolution

root_cause: A stale monolithic .so file (`quantum_language.cpython-313-x86_64-linux-gnu.so`, dated Jan 26) in site-packages was shadowing the freshly-compiled per-module .so files in `src/quantum_language/`. Python's import resolution found the monolithic .so first (in site-packages) before consulting the `.pth` file that points to `src/`. This old binary predated all Phase 32 bitwise fixes. The `pip install -e .` command fails due to a `setup.py` bug (absolute path in `package_dir`), which is why the previous executor's build succeeded locally but never updated the site-packages binary.

fix: Removed stale `/home/agent/.local/lib/python3.13/site-packages/quantum_language.cpython-313-x86_64-linux-gnu.so`, then rebuilt with `python3 setup.py build_ext --inplace` which places correct .so files in `src/quantum_language/`. The existing `.pth` file now correctly resolves imports to `src/`.

verification: Full test suites pass:
- test_bitwise.py: 2418/2418 passed (was 754 failing)
- test_bitwise_mixed.py: 1266 passed, 292 xfailed, 50 xpassed (was 585 failing)
- No PYTHONPATH override needed -- works via .pth file

files_changed:
- DELETED: /home/agent/.local/lib/python3.13/site-packages/quantum_language.cpython-313-x86_64-linux-gnu.so (stale binary)
- REBUILT: src/quantum_language/*.cpython-313-x86_64-linux-gnu.so (6 extension modules)

secondary_issue: setup.py uses absolute path for package_dir (SRC_DIR = os.path.join(PROJECT_ROOT, "src")), causing pip install -e . to fail. This should be fixed to use a relative path ("src") to prevent this class of staleness bugs in the future.
