	# ====================================================================
	# ARITHMETIC OPERATIONS
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef addition_inplace(self, other, int invert=False):
		# Phase 60-03: Thin Cython wrapper -- all hot-path logic moved to C
		# (hot_path_add.c). We only extract qubit indices from Python objects
		# here, then call the C function with nogil.
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int ancilla_qa[128]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef int num_ancilla = NUMANCILLY
		cdef unsigned int[:] ancilla_arr
		cdef unsigned int[:] control_qubits

		# Extract self qubits (right-aligned in 64-element array)
		for i in range(self_bits):
			self_qa[i] = self.qubits[self_offset + i]

		# Extract control qubit if controlled
		if _controlled:
			control_qubits = (<qint> _control_bool).qubits
			control_qubit = control_qubits[63]

		# Extract ancilla qubits
		ancilla_arr = _get_ancilla()
		for i in range(num_ancilla):
			ancilla_qa[i] = ancilla_arr[i]

		if type(other) == int:
			classical_value = <int64_t>other
			with nogil:
				hot_path_add_cq(_circuit, self_qa, self_bits,
								classical_value,
								invert, _controlled, control_qubit,
								ancilla_qa, num_ancilla)
			return self

		if not isinstance(other, qint):
			raise ValueError()

		# Extract other qubits for quantum-quantum addition
		cdef int other_bits = (<qint> other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint> other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		with nogil:
			hot_path_add_qq(_circuit, self_qa, self_bits,
							other_qa, other_bits,
							invert, _controlled, control_qubit,
							ancilla_qa, num_ancilla)
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_add = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		# BUG-04 fix: zero-extend narrower operand so QQ_add gets result_width
		# qubits for both registers
		if type(other) == qint and (<qint>other).bits < result_width:
			padded_other = qint(width=result_width)
			padded_other ^= other
			a += padded_other
		else:
			a += other

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_add
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_radd = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		# BUG-04 fix: zero-extend narrower operand so QQ_add gets result_width
		# qubits for both registers
		if type(other) == qint and (<qint>other).bits < result_width:
			padded_other = qint(width=result_width)
			padded_other ^= other
			a += padded_other
		else:
			a += other

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_radd
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_sub = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# out of place subtraction - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		# BUG-04 fix: zero-extend narrower operand so QQ_add gets result_width
		# qubits for both registers
		if type(other) == qint and (<qint>other).bits < result_width:
			padded_other = qint(width=result_width)
			padded_other ^= other
			a -= padded_other
		else:
			a -= other

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'SUB'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_sub
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_neg = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		result = qint(width=self.bits)
		result -= self  # 0 - self = two's complement negation

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'NEG'
		result.add_dependency(self)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_neg
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_rsub = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

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

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_rsub
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_lsh = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result *= (1 << other)

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'LSHIFT'
		result.add_dependency(self)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_lsh
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_rsh = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result //= (1 << other)

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'RSHIFT'
		result.add_dependency(self)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_rsh
		return result

	def __irshift__(self, int other):
		"""In-place right shift: self >>= other"""
		result = self >> other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self


	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef multiplication_inplace(self, other, qint ret):
		# Phase 60-02: Thin Cython wrapper -- all hot-path logic moved to C
		# (hot_path_mul.c). We only extract qubit indices from Python objects
		# here, then call the C function with nogil.
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int ret_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int ancilla_qa[128]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int ret_offset = 64 - (<qint>ret).bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef int num_ancilla = NUMANCILLY
		cdef unsigned int[:] ancilla_arr
		cdef unsigned int[:] control_qubits
		cdef unsigned int[:] ret_qubits_mv = (<qint>ret).qubits
		cdef int result_bits = (<qint>ret).bits

		# Extract ret qubits (right-aligned in 64-element array)
		for i in range(result_bits):
			ret_qa[i] = ret_qubits_mv[ret_offset + i]

		# Extract self qubits
		for i in range(self_bits):
			self_qa[i] = self.qubits[self_offset + i]

		# Extract control qubit if controlled
		if _controlled:
			control_qubits = (<qint>_control_bool).qubits
			control_qubit = control_qubits[63]

		# Extract ancilla qubits
		ancilla_arr = _get_ancilla()
		for i in range(num_ancilla):
			ancilla_qa[i] = ancilla_arr[i]

		if type(other) == int:
			classical_value = <int64_t>other
			with nogil:
				hot_path_mul_cq(_circuit, ret_qa, result_bits,
								self_qa, self_bits,
								classical_value,
								_controlled, control_qubit,
								ancilla_qa, num_ancilla)
			return ret

		if not isinstance(other, qint):
			raise TypeError("Multiplication requires qint or int")

		# Extract other qubits for quantum-quantum multiplication
		cdef int other_bits = (<qint>other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint>other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		with nogil:
			hot_path_mul_qq(_circuit, ret_qa, result_bits,
							self_qa, self_bits,
							other_qa, other_bits,
							_controlled, control_qubit,
							ancilla_qa, num_ancilla)
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_mul = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# Determine result width
		if isinstance(other, qint):  # Includes qint subclasses like qint_mod
			result_width = max(self.bits, (<qint>other).bits)
		elif type(other) == int:
			result_width = self.bits
		else:
			if _circ_init:
				(<circuit_s*>_circ).layer_floor = _saved_floor_mul
			raise TypeError("Multiplication requires qint or int")

		# BUG-COND-MUL-01 fix: prevent result registration in scope frame.
		# Multiplication results should never be auto-uncomputed by scope exit.
		# The user explicitly assigns them; cleanup is handled by GC, not scope.
		_saved_scope = current_scope_depth.get()
		current_scope_depth.set(0)

		# Allocate result with correct width
		result = qint(width=result_width)

		# Restore scope depth after result allocation
		current_scope_depth.set(_saved_scope)

		# Perform multiplication into result
		self.multiplication_inplace(other, result)

		# Phase 41: Layer tracking for uncomputation
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_mul
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

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_rmul = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# For int * qint, result width is qint's width
		if type(other) == int:
			result_width = self.bits
		else:
			# qint * qint should use __mul__, not __rmul__
			result_width = max(self.bits, (<qint>other).bits)

		# BUG-COND-MUL-01 fix: prevent result registration in scope frame
		_saved_scope_rmul = current_scope_depth.get()
		current_scope_depth.set(0)

		result = qint(width=result_width)

		current_scope_depth.set(_saved_scope_rmul)

		self.multiplication_inplace(other, result)

		# Phase 41: Layer tracking for uncomputation
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_rmul
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

		# BUG-02 defensive fix: prevent GC from uncomputing/freeing the swapped-out
		# qubits when result_qint goes out of scope. The multiplication gates now
		# belong to self; result_qint holds self's old (input) qubits which should
		# not be reversed or freed by result_qint's destructor.
		result_qint._is_uncomputed = True
		result_qint.allocated_qubits = False

		return self

