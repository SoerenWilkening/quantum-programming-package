# Project Research Summary

**Project:** Quantum Assembly -- v8.0 Quantum Chess Walk Rewrite
**Domain:** Quantum move legality predicates in superposition + compile infrastructure optimization
**Researched:** 2026-03-08
**Confidence:** MEDIUM-HIGH

## Executive Summary

The v8.0 milestone replaces classical move pre-filtering in the quantum chess walk with genuine quantum legality predicates that evaluate move validity in superposition. This is the core architectural shift: instead of computing legal moves classically and encoding only those into the circuit, the circuit now enumerates ALL geometrically possible moves and uses quantum predicates (piece-exists, no-friendly-capture, optionally check detection) to set per-move validity ancillae at runtime. No new dependencies are needed -- the existing stack (Python, NumPy, Cython C backend, ql.compile/qbool/qarray framework) is sufficient. The work spans two independent tracks: quantum chess predicates (new chess_predicates.py module) and compile infrastructure optimization (numpy qubit set operations in compile.py/call_graph.py).

The recommended approach is to tackle a critical blocker first: the existing `apply_diffusion` in chess_walk.py uses O(2^d_max) pattern enumeration, which is computationally impossible for the target of up to 218 moves. This must be replaced with an arithmetic counting circuit (O(d_max * log(d_max)) gates) before any predicate integration. After that, build predicates bottom-up (piece-exists, then no-friendly-capture, then check detection), integrate into evaluate_children, and optimize the compile infrastructure in parallel.

The key risks are: (1) the diffusion combinatorial explosion is a hard blocker that must be solved first, (2) the framework's `with qbool:` nesting limitation requires all predicates to use flat Toffoli-AND decomposition rather than nested conditionals, (3) raw qbool allocation per predicate call causes qubit explosion without compiled predicate recycling, and (4) the C backend's MAXLAYERINSEQUENCE (300K) may be exceeded by large chess circuits. All four have clear mitigation strategies identified in the research.

## Key Findings

### Recommended Stack

No new dependencies are required. The existing stack covers all v8.0 needs. The work is about using NumPy more aggressively for qubit set operations and composing new quantum predicates from existing ql.compile/qbool/qarray primitives. See `.planning/research/STACK-CHESS-LEGALITY.md` for full analysis.

**Core technologies (unchanged):**
- **Python 3.13 + NumPy 2.4.2**: Frontend language and array ops -- use NumPy matrix multiply for all-pairs overlap computation in call_graph.py, replacing O(n^2) frozenset intersection
- **ql.compile/qbool/qarray framework**: Quantum predicate composition -- all legality checks compose from existing @ql.compile(inverse=True), qbool AND/OR/NOT, and qarray element access
- **C backend + Cython**: Gate execution layer -- unchanged, but MAXLAYERINSEQUENCE may need increasing
- **rustworkx 0.17.1**: Call graph DAG -- unchanged

**What NOT to use:** python-chess (classical, cannot evaluate superposition), Cirq/PennyLane (would require backend rewrite), bitarray (numpy already covers it), scipy.sparse (overkill for chess-scale circuits).

### Expected Features

See `.planning/research/FEATURES.md` for full analysis including competitor comparison, dependency tree, and qubit budget.

**Must have (v8.0 table stakes):**
- All-moves enumeration table -- precompute ALL structurally possible (piece_type, src, dst) triples at circuit construction time
- Quantum piece-exists predicate -- check board qarray element in superposition via CNOT
- Quantum same-color-capture rejection -- check no friendly piece on target square
- Combined legality predicate -- AND of piece-exists and no-friendly-capture via Toffoli
- Rewritten evaluate_children -- calls quantum predicate instead of trivial always-valid
- Diffusion operator redesign -- arithmetic counting circuit replacing O(2^d_max) enumeration
- Compile infrastructure numpy optimization -- numpy qubit set operations in compile.py/call_graph.py

**Should have (v8.x differentiators):**
- Quantum check detection -- reversible king-safety predicate (knight attacks + king adjacency)
- Compiled predicate caching -- amortize compilation cost across move evaluations
- T-count-aware predicate design -- minimize T-gates since predicates run O(sqrt(T)) times

