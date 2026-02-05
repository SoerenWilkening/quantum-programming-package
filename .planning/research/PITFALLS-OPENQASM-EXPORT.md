# Domain Pitfalls: OpenQASM Export and Qiskit-Based Verification

**Domain:** Adding OpenQASM 3.0 export and Qiskit verification to existing quantum circuit framework
**Researched:** 2026-01-30
**Confidence:** HIGH (based on official OpenQASM 3 spec, Qiskit documentation, and current codebase analysis)

## Executive Summary

Adding OpenQASM export and Qiskit-based verification to an existing quantum framework involves navigating a minefield of subtle incompatibilities. The core challenges fall into five categories: (1) gate naming and syntax mismatches between internal representation and OpenQASM 3 standard library, (2) qubit ordering conventions where Qiskit's little-endian differs from internal layouts, (3) multi-controlled gate decomposition where Qiskit requires specific formats, (4) verification challenges distinguishing deterministic from probabilistic outcomes, and (5) floating-point precision in phase gate angle representation. The existing Quantum Assembly codebase already has OpenQASM export (`circuit_to_opanqasm` in circuit_output.c) but with critical bugs: Y/R/Rx/Ry/Rz gates are no-ops, large_control array is ignored, file handle not closed, and function has typo in name.

## Critical Pitfalls

These mistakes cause export failures, incorrect circuit semantics, or verification false positives/negatives.

### Pitfall 1: Qubit Ordering Mismatch (Endianness Convention)

**What goes wrong:** Internal circuit uses right-aligned qubit layout (LSB = lowest qubit index), but OpenQASM/Qiskit use little-endian convention where qubit 0 is rightmost in statevector but topmost in circuit diagrams. When exporting classical initialization or verifying measurement results, qubit index mapping can be inverted, causing:
- Classical integer 5 initialized on wrong qubits (qubit pattern reversed)
- Measurement results interpreted backward (bit 0 and bit n-1 swapped)
- Multi-qubit gate operand order flipped (control and target reversed)
- Statevector comparison fails despite correct circuit logic

**Why it happens:**
- Quantum Assembly uses "right-aligned" layout for variable-width integers (LSB at lowest index)
- Qiskit uses little-endian: qubit 0 = LSB = 2^0 weight = rightmost in bitstring
- OpenQASM 3 spec says "qubit n-1 is leftmost in string representation"
- Circuit diagrams show qubit 0 at TOP but qubit 0 is the RIGHTMOST bit in measurement results
- Different conventions for qargs in gate definitions vs measurement result ordering

**Consequences:**
- Verification tests pass with wrong circuit (false positive)
- Classical initialization creates flipped bit patterns
- Multi-controlled gates control wrong qubits
- Results appear correct in isolation but fail when integrated with other systems
- **Subtle bug that only manifests when comparing with external simulators**

**Prevention:**
1. **Document index mapping explicitly:** Create mapping table showing Quantum Assembly qubit index → OpenQASM qubit[i] → Qiskit qubit_i → measurement bit position
2. **Systematic test cases:** For each classical initialization (e.g., qint(5, width=4)), verify:
   - Internal circuit qubit pattern
   - Exported OpenQASM qubit indices
   - Qiskit statevector amplitude ordering
   - Measurement result bitstring interpretation
3. **Use `from_label()` for verification:** When verifying classical init, use `Statevector.from_label("0101")` where rightmost = qubit 0 to match Qiskit convention
4. **Reverse bits if needed:** If Quantum Assembly and Qiskit use opposite conventions, insert explicit reverse_bits() call or index transformation
5. **Measurement result parsing:** Extract measurement results using `int(result, 2)` where result[0] is qubit n-1 (leftmost) and result[-1] is qubit 0 (rightmost)

**Detection (warning signs):**
- Classical initialization tests fail: qint(5, width=4) exports as `x q[0]; x q[2];` (binary 0101) but Qiskit measures "1010"
- Multi-controlled gates don't apply when expected
- Statevector has amplitude at wrong index (e.g., |5⟩ amplitude at index 10 instead of 5)
- Verification script reports "qubit ordering mismatch" warnings

