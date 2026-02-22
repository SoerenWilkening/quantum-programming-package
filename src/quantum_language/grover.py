"""Grover search algorithm end-to-end API.

Provides ql.grover() that composes oracle + diffusion into a complete
Grover search: creates circuit, initializes superposition, runs optimal
iterations, simulates via Qiskit, and returns measured Python value(s).

Supports three calling styles:

1. Decorated oracle (Phase 79):
   >>> value, k = ql.grover(mark_five, width=3)

2. Lambda predicate (Phase 80):
   >>> value, k = ql.grover(lambda x: x > 5, width=3)

3. Compound predicate:
   >>> value, k = ql.grover(lambda x: (x > 10) & (x < 50), width=6)

4. Explicit registers:
   >>> x = ql.qint(0, width=3)
   >>> value, k = ql.grover(lambda x: x > 5, x)

5. Multi-register predicate:
   >>> x_val, y_val, k = ql.grover(lambda x, y: x + y == 10, widths=[4, 4])
"""

import inspect
import math

from ._core import circuit, option
from ._gates import emit_h
from .compile import CompiledFunc
from .diffusion import _collect_qubits, diffusion
from .openqasm import to_openqasm
from .oracle import GroverOracle, _predicate_to_oracle, grover_oracle

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_oracle_func(oracle):
    """Extract the original function from an oracle wrapper.

    Parameters
    ----------
    oracle : GroverOracle, CompiledFunc, or callable
        The oracle to extract the underlying function from.

    Returns
    -------
    callable
        The original Python function (for introspection).

    Raises
    ------
    TypeError
        If the argument is not a recognized oracle type.
    """
    if isinstance(oracle, GroverOracle):
        return oracle._original_func
    elif isinstance(oracle, CompiledFunc):
        return oracle._func
    elif callable(oracle):
        return oracle
    raise TypeError(f"Expected oracle function, got {type(oracle)}")


def _get_quantum_params(func):
    """Introspect oracle function to find quantum parameter names.

    Each parameter annotated as ``qint`` (or missing annotation) is
    treated as a quantum parameter that corresponds to a search register.

    Parameters
    ----------
    func : callable
        The original oracle function.

    Returns
    -------
    list[str]
        Names of quantum parameters.
    """
    from .qint import qint

    sig = inspect.signature(func)
    quantum_params = []
    for name, param in sig.parameters.items():
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            # No annotation -- assume quantum parameter
            quantum_params.append(name)
        elif annotation is qint or (isinstance(annotation, type) and issubclass(annotation, qint)):
            quantum_params.append(name)
        elif isinstance(annotation, str) and annotation in ("qint", "ql.qint"):
            quantum_params.append(name)
    return quantum_params


def _resolve_widths(param_names, width, widths):
    """Resolve register widths from user-provided arguments.

    Parameters
    ----------
    param_names : list[str]
        Quantum parameter names from oracle introspection.
    width : int or None
        Single width applied to all registers.
    widths : list[int] or None
        Per-register widths.

    Returns
    -------
    list[int]
        Width for each register.

    Raises
    ------
    ValueError
        If neither ``width`` nor ``widths`` is provided, or if both are
        provided and inconsistent.
    """
    n_params = len(param_names)
    if widths is not None:
        if len(widths) != n_params:
            raise ValueError(
                f"widths has {len(widths)} entries but oracle has "
                f"{n_params} quantum parameters ({param_names})"
            )
        if width is not None:
            # Both provided -- check consistency
            expected = [width] * n_params
            if list(widths) != expected:
                raise ValueError(f"width={width} and widths={widths} are inconsistent")
        return list(widths)
    if width is not None:
        return [width] * n_params
    raise ValueError("width or widths required (qint annotations do not carry width info)")


def _grover_iterations(N, M):
    """Calculate optimal Grover iteration count.

    Formula: ``floor(pi/4 * sqrt(N/M) - 0.5)``

    Parameters
    ----------
    N : int
        Total search space size.
    M : int
        Number of marked solutions.

    Returns
    -------
    int
        Optimal number of Grover iterations.
    """
    if M <= 0 or M >= N:
        return 0
    return int(math.floor(math.pi / 4 * math.sqrt(N / M) - 0.5))


