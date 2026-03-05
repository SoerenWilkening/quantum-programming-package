# Phase 106: Demo Scripts - Research

**Researched:** 2026-03-05
**Domain:** Python demo scripting, quantum circuit statistics, QWalkTree API comparison
**Confidence:** HIGH

## Summary

Phase 106 creates two demo scripts: (1) `src/demo.py` replacing the existing prototype with a chess quantum walk walkthrough, and (2) `src/chess_comparison.py` comparing manual walk circuit stats against QWalkTree API stats. All building blocks exist from Phases 103-105. This is a composition/integration phase with no new algorithmic work.

The primary challenge is correctly wiring together the existing APIs (chess_encoding, chess_walk, QWalkTree) and producing clean, readable output. Circuit generation only -- no simulation (qubit count ~150 exceeds 17-qubit budget). A single smoke test verifies both scripts run without error.

**Primary recommendation:** Build demo.py first (it validates all manual walk infrastructure), then chess_comparison.py (reuses same position constants and adds QWalkTree side).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Full walkthrough style: print board position, legal moves per side, tree structure summary (branching per level), walk operators, and circuit statistics (qubits, gates, depth)
- Progressive output: print each section as it happens (position -> moves -> registers -> building walk step... -> stats)
- Per-section timing: time each major step (move generation, register creation, walk step compilation) and print duration
- Optional circuit visualization: add a `--visualize` flag (or similar variable) to generate PNG via `ql.draw_circuit()`; skip by default since chess circuits are huge
- Use interesting endgame position: wk=e4 (sq 28), bk=e8 (sq 60), wn=[c3 (sq 18)]
- max_depth = 1 (single ply, white moves only, ~150 qubits)
- Position configured via module-level constants at top of script (WK_SQ, BK_SQ, WN_SQUARES, MAX_DEPTH) -- easy to modify
- Build walk step only (no detect()) -- create QWalkTree with same branching structure, compile walk_step(), print circuit stats
- Always-accept trivial predicate matching the manual approach (all children valid in precomputed KNK endgame)
- Side-by-side comparison table: Metric | Manual | QWalkTree | Delta -- clean, scannable format
- Replace existing src/demo.py with the chess walk demo (old prototype code superseded)
- New src/chess_comparison.py for QWalkTree comparison script
- Smoke test only: single test verifying demo main() completes without error and produces non-zero circuit stats

### Claude's Discretion
- Exact print formatting and section headers
- Which circuit statistics to include (gate types, T-count, etc.)
- Smoke test implementation details
- How to structure the --visualize flag (argparse vs module variable)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEMO-01 | demo.py with full manual quantum walk -- starting position, legal move tree, walk operators, circuit statistics | All building blocks exist: chess_encoding (print_position, print_moves, encode_position, get_legal_moves_and_oracle), chess_walk (prepare_walk_data, create_height_register, create_branch_registers, walk_step, all_walk_qubits), circuit object properties (gate_count, depth, qubit_count, gate_counts) |
| DEMO-02 | Secondary script using QWalkTree API on same chess position for comparison | QWalkTree class in quantum_language.walk takes max_depth, branching (list[int]), predicate. walk_step() method compiles and caches. Same circuit stats accessible via circuit object properties |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language | project-local | Circuit generation, QWalkTree, stats | Project's own framework |
| chess_encoding | project-local | Board encoding, move generation, print helpers | Phase 103 output |
| chess_walk | project-local | Walk registers, operators, walk_step | Phase 104-105 output |
| time | stdlib | Per-section timing | Established pattern in existing demo.py |
| argparse | stdlib | --visualize flag parsing | Standard CLI argument handling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| math | stdlib | ceil/log2 for branching width display | Tree structure summary |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | Module-level VISUALIZE constant | argparse is cleaner for CLI; constant is simpler but less discoverable |

**Installation:** No new dependencies needed.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── demo.py              # DEMO-01: Manual chess walk demo (replaces existing)
├── chess_comparison.py   # DEMO-02: QWalkTree API comparison
├── chess_encoding.py     # Phase 103: Board encoding + move generation
├── chess_walk.py         # Phase 104-105: Walk registers + operators
tests/python/
└── test_demo.py          # Smoke test for both scripts
```

### Pattern 1: Progressive Walkthrough with Timing
**What:** Print each section header, execute the step, print results and elapsed time.
**When to use:** demo.py main flow.
**Example:**
```python
import time
import quantum_language as ql

