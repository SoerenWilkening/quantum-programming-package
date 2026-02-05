# Phase 17: C Reverse Gate Generation - Research

**Researched:** 2026-01-28
**Domain:** Quantum gate adjoint generation and circuit uncomputation in C
**Confidence:** HIGH

## Summary

This phase builds on the existing `run_instruction` function which already implements gate reversal via the `invert` parameter (line 47 in execution.c: `g->GateValue *= pow(-1, invert)`). The current implementation reverses gate order (LIFO) and negates phase gates' GateValue field.

The research confirms that the existing infrastructure handles most gate types correctly through mathematical inversion. Self-adjoint gates (X, Y, Z, H) are their own inverses (GateValue stays constant under negation), while phase gates (P, controlled-P) automatically invert correctly (negating the angle produces the adjoint). Multi-controlled gates preserve their control structure during reversal.

**Primary recommendation:** Extend the existing execution.c infrastructure to support instruction range reversal, document gate inversion guarantees, and add debug-mode validation.

## Standard Stack

The project uses its own C quantum circuit backend (no external quantum libraries). Key infrastructure already exists.

### Core (Existing)
| Component | Location | Purpose | Current State |
|-----------|----------|---------|---------------|
| `run_instruction` | Execution/src/execution.c | Gate execution with invert parameter | Already implements LIFO reversal and phase negation |
| `gate_t` structure | Backend/include/types.h | Gate representation with GateValue field | Supports all required gate types |
| `add_gate` | Backend/src/optimizer.c | Appends gates to circuit | In-place append, no modification needed |
| `gates_are_inverse` | Backend/src/gate.c | Checks if two gates are inverses | Already validates P gate angle negation |

### Supporting
| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| `assert.h` | C standard library | Debug-mode validation | Parameter validation, range checks |
| `pow(-1, invert)` | execution.c:47 | Phase gate angle inversion | Already used for GateValue negation |
| `large_control` array | gate_t struct | n-controlled gates (n>2) | Already handled in run_instruction |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-place append | Separate adjoint circuit | Current approach is simpler, matches existing circuit compilation model |
| Generic angle negation | Explicit Tdg/Sdg gate types | Generic approach works for all phase gates, no special cases needed |

**Installation:**
No external dependencies. Uses existing C codebase infrastructure.

## Architecture Patterns

### Recommended Project Structure
```
Execution/
├── src/
│   └── execution.c       # run_instruction() - main entry point
├── include/
│   └── execution.h       # Public API declaration

Backend/
├── src/
│   ├── gate.c            # gates_are_inverse() helper
│   └── optimizer.c       # add_gate() for appending
└── include/
    ├── types.h           # gate_t, Standardgate_t enum
    └── circuit.h         # circuit_t structure
```

### Pattern 1: Instruction Range Reversal (LIFO)
**What:** Reverse a range of instructions from a circuit by iterating backwards through layers and gates
**When to use:** When Python layer provides start/end instruction indices for uncomputation
**Example:**
```c
// Source: Existing codebase (Execution/src/execution.c)
void run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert, circuit_t *circ) {
    if (res == NULL)
        return;
    int direction = (invert) ? -1 : 1;

    // When invert=1, iterates backwards: layer_index goes 0→n, but actual layer is reversed
    for (int layer_index = 0; layer_index < res->used_layer; ++layer_index) {
        layer_t layer = invert * res->used_layer + direction * layer_index - invert;
        for (int gate_index = 0; gate_index < res->gates_per_layer[layer]; ++gate_index) {
            layer_t gate = invert * res->gates_per_layer[layer] + direction * gate_index - invert;
            gate_t *g = malloc(sizeof(gate_t));
            memcpy(g, &res->seq[layer][gate], sizeof(gate_t));
            // ... qubit mapping ...
            g->GateValue *= pow(-1, invert);  // Phase gate inversion
            add_gate(circ, g);
        }
    }
}
```

### Pattern 2: Gate-Type-Specific Inversion
**What:** Different gate types invert differently - phase gates negate angle, self-adjoint gates are unchanged
**When to use:** All gate reversal operations
**Example:**
```c
// Source: Quantum computing theory + existing codebase patterns
// Self-adjoint gates (X, Y, Z, H):
// GateValue *= pow(-1, invert) has no effect (GateValue is 0 or 1)
// Result: X† = X, H† = H, CX† = CX

// Phase gates (P):
// GateValue *= pow(-1, invert) negates the angle
// Result: P(θ)† = P(-θ), CP(θ)† = CP(-θ)

// Special phase gates (derived from GateValue patterns):
// T gate: P(π/4) → T† is P(-π/4)
// S gate: P(π/2) → S† is P(-π/2)
```

