import sys
import warnings

import numpy as np
# cimport numpy as np

INTEGERSIZE = 8
NUMANCILLY = 2 * 64  # Max possible ancilla (2 * max_width)

QPU_state[0].R0 = <int *> malloc(sizeof(int))

QUANTUM = 0
CLASSICAL = 1

cdef circuit_t *_circuit
cdef bint _circuit_initialized = False
cdef int _num_qubits = 0

cdef bint _controlled = False
cdef object _control_bool = None
cdef int _int_counter = 0
cdef object list_of_constrols = []

cdef unsigned int _smallest_allocated_qubit = 0

# cdef unsigned int * qubit_array = <unsigned int *> malloc(6 * INTEGERSIZE)

qubit_array = np.ndarray(4 * 64 + NUMANCILLY, dtype = np.uint32)  # Max width support
ancilla = np.ndarray(NUMANCILLY, dtype = np.uint32)
for i in range(NUMANCILLY):
	ancilla[i] = i


def array(dim: int | tuple[int, int] | list[int], dtype = qint) -> list[qint | qbool]:
	if type(dim) == list:
		return [dtype(j) for j in dim]
	if type(dim) == tuple:
		return [[dtype() for j in range(dim[1])] for i in range(dim[0])]

	return [dtype() for j in range(dim)]


cdef class circuit:
	def __init__(self):
		global _circuit_initialized, _circuit, _num_qubits
		if not _circuit_initialized:
			_circuit = init_circuit()
		_circuit_initialized = True

	def add_qubits(self, qubits):
		global _num_qubits
		_num_qubits += qubits

	# def __str__(self):
	# 	print_circuit(_circuit)
	# 	return ""

	def __dealloc__(self):
		pass


