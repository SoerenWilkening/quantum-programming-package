# Phase 92: Modular Toffoli Arithmetic - Research

**Researched:** 2026-02-25
**Domain:** Quantum modular arithmetic circuits (Toffoli-based, fault-tolerant)
**Confidence:** HIGH

## Summary

Phase 92 implements fault-tolerant modular arithmetic (`qint_mod` add, sub, multiply mod N) using Toffoli gates. The existing `qint_mod` class (from Phase 91) already has a skeleton implementation with `__add__`, `__sub__`, `__mul__` operators, but has a critical bug: the C-level `toffoli_mod_reduce` in `ToffoliModReduce.c` leaks 1 persistent comparison ancilla per modular reduction call, causing incorrect results whenever the reduction actually modifies the value (raw result >= N). Phase 91's test suite (`tests/test_modular.py`) marks these as `xfail` with known failure predicates.

The core technical challenge is implementing a **clean ancilla uncomputation** in `toffoli_mod_reduce`. The standard approach from quantum computing literature (Beauregard 2003, Haner-Roetteler-Svore 2017) is to use a specific 7-step sequence for modular addition that avoids the persistent ancilla by leveraging properties specific to **modular addition** (not general reduction). The key insight is: when computing `(a + b) mod N` where both operands are known to be in `[0, N-1]`, the comparison ancilla can be uncomputed by subtracting `a` from the result (which reveals whether reduction occurred) and then adding `a` back. This is only possible when one operand (`a` or `b`) is still available -- which is true for modular addition/subtraction but NOT for general-purpose reduction.

**Primary recommendation:** Replace the current `toffoli_mod_reduce` + post-hoc approach with a dedicated **modular addition primitive** (`toffoli_mod_add_qq`, `toffoli_mod_add_cq`) that implements the Beauregard 7-step sequence with clean ancilla uncomputation. Build modular subtraction as `add(N - b)` and modular multiplication as repeated controlled modular additions. Force RCA (CDKM) internally regardless of CLA policy by calling `toffoli_CQ_add` / `toffoli_cCQ_add` / `toffoli_QQ_add` / `toffoli_cQQ_add` directly rather than going through the hot_path dispatch.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `qint_mod` type "infects" results: any operation involving a `qint_mod` returns `qint_mod`
- `qint_mod + int` returns `qint_mod` (modular type always wins)
- `qint_mod + qint` returns `qint_mod` (plain qint treated like int operand)
- `qint_mod + qint_mod` with **same N**: returns `qint_mod(N)`
- `qint_mod + qint_mod` with **different N**: raises `ValueError` (mismatched moduli)
- Supported operators: `+`, `-`, `*` (and in-place `+=`, `-=`, `*=`), unary `-`
- Comparisons: inherit from `qint` as-is (==, <, >, etc.) -- values always in [0, N-1] so comparisons are meaningful
- True modular subtraction: result always in [0, N-1]; when a < b: `(a - b) mod N` = `(a - b + N)`
- Both quantum-quantum and classical-quantum subtraction supported
- Both in-place and out-of-place supported for add, sub, mul
- Negation: `-qint_mod(3, N=5)` = `qint_mod(2, N=5)` (computes N - a)
- Classical-quantum multiply: `qint_mod * int` via standard `*` operator (both `a * 3` and `3 * a`)
- Quantum-quantum multiply: `qint_mod * qint_mod` also supported (same N required)
- Controlled modular multiply supported: `with flag: a *= 3`
- Multiply by 0 returns `qint_mod(0, N)` (no error)
- N must be >= 2 (N=0 and N=1 raise `ValueError`)
- N must fit in signed 64-bit integer
- Width too small for N: auto-widen to `N.bit_length()` (with warning)
- Width larger than `N.bit_length()`: allowed
- Initial value >= N: auto-reduce classically at construction
- Mismatched moduli in binary operations: `ValueError`