**Defer (v9+):**
- Sliding piece attack detection (bishops, rooks, queens) -- requires ray-tracing circuits
- Full chess rule support (castling, en passant, promotion) -- scope explosion
- Quantum evaluation function -- deferred EVAL-01/EVAL-02

### Architecture Approach

See `.planning/research/ARCHITECTURE.md` for full component inventory, data flows, and anti-patterns.

The architecture introduces one new module (chess_predicates.py) and modifies four existing ones. The key pattern is "quantum predicate as compiled oracle" -- each legality condition is a separate @ql.compile(inverse=True) function producing a qbool, AND-combined via Toffoli gates. Move enumeration stays classical (geometry is fixed); only legality determination becomes quantum. The compile infrastructure gets a _build_qubit_set() helper using numpy, while DAGNode maintains dual storage (qubit_array for fast overlap, frozenset for backward compatibility). Python int bitmask is kept for >64 qubit support.

**Major components:**
1. **chess_predicates.py (NEW)** -- Quantum legality sub-predicates (piece_exists, target_not_friendly, king_not_in_check) composed into move_is_legal
2. **chess_walk.py (MODIFIED)** -- evaluate_children calls chess_predicates.move_is_legal; diffusion redesigned with arithmetic counting
3. **chess_encoding.py (MODIFIED)** -- Raw destination generation (no legality filtering); attack tables for check detection
4. **compile.py (MODIFIED)** -- _build_qubit_set() helper using np.unique/np.concatenate
5. **call_graph.py (MODIFIED)** -- DAGNode.qubit_array with np.intersect1d for overlap computation

### Critical Pitfalls

See `.planning/research/PITFALLS-CHESS-WALK-REWRITE.md` for all 14 pitfalls with phase assignments and detection strategies.

1. **Diffusion combinatorial explosion (P1)** -- apply_diffusion is O(2^d_max); for 218 moves this is impossible. Replace with arithmetic counting circuit that sums validity bits into a count register, then conditions diffusion on the count value. This is a hard blocker.
2. **Raw qbool allocation causing qubit explosion (P2)** -- Each predicate call allocates fresh qubits without recycling. Use @ql.compile(inverse=True) for auto-uncomputation; recycle predicate ancillae per-child, keeping only validity qbools alive.
3. **Nested `with qbool:` limitation (P3)** -- Framework cannot nest conditional blocks. Design predicates with flat Toffoli-AND decomposition: compute each condition into separate ancilla, AND into result via explicit multi-controlled gates.
4. **Oracle assumes classical pre-filtering (P4)** -- Current oracle only handles classically-computed legal moves, which is wrong for superposition states at depth > 0. Switch to all-moves enumeration with quantum validity filtering.
5. **MAXLAYERINSEQUENCE overflow (P5)** -- 300K layer limit may be exceeded by chess circuits with 218 moves. Estimate gate counts early; increase limit or implement dynamic allocation if needed.

## Implications for Roadmap

Based on combined research, the v8.0 milestone splits into 5 phases. The critical insight from cross-referencing all research is that diffusion redesign (from PITFALLS) is a hard prerequisite that neither FEATURES nor ARCHITECTURE identified as a phase -- but without it, nothing works at chess scale.

### Phase 1: Foundation and Blockers
**Rationale:** The diffusion combinatorial explosion (P1) is a hard blocker that prevents ANY large-branching walk from generating a circuit. Test baseline (P10) must be established before code changes. MAXLAYERINSEQUENCE (P5) must be assessed. These must be solved first.
**Delivers:** Redesigned diffusion operator using arithmetic counting circuit (quantum adder tree summing validity bits into count register, O(d_max * log(d_max)) gates); test baseline with xfail annotations on pre-existing failures; MAXLAYERINSEQUENCE gate count assessment
**Addresses:** Diffusion redesign (critical infrastructure), test baseline establishment
**Avoids:** P1 (combinatorial explosion), P10 (masked regressions), P5 (layer overflow -- at least assessed)

