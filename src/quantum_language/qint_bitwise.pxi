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
		cdef int start_layer
		cdef int i
		cdef int _self_pad, _other_pad
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int[:] result_qubits
		cdef unsigned int[:] other_qubits
		cdef unsigned int[:] pad_qubits

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Quick-013: Save and set layer floor to prevent optimizer from placing gates before start_layer
		cdef unsigned int _saved_floor_and = (<circuit_s*>_circuit).layer_floor if _circuit_initialized else 0
		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = start_layer

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_and
			raise TypeError("Operand must be qint or int")

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
				raise NotImplementedError("Controlled quantum-quantum AND not yet supported")
			else:
				seq = Q_and(result_bits)

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit, 0)

		# Capture end layer
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = _saved_floor_and
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
		cdef int start_layer
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_or = (<circuit_s*>_circuit).layer_floor if _circuit_initialized else 0
		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = start_layer

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_or
			raise TypeError("Operand must be qint or int")

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
		run_instruction(seq, &arr[0], False, _circuit, 0)

		# Capture end layer
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = _saved_floor_or
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
		cdef int start_layer
		cdef int i
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int[:] result_qubits
		cdef unsigned int[:] other_qubits

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_xor = (<circuit_s*>_circuit).layer_floor if _circuit_initialized else 0
		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = start_layer

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_xor
			raise TypeError("Operand must be qint or int")

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

		# First, copy self to result by XORing self into result (result starts at 0)
		# CYT-03: Replace slice with explicit loop for memory view optimization
		result_qubits = result.qubits
		for i in range(self.bits):
			qubit_array[i] = result_qubits[result_offset + i]
		for i in range(self.bits):
			qubit_array[self.bits + i] = self.qubits[self_offset + i]
		arr = qubit_array
		seq = Q_xor(self.bits)  # XOR self into result (copying self to result)
		run_instruction(seq, &arr[0], False, _circuit, 0)

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
						run_instruction(seq, &arr[0], False, _circuit, 0)
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
			run_instruction(seq, &arr[0], False, _circuit, 0)

		# Capture end layer
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = _saved_floor_xor
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
		# Phase 60-04: Thin Cython wrapper -- all hot-path logic moved to C
		# (hot_path_xor.c). We only extract qubit indices from Python objects
		# here, then call the C function with nogil.
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int self_qa[64]
		cdef unsigned int other_qa[64]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int i
		cdef int64_t classical_value = 0

		# Extract self qubits (right-aligned in 64-element array)
		for i in range(self_bits):
			self_qa[i] = self.qubits[self_offset + i]

		if type(other) == int:
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
			classical_value = <int64_t>other
			with nogil:
				hot_path_ixor_cq(_circuit, self_qa, self_bits, classical_value)
			return self

		if not isinstance(other, qint):
			raise TypeError("Operand must be qint or int")

		if _controlled:
			raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")

		# Extract other qubits for quantum-quantum XOR
		cdef int other_bits = (<qint>other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint>other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		with nogil:
			hot_path_ixor_qq(_circuit, self_qa, self_bits,
							other_qa, other_bits)
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

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()

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
		run_instruction(seq, &arr[0], False, _circuit, 0)

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
		cdef int start_layer
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		self._check_not_uncomputed()

		# Phase 84: Validate qubit_array bounds before writes
		# copy uses 2*self.bits slots: [target:N], [source:N]
		validate_qubit_slots(2 * self.bits, "copy")

		# Capture start layer before any gates
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_copy = (<circuit_s*>_circuit).layer_floor if _circuit_initialized else 0
		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = start_layer

		# Allocate fresh result qint with |0> qubits
		result = qint(width=self.bits)

		# Apply CNOTs: source -> result (XOR pattern, result starts at 0)
		self_offset = 64 - self.bits
		result_offset = 64 - result.bits
		qubit_array[:self.bits] = result.qubits[result_offset:result_offset + self.bits]
		qubit_array[self.bits:2*self.bits] = self.qubits[self_offset:64]
		arr = qubit_array
		seq = Q_xor(self.bits)
		run_instruction(seq, &arr[0], False, _circuit, 0)

		# Layer tracking for uncomputation
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
		result.operation_type = 'COPY'
		result.add_dependency(self)

		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = _saved_floor_copy
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
		run_instruction(seq, &arr[0], False, _circuit, 0)

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

