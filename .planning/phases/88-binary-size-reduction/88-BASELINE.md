# Phase 88: Binary Size Reduction - Baseline

**Date:** 2026-02-24
**Platform:** Linux x86_64, Python 3.13.7
**Build flags:** compiler_args = ["-O3", "-pthread"], linker_args = []

## Current Platform .so Sizes (Linux x86_64, Python 3.13)

| File | Size (bytes) | Size (MB) |
|------|-------------|-----------|
| _core.cpython-313-x86_64-linux-gnu.so | 9,385,944 | 9.0 |
| _gates.cpython-313-x86_64-linux-gnu.so | 8,999,040 | 8.6 |
| openqasm.cpython-313-x86_64-linux-gnu.so | 8,575,936 | 8.2 |
| qarray.cpython-313-x86_64-linux-gnu.so | 10,644,616 | 10.2 |
| qbool.cpython-313-x86_64-linux-gnu.so | 8,815,400 | 8.4 |
| qint.cpython-313-x86_64-linux-gnu.so | 12,083,280 | 11.5 |
| qint_mod.cpython-313-x86_64-linux-gnu.so | 9,051,408 | 8.6 |
| **TOTAL** | **67,555,624** | **64.4** |

## All .so Sizes (All Platforms)

| File | Size (bytes) | Size (MB) |
|------|-------------|-----------|
| _core.cpython-311-darwin.so | 5,060,456 | 4.8 |
| _core.cpython-313-darwin.so | 5,010,816 | 4.8 |
| _core.cpython-313-x86_64-linux-gnu.so | 9,385,944 | 9.0 |
| _gates.cpython-311-darwin.so | 4,907,240 | 4.7 |
| _gates.cpython-313-darwin.so | 4,905,056 | 4.7 |
| _gates.cpython-313-x86_64-linux-gnu.so | 8,999,040 | 8.6 |
| openqasm.cpython-311-darwin.so | 4,878,504 | 4.7 |
| openqasm.cpython-313-darwin.so | 4,874,296 | 4.6 |
| openqasm.cpython-313-x86_64-linux-gnu.so | 8,575,936 | 8.2 |
| qarray.cpython-311-darwin.so | 5,247,096 | 5.0 |
| qarray.cpython-313-darwin.so | 5,201,672 | 5.0 |
| qarray.cpython-313-x86_64-linux-gnu.so | 10,644,616 | 10.2 |
| qbool.cpython-311-darwin.so | 4,912,384 | 4.7 |
| qbool.cpython-313-darwin.so | 4,902,128 | 4.7 |
| qbool.cpython-313-x86_64-linux-gnu.so | 8,815,400 | 8.4 |
| qint.cpython-311-darwin.so | 5,502,144 | 5.2 |
| qint.cpython-313-darwin.so | 5,343,064 | 5.1 |
| qint.cpython-313-x86_64-linux-gnu.so | 12,083,280 | 11.5 |
| qint_mod.cpython-311-darwin.so | 4,950,080 | 4.7 |
| qint_mod.cpython-313-darwin.so | 4,935,368 | 4.7 |
| qint_mod.cpython-313-x86_64-linux-gnu.so | 9,051,408 | 8.6 |
| **TOTAL** | **138,185,928** | **131.8** |