**Which phase:** Phase 1 (Fix Export) must document and test qubit ordering; Phase 3 (Verification) will catch remaining issues in integration tests

**Sources:**
- [Qiskit Bit Ordering Guide](https://quantum.cloud.ibm.com/docs/guides/bit-ordering) — "qubit 0 is the least significant bit"
- [OpenQASM 3 Spec - Qubit Indexing](https://openqasm.com/language/gates.html) — "nth qubit argument is n places from the right"
- Codebase: PROJECT.md "Right-aligned qubit array layout (LSB = lowest qubit index)"

---

### Pitfall 2: Multi-Controlled Gate Syntax and Decomposition

**What goes wrong:** Quantum Assembly supports n-controlled X gates via `large_control` array, but:
- Current export code ignores `large_control` (line 114, 322: only uses Control[0], Control[1])
- OpenQASM 3 syntax for multi-controlled gates uses `ctrl @` modifier, NOT `ccccx` for 4+ controls
- Qiskit's MCXGate requires specific decomposition mode ('noancilla', 'recursion', 'v-chain', 'v-chain-dirty')
- Exporting `ccccx q[0], q[1], q[2], q[3], q[4];` (4 controls, 1 target) is INVALID in OpenQASM 3.0

**Why it happens:**
- OpenQASM 3 standard library only defines: `cx` (1 control), `ccx` (2 controls), `cswap` (1 control)
- For >2 controls, must use gate modifier syntax: `ctrl(3) @ x q[0], q[1], q[2], q[3];` (3 controls + 1 target)
- Current Quantum Assembly export uses prefix notation `ccc...x` which isn't valid OpenQASM 3
- Qiskit can parse `ctrl @` but may not support all control counts without decomposition
- The `large_control` array is allocated but never read in export function

**Consequences:**
- OpenQASM export fails to parse (syntax error on `cccx`)
- Multi-controlled gates silently export with wrong control count (only first 2 controls)
- Qiskit import fails: "gate 'cccx' not recognized"
- Verification tests use wrong circuit (missing control qubits)
- **This affects ALL comparison operations with >2 qubits (uses multi-controlled X)**

**Prevention:**
1. **Fix export to use `ctrl @` modifier:**
   ```c
   if (g.NumControls > 2) {
       fprintf(oq_file, "ctrl(%d) @ x ", g.NumControls);
       for (int i = 0; i < g.NumControls; i++)
           fprintf(oq_file, "q[%d]%s", g.large_control[i], i < g.NumControls ? ", " : "");
       fprintf(oq_file, "q[%d];\n", g.Target);
   }
   ```
2. **Use OpenQASM 3 gate modifier syntax:** `ctrl(n) @ gate` for n controls
3. **Test large_control array:** Add test case with >2 controls, verify all control indices exported
4. **Qiskit compatibility check:** After export, test that `qiskit.qasm3.load()` can parse the file
5. **Document decomposition mode:** In verification script, specify MCXGate mode if needed (default 'noancilla' works but may be slow)

**Detection (warning signs):**
- OpenQASM parser error: "unexpected token 'cccx'"
- Qiskit import raises `QASM3ImporterError`
- Multi-controlled gate test exports only 2 controls despite NumControls = 5
- Comparison operations (>=, <=) fail verification with wrong results

**Which phase:** Phase 1 (Fix Export) must implement correct syntax; Phase 2 (Qiskit Integration) validates with import tests

**Sources:**
- [OpenQASM 3 Gates Spec](https://openqasm.com/language/gates.html) — "ctrl @ replaces gate U by controlled-U"
- [Qiskit MCXGate Documentation](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.MCXGate) — Decomposition modes
- [MCMT Gate Deprecation Notice](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.MCMT) — "Deprecated as of Qiskit 1.4"
- Codebase: circuit_output.c line 114, 322 — large_control not used

---

### Pitfall 3: Gate Naming and Missing Gate Implementations

**What goes wrong:** Current export has several no-op cases:
- `case Y: break;` (line 310) — Y gate not exported
- `case R: break;` (line 312) — R gate not exported
- `case Rx: break;` (line 314) — Rx rotation not exported
- `case Ry: break;` (line 316) — Ry rotation not exported
- `case Rz: break;` (line 318) — Rz rotation not exported

Additionally:
- `case M: fprintf(oq_file, "m ");` (line 308) — `m` is NOT a valid OpenQASM 3 gate, measurement is `measure q[i] -> c[i];`
- Phase gate exports 20 decimal places but OpenQASM 3 uses fixed-point `angle[n]` type

**Why it happens:**
- Original export function was incomplete placeholder
- OpenQASM 2.0 used `measure` statement, but internal gate enum has `M` token
- Rotation gates (Rx, Ry, Rz) have different capitalization in OpenQASM: `rx(θ)`, `ry(θ)`, `rz(θ)` (lowercase)
- Phase gate in OpenQASM is `p(λ)` with angle parameter, but precision semantics differ
- Y gate is `y` in OpenQASM (lowercase)

**Consequences:**
- Circuits with Y, Rx, Ry, Rz gates export as empty (no gates in those layers)
- Measurement gate exports as invalid syntax `m q[i];` instead of `measure q[i] -> c[i];`
- Qiskit import fails or produces empty circuit
- Phase angles may lose precision or export in wrong format
- **Entire gate types silently dropped from export**

**Prevention:**
1. **Complete gate mapping table:**
   ```
   Internal  → OpenQASM 3
   X         → x
   Y         → y
   Z         → z
   H         → h
   P(θ)      → p(θ)
   Rx(θ)     → rx(θ)
   Ry(θ)     → ry(θ)
   Rz(θ)     → rz(θ)
   M         → measure q[i] -> c[i]; (requires classical register)
   R         → reset q[i]; (if R means reset)
   ```
2. **Add classical register for measurements:** If circuit contains M gates, declare `bit[n] c;` and export `measure q[i] -> c[i];`
3. **Fix gate name capitalization:** All single-qubit gates are lowercase in OpenQASM 3
4. **Test each gate type:** Add verification test for X, Y, Z, H, P, Rx, Ry, Rz, measure
5. **Angle precision:** Use `%.17g` format (17 significant digits) instead of `%.20f` to match IEEE double precision

**Detection (warning signs):**
- Exported QASM file much smaller than expected (missing gates)
- Qiskit import raises "unknown gate 'm'" error
- Circuit with Y gates exports but Qiskit shows only identity
- Rotation gate circuits fail verification (wrong final state)

**Which phase:** Phase 1 (Fix Export) implements all gate types

**Sources:**
- [OpenQASM 3 Standard Library](https://openqasm.com/language/standard_library.html) — Complete gate list with lowercase names
- [OpenQASM 3 Built-in Instructions](https://openqasm.com/language/insts.html) — `measure` and `reset` syntax
- Codebase: circuit_output.c lines 310-318 — Missing gate implementations

---

### Pitfall 4: Phase Gate Precision and Angle Representation

**What goes wrong:** Phase gate exports as `p(%.20f)` using floating-point format, but:
- OpenQASM 3 defines `angle[n]` fixed-point type for phase parameters (not float)
- Fixed-point angles represent values in [0, 2π) with binary decimal expansion
- Floating-point angles may exceed 2π or be negative, requiring modular arithmetic
- Qiskit may interpret phase angles differently depending on import path (qasm2 vs qasm3)
- Precision loss when converting from double (53 bits) to angle[n] with smaller n

**Why it happens:**
- OpenQASM 3 introduced fixed-point `angle[n]` to match quantum control hardware
- Current export uses `fprintf(oq_file, "p(%.20f) ", g.GateValue);` (line 296) — raw float
- No angle normalization to [0, 2π)
- No consideration of angle bit-width requirements
- Different hardware backends support different angle precisions

**Consequences:**
- Phase angles outside [0, 2π) may wrap unexpectedly
- Precision loss for small angles (e.g., π/1024)
- Different results when running on hardware vs simulator
- Verification fails due to phase differences below floating-point epsilon
- **Especially problematic for QFT and phase estimation algorithms**

**Prevention:**
1. **Normalize angles to [0, 2π):**
   ```c
   double normalized_angle = fmod(g.GateValue, 2 * M_PI);
   if (normalized_angle < 0) normalized_angle += 2 * M_PI;
   fprintf(oq_file, "p(%.17g) ", normalized_angle);
   ```
2. **Use appropriate format specifier:** `%.17g` for doubles (53-bit mantissa ≈ 15.9 decimal digits)
3. **Document angle precision:** Note in export comments that angles are IEEE double precision
4. **Verification tolerance:** When comparing phases in Qiskit verification, use `np.isclose(angle1, angle2, atol=1e-15)`
5. **Consider angle[n] declaration:** For production, declare `angle[32]` or `angle[64]` to match precision needs

**Detection (warning signs):**
- QFT verification fails with small phase errors accumulating
- Phase gates with π + ε export as negative angles
- Qiskit statevector has phase differences at 1e-16 level (floating-point noise)
- Hardware execution differs from simulation due to angle precision

**Which phase:** Phase 1 (Fix Export) normalizes angles; Phase 3 (Verification) tests precision limits

**Sources:**
- [OpenQASM 3 Types - Angle](https://openqasm.com/language/types.html) — "angle[n] for representing angles or phases"
- [OpenQASM 3 Spec - Fixed-Point Angles](https://arxiv.org/pdf/2104.14722) — Section on angle type rationale
- [Qiskit Phase Gate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.PhaseGate) — Takes angle parameter

---

### Pitfall 5: Verification False Positives (Deterministic vs Probabilistic Outcomes)

**What goes wrong:** Verification script runs Qiskit simulation and checks outcomes, but:
- Deterministic circuits (no superposition) should have single outcome with probability 1.0
- Probabilistic circuits (with H gates creating superposition) have multiple outcomes
- Shot noise causes small probability variations even for deterministic circuits
- Measurement ordering may differ between Quantum Assembly and Qiskit
- Comparing exact statevectors fails due to global phase differences

**Why it happens:**
- `StatevectorSimulator` gives exact amplitudes but global phase is arbitrary
- `QasmSimulator` with shots gives sampling noise (binomial distribution)
- Circuits with measurements mid-circuit have probabilistic trajectories
- Qiskit measurement results are dict `{'01': 502, '10': 498}` (little-endian bitstrings)
- No clear distinction in verification script between "expected deterministic" vs "expected probabilistic"

**Consequences:**
- Verification accepts wrong circuits because outcomes are "close enough"
- Deterministic circuits reported as probabilistic due to shot noise
- Measurement ordering bugs masked by probability tolerance
- False positive: circuit with bug passes verification if bug affects low-probability branch
- **Cannot distinguish between correct probabilistic behavior and incorrect computation**

**Prevention:**
1. **Separate deterministic and probabilistic test cases:**
   - Deterministic: Classical init, arithmetic without superposition → check single outcome
   - Probabilistic: Circuits with H gates → check probability distribution
2. **Use StatevectorSimulator for deterministic checks:**
   ```python
   sv = Statevector(circuit)
   # Check that all amplitudes except one are ~0
   probabilities = sv.probabilities_dict()
   assert len([p for p in probabilities.values() if p > 1e-10]) == 1
   ```
3. **Use shots only for probabilistic checks:**
   ```python
   counts = execute(circuit, QasmSimulator(), shots=10000).result().get_counts()
   # Chi-squared test against expected distribution
   ```
4. **Global phase invariance:** Compare `|⟨ψ₁|ψ₂⟩|² ≈ 1` instead of `ψ₁ == ψ₂`
5. **Measurement ordering test:** Export circuit `x q[0]; measure q[0] -> c[0];` and verify result is "1" not "01" or other interpretations

**Detection (warning signs):**
- Test passes with 95% probability but occasionally fails (shot noise)
- Deterministic circuit shows multiple measurement outcomes
- Statevector comparison fails despite correct circuit (global phase)
- Probability distribution has unexpected outcomes with >1% probability

**Which phase:** Phase 3 (Verification) implements robust statistical tests

**Sources:**
- [Qiskit Statevector Simulator](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.StatevectorSimulator.html) — Exact simulation
- [Software Testing in Quantum World (Jan 2026)](https://arxiv.org/html/2601.13996) — "shift from deterministic to probabilistic correctness"
- [Composable Verification via Magic-Blindness (Jan 2026)](https://arxiv.org/html/2601.07111v1) — Deterministic measurement outcomes for verification

---

### Pitfall 6: File Handle Leak and Resource Management

**What goes wrong:** Current `circuit_to_opanqasm` implementation:
- Opens FILE pointer: `FILE *oq_file = fopen(p, "w");` (line 277)
- Never calls `fclose(oq_file);`
- Function takes file path instead of returning string
- Cannot export to memory buffer for Python API

**Why it happens:**
- Original implementation designed for file-only export
- Missing cleanup in function (forgot fclose)
- No error handling if fopen fails
- Python API needs string return, not file writing

**Consequences:**
- File descriptor leak grows with repeated exports
- Eventually hits OS file descriptor limit (ulimit -n, typically 1024-4096)
- Python wrapper cannot provide `ql.to_openqasm()` returning string
- Cannot export circuit for testing without filesystem side effects
- **Process crash after ~1000 exports due to fd exhaustion**

**Prevention:**
1. **Always close file handles:**
   ```c
   FILE *oq_file = fopen(p, "w");
   if (oq_file == NULL) return -1; // Error handling
   // ... write content ...
   fclose(oq_file);
   return 0;
   ```
2. **Add string buffer export variant:**
   ```c
   char* circuit_to_openqasm_string(circuit_t *circ, size_t *out_length);
   // Allocates buffer, caller must free()
   ```
3. **Error handling:** Check fopen, fprintf, fclose return values
4. **Memory-only mode for testing:** Python API can use string variant without filesystem
5. **Resource cleanup tests:** Run 10,000 export iterations, monitor `lsof -p $PID | wc -l`

**Detection (warning signs):**
- `lsof -p $PID` shows growing number of open files
- Error after many exports: "Too many open files"
- Python test suite crashes after ~1000 test cases
- ulimit warnings in CI/CD logs

**Which phase:** Phase 1 (Fix Export) adds fclose and error handling; Phase 2 (Python API) adds string variant

**Sources:**
- Codebase: circuit_output.c line 277 — Missing fclose
- PROJECT.md requirements: "`ql.to_openqasm()` Python API returning QASM string (in-memory, no file I/O)"

---

## Moderate Pitfalls

These mistakes cause delays or technical debt but are fixable without rewrites.

### Pitfall 7: OpenQASM 3 Feature Compatibility Limits

**What goes wrong:** Not all OpenQASM 3 features work everywhere:
- Control flow (if, for, while) not supported on IBM hardware
- Nested control flow not eligible for hardware execution
- Classical register aliasing strongly discouraged (execution fails)
- Variable declarations not parsed by qiskit-qasm3-import v0.6.0
- Duration and stretch types have limited hardware support

**Why it happens:**
- OpenQASM 3 language is evolving faster than hardware capabilities
- Qiskit transpiler may not support all language features
- Different backends (simulator, hardware, cloud) have different subsets
- No official "OpenQASM 3 Hardware Profile" specification yet

**Consequences:**
- Exported QASM file valid but cannot run on hardware
- Qiskit import succeeds but transpilation fails
- Different simulators accept different feature subsets
- Verification works locally but fails on cloud backends

**Prevention:**
1. **Stick to "universal gate set" subset:** Only use gates from stdgates.inc, no custom gates
2. **Avoid control flow in export:** Classical conditionals can be compiled to gate sequences before export
3. **Feature detection:** Document which features are used in export comments
4. **Test on multiple backends:** Verify export on StatevectorSimulator, QasmSimulator, and real backend
5. **Version compatibility matrix:** Track which Qiskit versions support which OpenQASM features

**Detection (warning signs):**
- Transpilation error: "control flow not supported"
- Backend raises "feature not implemented"
- Same QASM works on simulator but fails on hardware

**Which phase:** Phase 2 (Qiskit Integration) tests on multiple backends

**Sources:**
- [OpenQASM 3 Feature Table](https://quantum.cloud.ibm.com/docs/en/guides/qasm-feature-table) — Hardware compatibility
- [Qiskit GitHub Issue #10737](https://github.com/Qiskit/qiskit/issues/10737) — Header file management challenges

---

### Pitfall 8: Classical Register and Measurement Export

**What goes wrong:** M gate exports but:
- No classical register declared in current export
- OpenQASM requires `bit[n] c;` before any measurements
- Measurement syntax is `measure q[i] -> c[i];` not `m q[i];`
- Cannot verify measurement outcomes without classical register mapping

**Why it happens:**
- Current circuit_t structure may not track classical registers
- Export function assumes all gates are unitary (no measurements)
- OpenQASM 3 requires explicit classical bit allocation
- Measurement maps qubit → classical bit (may be different indices)

**Consequences:**
- Exported QASM with measurements is syntactically invalid
- Qiskit import fails: "measure requires classical target"
- Cannot verify circuits that use measurement
- Mid-circuit measurement not supported

**Prevention:**
1. **Add classical register to export:**
   ```c
   // Count M gates to determine classical register size
   int num_measurements = count_gates_by_type(circ, M);
   if (num_measurements > 0) {
       fprintf(oq_file, "bit[%d] c;\n\n", num_measurements);
   }
   ```
2. **Fix measurement syntax:**
   ```c
   case M:
       fprintf(oq_file, "measure q[%d] -> c[%d];\n", g.Target, measurement_index++);
       break;
   ```
3. **Track classical bit allocation:** Map each measurement to classical bit index
4. **Verify measurement results:** In verification script, extract classical register values

**Detection (warning signs):**
- OpenQASM parser error: "classical target required"
- Exported circuit with M gates fails to import
- No classical output in Qiskit results

**Which phase:** Phase 1 (Fix Export) implements classical register support

**Sources:**
- [OpenQASM 3 Measurement Syntax](https://openqasm.com/language/insts.html) — `measure q -> c;`

---

### Pitfall 9: Memory/Performance for Large Circuit Export

**What goes wrong:** Large circuits (>10,000 gates) may:
- Exhaust fprintf buffer causing incomplete export
- Take excessive time to export (O(n²) string concatenation)
- Produce QASM files too large for Qiskit import (>100 MB)
- Cause memory issues in string buffer variant

**Why it happens:**
- Current export uses fprintf per gate (many syscalls)
- String concatenation in Python grows quadratically without pre-allocation
- Qiskit QASM parser loads entire file into memory
- No progress reporting for long exports

**Consequences:**
- Export hangs for large circuits
- Python process OOM killed during export
- Generated QASM file truncated (invalid syntax at end)
- Qiskit import times out or crashes

**Prevention:**
1. **Pre-allocate string buffer:**
   ```c
   size_t estimated_size = circ->used * 80; // ~80 chars per gate
   char *buffer = malloc(estimated_size);
   size_t offset = 0;
   offset += sprintf(buffer + offset, "OPENQASM 3.0;\n");
   // ... accumulate in buffer ...
   ```
2. **Batch write to file:** Use setvbuf for larger buffer
3. **Benchmark export performance:** Test with 1k, 10k, 100k, 1M gate circuits
4. **Streaming export:** Write gate-by-gate instead of accumulating
5. **Size limits:** Document maximum supported circuit size (e.g., 1M gates)

**Detection (warning signs):**
- Export time grows superlinearly with circuit size
- Memory usage spikes during export
- Exported file is truncated
- Python RSS exceeds 1GB for moderate circuit

**Which phase:** Phase 2 (Python API) optimizes string handling; Phase 3 (Verification) tests scaling

**Sources:**
- [Qiskit Memory Usage Issue #6991](https://github.com/Qiskit/qiskit/issues/6991) — "Memory usage grows quickly with circuit depth"
- [Qiskit Issue #5895](https://github.com/Qiskit/qiskit/issues/5895) — Transpiling long circuits requires large memory

---

### Pitfall 10: Function Naming and API Design

**What goes wrong:** Current function name is `circuit_to_opanqasm` (missing 'e' in "openqasm"):
- Typo in function name → hard to discover in documentation
- Takes file path parameter instead of returning string
- No error return code (void function)
- Python wrapper will expose the typo to users

**Why it happens:**
- Copy-paste error in original implementation
- Function designed before Python API requirements defined
- No code review or spell-check process

**Consequences:**
- User confusion: "Why is it 'opanqasm' not 'openqasm'?"
- Cannot detect export failures (no return value)
- Python API inherits awkward naming
- Breaking change required to fix typo later

**Prevention:**
1. **Rename function:** `circuit_to_openqasm` (fix typo)
2. **Add return value:**
   ```c
   int circuit_to_openqasm(circuit_t *circ, const char *path);
   // Returns 0 on success, -1 on error
   ```
3. **Add string variant:**
   ```c
   char* circuit_to_openqasm_string(circuit_t *circ);
   // Returns allocated string, caller must free()
   ```
4. **Python API design:**
   ```python
   def to_openqasm(self) -> str:
       """Export circuit as OpenQASM 3.0 string."""
   ```
5. **Deprecation path:** If typo shipped, add deprecation warning for old name

**Detection (warning signs):**
- User reports: "function name has typo"
- Linter/IDE autocomplete suggests wrong spelling
- Documentation inconsistent (some places "openqasm", some "opanqasm")

**Which phase:** Phase 1 (Fix Export) renames function; Phase 2 (Python API) designs clean interface

**Sources:**
- Codebase: circuit_output.c line 274 — Typo in function name
- PROJECT.md: "`ql.to_openqasm()` Python API" — Correct spelling

---

## Minor Pitfalls

These cause annoyance but are easily fixable.

### Pitfall 11: Missing Include Guard in Export

**What goes wrong:** If OpenQASM file re-exports or concatenates circuits, duplicate includes cause warnings:
```
include "stdgates.inc";
include "stdgates.inc";  // Duplicate
```

**Prevention:**
- OpenQASM 3 doesn't require include guards (single-file model)
- Just include once at top of file
- If concatenating exports, strip duplicate includes

**Detection:** OpenQASM parser warnings (non-fatal)

---

### Pitfall 12: Comment and Metadata Loss

**What goes wrong:** Export loses circuit metadata:
- No comment showing source (Quantum Assembly framework)
- No timestamp or version info
- No gate count or depth statistics
- Hard to trace exported file back to source

**Prevention:**
```c
fprintf(oq_file,
    "// Generated by Quantum Assembly v%s\n"
    "// Date: %s\n"
    "// Gates: %zu, Layers: %u, Qubits: %d\n",
    VERSION, timestamp, circ->used, circ->used_layer, circ->used_qubits + 1);
```

**Detection:** User confusion about file origin

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Fix C Export | Qubit ordering mismatch, missing gates, typo | Systematic test for each gate type, qubit index validation |
| Python API | Memory leak in string return, GIL issues | Use PyMem_Malloc, release GIL during export |
| Qiskit Integration | Import fails on multi-controlled gates | Test ctrl @ syntax, validate with qiskit.qasm3.load() |
| Verification Script | False positives from shot noise | Separate deterministic/probabilistic test suites |
| Classical Init Verification | Endianness causes wrong bit patterns | Document index mapping, use from_label() |
| Phase Precision | Angle normalization, precision loss | Normalize to [0, 2π), use %.17g format |
| Large Circuit Export | Memory/performance bottleneck | Pre-allocate buffer, benchmark scaling |

---

## Testing Strategy

### Unit Tests (Phase 1)
- Export each gate type individually, verify syntax
- Multi-controlled gates with n=0,1,2,3,10 controls
- Qubit ordering: export qint(5, width=4), check indices
- Classical measurement: export M gate, check syntax
- Phase angles: test 0, π/4, π, 2π, -π/4, 3π
- Large circuits: 10k, 100k gates (performance)

### Integration Tests (Phase 2-3)
- Round-trip: export → Qiskit import → compare circuits
- Statevector verification: export classical init → simulate → check state
- Measurement verification: deterministic vs probabilistic
- Endianness: compare Quantum Assembly and Qiskit measurement results
- Multi-backend: test on StatevectorSimulator, QasmSimulator
- Precision: QFT circuit with known phase pattern

### Regression Tests
- Y/Rx/Ry/Rz gates export correctly (current bugs)
- large_control array used for >2 controls (current bug)
- File handle closed properly (current bug)
- Function name spelled correctly

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Qubit Ordering | HIGH | Official Qiskit docs explicit about little-endian |
| Multi-Controlled Gates | HIGH | OpenQASM 3 spec defines ctrl @ syntax |
| Gate Naming | HIGH | Standard library documented, current code has obvious bugs |
| Phase Precision | MEDIUM | Angle type new in OpenQASM 3, implementation varies |
| Verification Strategy | MEDIUM | Recent research (Jan 2026) but rapidly evolving |
| File I/O | HIGH | C standard library behavior well-known |
| Memory/Performance | MEDIUM | Depends on circuit size, needs empirical testing |
| Qiskit API Changes | MEDIUM | Qiskit 1.0+ stable but deprecations ongoing |

---

## Open Questions

1. **Angle precision:** Should export use `angle[32]` or `angle[64]` declaration? Does Qiskit qasm3 importer support angle types?
2. **Reset gate semantics:** Is internal `R` gate equivalent to OpenQASM `reset`? Needs clarification.
3. **Measurement mid-circuit:** Does circuit_t support mid-circuit measurements? Or only terminal measurements?
4. **Global phase tracking:** Should verification account for global phase, or is phase-invariant comparison sufficient?
5. **Hardware testing:** Can verification script test on real IBM quantum hardware, or simulator-only?

---

## Sources

### Official Documentation (HIGH confidence)
- [OpenQASM 3 Language Spec - Gates](https://openqasm.com/language/gates.html)
- [OpenQASM 3 Standard Library](https://openqasm.com/language/standard_library.html)
- [OpenQASM 3 Built-in Instructions](https://openqasm.com/language/insts.html)
- [OpenQASM 3 Types](https://openqasm.com/language/types.html)
- [Qiskit Bit Ordering Guide](https://quantum.cloud.ibm.com/docs/guides/bit-ordering)
- [Qiskit MCXGate API](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.MCXGate)
- [OpenQASM 3 Feature Table](https://quantum.cloud.ibm.com/docs/en/guides/qasm-feature-table)

### Research Papers (2025-2026)
- [Software Testing in the Quantum World (Jan 2026)](https://arxiv.org/html/2601.13996)
- [Composable Verification via Magic-Blindness (Jan 2026)](https://arxiv.org/html/2601.07111v1)
- [Estimating Shots and Variance on Noisy Quantum Circuits (Jan 2026)](https://arxiv.org/html/2501.03194)
- [OpenQASM 3: A Broader and Deeper Quantum Assembly Language (2021)](https://arxiv.org/pdf/2104.14722)

### Qiskit Issues and Release Notes
- [Qiskit 1.0 Release Notes](https://docs.quantum.ibm.com/api/qiskit/release-notes/1.0)
- [Qiskit 2.1 Release Summary](https://www.ibm.com/quantum/blog/qiskit-2-1-release-summary)
- [Qiskit Memory Usage Issue #6991](https://github.com/Qiskit/qiskit/issues/6991)
- [Qiskit Issue #5895 - Long Circuit Memory](https://github.com/Qiskit/qiskit/issues/5895)
- [MCMT Deprecation Notice](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.library.MCMT)

### Codebase Analysis
- `c_backend/src/circuit_output.c` — Current OpenQASM export implementation
- `.planning/PROJECT.md` — Requirements and architecture
- Gate enum definition (X, Y, Z, H, P, M, R, Rx, Ry, Rz)
- Right-aligned qubit layout documentation
