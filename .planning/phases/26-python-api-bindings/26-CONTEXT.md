# Phase 26: Python API Bindings - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose the C backend's OpenQASM 3.0 export to Python via Cython. Users call `ql.to_openqasm()` to get a complete OpenQASM string from their current circuit. Optional verification dependencies available via extras_require. File-based export and circuit methods are out of scope.

</domain>

<decisions>
## Implementation Decisions

### API surface design
- Function name: `to_openqasm()` — explicit, matches C-level naming
- No parameters — exports current circuit as-is
- Module-level only — `ql.to_openqasm()`, no circuit method
- Returns full valid OpenQASM 3.0 string (header, declarations, gates) — ready to paste into a simulator

### Error behavior
- Raise `RuntimeError` if no circuit exists (no gates applied)
- Raise `RuntimeError` if C backend returns NULL (generic, don't assume cause)
- Simple error messages — just "Failed to export circuit to OpenQASM", no circuit state details
- No measurement validation — export whatever state exists, user may want intermediate inspection

### Integration with existing API
- Cython wrapper lives in new `openqasm.pyx` module — separate from _core.pyx
- Re-export from `__init__.py` — `ql.to_openqasm()` available at package level
- Clean name only — no exposure of legacy `to_opanqasm()` typo at Python level
- Added to `__all__` in `__init__.py` — explicit public API declaration

### Optional dependencies
- `to_openqasm()` works with base package only — no extras required for export
- Verification extras key: `[verification]` — `pip install quantum-assembly[verification]`
- Minimum version constraints for Qiskit (e.g., `qiskit>=1.0`) — flexible, avoids conflicts
- Lazy import for Qiskit — only imported when verification functions are called, no impact on base usage

### Claude's Discretion
- Cython memory management pattern for C string buffer (malloc/free in finally block)
- openqasm.pxd declaration file structure
- setup.py Extension configuration for new module
- Test structure for the wrapper

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for Cython wrapping and module structure.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-python-api-bindings*
*Context gathered: 2026-01-30*