### Claude's Discretion
- Ancilla allocation strategy for modular operations
- Internal RCA enforcement mechanism (success criteria requires RCA, not CLA)
- Modular reduction algorithm details (Beauregard conditional subtraction)
- Circuit optimization for controlled variants
- QQ modular multiply algorithm choice (repeated controlled modular addition vs other approaches)
- Warning mechanism for auto-widening (print, logging, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Modular exponentiation (`a^e mod N`) -- future phase (Shor's full algorithm)
- Modular inverse (`a^-1 mod N`) -- future phase
- Arbitrarily large N (beyond int64_t) -- not needed for near-term simulation
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MOD-01 | User can compute (a + b) mod N using Toffoli gates via qint_mod addition | Beauregard 7-step modular addition with clean ancilla uncomputation; dedicated `toffoli_mod_add_qq` and `toffoli_mod_add_cq` C functions |
| MOD-02 | User can compute (a - b) mod N using Toffoli gates via qint_mod subtraction | Subtraction implemented as `add(N - b)` for CQ, or `add(complement)` for QQ with proper handling |
| MOD-03 | User can compute controlled (a + b) mod N inside a with block | Controlled variants `toffoli_cmod_add_qq` / `toffoli_cmod_add_cq` using extra control qubit; Python `__enter__`/`__exit__` controlled context already works |
| MOD-04 | User can compute (a * c) mod N (c classical) using Toffoli gates via qint_mod multiplication | Schoolbook modular multiply: for each bit of c, add shifted a mod N; QQ multiply via repeated controlled modular add |
| MOD-05 | Modular operations verified exhaustively for widths 2-4 (statevector) and 5-8 (MPS) | Test framework exists in `tests/test_modular.py`; remove xfail markers, add exhaustive parameterization at higher widths using MPS simulator |
</phase_requirements>

## Standard Stack

### Core
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| C backend ToffoliModReduce.c | `c_backend/src/ToffoliModReduce.c` | Modular reduction / modular addition primitives | Phase 91 created this; Phase 92 rewrites the core algorithm |
| CDKM adder (ToffoliAdditionCDKM.c) | `c_backend/src/ToffoliAdditionCDKM.c` | RCA primitives: `toffoli_CQ_add`, `toffoli_cCQ_add`, `toffoli_QQ_add`, `toffoli_cQQ_add` | Proven correct; used by all Toffoli arithmetic |
| qint_mod (Cython) | `src/quantum_language/qint_mod.pyx` | Python API for modular arithmetic | Phase 91 skeleton; Phase 92 rewires to correct C primitives |
| qubit_allocator | `c_backend/src/qubit_allocator.c` | Ancilla alloc/free within C functions | Established pattern from multiplication/division |

### Supporting
| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| ToffoliMultiplication.c | `c_backend/src/ToffoliMultiplication.c` | Schoolbook multiply pattern | Reference for shift-and-add loop structure |
| hot_path_add_toffoli.c | `c_backend/src/hot_path_add_toffoli.c` | CLA/RCA dispatch logic | Reference for understanding adder selection; mod ops bypass this |
| Qiskit AerSimulator | External | Simulation verification | statevector for <= 17 qubits, MPS for larger |
| pytest | External | Test framework | Exhaustive parameterized tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Beauregard mod-add | General mod_reduce (current) | General mod_reduce cannot cleanly uncompute ancilla; Beauregard is specific to addition but solves the ancilla problem |
| Schoolbook mod-multiply | Montgomery multiplication | Montgomery requires gcd(N, 2^n)=1 (odd N only); schoolbook is simpler and works for all N |
| CDKM RCA | BK CLA | CLA subtraction is forward-only (cannot invert); mod operations need both add and subtract, so RCA is required |

## Architecture Patterns

### Recommended C Function Structure
```
c_backend/src/ToffoliModReduce.c  (rewrite / expand)
  toffoli_mod_add_cq()     -- (value + classical) mod N, in-place
  toffoli_cmod_add_cq()    -- controlled version
  toffoli_mod_add_qq()     -- (value + quantum) mod N, in-place
  toffoli_cmod_add_qq()    -- controlled version
  toffoli_mod_sub_cq()     -- (value - classical) mod N (= add(N - classical))
  toffoli_cmod_sub_cq()    -- controlled version
  toffoli_mod_sub_qq()     -- (value - quantum) mod N
  toffoli_cmod_sub_qq()    -- controlled version
  toffoli_mod_mul_cq()     -- (value * classical) mod N
  toffoli_cmod_mul_cq()    -- controlled version
  toffoli_mod_mul_qq()     -- (value * quantum) mod N
  toffoli_cmod_mul_qq()    -- controlled version
```

### Pattern 1: Beauregard Modular Addition (CQ variant)
**What:** The standard 7-step modular addition that cleanly uncomputes all ancillae.
**When to use:** Computing `(value + a) mod N` where `a` is classical and `value` is quantum in `[0, N-1]`.
**Algorithm (value += a mod N):**
```
Input: value in [0, N-1], classical a in [0, N-1], classical N
Ancilla: 1 qubit (cmp_anc), initialized to |0>

Step 1: value += a                    (CQ add, CDKM)
         -- value now in [0, 2N-2]
Step 2: value -= N                    (CQ add of -N, CDKM)
         -- if value was >= N: now in [0, N-2], MSB/overflow bit = 0
         -- if value was < N: wrapped to [2^n - N, 2^n - 1], high bit signals borrow
Step 3: Copy sign to cmp_anc          (CNOT: cmp_anc ^= high_bit)
         -- cmp_anc = 1 if value < N after step 1 (borrow occurred)
         -- cmp_anc = 0 if value >= N after step 1 (no borrow)
Step 4: Controlled add N              (if cmp_anc=1: value += N, restoring original)
         -- value now = (value + a) mod N in both cases
Step 5: value -= a                    (CQ add of -a, CDKM -- reverse of step 1)
         -- value now back to original value (step 4 restored mod-N result, step 5 undoes step 1)
         -- EXCEPT: value = original_value if no reduction, or original_value - N + N - a + a...
         -- Actually: after step 4, value = (orig + a) mod N.
         --   Step 5: value = (orig + a) mod N - a
         --   If orig + a < N (no reduction): value = orig. cmp_anc was 1.
         --   If orig + a >= N (reduction): value = orig + a - N - a = orig - N.
         --     Since orig < N: value = orig - N < 0, wraps to 2^n + orig - N.
         --     cmp_anc was 0.
         -- To reset cmp_anc: compare value vs 0 (check if value is negative/wrapped)
Step 6: X(cmp_anc)                    (flip cmp_anc)
         -- Now: cmp_anc = 0 if value < N after step 1 (original case, value = orig)
         --       cmp_anc = 1 if value >= N (wrapped case, value = 2^n + orig - N)
Step 7: Use (n+1)-bit subtraction to detect if value is in [0, N-1]:
         -- If value is in [0, N-1] (original, no wrap): high bit from subtracting N = 1
         --   cmp_anc is 0 after X. But we need to uncompute it.
         -- ALTERNATIVE RESET:
         --   Detect whether value < 0 (in unsigned: value > N-1).
         --   If cmp_anc_after_X = 1 (wrapped): controlled add N: value += N -> value = orig.
         --     Now cmp_anc should be reset.
         --   CNOT(cmp_anc, based on comparison)...
```

The above shows the complexity. Let me state the CORRECT standard Beauregard sequence used in practice:

**Correct Beauregard 7-step sequence for CQ modular add (value += a mod N):**
```
Allocate: (n+1)-bit temp register, 1 cmp_anc qubit

1. value += a                        [CQ add using CDKM]
2. value -= N                        [CQ add of -N using CDKM, on (n+1)-bit register]
3. cmp_anc = sign(value)             [CNOT from MSB/overflow to cmp_anc]
4. if cmp_anc: value += N            [controlled CQ add of +N]
   -- Now value = (orig + a) mod N. cmp_anc still set from step 3.
5. value -= a                        [CQ add of -a -- UNDO step 1]
   -- Now value = (orig + a) mod N - a = orig (if no reduction) or orig - N (if reduction)
6. X(cmp_anc)                        [Flip]
7. if sign(value) negative: X(cmp_anc)  [Detects whether value wrapped below 0]
   -- Equivalently: compare value < 0 in unsigned, use that to reset cmp_anc
   -- After this: cmp_anc = 0 in both cases
8. value += a                        [CQ add of +a -- REDO step 1, now with cmp_anc clean]
   -- value = orig + a (no reduction) or orig - N + a (reduction)
   -- But step 4 already applied the reduction, so...

WAIT: The standard sequence actually avoids this complexity. The CORRECT version:

BEAUREGARD MODULAR ADDITION (a + b mod N):
  -- Given: b register in [0, N-1], classical a in [0, N-1], classical N
  -- Using: QFT-based adder (Draper) in Beauregard's original
  -- For Toffoli: use CDKM adder instead

  1. ADD(a, b)        -- b += a. Now b in [a, a+N-1] subset [0, 2N-2]
  2. ADD(-N, b)       -- b -= N. If b >= N: b in [0, N-2]. If b < N: b wrapped (negative in signed)
  3. CNOT(MSB(b), anc) -- anc = sign_bit (1 if b < 0 in signed = wrapped)
  4. cADD(N, b, anc)  -- if anc=1: b += N (restore). Now b = (a+orig_b) mod N
  5. ADD(-a, b)       -- b -= a. Now b = orig_b (if no reduction) or orig_b - N (if reduction)
  6. X(anc)           -- flip
  7. CNOT(MSB(b), anc) -- detect sign of (orig_b - N) which is always negative since orig_b < N
                       -- MSB = 1 (negative). anc was flipped in step 6.
                       -- If no reduction: b = orig_b >= 0, MSB = 0. X made anc = 0. CNOT(0) = 0. OK ✓
                       -- If reduction: b = orig_b - N < 0 (wrapped), MSB = 1. X made anc = 1. CNOT(1) = 0. OK ✓
                       -- WRONG: Let me trace more carefully.

Actually, let me trace both cases:
  Case A: orig_b + a < N (no reduction needed)
    Step 1: b = orig_b + a (< N)
    Step 2: b = orig_b + a - N (< 0, wrapped). In (n+1)-bit: MSB = 1.
    Step 3: anc = 1
    Step 4: anc=1, so b += N. b = orig_b + a.
    Step 5: b -= a. b = orig_b.
    Step 6: X(anc). anc = 0.
    Step 7: b = orig_b. In (n+1)-bit: orig_b >= 0, MSB = 0. CNOT(anc, 0) -> anc = 0. ✓

  Case B: orig_b + a >= N (reduction needed)
    Step 1: b = orig_b + a (>= N)
    Step 2: b = orig_b + a - N (>= 0). In (n+1)-bit: MSB = 0.
    Step 3: anc = 0
    Step 4: anc=0, so nothing. b = orig_b + a - N.
    Step 5: b -= a. b = orig_b - N (< 0, wrapped). In (n+1)-bit: MSB = 1.
    Step 6: X(anc). anc = 1.
    Step 7: CNOT(anc, MSB). MSB = 1. anc = 1 XOR 1 = 0. ✓

  Now anc = 0 in both cases! Then:
  Step 8: b += a.
    Case A: b = orig_b + a (correct, < N)
    Case B: b = orig_b - N + a = orig_b + a - N (correct modular result)

  FINAL: b = (orig_b + a) mod N. anc = 0 (clean). ✓
```

This is the correct Beauregard modular addition sequence. The key insight for ancilla uncomputation is: after step 5 (`b -= a`), the sign of b distinguishes the two cases (reduction vs no reduction), allowing the ancilla to be reset in step 7.

**CRITICAL:** This requires 8 addition operations (steps 1-5 and step 8 are additions/subtractions, steps 3/7 are CNOTs, step 6 is X). For CQ operations, steps 1, 2, 4, 5, 8 use `toffoli_CQ_add` (or `toffoli_cCQ_add` for controlled versions).

### Pattern 2: Modular Subtraction via Addition
**What:** `(a - b) mod N` = `(a + (N - b)) mod N`
**When to use:** All modular subtraction operations.
**Implementation:**
- CQ subtraction: `value -= classical_b mod N` becomes `mod_add_cq(value, N - classical_b, N)` (computed classically since both b and N are classical)
- QQ subtraction: More complex; requires computing `N - b` on a quantum register, then modular adding, then uncomputing `N - b`. Alternative: direct QQ mod-sub circuit.
- Negation: `-qint_mod(a, N)` = `(N - a)` = modular add of `(N - a)` to zero, or subtract `a` from `N`.

### Pattern 3: Modular CQ Multiplication via Repeated Modular Addition
**What:** `(value * c) mod N` where `c` is classical.
**When to use:** Classical-quantum modular multiplication (MOD-04).
**Algorithm:**
```
result = 0  (n-bit quantum register, initialized to |0>)
For each bit j of c (from LSB to MSB):
  if c[j] == 1:
    result += (value << j) mod N      -- i.e., mod_add_cq(result, (value_classical_shift * 2^j) mod N, N)
  Wait -- value is quantum, not classical. Can't precompute shifts.

CORRECT approach for CQ multiply (value * classical_c mod N):
  result = 0
  For each bit j of c (from LSB to MSB):
    if c[j] == 1:
      mod_add_qq(result, value, N)   -- result += value mod N
    value = (value * 2) mod N        -- but value is quantum, can't classically double

WAIT: For CQ multiply, the multiplier c is classical. So we precompute:
  a_j = (c * 2^j) mod N for each j from 0 to n-1   -- these are all classical values
  Then: value * c mod N = sum_{j where value[j]=1} a_j mod N
  This is a sum of classical values, controlled by quantum bits of value.

  For each bit j of value (quantum):
    controlled_mod_add_cq(result, a_j, N, control=value[j])

This is the standard approach: n controlled modular additions of classical values.
```

### Pattern 4: Modular QQ Multiplication via Repeated Controlled Modular Addition
**What:** `(a * b) mod N` where both `a` and `b` are quantum.
**When to use:** Quantum-quantum modular multiplication.
**Algorithm:**
```
result = 0  (n-bit register)
For each bit j of b:
  controlled_mod_add_qq(result, a, N, control=b[j])
  a = (a * 2) mod N   -- quantum doubling mod N (= mod_add_qq(a, a, N))

But doubling a is modifying the input register, which must be preserved.
Alternative: precompute shifts and use controlled additions.

For QQ multiply: value * other mod N:
  result = 0
  For each bit j of other:
    shift_val = (2^j) -- classical
    controlled: result += value * shift_val mod N
    But this is controlled QQ mod add of (value << j), which is still QQ.

SIMPLER: Follow schoolbook multiplication pattern from ToffoliMultiplication.c:
  result = 0
  For each bit j of other (quantum register):
    For the sub-register value[0..n-1-j] shifted by j:
      controlled_mod_add_qq(result[j..n-1], value[0..n-1-j], N, control=other[j])

This requires n iterations of controlled QQ modular addition.
Each iteration: Beauregard mod_add with external control (doubly-controlled operations).
```

### Pattern 5: RCA Enforcement for Modular Operations
**What:** Force CDKM ripple-carry adder regardless of CLA policy.
**Why:** CLA (Brent-Kung) subtraction is forward-only -- the sequence cannot be inverted. Beauregard modular addition requires both forward addition and inverse (subtraction). Since `run_instruction(seq, qa, invert=1, circ)` must work, CLA cannot be used.
**How to implement:**
- Call `toffoli_CQ_add()` / `toffoli_cCQ_add()` / `toffoli_QQ_add()` / `toffoli_cQQ_add()` directly (these are always CDKM/RCA)
- Do NOT use `hot_path_add_cq` or `hot_path_add_qq` (which go through CLA dispatch)
- Do NOT use `mod_cq_add` helper (which also calls `toffoli_CQ_add` already, but the ancilla layout must be carefully managed)
- Allocate ancillae explicitly within the C function using `allocator_alloc` / `allocator_free`

### Anti-Patterns to Avoid
- **General mod_reduce then mod_add:** Don't implement modular addition as `add(a, b)` then `mod_reduce(result)`. This approach (current Phase 91) cannot cleanly uncompute the comparison ancilla because the original operand `a` is no longer available after reduction.
- **Python-level reduction:** Don't implement reduction in Python/Cython. The old `_reduce_mod` leaked n+1 qubits per comparison. All modular arithmetic must happen at C level.
- **CLA for modular operations:** CLA's forward-only limitation makes it incompatible with the Beauregard sequence which requires `run_instruction(seq, qa, invert=1)` for subtraction steps.
- **Separate sign-bit register:** Don't use an (n+1)-bit register for the value. The Beauregard approach works with the existing n-bit register by using temporary widening only during the comparison steps (allocate n+1-bit temp, copy, compare, uncopy, free).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CDKM adder sequences | Custom adder circuit | `toffoli_CQ_add()`, `toffoli_QQ_add()`, `toffoli_cCQ_add()`, `toffoli_cQQ_add()` | Proven correct, cached, handles all widths |
| Ancilla allocation | Manual qubit tracking | `allocator_alloc()` / `allocator_free()` | Handles fragmentation, reuse, statistics |
| Gate emission | Direct gate_t construction | `mod_emit_cx()`, `mod_emit_ccx()`, `mod_emit_x()` helpers | Already exist in ToffoliModReduce.c |
| Controlled context | Custom control qubit management | Python `with flag:` / `_get_controlled()` / `_get_control_bool()` | Established project pattern |

**Key insight:** The modular addition circuit is fundamentally different from general modular reduction. It exploits the fact that one operand is still available to create an uncomputation path for the comparison ancilla. This is not a bug fix for `toffoli_mod_reduce` -- it is a fundamentally different algorithm.

## Common Pitfalls

### Pitfall 1: Persistent Ancilla in Modular Reduction
**What goes wrong:** The comparison ancilla (`cmp_anc`) in `toffoli_mod_reduce` cannot be uncomputed because after conditional subtraction of N, the value register no longer contains enough information to re-derive the comparison result.
**Why it happens:** The Phase 91 implementation uses a general-purpose "compare and conditionally subtract" approach. After subtraction, both cases (subtracted and not-subtracted) produce values in `[0, N-1]`, making them indistinguishable.
**How to avoid:** Use the Beauregard 8-step modular addition sequence which includes `subtract a` (step 5) to distinguish cases, then `add a` (step 8) to produce the final result.
**Warning signs:** Test failures where `a + b >= N` (reduction needed) but `a + b < N` passes (no reduction).

### Pitfall 2: Width Mismatch in (n+1)-bit Operations
**What goes wrong:** The Beauregard sequence uses (n+1)-bit addition to detect borrow/overflow. If the extra bit is not properly handled, the comparison result is wrong.
**Why it happens:** CDKM adder operates on n-bit registers. For (n+1)-bit operations, the value register must be temporarily widened by copying to a wider temp register.
**How to avoid:** Use the helper pattern from Phase 91's `mod_cq_add`: copy value to (n+1)-bit temp, perform (n+1)-bit arithmetic, extract sign, uncopy. Or: use the value register at n bits and a separate high-bit ancilla that acts as bit n.
**Warning signs:** Incorrect sign detection, values that should reduce don't.

### Pitfall 3: Subtraction via Inverse Addition
**What goes wrong:** CDKM subtraction uses `run_instruction(seq, qa, invert=1, circ)` which reverses the gate sequence. This works for CDKM but NOT for CLA.
**Why it happens:** CLA carry-copy ancillae are not fully uncomputed when the sequence is reversed.
**How to avoid:** Always use CDKM (RCA) adders for modular operations. Call `toffoli_CQ_add()` directly, never `toffoli_CQ_add_bk()`.
**Warning signs:** Ancilla corruption when subtracting, correct addition but wrong subtraction.

### Pitfall 4: Qubit Layout Convention Mismatch
**What goes wrong:** C functions use LSB-first qubit arrays, Python uses right-aligned 64-element arrays. Incorrect mapping corrupts operands.
**Why it happens:** The `qubits[64 - bits + i]` mapping in Cython must produce LSB-first arrays for C.
**How to avoid:** Follow the exact pattern used in `qint_mod._reduce_mod_c()`: `value_qa[i] = value.qubits[offset + i]` where `offset = 64 - n`.
**Warning signs:** Results are bit-reversed or shifted.

### Pitfall 5: Controlled Modular Operations Require Double-Controlled Additions
**What goes wrong:** A controlled modular addition (`with flag: a += b mod N`) requires that ALL internal additions in the Beauregard sequence are controlled by the external control qubit. Steps 1-8 each become controlled.
**Why it happens:** If only the "main" addition is controlled but the comparison/uncomputation steps are not, the ancilla gets corrupted in the uncontrolled branch.
**How to avoid:** Use `toffoli_cCQ_add()` / `toffoli_cmod_add_cq()` for all steps. For doubly-controlled operations (controlled by both `cmp_anc` AND `ext_ctrl`), use the AND-ancilla pattern: `CCX(and_anc, cmp_anc, ext_ctrl); cCQ_add(controlled by and_anc); CCX(and_anc, cmp_anc, ext_ctrl)`.
**Warning signs:** Controlled operations leave extra entanglement; uncontrolled path (control=0) modifies the register.

### Pitfall 6: Modular Multiplication Qubit Budget
**What goes wrong:** Modular CQ multiplication requires n iterations of controlled modular addition. Each modular addition uses temporary ancillae, but if the total qubit count exceeds 17, statevector simulation fails.
**Why it happens:** For width n, each modular addition needs ~(n+1) temp qubits + 1 cmp_anc. With n iterations, the peak ancilla count is ~(n+2) if ancillae are freed between iterations.
**How to avoid:** Ensure allocator_free is called after each modular addition step. Check total qubit count: for width 4, value(4) + result(4) + ancillae(~6) = ~14 qubits. For width 8 with MPS: value(8) + result(8) + ancillae(~10) = ~26 qubits (fine for MPS, but not statevector).
**Warning signs:** Simulation crashes or runs out of memory for larger widths.

### Pitfall 7: Simulator Limit for Testing
**What goes wrong:** Tests at width 5+ exceed 17-qubit statevector limit.
**Why it happens:** Modular multiplication at width 5 uses value(5) + result(5) + ancillae(~7) = 17+ qubits.
**How to avoid:** Use MPS simulator for widths 5-8 (as specified in MOD-05). Statevector only for widths 2-4.
**Warning signs:** Qiskit simulation hangs or errors with "insufficient memory".

## Code Examples

### Example 1: Beauregard Modular CQ Addition (C-level)
```c
// Source: Beauregard (2003), adapted for CDKM adder
// value += classical_a mod N  (value in [0, N-1])
void toffoli_mod_add_cq(circuit_t *circ, const unsigned int *value_qubits,
                         int value_bits, int64_t addend, int64_t modulus) {
    int n = value_bits;
    int64_t a = addend % modulus;  // Reduce classically
    if (a == 0) return;  // Nothing to do

    // Allocate (n+1)-bit working register for sign detection
    // We work directly on value (n bits) + 1 high_bit ancilla
    qubit_t high_bit = allocator_alloc(circ->allocator, 1, true);
    qubit_t cmp_anc = allocator_alloc(circ->allocator, 1, true);

    // Build (n+1)-bit register: [value_qubits[0..n-1], high_bit]
    unsigned int wide_reg[64];
    for (int i = 0; i < n; i++) wide_reg[i] = value_qubits[i];
    wide_reg[n] = high_bit;

    // Step 1: value += a  (on n+1 bits so overflow goes to high_bit)
    mod_cq_add(circ, wide_reg, n + 1, a);

    // Step 2: value -= N
    mod_cq_add(circ, wide_reg, n + 1, -modulus);

    // Step 3: Copy sign (high_bit) to cmp_anc
    mod_emit_cx(circ, cmp_anc, wide_reg[n]);

    // Step 4: if cmp_anc=1: value += N (controlled)
    mod_ccq_add(circ, wide_reg, n + 1, modulus, cmp_anc);

    // Step 5: value -= a (UNDO step 1)
    mod_cq_add(circ, wide_reg, n + 1, -a);

    // Step 6: X(cmp_anc)
    mod_emit_x(circ, cmp_anc);

    // Step 7: Copy sign to reset cmp_anc
    // After step 5: value = orig_b (case A) or 2^(n+1)+orig_b-N (case B, wrapped)
    // Sign bit: case A: 0, case B: 1
    // cmp_anc after X: case A: 0, case B: 1
    // CNOT(cmp_anc, sign): case A: 0^0=0 ✓, case B: 1^1=0 ✓
    mod_emit_cx(circ, cmp_anc, wide_reg[n]);

    // Step 8: value += a (REDO step 1)
    mod_cq_add(circ, wide_reg, n + 1, a);

    // high_bit should be 0 now (value back in [0, N-1], fits in n bits)
    allocator_free(circ->allocator, cmp_anc, 1);
    allocator_free(circ->allocator, high_bit, 1);
}
```

### Example 2: Modular CQ Subtraction (wrapper)
```c
// (value - b) mod N = (value + (N - b)) mod N
void toffoli_mod_sub_cq(circuit_t *circ, const unsigned int *value_qubits,
                         int value_bits, int64_t subtrahend, int64_t modulus) {
    int64_t complement = (modulus - (subtrahend % modulus)) % modulus;
    toffoli_mod_add_cq(circ, value_qubits, value_bits, complement, modulus);
}
```

### Example 3: Modular CQ Multiplication
```c
// result = value * classical_c mod N
// Uses: for each bit j of value, controlled mod_add of (c * 2^j mod N)
void toffoli_mod_mul_cq(circuit_t *circ, const unsigned int *value_qubits,
                         int value_bits, const unsigned int *result_qubits,
                         int result_bits, int64_t multiplier, int64_t modulus) {
    int n = value_bits;
    int64_t shifted = multiplier % modulus;

    for (int j = 0; j < n; j++) {
        if (shifted != 0) {
            // Controlled modular addition: result += shifted mod N, controlled by value[j]
            toffoli_cmod_add_cq(circ, result_qubits, result_bits,
                                shifted, modulus, value_qubits[j]);
        }
        shifted = (shifted * 2) % modulus;  // Classical doubling
    }
}
```

### Example 4: Python qint_mod.__add__ (rewired)
```python
# Source: existing qint_mod.pyx pattern
def __add__(self, other):
    if isinstance(other, qint_mod):
        if other._modulus != self._modulus:
            raise ValueError(f"Moduli must match")

    # Allocate result register
    result = qint_mod.__new__(qint_mod)
    # ... copy self to result using XOR ...

    # Dispatch to C-level modular addition
    if isinstance(other, int):
        toffoli_mod_add_cq(_circ, result_qa, n, other % self._modulus, self._modulus)
    elif isinstance(other, qint_mod) or isinstance(other, qint):
        toffoli_mod_add_qq(_circ, result_qa, n, other_qa, other_bits, self._modulus)

    return self._wrap_result(result)
```

## State of the Art

| Old Approach (Phase 91) | New Approach (Phase 92) | Impact |
|--------------------------|-------------------------|--------|
| `toffoli_mod_reduce` (general purpose) | Beauregard modular add (operation-specific) | Clean ancilla uncomputation; all cases correct |
| Python-level `add + reduce` | Single C-level `toffoli_mod_add_cq` | Fewer function calls, cleaner qubit management |
| `qint.__sub__` then `+= N` then reduce | `toffoli_mod_sub_cq` as `mod_add(N-b)` | Correct subtraction semantics, no unconditional N addition |
| `qint.__mul__` then reduce (multiple passes) | Schoolbook controlled mod-add loop | Fewer total reductions, deterministic ancilla count |
| `xfail` tests for all reduction cases | Exhaustive passing tests widths 2-8 | Full correctness verification |

## Open Questions

1. **QQ Modular Addition: Beauregard sequence with quantum operand**
   - What we know: CQ variant (classical addend) works because `a` is available for steps 5 and 8. For QQ variant, the addend `b` is quantum and must be preserved.
   - What's unclear: Whether the QQ version needs a copy of `b` (extra n qubits) or can use `b` directly (it is preserved by addition since CDKM QQ add preserves the source register).
   - Recommendation: CDKM QQ add preserves the `b` register. So `toffoli_QQ_add(result, b)` does `result += b` and `b` is unchanged. Steps 5 and 8 can use `b` directly. This should work. Verify with testing.

2. **QQ Modular Multiplication Qubit Budget**
   - What we know: QQ multiply uses n controlled QQ modular additions. Each needs temporary ancillae.
   - What's unclear: Total qubit count for QQ multiply at width 8.
   - Recommendation: Estimate: value(8) + other(8) + result(8) + per-iteration-ancillae(~10) = ~34 qubits. Fine for MPS. May need to verify MPS handles this circuit size in reasonable time.

3. **`_modulus` field width: `int` vs `int64_t`**
   - What we know: The `qint_mod.pxd` declares `cdef int _modulus`. CONTEXT.md says N fits in int64_t.
   - What's unclear: Whether `int` (32-bit on most platforms) is sufficient. For N up to 2^63-1, need int64_t.
   - Recommendation: Change `_modulus` from `int` to `int64_t` in the `.pxd` file. This is a one-line change but important for correctness with large N.

4. **Existing `toffoli_mod_add_cq` and `toffoli_cmod_add_cq` functions**
   - What we know: Phase 91 created these in ToffoliModReduce.c. They are simple wrappers: `add + reduce`.
   - What's unclear: Whether to rename or replace them.
   - Recommendation: Replace the implementations entirely with the Beauregard 8-step sequence. Keep the same function signatures. This is a drop-in replacement.

5. **Controlled Modular Addition: ext_ctrl + cmp_anc Double Control**
   - What we know: Step 4 of Beauregard requires `controlled add N, controlled by cmp_anc`. For a controlled modular addition (external control), this becomes doubly-controlled.
   - What's unclear: Whether the AND-ancilla pattern from ToffoliModReduce.c's `toffoli_cmod_reduce` is sufficient.
   - Recommendation: Yes, use the same pattern: `CCX(and_anc, cmp_anc, ext_ctrl); controlled_add(N, and_anc); CCX(and_anc, cmp_anc, ext_ctrl)`. This is already implemented in Phase 91's controlled variant.

## Sources

### Primary (HIGH confidence)
- Project codebase: `c_backend/src/ToffoliModReduce.c` -- Current modular reduction implementation with persistent ancilla leak
- Project codebase: `c_backend/src/ToffoliAdditionCDKM.c` -- CDKM ripple-carry adder (proven correct, all variants)
- Project codebase: `src/quantum_language/qint_mod.pyx` -- Existing qint_mod skeleton (Phase 91)
- Project codebase: `tests/test_modular.py` -- Existing tests with xfail markers for known failures
- Project codebase: `.planning/phases/91-arithmetic-bug-fixes/91-02-SUMMARY.md` -- Phase 91 mod_reduce summary documenting persistent ancilla issue

### Secondary (MEDIUM confidence)
- [Beauregard (2003) "Circuit for Shor's algorithm using 2n+3 qubits"](https://arxiv.org/abs/quant-ph/0205095) -- Original modular addition circuit with ancilla uncomputation
- [Haner, Roetteler, Svore (2017) "Factoring using 2n+2 qubits with Toffoli based modular multiplication"](https://arxiv.org/abs/1611.07995) -- Toffoli-based modular multiplication with dirty ancilla reuse
- [Comprehensive Study of Quantum Arithmetic Circuits (2024)](https://arxiv.org/html/2406.03867v1) -- Survey of quantum arithmetic including modular operations

### Tertiary (LOW confidence)
- Training data knowledge of Beauregard modular addition sequence -- verified against codebase constraints but not verified against the actual paper text (PDF not parseable)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All components already exist in the codebase; Phase 92 rewrites the algorithm inside existing functions
- Architecture: HIGH -- Beauregard modular addition is the standard approach in quantum computing; the 8-step sequence is well-established
- Pitfalls: HIGH -- Most pitfalls identified from actual Phase 91 bugs and code analysis
- Modular addition sequence correctness: MEDIUM -- Hand-traced both cases and they check out, but not verified against actual Beauregard paper text. Step numbering may differ from literature.

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain, established algorithms)
