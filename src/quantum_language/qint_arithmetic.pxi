	# ====================================================================
	# ARITHMETIC OPERATIONS
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef addition_inplace(self, other, int invert=False):
		# Cython-level addition: calls sequence generators directly,
		# with Toffoli dispatch (CLA/RCA, BK/KS, Clifford+T) handled
		# in toffoli_dispatch.pxi. No C hot path -- all logic in Cython.
		_mark_arithmetic_performed()
		cdef circuit_s *_circ = <circuit_s*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef unsigned int[:] control_qubits
		cdef sequence_t *seq
		cdef int result_bits
		cdef int pos
		cdef size_t gc_before, gc_delta
		cdef unsigned int layer_before
		cdef gate_counts_t range_counts

		# Extract self qubits (right-aligned in 64-element array)
		for i in range(self_bits):
			self_qa[i] = self.qubits[self_offset + i]

		# Extract control qubit if controlled
		if _controlled:
			control_qubits = (<qint> _control_bool).qubits
			control_qubit = control_qubits[63]

		if type(other) == int:
			classical_value = <int64_t>other

			# Compile-mode: record IR entry, skip gate emission.
			# Only for QFT mode — Toffoli mode falls through to direct dispatch
			# which produces correct gate types (X/CX/CCX instead of QFT rotations).
			if _is_compile_mode() and _circ.arithmetic_mode != 1:
				regs = tuple(self_qa[i] for i in range(self_bits))
				if _controlled:
					regs = regs + (control_qubit,)
				_uc_seq = CQ_add(self_bits, classical_value)
				_cc_seq = cCQ_add(self_bits, classical_value)
				_record_instruction(
					"add_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
					invert=bool(invert),
				)
				return self

			# Toffoli dispatch for CQ
			if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
				gc_before = _circ.gate_count
				layer_before = _circ.used_layer
				_toffoli_dispatch_cq(_circ, self_qa, self_bits,
				                     classical_value, invert,
				                     _controlled, control_qubit)
				gc_delta = _circ.gate_count - gc_before
				if _circ.simulate and _circ.used_layer > layer_before:
					range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
				else:
					range_counts.t_count = 0
				_record_operation(
					"add_cq",
					tuple(self_qa[i] for i in range(self_bits))
					+ ((control_qubit,) if _controlled else ()),
					gate_count=gc_delta,
					invert=bool(invert),
					controlled=bool(_controlled),
					depth=_circ.used_layer - layer_before,
					t_count=range_counts.t_count,
				)
				return self

			# QFT path: build qubit array and call sequence generator
			pos = 0
			for i in range(self_bits):
				qa[pos] = self_qa[i]
				pos += 1
			if _controlled:
				qa[pos] = control_qubit
				pos += 1
				seq = cCQ_add(self_bits, classical_value)
			else:
				seq = CQ_add(self_bits, classical_value)
			if seq == NULL:
				return self
			layer_before = _circ.used_layer
			run_instruction(seq, qa, invert, <circuit_t*>_circ)
			if _circ.simulate and _circ.used_layer > layer_before:
				range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
			else:
				range_counts.t_count = 0
			_record_operation(
				"add_cq",
				tuple(qa[i] for i in range(pos)),
				gate_count=seq.total_gate_count,
				sequence_ptr=<unsigned long long>seq,
				invert=bool(invert),
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before,
				t_count=range_counts.t_count,
			)
			return self

		if not isinstance(other, qint):
			raise ValueError()

		# Extract other qubits for quantum-quantum addition
		cdef int other_bits = (<qint> other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint> other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		result_bits = self_bits if self_bits > other_bits else other_bits

		# Compile-mode: record IR entry, skip gate emission.
		# Only for QFT mode — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			regs = (tuple(self_qa[i] for i in range(self_bits))
			        + tuple(other_qa[i] for i in range(other_bits)))
			if _controlled:
				regs = regs + (control_qubit,)
			_uc_seq = QQ_add(result_bits)
			_cc_seq = cQQ_add(result_bits)
			_record_instruction(
				"add_qq", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				invert=bool(invert),
			)
			return self

		# Toffoli dispatch for QQ
		if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
			gc_before = _circ.gate_count
			layer_before = _circ.used_layer
			_toffoli_dispatch_qq(_circ, self_qa, self_bits,
			                     other_qa, other_bits, invert,
			                     _controlled, control_qubit, result_bits)
			gc_delta = _circ.gate_count - gc_before
			if _circ.simulate and _circ.used_layer > layer_before:
				range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
			else:
				range_counts.t_count = 0
			_record_operation(
				"add_qq",
				tuple(self_qa[i] for i in range(self_bits))
				+ tuple(other_qa[i] for i in range(other_bits))
				+ ((control_qubit,) if _controlled else ()),
				gate_count=gc_delta,
				invert=bool(invert),
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before,
				t_count=range_counts.t_count,
			)
			return self

		# QFT path: build qubit array and call sequence generator
		pos = 0
		for i in range(self_bits):
			qa[pos] = self_qa[i]
			pos += 1
		for i in range(other_bits):
			qa[pos] = other_qa[i]
			pos += 1
		if _controlled:
			qa[2 * result_bits] = control_qubit
			seq = cQQ_add(result_bits)
		else:
			seq = QQ_add(result_bits)
		if seq == NULL:
			return self
		layer_before = _circ.used_layer
		run_instruction(seq, qa, invert, <circuit_t*>_circ)
		if _circ.simulate and _circ.used_layer > layer_before:
			range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
		else:
			range_counts.t_count = 0
		_record_operation(
			"add_qq",
			tuple(qa[i] for i in range(pos + (1 if _controlled else 0))),
			gate_count=seq.total_gate_count,
			sequence_ptr=<unsigned long long>seq,
			invert=bool(invert),
			controlled=bool(_controlled),
			depth=_circ.used_layer - layer_before,
			t_count=range_counts.t_count,
		)
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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

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

		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= and += (Step 6.4 transparency)
		del (<qint>a).history.entries[:]
		_self_offset_h = 64 - self.bits
		_a_offset_h = 64 - (<qint>a).bits
		_qm = tuple((<qint>a).qubits[_a_offset_h + i] for i in range((<qint>a).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>a).history.append(0, _qm)
		if type(other) == qint and (<qint>other).bits < result_width:
			(<qint>a).history.add_child(padded_other)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(a)
		if type(other) == qint:
			(<qint>other).history.add_blocker(a)

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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

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

		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= and += (Step 6.4 transparency)
		del (<qint>a).history.entries[:]
		_self_offset_h = 64 - self.bits
		_a_offset_h = 64 - (<qint>a).bits
		_qm = tuple((<qint>a).qubits[_a_offset_h + i] for i in range((<qint>a).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>a).history.append(0, _qm)
		if type(other) == qint and (<qint>other).bits < result_width:
			(<qint>a).history.add_child(padded_other)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(a)
		if type(other) == qint:
			(<qint>other).history.add_blocker(a)

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
		# Step 6.2: Blocker insertion — source operand references dest
		if type(other) == qint and other is not self:
			(<qint>other).history.add_blocker(self)
		# in place addition
		self.addition_inplace(other)
		# Step 6.4: Record history with kind for inverse cancellation
		_ia_offset = 64 - self.bits
		if type(other) == int:
			_ia_qm = tuple(self.qubits[_ia_offset + i] for i in range(self.bits)) + (int(other),)
		else:
			_ia_other_offset = 64 - (<qint>other).bits
			_ia_qm = tuple(self.qubits[_ia_offset + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_ia_other_offset + i] for i in range((<qint>other).bits))
		self.history.append(0, _ia_qm, kind='add')
		return self

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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

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

		a.operation_type = 'SUB'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= and -= (Step 6.4 transparency)
		del (<qint>a).history.entries[:]
		_self_offset_h = 64 - self.bits
		_a_offset_h = 64 - (<qint>a).bits
		_qm = tuple((<qint>a).qubits[_a_offset_h + i] for i in range((<qint>a).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>a).history.append(0, _qm)
		if type(other) == qint and (<qint>other).bits < result_width:
			(<qint>a).history.add_child(padded_other)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(a)
		if type(other) == qint:
			(<qint>other).history.add_blocker(a)

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
		# Step 6.2: Blocker insertion — source operand references dest
		if type(other) == qint and other is not self:
			(<qint>other).history.add_blocker(self)
		# in place subtraction (addition with invert)
		self.addition_inplace(other, invert = True)
		# Step 6.4: Record history with kind for inverse cancellation
		_is_offset = 64 - self.bits
		if type(other) == int:
			_is_qm = tuple(self.qubits[_is_offset + i] for i in range(self.bits)) + (int(other),)
		else:
			_is_other_offset = 64 - (<qint>other).bits
			_is_qm = tuple(self.qubits[_is_offset + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_is_other_offset + i] for i in range((<qint>other).bits))
		self.history.append(0, _is_qm, kind='sub')
		return self

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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		result -= self  # 0 - self = two's complement negation

		result.operation_type = 'NEG'
		result.add_dependency(self)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from -= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operand references the result
		self.history.add_blocker(result)

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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		if type(other) == int:
			result += other   # classical add into zero-init (OK, other is classical)
		else:
			result ^= other   # quantum copy other
		result -= self         # result = other - self

		result.operation_type = 'SUB'
		result.add_dependency(self)
		if type(other) == qint:
			result.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from +=, ^=, -= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) == qint:
			(<qint>other).history.add_blocker(result)

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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result *= (1 << other)

		result.operation_type = 'LSHIFT'
		result.add_dependency(self)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operand references the result
		self.history.add_blocker(result)

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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result //= (1 << other)

		result.operation_type = 'RSHIFT'
		result.add_dependency(self)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operand references the result
		self.history.add_blocker(result)

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
		# Cython-level multiplication: calls sequence generators directly,
		# with Toffoli path calling toffoli_mul_qq/cq directly.
		# No C hot path -- all logic in Cython.
		_mark_arithmetic_performed()
		cdef circuit_s *_circ = <circuit_s*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int ret_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int ret_offset = 64 - (<qint>ret).bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef unsigned int[:] control_qubits
		cdef unsigned int[:] ret_qubits_mv = (<qint>ret).qubits
		cdef int result_bits = (<qint>ret).bits
		cdef sequence_t *seq
		cdef int pos
		cdef size_t gc_before, gc_delta
		cdef unsigned int layer_before_mul
		cdef gate_counts_t range_counts_mul

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

		if type(other) == int:
			classical_value = <int64_t>other

			# Compile-mode: record IR entry, skip gate emission.
			# Only for QFT mode — Toffoli mode falls through to direct dispatch.
			if _is_compile_mode() and _circ.arithmetic_mode != 1:
				regs = (tuple(ret_qa[i] for i in range(result_bits))
				        + tuple(self_qa[i] for i in range(self_bits)))
				if _controlled:
					regs = regs + (control_qubit,)
				_uc_seq = CQ_mul(result_bits, classical_value)
				_cc_seq = cCQ_mul(result_bits, classical_value)
				_record_instruction(
					"mul_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				return ret

			# Toffoli dispatch for CQ
			if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
				gc_before = _circ.gate_count
				layer_before_mul = _circ.used_layer
				if _controlled:
					toffoli_cmul_cq(<circuit_t*>_circ, ret_qa, result_bits,
					                self_qa, self_bits, classical_value,
					                control_qubit)
				else:
					toffoli_mul_cq(<circuit_t*>_circ, ret_qa, result_bits,
					               self_qa, self_bits, classical_value)
				gc_delta = _circ.gate_count - gc_before
				if _circ.simulate and _circ.used_layer > layer_before_mul:
					range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
				else:
					range_counts_mul.t_count = 0
				_record_operation(
					"mul_cq",
					tuple(ret_qa[i] for i in range(result_bits))
					+ tuple(self_qa[i] for i in range(self_bits))
					+ ((control_qubit,) if _controlled else ()),
					gate_count=gc_delta,
					controlled=bool(_controlled),
					depth=_circ.used_layer - layer_before_mul,
					t_count=range_counts_mul.t_count,
				)
				return ret

			# QFT path: build qubit array and call sequence generator
			pos = 0
			for i in range(result_bits):
				qa[pos] = ret_qa[i]
				pos += 1
			for i in range(self_bits):
				qa[pos] = self_qa[i]
				pos += 1
			if _controlled:
				qa[pos] = control_qubit
				pos += 1
				seq = cCQ_mul(result_bits, classical_value)
			else:
				seq = CQ_mul(result_bits, classical_value)
			if seq == NULL:
				return ret
			layer_before_mul = _circ.used_layer
			run_instruction(seq, qa, 0, <circuit_t*>_circ)
			if _circ.simulate and _circ.used_layer > layer_before_mul:
				range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
			else:
				range_counts_mul.t_count = 0
			_record_operation(
				"mul_cq",
				tuple(qa[i] for i in range(pos)),
				gate_count=seq.total_gate_count,
				sequence_ptr=<unsigned long long>seq,
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before_mul,
				t_count=range_counts_mul.t_count,
			)
			return ret

		if not isinstance(other, qint):
			raise TypeError("Multiplication requires qint or int")

		# Extract other qubits for quantum-quantum multiplication
		cdef int other_bits = (<qint>other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint>other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		# Compile-mode: record IR entry, skip gate emission.
		# Only for QFT mode — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			regs = (tuple(ret_qa[i] for i in range(result_bits))
			        + tuple(self_qa[i] for i in range(self_bits))
			        + tuple(other_qa[i] for i in range(other_bits)))
			if _controlled:
				regs = regs + (control_qubit,)
			_uc_seq = QQ_mul(result_bits)
			_cc_seq = cQQ_mul(result_bits)
			_record_instruction(
				"mul_qq", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
			)
			return ret

		# Toffoli dispatch for QQ
		if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
			gc_before = _circ.gate_count
			layer_before_mul = _circ.used_layer
			if _controlled:
				toffoli_cmul_qq(<circuit_t*>_circ, ret_qa, result_bits,
				                self_qa, self_bits, other_qa, other_bits,
				                control_qubit)
			else:
				toffoli_mul_qq(<circuit_t*>_circ, ret_qa, result_bits,
				               self_qa, self_bits, other_qa, other_bits)
			gc_delta = _circ.gate_count - gc_before
			if _circ.simulate and _circ.used_layer > layer_before_mul:
				range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
			else:
				range_counts_mul.t_count = 0
			_record_operation(
				"mul_qq",
				tuple(ret_qa[i] for i in range(result_bits))
				+ tuple(self_qa[i] for i in range(self_bits))
				+ tuple(other_qa[i] for i in range(other_bits))
				+ ((control_qubit,) if _controlled else ()),
				gate_count=gc_delta,
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before_mul,
				t_count=range_counts_mul.t_count,
			)
			return ret

		# QFT path: build qubit array and call sequence generator
		pos = 0
		for i in range(result_bits):
			qa[pos] = ret_qa[i]
			pos += 1
		for i in range(self_bits):
			qa[pos] = self_qa[i]
			pos += 1
		for i in range(other_bits):
			qa[pos] = other_qa[i]
			pos += 1
		if _controlled:
			qa[pos] = control_qubit
			pos += 1
			seq = cQQ_mul(result_bits)
		else:
			seq = QQ_mul(result_bits)
		if seq == NULL:
			return ret
		layer_before_mul = _circ.used_layer
		run_instruction(seq, qa, 0, <circuit_t*>_circ)
		if _circ.simulate and _circ.used_layer > layer_before_mul:
			range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
		else:
			range_counts_mul.t_count = 0
		# Resolve both UC/CC gate counts from sequence generators
		_record_operation(
			"mul_qq",
			tuple(qa[i] for i in range(pos)),
			gate_count=seq.total_gate_count,
			sequence_ptr=<unsigned long long>seq,
			controlled=bool(_controlled),
			depth=_circ.used_layer - layer_before_mul,
			t_count=range_counts_mul.t_count,
		)
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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Determine result width
		if isinstance(other, qint):  # Includes qint subclasses like qint_mod
			result_width = max(self.bits, (<qint>other).bits)
		elif type(other) == int:
			result_width = self.bits
		else:
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

		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if isinstance(other, qint):
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

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
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

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

		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if isinstance(other, qint):
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

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

