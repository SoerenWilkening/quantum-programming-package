"""Iterative Quantum Amplitude Estimation (IQAE) module.

Provides ``ql.amplitude_estimate()`` that estimates the success probability
of a quantum oracle with configurable precision and confidence.  Uses the
QFT-free IQAE algorithm from Grinko, Gacon, Zoufal & Woerner (2021).

The algorithm iteratively runs Grover circuits with increasing powers and
narrows a confidence interval for the amplitude.  It achieves O(1/epsilon)
oracle calls (up to log factors) using only the standard Grover operator
(oracle + diffusion), requiring no QFT circuit.

Usage
-----
>>> import quantum_language as ql

Lambda predicate (auto-synthesized oracle):
>>> result = ql.amplitude_estimate(lambda x: x > 5, width=3, epsilon=0.01)
>>> print(result.estimate, result.num_oracle_calls)

Decorated oracle with predicate for classification:
>>> result = ql.amplitude_estimate(mark_five, width=3, predicate=lambda x: x == 5)
"""

import inspect
import math
import warnings

import numpy as np
from scipy.stats import beta

from ._core import circuit, option
from .compile import CompiledFunc
from .diffusion import diffusion
from .grover import (
    _apply_hadamard_layer,
    _ensure_oracle,
    _get_oracle_func,
    _get_quantum_params,
    _parse_bitstring,
    _resolve_widths,
    _verify_classically,
)
from .openqasm import to_openqasm
from .oracle import GroverOracle, _predicate_to_oracle
from .sim_backend import load_qasm, simulate

# ---------------------------------------------------------------------------
# Result class
# ---------------------------------------------------------------------------


