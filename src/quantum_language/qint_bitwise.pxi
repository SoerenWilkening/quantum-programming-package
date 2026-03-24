	# ====================================================================
	# BITWISE OPERATIONS
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	def __and__(self, other):
		"""Bitwise AND: self & other

		Result width is max(self.width, other.width).

		Parameters
		----------
		other : qint or int
			Value to AND with.

		Returns
		-------
		qint
			New quantum integer containing bitwise AND result.

		Examples
		--------
		>>> a = qint(0b1101, width=4)
		>>> b = qint(0b1011, width=4)
		>>> c = a & b
		>>> # c represents |1001>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef int i
		cdef int _self_pad, _other_pad
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int[:] result_qubits
		cdef unsigned int[:] other_qubits
		cdef unsigned int[:] pad_qubits
		cdef size_t gc_before_and, gc_delta_and
		cdef unsigned int layer_before_and
		cdef gate_counts_t range_counts_and

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			result = qint(width=result_bits)
			result.add_dependency(self)
			if type(other) != int:
				result.add_dependency(other)
			result.operation_type = 'AND'
			self_offset = 64 - self.bits
			result_offset = 64 - result_bits
			regs = tuple((<qint>result).qubits[result_offset + i] for i in range(result_bits))
			regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
			if type(other) != int and isinstance(other, qint):
				other_offset = 64 - (<qint>other).bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
			if type(other) == int:
				_uc_seq = CQ_and(result_bits, other)
				_cc_seq = cCQ_and(result_bits, other)
				_record_instruction(
					"and_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			else:
				_uc_seq = Q_and(result_bits)
				_cc_seq = cQ_and(result_bits)
				_record_instruction(
					"and_qq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			self.history.add_blocker(result)
			if type(other) != int and isinstance(other, qint):
				(<qint>other).history.add_blocker(result)
			return result

		# Phase 84: Validate qubit_array bounds before writes
		# AND uses up to 3*result_bits slots: [output:N], [self:N], [other:N]
		validate_qubit_slots(3 * result_bits, "__and__")

		# Allocate padding ancilla BEFORE result so result gets highest qubit indices
		# (result must be last-allocated for bitstring[:width] extraction to work)
		_self_pad_qint = None
		_other_pad_qint = None
		if self.bits < result_bits:
			_self_pad_qint = qint(width=result_bits - self.bits)
		if type(other) != int and isinstance(other, qint):
			if (<qint>other).bits < result_bits:
				_other_pad_qint = qint(width=result_bits - (<qint>other).bits)

		# Allocate result (ancilla qubits) -- must be last for extraction
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:  # Don't track classical operands
			result.add_dependency(other)
		result.operation_type = 'AND'

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_and expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		# Qubit storage is LSB-first: index 0 = LSB
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		# CYT-03: Replace slice with explicit loop for memory view optimization
		result_qubits = result.qubits
		for i in range(result_bits):
			qubit_array[i] = result_qubits[result_offset + i]
		# Self qubits (LSB positions) - at position result_bits
		for i in range(self.bits):
			qubit_array[result_bits + i] = self.qubits[self_offset + i]
		# Zero-extend self if narrower: use pre-allocated padding for MSB
		if _self_pad_qint is not None:
			_self_pad = result_bits - self.bits
			pad_qubits = _self_pad_qint.qubits
			for i in range(_self_pad):
				qubit_array[result_bits + self.bits + i] = pad_qubits[64 - _self_pad + i]

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
			other_qubits = (<qint>other).qubits
			for i in range((<qint>other).bits):
				qubit_array[2*result_bits + i] = other_qubits[other_offset + i]
			# Zero-extend other if narrower: use pre-allocated padding for MSB
			if _other_pad_qint is not None:
				_other_pad = result_bits - (<qint>other).bits
				pad_qubits = _other_pad_qint.qubits
				for i in range(_other_pad):
					qubit_array[2*result_bits + (<qint>other).bits + i] = pad_qubits[64 - _other_pad + i]

			if _controlled:
				# Controlled quantum-quantum AND: decompose C-CCX into
				# standard Toffolis + ancilla.
				# For each bit i, C-CCX(output[i], A[i], B[i], ext_ctrl)
				# decomposes as:
				#   CCX(ancilla, A[i], ext_ctrl)  -- partial AND
				#   CCX(output[i], ancilla, B[i]) -- use partial AND
				#   CCX(ancilla, A[i], ext_ctrl)  -- uncompute ancilla
				_control_bool = _get_control_bool()
				_ctrl_qubit = (<qint>_control_bool).qubits[63]
				from quantum_language._gates import emit_ccx as _emit_ccx
				from quantum_language.qbool import qbool as _qbool_cls
				gc_before_and = (<circuit_s*>_circuit).gate_count
				layer_before_and = (<circuit_s*>_circuit).used_layer
				_and_ancilla = _qbool_cls()
				_anc_qubit = _and_ancilla.qubits[63]
				for i in range(result_bits):
					_a_qubit = qubit_array[result_bits + i]
					_b_qubit = qubit_array[2 * result_bits + i]
					_out_qubit = qubit_array[i]
					_emit_ccx(_anc_qubit, _a_qubit, _ctrl_qubit)
					_emit_ccx(_out_qubit, _anc_qubit, _b_qubit)
					_emit_ccx(_anc_qubit, _a_qubit, _ctrl_qubit)
				# Free ancilla
				_and_ancilla._is_uncomputed = True
				_and_ancilla.allocated_qubits = False
				from ._core import _deallocate_qubits
				_deallocate_qubits(_and_ancilla.allocated_start, 1)
				gc_delta_and = (<circuit_s*>_circuit).gate_count - gc_before_and
				if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_and:
					range_counts_and = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_and, (<circuit_s*>_circuit).used_layer)
				else:
					range_counts_and.t_count = 0
				_total_and = 3 * result_bits
				_record_operation(
					"and",
					tuple(qubit_array[i] for i in range(_total_and)),
					gate_count=gc_delta_and,
					controlled=bool(_controlled),
					depth=(<circuit_s*>_circuit).used_layer - layer_before_and,
					t_count=range_counts_and.t_count,
					is_composite=True,
					op_params={"width": result_bits},
				)
				_qm = tuple(qubit_array[i] for i in range(_total_and))
				result.history.append(0, _qm)
				# Step 6.2: Blocker insertion — source operands reference the result
				self.history.add_blocker(result)
				if type(other) != int and isinstance(other, qint):
					(<qint>other).history.add_blocker(result)
				return result
			else:
				seq = Q_and(result_bits)

		arr = qubit_array
		layer_before_and = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_and:
			range_counts_and = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_and, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_and.t_count = 0
		_record_operation(
			"and",
			tuple(qubit_array[i] for i in range(3 * result_bits if type(other) != int else 2 * result_bits)),
			sequence_ptr=<unsigned long long>seq,
			gate_count=seq.total_gate_count,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_and,
			t_count=range_counts_and.t_count,
		)

		# Step 1.2: Record operation into result's per-variable history
		# Must match the exact qubit_array layout passed to run_instruction,
		# including zero-extension padding qubits for narrower operands.
		_total_and = 3 * result_bits if (type(other) != int and isinstance(other, qint)) else 2 * result_bits
		_qm = tuple(qubit_array[i] for i in range(_total_and))
		result.history.append(<unsigned long long>seq, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) != int and isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	def __iand__(self, other):
		"""In-place AND: self &= other

		Parameters
		----------
		other : qint or int
			Value to AND with.

		Returns
		-------
		qint
			Self (with swapped qubit references).

		Examples
		--------
		>>> a = qint(0b1101, width=4)
		>>> a &= 0b1011
		>>> # a now represents |1001>
		"""
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
		"""Bitwise OR: self | other

		Result width is max(self.width, other.width).

		Parameters
		----------
		other : qint or int
			Value to OR with.

		Returns
		-------
		qint
			New quantum integer containing bitwise OR result.

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> b = qint(0b0011, width=4)
		>>> c = a | b
		>>> # c represents |1111>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int layer_before_or
		cdef gate_counts_t range_counts_or

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			result = qint(width=result_bits)
			result.add_dependency(self)
			if type(other) != int:
				result.add_dependency(other)
			result.operation_type = 'OR'
			self_offset = 64 - self.bits
			result_offset = 64 - result_bits
			regs = tuple((<qint>result).qubits[result_offset + i] for i in range(result_bits))
			regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
			if type(other) != int and isinstance(other, qint):
				other_offset = 64 - (<qint>other).bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
			if type(other) == int:
				_uc_seq = CQ_or(result_bits, other)
				_cc_seq = cCQ_or(result_bits, other)
				_record_instruction(
					"or_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			else:
				_uc_seq = Q_or(result_bits)
				_cc_seq = cQ_or(result_bits)
				_record_instruction(
					"or_qq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			self.history.add_blocker(result)
			if type(other) != int and isinstance(other, qint):
				(<qint>other).history.add_blocker(result)
			return result

		# Phase 84: Validate qubit_array bounds before writes
		# OR uses up to 3*result_bits slots: [output:N], [self:N], [other:N]
		validate_qubit_slots(3 * result_bits, "__or__")

		# Allocate padding ancilla BEFORE result so result gets highest qubit indices
		_self_pad_qint = None
		_other_pad_qint = None
		if self.bits < result_bits:
			_self_pad_qint = qint(width=result_bits - self.bits)
		if type(other) != int and isinstance(other, qint):
			if (<qint>other).bits < result_bits:
				_other_pad_qint = qint(width=result_bits - (<qint>other).bits)

		# Allocate result (ancilla qubits) -- must be last for extraction
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:
			result.add_dependency(other)
		result.operation_type = 'OR'

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_or expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		# Qubit storage is LSB-first: index 0 = LSB
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		# Self qubits (LSB positions) - at position result_bits
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]
		# Zero-extend self if narrower
		if _self_pad_qint is not None:
			_self_pad = result_bits - self.bits
			qubit_array[result_bits + self.bits:2*result_bits] = _self_pad_qint.qubits[64 - _self_pad:64]

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
			# Zero-extend other if narrower
			if _other_pad_qint is not None:
				_other_pad = result_bits - (<qint>other).bits
				qubit_array[2*result_bits + (<qint>other).bits:3*result_bits] = _other_pad_qint.qubits[64 - _other_pad:64]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum OR not yet supported")
			else:
				seq = Q_or(result_bits)

		arr = qubit_array
		layer_before_or = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_or:
			range_counts_or = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_or, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_or.t_count = 0
		_record_operation(
			"or",
			tuple(qubit_array[i] for i in range(3 * result_bits if type(other) != int else 2 * result_bits)),
			sequence_ptr=<unsigned long long>seq,
			gate_count=seq.total_gate_count,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_or,
			t_count=range_counts_or.t_count,
		)

		# Step 1.2: Record operation into result's per-variable history
		# Must match the exact qubit_array layout passed to run_instruction,
		# including zero-extension padding qubits for narrower operands.
		_total_or = 3 * result_bits if (type(other) != int and isinstance(other, qint)) else 2 * result_bits
		_qm = tuple(qubit_array[i] for i in range(_total_or))
		result.history.append(<unsigned long long>seq, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) != int and isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	def __ior__(self, other):
		"""In-place OR: self |= other

		Parameters
		----------
		other : qint or int
			Value to OR with.

		Returns
		-------
		qint
			Self (with swapped qubit references).

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> a |= 0b0011
		>>> # a now represents |1111>
		"""
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

	@cython.boundscheck(False)
	@cython.wraparound(False)
	def __xor__(self, other):
		"""Bitwise XOR: self ^ other

		Result width is max(self.width, other.width).

		Parameters
		----------
		other : qint or int
			Value to XOR with.

		Returns
		-------
		qint
			New quantum integer containing bitwise XOR result.

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> b = qint(0b0110, width=4)
		>>> c = a ^ b
		>>> # c represents |1010>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef int i
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int[:] result_qubits
		cdef unsigned int[:] other_qubits
		cdef size_t gc_before_xor, gc_delta_xor
		cdef unsigned int layer_before_xor
		cdef gate_counts_t range_counts_xor

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			result = qint(width=result_bits)
			result.add_dependency(self)
			if type(other) != int:
				result.add_dependency(other)
			result.operation_type = 'XOR'
			self_offset = 64 - self.bits
			result_offset = 64 - result_bits
			regs = tuple((<qint>result).qubits[result_offset + i] for i in range(result_bits))
			regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
			if type(other) != int and isinstance(other, qint):
				other_offset = 64 - (<qint>other).bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
			_uc_seq = Q_xor(self.bits)
			_cc_seq = cQ_xor(self.bits)
			_record_instruction(
				"xor", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
			)
			self.history.add_blocker(result)
			if type(other) != int and isinstance(other, qint):
				(<qint>other).history.add_blocker(result)
			return result

		# Phase 84: Validate qubit_array bounds before writes
		# XOR uses up to 2*result_bits slots: [target:N], [source:N]
		validate_qubit_slots(2 * result_bits, "__xor__")

		# Allocate result (ancilla qubits)
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:
			result.add_dependency(other)
		result.operation_type = 'XOR'

		# Q_xor expects: [0:bits] = target, [bits:2*bits] = source
		# XOR modifies target in-place: target ^= source
		# So we need to first copy self to result, then XOR other into result

		# Copy self qubits to result using CNOT pattern
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Capture gate_count before multi-step XOR
		gc_before_xor = (<circuit_s*>_circuit).gate_count
		layer_before_xor = (<circuit_s*>_circuit).used_layer

		# First, copy self to result by XORing self into result (result starts at 0)
		# CYT-03: Replace slice with explicit loop for memory view optimization
		result_qubits = result.qubits
		for i in range(self.bits):
			qubit_array[i] = result_qubits[result_offset + i]
		for i in range(self.bits):
			qubit_array[self.bits + i] = self.qubits[self_offset + i]
		arr = qubit_array
		seq = Q_xor(self.bits)  # XOR self into result (copying self to result)
		run_instruction(seq, &arr[0], False, _circuit)

		# Now XOR other into result
		if type(other) == int:
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
			else:
				for i in range(result_bits):
					if (other >> i) & 1:
						qubit_array[0] = result_qubits[64 - result_bits + i]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)
		else:
			other_offset = 64 - (<qint>other).bits
			for i in range((<qint>other).bits):
				qubit_array[i] = result_qubits[result_offset + i]
			other_qubits = (<qint>other).qubits
			for i in range((<qint>other).bits):
				qubit_array[(<qint>other).bits + i] = other_qubits[other_offset + i]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")
			else:
				seq = Q_xor((<qint>other).bits)

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)

		# Record XOR operation on the DAG
		gc_delta_xor = (<circuit_s*>_circuit).gate_count - gc_before_xor
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_xor:
			range_counts_xor = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_xor, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_xor.t_count = 0
		_record_operation(
			"xor",
			tuple(result_qubits[result_offset + i] for i in range(result_bits))
			+ tuple(self.qubits[self_offset + i] for i in range(self.bits))
			+ (tuple((<qint>other).qubits[64 - (<qint>other).bits + i]
			         for i in range((<qint>other).bits))
			   if type(other) != int else ()),
			gate_count=gc_delta_xor,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_xor,
			t_count=range_counts_xor.t_count,
			is_composite=True,
			op_params={"result_width": result_bits, "self_width": self.bits,
			           "other_width": (<qint>other).bits if type(other) != int else 0,
			           "value": int(other) if type(other) == int else 0},
		)

		# Step 1.2: Record operation into result's per-variable history
		_self_offset_h = 64 - self.bits
		_qm = tuple(result_qubits[result_offset + i] for i in range(result_bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) != int and isinstance(other, qint):
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		result.history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) != int and isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	@cython.boundscheck(False)
	@cython.wraparound(False)
	def __ixor__(self, other):
		"""In-place XOR: self ^= other

		Modifies qubits directly (true in-place operation).

		Parameters
		----------
		other : qint or int
			Value to XOR with.

		Returns
		-------
		qint
			Self (modified in-place).

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> a ^= 0b0110
		>>> # a now represents |1010>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int i
		cdef int xor_bits
		cdef size_t gc_before_ixor, gc_delta_ixor
		cdef unsigned int layer_before_ixor
		cdef gate_counts_t range_counts_ixor

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			regs = tuple(self.qubits[self_offset + i] for i in range(self_bits))
			if type(other) == int:
				_uc_seq = Q_not(1)
				_cc_seq = cQ_not(1)
				_record_instruction(
					"ixor_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			elif isinstance(other, qint):
				if other is not self:
					(<qint>other).history.add_blocker(self)
				_cm_other_offset = 64 - (<qint>other).bits
				_cm_xor_bits = self_bits if self_bits < (<qint>other).bits else (<qint>other).bits
				regs = tuple(self.qubits[self_offset + i] for i in range(_cm_xor_bits))
				regs = regs + tuple(
					(<qint>other).qubits[_cm_other_offset + i]
					for i in range(_cm_xor_bits)
				)
				_uc_seq = Q_xor(_cm_xor_bits)
				_cc_seq = cQ_xor(_cm_xor_bits)
				_record_instruction(
					"ixor_qq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			return self

		if type(other) == int:
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")

			# CQ path: for each set bit in classical value, apply Q_not(1)
			gc_before_ixor = (<circuit_s*>_circuit).gate_count
			layer_before_ixor = (<circuit_s*>_circuit).used_layer
			for i in range(self_bits):
				if ((<int64_t>other) >> i) & 1:
					qubit_array[0] = self.qubits[self_offset + i]
					arr = qubit_array
					seq = Q_not(1)
					run_instruction(seq, &arr[0], False, _circuit)
			gc_delta_ixor = (<circuit_s*>_circuit).gate_count - gc_before_ixor
			if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_ixor:
				range_counts_ixor = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_ixor, (<circuit_s*>_circuit).used_layer)
			else:
				range_counts_ixor.t_count = 0
			_record_operation(
				"ixor_cq",
				tuple(self.qubits[self_offset + i] for i in range(self_bits)),
				gate_count=gc_delta_ixor,
				controlled=bool(_controlled),
				depth=(<circuit_s*>_circuit).used_layer - layer_before_ixor,
				t_count=range_counts_ixor.t_count,
				is_composite=True,
				op_params={"width": self_bits, "value": int(other)},
			)
			# Step 6.4: Record history with kind for inverse cancellation
			_ixor_qm = tuple(self.qubits[self_offset + i] for i in range(self_bits)) + (int(other),)
			self.history.append(0, _ixor_qm, kind='xor')
			return self

		if not isinstance(other, qint):
			raise TypeError("Operand must be qint or int")

		if _controlled:
			raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")

		# Step 6.2: Blocker insertion — source operand references dest
		if other is not self:
			(<qint>other).history.add_blocker(self)

		# QQ path: self ^= other using Q_xor
		# Layout: [0..xor_bits-1] = self (target), [xor_bits..2*xor_bits-1] = other (source)
		cdef int other_bits = (<qint>other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits = (<qint>other).qubits
		xor_bits = self_bits if self_bits < other_bits else other_bits

		# Phase 84: Validate qubit_array bounds before writes
		validate_qubit_slots(2 * xor_bits, "__ixor__")

		for i in range(xor_bits):
			qubit_array[i] = self.qubits[self_offset + i]
		for i in range(xor_bits):
			qubit_array[xor_bits + i] = other_qubits[other_offset + i]

		arr = qubit_array
		seq = Q_xor(xor_bits)
		layer_before_ixor = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_ixor:
			range_counts_ixor = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_ixor, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_ixor.t_count = 0
		_record_operation(
			"ixor_qq",
			tuple(qubit_array[i] for i in range(2 * xor_bits)),
			sequence_ptr=<unsigned long long>seq,
			gate_count=seq.total_gate_count,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_ixor,
			t_count=range_counts_ixor.t_count,
		)
		# Step 6.4: Record history with kind for inverse cancellation
		_ixor_qm = tuple(self.qubits[self_offset + i] for i in range(xor_bits)) \
			+ tuple(other_qubits[other_offset + i] for i in range(xor_bits))
		self.history.append(0, _ixor_qm, kind='xor')
		return self

	def __rxor__(self, other):
		"""Reverse XOR for int ^ qint."""
		return self ^ other

	def __invert__(self):
		"""Bitwise NOT: ~self

		Inverts all bits in-place.

		Returns
		-------
		qint
			Self (modified in-place).

		Examples
		--------
		>>> a = qint(0b1010, width=4)
		>>> ~a
		>>> # a now represents |0101>

		Notes
		-----
		Applies X gate to each qubit (parallel execution).
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int layer_before_not
		cdef gate_counts_t range_counts_not

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			self_offset = 64 - self.bits
			regs = tuple(self.qubits[self_offset + i] for i in range(self.bits))
			_uc_seq = Q_not(self.bits)
			_cc_seq = cQ_not(self.bits)
			_record_instruction(
				"not", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
			)
			return self

		# Phase 84: Validate qubit_array bounds before writes
		# NOT uses up to self.bits + 1 slots (controlled case)
		validate_qubit_slots(self.bits + 1, "__invert__")

		# Use width-parameterized NOT for multi-bit qints
		self_offset = 64 - self.bits

		if _controlled:
			# Controlled NOT: [0:bits] = target, [bits] = control
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			qubit_array[self.bits] = (<qint> _control_bool).qubits[63]
			seq = cQ_not(self.bits)
		else:
			# Uncontrolled NOT: [0:bits] = target
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			seq = Q_not(self.bits)

		arr = qubit_array
		layer_before_not = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_not:
			range_counts_not = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_not, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_not.t_count = 0
		_record_operation(
			"not",
			tuple(qubit_array[i] for i in range(self.bits + (1 if _controlled else 0))),
			sequence_ptr=<unsigned long long>seq,
			gate_count=seq.total_gate_count,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_not,
			t_count=range_counts_not.t_count,
		)

		return self

	# ====================================================================
	# QUANTUM COPY OPERATIONS
	# Phase 42: CNOT-based state copying for quantum expressions
	# ====================================================================

	def copy(self):
		"""Create a quantum copy of this integer.

		Allocates fresh qubits and applies CNOT gates from each source qubit
		to the corresponding target qubit, producing a new qint whose
		computational-basis measurement outcome matches the source.

		Returns
		-------
		qint
			New quantum integer with CNOT-entangled fresh qubits.

		Raises
		------
		ValueError
			If this qint has been uncomputed.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> b = a.copy()
		>>> b.width
		4

		Notes
		-----
		The copy has distinct qubits from the source (no shared references).
		The copy participates in scope-based automatic uncomputation.
		For computational basis states, the copy measures to the same value.
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset, result_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		self._check_not_uncomputed()

		# Phase 84: Validate qubit_array bounds before writes
		# copy uses 2*self.bits slots: [target:N], [source:N]
		validate_qubit_slots(2 * self.bits, "copy")

		# Allocate fresh result qint with |0> qubits
		result = qint(width=self.bits)

		# Apply CNOTs: source -> result (XOR pattern, result starts at 0)
		self_offset = 64 - self.bits
		result_offset = 64 - result.bits
		qubit_array[:self.bits] = result.qubits[result_offset:result_offset + self.bits]
		qubit_array[self.bits:2*self.bits] = self.qubits[self_offset:64]
		arr = qubit_array
		seq = Q_xor(self.bits)
		run_instruction(seq, &arr[0], False, _circuit)

		result.operation_type = 'COPY'
		result.add_dependency(self)

		return result

	def copy_onto(self, target):
		"""XOR-copy this integer's state onto an existing target.

		Applies CNOT gates from each source qubit to the corresponding
		target qubit: target ^= self. If target starts at |0>, this
		produces a copy of self. If target is non-zero, this XORs self
		into target.

		Parameters
		----------
		target : qint
			Target quantum integer to copy onto. Must have same bit width.

		Raises
		------
		ValueError
			If target width does not match source width.
		ValueError
			If this qint has been uncomputed.
		TypeError
			If target is not a qint.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> b = qint(width=4)
		>>> a.copy_onto(b)
		>>> # b now holds a copy of a's state

		Notes
		-----
		This is a raw CNOT operation. The caller manages the target's
		lifecycle and uncomputation. No layer tracking or dependency
		is set on the target by this method.
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset, target_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()

		self._check_not_uncomputed()

		if not isinstance(target, qint):
			raise TypeError("copy_onto target must be a qint")

		if (<qint>target).bits != self.bits:
			raise ValueError(
				f"Width mismatch: source has {self.bits} bits, "
				f"target has {(<qint>target).bits} bits"
			)

		# Phase 84: Validate qubit_array bounds before writes
		# copy_onto uses 2*self.bits slots: [target:N], [source:N]
		validate_qubit_slots(2 * self.bits, "copy_onto")

		# Apply CNOTs: source -> target
		self_offset = 64 - self.bits
		target_offset = 64 - (<qint>target).bits
		qubit_array[:self.bits] = (<qint>target).qubits[target_offset:target_offset + self.bits]
		qubit_array[self.bits:2*self.bits] = self.qubits[self_offset:64]
		arr = qubit_array
		seq = Q_xor(self.bits)
		run_instruction(seq, &arr[0], False, _circuit)

	def __getitem__(self, item: int):
		"""Access individual qubit as qbool: self[index]

		Parameters
		----------
		item : int
			Qubit index (right-aligned, 0 = LSB).

		Returns
		-------
		qbool
			Single-qubit quantum boolean.

		Examples
		--------
		>>> a = qint(0b1010, width=4)
		>>> bit1 = a[1]  # Second bit from right (LSB=0)
		>>> # bit1 is qbool representing |1>
		"""
		from quantum_language.qbool import qbool
		if item < 0 or item >= self.bits:
			raise IndexError(f"qubit index {item} out of range for qint with width {self.bits}")
		# Use uint32 dtype to match qint.qubits memory view type
		bit_list = np.zeros(64, dtype=np.uint32)
		bit_list[-1] = self.qubits[64 - self.bits + item]
		a = qbool(create_new = False, bit_list = bit_list)
		return a