def main():
    c = ql.circuit()

    # --- Section: Position ---
    print("=" * 60)
    print("QUANTUM CHESS WALK DEMO")
    print("=" * 60)
    t0 = time.time()
    print_position(WK_SQ, BK_SQ, WN_SQUARES)
    print(f"  ({time.time() - t0:.3f}s)")

    # ... more sections ...

    # --- Section: Circuit Statistics ---
    print("\n--- Circuit Statistics ---")
    print(f"  Qubits:     {c.qubit_count}")
    print(f"  Gates:      {c.gate_count}")
    print(f"  Depth:      {c.depth}")
    counts = c.gate_counts
    for gate, count in sorted(counts.items()):
        if count > 0:
            print(f"  {gate:10s}: {count}")
```

### Pattern 2: QWalkTree with Trivial Predicate
**What:** Create QWalkTree with same branching, trivial always-accept predicate, compile walk_step.
**When to use:** chess_comparison.py.
**Example:**
```python
import quantum_language as ql

def trivial_predicate(node):
    """Always-accept: no node is rejected."""
    is_accept = ql.qbool()   # |0> = not accepted (leaf check irrelevant for walk_step)
    is_reject = ql.qbool()   # |0> = not rejected (all children valid)
    return (is_accept, is_reject)

c = ql.circuit()
# branching must match manual approach's move counts
tree = ql.QWalkTree(max_depth=MAX_DEPTH, branching=branching_list, predicate=trivial_predicate)
tree.walk_step()
# Stats from c.gate_count, c.depth, c.qubit_count
```

### Pattern 3: Side-by-Side Comparison Table
**What:** Print aligned table comparing manual vs QWalkTree circuit stats.
**When to use:** chess_comparison.py output.
**Example:**
```python
def print_comparison(manual_stats, api_stats):
    header = f"{'Metric':<20} {'Manual':>10} {'QWalkTree':>10} {'Delta':>10}"
    print(header)
    print("-" * len(header))
    for key in ['qubit_count', 'gate_count', 'depth']:
        m = manual_stats[key]
        a = api_stats[key]
        delta = a - m
        sign = "+" if delta > 0 else ""
        print(f"{key:<20} {m:>10} {a:>10} {sign}{delta:>9}")
```

### Pattern 4: Script with main() Entry Point
**What:** Wrap demo logic in `main()` function callable from tests and from `if __name__ == "__main__"`.
**When to use:** Both demo.py and chess_comparison.py.
**Example:**
```python
def main(visualize=False):
    """Run the demo. Returns circuit stats dict for testing."""
    c = ql.circuit()
    # ... demo logic ...
    stats = {'qubit_count': c.qubit_count, 'gate_count': c.gate_count, 'depth': c.depth}
    return stats

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--visualize", action="store_true")
    args = parser.parse_args()
    main(visualize=args.visualize)
