---
status: diagnosed
trigger: "ModuleNotFoundError: No module named 'quantum_language._core' - direct import works but pytest fails"
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:01Z
---

## Current Focus

hypothesis: The error is environment-specific - likely user's local macOS Python 3.11 environment
test: reproduced on Linux Python 3.13 - works with pythonpath=src
expecting: different behavior on user's actual machine
next_action: report findings - cannot reproduce in current environment

## Symptoms

expected: pytest should import quantum_language successfully like direct python does
actual: pytest fails with ModuleNotFoundError for quantum_language._core
errors: ModuleNotFoundError: No module named 'quantum_language._core' at conftest.py:17
reproduction: pip install -e . && pytest tests/python/test_branch_superposition.py
started: comparison between direct import (works) and pytest (fails)

## Eliminated

- hypothesis: _core.so file is missing
  evidence: _core.cpython-313-x86_64-linux-gnu.so exists in src/quantum_language/
  timestamp: 2026-02-20

- hypothesis: pythonpath not set correctly in pytest
  evidence: pytest.ini has pythonpath=src, tests run and find _core successfully
  timestamp: 2026-02-20

## Evidence

- timestamp: 2026-02-20
  checked: Package installation status
  found: quantum-assembly is NOT installed via pip, pip show fails
  implication: User's "Test 1 passed" installed it, but something reset the state

- timestamp: 2026-02-20
  checked: pytest.ini configuration
  found: pythonpath=src is set, testpaths=tests/python
  implication: pytest should add src/ to path automatically

- timestamp: 2026-02-20
  checked: _core.so files in src/quantum_language/
  found: _core.cpython-313-x86_64-linux-gnu.so (Linux 3.13) and _core.cpython-311-darwin.so (macOS 3.11) both exist
  implication: Compiled extensions exist for both environments

- timestamp: 2026-02-20
  checked: Direct import with src in path
  found: python -c "sys.path.insert(0,'src'); import quantum_language._core" works
  implication: Module imports correctly when path is set

- timestamp: 2026-02-20
  checked: pytest tests/python/test_branch_superposition.py
  found: Tests RUN (no _core import error), fail with different error (missing branch method)
  implication: Cannot reproduce the reported _core import error in current environment

- timestamp: 2026-02-20
  checked: pytest tests/test_add.py (root tests/ directory)
  found: Tests RUN (no _core import error), fail with qiskit_qasm3_import missing
  implication: Both conftest.py files import quantum_language successfully

- timestamp: 2026-02-20
  checked: Compiled .so files for _gates module
  found: _gates.cpython-311-darwin.so exists but _gates.cpython-313-x86_64-linux-gnu.so does NOT exist
  implication: _gates module was recently added and not compiled for Linux 3.13

## Resolution

root_cause: Cannot reproduce in current environment. The reported error likely occurs on the user's local macOS Python 3.11 environment where there may be a path conflict or stale installation. The most likely causes are:

1. **Stale editable install**: If `pip install -e .` was done previously, and then the user's working directory changed, the editable install link (in site-packages) may point to a stale location or conflict with the pythonpath=src setting.

2. **Python version mismatch**: If the user is running Python 3.11 on macOS but there's a version conflict in how the package is discovered.

3. **Build artifacts interference**: Old build artifacts in build/ directory may interfere with imports.

fix: Recommended steps to resolve:
1. Clean all build artifacts: `rm -rf build/ *.egg-info src/*.egg-info`
2. Uninstall any existing package: `pip uninstall quantum-assembly -y`
3. Fresh install: `pip install -e .`
4. Verify: `python -c "from quantum_language import qint; print('OK')"`
5. Run tests: `pytest tests/python/test_branch_superposition.py`

verification: N/A - cannot reproduce
files_changed: []