### Pattern 3: Control Structure Preservation
**What:** Multi-controlled gates maintain their control qubits during inversion
**When to use:** Reversing controlled operations (CX, CCX, n-controlled gates)
**Example:**
```c
// Source: Existing codebase (Execution/src/execution.c:30-46)
// Control qubits are preserved during reversal
if (g->NumControls > 2 && res->seq[layer][gate].large_control != NULL) {
    // Allocate new large_control array for mapped qubits
    g->large_control = malloc(g->NumControls * sizeof(qubit_t));
    for (int i = 0; i < (int)g->NumControls; ++i) {
        g->large_control[i] = qubit_array[res->seq[layer][gate].large_control[i]];
    }
    // Control structure unchanged, only qubit mapping applied
}
// Result: CCX(c1,c2,t)† = CCX(c1,c2,t) with same controls
```

### Pattern 4: Hybrid Python-C Interface
**What:** Python stores instruction indices, calls C with those indices to reverse gates
**When to use:** Uncomputation triggered from Python qbool lifetime management
**Example:**
```python
# Source: Context decisions (17-CONTEXT.md)
# Python layer (conceptual, to be implemented in Phase 18):
class qbool:
    def __init__(self):
        self.start_instruction = get_current_instruction_count()
        self.end_instruction = None

    def finalize(self):
        self.end_instruction = get_current_instruction_count()

    def uncompute(self):
        # Call C to reverse instructions [start_instruction, end_instruction)
        reverse_instruction_range(self.start_instruction, self.end_instruction)
```

### Anti-Patterns to Avoid
- **Separate gate type handling:** Don't create separate code paths for T/S gates vs generic P gates - the generic angle negation handles all phase gates uniformly
- **Explicit Tdg/Sdg types:** Don't add new gate types to the enum - use the existing P gate with negated angle
- **Bidirectional iteration:** Don't use separate forward/backward loop logic - the existing `direction` variable elegantly handles both cases
- **Ownership validation in C:** Don't verify qubit ownership or dependency order in C - Python layer is responsible, C trusts provided indices

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate inversion logic | Manual switch statements per gate type | Existing `pow(-1, invert)` pattern | Already handles self-adjoint (no change) and phase gates (negate angle) uniformly |
| LIFO reversal | New backward iteration code | Existing `direction` variable pattern | Lines 17-24 of execution.c elegantly handle both directions |
| Inverse validation | Custom gate comparison logic | Existing `gates_are_inverse()` function | Already implemented in gate.c:438-456, validates phase angles correctly |
| Multi-control handling | Special case code for n-controlled gates | Existing `large_control` infrastructure | Phase 12/13 already solved this, execution.c:30-46 |
| Circuit appending | Custom gate insertion | Existing `add_gate()` function | Optimizer handles layer assignment, merging, collision detection |

**Key insight:** The existing codebase already solves ~80% of this phase. The main work is exposing instruction range reversal to Python, not reimplementing gate inversion.

## Common Pitfalls

### Pitfall 1: Assuming T/S Need Special Handling
**What goes wrong:** Developer adds explicit Tdg/Sdg gate types to the Standardgate_t enum
**Why it happens:** Quantum frameworks like Qiskit have separate T/Tdg gate types, suggests special handling is needed
**How to avoid:** Recognize that T and S are just P gates with specific angles (π/4 and π/2). The generic P gate inversion via angle negation handles them automatically.
**Warning signs:** New enum values, switch statement cases for Tdg/Sdg, duplicate code paths

### Pitfall 2: Validating Instruction Ranges in C
**What goes wrong:** Adding asserts like `assert(start < end)` or `assert(start < circuit->used)`
**Why it happens:** Defensive programming instinct to validate inputs
**How to avoid:** Follow the agreed boundary - Python layer owns correctness, C layer trusts provided indices. Only add asserts in debug builds for truly impossible conditions (NULL pointers).
**Warning signs:** Asserts on range bounds, ownership checks, entanglement validation

### Pitfall 3: Self-Adjoint Gate Recognition
**What goes wrong:** Adding explicit checks like `if (gate == X || gate == H) return gate;` before inversion
**Why it happens:** Optimization attempt - skip inversion for self-adjoint gates
**How to avoid:** The existing `GateValue *= pow(-1, invert)` already handles this correctly - for X/H/CX, GateValue doesn't represent phase, so negation has no semantic effect. The gate appends correctly either way.
**Warning signs:** Gate type switch statements, "skip inversion" comments, premature optimization

### Pitfall 4: Memory Management for large_control
**What goes wrong:** Forgetting to allocate new `large_control` array when copying gates during reversal
**Why it happens:** The static `Control[2]` array doesn't need allocation, easy to forget dynamic array does
**How to avoid:** Follow the existing pattern in execution.c:30-40 - always check `NumControls > 2` and allocate accordingly. The infrastructure is already correct.
**Warning signs:** Segfaults on n-controlled gates (n>2), valgrind errors, shallow copy bugs

