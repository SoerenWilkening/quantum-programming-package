	# ====================================================================
	# ARITHMETIC OPERATIONS
	# ====================================================================

	cdef addition_inplace(self, other, int invert=False):
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int other_bits
		cdef int self_offset
		cdef int other_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()

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
				qubit_array[start: start + 1] = (<qint> _control_bool).qubits[63:64]
				qubit_array[start + 1: start + 1 + NUMANCILLY] = _get_ancilla()
				seq = cCQ_add(self.bits, other)
			else:
				qubit_array[start: start + NUMANCILLY] = _get_ancilla()
				seq = CQ_add(self.bits, other)


			arr = qubit_array
			run_instruction(seq, &arr[0], invert, _circuit)

			return self
		if not isinstance(other, qint):
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
			qubit_array[start: start + 1] = (<qint> _control_bool).qubits[63:64]
			qubit_array[start + 1: start + 1 + NUMANCILLY] = _get_ancilla()
			seq = cQQ_add(result_bits)
		else:
			qubit_array[start: start + NUMANCILLY] = _get_ancilla()
			seq = QQ_add(result_bits)

		arr = qubit_array
		run_instruction(seq, &arr[0], invert, _circuit)
		return self

	def __add__(self, other: qint | int):
		"""Add quantum integers: self + other

		Result width is max(self.width, other.width). Overflow wraps (modular).

		Parameters
		----------
		other : qint or int
			Value to add.

		Returns
		-------
		qint
			New quantum integer containing sum.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> c = a + b
		>>> c.width
		8
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		a += other

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		return a

	def __radd__(self, other: qint | int):
		"""Reverse addition: other + self (for int + qint).

		Parameters
		----------
		other : int
			Classical value to add.

		Returns
		-------
		qint
			New quantum integer containing sum.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = 3 + a  # Uses __radd__
		>>> b.width
		8
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		a += other

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		return a

	def __iadd__(self, other: qint | int):
		"""In-place addition: self += other

		Parameters
		----------
		other : qint or int
			Value to add.

		Returns
		-------
		qint
			Self (modified in-place via quantum gates).

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> a += 3
		>>> # a now represents |5+3> = |8>
		"""
		# in place addition
		return self.addition_inplace(other)

	def __sub__(self, other: qint | int):
		"""Subtract quantum integers: self - other

		Result width is max(self.width, other.width). Underflow wraps (modular).

		Parameters
		----------
		other : qint or int
			Value to subtract.

		Returns
		-------
		qint
			New quantum integer containing difference.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> c = a - b
		>>> c.width
		8
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# out of place subtraction - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		a -= other

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'SUB'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		return a

	def __isub__(self, other: qint | int):
		"""In-place subtraction: self -= other

		Parameters
		----------
		other : qint or int
			Value to subtract.

		Returns
		-------
		qint
			Self (modified in-place via quantum gates).

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> a -= 3
		>>> # a now represents |5-3> = |2>
		"""
		# in place addition
		return self.addition_inplace(other, invert = True)

	def __neg__(self):
		"""Two's complement negation: -self

		Returns a new qint whose value is (-self) % (2**width).

		Returns
		-------
		qint
			New quantum integer with negated value.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> b = -a
		>>> # b represents |(-5) % 16> = |11>
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		result = qint(width=self.bits)
		result -= self  # 0 - self = two's complement negation

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'NEG'
		result.add_dependency(self)
		return result

	def __rsub__(self, other):
		"""Reverse subtraction: other - self

		Handles the case where Python dispatches int - qint to qint.__rsub__.

		Parameters
		----------
		other : int or qint
			Left operand.

		Returns
		-------
		qint
			New quantum integer with value (other - self) % (2**width).

		Examples
		--------
		>>> a = qint(3, width=4)
		>>> b = 10 - a
		>>> # b represents |7>
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		result = qint(width=self.bits)
		if type(other) == int:
			result += other   # classical add into zero-init (OK, other is classical)
		else:
			result ^= other   # quantum copy other
		result -= self         # result = other - self

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'SUB'
		result.add_dependency(self)
		if type(other) == qint:
			result.add_dependency(other)
		return result

	def __lshift__(self, int other):
		"""Left shift: self << other (other must be classical int).

		Implements left shift as multiplication by 2^other.

		Parameters
		----------
		other : int
			Shift amount (must be non-negative).

		Returns
		-------
		qint
			New quantum integer with value (self << other) % (2**width).

		Raises
		------
		ValueError
			If other is negative.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = a << 2
		>>> # b represents |12>
		"""
		if other < 0:
			raise ValueError("Negative shift count")
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result *= (1 << other)

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'LSHIFT'
		result.add_dependency(self)
		return result

	def __ilshift__(self, int other):
		"""In-place left shift: self <<= other"""
		result = self << other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __rshift__(self, int other):
		"""Right shift: self >> other (other must be classical int).

		Implements right shift as floor division by 2^other.

		Parameters
		----------
		other : int
			Shift amount (must be non-negative).

		Returns
		-------
		qint
			New quantum integer with value self >> other.

		Raises
		------
		ValueError
			If other is negative.

		Examples
		--------
		>>> a = qint(12, width=8)
		>>> b = a >> 2
		>>> # b represents |3>
		"""
		if other < 0:
			raise ValueError("Negative shift count")
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result //= (1 << other)

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'RSHIFT'
		result.add_dependency(self)
		return result

	def __irshift__(self, int other):
		"""In-place right shift: self >>= other"""
		result = self >> other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self


	cdef multiplication_inplace(self, other, qint ret):
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int other_bits
		cdef int self_offset
		cdef int ret_offset
		cdef int other_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()

		start = 0

		# Determine result width (must match ret's width)
		result_bits = (<qint>ret).bits

		# Multiplication layout: ret (accumulator) at position 0, self at position result_bits
		# Extract only used qubits (right-aligned in 64-element array)
		self_offset = 64 - self.bits
		ret_offset = 64 - result_bits

		# ret qubits at position 0
		qubit_array[:result_bits] = (<qint>ret).qubits[ret_offset:64]
		# self qubits at position result_bits
		qubit_array[result_bits: result_bits + self.bits] = self.qubits[self_offset:64]
		start = result_bits + self.bits

		if type(other) == int:
			# Classical-quantum multiplication
			if _controlled:
				# Control qubit from qbool (last element)
				qubit_array[start: start + 1] = (<qint> _control_bool).qubits[63:64]
				qubit_array[start + 1: start + 1 + NUMANCILLY] = _get_ancilla()
				seq = cCQ_mul(result_bits, other)  # Pass bits parameter
			else:
				qubit_array[start: start + NUMANCILLY] = _get_ancilla()
				seq = CQ_mul(result_bits, other)  # Pass bits parameter

			if seq == NULL:
				raise RuntimeError(f"Multiplication circuit generation failed for width {result_bits}")

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)
			return ret

		if not isinstance(other, qint):
			raise TypeError("Multiplication requires qint or int")

		# Quantum-quantum multiplication
		other_bits = (<qint> other).bits
		other_offset = 64 - other_bits

		# other qubits at position start
		qubit_array[start: start + other_bits] = (<qint> other).qubits[other_offset:64]
		start += other_bits

		if _controlled:
			qubit_array[start: start + 1] = (<qint> _control_bool).qubits[63:64]
			qubit_array[start + 1: start + 1 + NUMANCILLY] = _get_ancilla()
			seq = cQQ_mul(result_bits)  # Pass bits parameter
		else:
			qubit_array[start: start + NUMANCILLY] = _get_ancilla()
			seq = QQ_mul(result_bits)  # Pass bits parameter

		if seq == NULL:
			raise RuntimeError(f"Multiplication circuit generation failed for width {result_bits}")

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)
		return ret

	def __mul__(self, other):
		"""Multiply quantum integers.

		Result width is max(self.width, other.width) per CONTEXT.md.
		Overflow wraps silently (modular arithmetic).

		Parameters
		----------
		other : qint or int
			Value to multiply by.

		Returns
		-------
		qint
			New qint containing product.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = qint(4, width=16)
		>>> c = a * b
		>>> c.width
		16
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Determine result width
		if isinstance(other, qint):  # Includes qint subclasses like qint_mod
			result_width = max(self.bits, (<qint>other).bits)
		elif type(other) == int:
			result_width = self.bits
		else:
			raise TypeError("Multiplication requires qint or int")

		# Allocate result with correct width
		result = qint(width=result_width)

		# Perform multiplication into result
		self.multiplication_inplace(other, result)

		# Phase 41: Layer tracking for uncomputation
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		return result

	def __rmul__(self, other):
		"""Reverse multiplication: other * self (for int * qint).

		Parameters
		----------
		other : int
			Classical value to multiply by.

		Returns
		-------
		qint
			New qint containing product.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = 3 * a  # Uses __rmul__
		>>> b.width
		8
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# For int * qint, result width is qint's width
		if type(other) == int:
			result_width = self.bits
		else:
			# qint * qint should use __mul__, not __rmul__
			result_width = max(self.bits, (<qint>other).bits)

		result = qint(width=result_width)
		self.multiplication_inplace(other, result)

		# Phase 41: Layer tracking for uncomputation
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		return result

	def __imul__(self, other):
		"""In-place multiplication: self *= other

		Note: Due to quantum mechanics, in-place multiplication allocates
		new qubits for the result and swaps qubit references.

		Parameters
		----------
		other : qint or int
			Value to multiply by.

		Returns
		-------
		qint
			Self (with swapped qubit references).

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> a *= 4
		>>> # a now references new qubits containing 3*4
		"""
		# Perform out-of-place multiplication
		result = self * other

		# Swap qubit arrays (like __iand__ pattern from Phase 6)
		cdef qint result_qint = <qint>result

		# Swap qubit references
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits

		return self