def _ensure_oracle(oracle):
    """Ensure *oracle* is a ``GroverOracle`` instance.

    If the argument is already a ``GroverOracle`` it is returned as-is.
    Otherwise it is wrapped via ``grover_oracle()`` which handles both
    ``CompiledFunc`` and plain callables.

    Parameters
    ----------
    oracle : GroverOracle, CompiledFunc, or callable
        The oracle to wrap.

    Returns
    -------
    GroverOracle
    """
    if isinstance(oracle, GroverOracle):
        return oracle
    # Auto-wrap with validate=False because the standard phase oracle
    # pattern (x.phase += pi inside `with flag:`) emits P gate on the
    # comparison ancilla, not on search register qubits, which triggers
    # a false positive in compute-phase-uncompute validation.
    return grover_oracle(oracle, validate=False)


def _apply_hadamard_layer(registers):
    """Apply H gate to every qubit in all *registers*.

    Uses ``emit_h`` (true Hadamard) instead of ``branch(0.5)`` (Ry)
    because H^2 = I while Ry(pi/2)^2 != I.  The H-sandwich in Grover
    iterations requires actual Hadamard gates for correct diffusion.

    Parameters
    ----------
    registers : list[qint]
        Quantum registers whose qubits receive H gates.
    """
    qubits = _collect_qubits(*registers)
    for q in qubits:
        emit_h(q)


def _parse_bitstring(bitstring, register_widths):
    """Parse Qiskit measurement bitstring into register values.

    Qiskit uses big-endian bitstrings with respect to qubit indices:
    ``bitstring[0]`` corresponds to the highest-numbered qubit, and
    ``bitstring[-1]`` corresponds to ``q[0]``.  Search registers are
    allocated first (``q[0..w1-1]``, ``q[w1..w1+w2-1]``, etc.) so their
    bits are the *rightmost* portion of the bitstring.

    Parameters
    ----------
    bitstring : str
        Measurement bitstring from Qiskit (e.g. ``'010 110'``).
    register_widths : list[int]
        Width of each search register.

    Returns
    -------
    tuple[int, ...]
        Integer value measured in each register.
    """
    # Qiskit may insert spaces in bitstrings -- strip them
    bitstring = bitstring.replace(" ", "")

    values = []
    bit_offset = 0  # offset from the right (LSB) of the bitstring
    for width in register_widths:
        start = len(bitstring) - bit_offset - width
        end = len(bitstring) - bit_offset
        register_bits = bitstring[start:end]
        value = int(register_bits, 2)
        values.append(value)
        bit_offset += width
    return tuple(values)


def _simulate_single_shot(qasm_str, register_widths):
    """Run single-shot Qiskit simulation and return measured values.

    Parameters
    ----------
    qasm_str : str
        OpenQASM 3.0 circuit string.
    register_widths : list[int]
        Width of each search register.

    Returns
    -------
    tuple[int, ...]
        Integer value measured in each register.
    """
    import qiskit.qasm3
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    circuit_qk = qiskit.qasm3.loads(qasm_str)
    if not circuit_qk.cregs:
        circuit_qk.measure_all()
    sim = AerSimulator(max_parallel_threads=4)
    result = sim.run(transpile(circuit_qk, sim), shots=1).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]
    return _parse_bitstring(bitstring, register_widths)


# ---------------------------------------------------------------------------
# Classical verification helper
# ---------------------------------------------------------------------------


