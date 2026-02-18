# Phase 21: Package Restructuring - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize the codebase from large Cython files into a maintainable package structure. Split files so no single Cython file exceeds ~300 lines. Create proper `import quantum_language` structure with accessible submodules. All existing tests must pass without modification (beyond import updates).

</domain>

<decisions>
## Implementation Decisions

### Module Organization
- Split by type: separate modules for qint, qbool, qfixed, etc. — each type owns its operations
- Shared utilities (circuit building, qubit management) in a separate `_core` module
- State management (QPU state, uncomputation) gets its own subpackage: `quantum_language.state`
- Cross-type operations: Claude decides placement based on minimizing circular imports

### Naming Conventions
- Top-level package name: `quantum_language` (users import as `import quantum_language as ql`)
- Internal/private modules use single underscore prefix: `_core`, `_utils`, `_circuit`
- Type modules match class names in lowercase: `qint.pyx` contains `class qint`, `qbool.pyx` contains `class qbool`
- State subpackage module naming: Claude decides clear, consistent names

### API Surface
- Top level exposes types only: `ql.qint`, `ql.qbool`, `ql.qfixed`
- Quantum gates are internal implementation details — not user-facing API
- State management requires submodule import: `from quantum_language.state import ...` or `ql.state.X()`
- `__all__` enforcement: Claude decides based on Python best practices

### Migration Approach
- Hard break: old imports stop working immediately — update all at once
- Tests migrated alongside restructuring in the same phase
- Build system updates: Claude decides based on current setup (update existing vs fresh pyproject.toml)
- Currently sole user, but design as if potential future users exist

### Claude's Discretion
- Cross-type operation placement (minimize circular imports)
- State subpackage module names
- `__all__` enforcement strategy
- Build system approach (modify existing vs create fresh)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches that follow the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 21-package-restructuring*
*Context gathered: 2026-01-29*