cdef class qint(circuit):
	cdef int counter
	cdef int bits
	cdef int value
	cdef object qubits
	cdef bint allocated_qubits
	cdef unsigned int allocated_start  # Starting qubit index from allocator

	def __init__(self, value = 0, width = None, bits = None, classical = False, create_new = True, bit_list = None):
		"""Create a quantum integer.

		Args:
			value: Initial value (default 0)
			width: Bit width (1-64, default 8) - primary parameter
			bits: Bit width alias for backward compatibility
			classical: Whether this is a classical integer
			create_new: Whether to allocate new qubits
			bit_list: External qubit list (when create_new=False)

		Raises:
			ValueError: If width < 1 or width > 64

		Examples:
			qint(5)          - 8-bit quantum integer with value 5 (default)
			qint(5, width=16) - 16-bit quantum integer with value 5
			qint(5, bits=16)  - backward compatible alias for width
		"""
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits
		cdef qubit_allocator_t *alloc
		cdef unsigned int start
		cdef int actual_width

		super().__init__()

		# Handle width/bits parameter (width takes precedence, bits for backward compat)
		if width is None and bits is None:
			actual_width = INTEGERSIZE  # Default 8 bits
		elif width is not None:
			actual_width = width
		else:
			actual_width = bits  # Backward compatibility

		# Width validation
		if actual_width < 1 or actual_width > 64:
			raise ValueError(f"Width must be 1-64, got {actual_width}")

		if create_new:
			_int_counter += 1
			self.counter = _int_counter
			self.bits = actual_width
			self.value = value

			# Warn if value exceeds width (two's complement range)
			# Note: For 1-bit (qbool), treat as unsigned [0,1] for clarity
			if value != 0:
				if actual_width == 1:
					# Single bit: unsigned range [0, 1]
					max_value = 1
					min_value = 0
				else:
					# Multi-bit: signed range
					max_value = (1 << (actual_width - 1)) - 1
					min_value = -(1 << (actual_width - 1))
				if value > max_value or value < min_value:
					warnings.warn(
						f"Value {value} exceeds {actual_width}-bit range [{min_value}, {max_value}]. "
						f"Value will wrap (modular arithmetic).",
						UserWarning
					)

			_num_qubits += actual_width

			self.qubits = np.ndarray(64, dtype = np.uint32)  # Max width support

			# NEW: Allocate qubits through circuit's allocator
			alloc = circuit_get_allocator(<circuit_s*>_circuit)
			if alloc == NULL:
				raise RuntimeError("Circuit allocator not initialized")

			start = allocator_alloc(alloc, actual_width, True)  # is_ancilla=True
			if start == <unsigned int>-1:
				raise MemoryError("Qubit allocation failed - limit exceeded")

			# Right-aligned qubit storage: indices [64-width] through [63]
			for i in range(actual_width):
				self.qubits[64 - actual_width + i] = start + i

			self.allocated_start = start  # Track for deallocation
			self.allocated_qubits = True

			# Keep backward compat tracking (deprecated, remove later)
			# Note: _smallest_allocated_qubit and ancilla numpy array still updated
			# for any code that might still use them
			_smallest_allocated_qubit += actual_width
			ancilla += actual_width
		else:
			self.bits = actual_width
			self.qubits = bit_list
			self.allocated_qubits = False

	@property
	def width(self):
		"""Get the bit width of this quantum integer (read-only).

		Returns:
			int: Bit width (1-64)

		Examples:
			>>> a = qint(5, width=16)
			>>> a.width
			16
		"""
		return self.bits

	def print_circuit(self):
		print_circuit(_circuit)

	def __del__(self):
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits
		cdef qubit_allocator_t *alloc

		if self.allocated_qubits:
			# NEW: Return qubits to allocator
			alloc = circuit_get_allocator(<circuit_s*>_circuit)
			if alloc != NULL:
				allocator_free(alloc, self.allocated_start, self.bits)

			# Keep backward compat tracking (deprecated)
			_smallest_allocated_qubit -= self.bits
			ancilla -= self.bits

	def __str__(self):
		return f"{self.qubits}"

	# Context manager protocol
	def __enter__(self):
		global _controlled, _control_bool
		if not _controlled:
			_control_bool = self
		else:
			# TODO: and operation of self and qint._control_bool
			list_of_constrols.append(_control_bool)
			_control_bool &= self
			pass
		_controlled = True
		return self

	def __exit__(self, exc__type, exc, tb):
		global _controlled, _control_bool, ancilla, _smallest_allocated_qubit
		_controlled = False
		_control_bool = None

		# undo logical and operations
		return False  # do not suppress exceptions

	cdef addition_inplace(self, other: qint | int, invert: int  = False):
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int other_bits
		cdef int self_offset
		cdef int other_offset

		start = 0

		# Extract only the used qubits (right-aligned in 64-element array)
		# self.qubits[64-self.bits:64] contains the actual qubit indices
		self_offset = 64 - self.bits
		qubit_array[:self.bits] = self.qubits[self_offset:64]
		start += self.bits

		if type(other) == int:
			# value is a classical integer
			QPU_state[0].R0[0] = other
			if _controlled:
				# Control qubit from qbool (last element)
				qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
				qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
				seq = cCQ_add(self.bits)
			else:
				qubit_array[start: start + NUMANCILLY] = ancilla
				seq = CQ_add(self.bits)


			arr = qubit_array
			run_instruction(seq, &arr[0], invert, _circuit)

			return self
		if type(other) != qint:
			raise ValueError()


		# other type is qint as well - determine result width
		other_bits = (<qint> other).bits
		result_bits = max(self.bits, other_bits)
		other_offset = 64 - other_bits

		# Extract used qubits from other
		qubit_array[start: start + other_bits] = (<qint> other).qubits[other_offset:64]
		start += other_bits


		if _controlled:
			# Control qubit from qbool (last element)
			qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
			qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
			seq = cQQ_add(result_bits)
		else:
			qubit_array[start: start + NUMANCILLY] = ancilla
			seq = QQ_add(result_bits)

		arr = qubit_array
		run_instruction(seq, &arr[0], invert, _circuit)
		return self

	def __add__(self, other: qint | int):
		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(value = self.value, width = result_width)
		a += other
		return a

	def __radd__(self, other: qint | int):
		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(value = self.value, width = result_width)
		a += other
		return a

	def __iadd__(self, other: qint | int):
		# in place addition
		return self.addition_inplace(other)

	def __sub__(self, other: qint | int):
		# out of place subtraction - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(value = self.value, width = result_width)
		a -= other
		return a

	def __isub__(self, other: qint | int):
		# in place addition
		return self.addition_inplace(other, invert = True)


	cdef multiplication_inplace(self, other: qint | int, ret: qint):
			global _controlled, _control_bool, qubit_array
			cdef sequence_t *seq
			cdef unsigned int[:] arr
			cdef int result_bits
			cdef int other_bits
			cdef int self_offset
			cdef int ret_offset
			cdef int other_offset

			start = 0

			# Multiplication layout: ret (accumulator) at position 0, self at position bits
			# Extract only used qubits (right-aligned in 64-element array)
			self_offset = 64 - self.bits
			ret_offset = 64 - (<qint>ret).bits

			# ret qubits at position 0
			qubit_array[:self.bits] = (<qint>ret).qubits[ret_offset:64]
			# self qubits at position bits
			qubit_array[self.bits: 2 * self.bits] = self.qubits[self_offset:64]
			start = 2 * self.bits

			if type(other) == int:
				# value is a classical integer
				QPU_state[0].R0[0] = other
				if _controlled:
					# Control qubit from qbool (last element)
					qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
					qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
					seq = cCQ_mul()
				else:
					qubit_array[start: start + NUMANCILLY] = ancilla
					seq = CQ_mul()

				arr = qubit_array
				run_instruction(seq, &arr[0], False, _circuit)

				return ret

			if type(other) != qint:
				raise ValueError()

			# Quantum-quantum multiplication - determine result width
			other_bits = (<qint> other).bits
			result_bits = max(self.bits, other_bits)
			other_offset = 64 - other_bits

			# other qubits at position 2*bits
			qubit_array[start: start + other_bits] = (<qint> other).qubits[other_offset:64]
			start += other_bits

			# value is a quantum integer

			if _controlled:
				# Control qubit from qbool (last element)
				qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
				qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
				seq = cQQ_add(result_bits)
			else:
				qubit_array[start: start + NUMANCILLY] = ancilla
				seq = QQ_add(result_bits)

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)
			return self

	def __mul__(self, other):
		a = qint(bits = self.bits)
		self.multiplication_inplace(other, a)
		return a

	def __rmul__(self, other):
		a = qint(bits = self.bits)
		self.multiplication_inplace(other, a)
		return a

	cdef and_functionality(self, other, ret):
		cdef sequence_t *seq;
		cdef unsigned int[:] arr

		# Logic operations use INTEGERSIZE layout - qubits at position INTEGERSIZE-1
		# For qbool (width=1), the qubit is at self.qubits[63] (last element)
		qubit_array[INTEGERSIZE - 1] = (<qbool> ret).qubits[63]
		qubit_array[2 * INTEGERSIZE - 1] = self.qubits[63]
		qubit_array[3 * INTEGERSIZE - 1] = (<qbool> other).qubits[63]

		seq = qq_and_seq()

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)
		free(seq)

	def measure(self):
		return self.value

	def __and__(self, other):
		a = qbool()
		# print("and")
		# TODO: include quantum functionality
		self.and_functionality(other, a)
		return a

	def __iand__(self, other):
		a = qbool()
		print("iand")
		self.and_functionality(other, a)
		return a

	def __or__(self, other):
		global _smallest_allocated_qubit, ancilla
		a = qbool()
		cdef sequence_t *seq;
		cdef unsigned int[:] arr

		# Logic operations use INTEGERSIZE layout - qubits at position INTEGERSIZE-1
		# For qbool (width=1), the qubit is at self.qubits[63] (last element)
		qubit_array[INTEGERSIZE - 1] = a.qubits[63]
		qubit_array[2 * INTEGERSIZE - 1] = self.qubits[63]
		qubit_array[3 * INTEGERSIZE - 1] = (<qbool> other).qubits[63]

		seq = qq_or_seq()

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)
		free(seq)
		_smallest_allocated_qubit += 1
		ancilla += 1
		return a

	def __ior__(self, other):

		return

	def __xor__(self, other):
		a = qbool()
		print("xor")
		# TODO: include quantum functionality
		return a

	def __ixor__(self, other):
		a = qbool()
		print("inplace xor")
		# TODO: include quantum functionality
		return a

	def __invert__(self):
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr

		# Logic operations use INTEGERSIZE layout - qubit at position INTEGERSIZE-1
		# For qbool (width=1), the qubit is at self.qubits[63] (last element)
		if _controlled:
			qubit_array[2 * INTEGERSIZE - 1] = (<qbool> _control_bool).qubits[63]
			qubit_array[INTEGERSIZE - 1] = self.qubits[63]
			seq = cq_not_seq()
		else:
			qubit_array[INTEGERSIZE - 1] = self.qubits[63]
			seq = q_not_seq()

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)

		free(seq)

		# TODO: include quantum functionality
		return self

	def __getitem__(self, item: int):
		bit_list = np.zeros(64)
		bit_list[-1] = self.qubits[item]
		a = qbool(create_new = False, bit_list = bit_list)
		return a

	def __gt__(self, other):
		global _smallest_allocated_qubit, ancilla
		a = self[64 - self.bits]  # MSB is at index (64 - width)
		self.addition_inplace(other, True)
		c = qbool()
		c = ~c

		with a:
			c = ~c

		self.addition_inplace(other, False)
		return c

	def __ge__(self, other):
		return self > other - 1

	def __lt__(self, other):
		global _smallest_allocated_qubit, ancilla
		a = self[64 - self.bits]  # MSB is at index (64 - width)
		self.addition_inplace(other, True)
		c = qbool()
		with a:
			c = ~c

		self.addition_inplace(other, False)
		return c

	def __le__(self, other):
		return self < other + 1



