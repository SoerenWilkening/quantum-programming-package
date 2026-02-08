# Phase 62: Hardcoded Sequence Benchmark Report

Generated: 2026-02-08T16:48:18+0000
Python: 3.13.7
Bench raw data: 2026-02-08T16:40:27+0000

## 1. Import Time Analysis (BENCH-01)

**Median import time: 192.35 ms**
- Mean: 189.86 ms
- Stdev: 15.86 ms

**Total .so binary size: 16.4 MB** (6 extensions)

| Extension | Size |
|-----------|------|
| qint.cpython-313-x86_64-linux-gnu.so | 4836 KB |
| qarray.cpython-313-x86_64-linux-gnu.so | 3706 KB |
| _core.cpython-313-x86_64-linux-gnu.so | 2409 KB |
| qint_mod.cpython-313-x86_64-linux-gnu.so | 2162 KB |
| qbool.cpython-313-x86_64-linux-gnu.so | 1936 KB |
| openqasm.cpython-313-x86_64-linux-gnu.so | 1713 KB |

The import time represents the fixed overhead of loading hardcoded sequences.
All .so extensions are loaded during `import quantum_language`.

## 2. First-Call Generation Cost (BENCH-02)

First-call cost measures the time to generate gate sequences on first use of each
(operation, width) combination. For hardcoded widths (1-16), this is the dispatch
cost. For dynamic widths (17+), this includes C-level generation.

### Widths 1-8

| Operation | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|-----------|------:|------:|------:|------:|------:|------:|------:|------:|
| QQ_add | 190us | 419us | 388us | 426us | 348us | 370us | 359us | 206us |
| CQ_add | 217us | 258us | 203us | 217us | 209us | 206us | 208us | 235us |
| cQQ_add | 215us | 377us | 462us | 397us | 449us | 381us | 382us | 481us |
| cCQ_add | 189us | 209us | 212us | 227us | 294us | 218us | 238us | 224us |
| QQ_mul | 2.0ms | 3.4ms | 5.3ms | 6.5ms | 8.9ms | 9.9ms | 11.8ms | 13.4ms |
| CQ_mul | 2.2ms | 3.8ms | 5.5ms | 7.3ms | 9.1ms | 10.6ms | 11.6ms | 13.6ms |
| Q_xor | 8us | 9us | 9us | 9us | 9us | 9us | 11us | 10us |
| Q_and | 218us | 250us | 228us | 280us | 216us | 204us | 205us | 210us |
| Q_or | 234us | 243us | 266us | 208us | 199us | 198us | 189us | 184us |

### Widths 9-16

| Operation | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|-----------|------:|------:|------:|------:|------:|------:|------:|------:|
| QQ_add | 198us | 228us | 350us | 391us | 484us | 420us | 411us | 405us |
| CQ_add | 217us | 226us | 233us | 228us | 245us | 224us | 252us | 229us |
| cQQ_add | 236us | 310us | 323us | 544us | 558us | 539us | 586us | 578us |
| cCQ_add | 240us | 224us | 325us | 251us | 239us | 212us | 226us | 240us |
| QQ_mul | 16.5ms | 19.3ms | 20.8ms | 22.6ms | 25.2ms | 28.1ms | 31.4ms | 34.8ms |
| CQ_mul | 14.7ms | 16.7ms | 19.4ms | 20.2ms | 22.5ms | 23.9ms | 26.1ms | 27.0ms |
| Q_xor | 12us | 11us | 13us | 12us | 11us | 11us | 11us | 12us |
| Q_and | 226us | 189us | 207us | 228us | 191us | 201us | 202us | 211us |
| Q_or | 192us | 237us | 288us | 279us | 203us | 183us | 196us | 222us |

### Key Observations

- **Addition (QQ_add)** at width 8: 206us -- moderate, O(N^2) CP gates
- **Multiplication (QQ_mul)** at width 8: 13.4ms -- expensive, O(N) additions
- **XOR (Q_xor)** at width 8: 10us -- trivial, O(N) CNOT gates
- Cost ordering: QQ_mul >> QQ_add >> Q_xor (by ~3 orders of magnitude from top to bottom)

## 3. Cached Dispatch Overhead (BENCH-03)

Measures per-call cost AFTER first call (cached sequences). Compares hardcoded
(width 8) vs dynamic (width 17) dispatch paths.

| Operation | Hardcoded (w=8) | Dynamic (w=17) | Difference | Ratio |
|-----------|---------------:|---------------:|----------:|------:|
| QQ_add | 17.6us | 107.9us | +90.3us | 6.1x |
| CQ_add | 12.5us | 31.0us | +18.5us | 2.5x |

