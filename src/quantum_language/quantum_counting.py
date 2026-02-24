"""Quantum counting module — estimate the number of solutions to a search problem.

Provides ``ql.count_solutions()`` that wraps the existing IQAE amplitude
estimation to convert an amplitude estimate into an integer solution count.
Returns a ``CountResult`` object with ``.count``, ``.estimate``,
``.count_interval``, ``.search_space``, and ``.num_oracle_calls`` attributes.

The function delegates entirely to ``amplitude_estimate()`` and applies
amplitude-to-count conversion: ``count = round(N * amplitude)`` where
``N = 2^width`` is the search space size.

Usage
-----
>>> import quantum_language as ql

Lambda predicate (auto-synthesized oracle):
>>> result = ql.count_solutions(lambda x: x > 5, width=3)
>>> print(result.count, result.search_space)  # ~2, 8

Decorated oracle with predicate:
>>> result = ql.count_solutions(mark_five, width=3, predicate=lambda x: x == 5)
>>> print(result.count)  # ~1
"""

import inspect
import math

from .amplitude_estimation import amplitude_estimate
from .compile import CompiledFunc
from .grover import _get_oracle_func, _get_quantum_params, _resolve_widths
from .oracle import GroverOracle

# ---------------------------------------------------------------------------
# Result class
# ---------------------------------------------------------------------------