### Phase 2: Compile Infrastructure Optimization
**Rationale:** Independent of chess features; can be built and tested in isolation using existing 186+ compile tests. Provides performance benefit for the larger circuits coming in later phases. Lower risk than chess-specific work.
**Delivers:** numpy qubit set operations in compile.py (_build_qubit_set helper using np.unique/np.concatenate), numpy overlap computation in call_graph.py (DAGNode.qubit_array with np.intersect1d), verified via existing test suite with no regressions
**Uses:** NumPy boolean arrays, np.unique, np.concatenate, np.intersect1d
**Implements:** Architecture Pattern 3 (numpy qubit set operations)
**Avoids:** P6 (frozenset semantics -- keep frozenset on DAGNode for backward compat), P13 (array overhead -- profile before migrating small-set operations)

### Phase 3: Quantum Predicate Module
**Rationale:** Depends on the framework (not on Phase 2), but must be built before walk integration. Each sub-predicate is independently testable on tiny boards (2x2, 3x3) within the 17-qubit simulation limit.
**Delivers:** chess_predicates.py with piece_exists_on_source, target_not_friendly, move_is_legal (AND-combined via Toffoli); unit tests on small boards verifying correctness against classical equivalents
**Addresses:** Quantum piece-exists (1 CNOT), same-color-capture rejection (~4 CNOTs), combined legality predicate
**Avoids:** P3 (nested with -- flat Toffoli-AND from the start), P2 (qubit explosion -- compiled predicates with @ql.compile(inverse=True)), P11 (64-qubit boundary -- separate qarray arguments)

### Phase 4: Walk Integration
**Rationale:** Depends on Phase 1 (diffusion redesign) and Phase 3 (predicates). This is where classical pre-filtering is replaced with quantum legality evaluation. The highest-risk integration point where predicates, oracle, diffusion, and walk framework converge.
**Delivers:** Modified chess_encoding.py with raw destination generation (knight_destinations, king_destinations for all squares); modified evaluate_children calling move_is_legal; all-moves enumeration table with branch register indexing; end-to-end walk with quantum predicates on KNK position
**Addresses:** All-moves enumeration, rewritten evaluate_children, variable branching integration, reversible move application oracle
**Avoids:** P4 (classical pre-filter assumption -- all-moves enumeration), P8 (validity ancilla leaks -- compiled predicates with same-qubit uncompute), P9 (cache key collisions -- use key= parameter), P12 (wasted branch states -- predicate rejects out-of-range)

### Phase 5: Check Detection (v8.x)
**Rationale:** Additive feature that composes into the existing legality predicate as a third AND condition. Can be developed independently after core legality is proven correct. Uses the same "classical attack table, quantum lookup" pattern.
**Delivers:** king_not_in_check predicate using pre-computed classical attack tables (8 king adjacents + 8 knight L-shapes) with quantum board qarray lookups; integrated into move_is_legal as third AND condition
**Addresses:** Quantum check detection (differentiator feature -- no other quantum chess implementation does this reversibly)
**Avoids:** P7 (full-board scan -- use pre-computed attack tables, ~16 CNOT checks + OR reduction per move)

### Phase Ordering Rationale

