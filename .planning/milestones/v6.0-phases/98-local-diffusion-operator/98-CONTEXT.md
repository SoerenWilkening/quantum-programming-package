# Phase 98: Local Diffusion Operator - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the local diffusion operator D_x for any tree node with verified-correct amplitude coefficients per Montanaro 2015 Section 2. Covers uniform branching (any degree d), root special case, height-controlled dispatch, and statevector verification. Variable per-node branching is Phase 100. Walk operators (R_A, R_B composition) are Phase 99.

</domain>

<decisions>
## Implementation Decisions

### Diffusion Circuit Structure
- Ry rotation approach: use Ry(phi) where phi = 2*arctan(sqrt(d)) to split parent/children amplitude
- Controlled-Ry cascade for exact child amplitude distribution (supports arbitrary d, not just power-of-2)
- D_x implemented as reflection: U†(map |psi_x> to |0>), then S_0 reflection, then U
- Reuse existing Grover S_0 reflection from `diffusion.py` (`ql.diffusion()` X-MCZ-X pattern) for the reflection step
- Support all uniform branching degrees from the start (d=2,3,4,5... not restricted to power-of-2)
- D_x acts on height register + branch register together: transitions h[k] → h[k-1] and superimposes across branch register at that level
- Use @ql.compile controlled infrastructure for the controlled-Ry cascade (framework auto-derives controlled variants)

### Height-Controlled Dispatch
- Explicit depth parameter: `tree.local_diffusion(depth=k)` where h[k]=|1> means node at depth k
- D_x internally controlled on height qubit h[k] — calling at wrong depth is a no-op (safe for walk operator loops)
- Root special case handled inside the same local_diffusion() method (not a separate function): detects depth=max_depth and applies Montanaro's exact root reflection formula (no parent edge, only children superposition)
- Paper's exact root formula: D_root = 2|psi_root><psi_root| - I where |psi_root> is uniform over children only
- All-depths single pass: walk operators (Phase 99) call local_diffusion(depth=k) for each k in a loop; h[k] control makes irrelevant calls no-ops
- Explicit skip at depth 0 (leaf nodes): return immediately, no gates emitted
- Branch register mapping: D_x(depth=k) operates on `branch_registers[max_depth - k]`
- Per-level branching supported: branching[i] determines angles for that tree level

### Angle Precomputation
- All diffusion rotation angles precomputed eagerly at QWalkTree construction time
- Per-depth angle arrays stored privately on QWalkTree (one set of angles per depth level)
- Computation happens in `_setup_diffusion()` private helper called from `__init__` (same pattern as `_validate_predicate()`)

### API & Module Placement
- Method on QWalkTree: `tree.local_diffusion(depth=k)` — not a standalone function
- Private angle storage with debug accessor: `tree.diffusion_info(depth)` returns angles and formula for inspection
- No top-level ql namespace export — method-only access via tree instance
- Runtime depth validation: raises ValueError for out-of-bounds depth with clear error message

### Claude's Discretion
- Exact controlled-Ry cascade decomposition (how to split d-way amplitude with Ry chain)
- Internal angle storage data structure (dict vs list of tuples)
- `_setup_diffusion()` implementation details
- `diffusion_info()` return format
- How S_0 reflection from diffusion.py is invoked within D_x circuit
- Gate ordering within the reflection pattern
- Error message wording

</decisions>

<specifics>
## Specific Ideas

- The controlled-Ry cascade for d children uses angles like Ry(2*arctan(sqrt(1/d))), Ry(2*arctan(sqrt(1/(d-1)))), etc. to split amplitude exactly d ways
- Height register is one-hot: root at h[max_depth], leaves at h[0]
- D_x² = I (reflection property) should be verifiable via statevector
- The height register serves as a quantum depth marker because the walk state is in superposition over multiple depths simultaneously — classical depth tracking is impossible after multiple walk steps

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `emit_ry(target, angle)` in `_gates.pyx`: single-qubit Ry rotation primitive — used for parent/children amplitude split
- `ql.diffusion()` in `diffusion.py`: Grover S_0 reflection (X-MCZ-X pattern) — reused for the reflection step inside D_x
- `@ql.compile` in `compile.py`: auto-derives controlled gate variants, caching, adjoint replay — used for the controlled-Ry cascade
- `_collect_qubits()` in `diffusion.py`: extracts physical qubit indices from registers — may be useful for D_x qubit targeting
- `emit_h`, `emit_x`, `emit_z`, `emit_mcz` in `_gates.pyx`: basic gate primitives available

### Established Patterns
- QWalkTree uses eager register allocation at construction (height + branch registers allocated in `__init__`)
- Private setup helpers called from `__init__`: `_validate_predicate()` pattern exists, `_setup_diffusion()` follows same pattern
- Qiskit statevector verification via `_simulate_statevector()` helper in test files
- Tests organized by requirement groups in separate classes (TestQWalkTreeEncoding, TestRootStatePreparation, TestQubitBudget)

### Integration Points
- `QWalkTree.__init__` needs new `_setup_diffusion()` call after register allocation
- `tree.local_diffusion(depth)` is the entry point for Phase 99 walk operators (R_A, R_B)
- Branch register index mapping: `branch_registers[max_depth - depth]` for depth k
- Predicate accept/reject qbools (`tree._accept`, `tree._reject`) stored from Phase 97 — not used by D_x but will be by walk operators

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 98-local-diffusion-operator*
*Context gathered: 2026-03-02*
