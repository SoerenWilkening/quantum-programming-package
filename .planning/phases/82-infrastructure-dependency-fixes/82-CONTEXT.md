# Phase 82: Infrastructure & Dependency Fixes - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Measurement tooling and dependency declarations are in place before any code changes begin. This phase establishes pytest-cov infrastructure (Python, Cython, and C), declares the qiskit-aer dependency properly, adds friendly import error handling, and records a coverage baseline. No bug fixes or code changes beyond infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Coverage configuration
- Measure Python (.py), Cython (.pyx), and C backend (.c) code coverage
- No minimum coverage threshold — report only, no build failures on low coverage
- HTML reports generated in `reports/coverage/` (gitignored)
- Exclude from measurement: `tests/*`, `setup.py`, `build_preprocessor.py`, `*_preprocessed.pyx`
- Unified report: merge C coverage (gcov/lcov) into the same HTML report as Python/Cython
- Coverage collection is opt-in via `pytest --cov` flag, not always-on
- C coverage build mode: Claude's discretion on env var vs build flag (follow existing `QUANTUM_PROFILE` pattern)
- Provide a convenience script or Makefile target (e.g., `make coverage`) for the full pipeline: build with coverage flags, run tests, generate unified report

### Dependency extras groups
- `pyproject.toml` is the single source of truth for all dependency metadata
- Remove `extras_require` and `install_requires` from `setup.py` (keep setup.py for Cython build only)
- Keep the extras group named `[verification]`
- Add `qiskit-aer>=0.13` to the `[verification]` group alongside `qiskit>=1.0`
- Coverage tooling deps (pytest-cov, Cython coverage plugin): Claude's discretion on whether to add to `[dev]` or create new `[test]` group

### Import error messages
- Lazy guards: imports succeed, error raised when simulation function is actually called
- Short generic message: "Simulation backend required. Install with: pip install quantum_language[verification]"
- Per-module guards (not a central helper function)
- Guard all qiskit-dependent modules, not just grover + amplitude_estimate
- Create a thin wrapper module at `src/quantum_language/sim_backend.py`
  - Wraps qiskit/qiskit-aer with thin function wrappers (e.g., `sim_backend.simulate(circuit)`)
  - Guards qiskit and qiskit-aer separately (some features may work with just qiskit)
  - Migrate all existing qiskit imports across the codebase to use the wrapper in this phase
- Generic wording (no mention of "qiskit" in error messages) — future-proofs for backend swaps

### Claude's Discretion
- C coverage build mode implementation (env var pattern preferred)
- Coverage tooling extras group placement ([dev] vs [test])
- Exact sim_backend.py function signatures and API surface
- Exact gcov/lcov integration approach for unified reporting
- Convenience script format (Makefile vs shell script)

</decisions>

<specifics>
## Specific Ideas

- "qiskit could also be replaced by other software in the future" — the sim_backend wrapper module should abstract away the specific simulation backend
- Error messages should reference `[verification]` extras group, not qiskit directly
- Follow existing `QUANTUM_PROFILE` env var pattern for C coverage build mode

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

### Baseline Recording
- Record overall coverage %, per-module breakdown, and automatically identified critical untested paths
- Include timestamp and git commit hash for traceability
- Manual baseline recording (coverage script generates reports, recording baseline is a separate explicit step)
- Automated gap identification: script parses coverage data to find uncovered functions/methods in critical modules
- Recording location: Claude's discretion

---

*Phase: 82-infrastructure-dependency-fixes*
*Context gathered: 2026-02-22*
