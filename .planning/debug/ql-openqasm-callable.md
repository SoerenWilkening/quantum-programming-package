---
status: resolved
trigger: "TypeError: 'module' object is not callable when tests call ql.openqasm() in test_branch_superposition.py:62"
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - ql.openqasm is the Cython module, not a callable; tests must use ql.to_openqasm()
test: Static analysis of __init__.py imports and openqasm.pyx exports
expecting: N/A - root cause confirmed
next_action: Apply fix to test file (replace all ql.openqasm() with ql.to_openqasm())

## Symptoms

expected: ql.openqasm() returns an OpenQASM 3.0 string
actual: TypeError: 'module' object is not callable
errors: TypeError at test_branch_superposition.py:62 (and every other call to ql.openqasm())
reproduction: Run any test in test_branch_superposition.py that calls _run_branch_circuit() or ql.openqasm()
started: When test file was written (test references a non-existent API)

## Eliminated

(none needed - root cause found on first hypothesis)

## Evidence

- timestamp: 2026-02-20T00:01:00Z
  checked: src/quantum_language/__init__.py (line 50)
  found: "from .openqasm import to_openqasm" -- imports the function `to_openqasm` from the `openqasm` module. The module itself is also implicitly available as `ql.openqasm` (Python module attribute).
  implication: `ql.openqasm` resolves to the module object; `ql.to_openqasm` resolves to the callable function.

- timestamp: 2026-02-20T00:02:00Z
  checked: src/quantum_language/openqasm.pyx (line 8)
  found: The function is named `to_openqasm()` (not `openqasm()`). It takes no arguments and returns a str. The docstring example shows usage as `ql.to_openqasm()`.
  implication: The public API is `ql.to_openqasm()`, not `ql.openqasm()`.

- timestamp: 2026-02-20T00:03:00Z
  checked: src/quantum_language/__init__.py __all__ list (line 192)
  found: `"to_openqasm"` is in __all__. There is no `openqasm` function exported.
  implication: The intended public API is definitively `ql.to_openqasm()`.

- timestamp: 2026-02-20T00:04:00Z
  checked: tests/python/test_branch_superposition.py (all occurrences)
  found: `ql.openqasm()` appears on lines 62, 131, 153, 179, 207, 243, 315, 339, 362, 406, 447, 469, 491 (13 total occurrences). Every single one is wrong.
  implication: All 13 occurrences need to be changed to `ql.to_openqasm()`.

## Resolution

root_cause: The test file calls `ql.openqasm()` but the quantum_language package does not export a callable named `openqasm`. The module `openqasm` (a Cython .pyx file) is implicitly accessible as `ql.openqasm` because Python makes submodules available as attributes, but it is not callable. The actual exported function is `ql.to_openqasm()`, as defined in `openqasm.pyx` line 8 and exported via `__init__.py` line 50 and `__all__` line 192.

fix: Replace all 13 occurrences of `ql.openqasm()` with `ql.to_openqasm()` in tests/python/test_branch_superposition.py.

verification: Pending (need to run tests in project virtualenv)

files_changed:
- tests/python/test_branch_superposition.py
