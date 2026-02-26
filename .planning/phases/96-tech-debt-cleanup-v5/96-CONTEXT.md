# Phase 96: v5.0 Tech Debt Cleanup - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Address tech debt items identified by the v5.0 milestone audit that don't block closure but improve code health. Covers dead code removal, qubit accounting test gap closure, and known limitation documentation. No new features or capability additions.

</domain>

<decisions>
## Implementation Decisions

### Dead code disposition
- Remove all dead declarations and imports completely — no stubs
- `toffoli_mod_reduce` declaration in `_core.pxd`: clean removal
- `toffoli_cdivmod_cq` and `toffoli_cdivmod_qq` imports: clean removal
- If needed later, recover from git history

### Qubit accounting test scope
- Test all modular operations, not just FIX-03 related ops
- Use no-leak check pattern: verify `circuit_stats()['current_in_use']` returns to expected value after each operation
- Avoid brittle exact-count assertions — focus on regression detection

### Ancilla leak documentation
- Document QQ division ancilla leak in all three locations:
  - Inline code comment at the QQ division implementation
  - GitHub issue as tracking issue with details and potential fix approaches
  - Project-level known issues/limitations document

### Claude's Discretion
- Exact GitHub issue format and labels
- Which known issues doc to use or whether to create one
- Specific modular operations to include in qubit accounting tests (all that exist)
- Order of cleanup operations

</decisions>

<specifics>
## Specific Ideas

No specific requirements — straightforward tech debt cleanup guided by milestone audit findings.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 96-tech-debt-cleanup-v5*
*Context gathered: 2026-02-26*