```

### Anti-Patterns to Avoid
- **Top-level circuit creation without main():** Makes testing impossible; always wrap in a function
- **Simulating the circuit:** ~150 qubits far exceeds 17-qubit budget; circuit generation only
- **Hardcoding position in function bodies:** Use module-level constants per CONTEXT.md decision

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Board visualization | Custom board printer | `chess_encoding.print_position()` | Already handles formatting, rank labels, piece chars |
| Move listing | Custom move formatter | `chess_encoding.print_moves()` | Has algebraic notation, indices, formatting |
| Legal move generation | Manual move logic | `chess_encoding.legal_moves()` / `get_legal_moves_and_oracle()` | Edge-aware, side-specific, already tested |
| Walk registers | Manual qint allocation | `chess_walk.create_height_register()`, `create_branch_registers()` | One-hot encoding, correct initialization |
| Walk step compilation | Manual R_A/R_B calls | `chess_walk.walk_step()` | Handles compile caching, mega-register wrapping |
| Circuit stats | Manual qubit counting | `circuit.gate_count`, `.depth`, `.qubit_count`, `.gate_counts` | Built into framework |

**Key insight:** Phase 106 is pure integration -- every building block is already implemented and tested. The demo scripts should compose existing functions, not reimplement any logic.

## Common Pitfalls

### Pitfall 1: Forgetting to Reset _walk_compiled_fn Between Scripts
**What goes wrong:** chess_walk.walk_step uses a module-level `_walk_compiled_fn` cache. If both demo.py and chess_comparison.py run in the same process, the second call may replay the first circuit's gates.
**Why it happens:** Module-level compiled function persists across circuit() calls.
**How to avoid:** Each script creates its own `ql.circuit()` at the start. For the comparison script, it needs a separate circuit. The smoke test should test each in isolation (separate function calls, each starting with `ql.circuit()`). Reset `_walk_compiled_fn = None` if needed between runs in same process.
**Warning signs:** Gate counts don't match expectations; second script's circuit is empty or duplicated.

### Pitfall 2: QWalkTree branching Must Be a List Matching max_depth
**What goes wrong:** Passing an int when move counts differ per level, or passing wrong-length list.
**Why it happens:** For max_depth=1, branching is a 1-element list `[move_count]`.
**How to avoid:** Extract move_count from `prepare_walk_data()` output and pass as `branching=[move_count]`.
**Warning signs:** ValueError from QWalkTree constructor about list length.

### Pitfall 3: QWalkTree Predicate Must Return (is_accept, is_reject) Tuple
**What goes wrong:** Predicate returns wrong type; constructor validation fails.
**Why it happens:** API requires two qbools, not a single bool.
**How to avoid:** Return `(ql.qbool(), ql.qbool())` -- both initialized to |0> means "not accepted, not rejected" (trivial predicate for walk_step-only usage).
**Warning signs:** TypeError from QWalkTree constructor.

### Pitfall 4: sys.path for Imports
**What goes wrong:** `import chess_encoding` fails when running from project root.
**Why it happens:** chess_encoding.py is in src/, not installed as a package.
**How to avoid:** Add `sys.path.insert(0, os.path.join(os.path.dirname(__file__)))` at top of demo scripts, or run from src/ directory. Tests already handle this via conftest.py.
**Warning signs:** ModuleNotFoundError for chess_encoding or chess_walk.

### Pitfall 5: Circuit Object Must Be Created Before Any Quantum Operations
**What goes wrong:** Segfault or "circuit not initialized" error.
**Why it happens:** quantum_language requires `ql.circuit()` call before any qint/qarray allocation.
**How to avoid:** Call `c = ql.circuit()` as the very first quantum operation in main().
**Warning signs:** RuntimeError about circuit validation.

## Code Examples

### demo.py Main Flow (Verified from Existing APIs)
```python
# Source: chess_encoding.py, chess_walk.py APIs
import quantum_language as ql
from chess_encoding import (
    encode_position, get_legal_moves_and_oracle,
    print_position, print_moves, legal_moves
)
from chess_walk import (
    create_height_register, create_branch_registers,
    prepare_walk_data, walk_step, all_walk_qubits
)

WK_SQ = 28   # e4
BK_SQ = 60   # e8
WN_SQUARES = [18]  # c3
MAX_DEPTH = 1

def main(visualize=False):
    c = ql.circuit()

    # 1. Print position
    print_position(WK_SQ, BK_SQ, WN_SQUARES)

    # 2. Print legal moves
    white_moves = legal_moves(WK_SQ, BK_SQ, WN_SQUARES, "white")
    print_moves(white_moves, label="White moves")

    # 3. Create board qarrays
    boards = encode_position(WK_SQ, BK_SQ, WN_SQUARES)
    board_arrs = (boards["white_king"], boards["black_king"], boards["white_knights"])

    # 4. Prepare walk data
    move_data = prepare_walk_data(WK_SQ, BK_SQ, WN_SQUARES, MAX_DEPTH)
    oracle_per_level = [md["apply_move"] for md in move_data]

    # 5. Create registers
    h_reg = create_height_register(MAX_DEPTH)
    branch_regs = create_branch_registers(MAX_DEPTH, move_data)

    # 6. Compile walk step
    walk_step(h_reg, branch_regs, board_arrs, oracle_per_level, move_data, MAX_DEPTH)

    # 7. Print stats
    stats = {
        'qubit_count': c.qubit_count,
        'gate_count': c.gate_count,
        'depth': c.depth,
        'gate_counts': c.gate_counts,
    }
    return stats
