	# ====================================================================
	# DIVISION OPERATIONS
	# Phase 41: Added layer tracking for uncomputation support
	# ====================================================================

	def __floordiv__(self, divisor):
		"""Floor division: self // divisor

		Uses restoring division algorithm (repeated subtraction).

		Parameters
		----------
		divisor : int or qint
			Divisor.

		Returns
		-------
		qint
			Quotient.

		Raises
		------
		ZeroDivisionError
			If divisor is zero (classical only).
		TypeError
			If divisor is not int or qint.

		Examples
		--------
		>>> a = qint(17, width=8)
		>>> q = a // 5
		>>> # q represents |3>

		Notes
		-----
		Classical divisor: O(width) circuit via bit-level algorithm.
		Quantum divisor: O(quotient) circuit via repeated subtraction.
		"""
		from quantum_language.qbool import qbool
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Division by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			# Allocate quotient and remainder
			quotient = qint(0, width=self.bits)
			remainder = qint(0, width=self.bits)

			# Copy self to remainder via XOR (remainder starts at 0)
			remainder ^= self

			# Restoring division: try subtracting divisor * 2^bit for each bit position
			for bit_pos in range(self.bits - 1, -1, -1):
				# Try subtracting divisor << bit_pos
				trial_value = divisor << bit_pos

				# Check if remainder >= trial_value
				can_subtract = remainder >= trial_value

				# Conditional subtraction and quotient bit set
				with can_subtract:
					remainder -= trial_value
					quotient += (1 << bit_pos)

			# Phase 41: Layer tracking for uncomputation
			quotient._start_layer = start_layer
			quotient._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
			quotient.operation_type = 'DIV'
			quotient.add_dependency(self)

			return quotient

		elif type(divisor) == qint:
			# Quantum divisor - delegate to quantum division method
			result = self._floordiv_quantum(divisor)
			# Phase 41: Layer tracking for uncomputation
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
			result.operation_type = 'DIV'
			result.add_dependency(self)
			result.add_dependency(divisor)
			return result
		else:
			raise TypeError("Divisor must be int or qint")

	def __ifloordiv__(self, other):
		"""In-place floor division: self //= other"""
		result = self // other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def _floordiv_quantum(self, divisor: qint):
		"""Floor division with quantum divisor: self // divisor"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		quotient = qint(0, width=comp_bits)
		remainder = qint(0, width=comp_bits)
		remainder ^= self

		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			can_subtract = remainder >= divisor
			with can_subtract:
				remainder -= divisor
				quotient += 1

		return quotient

	def __mod__(self, divisor):
		"""Modulo operation: self % divisor

		Computes remainder via restoring division.

		Parameters
		----------
		divisor : int or qint
			Divisor.

		Returns
		-------
		qint
			Remainder.

		Raises
		------
		ZeroDivisionError
			If divisor is zero (classical only).
		TypeError
			If divisor is not int or qint.

		Examples
		--------
		>>> a = qint(17, width=8)
		>>> r = a % 5
		>>> # r represents |2>
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Modulo by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			remainder = qint(0, width=self.bits)
			remainder ^= self

			for bit_pos in range(self.bits - 1, -1, -1):
				trial_value = divisor << bit_pos
				can_subtract = remainder >= trial_value
				with can_subtract:
					remainder -= trial_value

			# Phase 41: Layer tracking for uncomputation
			remainder._start_layer = start_layer
			remainder._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
			remainder.operation_type = 'MOD'
			remainder.add_dependency(self)

			return remainder

		elif type(divisor) == qint:
			result = self._mod_quantum(divisor)
			# Phase 41: Layer tracking for uncomputation
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
			result.operation_type = 'MOD'
			result.add_dependency(self)
			result.add_dependency(divisor)
			return result
		else:
			raise TypeError("Divisor must be int or qint")

	def _mod_quantum(self, divisor: qint):
		"""Modulo with quantum divisor: self % divisor"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		remainder = qint(0, width=comp_bits)
		remainder ^= self

		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			can_subtract = remainder >= divisor
			with can_subtract:
				remainder -= divisor

		return remainder

	def __divmod__(self, divisor):
		"""Divmod operation: divmod(self, divisor)

		Computes both quotient and remainder in single pass.

		Parameters
		----------
		divisor : int or qint
			Divisor.

		Returns
		-------
		tuple of qint
			(quotient, remainder).

		Raises
		------
		ZeroDivisionError
			If divisor is zero (classical only).
		TypeError
			If divisor is not int or qint.

		Examples
		--------
		>>> a = qint(17, width=8)
		>>> q, r = divmod(a, 5)
		>>> # q represents |3>, r represents |2>
		"""
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Divmod by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			quotient = qint(0, width=self.bits)
			remainder = qint(0, width=self.bits)
			remainder ^= self

			for bit_pos in range(self.bits - 1, -1, -1):
				trial_value = divisor << bit_pos
				can_subtract = remainder >= trial_value
				with can_subtract:
					remainder -= trial_value
					quotient += (1 << bit_pos)

			# Phase 41: Layer tracking for uncomputation
			end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
			quotient._start_layer = start_layer
			quotient._end_layer = end_layer
			quotient.operation_type = 'DIVMOD'
			quotient.add_dependency(self)
			remainder._start_layer = start_layer
			remainder._end_layer = end_layer
			remainder.operation_type = 'DIVMOD'
			remainder.add_dependency(self)

			return (quotient, remainder)

		elif type(divisor) == qint:
			q, r = self._divmod_quantum(divisor)
			# Phase 41: Layer tracking for uncomputation
			end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
			q._start_layer = start_layer
			q._end_layer = end_layer
			q.operation_type = 'DIVMOD'
			q.add_dependency(self)
			q.add_dependency(divisor)
			r._start_layer = start_layer
			r._end_layer = end_layer
			r.operation_type = 'DIVMOD'
			r.add_dependency(self)
			r.add_dependency(divisor)
			return (q, r)
		else:
			raise TypeError("Divisor must be int or qint")

	def _divmod_quantum(self, divisor: qint):
		"""Divmod with quantum divisor: divmod(self, divisor)"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		quotient = qint(0, width=comp_bits)
		remainder = qint(0, width=comp_bits)
		remainder ^= self

		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			can_subtract = remainder >= divisor
			with can_subtract:
				remainder -= divisor
				quotient += 1

		return (quotient, remainder)

	def __rfloordiv__(self, other):
		"""Reverse floor division: other // self"""
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint // self
		else:
			raise TypeError("Reverse floor division requires int divisor")

	def __rmod__(self, other):
		"""Reverse modulo: other % self"""
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint % self
		else:
			raise TypeError("Reverse modulo requires int divisor")

	def __rdivmod__(self, other):
		"""Reverse divmod: divmod(other, self)"""
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return divmod(other_qint, self)
		else:
			raise TypeError("Reverse divmod requires int divisor")
