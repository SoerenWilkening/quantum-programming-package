	# ====================================================================
	# DIVISION OPERATIONS
	# Phase 41: Added layer tracking for uncomputation support
	# Phase 91: Rewired to C-level restoring divmod (fixes BUG-DIV-02, BUG-QFT-DIV)
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef _divmod_c(self, divisor, bint need_quotient, bint need_remainder):
		"""Internal: call C-level divmod and return (quotient, remainder).

		Dispatches to toffoli_divmod_cq (classical divisor) or
		toffoli_divmod_qq (quantum divisor). All ancillae are managed
		internally by the C functions.

		Parameters
		----------
		divisor : int or qint
		    Divisor value.
		need_quotient : bool
		    If True, return quotient; if False, quotient register is unused.
		need_remainder : bool
		    If True, return remainder; if False, remainder register is unused.

		Returns
		-------
		tuple of (qint or None, qint or None)
		    (quotient, remainder), either may be None if not needed.
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef int i
		cdef int n = self.bits
		cdef int self_offset = 64 - n
		cdef unsigned int dividend_qa[64]
		cdef unsigned int quotient_qa[64]
		cdef unsigned int remainder_qa[64]
		cdef unsigned int divisor_qa[64]
		cdef int div_bits = 0
		cdef int d_offset = 0
		cdef size_t gc_before_div, gc_delta_div
		cdef unsigned int layer_before_div
		cdef gate_counts_t range_counts_div
		cdef bint _controlled = _get_controlled()

		# Extract dividend qubits (LSB-first for C convention)
		# Python qint right-aligned layout: qubits[64-bits] = LSB (bit 0), qubits[63] = MSB
		# C expects LSB-first: index 0 = LSB, index n-1 = MSB
		# So qa[i] = qubits[self_offset + i] gives qa[0]=LSB, qa[n-1]=MSB
		for i in range(n):
			dividend_qa[i] = self.qubits[self_offset + i]

		# Allocate output registers
		quotient = qint(0, width=n)
		remainder = qint(0, width=n)

		cdef int q_offset = 64 - (<qint>quotient).bits
		cdef int r_offset = 64 - (<qint>remainder).bits

		# Extract output qubits (LSB-first)
		for i in range(n):
			quotient_qa[i] = (<qint>quotient).qubits[q_offset + i]
			remainder_qa[i] = (<qint>remainder).qubits[r_offset + i]

		if type(divisor) == int:
			gc_before_div = (<circuit_s*>_circ).gate_count
			layer_before_div = (<circuit_s*>_circ).used_layer
			toffoli_divmod_cq(_circ, dividend_qa, n,
			                  <int64_t>divisor,
			                  quotient_qa, remainder_qa)
			gc_delta_div = (<circuit_s*>_circ).gate_count - gc_before_div
			if (<circuit_s*>_circ).simulate and (<circuit_s*>_circ).used_layer > layer_before_div:
				range_counts_div = circuit_gate_counts_range(<circuit_s*>_circ, layer_before_div, (<circuit_s*>_circ).used_layer)
			else:
				range_counts_div.t_count = 0
			_record_operation(
				"divmod_cq",
				tuple(dividend_qa[i] for i in range(n))
				+ tuple(quotient_qa[i] for i in range(n))
				+ tuple(remainder_qa[i] for i in range(n)),
				gate_count=gc_delta_div,
				controlled=bool(_controlled),
				depth=(<circuit_s*>_circ).used_layer - layer_before_div,
				t_count=range_counts_div.t_count,
			)
		elif type(divisor) == qint:
			div_bits = (<qint>divisor).bits
			d_offset = 64 - div_bits
			for i in range(div_bits):
				divisor_qa[i] = (<qint>divisor).qubits[d_offset + i]

			gc_before_div = (<circuit_s*>_circ).gate_count
			layer_before_div = (<circuit_s*>_circ).used_layer
			toffoli_divmod_qq(_circ, dividend_qa, n,
			                  divisor_qa, div_bits,
			                  quotient_qa, remainder_qa)
			gc_delta_div = (<circuit_s*>_circ).gate_count - gc_before_div
			if (<circuit_s*>_circ).simulate and (<circuit_s*>_circ).used_layer > layer_before_div:
				range_counts_div = circuit_gate_counts_range(<circuit_s*>_circ, layer_before_div, (<circuit_s*>_circ).used_layer)
			else:
				range_counts_div.t_count = 0
			_record_operation(
				"divmod_qq",
				tuple(dividend_qa[i] for i in range(n))
				+ tuple(divisor_qa[i] for i in range(div_bits))
				+ tuple(quotient_qa[i] for i in range(n))
				+ tuple(remainder_qa[i] for i in range(n)),
				gate_count=gc_delta_div,
				controlled=bool(_controlled),
				depth=(<circuit_s*>_circ).used_layer - layer_before_div,
				t_count=range_counts_div.t_count,
			)
		else:
			raise TypeError("Divisor must be int or qint")

		return (quotient, remainder)

	def __floordiv__(self, divisor):
		"""Floor division: self // divisor

		Uses C-level restoring division algorithm (Phase 91).

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
		Phase 91: Rewired to C-level toffoli_divmod_cq/qq.
		Classical divisor: O(width) circuit via bit-level restoring division.
		Quantum divisor: O(2^width) circuit via repeated subtraction.
		"""
		from quantum_language.qbool import qbool

		# Validation
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Division by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, True, False)

		quotient.operation_type = 'DIV'
		quotient.add_dependency(self)
		if type(divisor) == qint:
			quotient.add_dependency(divisor)

		return quotient

	def __ifloordiv__(self, other):
		"""In-place floor division: self //= other"""
		result = self // other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __mod__(self, divisor):
		"""Modulo operation: self % divisor

		Computes remainder via C-level restoring division (Phase 91).

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
		# Validation
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Modulo by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, False, True)

		remainder.operation_type = 'MOD'
		remainder.add_dependency(self)
		if type(divisor) == qint:
			remainder.add_dependency(divisor)

		return remainder

	def __divmod__(self, divisor):
		"""Divmod operation: divmod(self, divisor)

		Computes both quotient and remainder in single pass via C-level
		restoring division (Phase 91).

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
		# Validation
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Divmod by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, True, True)

		quotient.operation_type = 'DIVMOD'
		quotient.add_dependency(self)
		remainder.operation_type = 'DIVMOD'
		remainder.add_dependency(self)
		if type(divisor) == qint:
			quotient.add_dependency(divisor)
			remainder.add_dependency(divisor)

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
