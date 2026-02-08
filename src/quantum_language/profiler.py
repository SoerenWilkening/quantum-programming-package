"""Profiling utilities for quantum circuit generation.

This module provides a user-friendly context manager for profiling
quantum operations using Python's cProfile.

Usage:
    import quantum_language as ql

    with ql.profile() as stats:
        a = ql.qint(5, width=8)
        b = a + 3

    print(stats.report())
"""

import cProfile
import pstats
from contextlib import contextmanager
from io import StringIO


class ProfileStats:
    """Container for profiling results.

    Wraps cProfile.Profile with convenience methods for extracting
    and displaying profiling statistics.

    Attributes
    ----------
    _profiler : cProfile.Profile
        The underlying profiler instance.
    """

    def __init__(self):
        """Initialize a new ProfileStats container."""
        self._profiler = cProfile.Profile()

    def report(self, sort_key="cumulative", limit=20):
        """Generate human-readable profiling report.

        Parameters
        ----------
        sort_key : str, optional
            Sort criterion for results. Options:
            - 'cumulative': Time including subcalls (default)
            - 'tottime': Time excluding subcalls
            - 'calls': Number of calls
            - 'ncalls': Same as calls
            - 'filename': Source file
            - 'name': Function name
        limit : int, optional
            Maximum number of functions to show (default 20).

        Returns
        -------
        str
            Formatted profiling report.
        """
        stream = StringIO()
        stats = pstats.Stats(self._profiler, stream=stream)
        stats.sort_stats(sort_key)
        stats.print_stats(limit)
        return stream.getvalue()

    def top_functions(self, n=10, sort_key="cumulative"):
        """Get top N functions by time.

        Parameters
        ----------
        n : int, optional
            Number of functions to return (default 10).
        sort_key : str, optional
            Sort criterion (default 'cumulative').

        Returns
        -------
        list of tuple
            List of (name, stats_dict) tuples.
        """
        stats = pstats.Stats(self._profiler)
        stats.sort_stats(sort_key)
        # stats.stats is dict: (filename, line, name) -> (calls, ncalls, tottime, cumtime, callers)
        items = list(stats.stats.items())[:n]
        return [
            (
                f"{k[0]}:{k[1]}({k[2]})",
                {
                    "calls": v[0],
                    "tottime": v[2],
                    "cumtime": v[3],
                },
            )
            for k, v in items
        ]

    def save(self, filename):
        """Save profiling data to file.

        Parameters
        ----------
        filename : str
            Output file path (typically .prof extension).
        """
        self._profiler.dump_stats(filename)


@contextmanager
def profile():
    """Profile quantum operations within a context block.

    A convenience wrapper around cProfile.Profile that provides
    a clean context manager interface with built-in statistics.

    Yields
    ------
    ProfileStats
        Container with profiling methods (report, top_functions, save).

    Examples
    --------
    Basic usage:

    >>> import quantum_language as ql
    >>> with ql.profile() as stats:
    ...     c = ql.circuit()
    ...     a = ql.qint(5, width=8)
    ...     b = a + 3
    >>> print(stats.report())

    Save for visualization with snakeviz:

    >>> with ql.profile() as stats:
    ...     # ... operations ...
    ...     pass
    >>> stats.save('profile.prof')
    # Then: snakeviz profile.prof

    Get top functions:

    >>> for name, info in stats.top_functions(5):
    ...     print(f"{name}: {info['cumtime']:.3f}s")
    """
    ps = ProfileStats()
    ps._profiler.enable()
    try:
        yield ps
    finally:
        ps._profiler.disable()


__all__ = ["profile", "ProfileStats"]
