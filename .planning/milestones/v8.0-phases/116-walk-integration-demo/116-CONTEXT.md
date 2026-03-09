# Phase 116: Walk Integration & Demo - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Rewrite chess_walk.py to evaluate move legality in superposition using quantum predicates (from Phases 114-115) instead of classical pre-filtering. Replace get_legal_moves_and_oracle with build_move_table for all-moves enumeration. Update demo.py as a minimal-stats framework showcase. Remove old classical pre-filtering code.

</domain>

<decisions>
## Implementation Decisions

### Predicate wiring
- Pre-build all combined predicates at prepare_walk_data time, one per move entry in the table
- Store compiled predicates alongside move data in the per-level dict
- evaluate_children indexes predicate[i] and calls it with board qarrays + validity[i]
- Side-aware arg packing: prepare_walk_data determines which qarrays are friendly/enemy based on side-to-move, packs args per combined predicate signature (piece_qarray, *friendly_qarrays, king_qarray, *enemy_qarrays, result)
- Predicate call happens AFTER oracle applies the move (evaluate on child board state): encode child index -> flip height -> apply oracle -> evaluate predicate on resulting board -> undo
- Replace only the trivial reject+flip block in evaluate_children (steps d-e), keep steps (a)-(c) and (f)-(h) identical to preserve proven navigate-evaluate-undo pattern

### Move table integration
- Replace get_legal_moves_and_oracle entirely in prepare_walk_data — call build_move_table instead
- Oracle still transforms board state (apply_move); needed for derive/underive pattern
- Predicate evaluates legality of the resulting board independently
- Independent tables per side with independent branch widths: white levels d_max=24, branch_width=5; black levels d_max=8, branch_width=3
- Off-board moves: oracle emits identity (no-op), predicate naturally returns |0> (piece-exists fails)

### Enemy attack configuration
- Build enemy_attacks in prepare_walk_data per level based on side-to-move
- White moves: enemy_attacks = [(king_offsets, 'bk')]
- Black moves: enemy_attacks = [(king_offsets, 'wk'), (knight_offsets, 'wn')]
- Explicit qarray mapping stored in move_data per level: piece_qarray_key, friendly_keys, king_key, enemy_keys
- At evaluate_children time, look up actual qarrays from board_arrs tuple using these keys

### Demo design
- Update existing demo.py (replace old approach entirely)
- KNK position: white king e4, white knight c3, black king e8
- Walk depth 2 (white move + black response)
- Minimal stats output: qubit count, gate count, circuit depth, build time
- Circuit-build-only (no Qiskit simulation — exceeds 17-qubit limit)

### Code clarity
- Readability first — the demo is a framework showcase, code should demonstrate natural programming style
- Drop the complex _walk_ctx closure/mutable-dict pattern from walk_step
- Keep @ql.compile on walk_step with explicit args (no closure tricks) for call graph visualization with opt=1
- Keep all_walk_qubits mega-register (required by @ql.compile to treat walk qubits as parameters) but simplify and add clear docstring explaining WHY it exists
- Simple key function based on qubit count instead of opaque lambda

### Old code cleanup
- Remove get_legal_moves_and_oracle from chess_encoding.py (replaced by build_move_table + quantum predicates)
- Keep legal_moves_white/black as test-only helpers (Phase 114-115 predicate tests depend on them for classical equivalence verification)
- Remove old test_demo.py tests entirely, write new tests for rewritten demo
- Tests are circuit-build-only (no simulation) — verify circuit construction succeeds, check stat assertions

### Claude's Discretion
- Exact structure of the per-level move_data dict (keys and values)
- How to thread qarray references through the predicate call signature
- Test assertions: specific gate count / qubit count ranges vs just "builds without error"
- Whether to keep or simplify precompute_diffusion_angles helper

</decisions>

<specifics>
## Specific Ideas

- The current chess_walk.py walk_step has incomprehensible closure patterns (_walk_ctx, _walk_compiled_fn, custom key lambda) that must be replaced with straightforward explicit-arg @ql.compile usage
- The demo should demonstrate that quantum algorithms are writable in natural programming style — the code itself is the showcase
- Phase 113's build_move_table provides fixed (piece_type, src_offset) entries that map directly to predicate factory parameters

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `build_move_table` (chess_encoding.py:66): All-moves enumeration replacing get_legal_moves_and_oracle
- `make_combined_predicate` (chess_predicates.py:322): Combined legality predicate factory
- `_make_apply_move` (chess_encoding.py:390): Oracle factory for board state transformation
- `counting_diffusion_core` (walk.py): Shared counting-based diffusion operator
- `encode_position` (chess_encoding.py:97): Board qarray creation for demo setup
- `_KNIGHT_OFFSETS` / `_KING_OFFSETS` (chess_encoding.py:42-63): Offset tables for attack config

### Established Patterns
- Factory pattern: classical precomputation outside @ql.compile, quantum ops inside
- Flat Toffoli-AND decomposition (no nested `with qbool:`)
- Variadic `*args` signature with result qbool as last argument
- Side-alternating levels: white at even indices, black at odd indices

### Integration Points
- `evaluate_children` (chess_walk.py:245): Replace trivial predicate block with combined_predicate call
- `prepare_walk_data` (chess_walk.py:140): Switch from get_legal_moves_and_oracle to build_move_table
- `walk_step` (chess_walk.py:609): Simplify @ql.compile wrapper, remove closure pattern
- `demo.py`: Full rewrite to use new quantum-predicate-based walk

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 116-walk-integration-demo*
*Context gathered: 2026-03-09*
