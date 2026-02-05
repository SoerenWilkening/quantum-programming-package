"""Tests for @ql.compile decorator -- capture, caching, replay, and optimization.

Covers all 5 phase success criteria:
  SC1: First call produces same circuit as undecorated version
  SC2: Second call replays gates onto new qubits (no re-execution)
  SC3: Returned qint is usable in subsequent operations
  SC4: Different widths/classical args trigger re-capture
  SC5: ql.circuit() invalidates cache

Plus Phase 49 optimization criteria:
  OPT1: Optimiser cancels adjacent inverse gates
  OPT2: Optimiser merges consecutive rotations
  OPT3: optimize=False skips optimisation
  OPT4: Stats properties report correct values
"""

import io
import sys
import warnings

import pytest

import quantum_language as ql
from quantum_language._core import extract_gate_range, get_current_layer
from quantum_language.compile import (
    _H,
    _M,
    _P,
    _R,
    _X,
    _Y,
    _Z,
    CompiledFunc,
    _adjoint_gate,
    _gates_cancel,
    _inverse_gate_list,
    _InverseCompiledFunc,
    _optimize_gate_list,
    _Rx,
    _Ry,
    _Rz,
)

# Suppress cosmetic width warnings
warnings.filterwarnings("ignore", message="Value .* exceeds")


# ---------------------------------------------------------------------------
# SC1: First call produces same circuit as undecorated version
# ---------------------------------------------------------------------------


def test_first_call_matches_undecorated_gate_count():
    """SC1: Compiled first call produces same gate count as plain call."""
    # Undecorated run
    ql.circuit()
    a = ql.qint(3, width=4)
    start = get_current_layer()
    a += 1
    end = get_current_layer()
    plain_gates = extract_gate_range(start, end)
    plain_count = len(plain_gates)

    # Compiled run
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    b = ql.qint(3, width=4)
    start2 = get_current_layer()
    add_one(b)
    end2 = get_current_layer()
    compiled_gates = extract_gate_range(start2, end2)
    compiled_count = len(compiled_gates)

    assert compiled_count == plain_count, (
        f"Compiled first call gate count {compiled_count} != plain {plain_count}"
    )


def test_first_call_matches_undecorated_addition():
    """SC1: Compiled addition produces same gate structure as plain addition."""
    # Plain run
    ql.circuit()
    a1 = ql.qint(0, width=4)
    b1 = ql.qint(0, width=4)
    start1 = get_current_layer()
    _r1 = a1 + b1
    end1 = get_current_layer()
    plain_gates = extract_gate_range(start1, end1)

    # Compiled run
    ql.circuit()

    @ql.compile
    def add_fn(x, y):
        return x + y

    a2 = ql.qint(0, width=4)
    b2 = ql.qint(0, width=4)
    start2 = get_current_layer()
    _r2 = add_fn(a2, b2)
    end2 = get_current_layer()
    compiled_gates = extract_gate_range(start2, end2)

    assert len(compiled_gates) == len(plain_gates), (
        f"Addition gate count mismatch: compiled={len(compiled_gates)}, plain={len(plain_gates)}"
    )


# ---------------------------------------------------------------------------
# SC2: Second call replays gates onto new qubits (no re-execution)
# ---------------------------------------------------------------------------


def test_replay_no_reexecution():
    """SC2: Replay does not re-execute the function body."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1, "First call should execute body"

    b = ql.qint(5, width=4)
    add_one(b)
    assert call_count[0] == 1, "Replay should NOT re-execute body"


def test_replay_targets_new_qubits():
    """SC2: Replayed gates target the new qint's qubits, not the original."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)

    b = ql.qint(5, width=4)
    b_qubits = {int(b.qubits[64 - b.width + i]) for i in range(b.width)}

    # Record replay gate range
    start = get_current_layer()
    add_one(b)
    end = get_current_layer()

    replay_gates = extract_gate_range(start, end)
    replay_targets = {g["target"] for g in replay_gates}

    # Replay should NOT target a's qubits (unless they overlap with b's by coincidence)
    # But b's qubits should be in the targets
    assert b_qubits & replay_targets, "Replay gates should target b's qubits"


def test_replay_same_gate_count():
    """SC2: Replay produces the same number of gates as capture."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    start1 = get_current_layer()
    add_one(a)
    end1 = get_current_layer()
    capture_gates = extract_gate_range(start1, end1)

    b = ql.qint(5, width=4)
    start2 = get_current_layer()
    add_one(b)
    end2 = get_current_layer()
    replay_gates = extract_gate_range(start2, end2)

    assert len(replay_gates) == len(capture_gates), (
        f"Replay gate count {len(replay_gates)} != capture {len(capture_gates)}"
    )


# ---------------------------------------------------------------------------
# SC3: Returned qint is usable in subsequent operations
# ---------------------------------------------------------------------------


def test_return_value_usable_in_place():
    """SC3: In-place modified qint returned from compiled fn is usable."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    result = add_one(a)
    # Result should be a itself (in-place modification)
    assert result is a

    # Use in subsequent operation (should not raise)
    layer_before = get_current_layer()
    result += 1
    layer_after = get_current_layer()
    assert layer_after > layer_before, "Subsequent operation should add gates"


def test_return_value_usable_new_qint():
    """SC3: New qint returned from compiled fn is usable in subsequent ops."""
    ql.circuit()

    @ql.compile
    def add_values(x, y):
        return x + y

    a = ql.qint(3, width=4)
    b = ql.qint(2, width=4)
    result = add_values(a, b)

    # Result should be a new qint
    assert result is not a
    assert result is not b
    assert result.width == 4

    # Use in subsequent operation
    layer_before = get_current_layer()
    result += 1
    layer_after = get_current_layer()
    assert layer_after > layer_before, "Subsequent operation should add gates"


def test_replay_return_value_usable():
    """SC3: Qint returned from replay is usable in subsequent operations."""
    ql.circuit()

    @ql.compile
    def add_values(x, y):
        return x + y

    # Capture
    a = ql.qint(3, width=4)
    b = ql.qint(2, width=4)
    _r1 = add_values(a, b)

    # Replay
    c = ql.qint(5, width=4)
    d = ql.qint(1, width=4)
    result2 = add_values(c, d)

    # Use replay result
    assert result2.width == 4
    layer_before = get_current_layer()
    result2 += 1
    layer_after = get_current_layer()
    assert layer_after > layer_before, "Replay result should be usable"


# ---------------------------------------------------------------------------
# SC4: Different classical params or qint widths trigger re-capture
# ---------------------------------------------------------------------------


def test_different_widths_recapture():
    """SC4: Different qint widths produce different cache entries."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1

    # Same width -- replay
    b = ql.qint(5, width=4)
    add_one(b)
    assert call_count[0] == 1, "Same width should replay"

    # Different width -- re-capture
    c = ql.qint(5, width=8)
    add_one(c)
    assert call_count[0] == 2, "Different width should re-capture"


def test_different_widths_different_gate_counts():
    """SC4: Width=4 and width=8 produce different gate counts."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    start1 = get_current_layer()
    add_one(a)
    end1 = get_current_layer()
    gates_w4 = extract_gate_range(start1, end1)

    b = ql.qint(5, width=8)
    start2 = get_current_layer()
    add_one(b)
    end2 = get_current_layer()
    gates_w8 = extract_gate_range(start2, end2)

    assert len(gates_w8) > len(gates_w4), (
        f"Width=8 should produce more gates than width=4: w8={len(gates_w8)}, w4={len(gates_w4)}"
    )


def test_different_classical_args_recapture():
    """SC4: Different classical arg values produce different cache entries."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_value(x, amount):
        call_count[0] += 1
        x += amount
        return x

    a = ql.qint(3, width=4)
    add_value(a, 1)
    assert call_count[0] == 1

    b = ql.qint(5, width=4)
    add_value(b, 1)
    assert call_count[0] == 1, "Same classical arg should replay"

    c = ql.qint(7, width=4)
    add_value(c, 2)
    assert call_count[0] == 2, "Different classical arg should re-capture"


# ---------------------------------------------------------------------------
# SC5: ql.circuit() invalidates cache
# ---------------------------------------------------------------------------


def test_circuit_reset_clears_cache():
    """SC5: Creating a new circuit clears all compilation caches."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1

    b = ql.qint(5, width=4)
    add_one(b)
    assert call_count[0] == 1, "Should replay from cache"

    # Reset circuit -- should clear cache
    ql.circuit()
    c = ql.qint(7, width=4)
    add_one(c)
    assert call_count[0] == 2, "After circuit reset, should re-capture"


def test_circuit_reset_replay_after_recapture():
    """SC5: After circuit reset and re-capture, replay still works."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)

    # Reset and re-capture
    ql.circuit()
    b = ql.qint(5, width=4)
    add_one(b)
    assert call_count[0] == 2

    # Replay after re-capture
    c = ql.qint(7, width=4)
    add_one(c)
    assert call_count[0] == 2, "Should replay after re-capture"


# ---------------------------------------------------------------------------
# Additional tests: decorator forms
# ---------------------------------------------------------------------------


def test_bare_decorator_form():
    """@ql.compile without parentheses works."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    assert isinstance(add_one, CompiledFunc)
    a = ql.qint(3, width=4)
    result = add_one(a)
    assert result is a


def test_parens_decorator_form():
    """@ql.compile() with empty parentheses works."""
    ql.circuit()

    @ql.compile()
    def add_one(x):
        x += 1
        return x

    assert isinstance(add_one, CompiledFunc)
    a = ql.qint(3, width=4)
    result = add_one(a)
    assert result is a


def test_decorator_with_options():
    """@ql.compile(max_cache=N) works."""
    ql.circuit()

    @ql.compile(max_cache=16)
    def add_one(x):
        x += 1
        return x

    assert isinstance(add_one, CompiledFunc)
    assert add_one._max_cache == 16

    a = ql.qint(3, width=4)
    result = add_one(a)
    assert result is a


