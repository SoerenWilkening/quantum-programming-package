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
			if _controlled:
				# Control qubit from qbool (last element)
				qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
				qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
				seq = cCQ_add(self.bits, other)
			else:
				qubit_array[start: start + NUMANCILLY] = ancilla
				seq = CQ_add(self.bits, other)


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
				if _controlled:
					# Control qubit from qbool (last element)
					qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
					qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
					seq = cCQ_mul(other)
				else:
					qubit_array[start: start + NUMANCILLY] = ancilla
					seq = CQ_mul(other)

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

	def measure(self):
		return self.value

	def __and__(self, other):
		"""Bitwise AND operation. Returns NEW qint.

		For qint & qint: result width = max(self.width, other.width)
		For qint & int: result width = max(self.width, value.bit_length())
		"""
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif type(other) == qint or type(other) == qbool:
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Allocate result (ancilla qubits)
		result = qint(width=result_bits)

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_and expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		# Self qubits (zero-extended if smaller) - at position result_bits
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]

		if type(other) == int:
			# Classical-quantum AND
			# CQ_and expects: [0:bits] = output, [bits:2*bits] = quantum operand
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum AND not yet supported")
			else:
				seq = CQ_and(result_bits, other)
		else:
			# Quantum-quantum AND
			other_offset = 64 - (<qint>other).bits
			qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum AND not yet supported")
			else:
				seq = Q_and(result_bits)

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)

		return result

	def __iand__(self, other):
		"""In-place AND: a &= b. Allocates result, swaps qubit references."""
		cdef qint result_qint
		result = self & other
		result_qint = <qint>result
		# Swap qubit arrays using cdef access
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __rand__(self, other):
		"""Reverse AND for int & qint."""
		return self & other

	def __or__(self, other):
		"""Bitwise OR operation. Returns NEW qint.

		For qint | qint: result width = max(self.width, other.width)
		For qint | int: result width = max(self.width, value.bit_length())
		"""
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif type(other) == qint or type(other) == qbool:
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Allocate result (ancilla qubits)
		result = qint(width=result_bits)

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_or expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		# Self qubits (zero-extended if smaller) - at position result_bits
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]

		if type(other) == int:
			# Classical-quantum OR
			# CQ_or expects: [0:bits] = output, [bits:2*bits] = quantum operand
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum OR not yet supported")
			else:
				seq = CQ_or(result_bits, other)
		else:
			# Quantum-quantum OR
			other_offset = 64 - (<qint>other).bits
			qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum OR not yet supported")
			else:
				seq = Q_or(result_bits)

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)

		return result

	def __ior__(self, other):
		"""In-place OR: a |= b. Allocates result, swaps qubit references."""
		cdef qint result_qint
		result = self | other
		result_qint = <qint>result
		# Swap qubit arrays using cdef access
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __ror__(self, other):
		"""Reverse OR for int | qint."""
		return self | other

	def __xor__(self, other):
		"""Bitwise XOR operation. Returns NEW qint.

		For qint ^ qint: result width = max(self.width, other.width)
		For qint ^ int: result width = max(self.width, value.bit_length())
		"""
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif type(other) == qint or type(other) == qbool:
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Allocate result (ancilla qubits)
		result = qint(width=result_bits)

		# Q_xor expects: [0:bits] = target, [bits:2*bits] = source
		# XOR modifies target in-place: target ^= source
		# So we need to first copy self to result, then XOR other into result

		# Copy self qubits to result using CNOT pattern
		# For now, we do out-of-place: result = self, then result ^= other
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# First, copy self to result by XORing self into result (result starts at 0)
		# Copy self qubits into result: result ^= self (where result is 0, so result = self)
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]
		arr = qubit_array
		seq = Q_xor(self.bits)  # XOR self into result (copying self to result)
		run_instruction(seq, &arr[0], False, _circuit)

		# Now XOR other into result
		if type(other) == int:
			# Classical XOR: apply X gates where classical bits are 1
			# We don't have CQ_xor, so we'll apply X gates manually
			# Actually, Q_xor with a classical value is just applying X where bit=1
			# For now, we use a simple loop pattern via existing NOT functionality
			# This is a limitation - we don't have CQ_xor exposed
			# We can simulate: for each bit i where (other >> i) & 1, apply X to result[i]
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
			else:
				# Apply X gates for each 1 bit in the classical value
				# Note: We need to do this at Python level since CQ_xor is not exposed
				# For now, apply individual X gates through Q_not on single bits
				# This is inefficient but works
				for i in range(result_bits):
					if (other >> i) & 1:
						# Apply X to result bit i (from LSB)
						# result.qubits[63-i] is the i-th bit from LSB
						qubit_array[0] = result.qubits[64 - result_bits + (result_bits - 1 - i)]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)
		else:
			# Quantum-quantum XOR: result ^= other
			other_offset = 64 - (<qint>other).bits
			qubit_array[:result_bits] = result.qubits[result_offset:64]
			qubit_array[result_bits:result_bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")
			else:
				seq = Q_xor((<qint>other).bits)

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)

		return result

	def __ixor__(self, other):
		"""In-place XOR: a ^= b. Modifies self directly (XOR is special)."""
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset, other_offset

		# XOR can be done truly in-place since target ^= source modifies target
		self_offset = 64 - self.bits

		if type(other) == int:
			# Classical XOR: apply X gates where classical bits are 1
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
			else:
				for i in range(self.bits):
					if (other >> i) & 1:
						# Apply X to self bit i (from LSB)
						qubit_array[0] = self.qubits[64 - self.bits + (self.bits - 1 - i)]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)
		elif type(other) == qint or type(other) == qbool:
			# Quantum-quantum XOR: self ^= other
			other_offset = 64 - (<qint>other).bits
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			qubit_array[self.bits:self.bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")
			else:
				seq = Q_xor(min(self.bits, (<qint>other).bits))

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)
		else:
			raise TypeError("Operand must be qint or int")

		return self

	def __rxor__(self, other):
		"""Reverse XOR for int ^ qint."""
		return self ^ other

	def __invert__(self):
		"""Bitwise NOT operation. Inverts all bits IN-PLACE and returns self."""
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset

		# Use width-parameterized NOT for multi-bit qints
		self_offset = 64 - self.bits

		if _controlled:
			# Controlled NOT: [0:bits] = target, [bits] = control
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			qubit_array[self.bits] = (<qbool> _control_bool).qubits[63]
			seq = cQ_not(self.bits)
		else:
			# Uncontrolled NOT: [0:bits] = target
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			seq = Q_not(self.bits)

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)

		return self

	def __getitem__(self, item: int):
		bit_list = np.zeros(64)
		bit_list[-1] = self.qubits[item]
		a = qbool(create_new = False, bit_list = bit_list)
		return a

	def __eq__(self, other):
		"""Equality comparison: self == other

		Uses optimized XOR-based circuit (O(n) gates).
		Returns qbool result. Preserves input operands.

		Strategy: XOR all bits together, then check if result is zero.
		If all bits are equal, XOR produces 0.
		"""
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int comp_bits
		cdef int self_offset, other_offset, temp_offset

		# Determine comparison width
		if type(other) == int:
			comp_bits = self.bits
			other_qint = qint(other, width=comp_bits)
		elif type(other) == qint:
			comp_bits = max(self.bits, (<qint>other).bits)
			other_qint = other
		else:
			raise TypeError("Comparison requires qint or int")

		# XOR self and other into temp
		# If self == other, temp will be all zeros
		temp = self ^ other_qint

		# Check if temp is all zeros
		# Start with result = True (assume equal)
		result = qbool(True)

		# For each bit in temp, if any bit is 1, set result to False
		# Use controlled NOT: if temp[i] is 1, flip result
		for i in range(comp_bits):
			bit_index = 64 - comp_bits + i
			bit = temp[bit_index]
			# Controlled NOT on result based on this bit
			with bit:
				result = ~result

		return result

	def __ne__(self, other):
		"""Not-equal comparison: self != other"""
		return ~(self == other)

	def __lt__(self, other):
		"""Less-than comparison: self < other

		Returns qbool result. Preserves input operands.
		Uses subtraction and MSB check.
		"""
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int comp_bits
		cdef int self_offset, other_offset, temp_offset

		# Determine comparison width
		if type(other) == int:
			comp_bits = self.bits
			other_qint = qint(other, width=comp_bits)
		elif type(other) == qint:
			comp_bits = max(self.bits, (<qint>other).bits)
			other_qint = other
		else:
			raise TypeError("Comparison requires qint or int")

		# Allocate ancilla for subtraction (temp = self - other)
		temp = qint(0, width=comp_bits)

		# Copy self to temp via XOR (since temp starts at 0)
		temp ^= self

		# Subtract other from temp (temp = self - other)
		temp -= other_qint

		# Extract MSB (sign bit) - if negative, self < other
		# MSB is at index (64 - comp_bits) for right-aligned storage
		msb = temp[64 - comp_bits]

		# Result: if MSB=1 (negative), self < other is True
		result = qbool()
		result ^= msb  # Copy MSB to result

		return result

	def __gt__(self, other):
		"""Greater-than comparison: self > other"""
		# self > other is equivalent to other < self (swap operands)
		# For int type, create qint and swap
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint < self
		elif type(other) == qint:
			return other < self
		else:
			raise TypeError("Comparison requires qint or int")

	def __le__(self, other):
		"""Less-than-or-equal comparison: self <= other"""
		# self <= other is equivalent to NOT (other < self)
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return ~(other_qint < self)
		elif type(other) == qint:
			return ~(other < self)
		else:
			raise TypeError("Comparison requires qint or int")

	def __ge__(self, other):
		"""Greater-than-or-equal comparison: self >= other"""
		# self >= other is equivalent to NOT (self < other)
		return ~(self < other)



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