### Pitfall 5: Instruction Index Semantics
**What goes wrong:** Confusion about whether indices are inclusive/exclusive, circuit-relative vs sequence-relative
**Why it happens:** Multiple representations (circuit has layers, sequence has used_layer, Python has instruction count)
**How to avoid:** Document clearly: Python instruction indices map to sequence boundaries. Use [start, end) half-open intervals (start inclusive, end exclusive) - standard for ranges.
**Warning signs:** Off-by-one errors, reversing wrong instructions, empty ranges not handled

## Code Examples

Verified patterns from existing codebase:

### Reversing a Sequence (Current Implementation)
```c
// Source: Execution/src/execution.c:13-52
void run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert, circuit_t *circ) {
    if (res == NULL)
        return;
    int direction = (invert) ? -1 : 1;

    for (int layer_index = 0; layer_index < res->used_layer; ++layer_index) {
        layer_t layer = invert * res->used_layer + direction * layer_index - invert;
        for (int gate_index = 0; gate_index < res->gates_per_layer[layer]; ++gate_index) {
            layer_t gate = invert * res->gates_per_layer[layer] + direction * gate_index - invert;
            gate_t *g = malloc(sizeof(gate_t));
            memcpy(g, &res->seq[layer][gate], sizeof(gate_t));
            g->Target = qubit_array[g->Target];

            // Handle n-controlled gates
            if (g->NumControls > 2 && res->seq[layer][gate].large_control != NULL) {
                g->large_control = malloc(g->NumControls * sizeof(qubit_t));
                if (g->large_control != NULL) {
                    for (int i = 0; i < (int)g->NumControls; ++i) {
                        g->large_control[i] = qubit_array[res->seq[layer][gate].large_control[i]];
                    }
                    g->Control[0] = g->large_control[0];
                    g->Control[1] = g->large_control[1];
                }
            } else {
                for (int i = 0; i < (int)g->NumControls && i < MAXCONTROLS; ++i) {
                    g->Control[i] = qubit_array[g->Control[i]];
                }
            }
            g->GateValue *= pow(-1, invert);  // Phase gate inversion
            add_gate(circ, g);
        }
    }
}
```

### Validating Gate Inversion (Existing Helper)
```c
// Source: Backend/src/gate.c:438-457
bool gates_are_inverse(gate_t *G1, gate_t *G2) {
    if (G2 == NULL)
        return false;
    if (G1->Target != G2->Target)
        return false;
    if (G1->NumControls != G2->NumControls)
        return false;
    if (G1->Gate != G2->Gate)
        return false;
    // Special handling for phase gates - angles must be negated
    if (G1->Gate == P) {
        if (G1->GateValue != -G2->GateValue)
            return false;
    } else if (G1->GateValue != G2->GateValue)
        return false;
    // Verify all control qubits match
    for (int i = 0; i < G1->NumControls; ++i)
        if (G1->Control[i] != G2->Control[i])
            return false;

    return true;
}
```

### QFT Inverse Example (Existing Pattern)
```c
// Source: Backend/src/gate.c:372-436
// This shows the manual LIFO pattern - reverse order, negate phase angles
sequence_t *QFT_inverse(sequence_t *qft, int num_qubits) {
    int offset = 0;
    // ... allocation code omitted ...

    // Notice: reverse order (j counts forward, but layer calculation reverses)
    for (int j = 0; j < num_qubits; ++j) {
        // Apply controlled-P gates first (reversed from QFT)
        for (int i = 0; i < num_qubits - 1 - j; ++i) {
            num_t layer = qft->used_layer + 2 * num_qubits - 1 - (2 * j + i + 1) - 1;
            // Note the negated angle: -M_PI instead of M_PI
            cp(&qft->seq[layer][qft->gates_per_layer[layer]++],
               offset + j, offset + (j + i + 1),
               -M_PI / pow(2, i + 1));  // Negative angle for inverse
        }
        // Apply Hadamard last (reversed from QFT)
        num_t layer = qft->used_layer + 2 * num_qubits - 1 - 2 * j - 1;
        h(&qft->seq[layer][qft->gates_per_layer[layer]++], offset + j);
    }
    qft->used_layer += 2 * num_qubits - 1;
    return qft;
}
```

