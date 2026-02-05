# Requirements: Quantum Assembly v2.2 Performance Optimization

**Defined:** 2026-02-05
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v2.2 Requirements

Requirements for performance optimization milestone.

### Profiling Infrastructure

- [ ] **PROF-01**: Python function profiling with cProfile integration
- [ ] **PROF-02**: Memory profiling for C extensions via memray
- [ ] **PROF-03**: Cython annotation HTML generation (`cython -a`)
- [ ] **PROF-04**: Cross-layer profiling via py-spy with `--native`
- [ ] **PROF-05**: `ql.profile()` context manager for inline profiling
- [ ] **PROF-06**: Benchmark suite with pytest-benchmark fixtures
- [ ] **PROF-07**: Profiling dependencies as optional `[profiling]` extra

### Compiler Bug Fix

- [ ] **FIX-01**: Investigate f() vs f.inverse() depth discrepancy
- [ ] **FIX-02**: Fix forward compilation path to match inverse optimization

### Cython Optimization

- [ ] **CYT-01**: Complete static typing in hot path functions
- [ ] **CYT-02**: Add compiler directives (boundscheck=False, wraparound=False)
- [ ] **CYT-03**: Convert array parameters to memory views where applicable
- [ ] **CYT-04**: Add nogil sections where call paths are Python-free

### Hardcoded Gate Sequences

- [ ] **HCS-01**: Pre-computed addition sequences for 1-4 bit widths
- [ ] **HCS-02**: Pre-computed addition sequences for 5-8 bit widths
- [ ] **HCS-03**: Pre-computed addition sequences for 9-12 bit widths
- [ ] **HCS-04**: Pre-computed addition sequences for 13-16 bit widths
- [ ] **HCS-05**: Validation tests comparing hardcoded vs dynamic generation
- [ ] **HCS-06**: Automatic fallback to dynamic for widths > 16

### C Hot Path Migration (Conditional)

- [ ] **MIG-01**: Identify top 3 hot paths via profiling
- [ ] **MIG-02**: Migrate identified hot paths to C (if profiling shows >20% benefit)
- [ ] **MIG-03**: Eliminate run_instruction() overhead for migrated operations

### Memory Optimization (Conditional)

- [ ] **MEM-01**: Profile malloc patterns in gate creation paths
- [ ] **MEM-02**: Reduce malloc in inject_remapped_gates (if profiled as bottleneck)
- [ ] **MEM-03**: Implement object pooling for gate_t (if profiled as beneficial)

## Future Requirements

Deferred to later milestones.

### Advanced Optimization

- **ADV-OPT-01**: Hardcoded sequences for multiplication
- **ADV-OPT-02**: Hardcoded sequences for controlled operations (cQQ_add, cCQ_add)
- **ADV-OPT-03**: SIMD vectorization for bulk gate operations
- **ADV-OPT-04**: Multi-threaded circuit building

## Out of Scope

| Feature | Reason |
|---------|--------|
| LTO (Link-Time Optimization) | Known GCC bug causes issues; disabled |
| Global nogil without analysis | Risk of Python callbacks; needs per-function verification |
| Python 3.12+ Cython profiling | PEP-669 breaks Cython profiling; use 3.11 |
| Micro-optimization without profiling | Anti-pattern; must measure first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROF-01 | Phase 55 | Pending |
| PROF-02 | Phase 55 | Pending |
| PROF-03 | Phase 55 | Pending |
| PROF-04 | Phase 55 | Pending |
| PROF-05 | Phase 55 | Pending |
| PROF-06 | Phase 55 | Pending |
| PROF-07 | Phase 55 | Pending |
| FIX-01 | Phase 56 | Pending |
| FIX-02 | Phase 56 | Pending |
| CYT-01 | Phase 57 | Pending |
| CYT-02 | Phase 57 | Pending |
| CYT-03 | Phase 57 | Pending |
| CYT-04 | Phase 57 | Pending |
| HCS-01 | Phase 58 | Pending |
| HCS-02 | Phase 58 | Pending |
| HCS-03 | Phase 59 | Pending |
| HCS-04 | Phase 59 | Pending |
| HCS-05 | Phase 58 | Pending |
| HCS-06 | Phase 58 | Pending |
| MIG-01 | Phase 60 | Pending |
| MIG-02 | Phase 60 | Pending |
| MIG-03 | Phase 60 | Pending |
| MEM-01 | Phase 61 | Pending |
| MEM-02 | Phase 61 | Pending |
| MEM-03 | Phase 61 | Pending |

**Coverage:**
- v2.2 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-02-05*
*Last updated: 2026-02-05 after roadmap creation*
