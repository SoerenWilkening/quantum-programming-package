# Phase 104: Walk Register Scaffolding & Local Diffusion - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Construct quantum walk registers (one-hot height, per-level branch) and a single local diffusion operator D_x from raw primitives — no QWalkTree API. The diffusion operator must derive the board position at each node by replaying branch register history from the starting position, then compute position-dependent branching factor d(x) for Montanaro diffusion angles. Phase 105 composes these into full R_A/R_B/walk step.

</domain>

<decisions>
## Implementation Decisions

### Board state derivation
- Sequential replay: apply move oracle level-by-level from starting position through branch registers 0..d-1
- Mux-style dispatch for move selection: build a multiplexer that reads the branch register value and applies the corresponding move (not one oracle per move with quantum conditionals)
- Inverse replay for uncomputation: use .inverse property of each compiled move oracle in reverse order (LIFO) to uncompute derived board state after diffusion
- Plain Python emitter (not a compiled function): a regular function that calls individual compiled oracles in sequence, giving transparency and easier debugging; manual inverse by calling in reverse

### Diffusion angle strategy
- Quantum d(x) computation: determine branching factor from the quantum board state at runtime, not precomputed classically
- Predicate-driven approach (walk.py _variable_diffusion style): evaluate each child's validity via validity qubits, then apply conditional Ry cascade rotations
- Purpose-built quantum predicate: write a new predicate that checks move legality directly from the board qarray state (does not call chess_encoding.legal_moves() classically)
- Exact Montanaro angles: phi = 2*arctan(sqrt(d)) for internal nodes, special root formula — same formulas from Montanaro 2015 as implemented in walk.py

### Walk module reuse
- Reuse walk.py internal helpers: import _plan_cascade_ops, _emit_cascade_ops, _emit_cascade_h_controlled directly — "manual" means no QWalkTree class, not no helper reuse
- Keep helpers private: no API changes to walk.py (no renaming to public)
- Use public ql.diffusion() for S_0 reflection — demonstrates framework usage
- Raw qint allocation for registers: directly call qint(0, width=...) for height and branch registers, no wrapper helpers

### Module organization
- New src/chess_walk.py module alongside chess_encoding.py
- Purely functional style (no class): functions like create_height_register(), create_branch_registers(), derive_board_state(), apply_diffusion()
- New tests/python/test_chess_walk.py for walk-specific tests
- Component testing only: test each function in isolation within 17-qubit budget (height register init, single move replay, single diffusion step) — no tiny-board integration tests

### Implementation style
- Keep quantum implementation as compact as possible for a better overview — minimize boilerplate, favor concise circuit construction

### Claude's Discretion
- Mux dispatch implementation details (controlled-swap vs conditional oracle activation)
- Validity qubit allocation strategy for predicate evaluation
- Exact function signatures and parameter ordering
- Which walk.py helpers to import vs which to inline
- Test case selection for component verification

</decisions>

<specifics>
## Specific Ideas

- The existing walk.py _variable_diffusion is the proven reference for predicate-driven diffusion with validity qubits and conditional Ry cascade — follow this pattern closely
- Phase 103's move oracle uses _make_apply_move() factory with classical move_specs in closure and @ql.compile(inverse=True) — the mux dispatcher needs to work with these compiled functions
- White max ~32 moves (5-bit branch register), black max 8 moves (3-bit branch register) — branch register width per level fixed at maximum for that player's turn
- User wants compact, overview-friendly quantum code — avoid verbose scaffolding

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `walk.py:_plan_cascade_ops(d, w)`: Pre-compute gate operations for d-way equal superposition Ry cascade
- `walk.py:_emit_cascade_ops(branch_reg, ops, sign)`: Execute planned cascade ops on branch register
- `walk.py:_emit_cascade_h_controlled(branch_reg, ops, h_qubit_idx, sign)`: Height-controlled cascade emission
- `walk.py:_emit_multi_controlled_ry(target, angle, ctrl_qubits)`: Multi-controlled Ry gate via V-gate CCRy decomposition
- `diffusion.py:diffusion(*registers)`: Public S_0 reflection (X-MCZ-X pattern)
- `chess_encoding.py:get_legal_moves_and_oracle()`: Returns compiled apply_move function with .inverse support
- `chess_encoding.py:knight_attacks(sq)`, `king_attacks(sq)`: Classical attack pattern generators

### Established Patterns
- @ql.compile(inverse=True) with .inverse property for automatic adjoint
- _make_apply_move() factory: classical move_specs in closure, separate qarray args for cache key
- V-gate CCRy decomposition for multi-controlled Ry without nested control contexts
- One-hot height encoding: h[k] = |1> when at depth k (walk.py convention)

### Integration Points
- chess_encoding.py move oracle feeds into mux dispatch for board state derivation
- walk.py internal helpers (_plan_cascade_ops, _emit_cascade_ops) for diffusion Ry cascade
- Phase 105 will compose D_x into height-controlled R_A/R_B from these building blocks
- Phase 106 demo scripts import chess_walk.py functions

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 104-walk-register-scaffolding-local-diffusion*
*Context gathered: 2026-03-03*
