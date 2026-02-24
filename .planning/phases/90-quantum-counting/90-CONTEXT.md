# Phase 90: Quantum Counting - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can estimate the number of solutions to a search problem via quantum counting. Provides `ql.count_solutions(oracle, width=n)` that wraps existing IQAE to convert amplitude estimate → integer solution count with a `CountResult` object. Requirements: CNT-01, CNT-02, CNT-03.

</domain>

<decisions>
## Implementation Decisions

### API calling convention
- Mirror `amplitude_estimate()` signature: `count_solutions(oracle, *registers, width=, widths=, epsilon=, confidence_level=, max_iterations=, predicate=)`
- `epsilon` controls amplitude precision (pass through to IQAE directly), not a separate count precision parameter
- `max_iterations` exposed as oracle call cap, same as `amplitude_estimate()`
- Top-level `ql.count_solutions()` function exported from `__init__.py`

### CountResult design
- Int-like behavior: `int(result)` returns `.count`, arithmetic operators work, `result == 3` works
- `.count` = rounded integer (the discrete solution count)
- `.estimate` = raw float (unrounded `N * amplitude` for precise analysis)
- `.count_interval` = `(floor(N * a_low), ceil(N * a_high))` — conservative integer bounds from amplitude confidence interval
- `.search_space` = `N` as integer (`2^width`), no separate `.width` property
- `.num_oracle_calls` = total oracle calls from IQAE

### Rounding strategy
- `.count` uses `round(N * amplitude)` clamped to `[0, N]`
- Zero is a valid count — `.count = 0` with no special case or sentinel
- Simple and predictable edge case handling

### Oracle compatibility
- Identical oracle support to `grover()` and `amplitude_estimate()`: `@grover_oracle` decorated, lambda predicates, explicit qint registers
- Decorated oracles require `predicate=` kwarg for classical verification (same as `amplitude_estimate()`)
- Same qubit-budget warnings when register width > 14 qubits (approaching 17-qubit simulator limit)

### Claude's Discretion
- Whether `count_solutions` lives in its own module (`quantum_counting.py`) or in `amplitude_estimation.py`
- Internal implementation details of the amplitude-to-count conversion
- Test structure and verification approach for M=1, M=2, M=3 known-M oracles
- `repr` format for CountResult
- scipy dependency declaration approach in pyproject.toml

</decisions>

<specifics>
## Specific Ideas

- CountResult should feel like AmplitudeEstimationResult's integer counterpart — same design pattern (wrapper with arithmetic operators) but for counts instead of probabilities
- The function is a thin semantic layer over existing IQAE, not a new algorithm implementation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 90-quantum-counting*
*Context gathered: 2026-02-24*