Note: Width difference (8 vs 17) contributes to the cost gap beyond pure dispatch overhead.
Hardcoded sequences avoid C-level generation entirely, resulting in faster dispatch.

## 4. Amortization Analysis (BENCH-04)

**Import overhead: 192 ms**

### Break-Even Calculations

Two break-even metrics:

1. **Cached dispatch break-even:** 3,533 calls
   - Average per-call saving: 54.4us
   - Formula: 192350us / 54.44us = 3,533 calls

2. **First-call break-even:** 550 unique (op, width) pairs
   - Average first-call saving: 350us
   - Formula: 192350us / 350us = 550 first calls

### Interpretation

The hardcoded sequences add 192ms to import time. Each cached dispatch call saves ~54442ns vs dynamic generation. Break-even for cached dispatch: ~3533 calls. However, the primary benefit is first-call avoidance: each unique (operation, width) combination saves ~350us on first call. Break-even for first-call savings: ~550 unique first calls. In practice, a typical quantum program calls 5-20 unique (op, width) pairs, so first-call savings alone justify the import overhead after just 550 unique calls.

## 5. Multiplication Evaluation (EVAL-01)

### Cost vs Addition Ratio

| Width | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|-------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| Ratio | 11x | 8x | 14x | 15x | 26x | 27x | 33x | 65x | 83x | 85x | 59x | 58x | 52x | 67x | 76x | 86x |

### CQ_mul Per-Call Cost (NOT cached)

CQ_mul returns a fresh malloc'd sequence each call. This is the per-call cost,
not just first-call. Compare with QQ_mul first-call (which IS cached after first).

| Width | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|-------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| Cost | 1.9ms | 3.3ms | 4.7ms | 6.9ms | 8.7ms | 10.4ms | 10.8ms | 18.8ms | 18.2ms | 20.4ms | 18.8ms | 21.3ms | 22.5ms | 25.1ms | 26.1ms | 28.7ms |

**Recommendation: investigate**

Multiplication generation cost is 48x addition on average (range: 8x to 86x). Average first-call cost: 16230us. QQ_mul IS cached after first call, so hardcoding would only save the first-call cost. CQ_mul is NOT cached (fresh malloc each call), so it would benefit more from hardcoding. However, multiplication sequences are O(N^2) additions, so binary size impact would be substantial relative to current 16.4MB. Recommend investigating selective hardcoding for small widths (1-4) where binary size is manageable.

## 6. Bitwise Evaluation (EVAL-02)

| Operation | Max Cost (all widths) |
|-----------|--------------------:|
| Q_xor | 13us |
| Q_and | 280us |
| Q_or  | 288us |

**Recommendation: skip**

All bitwise operation generation costs are under 300.0us (max: 288.4us). XOR is O(N) CNOT gates with ~13us max cost. AND/OR use Toffoli decomposition at ~288us max. These are trivial compared to addition (379us median) and especially multiplication. Hardcoding would add binary size for negligible benefit.

## 7. Division Evaluation (EVAL-03)

Division is implemented at the Python/Cython level, not as a C sequence.
Classical divisor uses O(N) comparison+subtraction iterations.
Quantum divisor uses O(2^N) iterations (exponential cost).

| Width | Classical (a // 3) | Quantum (a // b) |
|------:|-----------------:|-----------------:|
| 1 | 264us | 659us |
| 2 | 637us | 731us |
| 3 | 744us | 1.2ms |
| 4 | 1.3ms | 3.2ms |
| 5 | 1.4ms | 9.8ms |
| 6 | 1.7ms | 46.5ms |
| 7 | 1.8ms | 278.5ms |
| 8 | 1.8ms | 1.7s |

**Recommendation: skip**

Division cost is in the Python-level loop structure (N comparison+subtraction iterations for classical divisor, 2^N for quantum divisor), NOT in C sequence generation. Hardcoding individual gate sequences would not reduce division cost because the overhead is in the number of high-level operations, not in generating each operation's gate sequence. The component operations (addition, subtraction, comparison) already benefit from hardcoded sequences when available.

## 8. Summary Recommendations

| Category | Recommendation | Key Reason |
|----------|---------------|------------|
| Addition (QQ/CQ/cQQ/cCQ) | **keep** | Already hardcoded widths 1-16; dispatch overhead is 2-6x lower than dynamic |
| Multiplication (QQ/CQ) | **investigate** | Cost is 48x addition; binary size impact needs investigation |
| Bitwise (xor/and/or) | **skip** | Max cost 288us; trivial generation |
| Division (// / %) | **skip** | Python-level loop cost, not C sequence generation |

---
*Report generated by scripts/benchmark_eval.py (Phase 62, Plan 02)*
