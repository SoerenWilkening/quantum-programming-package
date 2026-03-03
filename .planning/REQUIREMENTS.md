# Requirements: Quantum Assembly

**Defined:** 2026-03-03
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits

## v6.1 Requirements

Requirements for Quantum Chess Demo milestone. Each maps to roadmap phases.

### Chess Board & Legal Moves

- [ ] **CHESS-01**: 8x8 board with piece positions encoded as qarray (2 kings + white knights)
- [ ] **CHESS-02**: Knight attack pattern generation from any occupied square
- [ ] **CHESS-03**: King move generation (8 adjacent squares, edge-aware)
- [ ] **CHESS-04**: Legal move filtering — destination not attacked by opponent, not occupied by friendly piece
- [ ] **CHESS-05**: Move oracle as `@ql.compile` function producing legal move set for current position

### Manual Quantum Walk Operators

- [ ] **WALK-01**: One-hot height register (max_depth+1 qubits) from raw qint with root initialization
- [ ] **WALK-02**: Per-level branch registers encoding chosen move index from legal move list
- [ ] **WALK-03**: Single local diffusion D_x with Montanaro angles (phi = 2*arctan(sqrt(d)))
- [ ] **WALK-04**: Height-controlled diffusion cascade (D_x only activates at correct depth level)
- [ ] **WALK-05**: R_A operator composing diffusion at even depths (excluding root)
- [ ] **WALK-06**: R_B operator composing diffusion at odd depths plus root
- [ ] **WALK-07**: Walk step U = R_B * R_A composed via `@ql.compile`

### Demo Scripts

- [ ] **DEMO-01**: demo.py with full manual quantum walk — starting position, legal move tree, walk operators, circuit statistics
- [ ] **DEMO-02**: Secondary script using QWalkTree API on same chess position for comparison

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
| CHESS-01 | — | Pending |
| CHESS-02 | — | Pending |
| CHESS-03 | — | Pending |
| CHESS-04 | — | Pending |
| CHESS-05 | — | Pending |
| WALK-01 | — | Pending |
| WALK-02 | — | Pending |
| WALK-03 | — | Pending |
| WALK-04 | — | Pending |
| WALK-05 | — | Pending |
| WALK-06 | — | Pending |
| WALK-07 | — | Pending |
| DEMO-01 | — | Pending |
| DEMO-02 | — | Pending |

**Coverage:**
- v6.1 requirements: 14 total
- Mapped to phases: 0
- Unmapped: 14 ⚠️

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after initial definition*
