# Requirements: Quantum Assembly

**Defined:** 2026-03-03
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits

## v6.1 Requirements

Requirements for Quantum Chess Demo milestone. Each maps to roadmap phases.

### Chess Board & Legal Moves

- [x] **CHESS-01**: 8x8 board with piece positions encoded as qarray (2 kings + white knights)
- [x] **CHESS-02**: Knight attack pattern generation from any occupied square
- [x] **CHESS-03**: King move generation (8 adjacent squares, edge-aware)
- [x] **CHESS-04**: Legal move filtering — destination not attacked by opponent, not occupied by friendly piece
- [x] **CHESS-05**: Move oracle as `@ql.compile` function producing legal move set for current position

### Manual Quantum Walk Operators

- [x] **WALK-01**: One-hot height register (max_depth+1 qubits) from raw qint with root initialization
- [x] **WALK-02**: Per-level branch registers encoding chosen move index from legal move list
- [x] **WALK-03**: Single local diffusion D_x with Montanaro angles (phi = 2*arctan(sqrt(d)))
- [x] **WALK-04**: Height-controlled diffusion cascade (D_x only activates at correct depth level)
- [x] **WALK-05**: R_A operator composing diffusion at even depths (excluding root)
- [x] **WALK-06**: R_B operator composing diffusion at odd depths plus root
- [x] **WALK-07**: Walk step U = R_B * R_A composed via `@ql.compile`

### Demo Scripts

- [x] **DEMO-01**: demo.py with full manual quantum walk — starting position, legal move tree, walk operators, circuit statistics
- [x] **DEMO-02**: Secondary script using QWalkTree API on same chess position for comparison

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Evaluation

- **EVAL-01**: Piece value evaluation function (material counting)
- **EVAL-02**: Minimax value accumulation across tree depth

### Verification

- **VERIF-01**: Classical Monte Carlo tree walk with coin flips for statistical verification
- **VERIF-02**: Comparison of classical vs quantum tree exploration statistics

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Qiskit simulation of chess circuits | Qubit count far exceeds 17-qubit budget — circuit generation only |
| Full chess rules (castling, en passant, promotion) | Simplified endgame with kings + knights only |
| QWalkTree API modifications | Demo uses existing API as-is for comparison |
| Evaluation function / minimax scoring | Deferred — focus on legal move tree exploration first |
| Monte Carlo classical verification | Deferred to separate phase |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHESS-01 | Phase 103 | Complete |
| CHESS-02 | Phase 103 | Complete |
| CHESS-03 | Phase 103 | Complete |
| CHESS-04 | Phase 103 | Complete |
| CHESS-05 | Phase 103 | Complete |
| WALK-01 | Phase 104 | Complete |
| WALK-02 | Phase 104 | Complete |
| WALK-03 | Phase 104 | Complete |
| WALK-04 | Phase 105 | Complete |
| WALK-05 | Phase 105 | Complete |
| WALK-06 | Phase 105 | Complete |
| WALK-07 | Phase 105 | Complete |
| DEMO-01 | Phase 106 | Complete |
| DEMO-02 | Phase 106 | Complete |

**Coverage:**
- v6.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after roadmap creation -- all 14 requirements mapped to phases 103-106*
