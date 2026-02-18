# Phase 73: Toffoli CQ/cCQ Classical-Bit Gate Reduction - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Reduce T-gate count in CQ (classical+quantum) and cCQ (controlled classical+quantum) Toffoli arithmetic by writing inline generators that exploit known classical bit values to simplify gates. Applies to both CDKM ripple-carry and BK CLA adder paths. The temp register is still required (carries need physical qubits during MAJ phase), but X-init/cleanup gates are folded into the CDKM/CLA gate sequences, and gates controlled on known-0 bits are eliminated while gates controlled on known-1 bits are simplified (CCX→CX).

</domain>

<decisions>
## Implementation Decisions

### Simplification approach
- Inline CQ generator: write CQ-specific MAJ/UMA emitters that take the classical bit value as a parameter and emit simplified gates directly
- Static simplification only: use known initial classical bit values (0 or 1) to simplify; do NOT propagate classical state dynamically through the MAJ chain
- Inline cCQ generator: same approach for controlled variants, folding classical bits into the controlled MAJ/UMA chain (saves CX-init/cleanup gates)
- Separate generators for CDKM and CLA (BK) — no shared simplification logic
- Replace old temp-register CQ/cCQ code entirely once inline version passes tests (no fallback)

### Qubit layout
- Keep identical layout: [0..N-1] temp, [N..2N-1] self, [2N] carry for CQ; [2N+1] control for cCQ
- No Python-side changes needed — only the gates emitted on existing qubit positions change
- Add #ifdef DEBUG assertion that temp register qubits are |0> after inline CQ completes

### Caching & hardcoding
- No caching for inline CQ sequences (value space too large, generator is fast)
- Hardcode CQ and cCQ sequences for value=1 (increment) at widths 1-8
- No generation script changes — hardcoded value=1 sequences written directly in C
- QQ/cQQ caching and hardcoding unchanged

### Scope of operations
- CDKM CQ/cCQ: inline generators (primary target)
- CLA BK CQ/cCQ: separate inline generators (also in this phase)
- CQ multiplication: automatically benefits via inline CQ adder calls (no mul-specific changes)
- Division/modulo: verify T-count improvement propagates (no div-specific changes)

### Verification
- Standalone exhaustive tests against expected arithmetic results (widths 1-4)
- Gate count comparison: verify new CQ sequences have fewer CCX gates than old approach
- T-count reporting verification for CQ operations

</decisions>

<specifics>
## Specific Ideas

- The savings are modest (primarily eliminating 2*popcount(value) X-init/cleanup gates and simplifying first-touch gates) but important for fault-tolerant T-gate budgets
- CDKM preserves the a-register (UMA restores it), so temp register cleanup is guaranteed
- CLA is worse: carry-copy ancilla NOT fully uncomputed (forward-only BK pattern)

</specifics>

<deferred>
## Deferred Ideas

- **MCX(3+ controls) decomposition in controlled operations** — Generalize Phase 72-03's AND-ancilla approach from multiplication to all cQQ/cCQ addition. Currently cMAJ/cUMA emit MCX(3 controls) which aren't directly executable. Future phase.
- **CCX-to-native gate decomposition** — CCX → 6 CNOT + 7 T gates for hardware execution. This is a compilation/transpilation concern, separate from arithmetic optimization. Future phase.

</deferred>

---

*Phase: 73-toffoli-cq-ccq-classical-bit-gate-reduction*
*Context gathered: 2026-02-17*
