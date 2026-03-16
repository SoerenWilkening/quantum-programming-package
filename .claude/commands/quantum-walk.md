You are guiding the user through designing quantum walk functions for the Quantum Assembly framework. Follow these phases in order.

---

## Background: Quantum Walks in This Framework

A quantum walk searches a tree by superposing over children at each node. The user provides:

- **`state`**: A quantum register (qarray/qint) representing a node (e.g., variable assignments for ILP, board position for chess)
- **`make_move(state, move_index)`**: A compiled quantum function that transforms the state by applying move `move_index`. Must be decorated with `@ql.compile(inverse=True)` for reversibility.
- **`is_valid(state)`**: A quantum predicate returning `qbool` — is this state feasible?
- **`is_marked(state)`**: A quantum predicate returning `qbool` — is this a solution? Evaluated **quantumly** on superpositions of basis states (no classical enumeration). Marked nodes receive identity (D_x = I) while unmarked nodes receive the standard diffusion operator (per Montanaro 2015).

The framework handles all internal machinery: height registers, branch registers, counting valid children, Montanaro rotation angles, R_A/R_B walk operators, and marking.

> **Note**: Detection via quantum phase estimation (Montanaro 2015, Theorem 1) is a future milestone. Currently `walk()` returns a `(config, registers)` pair for manual walk step iteration.

### API

```python
# Build a marked walk configuration with allocated registers.
# Returns (WalkConfig, WalkRegisters) — ready for use with walk_step.
config, registers = ql.walk(
    is_marked, max_depth=depth, num_moves=num,
    state=state, make_move=make_move, is_valid=is_valid,
)

# Local diffusion building block — for custom walk operators
ql.walk_diffusion(state, make_move, is_valid, num_moves=num)
```

### Key Principle

The user's functions (`make_move`, `is_valid`, `is_marked`) use normal Python arithmetic on quantum types (`qint`, `qbool`, `qarray`). They work on all computational basis states simultaneously — that's quantum parallelism. The user never touches gates. The `is_marked` predicate is evaluated quantumly: it returns a `qbool` that controls whether each node receives identity or diffusion. There is no classical enumeration of basis states.

---

## Phase 1: Problem Description (Structured)

Ask the user these questions, one at a time. If any answer is unclear, ask follow-up questions before moving on.

1. **State representation**: "What does a single node in your search tree look like? Describe the data — e.g., a list of variable assignments, a board position, a graph coloring."

2. **Move structure**: "What are the possible moves (transitions) from any node to its children? E.g., assign 0 or 1 to the next variable, move a piece, change a color."

3. **Validity rules**: "When is a partial state invalid? What constraints must hold? E.g., no two adjacent nodes share a color, no constraint violated."

4. **Marking criterion**: "What counts as a solution (marked node)? E.g., all variables assigned and all constraints satisfied, checkmate reached."

5. **Parameters**: "How deep is the tree (`max_depth`)? How many moves per node (`num_moves`)?"

After collecting answers, summarize back to the user:

> **Summary**: State is [X], moves are [Y], validity requires [Z], marked means [W], depth=[D], moves=[M]. Does this look right?

Wait for confirmation before proceeding.

---

## Phase 2: Write Quantum Functions

Generate three functions following these rules:

### Rules for Quantum Functions

1. **Use `with` for quantum conditionals, NEVER classical `if` on quantum values.**
   ```python
   # CORRECT — quantum conditional
   cond = (x[i] == 2)
   with cond:
       x[i] = move_index

   # WRONG — classical if on quantum value (collapses superposition)
   if x[i] == 2:
       x[i] = move_index
   ```

2. **Classical `if` is only valid on classical (Python int/bool) values.**
   ```python
   # OK — move_index is a classical int passed by the framework
   if move_index == 0:
       x ^= some_mask
   elif move_index == 1:
       x ^= other_mask
   ```

3. **`make_move` MUST be `@ql.compile(inverse=True)`** for the framework to undo moves during counting.

4. **`is_valid` and `is_marked` must return a `qbool`.** Use comparisons (`==`, `<`, `>`) and combine with `&` (AND) and `|` (OR).

5. **All functions must be pure** — no side effects, no classical state mutation, no print statements.

6. **The state carries its own depth information implicitly.** For ternary-encoded ILP/SAT, unassigned variables have value 2. The function inspects the state to determine what to do. No depth parameter needed.

### Idiom Library

Use these patterns when applicable:

**Ternary variable assignment (ILP/SAT)**
```python
@ql.compile(inverse=True)
def make_move(x, move_index):
    # x is a qarray of ternary qints (values 0, 1, or 2 = unassigned)
    # Assign move_index to the first unassigned variable
    assigned = ql.qbool()  # flag: have we assigned yet?
    for i in range(len(x)):
        is_unassigned = (x[i] == 2)
        can_assign = is_unassigned & (~assigned)
        with can_assign:
            x[i] ^= (2 ^ move_index)  # flip from 2 to move_index via XOR
            assigned ^= 1              # mark as assigned
```