```

### QWalkTree Comparison (Verified from walk.py API)
```python
# Source: quantum_language.walk.QWalkTree
import quantum_language as ql

def trivial_predicate(node):
    is_accept = ql.qbool()
    is_reject = ql.qbool()
    return (is_accept, is_reject)

c = ql.circuit()
# For max_depth=1 with N white moves:
branching = [len(white_moves)]  # Single-element list for depth 1
tree = ql.QWalkTree(max_depth=MAX_DEPTH, branching=branching,
                    predicate=trivial_predicate, max_qubits=200)
tree.walk_step()
api_stats = {
    'qubit_count': c.qubit_count,
    'gate_count': c.gate_count,
    'depth': c.depth,
}
```

### Circuit Stats Access (Verified from _core.pyx)
```python
# Source: _core.pyx circuit class properties
c = ql.circuit()
# ... build circuit ...
c.qubit_count    # int: total qubits allocated
c.gate_count     # int: total gate count
c.depth          # int: circuit depth (layers)
c.gate_counts    # dict: {'X': n, 'H': n, 'CNOT': n, 'Ry': n, 'Rz': n, 'T': n, ...}

# Allocator stats (separate function):
ql.circuit_stats()  # dict: peak_allocated, current_in_use, etc.
```

### draw_circuit Usage (Verified from __init__.py)
```python
# Source: quantum_language/__init__.py
img = ql.draw_circuit(c, save="chess_circuit.png")
# Returns PIL.Image.Image; save parameter auto-saves to file
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Old demo.py (knight attack prototype) | Chess walk walkthrough demo | Phase 106 | Old code superseded; safe to replace entirely |
| Manual R_A/R_B calls | `walk_step()` compiled function | Phase 105 | Single function call for full walk operator |

**Deprecated/outdated:**
- `src/demo.py`: Contains old prototype code (knight attack counting). Will be replaced entirely.

## Open Questions

1. **QWalkTree max_qubits parameter**
   - What we know: Default is 17 (simulation budget). Constructor accepts it but only checks at simulation time.
   - What's unclear: Whether walk_step() will raise if qubit count exceeds max_qubits since it doesn't simulate.
   - Recommendation: Pass `max_qubits=200` (or higher) to be safe. walk_step only generates circuit, no simulation.

2. **_walk_compiled_fn state between test runs**
   - What we know: Module-level cache in chess_walk.py.
   - What's unclear: Whether pytest test isolation handles this automatically via circuit() reset.
   - Recommendation: In smoke test, call `chess_walk._walk_compiled_fn = None` before each test if needed, or rely on separate ql.circuit() calls resetting compile cache.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | tests/python/conftest.py |
| Quick run command | `pytest tests/python/test_demo.py -v -x` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEMO-01 | demo.py main() runs without error, returns non-zero stats | smoke | `pytest tests/python/test_demo.py::test_demo_main -x` | No - Wave 0 |
| DEMO-02 | chess_comparison.py main() runs without error, returns stats | smoke | `pytest tests/python/test_demo.py::test_comparison_main -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_demo.py -v -x`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_demo.py` -- smoke tests for DEMO-01 and DEMO-02
- No new framework installs needed (pytest already configured)

## Sources

### Primary (HIGH confidence)
- `src/chess_encoding.py` - All chess encoding and move generation APIs (direct code inspection)
- `src/chess_walk.py` - Walk register, diffusion, R_A/R_B, walk_step APIs (direct code inspection)
- `src/quantum_language/walk.py` - QWalkTree class, walk_step(), detect() APIs (direct code inspection)
- `src/quantum_language/_core.pyx` - circuit class: gate_count, depth, qubit_count, gate_counts, circuit_stats() (direct code inspection)
- `src/quantum_language/__init__.py` - draw_circuit() signature, QWalkTree export (direct code inspection)

### Secondary (MEDIUM confidence)
- `tests/python/test_chess_walk.py` - Test patterns for chess walk modules (direct code inspection)
- `src/demo.py` - Existing prototype code to be replaced (direct code inspection)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries are project-internal, directly inspected
- Architecture: HIGH - composition of well-tested existing modules
- Pitfalls: HIGH - derived from direct API analysis and module-level state inspection

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- no external dependencies)