### Debug-Mode Assertion Pattern
```c
// Source: C best practices (assert.h documentation)
// Example for new reverse_instruction_range function:
#include <assert.h>

void reverse_instruction_range(circuit_t *circ, int start, int end) {
    // Debug-mode validation only
    assert(circ != NULL);
    assert(start >= 0);
    assert(end >= start);  // Empty range (start==end) is valid

    // Release mode: trust Python layer, no validation
    if (start == end) return;  // No-op for empty range

    // ... reversal logic ...
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual QFT_inverse | Generic run_instruction(invert=1) | Phase 11 (stateless C backend) | Uniform inversion mechanism for all sequences |
| Separate Tdg/Sdg gate types | P gate with negated angle | Original design | Simpler gate enum, no special cases |
| Global QPU state | Explicit sequence_t* parameters | Phase 11 | Enables Python-level dependency tracking |
| Forward-only circuits | Bidirectional run_instruction | Phase 11 | Foundation for uncomputation |

**Deprecated/outdated:**
- **Explicit inverse gate types:** Quantum frameworks (Qiskit, Cirq) often define separate T/Tdg, S/Sdg types. This codebase correctly uses parametric P gates, simpler and more general.
- **Circuit-level instruction tracking:** Some designs track instruction indices in C. This codebase delegates to Python layer (v1.2 design), cleaner boundary.

## Open Questions

Things that couldn't be fully resolved:

1. **Instruction Index Representation**
   - What we know: Python needs to track instruction ranges, C needs to reverse those ranges
   - What's unclear: Exact mapping between Python "instruction count" and C's layer/gate structure
   - Recommendation: Use sequence_t boundaries as natural instruction delimiters. Each qbool operation appends one sequence_t to circuit. Track sequence_t indices, not individual gate indices.

2. **Empty Range Handling**
   - What we know: start==end should be no-op (17-CONTEXT.md decision)
   - What's unclear: Should this be silent or log in verbose mode?
   - Recommendation: Silent no-op in release, optional debug log if verbose flag exists

3. **Already-Uncomputed State Tracking**
   - What we know: Context document marks this as Claude's discretion
   - What's unclear: Should C track "this range was already reversed" or is Python responsible?
   - Recommendation: Python layer tracks uncomputed state. C is stateless, accepts any valid range, reverses it. Python ensures no double-uncomputation.

4. **Measurement Gate Reversal**
   - What we know: M (measurement) is in the Standardgate_t enum, but measurements are irreversible
   - What's unclear: Should reverse_instruction_range error on M gates, or trust Python to never reverse measured qubits?
   - Recommendation: Trust Python layer initially. If bugs arise, add debug assert to detect M gates during reversal. M gates shouldn't appear in uncomputation ranges by design.

## Sources

### Primary (HIGH confidence)
- Existing codebase:
  - `/Users/.../Execution/src/execution.c` - run_instruction() implementation, lines 13-52
  - `/Users/.../Backend/src/gate.c` - gates_are_inverse() helper, lines 438-457
  - `/Users/.../Backend/src/gate.c` - QFT_inverse() manual pattern, lines 372-436
  - `/Users/.../Backend/include/types.h` - gate_t structure, Standardgate_t enum
- Phase 17 context: `.planning/phases/17-reverse-gate-generation/17-CONTEXT.md` - locked decisions on API surface, gate ordering, error handling
- Phase 16 foundation: `.planning/phases/16-dependency-tracking/16-01-PLAN.md` - dependency tracking infrastructure that phase 17 builds upon

### Secondary (MEDIUM confidence)
- [List of quantum logic gates - Wikipedia](https://en.wikipedia.org/wiki/List_of_quantum_logic_gates) - Adjoint gate definitions (S†, T†)
- [Quantum logic gate - Wikipedia](https://en.wikipedia.org/wiki/Quantum_logic_gate) - Self-adjoint property of Pauli and Hadamard gates
- [Microsoft Learn: assert Macro](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/assert-macro-assert-wassert) - C assert patterns for debug-mode validation
- [cppreference.com: assert](https://en.cppreference.com/w/cpp/error/assert.html) - NDEBUG and release build behavior

### Tertiary (LOW confidence - background only)
- [Modular Synthesis of Efficient Quantum Uncomputation](https://arxiv.org/pdf/2406.14227) - Research on adjoint synthesis (2024), not directly applicable to C implementation but confirms LIFO approach
- [inv - Inverse of quantum circuit - MATLAB](https://www.mathworks.com/help/matlab/ref/quantumcircuit.inv.html) - MATLAB's approach to circuit inversion, reverses gate order and replaces each gate with inverse
- [T Gate - Quantum Inspire](https://www.quantum-inspire.com/kbase/t-gate/) - T gate as π/4 phase shift, confirms T† is -π/4

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Existing codebase provides all infrastructure, verified by reading source files
- Architecture: HIGH - Existing patterns (run_instruction, gate inversion) are proven and correct
- Pitfalls: HIGH - Derived from examining existing code and user decisions in CONTEXT.md
- API design: HIGH - Hybrid Python-C approach is locked decision in CONTEXT.md
- Instruction index mapping: MEDIUM - Needs implementation details from Phase 18 integration

**Research date:** 2026-01-28
**Valid until:** 2026-02-28 (30 days - stable domain, C language and quantum computing fundamentals don't change rapidly)
