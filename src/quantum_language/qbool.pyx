"""Quantum boolean - a 1-bit quantum integer."""

from .qint cimport qint

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

	def copy(self):
		"""Create a quantum copy of this boolean.

		Returns a new qbool with fresh qubit CNOT-entangled to this boolean's
		qubit. The copy measures to the same value as the source for
		computational basis states.

		Returns
		-------
		qbool
			New quantum boolean with copied state.

		Examples
		--------
		>>> flag = qbool(True)
		>>> flag_copy = flag.copy()
		>>> flag_copy.width
		1
		"""
		# Use qint.copy() for the CNOT logic
		cdef qint result_qint = qint.copy(self)
		# Wrap in qbool using existing qubit (no new allocation)
		# Access qubits via cdef-level (qubits is cdef object, not public)
		result = qbool(create_new=False, bit_list=result_qint.qubits[63:64])
		# Carry over layer tracking metadata from the intermediate result
		result._start_layer = result_qint._start_layer
		result._end_layer = result_qint._end_layer
		result.operation_type = result_qint.operation_type
		result.dependency_parents = result_qint.dependency_parents
		# Transfer qubit ownership so uncomputation works correctly
		result.allocated_start = result_qint.allocated_start
		result.allocated_qubits = True
		result_qint.allocated_qubits = False
		return result