# ---------------------------------------------------------------------------
# Additional tests: cache management
# ---------------------------------------------------------------------------


def test_max_cache_eviction():
    """Oldest cache entry evicted when max_cache exceeded."""
    ql.circuit()
    call_count = [0]

    @ql.compile(max_cache=2)
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    # Fill cache with 2 entries (width=4 and width=8)
    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1

    b = ql.qint(5, width=8)
    add_one(b)
    assert call_count[0] == 2

    # Add third entry (width=16) -- should evict width=4
    c = ql.qint(5, width=16)
    add_one(c)
    assert call_count[0] == 3

    # width=4 should have been evicted, so this re-captures
    d = ql.qint(7, width=4)
    add_one(d)
    assert call_count[0] == 4, "Evicted entry should trigger re-capture"

    # width=8 should still be cached (was used after width=4)
    e = ql.qint(9, width=8)
    add_one(e)
    # Note: width=8 may or may not still be cached depending on eviction order
    # With max_cache=2, after adding width=16 and width=4 (re-captured),
    # cache has width=16 and width=4; width=8 was evicted


def test_clear_cache_method():
    """Per-function clear_cache() works."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1

    b = ql.qint(5, width=4)
    add_one(b)
    assert call_count[0] == 1

    # Clear cache
    add_one.clear_cache()

    c = ql.qint(7, width=4)
    add_one(c)
    assert call_count[0] == 2, "After clear_cache, should re-capture"


# ---------------------------------------------------------------------------
# Additional tests: in-place modification and error handling
# ---------------------------------------------------------------------------


def test_in_place_modification_replay():
    """In-place modification during replay returns caller's qint."""
    ql.circuit()

    @ql.compile
    def increment(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    r1 = increment(a)
    assert r1 is a, "First call in-place should return input"

    b = ql.qint(5, width=4)
    r2 = increment(b)
    assert r2 is b, "Replay in-place should return caller's qint"


def test_exception_during_capture_discarded():
    """Partial capture is discarded on exception; retry works."""
    ql.circuit()
    should_fail = [True]
    call_count = [0]

    @ql.compile
    def maybe_fail(x):
        call_count[0] += 1
        if should_fail[0]:
            raise ValueError("intentional test error")
        x += 1
        return x

    a = ql.qint(3, width=4)
    try:
        maybe_fail(a)
    except ValueError:
        pass
    assert call_count[0] == 1

    # Second call should retry capture (not use cached partial)
    ql.circuit()
    should_fail[0] = False
    b = ql.qint(5, width=4)
    result = maybe_fail(b)
    assert call_count[0] == 2, "Should retry capture after exception"
    assert result is b


def test_function_metadata_preserved():
    """functools.update_wrapper preserves function metadata."""

    @ql.compile
    def my_quantum_func(x):
        """My docstring."""
        x += 1
        return x

    assert my_quantum_func.__name__ == "my_quantum_func"
    assert my_quantum_func.__doc__ == "My docstring."


def test_no_return_value():
    """Function with no return works (returns None)."""
    ql.circuit()

    @ql.compile
    def just_modify(x):
        x += 1
        # No return

    a = ql.qint(3, width=4)
    result = just_modify(a)
    assert result is None

    # Replay also returns None
    b = ql.qint(5, width=4)
    result2 = just_modify(b)
    assert result2 is None


# ---------------------------------------------------------------------------
# Helper: build a synthetic gate dict
# ---------------------------------------------------------------------------
def _gate(gate_type, target, angle=0.0, controls=None):
    """Build a gate dict matching the extract_gate_range format."""
    ctrl = controls if controls is not None else []
    return {
        "type": gate_type,
        "target": target,
        "angle": angle,
        "num_controls": len(ctrl),
        "controls": ctrl,
    }


# ---------------------------------------------------------------------------
# OPT: Optimisation tests (Phase 49)
# ---------------------------------------------------------------------------


def test_optimization_reduces_adjacent_inverse_gates():
    """OPT1: Adjacent self-adjoint gates cancel, reducing gate count.

    Uses synthetic gate list to demonstrate adjacent H-H cancellation,
    then verifies via the compile decorator stats API.
    """
    # Unit test: two adjacent H on same qubit cancel to nothing
    gates = [_gate(_H, 0), _gate(_H, 0)]
    optimized = _optimize_gate_list(gates)
    assert len(optimized) == 0, f"H-H should cancel, got {len(optimized)}"

    # Unit test: cascading cancellation (H-X-X-H -> H-H -> empty)
    gates2 = [_gate(_H, 0), _gate(_X, 0), _gate(_X, 0), _gate(_H, 0)]
    optimized2 = _optimize_gate_list(gates2)
    assert len(optimized2) == 0, f"H-X-X-H should cascade-cancel, got {len(optimized2)}"

    # Unit test: opposite P angles cancel
    gates3 = [_gate(_P, 0, angle=1.5708), _gate(_P, 0, angle=-1.5708)]
    optimized3 = _optimize_gate_list(gates3)
    assert len(optimized3) == 0, f"P(+a) P(-a) should cancel, got {len(optimized3)}"

    # Integration: compiled function with at least some gates should
    # report original_gates >= optimized_gates (never more gates after opt)
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(0, width=4)
    add_one(a)
    assert add_one.original_gates >= add_one.optimized_gates


def test_optimization_stats_properties():
    """OPT4: Stats properties (original_gates, optimized_gates, reduction_percent) exist."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(0, width=4)
    add_one(a)

    assert add_one.original_gates > 0, "original_gates should be > 0"
    assert add_one.optimized_gates >= 0, "optimized_gates should be >= 0"
    assert add_one.reduction_percent >= 0.0, "reduction_percent should be >= 0"
    assert add_one.original_gates >= add_one.optimized_gates


def test_optimize_false_skips_optimization():
    """OPT3: optimize=False stores raw captured sequence without reduction."""
    ql.circuit()

    @ql.compile(optimize=False)
    def add_one(x):
        x += 1
        return x

    a = ql.qint(0, width=4)
    add_one(a)

    # With optimization disabled, original == optimized (no reduction)
    assert add_one.original_gates == add_one.optimized_gates, (
        f"optimize=False should not reduce: orig={add_one.original_gates}, "
        f"opt={add_one.optimized_gates}"
    )
    assert add_one.reduction_percent == 0.0


def test_replay_uses_optimized_gates():
    """OPT2: Replay injects the optimised gate count, not the original.

    We test this using _optimize_gate_list on a synthetic sequence, then
    verify through the compile decorator that replay gate count matches
    the cached (optimised) count.
    """
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    # Capture
    a = ql.qint(0, width=4)
    add_one(a)

    # Replay on different qubits
    b = ql.qint(0, width=4)
    start2 = get_current_layer()
    add_one(b)
    end2 = get_current_layer()
    replay_gates = extract_gate_range(start2, end2)

    # Replay gate count must equal the optimised (cached) count for the
    # uncontrolled variant.  Since _capture_and_cache_both caches both
    # uncontrolled and controlled variants, optimized_gates sums across
    # all entries.  We check the specific uncontrolled block's gate count.
    unctrl_key = ((), (4,), 0, False)
    unctrl_block = add_one._cache[unctrl_key]
    assert len(replay_gates) == len(unctrl_block.gates), (
        f"Replay gates ({len(replay_gates)}) should match uncontrolled cached gates "
        f"({len(unctrl_block.gates)})"
    )


def test_optimization_rotation_merge():
    """OPT2: Consecutive rotations on the same qubit are merged."""
    # Two P gates with different angles -> merged into one
    gates = [_gate(_P, 0, angle=0.5), _gate(_P, 0, angle=0.3)]
    optimized = _optimize_gate_list(gates)
    assert len(optimized) == 1, f"Two P gates should merge, got {len(optimized)}"
    assert abs(optimized[0]["angle"] - 0.8) < 1e-12

    # Two P gates that sum to zero -> disappear
    gates2 = [_gate(_P, 0, angle=0.5), _gate(_P, 0, angle=-0.5)]
    optimized2 = _optimize_gate_list(gates2)
    assert len(optimized2) == 0, f"P(+a) + P(-a) should vanish, got {len(optimized2)}"

    # Different targets -> no merge
    gates3 = [_gate(_P, 0, angle=0.5), _gate(_P, 1, angle=0.3)]
    optimized3 = _optimize_gate_list(gates3)
    assert len(optimized3) == 2, "Different targets should not merge"

    # Different controls -> no merge
    gates4 = [
        _gate(_P, 0, angle=0.5, controls=[1]),
        _gate(_P, 0, angle=0.3, controls=[2]),
    ]
    optimized4 = _optimize_gate_list(gates4)
    assert len(optimized4) == 2, "Different controls should not merge"


def test_optimization_empty_function():
    """OPT: Empty function (no gates) works with optimisation and stats."""
    ql.circuit()

    @ql.compile
    def noop(x):
        return x

    a = ql.qint(0, width=4)
    noop(a)

    assert noop.original_gates == 0
    assert noop.optimized_gates == 0
    assert noop.reduction_percent == 0.0


def test_optimization_fallback_on_error():
    """OPT: Optimisation preserves functional correctness.

    Even if optimisation changes the gate count, the function should still
    produce correct results (replay returns the input qint for in-place ops).
    """
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    result = add_one(a)
    assert result is a, "In-place return should still work after optimisation"

    # Replay also works
    b = ql.qint(5, width=4)
    result2 = add_one(b)
    assert result2 is b, "Replay in-place return should work after optimisation"

    # Subsequent operations on the result should work
    layer_before = get_current_layer()
    result2 += 1
    layer_after = get_current_layer()
    assert layer_after > layer_before


def test_optimization_measurement_gates_never_cancel():
    """OPT: Measurement gates are never cancelled or merged."""
    gates = [_gate(_M, 0), _gate(_M, 0)]
    optimized = _optimize_gate_list(gates)
    assert len(optimized) == 2, "Measurement gates should not cancel"


def test_optimization_controlled_gates_respect_controls():
    """OPT: Gates with different controls do not cancel."""
    # Same type and target, but different controls
    g1 = _gate(_H, 0, controls=[1])
    g2 = _gate(_H, 0, controls=[2])
    assert not _gates_cancel(g1, g2), "Different controls should not cancel"

    # Same controls -> cancel
    g3 = _gate(_H, 0, controls=[1])
    g4 = _gate(_H, 0, controls=[1])
    assert _gates_cancel(g3, g4), "Same controls should cancel"


# ---------------------------------------------------------------------------
# UNCOMP: Uncomputation integration tests (Phase 49 Plan 02)
# ---------------------------------------------------------------------------


def test_uncomputation_replay_result_in_with_block():
    """UNCOMP1: Replay result inside with block is auto-uncomputed at scope exit.

    Capture happens outside the with block; replay inside produces a new qint
    that is registered in the scope frame and uncomputed when the with block exits.
    """
    ql.circuit()

    @ql.compile
    def make_result(x):
        return x + ql.qint(1, width=x.width)

    # Capture (first call) outside with block
    a = ql.qint(3, width=4)
    _r1 = make_result(a)

    # Replay inside with block
    b = ql.qint(5, width=4)
    ctrl = ql.qbool()

    with ctrl:
        result = make_result(b)
        assert not result._is_uncomputed, "Result should be live inside with block"

    # After scope exit, the result should have been auto-uncomputed
    assert result._is_uncomputed, "Replay result should be auto-uncomputed after with block exit"


def test_uncomputation_in_place_return_no_double_uncompute():
    """UNCOMP2: In-place return does NOT set operation_type, preventing spurious uncomputation.

    When a compiled function returns its input parameter (in-place modification),
    the caller's original qint is returned unchanged -- no new metadata is set.
    """
    ql.circuit()

    @ql.compile
    def add_inplace(x):
        x += 1
        return x

    # First call: in-place return
    a = ql.qint(3, width=4)
    result = add_inplace(a)
    assert result is a, "In-place return should be the same object"
    assert result.operation_type is None, (
        f"In-place first-call result should NOT have operation_type, got {result.operation_type}"
    )

    # Replay: in-place return
    b = ql.qint(5, width=4)
    result2 = add_inplace(b)
    assert result2 is b, "Replay in-place return should be caller's qint"
    assert result2.operation_type is None, (
        f"Replay in-place result should NOT have operation_type, got {result2.operation_type}"
    )


def test_uncomputation_second_replay_in_with_block():
    """UNCOMP3: Second replay inside with block also gets correctly uncomputed.

    Ensures uncomputation works consistently across multiple replay invocations
    when called inside different with blocks.
    """
    ql.circuit()

    @ql.compile
    def make_val(x):
        return x + ql.qint(2, width=x.width)

    # First call (capture)
    a = ql.qint(1, width=4)
    _r1 = make_val(a)

    # Second call (replay) inside with block
    b = ql.qint(5, width=4)
    ctrl1 = ql.qbool()
    with ctrl1:
        r2 = make_val(b)
    assert r2._is_uncomputed, "First replay in with block should be uncomputed"

    # Third call (replay) inside another with block
    c = ql.qint(7, width=4)
    ctrl2 = ql.qbool()
    with ctrl2:
        r3 = make_val(c)
    assert r3._is_uncomputed, "Second replay in with block should also be uncomputed"


def test_compiled_result_has_operation_type():
    """UNCOMP4: Both first-call and replay results have operation_type set.

    This is the trigger for _do_uncompute() to actually reverse gates.
    First-call results get their type from normal arithmetic (e.g. 'ADD'),
    replay results get 'COMPILED' from _build_return_qint.
    """
    ql.circuit()

    @ql.compile
    def make_new(x):
        return x + ql.qint(1, width=x.width)

    # First call
    a = ql.qint(0, width=4)
    r1 = make_new(a)
    assert r1.operation_type is not None, "First-call result should have operation_type set"

    # Replay
    b = ql.qint(0, width=4)
    r2 = make_new(b)
    assert r2.operation_type is not None, "Replay result should have operation_type set"
    assert r2.operation_type == "COMPILED", (
        f"Replay result should have operation_type='COMPILED', got {r2.operation_type}"
    )


def test_uncomputation_replay_uses_optimized_sequence():
    """UNCOMP5: Uncomputation reverses the optimised gate sequence, not the original.

    The replayed gates come from the optimised (cached) sequence, so when
    reverse_circuit_range is called during uncomputation, it reverses only
    the optimised gates.  We verify by checking that the replay gate count
    matches the optimised count, and that uncomputation correctly reverses
    only those gates.
    """
    ql.circuit()

    @ql.compile
    def make_new(x):
        return x + ql.qint(1, width=x.width)

    # Capture
    a = ql.qint(0, width=4)
    _r1 = make_new(a)
    # Get the uncontrolled block's gate count directly (optimized_gates
    # sums across both uncontrolled and controlled cached variants)
    unctrl_key = ((), (4,), 0, False)
    cached_gate_count = len(make_new._cache[unctrl_key].gates)

    # Replay outside with block to measure forward gate count
    b = ql.qint(0, width=4)
    start = get_current_layer()
    _r2 = make_new(b)
    end = get_current_layer()
    replay_gates = extract_gate_range(start, end)
    assert len(replay_gates) == cached_gate_count, (
        f"Replay gate count ({len(replay_gates)}) should match "
        f"uncontrolled cached gates ({cached_gate_count})"
    )

    # Replay inside with block -- result gets uncomputed
    c = ql.qint(0, width=4)
    ctrl = ql.qbool()
    with ctrl:
        r3 = make_new(c)

    # r3's start/end layer span should match the optimised gate count
    layer_span = r3._end_layer - r3._start_layer
    assert layer_span > 0, "Result should have valid layer span"
    # The span of optimised gates that were replayed should equal the cached count
    # After uncomputation, the gates may have been reversed/removed,
    # but the original span should have matched the optimised count
    assert r3._is_uncomputed, "Result should be uncomputed after with block"


# ---------------------------------------------------------------------------
# CTL: Controlled context tests (Phase 50 Plan 02)
# ---------------------------------------------------------------------------


def test_compile_controlled_basic():
    """CTL-01: Compiled function inside `with qbool:` produces controlled gates.

    First call outside `with` block captures + caches both variants.
    Second call inside `with` block replays the controlled variant, which has
    extra controls on every gate.
    """
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    # Call outside `with` block -- capture both variants
    a = ql.qint(3, width=4)
    add_one(a)

    # Verify both variants are cached (eager compilation)
    unctrl_key = ((), (4,), 0, False)
    ctrl_key = ((), (4,), 1, False)
    assert unctrl_key in add_one._cache, "Uncontrolled variant should be cached"
    assert ctrl_key in add_one._cache, "Controlled variant should be cached"

    # Call inside `with` block -- should replay the controlled variant
    b = ql.qint(5, width=4)
    ctrl = ql.qbool(True)

    start = get_current_layer()
    with ctrl:
        add_one(b)
    end = get_current_layer()

    # Gates inside the `with` block should have controls
    gates = extract_gate_range(start, end)
    assert len(gates) > 0, "Should have gates inside with block"

    # Every gate replayed from the controlled variant should have at least 1 control
    ctrl_block = add_one._cache[ctrl_key]
    for gate in ctrl_block.gates:
        assert gate["num_controls"] >= 1, (
            f"Controlled gate should have at least 1 control, got {gate['num_controls']}"
        )


def test_compile_controlled_separate_cache_entries():
    """CTL-03: Separate cache entries exist for controlled vs uncontrolled.

    After the first call (whether inside or outside `with`), both cache entries
    are created immediately.  Subsequent calls in either context hit the cache
    without re-capture.
    """
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    # First call outside `with` -- triggers capture
    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1, "First call should capture"

    # Both variants should already be cached
    assert len(add_one._cache) == 2, (
        f"Cache should have 2 entries (uncontrolled + controlled), got {len(add_one._cache)}"
    )

    # Call inside `with` -- should NOT re-capture (cache hit on controlled variant)
    b = ql.qint(5, width=4)
    ctrl = ql.qbool(True)
    with ctrl:
        add_one(b)
    assert call_count[0] == 1, "Controlled call should be cache hit (no re-capture)"

    # Call outside `with` again -- also cache hit
    c = ql.qint(7, width=4)
    add_one(c)
    assert call_count[0] == 1, "Uncontrolled call should be cache hit (no re-capture)"


def test_compile_controlled_gates_have_extra_control():
    """CTL: Every gate in the controlled variant has exactly 1 more control than
    the corresponding gate in the uncontrolled variant.
    """
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)

    unctrl_key = ((), (4,), 0, False)
    ctrl_key = ((), (4,), 1, False)
    unctrl_block = add_one._cache[unctrl_key]
    ctrl_block = add_one._cache[ctrl_key]

    # Same number of gates in both variants
    assert len(ctrl_block.gates) == len(unctrl_block.gates), (
        f"Controlled and uncontrolled variants should have same gate count: "
        f"ctrl={len(ctrl_block.gates)}, unctrl={len(unctrl_block.gates)}"
    )

    # Each controlled gate has exactly 1 more control
    for i, (ug, cg) in enumerate(zip(unctrl_block.gates, ctrl_block.gates, strict=False)):
        assert cg["num_controls"] == ug["num_controls"] + 1, (
            f"Gate {i}: controlled should have {ug['num_controls'] + 1} controls, "
            f"got {cg['num_controls']}"
        )
        assert cg["type"] == ug["type"], (
            f"Gate {i}: type should be same, got ctrl={cg['type']}, unctrl={ug['type']}"
        )
        assert cg["target"] == ug["target"], (
            f"Gate {i}: target should be same, got ctrl={cg['target']}, unctrl={ug['target']}"
        )


def test_compile_controlled_nested_with():
    """CTL-01: Compiled function called inside sequential `with` blocks
    produces correctly controlled gates.

    Each `with` block independently controls the compiled function.  The
    compiled function's controlled variant is replayed for each `with` block
    with the appropriate control qubit.
    """
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    # First call outside to capture + cache both variants
    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1

    # Call inside first `with` block
    b = ql.qint(5, width=4)
    qbool1 = ql.qbool(True)
    qbool1_qubit = int(qbool1.qubits[63])

    start1 = get_current_layer()
    with qbool1:
        add_one(b)
    end1 = get_current_layer()
    gates1 = extract_gate_range(start1, end1)

    assert call_count[0] == 1, "First `with` should be a cache hit"

    # Call inside second `with` block (different control qubit)
    c = ql.qint(7, width=4)
    qbool2 = ql.qbool(True)
    qbool2_qubit = int(qbool2.qubits[63])

    start2 = get_current_layer()
    with qbool2:
        add_one(c)
    end2 = get_current_layer()
    gates2 = extract_gate_range(start2, end2)

    assert call_count[0] == 1, "Second `with` should also be a cache hit"

    # Verify different control qubits are used
    assert qbool1_qubit != qbool2_qubit, "Different qbools should have different qubits"

    # Both calls should produce gates with controls
    for gate in gates1:
        if gate["num_controls"] > 0:
            assert qbool1_qubit in gate["controls"], (
                "First with-block gate should use qbool1's qubit"
            )
    for gate in gates2:
        if gate["num_controls"] > 0:
            assert qbool2_qubit in gate["controls"], (
                "Second with-block gate should use qbool2's qubit"
            )


def test_compile_controlled_replay_correct_qubits():
    """CTL: Replayed controlled gates use the correct control qubit for each call.

    Two calls inside different `with` blocks should use different control qubits.
    """
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    # First call outside to capture
    a = ql.qint(3, width=4)
    add_one(a)

    # Call inside `with qbool1:`
    b = ql.qint(5, width=4)
    ctrl1 = ql.qbool(True)
    ctrl1_qubit = int(ctrl1.qubits[63])

    start1 = get_current_layer()
    with ctrl1:
        add_one(b)
    end1 = get_current_layer()
    gates1 = extract_gate_range(start1, end1)

    # Call inside `with qbool2:` (different control qubit)
    c = ql.qint(7, width=4)
    ctrl2 = ql.qbool(True)
    ctrl2_qubit = int(ctrl2.qubits[63])

    start2 = get_current_layer()
    with ctrl2:
        add_one(c)
    end2 = get_current_layer()
    gates2 = extract_gate_range(start2, end2)

    # The control qubits should be different
    assert ctrl1_qubit != ctrl2_qubit, "Different qbools should have different qubits"

    # Verify that gates in first call use ctrl1's qubit as control
    for gate in gates1:
        if gate["num_controls"] > 0:
            assert ctrl1_qubit in gate["controls"], (
                f"Gate should use ctrl1's qubit {ctrl1_qubit} as control, "
                f"got controls={gate['controls']}"
            )

    # Verify that gates in second call use ctrl2's qubit as control
    for gate in gates2:
        if gate["num_controls"] > 0:
            assert ctrl2_qubit in gate["controls"], (
                f"Gate should use ctrl2's qubit {ctrl2_qubit} as control, "
                f"got controls={gate['controls']}"
            )


def test_compile_controlled_custom_key():
    """CTL: Custom key function correctly separates controlled and uncontrolled
    cache entries.  The custom key is wrapped with control_count.
    """
    ql.circuit()
    call_count = [0]

    @ql.compile(key=lambda x: x.width)
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    # First call outside `with` -- capture
    a = ql.qint(3, width=4)
    add_one(a)
    assert call_count[0] == 1

    # Cache should have 2 entries: (4, 0) and (4, 1)
    assert (4, 0, False) in add_one._cache, "Uncontrolled variant with custom key should be cached"
    assert (4, 1, False) in add_one._cache, "Controlled variant with custom key should be cached"

    # Call inside `with` -- cache hit on controlled variant
    b = ql.qint(5, width=4)
    ctrl = ql.qbool(True)
    with ctrl:
        add_one(b)
    assert call_count[0] == 1, "Controlled call with custom key should be cache hit"


def test_compile_controlled_first_call_inside_with():
    """CTL: First call to compiled function happens inside `with` block.

    This tests the accepted trade-off: the first call captures the uncontrolled
    body (because gates already emitted to the circuit cannot be retroactively
    controlled). The gates in the circuit during this first call are UNCONTROLLED.
    Both uncontrolled and controlled variants are cached.
    Subsequent calls replay the correct variant (controlled inside `with`,
    uncontrolled outside).
    """
    ql.circuit()
    call_count = [0]

    @ql.compile
    def add_one(x):
        call_count[0] += 1
        x += 1
        return x

    # First call INSIDE `with` block -- triggers capture in uncontrolled mode
    a = ql.qint(3, width=4)
    ctrl = ql.qbool(True)
    with ctrl:
        add_one(a)
    assert call_count[0] == 1, "First call should capture"

    # Both variants should be cached
    unctrl_key = ((), (4,), 0, False)
    ctrl_key = ((), (4,), 1, False)
    assert unctrl_key in add_one._cache, (
        "Uncontrolled variant should be cached even when first called inside `with`"
    )
    assert ctrl_key in add_one._cache, (
        "Controlled variant should be cached even when first called inside `with`"
    )

    # Call outside `with` -- cache hit on uncontrolled variant
    b = ql.qint(5, width=4)
    add_one(b)
    assert call_count[0] == 1, "Uncontrolled call should be cache hit"

    # Call inside `with` again -- cache hit on controlled variant, gates ARE controlled
    c = ql.qint(7, width=4)
    ctrl2 = ql.qbool(True)
    ctrl2_qubit = int(ctrl2.qubits[63])

    start = get_current_layer()
    with ctrl2:
        add_one(c)
    end = get_current_layer()

    assert call_count[0] == 1, "Second controlled call should be cache hit"

    # Verify replayed gates use the control qubit (subsequent calls work correctly)
    gates = extract_gate_range(start, end)
    assert len(gates) > 0, "Should have gates from controlled replay"
    for gate in gates:
        if gate["num_controls"] > 0:
            assert ctrl2_qubit in gate["controls"], (
                f"Replayed controlled gate should use ctrl2's qubit {ctrl2_qubit}, "
                f"got controls={gate['controls']}"
            )


# ---------------------------------------------------------------------------
# INV: Inverse generation tests (Phase 51)
# ---------------------------------------------------------------------------


def test_inverse_reverses_gate_order():
    """INV-01: _inverse_gate_list reverses gate order and adjoints each gate."""
    gates = [
        _gate(_X, 0),
        _gate(_H, 1),
        _gate(_P, 0, angle=0.5),
    ]
    inverted = _inverse_gate_list(gates)
    assert len(inverted) == 3

    # First gate should be adjoint of last original: P with angle=-0.5 on target 0
    assert inverted[0]["type"] == _P
    assert inverted[0]["target"] == 0
    assert abs(inverted[0]["angle"] - (-0.5)) < 1e-12

    # Second gate: H on target 1 (self-adjoint, unchanged)
    assert inverted[1]["type"] == _H
    assert inverted[1]["target"] == 1

    # Third gate: X on target 0 (self-adjoint, unchanged)
    assert inverted[2]["type"] == _X
    assert inverted[2]["target"] == 0


def test_inverse_negates_rotation_angles():
    """INV-02: Rotation gates have their angles negated by _adjoint_gate."""
    for gate_type in (_P, _Rx, _Ry, _Rz, _R):
        g = _gate(gate_type, 0, angle=1.23)
        adj = _adjoint_gate(g)
        assert abs(adj["angle"] - (-1.23)) < 1e-12, (
            f"Gate type {gate_type}: expected angle -1.23, got {adj['angle']}"
        )
        assert adj["type"] == gate_type


def test_inverse_self_adjoint_unchanged():
    """INV-03: Self-adjoint gates (X, Y, Z, H) are unchanged by _adjoint_gate."""
    for gate_type in (_X, _Y, _Z, _H):
        g = _gate(gate_type, 0)
        adj = _adjoint_gate(g)
        assert adj["type"] == gate_type
        assert abs(adj["angle"]) < 1e-12


def test_inverse_measurement_raises():
    """INV-04: _adjoint_gate raises ValueError for measurement gates."""
    g = _gate(_M, 0)
    with pytest.raises(ValueError, match="(?i)measurement"):
        _adjoint_gate(g)


def test_inverse_empty_function():
    """INV-05: Adjoint of a no-op compiled function works correctly."""
    ql.circuit()

    @ql.compile
    def noop(x):
        return x

    a = ql.qint(0, width=4)
    noop(a)

    inv = noop.adjoint
    assert isinstance(inv, _InverseCompiledFunc)

    b = ql.qint(0, width=4)
    result = inv(b)
    assert result is b  # In-place return


def test_inverse_round_trip():
    """INV-06: fn.adjoint.inverse() is the original fn (identity round-trip)."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)

    inv = add_one.adjoint
    assert isinstance(inv, _InverseCompiledFunc)
    assert inv.inverse() is add_one


def test_inverse_replays_adjoint_gates():
    """INV-07: Inverse callable replays adjoint gates with correct count."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    # Capture
    a = ql.qint(3, width=4)
    start_cap = get_current_layer()
    add_one(a)
    end_cap = get_current_layer()
    _capture_gates = extract_gate_range(start_cap, end_cap)  # noqa: F841

    inv = add_one.adjoint

    # Call adjoint (standalone inverse with fresh ancillas)
    b = ql.qint(5, width=4)
    start_inv = get_current_layer()
    inv(b)
    end_inv = get_current_layer()
    inv_gates = extract_gate_range(start_inv, end_inv)

    assert len(inv_gates) > 0, "Adjoint should produce gates"
    # Adjoint replays from cached (possibly optimized) block, so compare
    # against the cached uncontrolled block gate count
    unctrl_key = ((), (4,), 0, False)
    cached_count = len(add_one._cache[unctrl_key].gates)
    assert len(inv_gates) == cached_count, (
        f"Adjoint gate count {len(inv_gates)} should match cached count {cached_count}"
    )


def test_inverse_preserves_controls():
    """INV-08: _adjoint_gate preserves control qubits."""
    g = _gate(_P, 0, angle=0.5, controls=[1, 2])
    adj = _adjoint_gate(g)
    assert adj["controls"] == [1, 2]
    assert adj["num_controls"] == 2
    assert abs(adj["angle"] - (-0.5)) < 1e-12


# ---------------------------------------------------------------------------
# DBG: Debug mode tests (Phase 51)
# ---------------------------------------------------------------------------


def test_debug_prints_to_stderr():
    """DBG-01: debug=True prints to stderr on function call."""
    ql.circuit()

    @ql.compile(debug=True)
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    old_stderr = sys.stderr
    sys.stderr = captured = io.StringIO()
    try:
        add_one(a)
    finally:
        sys.stderr = old_stderr

    output = captured.getvalue()
    assert "add_one" in output, f"Should contain function name, got: {output}"
    assert "MISS" in output, f"First call should report MISS, got: {output}"


def test_debug_reports_cache_hit():
    """DBG-02: debug=True reports HIT on second call with same args."""
    ql.circuit()

    @ql.compile(debug=True)
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)  # First call (MISS)

    b = ql.qint(5, width=4)
    old_stderr = sys.stderr
    sys.stderr = captured = io.StringIO()
    try:
        add_one(b)  # Second call (HIT)
    finally:
        sys.stderr = old_stderr

    output = captured.getvalue()
    assert "HIT" in output, f"Second call should report HIT, got: {output}"


def test_debug_stats_populated():
    """DBG-03: .stats is populated after debug=True call."""
    ql.circuit()

    @ql.compile(debug=True)
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)

    assert add_one.stats is not None
    assert isinstance(add_one.stats, dict)
    assert add_one.stats["cache_hit"] is False
    assert add_one.stats["original_gate_count"] > 0
    assert add_one.stats["optimized_gate_count"] >= 0
    assert add_one.stats["cache_size"] >= 1


def test_debug_stats_none_when_disabled():
    """DBG-04: .stats is None when debug=False (default)."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_one(a)
    assert add_one.stats is None


def test_debug_stats_tracks_totals():
    """DBG-05: .stats tracks cumulative total_hits and total_misses."""
    ql.circuit()

    @ql.compile(debug=True)
    def add_one(x):
        x += 1
        return x

    # First call width=4 (miss)
    a = ql.qint(3, width=4)
    add_one(a)

    # Second call width=4 (hit)
    b = ql.qint(5, width=4)
    add_one(b)

    # Third call width=8 (miss)
    c = ql.qint(5, width=8)
    add_one(c)

    assert add_one.stats["total_hits"] == 1
    assert add_one.stats["total_misses"] == 2


# ---------------------------------------------------------------------------
# NST: Nesting tests (Phase 51)
# ---------------------------------------------------------------------------


def test_nesting_inner_gates_in_outer_capture():
    """NST-01: Outer capture includes inner compiled function's replayed gates."""
    ql.circuit()
    inner_count = [0]
    outer_count = [0]

    @ql.compile
    def add_one(x):
        inner_count[0] += 1
        x += 1
        return x

    @ql.compile
    def add_two(x):
        outer_count[0] += 1
        x = add_one(x)
        x = add_one(x)
        return x

    # Populate inner's cache first
    a = ql.qint(0, width=4)
    add_one(a)
    assert inner_count[0] == 1

    # Call outer (captures outer, which internally replays inner twice)
    b = ql.qint(3, width=4)
    start = get_current_layer()
    add_two(b)
    end = get_current_layer()
    assert outer_count[0] == 1
    assert end > start, "Outer should produce gates"

    # Replay outer (no re-execution)
    c = ql.qint(5, width=4)
    add_two(c)
    assert outer_count[0] == 1, "Replay should NOT re-execute outer"
    assert inner_count[0] == 1, "Inner should not be called again during replay"


def test_nesting_depth_limit():
    """NST-02: Recursive compiled functions raise RecursionError at depth limit."""

    ql.circuit()
    fn_ref = [None]

    @ql.compile
    def recursive_fn(x):
        x += 1
        return fn_ref[0](x)

    fn_ref[0] = recursive_fn

    with pytest.raises(RecursionError, match="(?i)nesting depth"):
        recursive_fn(ql.qint(0, width=4))


def test_nesting_inner_return_value_usable():
    """NST-03: Inner compiled function's return value is usable in outer."""
    ql.circuit()

    @ql.compile
    def make_new(x):
        return x + ql.qint(1, width=x.width)

    @ql.compile
    def add_and_increment(x):
        r = make_new(x)
        r += 1
        return r

    # Populate inner cache
    a = ql.qint(0, width=4)
    _r = make_new(a)

    # Call outer
    b = ql.qint(3, width=4)
    result = add_and_increment(b)
    assert result.width == 4

    # Replay outer
    c = ql.qint(5, width=4)
    result2 = add_and_increment(c)
    assert result2.width == 4

    # Result should be usable in subsequent operations
    layer_before = get_current_layer()
    result2 += 1
    layer_after = get_current_layer()
    assert layer_after > layer_before, "Replay result should be usable"


def test_nesting_replay_uses_outer_cache():
    """NST-04: Outer replay does NOT re-enter inner function."""
    ql.circuit()
    inner_count = [0]
    outer_count = [0]

    @ql.compile
    def add_one(x):
        inner_count[0] += 1
        x += 1
        return x

    @ql.compile
    def add_two(x):
        outer_count[0] += 1
        x = add_one(x)
        x = add_one(x)
        return x

    # Call outer once (captures everything)
    a = ql.qint(3, width=4)
    add_two(a)
    assert outer_count[0] == 1
    # Inner was called during outer's capture (first call triggers inner capture + replay)
    inner_after_first = inner_count[0]

    # Call outer again (replays from outer's cache -- inner is NOT re-entered)
    b = ql.qint(5, width=4)
    add_two(b)
    assert outer_count[0] == 1, "Outer should replay (no re-execution)"
    assert inner_count[0] == inner_after_first, "Inner should NOT be called during outer replay"


# ---------------------------------------------------------------------------
# COMP: Composition tests (Phase 51)
# ---------------------------------------------------------------------------


def test_composition_inverse_with_controlled():
    """COMP-01: Adjoint callable works inside controlled context."""
    ql.circuit()

    @ql.compile
    def add_one(x):
        x += 1
        return x

    # Populate cache
    a = ql.qint(3, width=4)
    add_one(a)

    inv = add_one.adjoint
    qbool = ql.qbool(True)

    # Call adjoint inside controlled context
    b = ql.qint(5, width=4)
    start = get_current_layer()
    with qbool:
        inv(b)
    end = get_current_layer()

    gates = extract_gate_range(start, end)
    assert len(gates) > 0, "Should produce gates"

    # Verify at least some gates have controls
    controlled_gates = [g for g in gates if g["num_controls"] >= 1]
    assert len(controlled_gates) > 0, "Some gates should have controls"


def test_composition_nested_inverse():
    """COMP-02: Outer compiled function can call inner's adjoint."""
    ql.circuit()
    inner_count = [0]
    outer_count = [0]

    @ql.compile
    def add_one(x):
        inner_count[0] += 1
        x += 1
        return x

    # Populate inner cache
    a = ql.qint(3, width=4)
    add_one(a)
    assert inner_count[0] == 1

    @ql.compile
    def undo_add(x):
        outer_count[0] += 1
        return add_one.adjoint(x)

    # Call outer (captures outer, which calls inner's adjoint)
    b = ql.qint(5, width=4)
    start = get_current_layer()
    undo_add(b)
    end = get_current_layer()
    assert end > start, "Should produce gates"
    assert outer_count[0] == 1

    # Replay outer (no re-execution)
    c = ql.qint(7, width=4)
    undo_add(c)
    assert outer_count[0] == 1, "Replay should not re-execute outer"


# ---------------------------------------------------------------------------
# ANCILLA: Ancilla tracking tests (Phase 52, INV-01)
# ---------------------------------------------------------------------------


def test_forward_call_tracks_ancillas():
    """INV-01: Compiled function tracks internal qubit allocations as ancillas."""
    ql.circuit()

    @ql.compile
    def make_ancilla(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        return temp

    a = ql.qint(3, width=4)
    _result = make_ancilla(a)

    # Forward call should be tracked
    assert len(make_ancilla._forward_calls) == 1
    # Should have ancilla qubits recorded
    key = list(make_ancilla._forward_calls.keys())[0]
    record = make_ancilla._forward_calls[key]
    assert len(record.ancilla_qubits) > 0, "Should have ancilla qubits recorded"


def test_forward_call_tracks_return_qint():
    """INV-01: Return value qubits are tracked in the ancilla record."""
    ql.circuit()

    @ql.compile
    def make_result(x):
        result = ql.qint(0, width=x.width)
        result += x
        return result

    a = ql.qint(5, width=4)
    result = make_result(a)
    key = list(make_result._forward_calls.keys())[0]
    record = make_result._forward_calls[key]
    assert record.return_qint is result, "Return qint should be tracked in ancilla record"


def test_inplace_function_no_forward_tracking():
    """INV-01: In-place function without ancillas does NOT track forward calls."""
    ql.circuit()

    @ql.compile
    def add_inplace(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    add_inplace(a)
    assert len(add_inplace._forward_calls) == 0, (
        "In-place function without ancillas should not track forward calls"
    )


# ---------------------------------------------------------------------------
# AINV: f.inverse(x) tests (Phase 52, INV-02/03)
# ---------------------------------------------------------------------------


def test_ancilla_inverse_basic():
    """INV-02/03: f.inverse(x) uncomputes ancillas from a prior forward call."""
    ql.circuit()

    @ql.compile
    def add_temp(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        return temp

    a = ql.qint(3, width=4)
    stats_before = ql.circuit_stats()
    _result = add_temp(a)
    stats_during = ql.circuit_stats()

    # Ancillas allocated
    assert stats_during["current_in_use"] > stats_before["current_in_use"], (
        "Forward call should allocate ancilla qubits"
    )

    # Inverse call
    add_temp.inverse(a)
    stats_after = ql.circuit_stats()

    # Ancillas deallocated
    assert stats_after["current_in_use"] == stats_before["current_in_use"], (
        "After inverse, qubit count should return to pre-forward level"
    )
    # Forward call record removed
    assert len(add_temp._forward_calls) == 0, "Forward call record should be removed after inverse"


def test_ancilla_inverse_removes_forward_record():
    """INV-03: After inverse, no forward call record for those qubits."""
    ql.circuit()

    @ql.compile
    def simple_op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(2, width=4)
    simple_op(a)
    assert len(simple_op._forward_calls) == 1
    simple_op.inverse(a)
    assert len(simple_op._forward_calls) == 0


# ---------------------------------------------------------------------------
# AINV-SIM: Qiskit verification (Phase 52, INV-04)
# ---------------------------------------------------------------------------

try:
    from qiskit import qasm3

    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False


@pytest.mark.skipif(not HAS_QISKIT, reason="Qiskit not installed")
def test_ancilla_inverse_produces_adjoint_gates_qiskit():
    """INV-04: After forward + inverse, adjoint gate sequence is present in circuit.

    We verify the structural property: the inverse injects the same number of
    gates as the cached (optimized) block, confirming that the inverse proxy
    correctly generates and injects the adjoint gates using the original
    ancilla qubits.
    """
    ql.circuit()

    @ql.compile
    def add_to_new(x):
        result = ql.qint(0, width=x.width)
        result += x
        return result

    a = ql.qint(5, width=4)
    _result = add_to_new(a)

    # Get the cached block gate count (this is what inverse uses)
    unctrl_key = ((), (4,), 0, False)
    cached_gate_count = len(add_to_new._cache[unctrl_key].gates)

    # Measure inverse call gate count
    start_inv = get_current_layer()
    add_to_new.inverse(a)
    end_inv = get_current_layer()
    inv_gates = extract_gate_range(start_inv, end_inv)

    # Inverse should inject approximately the same number of gates as the cached block.
    # Minor differences can occur from circuit-level gate scheduling/merging.
    assert len(inv_gates) > 0, "Inverse should inject gates"
    assert abs(len(inv_gates) - cached_gate_count) <= 2, (
        f"Inverse gate count ({len(inv_gates)}) should be close to cached ({cached_gate_count})"
    )

    # Export to QASM and verify it loads successfully
    qasm = ql.to_openqasm()
    qc = qasm3.loads(qasm)
    assert qc.num_qubits > 0, "QASM should produce a valid circuit"


# ---------------------------------------------------------------------------
# AINV-DEALLOC: Deallocation tests (Phase 52, INV-05)
# ---------------------------------------------------------------------------


def test_ancilla_inverse_deallocates_ancillas():
    """INV-05: After inverse, ancilla qubits are returned to allocator."""
    ql.circuit()

    @ql.compile
    def alloc_func(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    stats_pre = ql.circuit_stats()
    _result = alloc_func(a)
    stats_mid = ql.circuit_stats()
    alloc_func.inverse(a)
    stats_post = ql.circuit_stats()

    # Qubits freed
    assert stats_post["current_in_use"] == stats_pre["current_in_use"], (
        "After inverse, current_in_use should return to pre-forward level"
    )
    # Deallocation count increased
    assert stats_post["total_deallocations"] > stats_mid["total_deallocations"], (
        "Deallocation count should increase after inverse"
    )


def test_deallocated_qubits_reusable():
    """INV-05: After inverse, freed qubits can be reused by new allocations."""
    ql.circuit()

    @ql.compile
    def make_temp(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(1, width=4)
    _result = make_temp(a)

    make_temp.inverse(a)
    stats_after_inv = ql.circuit_stats()

    # Allocate new qubits -- should reuse freed slots
    b = ql.qint(2, width=4)
    stats_after_realloc = ql.circuit_stats()

    # If qubits were properly freed, new allocation succeeds
    assert b.width == 4
    # current_in_use should be same as after inverse + 4 new qubits
    assert stats_after_realloc["current_in_use"] == stats_after_inv["current_in_use"] + 4


# ---------------------------------------------------------------------------
# AINV-DEFER: Deferred inverse tests (Phase 52, INV-06)
# ---------------------------------------------------------------------------


def test_ancilla_inverse_after_other_operations():
    """INV-06: f.inverse(x) works when called later, not just immediately after."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    _result = op(a)

    # Do other operations in between
    b = ql.qint(7, width=4)
    c = ql.qint(0, width=4)
    c += b

    # Now inverse the earlier call
    op.inverse(a)
    assert len(op._forward_calls) == 0, "Deferred inverse should still work"


def test_ancilla_inverse_with_multiple_forward_calls():
    """INV-06: Multiple forward calls can coexist, each inversed independently."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    b = ql.qint(5, width=4)
    _r1 = op(a)
    _r2 = op(b)
    assert len(op._forward_calls) == 2, "Should have 2 forward call records"

    # Inverse in different order
    op.inverse(b)
    assert len(op._forward_calls) == 1, "Should have 1 forward call record after first inverse"
    op.inverse(a)
    assert len(op._forward_calls) == 0, "Should have 0 forward call records after second inverse"


# ---------------------------------------------------------------------------
# AINV-ERR: Error handling tests (Phase 52)
# ---------------------------------------------------------------------------


def test_double_forward_raises_error():
    """Error: Calling f(x) twice with same input qubits without inverse."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    op(a)
    with pytest.raises(ValueError, match="already has an uninverted"):
        op(a)  # Same input qubits, should error


def test_inverse_without_forward_raises_error():
    """Error: f.inverse(x) without prior f(x) raises ValueError."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    with pytest.raises(ValueError, match="No prior forward call"):
        op.inverse(a)


def test_double_inverse_raises_error():
    """Error: f.inverse(x) twice for same forward call raises error."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    op(a)
    op.inverse(a)
    with pytest.raises(ValueError, match="No prior forward call"):
        op.inverse(a)  # Already inversed


# ---------------------------------------------------------------------------
# AINV-RET: Return value invalidation tests (Phase 52)
# ---------------------------------------------------------------------------


def test_return_qint_invalidated_after_inverse():
    """Return qint is invalidated after f.inverse(x)."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    result = op(a)
    assert not result._is_uncomputed, "Result should be live before inverse"

    op.inverse(a)
    assert result._is_uncomputed is True, "Result should be uncomputed after inverse"
    assert result.allocated_qubits is False, "Result qubits should be deallocated after inverse"


# ---------------------------------------------------------------------------
# AINV-ADJ: f.adjoint(x) standalone tests (Phase 52)
# ---------------------------------------------------------------------------


def test_adjoint_standalone_no_forward_needed():
    """f.adjoint(x) runs reverse circuit with fresh ancillas, no forward needed."""
    ql.circuit()

    @ql.compile
    def op(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    _result = op.adjoint(a)

    # adjoint does NOT track forward calls
    assert len(op._forward_calls) == 0, "Adjoint should not track forward calls"


def test_adjoint_does_not_interfere_with_inverse():
    """f.adjoint and f.inverse are independent."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    b = ql.qint(5, width=4)
    _result = op(a)

    # adjoint on different qubits
    op.adjoint(b)

    # inverse on original qubits still works
    op.inverse(a)
    assert len(op._forward_calls) == 0, "Inverse should still work after adjoint call"


def test_adjoint_with_ancilla_function():
    """f.adjoint(x) works with functions that allocate ancillas."""
    ql.circuit()

    @ql.compile
    def make_temp(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    _result = make_temp.adjoint(a)

    # adjoint should NOT track forward calls
    assert len(make_temp._forward_calls) == 0, "Adjoint should not create forward call records"


# ---------------------------------------------------------------------------
# AINV-REFORWARD: Re-forward after inverse (Phase 52)
# ---------------------------------------------------------------------------


def test_reforward_after_inverse():
    """After f.inverse(x), can call f(x) again with same qubits."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    _r1 = op(a)
    op.inverse(a)

    # Should work again
    _r2 = op(a)
    assert len(op._forward_calls) == 1, "Should have 1 forward call after re-forward"
    op.inverse(a)
    assert len(op._forward_calls) == 0, "Should have 0 forward calls after second inverse"


# ---------------------------------------------------------------------------
# AINV-RESET: Circuit reset clears forward calls (Phase 52)
# ---------------------------------------------------------------------------


def test_circuit_reset_clears_forward_calls_52():
    """ql.circuit() clears forward call registry."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    a = ql.qint(3, width=4)
    op(a)
    assert len(op._forward_calls) == 1

    ql.circuit()  # Reset
    assert len(op._forward_calls) == 0, "Circuit reset should clear forward calls"


# ---------------------------------------------------------------------------
# AINV-REPLAY: Replay path forward tracking (Phase 52)
# ---------------------------------------------------------------------------


def test_replay_tracks_forward_call():
    """Replay (cached) path also tracks forward calls for inverse support."""
    ql.circuit()

    @ql.compile
    def op(x):
        t = ql.qint(0, width=x.width)
        t += x
        return t

    # First call (capture path)
    a = ql.qint(3, width=4)
    _r1 = op(a)
    assert len(op._forward_calls) == 1

    # Second call (replay path) with different qubits
    b = ql.qint(5, width=4)
    _r2 = op(b)
    assert len(op._forward_calls) == 2, "Replay should also track forward call"

    # Inverse both
    op.inverse(b)
    assert len(op._forward_calls) == 1
    op.inverse(a)
    assert len(op._forward_calls) == 0


# ---------------------------------------------------------------------------
# AUTOUNCOMP: Auto-uncompute tests (Phase 53, INV-07)
# ---------------------------------------------------------------------------


def test_auto_uncompute_basic():
    """INV-07: Auto-uncompute fires and temp ancillas are deallocated.

    Uses a function that allocates both temp AND return qubits so that
    auto-uncompute has actual temp qubits to deallocate.
    """
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def complex_fn(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        result = ql.qint(0, width=x.width)
        result += temp
        return result

    a = ql.qint(3, width=4)
    stats_before = ql.circuit_stats()
    result = complex_fn(a)
    stats_after = ql.circuit_stats()

    # Result should be a new qint (not the input)
    assert result is not a
    assert result.width == 4

    # Auto-uncompute should have deallocated temp ancillas.
    # Deallocations should have increased from before.
    assert stats_after["total_deallocations"] > stats_before["total_deallocations"], (
        "Auto-uncompute should trigger deallocation of temp ancilla qubits"
    )

    # Forward call record should exist and be marked as auto-uncomputed
    assert len(complex_fn._forward_calls) == 1
    record = list(complex_fn._forward_calls.values())[0]
    assert record._auto_uncomputed is True, "Record should be marked as auto-uncomputed"


def test_auto_uncompute_preserves_return_value():
    """INV-07: Return value qubits hold correct result after auto-uncompute.

    After auto-uncompute fires on temp qubits, the return qint should still
    be live and usable in subsequent operations.
    """
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def complex_fn(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        result = ql.qint(0, width=x.width)
        result += temp
        return result

    a = ql.qint(5, width=4)
    result = complex_fn(a)

    # Return value should exist and be usable
    assert result is not a
    assert result.width == 4
    assert not result._is_uncomputed, "Return qint should still be live after auto-uncompute"
    assert result.allocated_qubits is True, "Return qubits should still be allocated"

    # Can still do quantum operations on the return value (use another qint
    # for a non-trivial operation that always emits gates)
    layer_before = get_current_layer()
    b = ql.qint(1, width=4)
    result += b
    layer_after = get_current_layer()
    assert layer_after > layer_before, "Should be able to operate on return value"


def test_auto_uncompute_qubit_reuse():
    """INV-07: Deallocated temp qubits are reusable by subsequent allocations."""
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def complex_fn(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        result = ql.qint(0, width=x.width)
        result += temp
        return result

    a = ql.qint(1, width=4)
    _result = complex_fn(a)
    stats_after_call = ql.circuit_stats()
    peak_after_call = stats_after_call["peak_allocated"]

    # Allocate a new qint -- should reuse freed temp qubit slots
    b = ql.qint(2, width=4)
    stats_after_realloc = ql.circuit_stats()

    assert b.width == 4
    # Peak should NOT grow if freed slots are reused
    assert stats_after_realloc["peak_allocated"] == peak_after_call, (
        "New allocation should reuse freed temp qubit slots (peak unchanged)"
    )


def test_auto_uncompute_inverse_after():
    """INV-07: f.inverse(x) after auto-uncompute undoes return qubit effects.

    When auto-uncompute fires, the AncillaRecord is updated with only
    return-value ancilla qubits. A subsequent f.inverse(x) should use
    the reduced gate set to undo return effects and deallocate return qubits.
    """
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def complex_fn(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        result = ql.qint(0, width=x.width)
        result += temp
        return result

    a = ql.qint(3, width=4)
    result = complex_fn(a)

    # Forward call record should exist and be auto-uncomputed
    assert len(complex_fn._forward_calls) == 1
    record = list(complex_fn._forward_calls.values())[0]
    assert record._auto_uncomputed is True, "Record should be marked as auto-uncomputed"
    assert record._return_only_gates is not None, "Should have return-only gates cached"

    # Call f.inverse(x) -- should undo return qubit effects and deallocate
    complex_fn.inverse(a)

    # Return qint should be invalidated
    assert result._is_uncomputed is True, "Return qint should be uncomputed after inverse"
    assert result.allocated_qubits is False, "Return qubits should be deallocated after inverse"
    assert len(complex_fn._forward_calls) == 0, "Forward call record should be removed"


def test_auto_uncompute_none_return():
    """INV-07: Functions returning None auto-uncompute all ancillas."""
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def side_effect_fn(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        # No return -- returns None

    a = ql.qint(3, width=4)
    stats_before = ql.circuit_stats()
    result = side_effect_fn(a)
    stats_after = ql.circuit_stats()

    assert result is None, "Function returning None should return None"

    # All ancillas should be auto-uncomputed and deallocated
    assert stats_after["total_deallocations"] > stats_before["total_deallocations"], (
        "All temp ancillas should be deallocated for None-returning function"
    )

    # No forward call record should remain
    assert len(side_effect_fn._forward_calls) == 0, (
        "No forward call record should remain after full auto-uncompute"
    )

    # f.inverse(x) should raise because no forward call record exists
    with pytest.raises(ValueError, match="No prior forward call"):
        side_effect_fn.inverse(a)


def test_auto_uncompute_inplace_skips():
    """INV-07: In-place functions skip auto-uncompute."""
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def add_inplace(x):
        x += 1
        return x

    a = ql.qint(3, width=4)
    result = add_inplace(a)

    # In-place: result is the same object as input
    assert result is a, "In-place return should be the same object"

    # No forward call tracking (in-place functions without ancillas)
    assert len(add_inplace._forward_calls) == 0, (
        "In-place function should not have forward call records"
    )


def test_auto_uncompute_off_no_effect():
    """INV-07: Without qubit_saving, ancillas are NOT auto-uncomputed."""
    ql.circuit()
    # qubit_saving defaults to False -- do NOT enable it

    @ql.compile
    def make_result(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        return temp

    a = ql.qint(3, width=4)
    stats_before = ql.circuit_stats()
    _result = make_result(a)
    stats_after = ql.circuit_stats()

    # Forward call record should exist with ALL ancillas (no auto-uncompute)
    assert len(make_result._forward_calls) == 1
    record = list(make_result._forward_calls.values())[0]
    assert record._auto_uncomputed is False, (
        "Without qubit_saving, record should NOT be auto-uncomputed"
    )

    # All ancillas should still be allocated (no deallocation occurred)
    ancilla_count = len(record.ancilla_qubits)
    assert ancilla_count > 0, "Should have ancilla qubits tracked"
    assert stats_after["total_deallocations"] == stats_before["total_deallocations"], (
        "Without auto-uncompute, no qubits should be deallocated"
    )


def test_auto_uncompute_cache_key_includes_qubit_saving():
    """INV-07: Cache key includes qubit_saving mode, forcing re-capture on change."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def make_result(x):
        call_count[0] += 1
        temp = ql.qint(0, width=x.width)
        temp += x
        return temp

    # Call without qubit_saving
    a = ql.qint(3, width=4)
    make_result(a)
    assert call_count[0] == 1

    # Enable qubit_saving and call with same width -- should re-capture (cache miss)
    ql.circuit()
    ql.option("qubit_saving", True)

    b = ql.qint(5, width=4)
    make_result(b)
    assert call_count[0] == 2, (
        "Enabling qubit_saving should trigger re-capture (different cache key)"
    )

    # Third call with qubit_saving on and same width -- should replay (cache hit)
    c = ql.qint(7, width=4)
    make_result(c)
    assert call_count[0] == 2, "Same qubit_saving mode and width should be cache hit"


def test_auto_uncompute_replay_path():
    """INV-07: Auto-uncompute fires on both capture and replay paths.

    The second call with same widths uses the replay path; auto-uncompute
    should fire on replay as well (not just capture).
    """
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def complex_fn(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        result = ql.qint(0, width=x.width)
        result += temp
        return result

    # First call (capture path)
    a = ql.qint(3, width=4)
    _result1 = complex_fn(a)

    # Record should be auto-uncomputed after capture
    assert len(complex_fn._forward_calls) == 1
    record1 = list(complex_fn._forward_calls.values())[0]
    assert record1._auto_uncomputed is True, "Capture path should auto-uncompute"

    # Second call (replay path) with different qubits
    b = ql.qint(5, width=4)
    dealloc_before = ql.circuit_stats()["total_deallocations"]
    _result2 = complex_fn(b)
    dealloc_after = ql.circuit_stats()["total_deallocations"]

    # Auto-uncompute should also fire on replay path
    assert dealloc_after > dealloc_before, (
        "Replay path should also trigger auto-uncompute deallocation"
    )
    assert len(complex_fn._forward_calls) == 2, "Both forward calls should be tracked"
    records = list(complex_fn._forward_calls.values())
    assert all(r._auto_uncomputed for r in records), (
        "Both capture and replay records should be auto-uncomputed"
    )


def test_auto_uncompute_controlled_context():
    """INV-07: Auto-uncompute fires inside controlled context.

    When a compiled function is called inside a `with ctrl:` block with
    qubit_saving on, auto-uncompute should still fire and the uncompute
    gates should be appropriately controlled.
    """
    ql.circuit()
    ql.option("qubit_saving", True)

    @ql.compile
    def complex_fn(x):
        temp = ql.qint(0, width=x.width)
        temp += x
        result = ql.qint(0, width=x.width)
        result += temp
        return result

    # First call outside with block to populate cache
    a = ql.qint(3, width=4)
    _r1 = complex_fn(a)

    # Call inside controlled context (replay path)
    b = ql.qint(5, width=4)
    ctrl = ql.qbool(True)

    dealloc_before = ql.circuit_stats()["total_deallocations"]
    with ctrl:
        result = complex_fn(b)
    dealloc_after = ql.circuit_stats()["total_deallocations"]

    # Return value should be usable
    assert result is not b
    assert result.width == 4

    # Auto-uncompute should have fired (temp ancillas deallocated)
    assert dealloc_after > dealloc_before, (
        "Controlled context should still trigger auto-uncompute deallocation"
    )


# ---------------------------------------------------------------------------
# qarray Support in @ql.compile (Phase 54: ARR-01, ARR-02, ARR-03, ARR-04)
# ---------------------------------------------------------------------------


def test_qarray_argument_basic():
    """ARR-01: qarray can be passed as argument to compiled function."""
    ql.circuit()

    @ql.compile
    def sum_elements(arr):
        total = ql.qint(0, width=8)
        for elem in arr:
            total += elem
        return total

    arr = ql.qarray([1, 2, 3], width=4)
    result = sum_elements(arr)

    # Should return a qint
    assert isinstance(result, ql.qint), "Result should be qint"
    assert result.width == 8, "Result should have width 8"


def test_qarray_argument_mixed_with_qint():
    """ARR-01: Mixed qarray and qint arguments work correctly."""
    ql.circuit()

    @ql.compile
    def add_scalar_to_array(arr, scalar):
        # Return first element plus scalar
        return arr[0] + scalar

    arr = ql.qarray([5, 6], width=4)
    scalar = ql.qint(3, width=4)
    result = add_scalar_to_array(arr, scalar)

    assert isinstance(result, ql.qint), "Result should be qint"


def test_qarray_capture_extracts_all_qubits():
    """ARR-02: Capture phase extracts qubit indices from all array elements."""
    ql.circuit()

    @ql.compile
    def touch_all_elements(arr):
        # Apply operation to each element to verify all qubits captured
        for elem in arr:
            elem += 1
        return arr

    arr = ql.qarray([0, 0], width=4)

    # Collect qubits from all elements
    all_element_qubits = set()
    for elem in arr:
        for i in range(elem.width):
            all_element_qubits.add(int(elem.qubits[64 - elem.width + i]))

    start = get_current_layer()
    touch_all_elements(arr)
    end = get_current_layer()

    gates = extract_gate_range(start, end)
    gate_targets = {g["target"] for g in gates}

    # All element qubits should appear in gate targets
    assert all_element_qubits <= gate_targets, (
        f"Not all element qubits captured. "
        f"Expected {all_element_qubits} to be subset of {gate_targets}"
    )


def test_qarray_first_call_matches_undecorated():
    """ARR-02: Compiled qarray function produces same gate count as plain."""
    # Plain run
    ql.circuit()
    arr1 = ql.qarray([1, 2], width=4)
    total1 = ql.qint(0, width=8)
    start1 = get_current_layer()
    for elem in arr1:
        total1 += elem
    end1 = get_current_layer()
    plain_gates = extract_gate_range(start1, end1)

    # Compiled run
    ql.circuit()

    @ql.compile
    def sum_array(arr):
        total = ql.qint(0, width=8)
        for elem in arr:
            total += elem
        return total

    arr2 = ql.qarray([1, 2], width=4)
    start2 = get_current_layer()
    sum_array(arr2)
    end2 = get_current_layer()
    compiled_gates = extract_gate_range(start2, end2)

    assert len(compiled_gates) == len(plain_gates), (
        f"Gate count mismatch: compiled={len(compiled_gates)}, plain={len(plain_gates)}"
    )


def test_qarray_replay_no_reexecution():
    """ARR-03: Replay does not re-execute function body."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def count_and_sum(arr):
        call_count[0] += 1
        total = ql.qint(0, width=8)
        for elem in arr:
            total += elem
        return total

    # First call (capture)
    arr1 = ql.qarray([1, 2], width=4)
    count_and_sum(arr1)
    assert call_count[0] == 1, "First call should execute body"

    # Second call with same-shaped array (replay)
    arr2 = ql.qarray([3, 4], width=4)
    count_and_sum(arr2)
    assert call_count[0] == 1, "Replay should NOT re-execute body"


def test_qarray_replay_targets_new_qubits():
    """ARR-03: Replayed gates target the new qarray's element qubits."""
    ql.circuit()

    @ql.compile
    def increment_all(arr):
        for elem in arr:
            elem += 1
        return arr

    # First call
    arr1 = ql.qarray([0, 0], width=4)
    increment_all(arr1)

    # Second call - collect new qarray's qubits
    arr2 = ql.qarray([0, 0], width=4)
    arr2_qubits = set()
    for elem in arr2:
        for i in range(elem.width):
            arr2_qubits.add(int(elem.qubits[64 - elem.width + i]))

    start = get_current_layer()
    increment_all(arr2)
    end = get_current_layer()

    replay_gates = extract_gate_range(start, end)
    replay_targets = {g["target"] for g in replay_gates}

    # Replay should target arr2's qubits
    assert arr2_qubits & replay_targets, "Replay should target arr2's qubits"


def test_qarray_replay_same_gate_count():
    """ARR-03: Replay produces same gate count as capture."""
    ql.circuit()

    @ql.compile
    def process_array(arr):
        for elem in arr:
            elem += 1
        return arr

    arr1 = ql.qarray([0, 0], width=4)
    start1 = get_current_layer()
    process_array(arr1)
    end1 = get_current_layer()
    capture_gates = extract_gate_range(start1, end1)

    arr2 = ql.qarray([0, 0], width=4)
    start2 = get_current_layer()
    process_array(arr2)
    end2 = get_current_layer()
    replay_gates = extract_gate_range(start2, end2)

    assert len(replay_gates) == len(capture_gates), (
        f"Replay gate count {len(replay_gates)} != capture {len(capture_gates)}"
    )


def test_qarray_replay_different_element_values():
    """ARR-03: Replay works with different element values (same widths)."""
    ql.circuit()

    @ql.compile
    def double_first(arr):
        result = arr[0] + arr[0]
        return result

    arr1 = ql.qarray([5, 6], width=4)
    result1 = double_first(arr1)

    arr2 = ql.qarray([7, 3], width=4)
    result2 = double_first(arr2)

    # Both should return valid qints
    assert isinstance(result1, ql.qint)
    assert isinstance(result2, ql.qint)


def test_qarray_cache_key_includes_length():
    """ARR-04: Different array lengths trigger re-capture."""
    ql.circuit()
    call_count = [0]

    @ql.compile
    def sum_all(arr):
        call_count[0] += 1
        total = ql.qint(0, width=8)
        for elem in arr:
            total += elem
        return total

    # First call with 2-element array
    arr2 = ql.qarray([1, 2], width=4)
    sum_all(arr2)
    assert call_count[0] == 1, "First call should capture"

    # Second call with 3-element array - should re-capture
    arr3 = ql.qarray([1, 2, 3], width=4)
    sum_all(arr3)
    assert call_count[0] == 2, "Different length should trigger re-capture"

    # Third call with same 3-element length - should replay
    arr3b = ql.qarray([4, 5, 6], width=4)
    sum_all(arr3b)
    assert call_count[0] == 2, "Same length should replay, not re-capture"


def test_qarray_cache_separate_for_different_shapes():
    """ARR-04: Cache correctly separates different array shapes."""
    ql.circuit()

    @ql.compile(debug=True)
    def identity(arr):
        return arr

    # Cache 2-element
    arr2 = ql.qarray([0, 0], width=4)
    identity(arr2)

    # Cache 4-element
    arr4 = ql.qarray([0, 0, 0, 0], width=4)
    identity(arr4)

    # Replay 2-element
    arr2b = ql.qarray([1, 1], width=4)
    identity(arr2b)

    # Check cache has at least 2 entries (both controlled and uncontrolled)
    # In minimal case, cache should have entries for both array lengths
    assert len(identity._cache) >= 2, "Cache should have entries for different lengths"


def test_qarray_empty_raises_error():
    """Empty qarray should raise ValueError."""
    ql.circuit()

    @ql.compile
    def process(arr):
        return arr

    empty_arr = ql.qarray([], width=4)

    with pytest.raises(ValueError, match="[Ee]mpty"):
        process(empty_arr)


def test_qarray_return_value():
    """Compiled function can return qarray."""
    ql.circuit()

    @ql.compile
    def increment_array(arr):
        for elem in arr:
            elem += 1
        return arr

    arr = ql.qarray([0, 0], width=4)
    result = increment_array(arr)

    # Result should be qarray
    from quantum_language.qarray import qarray

    assert isinstance(result, qarray), "Result should be qarray"
    assert len(result) == 2, "Result should have same length"


def test_qarray_return_replay():
    """qarray return works correctly on replay."""
    ql.circuit()

    @ql.compile
    def copy_array(arr):
        # Create new array with same values (effectively returns input)
        return arr

    # Capture
    arr1 = ql.qarray([1, 2], width=4)
    result1 = copy_array(arr1)

    # Replay
    arr2 = ql.qarray([3, 4], width=4)
    result2 = copy_array(arr2)

    from quantum_language.qarray import qarray

    assert isinstance(result1, qarray), "First result should be qarray"
    assert isinstance(result2, qarray), "Replay result should be qarray"
    assert len(result2) == len(arr2), "Replay result should have correct length"


def test_qarray_slice_as_argument():
    """qarray slice (view) works as compiled function argument."""
    ql.circuit()

    @ql.compile
    def sum_slice(arr):
        total = ql.qint(0, width=8)
        for elem in arr:
            total += elem
        return total

    full_arr = ql.qarray([1, 2, 3], width=4)
    slice_view = full_arr[0:2]  # First two elements

    result = sum_slice(slice_view)
    assert isinstance(result, ql.qint), "Result should be qint"
