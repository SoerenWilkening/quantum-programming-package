# Phase 80: Deferred Items

## Out-of-Scope Discoveries

### BUG-CMP-MSB: Inequality comparison operators access qubit index 63

- **Found during:** Plan 02, Task 2 (test creation)
- **Issue:** `qint.__lt__`, `__gt__`, `__le__`, `__ge__` operators access `msb = temp_self[63]` or `msb = temp_other[63]`, which causes `IndexError: qubit index 63 out of range for qint with width N` when used in fault-tolerant mode with small-width qints (width < 64).
- **Impact:** Lambda predicate synthesis with inequality comparisons (e.g., `lambda x: x > 5`) fails at runtime when the oracle is actually invoked (j >= 1 Grover iterations). Only `==` and `!=` work correctly.
- **Workaround:** Tests use `==` and `!=` predicates only. Users can use decorated oracles with `@ql.grover_oracle` for inequality predicates.
- **Pre-existing:** This is not caused by Phase 80 changes. The bug exists in `qint_preprocessed.pyx` comparison operators.