cdef class qbool(qint):
	"""Quantum boolean - a 1-bit quantum integer.

	qbool is syntactic sugar for qint with width=1. All qint operations
	apply to qbool, with single-bit semantics.

	Examples:
		>>> b = qbool(True)
		>>> b.width
		1
		>>> c = qbool()  # False by default
	"""

	def __init__(self, value: bool = False, classical: bool = False, create_new = True, bit_list = None):
		super().__init__(value, width=1, classical=classical, create_new=create_new, bit_list=bit_list)


def circuit_stats():
	"""Get qubit allocation statistics for the current circuit.

	Returns:
		dict with keys: peak_allocated, total_allocations, total_deallocations,
		                current_in_use, ancilla_allocations
		None if circuit not initialized
	"""
	cdef qubit_allocator_t *alloc
	cdef allocator_stats_t stats

	if not _circuit_initialized:
		return None

	alloc = circuit_get_allocator(<circuit_s*>_circuit)
	if alloc == NULL:
		return None

	stats = allocator_get_stats(alloc)
	return {
		'peak_allocated': stats.peak_allocated,
		'total_allocations': stats.total_allocations,
		'total_deallocations': stats.total_deallocations,
		'current_in_use': stats.current_in_use,
		'ancilla_allocations': stats.ancilla_allocations
	}