class CountResult:
    """Result of quantum counting with int-like behavior.

    Wraps an amplitude estimation result, converting the estimated amplitude
    to an integer solution count.  Supports arithmetic operations so the
    result can be used directly in numerical expressions.

    Parameters
    ----------
    amplitude_result : AmplitudeEstimationResult
        Result from ``amplitude_estimate()``.
    search_space : int
        Total search space size ``N`` (typically ``2^width``).
    """

    def __init__(self, amplitude_result, search_space):
        N = search_space
        a = amplitude_result.estimate
        ci = amplitude_result.confidence_interval

        self._count = max(0, min(N, round(N * a)))
        self._estimate = N * a
        self._search_space = N
        self._num_oracle_calls = amplitude_result.num_oracle_calls

        if ci is not None:
            self._count_interval = (
                max(0, math.floor(N * ci[0])),
                min(N, math.ceil(N * ci[1])),
            )
        else:
            self._count_interval = (self._count, self._count)

    @property
    def count(self):
        """int: Rounded integer solution count clamped to [0, N]."""
        return self._count

    @property
    def estimate(self):
        """float: Raw unrounded count estimate (N * amplitude)."""
        return self._estimate

    @property
    def count_interval(self):
        """tuple of (int, int): Conservative integer bounds ``(floor(N*a_low), ceil(N*a_high))``."""
        return self._count_interval

    @property
    def search_space(self):
        """int: Total search space size N."""
        return self._search_space

    @property
    def num_oracle_calls(self):
        """int: Total oracle calls used during estimation."""
        return self._num_oracle_calls

    # -- Int-like behavior --------------------------------------------------

    def __int__(self):
        return self._count

    def __float__(self):
        return self._estimate

    def __round__(self, ndigits=None):
        return round(self._count, ndigits)

    def __bool__(self):
        return bool(self._count)

    # Arithmetic
    def __add__(self, other):
        return self._count + int(other)

    def __radd__(self, other):
        return int(other) + self._count

    def __sub__(self, other):
        return self._count - int(other)

    def __rsub__(self, other):
        return int(other) - self._count

    def __mul__(self, other):
        return self._count * int(other)

    def __rmul__(self, other):
        return int(other) * self._count

    def __truediv__(self, other):
        return self._count / other

    def __rtruediv__(self, other):
        return other / self._count

    def __neg__(self):
        return -self._count

    def __abs__(self):
        return abs(self._count)

    # Comparison
    def __eq__(self, other):
        try:
            return self._count == int(other)
        except (TypeError, ValueError):
            return NotImplemented

    def __lt__(self, other):
        return self._count < int(other)

    def __le__(self, other):
        return self._count <= int(other)

    def __gt__(self, other):
        return self._count > int(other)

    def __ge__(self, other):
        return self._count >= int(other)

    def __repr__(self):
        return (
            f"CountResult(count={self._count}, "
            f"estimate={self._estimate:.4f}, "
            f"search_space={self._search_space})"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def count_solutions(
    oracle,
    *registers,
    width=None,
    widths=None,
    epsilon=0.01,
    confidence_level=0.95,
    max_iterations=None,
    predicate=None,
):
    """Estimate the number of solutions to a search problem via quantum counting.

    Wraps ``amplitude_estimate()`` (IQAE) and converts the estimated amplitude
    to an integer solution count.  The search space size ``N = 2^(sum of widths)``
    is used to map amplitude ``a`` to count ``M = round(N * a)``.

    Accepts the same oracle types as ``grover()`` and ``amplitude_estimate()``:
    ``@grover_oracle`` decorated functions and lambda predicates.

    Parameters
    ----------
    oracle : GroverOracle, CompiledFunc, or callable
        The oracle marking target states.  If a plain callable (lambda,
        named function), it is auto-synthesized into a ``GroverOracle``
        via tracing (same as ``grover()``).
    *registers : qint
        Optional positional qint arguments.  If provided, their widths
        are used instead of ``width``/``widths`` kwargs.
    width : int, optional
        Width (in qubits) for all search registers.
    widths : list of int, optional
        Per-register widths (for multi-register oracles).
    epsilon : float, optional
        Target precision for the amplitude estimate (half-width of
        estimate interval).  Controls amplitude precision -- passed
        through to IQAE directly.  Default is ``0.01``.
    confidence_level : float, optional
        Confidence level for the estimate.  Default is ``0.95`` (95%).
    max_iterations : int, optional
        Cap on total oracle calls.  When reached before target precision,
        a warning is emitted and the best estimate is returned.
    predicate : callable, optional
        Classical predicate for classifying measurement outcomes as
        "good" or "bad".  Required for decorated oracles (``@grover_oracle``).
        For lambda/callable oracles, this is inferred automatically.

    Returns
    -------
    CountResult
        Result object with ``.count`` (int), ``.estimate`` (float),
        ``.count_interval`` (tuple), ``.search_space`` (int), and
        ``.num_oracle_calls`` (int).  Supports int-like arithmetic:
        ``int(result)``, ``result + 1``, ``result == 3``, etc.

    Raises
    ------
    ValueError
        If IQAE needs a classical predicate but none is available.
    ValueError
        If both ``registers`` and ``width``/``widths`` are provided.

    Examples
    --------
    Single-solution oracle:

    >>> result = ql.count_solutions(lambda x: x == 5, width=3)
    >>> print(result.count)  # 1

    Multi-solution oracle:

    >>> result = ql.count_solutions(lambda x: x > 5, width=3)
    >>> print(result.count)  # 2 (x=6 and x=7)

    With explicit precision:

    >>> result = ql.count_solutions(lambda x: x > 5, width=3, epsilon=0.05)
    """
    # Resolve register widths (needed for computing N)
    is_predicate = not isinstance(oracle, GroverOracle | CompiledFunc) and callable(oracle)

    if registers:
        register_widths = [r.width for r in registers]
    else:
        if is_predicate:
            param_names = list(inspect.signature(oracle).parameters.keys())
        else:
            param_names = _get_quantum_params(_get_oracle_func(oracle))
        register_widths = _resolve_widths(param_names, width, widths)

    # Compute search space size N
    N = 1
    for w in register_widths:
        N *= 2**w

    # Delegate to amplitude_estimate
    ae_result = amplitude_estimate(
        oracle,
        *registers,
        width=width,
        widths=widths,
        epsilon=epsilon,
        confidence_level=confidence_level,
        max_iterations=max_iterations,
        predicate=predicate,
    )

    return CountResult(ae_result, N)
