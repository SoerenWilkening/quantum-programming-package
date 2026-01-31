# Phase 31: Comparison Verification - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Exhaustively verify all six comparison operators (==, !=, <, >, <=, >=) across qint-vs-int (CQ) and qint-vs-qint (QQ) variants through the full pipeline (Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check). This phase verifies existing behavior — no new operators or comparison features are added.

</domain>

<decisions>
## Implementation Decisions

### Result extraction
- Comparison result is expected to land in a dedicated ancilla qubit — use existing `verify_circuit` framework to extract the boolean from the bitstring
- No new comparison helper needed — reuse the existing verification framework
- Tests must verify BOTH the boolean comparison result AND that input operands are preserved (not corrupted) after comparison
- Add explicit BUG-02 regression tests: grouped as a single regression suite with sub-cases for MSB index, GC gate reversal, and unsigned overflow root causes

### Edge case strategy
- Use Python's native comparison operators (==, !=, <, >, <=, >=) as the oracle for expected values
- Exhaustive coverage at 1-4 bits naturally includes all boundary cases (0, max, equal values, symmetric pairs) — no need for separately named boundary or symmetry tests
- Exhaustive pairs implicitly cover all orderings

### Bug handling
- New comparison bugs discovered during verification: mark as xfail with BUG-CMP-XX IDs, keep suite green
- xfail strictness: Claude's discretion (follow Phase 30 precedent)
- New bugs documented in BOTH STATE.md (project visibility) AND test file xfail markers
- BUG-02 regression tests grouped as a single suite with sub-cases per root cause

### Width & variant coverage
- Exhaustive: 1-4 bit widths (all input pairs × all 6 operators)
- Sampled at 5-8 bits: boundary pairs (0,0), (0,max), (max,0), (max,max) plus ~10 random pairs per width
- CQ and QQ variants get equal coverage — both use different circuit paths and deserve the same treatment
- Signed comparisons: Claude should investigate whether signed comparison paths exist in the codebase and include them if found

### Claude's Discretion
- Whether to test all 6 operators per (a,b) pair in one test or separately — pick most efficient approach
- xfail strict vs non-strict — follow Phase 30 precedent
- Exact number of random sample pairs for 5-8 bit widths
- Test file organization and naming conventions

</decisions>

<specifics>
## Specific Ideas

- Follow Phase 30's proven pattern: exhaustive at small widths, sampled at larger widths
- BUG-02 was a multi-root-cause bug (MSB index, GC gate reversal, unsigned overflow) — regression suite should make each root cause visible as a sub-case
- Operand preservation check ensures comparisons don't have side effects on quantum registers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-comparison-verification*
*Context gathered: 2026-01-31*