def _verify_classically(predicate, measured_values):
    """Evaluate predicate with classical Python int values.

    Used for post-measurement verification in adaptive BBHT search (Plan 02)
    and can be used by user code for debugging.

    Parameters
    ----------
    predicate : callable
        The original predicate function (e.g. ``lambda x: x > 5``).
    measured_values : tuple[int, ...]
        Integer values measured from each search register.

    Returns
    -------
    bool
        Whether the measured values satisfy the predicate.
    """
    if len(measured_values) == 1:
        return bool(predicate(measured_values[0]))
    return bool(predicate(*measured_values))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def grover(oracle, *registers, width=None, widths=None, m=None, iterations=None, max_attempts=None):
    """Execute Grover's search algorithm and return measured result.

    Composes oracle + diffusion into a complete Grover search: creates a
    fresh circuit, infers register parameters from the oracle signature,
    initializes equal superposition, applies the optimal number of
    oracle + diffusion iterations, simulates with Qiskit, and returns
    the measured value(s).

    Supports three oracle styles:

    1. **Decorated oracle** (Phase 79 -- existing):
       Pass a ``@ql.grover_oracle`` or ``@ql.compile`` decorated function.

    2. **Lambda/callable predicate** (Phase 80 -- new):
       Pass a Python callable that accepts qint arguments and returns
       a qbool via comparison operators.

    3. **Explicit registers** (Phase 80 -- new):
       Pass positional qint arguments after the oracle to use existing
       registers instead of allocating new ones.

    Parameters
    ----------
    oracle : GroverOracle, CompiledFunc, or callable
        The oracle marking target states.  If a plain callable (lambda,
        named function, method), it is automatically synthesized into a
        ``GroverOracle`` via tracing.
    *registers : qint
        Optional positional qint arguments.  If provided, their widths
        are used instead of ``width``/``widths`` kwargs.  Cannot be
        combined with ``width`` or ``widths``.
    width : int, optional
        Width (in qubits) for all search registers.
    widths : list[int], optional
        Per-register widths (for multi-register oracles).
    m : int, optional
        Number of marked solutions.  When ``None`` (default), defaults
        to ``m=1`` for now.
        # TODO: Plan 02 will add BBHT adaptive search when m is None
    iterations : int, optional
        Explicit iteration count (overrides auto-calculation).
    max_attempts : int, optional
        Maximum BBHT attempts (Plan 02).  Currently unused.

    Returns
    -------
    tuple
        ``(value, iterations)`` for single-register oracles, or
        ``(x_val, y_val, ..., iterations)`` for multi-register oracles.
        The last element is always the iteration count used.

    Raises
    ------
    ValueError
        If both ``registers`` and ``width``/``widths`` are provided, or
        if width information cannot be determined.

    Examples
    --------
    Decorated oracle (existing):

    >>> value, k = ql.grover(mark_five, width=3)

    Lambda predicate:

    >>> value, k = ql.grover(lambda x: x > 5, width=3)

    Compound predicate:

    >>> value, k = ql.grover(lambda x: (x > 10) & (x < 50), width=6)

    Explicit registers:

    >>> value, k = ql.grover(lambda x: x > 5, x)

    Multi-register:

    >>> x_val, y_val, k = ql.grover(lambda x, y: x + y == 10, widths=[4, 4])
    """
    from .qint import qint as qint_type

    # 0. Detect if oracle is a predicate (raw callable, not GroverOracle/CompiledFunc)
    is_predicate = not isinstance(oracle, GroverOracle | CompiledFunc) and callable(oracle)

    # Save the original predicate callable for classical verification (Plan 02 BBHT)
    predicate = oracle if is_predicate else None  # noqa: F841

    # 1. Resolve register widths from *registers or width/widths kwargs
    if registers:
        # Explicit qint registers provided as positional args
        if width is not None or widths is not None:
            raise ValueError(
                "Cannot provide both positional register arguments and "
                "width/widths keyword arguments (ambiguous)."
            )
        register_widths = [r.width for r in registers]
    else:
        # Use width/widths kwargs -- need oracle introspection for param count
        if is_predicate:
            # For predicates, use inspect.signature to find param count
            param_names = list(inspect.signature(oracle).parameters.keys())
        else:
            # For decorated oracles, use existing introspection
            param_names = _get_quantum_params(_get_oracle_func(oracle))
        register_widths = _resolve_widths(param_names, width, widths)

    # 2. Synthesize oracle from predicate if needed
    if is_predicate:
        oracle = _predicate_to_oracle(oracle, register_widths)
    else:
        oracle = _ensure_oracle(oracle)

    # 3. Default m to 1 when None (Plan 01 backwards-compatibility placeholder)
    # TODO: Plan 02 will add BBHT adaptive search when m is None
    if m is None:
        m = 1

    # 4. Calculate total search space size and iteration count
    N = 1
    for w in register_widths:
        N *= 2**w
    if iterations is not None:
        k = iterations
    else:
        k = _grover_iterations(N, m)

    # 5. Build circuit
    circuit()
    option("fault_tolerant", True)

    # 6. Create fresh registers (all initialized to |0>)
    # Even if explicit *registers were passed, we always build a fresh circuit
    # and allocate fresh qints inside grover(). The explicit registers were
    # only used to extract widths above.
    registers = [qint_type(0, width=w) for w in register_widths]

    # 7. Initialize equal superposition (branch(0.5) on |0> is correct)
    for reg in registers:
        reg.branch(0.5)

    # 8. Apply k Grover iterations
    for _ in range(k):
        # Oracle application -- phase flip marked states
        oracle(*registers)
        # Diffusion: H^n - S_0 - H^n
        _apply_hadamard_layer(registers)
        diffusion(*registers)
        _apply_hadamard_layer(registers)

    # 9. Export and simulate
    qasm = to_openqasm()
    values = _simulate_single_shot(qasm, register_widths)

    # 10. Return flat tuple with iteration count last
    return (*values, k)
