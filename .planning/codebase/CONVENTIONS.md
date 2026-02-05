# Coding Conventions

**Analysis Date:** 2026-01-25

## Naming Patterns

**Files:**
- C source files: `snake_case.c` (e.g., `gate.c`, `IntegerAddition.c`, `circuit_allocations.c`)
- C header files: `PascalCase.h` (e.g., `QPU.h`, `Integer.h`, `IntegerComparison.h`)
- Python files: `snake_case.py` (e.g., `test.py`)
- Cython extension files: `snake_case.pyx` (e.g., `quantum_language.pyx`)

**Functions:**
- C functions use lowercase with underscores: `print_sequence()`, `allocate_more_qubits()`, `qubit_mapping()`
- Quantum gate functions use single lowercase letters: `x()`, `y()`, `z()`, `h()`, `p()`, `cx()`, `cy()`, `cz()`, `cp()`, `ccx()`
- Initialization functions: `init_circuit()`, `QINT()`, `QBOOL()`, `QINT()` (some uppercase for quantum operations)
- Struct/type construction functions use ALL_CAPS: `QINT()`, `QBOOL()`, `INT()`, `BOOL()`

**Variables:**
- Local variables and parameters use `snake_case`: `qubit_array`, `layer_index`, `gate_index`, `num_qubits`, `num_layers`
- Global variables use `snake_case` with external declaration: `instruction_list`, `instruction_counter`, `QPU_state`, `circuit`
- Type abbreviations in variable names: `seq` for `sequence_t`, `g` for `gate_t`, `circ` for `circuit_t`
- Loop counters use single letters: `i`, `j`, `k`, `layer`, `gate`

**Types:**
- Struct types use `PascalCase_t` suffix: `gate_t`, `sequence_t`, `circuit_t`, `quantum_int_t`, `instruction_t`, `Standardgate_t`
- Typedef enums use `PascalCase_t` suffix: `Standardgate_t` with enum values in ALL_CAPS
- Custom integer types use suffixes: `qubit_t`, `layer_t`, `num_t`
- Gate enum values: `X`, `Y`, `Z`, `H`, `P`, `Rx`, `Ry`, `Rz`, `M`, `R` (all caps)

**Constants and Macros:**
- Macros use ALL_CAPS with underscores: `INTEGERSIZE`, `MAXLAYERINSEQUENCE`, `MAXGATESPERLAYER`, `MAXCONTROLS`, `MAXQUBITS`, `MAXINSTRUCTIONS`
- Define constants use ALL_CAPS: `QUBIT_BLOCK`, `LAYER_BLOCK`, `GATES_PER_LAYER_BLOCK`
- Configuration flags: `POINTER`, `VALUE`, `Qu`, `Cl`, `INVERTED`, `NOTINVERTED`, `DECOMPOSETOFFOLI`, `DONTDECOMPOSETOFFOLI`

## Code Style

**Formatting:**
- No automated formatter configured (no `.prettierrc`, `clang-format`, or similar)
- Indentation: Appears to use tabs in some files, spaces (4-space) in others
- Brace style: C style with opening brace on same line: `if (condition) {`
- Line length: No strict limit observed; some lines exceed 100 characters

**Linting:**
- No linter configuration file detected (no `.eslintrc`, `.flake8`, `.pylintrc`)
- Build uses CMake with C23 standard and `-O3` optimization flag

**Spacing:**
- Space after control keywords: `if (`, `for (`, `while (`
- Space around operators: `x = 1`, `i < limit`
- No space between function name and parentheses in definitions: `void print_sequence(sequence_t *seq) {`

## Import Organization

**C Header Includes:**
Order observed in `gate.c` (standard pattern):
1. Standard library headers: `#include <stdlib.h>`, `#include <stdio.h>`, `#include <string.h>`, `#include <math.h>`
2. Project headers: `#include "definition.h"`, `#include "gate.h"`

**Python Imports:**
Order observed in `test.py`:
1. Standard library imports first
2. Third-party imports (e.g., `import quantum_language as ql`)
3. Import aliases used where appropriate

## Error Handling

**Patterns:**
- Null pointer checks: `if (seq == NULL) return;` or `if (g == NULL) return false;`
- Early returns for error conditions: Return NULL or false for failure, data/true for success
- Memory allocation: Malloc used extensively with no null checks in most cases (potential concern)
- Example: `if (res == NULL) return;` in `execution.c:31`
- Example: `if (QPU_state->Q0 != NULL) { ... }` in `execution.c:9` - conditional checks for optional quantum registers

**No exceptions:** C code uses return values and status checks; no exception handling mechanism

## Logging

**Framework:** `printf()` - C standard library