class AmplitudeEstimationResult:
    """Result of amplitude estimation with float-like behavior.

    Wraps the estimated amplitude with metadata about the estimation
    process.  Supports arithmetic operations so the result can be used
    directly in numerical expressions.

    Parameters
    ----------
    estimate : float
        Estimated success probability (amplitude squared).
    num_oracle_calls : int
        Total number of oracle calls used during estimation.
    confidence_interval : tuple of float, optional
        ``(lower, upper)`` bounds of the final confidence interval.
    """

    def __init__(self, estimate, num_oracle_calls, confidence_interval=None):
        self._estimate = float(estimate)
        self._num_oracle_calls = int(num_oracle_calls)
        self._confidence_interval = confidence_interval

    @property
    def estimate(self):
        """float: Estimated success probability."""
        return self._estimate

    @property
    def num_oracle_calls(self):
        """int: Total oracle calls used during estimation."""
        return self._num_oracle_calls

    @property
    def confidence_interval(self):
        """tuple or None: ``(lower, upper)`` confidence interval bounds."""
        return self._confidence_interval

    # -- Float-like behavior ------------------------------------------------

    def __float__(self):
        return self._estimate

    def __int__(self):
        return int(self._estimate)

    def __round__(self, ndigits=None):
        return round(self._estimate, ndigits)

    def __bool__(self):
        return bool(self._estimate)

    # Arithmetic
    def __add__(self, other):
        return self._estimate + float(other)

    def __radd__(self, other):
        return float(other) + self._estimate

    def __sub__(self, other):
        return self._estimate - float(other)

    def __rsub__(self, other):
        return float(other) - self._estimate

    def __mul__(self, other):
        return self._estimate * float(other)

    def __rmul__(self, other):
        return float(other) * self._estimate

    def __truediv__(self, other):
        return self._estimate / float(other)

    def __rtruediv__(self, other):
        return float(other) / self._estimate

    def __neg__(self):
        return -self._estimate

    def __abs__(self):
        return abs(self._estimate)

    # Comparison
    def __eq__(self, other):
        try:
            return self._estimate == float(other)
        except (TypeError, ValueError):
            return NotImplemented

    def __lt__(self, other):
        return self._estimate < float(other)

    def __le__(self, other):
        return self._estimate <= float(other)

    def __gt__(self, other):
        return self._estimate > float(other)

    def __ge__(self, other):
        return self._estimate >= float(other)

    def __repr__(self):
        return (
            f"AmplitudeEstimationResult(estimate={self._estimate}, "
            f"num_oracle_calls={self._num_oracle_calls})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _simulate_multi_shot(qasm_str, shots):
    """Run multi-shot Qiskit simulation and return counts dict.

    Extends the ``_simulate_single_shot`` pattern from ``grover.py`` to
    support configurable shot counts for IQAE statistical estimation.

    Parameters
    ----------
    qasm_str : str
        OpenQASM 3.0 circuit string.
    shots : int
        Number of measurement shots.

    Returns
    -------
    dict
        Qiskit counts dictionary ``{bitstring: count}``.
    """
    circuit_qk = load_qasm(qasm_str)
    counts = simulate(circuit_qk, shots=shots)
    return counts


def _count_good_states(counts, register_widths, predicate):
    """Count measurement outcomes that satisfy the predicate.

    Parses each bitstring from the Qiskit counts dict using
    ``_parse_bitstring``, evaluates the classical ``predicate`` via
    ``_verify_classically``, and tallies good vs total counts.

    Parameters
    ----------
    counts : dict
        Qiskit measurement counts ``{bitstring: count}``.
    register_widths : list of int
        Width of each search register.
    predicate : callable
        Classical predicate function accepting integer values.

    Returns
    -------
    tuple of (int, int)
        ``(good_counts, total_shots)``.
    """
    good_counts = 0
    total_shots = 0
    for bitstring, count in counts.items():
        total_shots += count
        values = _parse_bitstring(bitstring, register_widths)
        if _verify_classically(predicate, values):
            good_counts += count
    return good_counts, total_shots


def _clopper_pearson_confint(counts, shots, alpha):
    """Compute Clopper-Pearson confidence interval for a binomial proportion.

    Uses ``scipy.stats.beta.ppf`` for the exact binomial confidence
    interval.  Handles edge cases where counts is 0 or equals shots.

    Parameters
    ----------
    counts : int
        Number of "good" outcomes.
    shots : int
        Total number of measurements.
    alpha : float
        Significance level (confidence interval is ``1 - alpha``).

    Returns
    -------
    tuple of (float, float)
        ``(lower, upper)`` bounds for the true probability.
    """
    lower = 0.0
    upper = 1.0
    if counts != 0:
        lower = beta.ppf(alpha / 2, counts, shots - counts + 1)
    if counts != shots:
        upper = beta.ppf(1 - alpha / 2, counts + 1, shots - counts)
    return lower, upper


def _find_next_k(k, upper_half_circle, theta_interval, min_ratio=2.0):
    """Find the next Grover power k for IQAE (Algorithm 2 from Grinko et al.).

    Finds the largest ``k_next`` such that the scaled theta interval
    stays within one half-circle, ensuring the arccos mapping remains
    well-defined.

    Parameters
    ----------
    k : int
        Current Grover power.
    upper_half_circle : bool
        Whether current interval is in the upper half-circle.
    theta_interval : list of float
        Current ``[theta_l, theta_u]`` normalized to ``[0, 1]``.
    min_ratio : float
        Minimum ratio ``K_next / K_current`` for convergence guarantee.

    Returns
    -------
    tuple of (int, bool)
        ``(next_power, upper_half_circle)``.
    """
    theta_l, theta_u = theta_interval
    old_scaling = 4 * k + 2

    # Maximum scaling bounded by interval width
    if theta_u - theta_l <= 0:
        return k, upper_half_circle

    max_scaling = int(1 / (2 * (theta_u - theta_l)))
    # Enforce form 4k+2: scaling = max_scaling - ((max_scaling - 2) % 4)
    scaling = max_scaling - (max_scaling - 2) % 4

    while scaling >= min_ratio * old_scaling:
        theta_min = scaling * theta_l - int(scaling * theta_l)
        theta_max = scaling * theta_u - int(scaling * theta_u)

        if theta_min <= theta_max <= 0.5 and theta_min <= 0.5:
            return int((scaling - 2) / 4), True
        elif theta_max >= 0.5 and theta_max >= theta_min >= 0.5:
            return int((scaling - 2) / 4), False

        scaling -= 4

    return k, upper_half_circle


def _update_theta_interval(theta_interval, a_min, a_max, k, upper_half_circle):
    """Refine theta interval from measured amplitude bounds.

    Maps measured probability bounds ``[a_min, a_max]`` through arccos
    to theta space, accounts for scaling factor ``K = 4k + 2``, and
    intersects with the previous interval.

    Parameters
    ----------
    theta_interval : list of float
        Current ``[theta_l, theta_u]`` in ``[0, 1]``.
    a_min : float
        Lower bound of measured probability confidence interval.
    a_max : float
        Upper bound of measured probability confidence interval.
    k : int
        Current Grover power.
    upper_half_circle : bool
        Whether the scaled interval is in the upper half-circle.

    Returns
    -------
    list of float
        Refined ``[theta_l, theta_u]``.
    """
    scaling = 4 * k + 2

    if upper_half_circle:
        theta_min_i = np.arccos(1 - 2 * a_min) / (2 * np.pi)
        theta_max_i = np.arccos(1 - 2 * a_max) / (2 * np.pi)
    else:
        theta_min_i = 1 - np.arccos(1 - 2 * a_max) / (2 * np.pi)
        theta_max_i = 1 - np.arccos(1 - 2 * a_min) / (2 * np.pi)

    # Unscale: combine with previous interval bounds
    theta_u = (int(scaling * theta_interval[1]) + theta_max_i) / scaling
    theta_l = (int(scaling * theta_interval[0]) + theta_min_i) / scaling

    return [theta_l, theta_u]


def _build_and_simulate(oracle, register_widths, k, shots):
    """Build a fresh circuit with k Grover iterations and simulate multi-shot.

    Each call creates a completely fresh ``circuit()`` to avoid stale state
    between IQAE rounds.  Reuses the circuit-building pattern from
    ``_run_grover_attempt`` in ``grover.py``.

    Parameters
    ----------
    oracle : GroverOracle
        The oracle marking target states.
    register_widths : list of int
        Width of each search register.
    k : int
        Number of Grover iterations to apply.
    shots : int
        Number of measurement shots.

    Returns
    -------
    dict
        Qiskit counts dictionary ``{bitstring: count}``.
    """
    from .qint import qint as qint_type

    # Fresh circuit for each round (required: global circuit state)
    circuit()
    option("fault_tolerant", True)
    option("simulate", True)

    # Allocate registers
    registers = [qint_type(0, width=w) for w in register_widths]

    # Initialize equal superposition
    for reg in registers:
        reg.branch(0.5)

    # Apply k Grover iterations
    for _ in range(k):
        oracle(*registers)
        _apply_hadamard_layer(registers)
        diffusion(*registers)
        _apply_hadamard_layer(registers)

    # Export and simulate multi-shot
    qasm = to_openqasm()
    return _simulate_multi_shot(qasm, shots)


# ---------------------------------------------------------------------------
# IQAE main loop
# ---------------------------------------------------------------------------


def _iqae_loop(oracle, register_widths, epsilon, alpha, max_iterations, predicate):
    """Run the Iterative Quantum Amplitude Estimation algorithm.

    Implements Algorithm 1 from Grinko et al. (2021).  Iteratively selects
    Grover powers, runs multi-shot circuits, computes confidence intervals,
    and refines theta bounds until the desired precision is reached.

    Parameters
    ----------
    oracle : GroverOracle
        The oracle marking target states.
    register_widths : list of int
        Width of each search register.
    epsilon : float
        Target precision (half-width of estimate interval).
    alpha : float
        Significance level (``1 - confidence_level``).
    max_iterations : int or None
        Cap on total oracle calls.  ``None`` means no cap.
    predicate : callable
        Classical predicate for good-state classification.

    Returns
    -------
    tuple of (float, int, tuple)
        ``(estimate, num_oracle_queries, (ci_lower, ci_upper))``.
    """
    min_ratio = 2.0

    # Initial theta interval: theta/2pi in [0, 1/4]
    theta_interval = [0.0, 0.25]
    upper_half_circle = True
    k = 0  # current Grover power

    # Compute max rounds for Bonferroni correction
    max_rounds = (
        int(math.ceil(math.log(min_ratio * math.pi / 8 / epsilon) / math.log(min_ratio))) + 1
    )
    max_rounds = max(max_rounds, 1)

    # Compute shots per round (from IQAE paper)
    # N_shots = ceil(32 / (1 - 2*sin(pi/14))^2 * ln(2 * max_rounds / alpha))
    denom = (1 - 2 * math.sin(math.pi / 14)) ** 2
    shots_per_round = int(math.ceil(32 / denom * math.log(2 * max_rounds / alpha)))
    shots_per_round = max(shots_per_round, 1)

    num_oracle_queries = 0

    while theta_interval[1] - theta_interval[0] > epsilon / math.pi:
        # Find next Grover power
        k, upper_half_circle = _find_next_k(k, upper_half_circle, theta_interval, min_ratio)

        # Build circuit and simulate
        counts = _build_and_simulate(oracle, register_widths, k, shots_per_round)

        # Count good states
        good_counts, total_shots = _count_good_states(counts, register_widths, predicate)

        # Track oracle queries: each shot at power k costs k oracle calls
        # (plus the initial superposition prep which doesn't count as oracle call)
        num_oracle_queries += shots_per_round * k

        # Check max_iterations cap on oracle calls
        if max_iterations is not None and num_oracle_queries > max_iterations:
            warnings.warn(
                f"max_iterations ({max_iterations}) reached before target precision "
                f"(epsilon={epsilon}). Returning best estimate after "
                f"{num_oracle_queries} oracle calls.",
                stacklevel=3,
            )
            break

        # Compute Clopper-Pearson confidence interval with Bonferroni correction
        a_min, a_max = _clopper_pearson_confint(good_counts, total_shots, alpha / max_rounds)

        # Refine theta interval
        theta_interval = _update_theta_interval(theta_interval, a_min, a_max, k, upper_half_circle)

    # Final estimate: midpoint of amplitude bounds
    a_l = np.sin(2 * np.pi * theta_interval[0]) ** 2
    a_u = np.sin(2 * np.pi * theta_interval[1]) ** 2
    estimate = (a_l + a_u) / 2
    confidence_interval = (float(a_l), float(a_u))

    return float(estimate), num_oracle_queries, confidence_interval


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def amplitude_estimate(
    oracle,
    *registers,
    width=None,
    widths=None,
    epsilon=0.01,
    confidence_level=0.95,
    max_iterations=None,
    predicate=None,
):
    """Estimate the success probability of a quantum oracle using IQAE.

    Runs the Iterative Quantum Amplitude Estimation algorithm to estimate
    the probability that a random input satisfies the oracle/predicate.
    Uses QFT-free IQAE variant (Grinko et al. 2021) with only Grover
    operator powers.

    Accepts the same oracle types as ``grover()``: ``@grover_oracle``
    decorated functions and lambda predicates.

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
        Target precision (half-width of estimate interval).
        Default is ``0.01``.
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
    AmplitudeEstimationResult
        Result object with ``.estimate`` (float), ``.num_oracle_calls``
        (int), and ``.confidence_interval`` (tuple).  Supports float-like
        arithmetic: ``float(result)``, ``result + 1.0``, etc.

    Raises
    ------
    ValueError
        If IQAE needs a classical predicate to classify measurement
        outcomes but none is available (decorated oracle without
        ``predicate`` kwarg).
    ValueError
        If both ``registers`` and ``width``/``widths`` are provided.

    Examples
    --------
    Lambda predicate:

    >>> result = ql.amplitude_estimate(lambda x: x > 5, width=3)
    >>> print(result.estimate)  # ~0.25 (2 out of 8 values satisfy x > 5)

    With explicit precision:

    >>> result = ql.amplitude_estimate(lambda x: x > 5, width=3, epsilon=0.05)

    Decorated oracle with predicate:

    >>> result = ql.amplitude_estimate(
    ...     mark_five, width=3, predicate=lambda x: x == 5
    ... )
    """
    # 0. Detect if oracle is a predicate (raw callable)
    is_predicate = not isinstance(oracle, GroverOracle | CompiledFunc) and callable(oracle)

    # Save original predicate for classical verification
    if is_predicate:
        classical_predicate = oracle
    elif predicate is not None:
        classical_predicate = predicate
    else:
        classical_predicate = None

    # 1. Resolve register widths from *registers or width/widths kwargs
    if registers:
        if width is not None or widths is not None:
            raise ValueError(
                "Cannot provide both positional register arguments and "
                "width/widths keyword arguments (ambiguous)."
            )
        register_widths = [r.width for r in registers]
    else:
        if is_predicate:
            param_names = list(inspect.signature(oracle).parameters.keys())
        else:
            param_names = _get_quantum_params(_get_oracle_func(oracle))
        register_widths = _resolve_widths(param_names, width, widths)

    # 2. Validate that we have a predicate for good-state classification
    if classical_predicate is None:
        raise ValueError(
            "IQAE requires a classical predicate to classify measurement "
            "outcomes as 'good' or 'bad'. For decorated oracles, pass "
            "predicate=lambda x: <condition> as a keyword argument. "
            "For lambda predicates, this is inferred automatically."
        )

    # 3. Synthesize oracle from predicate if needed
    if is_predicate:
        oracle = _predicate_to_oracle(oracle, register_widths)
    else:
        oracle = _ensure_oracle(oracle)

    # 4. Compute alpha from confidence_level
    alpha = 1.0 - confidence_level

    # 5. Warn about register width approaching simulator limit
    total_register_width = sum(register_widths)
    if total_register_width > 18:
        warnings.warn(
            f"Search register width sum ({total_register_width} qubits) is close to "
            f"the 21-qubit simulator limit. Ancilla overhead from predicate "
            f"evaluation may exceed the budget.",
            stacklevel=2,
        )

    # 6. Warn about unreasonably small epsilon
    if epsilon < 0.001:
        N = 1
        for w in register_widths:
            N *= 2**w
        warnings.warn(
            f"epsilon={epsilon} is very small. For a search space of size "
            f"{N}, this may require a large number of oracle calls. "
            f"Consider using epsilon >= 0.001 or setting max_iterations.",
            stacklevel=2,
        )

    # 7. Run IQAE
    estimate, num_oracle_queries, confidence_interval = _iqae_loop(
        oracle, register_widths, epsilon, alpha, max_iterations, classical_predicate
    )

    return AmplitudeEstimationResult(estimate, num_oracle_queries, confidence_interval)
