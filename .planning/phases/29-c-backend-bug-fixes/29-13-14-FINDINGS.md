# Plan 29-13 & 29-14 Implementation Findings

## Critical Discovery: `.pxi` files are NOT included by `qint.pyx`

The `.pxi` files in `src/quantum_language/` are **reference copies only**. The actual code lives directly in `qint.pyx`. There are NO `include` directives in `qint.pyx`.

**All Python-side changes must be made to `qint.pyx`, NOT the `.pxi` files.**

## Plan 29-13 (BUG-02): Changes Applied

### File: `src/quantum_language/qint.pyx`

1. **`__gt__` int path (~line 1896)**: Changed from `return ~(self <= other)` to:
   ```python
   temp = qint(other, width=self.bits)
   return self > temp
   ```
   This avoids circular dependency with the new `__le__`.

2. **`__le__` (~lines 1901-1996)**: Replaced the entire MSB+zero+OR block with:
   ```python
   return ~(self > other)
   ```
   Keeps self-comparison optimization (`if self is other: return qbool(True)`).

### File: `src/quantum_language/qint_comparison.pxi` (also changed but NOT used)
Same changes applied here for consistency, but these files are not included.

## Plan 29-14 (BUG-03): Changes Applied

### File: `c_backend/src/IntegerMultiplication.c`

1. **`CP_sequence` (line 24)**: `bits - i - 1 - rounds` → `rounds + i`
2. **QQ_mul Block 2 culmination (line 232)**: `bits - i - 1` → `i` (target in `cp()`)
3. **cQQ_mul first block (line 428)**: `bits - bit - 1` → `bit` (target in `cp()`)
4. **cQQ_mul culmination in loop (line 443)**: `bits - bit - 1` → `bit` (target in `cp()`)
5. **cQQ_mul decomposition blocks (lines 452-453, 463-464, 471-474)**: All `bits - i - 1` → `i`

## Build Process Findings

### Cython rebuild requires removing `.c` files
```bash
rm -f src/quantum_language/qint.c
python3 setup.py build_ext --inplace
```
Just touching `.pyx` is NOT enough — Cython's dependency tracker doesn't detect `.pxi` changes, and even with `.pyx` touch, if the `.c` file exists and is newer, Cython may skip regeneration.

### System-installed module shadows local build
```
python3 -c "import quantum_language; print(quantum_language.__file__)"
# Returns: /home/agent/.local/lib/python3.13/site-packages/quantum_language.cpython-313-x86_64-linux-gnu.so
```

The system has a **monolithic** `quantum_language.so` installed at site-packages that shadows the local `src/quantum_language/` package. When running `pytest`, even with `pythonpath = src` in pytest.ini, the site-packages version takes precedence.

### Solution needed
Either:
- **Option A**: Copy the rebuilt `.so` files to replace the site-packages version
- **Option B**: Use `pip install --break-system-packages -e .` (was interrupted)
- **Option C**: Uninstall the old package first, then reinstall
- **Option D**: Use `PYTHONPATH=src` explicitly when running pytest

### Verification that changes work (with PYTHONPATH=src)
```
PYTHONPATH=src python3 -c "..."
# 5 <= 5 returns 1 (CORRECT) with 9 qubits
# 5 > 5 returns 0 (CORRECT)
# x.__le__(y) returns correct qbool
```

## Current State
- **qint.pyx**: Both BUG-02 changes applied and Cython-compiled
- **IntegerMultiplication.c**: All BUG-03 changes applied and compiled
- **Local .so files**: Correctly rebuilt in `src/quantum_language/`
- **Blocking issue**: System site-packages `.so` shadows local build during pytest
- **Next step**: Update the installed package so pytest uses the fixed code

## Test Commands (after fixing install)
```bash
python3 -m pytest tests/bugfix/test_bug02_comparison.py -xvs
python3 -m pytest tests/bugfix/test_bug03_multiplication.py -xvs
python3 -m pytest tests/bugfix/test_bug01_subtraction.py -xvs
python3 -m pytest tests/bugfix/test_bug04_qft_addition.py -xvs
```
