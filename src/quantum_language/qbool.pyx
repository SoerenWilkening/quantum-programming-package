"""Quantum boolean - a 1-bit quantum integer."""

from quantum_language.qint cimport qint

cdef class qbool(qint):
	"""Quantum boolean - a 1-bit quantum integer.

	qbool is syntactic sugar for qint with width=1. All qint operations
	apply to qbool with single-bit semantics.

	Parameters
	----------
	value : bool, optional
		Initial value (default False). Encoded as |0> or |1>.
	classical : bool, optional
		Whether this is a classical boolean (default False).
	create_new : bool, optional
		Whether to allocate new qubit (default True).
	bit_list : array-like, optional
		External qubit (when create_new=False).

	Examples
	--------
	>>> b = qbool(True)   # Creates |1>
	>>> b.width
	1
	>>> c = qbool()       # Creates |0> (False by default)

	Notes
	-----
	Used for quantum conditionals via context manager (with statement).
	"""

	def __init__(self, value: bool = False, classical: bool = False, create_new = True, bit_list = None):
		"""Create quantum boolean.

		Parameters
		----------
		value : bool, optional
			Initial value (default False).
		classical : bool, optional
			Classical boolean flag (default False).
		create_new : bool, optional
			Allocate new qubit (default True).
		bit_list : array-like, optional
			External qubit array (when create_new=False).

		Examples
		--------
		>>> flag = qbool(True)
		>>> with flag:
		...     # Controlled operations
		"""
		super().__init__(value, width=1, classical=classical, create_new=create_new, bit_list=bit_list)
