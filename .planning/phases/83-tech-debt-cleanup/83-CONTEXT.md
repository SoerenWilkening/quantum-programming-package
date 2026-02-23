# Phase 83: Tech Debt Cleanup - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Dead code is removed, preprocessor automation prevents drift, and sequence generation is documented. Covers: removing QPU.c/QPU.h stubs and all supporting code, automating qint_preprocessed.pyx drift detection via pre-commit hook, removing vulture-identified dead Python code, and documenting hardcoded sequence regeneration.

</domain>

<decisions>
## Implementation Decisions

### QPU removal strategy
- Full cleanup: remove QPU.c, QPU.h, all #include/import lines, AND any functions/code that existed solely to support QPU functionality
- Fix compile errors inline as part of the removal — don't flag for manual review
- Clean up build config too: remove QPU references from Makefiles, CMakeLists, CI workflows, and any other build scripts
- Verification: compile check is sufficient; full test suite not required during removal (tests run separately)

### Preprocessor drift check
- Claude's Discretion on detection approach (regenerate-and-diff vs checksum — pick most reliable and lowest friction)
- On drift detection: auto-fix and stage — regenerate the .pyx file automatically and stage it so the commit includes the fix
- Pre-commit hook only, no CI check needed
- Use pre-commit framework (.pre-commit-config.yaml), not a standalone script

### Dead code removal scope
- Claude's Discretion on borderline confidence cases (80-89%) — examine each and make the call
- If supposedly dead code turns out to be needed: remove it, and if tests break, restore it and add a comment explaining why it's needed
- Scan production code only: python-backend/ and src/ directories (skip tests, scripts, tooling)
- One-time cleanup: don't persist vulture config to the repo

### Sequence generation docs
- Documentation lives inline in the generator script: docstring/comments at top, plus a --help flag
- Quick reference style: one-liner command to regenerate, plus a note on when you'd need to
- Clean up the generator script too: improve arg parsing, clearer output, make it more user-friendly
- Add a Makefile target (e.g., `make generate-sequences`) so developers don't need to remember the exact command

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 83-tech-debt-cleanup*
*Context gathered: 2026-02-23*