**State modification via XOR (instead of raw qubit manipulation)**
```python
# Instead of getting qubit indices and applying X gates:
# Use XOR with classical values — cleaner, no gate-level code
x[i] ^= value  # flips the bits that differ between current and target
```

**Counting elements matching a condition**
```python
count = ql.qint(0, width=needed_bits)
for i in range(len(arr)):
    cond = (arr[i] == target)
    with cond:
        count += 1
```

**Compound validity check**
```python
def is_valid(x):
    valid = ql.qbool(1)  # start True
    # Check each constraint
    for i, j in constraint_pairs:
        conflict = (x[i] == x[j]) & (x[i] != 2) & (x[j] != 2)
        with conflict:
            valid ^= 1  # flip to False on conflict
    return valid
```

**All-assigned check (for marking)**
```python
def is_marked(x):
    all_assigned = ql.qbool(1)
    for i in range(len(x)):
        unassigned = (x[i] == 2)
        with unassigned:
            all_assigned ^= 1
    # Additional problem-specific check
    satisfies = check_objective(x)
    return all_assigned & satisfies
```

### Generate Classical Equivalents

For every quantum function, generate a classical mirror using plain Python types. Translation rules:

| Quantum | Classical |
|---------|-----------|
| `ql.qint(v, width=w)` | `int(v)` |
| `ql.qbool()` | `bool(False)` |
| `ql.qbool(1)` | `bool(True)` |
| `ql.qarray(...)` | `list[int]` |
| `with cond:` block | `if cond:` block |
| `x ^= val` | `x ^= val` (same) |
| `a & b` (qbool) | `a and b` |
| `a \| b` (qbool) | `a or b` |
| `~a` (qbool) | `not a` |

Example:
```python
# Quantum version
@ql.compile(inverse=True)
def make_move(x, move_index):
    assigned = ql.qbool()
    for i in range(len(x)):
        is_unassigned = (x[i] == 2)
        can_assign = is_unassigned & (~assigned)
        with can_assign:
            x[i] ^= (2 ^ move_index)
            assigned ^= 1

# Classical equivalent
def make_move_classical(x, move_index):
    x = list(x)  # copy
    assigned = False
    for i in range(len(x)):
        is_unassigned = (x[i] == 2)
        can_assign = is_unassigned and (not assigned)
        if can_assign:
            x[i] ^= (2 ^ move_index)
            assigned = not assigned  # XOR with 1
    return x
```

---

## Phase 3: Verify (CC-as-Oracle Loop)

Launch an independent verifier agent with the following instructions:

### Verifier Protocol

1. **Generate test scenarios.** Create domain-relevant inputs covering:
   - **Base cases**: empty state (all unassigned), fully assigned state
   - **Edge cases**: single variable remaining, all constraints tight
   - **Known solutions**: states the user described as solutions during Phase 1
   - **Known non-solutions**: states that should fail validity or marking
   - **Random states**: k=20 random partial assignments for Monte Carlo coverage

2. **Run classical equivalents** on each scenario. Print inputs and outputs clearly:
   ```
   Scenario: x=[2,2,2], move_index=0
   make_move result: [0,2,2]
   is_valid result: True
   is_marked result: False
   ```

3. **Judge each output** using domain knowledge of the problem described in Phase 1:
   - Does `make_move` modify exactly the right variable?
   - Does `make_move_inverse(make_move(x, i))` return to the original state?
   - Does `is_valid` correctly identify constraint violations?
   - Does `is_marked` correctly identify complete solutions?
   - Are `is_valid` and `is_marked` consistent? (marked implies valid, typically)

4. **For exotic/custom problems** where the domain rules are unusual or complex: stop and flag the user with the test results. Ask them to confirm correctness before proceeding.

5. **If issues found**: report the failing scenario, what went wrong, and a proposed fix. Return control to the main conversation to apply the fix. Then re-verify.

6. **If all pass**: report "All N scenarios verified correctly" and return.

---

## Phase 4: Assemble

Wire the verified functions into the walk API:

```python
import quantum_language as ql

ql.circuit()

# State initialization (from Phase 1)
x = ...  # as designed

# Build marked walk configuration and registers.
# walk() returns (WalkConfig, WalkRegisters), not a bool.
# Detection via phase estimation is a future milestone.
config, registers = ql.walk(
    is_marked, max_depth=..., num_moves=...,
    state=x, make_move=make_move, is_valid=is_valid,
)

# Apply walk steps manually (phase-estimation wrapper is TODO)
from quantum_language.walk_operators import walk_step
num_steps = 4  # or compute from tree size
for _ in range(num_steps):
    walk_step(config, registers)
```

Or for custom walk construction using the diffusion building block:

```python
# User builds their own R_A / R_B using walk_diffusion at specific depths
ql.walk_diffusion(x, make_move, is_valid, num_moves=...)
```

Present the complete code to the user.