- Phase 1 first because diffusion explosion is a hard blocker -- no walk circuit with >3 children can be generated without fixing it
- Phase 2 is independent and can run in parallel with Phase 1, but ordered after for sequential execution since it is lower priority
- Phase 3 before Phase 4 because predicates must exist before they can be integrated into the walk
- Phase 4 is the integration phase that combines Phases 1 and 3 -- cannot start until both are complete
- Phase 5 is additive and does not block core functionality; it adds a third condition to an already-working predicate

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Diffusion redesign):** The arithmetic counting circuit (quantum adder tree summing validity bits into a count register) is non-trivial quantum circuit design. Needs research into efficient Hamming weight circuits, how they interact with the existing diffusion angle computation (precompute_diffusion_angles), and qubit requirements for the count register (ceil(log2(d_max)) qubits).
- **Phase 4 (Walk integration):** Complex integration point where predicates, oracle, diffusion, and walk framework converge. The evaluate_children rewrite touches multiple interacting systems with subtle qubit lifecycle requirements. Needs careful sequencing research.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Compile numpy):** Standard numpy refactoring with 186+ existing tests for validation. Well-understood patterns. Profile-driven.
- **Phase 3 (Quantum predicates):** Each sub-predicate is straightforward composition of existing ql.compile/qbool/qarray operations. Patterns established in codebase (e.g., _make_apply_move factory).
- **Phase 5 (Check detection):** Classical attack tables are well-documented in chess programming literature (chessprogramming.org); quantum lookup uses the same board[rank, file] access as piece-exists.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies; all technologies already installed and verified working with Python 3.13 |
| Features | MEDIUM | Novel domain (quantum chess predicates in Montanaro walk); individual sub-features well-understood but integration is uncharted. No prior art for reversible chess legality predicates. |
| Architecture | HIGH | Based on direct codebase analysis of chess_walk.py, chess_encoding.py, compile.py, call_graph.py. Architecture follows established project patterns (factory oracles, compiled predicates). |
| Pitfalls | HIGH | All 14 pitfalls derived from code inspection and mathematical analysis. Several are documented known limitations in PROJECT.md. Combinatorial analysis verified computationally. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Diffusion redesign specifics:** The arithmetic counting circuit approach is identified but not fully designed. Need to determine exact qubit count for count register, ancilla requirements for the adder tree, and how diffusion angles are conditioned on the count value rather than per-pattern enumeration. This is the biggest unknown and the highest-risk item.
- **MAXLAYERINSEQUENCE sizing:** Gate count for full chess circuits not yet estimated. Need to compute: (gates per predicate) x (moves per level) x (depth) x (walk iterations) x 2 (forward + adjoint) and compare against 300K limit. May need dynamic allocation or the deferred sparse circuit arrays.
- **Qubit budget validation:** Total qubit count (~210 for depth-1 KNK) far exceeds 17-qubit simulation limit. Testing strategy relies on tiny-board unit tests and structural verification. Need to validate that this testing approach provides sufficient confidence for correctness.
- **Cache key correctness for predicates:** The @ql.compile cache key behavior with move-index-parameterized predicates needs validation during implementation to avoid P9 (cache collisions). The factory pattern from _make_apply_move provides a model but has not been tested with the predicate pattern.
- **Toffoli AND-combination gate cost:** The combined legality predicate (AND of 2-3 sub-predicates) uses Toffoli gates. The exact ancilla and T-gate cost for multi-predicate AND, multiplied by up to 218 moves, needs budgeting. Each additional predicate condition adds ~7 T-gates per move.

## Sources

### Primary (HIGH confidence)
- Project codebase: compile.py, call_graph.py, chess_encoding.py, chess_walk.py, walk.py -- direct code analysis with line-number references
- PROJECT.md known limitations and key decisions -- documented constraints
- c_backend/include/types.h -- MAXLAYERINSEQUENCE = 300,000
- pyproject.toml and pip show -- dependency verification

### Secondary (MEDIUM confidence)
- Montanaro, "Quantum walk speedup of backtracking algorithms" (arXiv:1509.02374) -- walk operator structure, predicate oracle interface P_x
- Martiel, "Practical implementation of a quantum backtracking algorithm" -- resource estimates for predicate oracles
- Google Quantum Chess (Cirq) documentation -- competitor approach (measurement-based, incompatible with walk)
- Chessprogramming wiki (Knight Pattern, Square Attacked By) -- classical attack pattern algorithms

### Tertiary (LOW confidence)
- Quantum adder tree / Hamming weight circuit designs -- referenced for diffusion redesign but not yet validated against project framework constraints
- psitae/game-tree (GitHub) -- quantum game tree evaluation, tangential reference
- Cantwell Quantum Chess documentation -- full quantum chess rule set, different architectural approach

---
*Research completed: 2026-03-08*
*Ready for roadmap: yes*
