# Testing Patterns

**Analysis Date:** 2026-01-25

## Test Framework

**Runner:**
- C: CMake with implicit test structure (no CTest configured)
- Python: Manual test scripts using Python standard library

**Assertion Library:**
- C: No assertion library detected (no Unity, Check, or similar)
- Python: Direct assertions via `print()` calls for circuit output

**Run Commands:**
```bash
cmake .               # Configure CMake build
make                  # Build project
./CQ_backend_improved # Run C executable with default or custom args
python python-backend/test.py  # Run Python backend tests
```

**Build Configuration:**
- File: `CMakeLists.txt`
- C Standard: C23
- Compiler Flags: `-O3` (optimization only, no debug symbols by default)

## Test File Organization

**Location:**
- C tests: Not organized as separate test files; currently integrated into main functionality
- Python tests: `/Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly/python-backend/test.py`

**Naming:**
- Single test file: `test.py` (follows Python convention of `test_*.py` pattern but uses simple name)
- No separate test directory structure

**Structure:**
```
python-backend/
├── test.py          # Integration/functional test
├── setup.py         # Build configuration
└── quantum_language.pyx  # Cython extension source
```

## Test Structure

**Python Test Pattern:**
The `test.py` file demonstrates functional testing of the quantum language:

```python
import quantum_language as ql

# Initialize quantum variables
count_cross_in_row = ql.qint(bits = 2)
count_circle_in_row = ql.qint(bits = 2)
# ... more variable initialization ...

# Use control flow with quantum conditions
for row in range(3):
	for line in range(3):
		# Quantum operations in conditional context
		with ~assigned[row][line] & ~unoccupied[row][line]:
			count_cross_in_line += 1
		# ... more quantum operations ...

# Output circuit representation
count_circle_in_row.print_circuit()
```

**Characteristics:**
- Declarative style using context managers (`with` statement)
- Tests functionality by executing quantum operations and printing circuit output
- Verifies circuit generation, not numerical results
- No structured assertions; manual inspection of output required

## Mocking

**Framework:** None detected

**Patterns:** Not used - tests execute against actual quantum circuit backend

**What to Mock:**
- No mocking currently employed; tests are integration-level, not unit-level

**What NOT to Mock:**
- Entire backend is exercised in tests, not isolated

## Fixtures and Factories

**Test Data:**
Python test initializes quantum variables as fixtures:

```python
count_cross_in_row = ql.qint(bits = 2)
assigned = ql.array((3, 3), dtype=ql.qbool)
unoccupied = ql.array((3, 3), dtype=ql.qbool)
```

Factory functions from `quantum_language` module:
- `ql.qint(bits=N)` - create quantum integer with N bits
- `ql.array((M, N), dtype=...)` - create multidimensional quantum array
- `ql.qbool` - quantum boolean type

**Location:**
- Inline in test file: `/Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly/python-backend/test.py`
- No separate fixtures directory

## Coverage

**Requirements:** None enforced

**View Coverage:** No coverage tools configured

**Current State:** No test coverage metrics available

## Test Types

**Unit Tests:**
- Not present; no isolated unit test structure
- Backend functions tested indirectly through integration tests

**Integration Tests:**
- Located in `python-backend/test.py`
- Tests full quantum operation pipeline: variable initialization → quantum operations → circuit generation
- Example: Tic-tac-toe game logic with quantum state tracking (lines 3-70 of test.py)
- Verifies circuit output via `print_circuit()` method

**E2E Tests:**
- Not structured as separate E2E tests
- Integration test serves as functional validation

**C Backend Tests:**
- Implicit in `main.c` which runs backend operations
- Can pass command-line arguments: `./CQ_backend_improved <num_qubits> <run_flag>`
- Example from main.c:
  ```c
  if (argc > 2) {
      num_qubits = (int) strtol(argv[1], NULL, 10);
      run = (int) strtol(argv[2], NULL, 10);
  }
  ```

## Common Patterns

**Async Testing:**
Not applicable - C and Python backends are synchronous

**Error Testing:**
No explicit error test cases found

**Quantum-Specific Testing:**
Circuit output verification:
```python
# Example from test.py
count_circle_in_row.print_circuit()
```

The `print_circuit()` method from `quantum_language` (C backend) outputs visual representation:
- From `gate.c:36`, function `print_sequence()` prints ASCII circuit diagrams
- Example output format:
  ```
  cycles = [number]
  gates = [number]
  [qubit layout with gates and controls visualized]
  ```

**Manual Verification Approach:**
- Tests run backend code and produce circuit output
- Developer inspects output for correctness
- No automated assertion validation

## Command-Line Testing

**Main executable behavior:**
```c
// From main.c
int main(int argc, char *argv[]) {
    int num_qubits;
    int run;

    if (argc > 2) {
        num_qubits = (int) strtol(argv[1], NULL, 10);
        run = (int) strtol(argv[2], NULL, 10);
    } else {
        num_qubits = 64;
        run = 1;
    }

    // Execution...
    printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
}
```

**Usage:**
```bash
./CQ_backend_improved           # Default: 64 qubits, run=1
./CQ_backend_improved 32 1      # 32 qubits, execute
./CQ_backend_improved 32 0      # 32 qubits, skip execution (timing only)
```

**Output:** Execution time in seconds printed to stdout

## Test Infrastructure Gaps

**Missing:**
- No unit test framework (CMake/CTest not configured)
- No assertion library
- No coverage measurement tools
- No test fixture framework
- No automated test runners
- No continuous integration configuration

**Current Testing Model:**
Manual functional/integration testing with:
1. Executable runs with command-line parameters
2. Prints circuit representation and timing
3. Developer inspects output for correctness
4. Python tests exercise language features and output circuits

---

*Testing analysis: 2026-01-25*