**Patterns:**
- Debug output: `printf("cycles = %d\n", seq->used_layer);` in `gate.c:42`
- Formatted output for debugging: `printf("gates = %d\n", count);` in `gate.c:43`
- Verbose circuit printing: `print_sequence()` and `print_gate()` functions provide detailed visualization
- Some printf calls are commented out for debugging: `//#include <stdio.h>` lines suggest removed debug output
- Printf statements remain in production code (not systematized)

## Comments

**When to Comment:**
- File headers: Every file starts with creation date and author: `// Created by Sören Wilkening on 27.10.24.`
- Complex quantum algorithms: Comments explain gate sequences like "determine the number of gates per layer for the qft"
- Magic numbers: Constants like `INTEGERSIZE - num_qubits` and layer calculations get comments
- Inline comments for non-obvious logic: E.g., `// do the hadamards`, `// for the controls`

**JSDoc/TSDoc:**
- Not used in C code (no Doxygen-style comments detected)
- Function declarations in headers lack documentation comments

## Function Design

**Size:** Functions are moderately sized, ranging from 10-50 lines typically
- Example small: `void y(gate_t *g, qubit_t target)` - 5 lines
- Example medium: `void print_sequence(sequence_t *seq)` - 65 lines
- Example large: `sequence_t *QFT(sequence_t *qft, int num_qubits)` - 36 lines

**Parameters:**
- Pointers are explicit: Most operations on structs use pointers `gate_t *g`, `sequence_t *seq`
- Multiple return values via pointer parameters: E.g., gates modified in place
- Limited use of varargs; most functions have fixed signatures
- Quantum operations often take target and control parameters: `cx(gate_t *g, qubit_t target, qubit_t control)`

**Return Values:**
- Pointers for allocated structures: `quantum_int_t *QINT()` returns newly allocated memory
- Boolean flags: `bool gates_are_inverse(gate_t *G1, gate_t *G2)` returns true/false
- Void for in-place modifications: `void x(gate_t *g, qubit_t target)` modifies `g` in place
- NULL returns for error conditions or null operations: `sequence_t *CC_add()` returns NULL

## Module Design

**Exports:**
- C header files declare function signatures explicitly
- No barrel exports pattern used
- All public functions declared in headers with comments showing purpose

**Barrel Files:**
- Not used; header files directly expose functions

**Header Guard Pattern:**
```c
#ifndef CQ_BACKEND_IMPROVED_GATE_H
#define CQ_BACKEND_IMPROVED_GATE_H
// ... content ...
#endif //CQ_BACKEND_IMPROVED_GATE_H
```
Guards use `CQ_BACKEND_IMPROVED_` prefix based on module name, `_H` suffix

**Python Module:**
- Setup.py organizes compilation of C sources into Python extension: `quantum_language` module
- Cython (.pyx) files bridge C and Python code
- No namespace packages used

## Git Workflow

This project uses **Git Flow** branching model.

**Branch Structure:**

| Branch | Purpose | Merges To |
|--------|---------|-----------|
| `main` | Production releases only | — |
| `develop` | Integration branch for features | `main` (releases) |
| `feature/*` | New features and enhancements | `develop` |
| `hotfix/*` | Urgent production fixes | `main` and `develop` |
| `release/*` | Release preparation | `main` and `develop` |

**Workflow:**

1. **Start a feature:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-feature
   ```

2. **Work on the feature:**
   - Make commits on the feature branch
   - Keep commits atomic and well-described

3. **Complete a feature:**
   ```bash
   git checkout develop
   git pull origin develop
   git merge --no-ff feature/my-feature
   git push origin develop
   git branch -d feature/my-feature
   ```

4. **Create a release:**
   ```bash
   git checkout develop
   git checkout -b release/v1.x.x
   # Update version numbers, final testing
   git checkout main
   git merge --no-ff release/v1.x.x
   git tag -a v1.x.x -m "Release v1.x.x"
   git checkout develop
   git merge --no-ff release/v1.x.x
   ```

5. **Hotfix (urgent production fix):**
   ```bash
   git checkout main
   git checkout -b hotfix/critical-fix
   # Fix the issue
   git checkout main
   git merge --no-ff hotfix/critical-fix
   git tag -a v1.x.y -m "Hotfix v1.x.y"
   git checkout develop
   git merge --no-ff hotfix/critical-fix
   ```

**Branch Naming Conventions:**
- `feature/short-description` — New features
- `hotfix/issue-description` — Production fixes
- `release/vX.Y.Z` — Release preparation

**Commit Messages:**
- Use imperative mood: "Add feature" not "Added feature"
- Keep first line under 72 characters
- Reference issues when applicable: "Fix #123: description"

---

*Convention analysis: 2026-01-25*
