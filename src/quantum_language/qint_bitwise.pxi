# ====================================================================
# BITWISE OPERATIONS
# ====================================================================
#
# This is a Cython include file (.pxi) containing bitwise operation
# methods for the qint class. It is included into qint.pyx via:
#   include "qint_bitwise.pxi"
#
# Methods are indented at class level and become part of the qint class
# when the file is compiled. Do NOT include imports or class declarations
# here - those remain in qint.pyx.
#
# Phase 41: Updated to match inline implementations with correct
# allocation ordering (padding before result) and layer tracking.
# ====================================================================

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
	cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
	cdef bint _circuit_initialized = _get_circuit_initialized()
	cdef bint _controlled = _get_controlled()

	# Phase 18: Check for use-after-uncompute
	self._check_not_uncomputed()
	if isinstance(other, qint):
		(<qint>other)._check_not_uncomputed()

	# Capture start layer
	start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

	# Determine result width
	if type(other) == int:
		classical_width = other.bit_length() if other > 0 else 1
		result_bits = max(self.bits, classical_width)
	elif isinstance(other, qint):
		result_bits = max(self.bits, (<qint>other).bits)
	else:
		raise TypeError("Operand must be qint or int")

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
	self_offset = 64 - self.bits
	result_offset = 64 - result_bits

	# Output qubits (result) - at position 0
	qubit_array[:result_bits] = result.qubits[result_offset:64]
	# Self qubits (LSB positions) - at position result_bits
	qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]
	# Zero-extend self if narrower: use pre-allocated padding for MSB
	if _self_pad_qint is not None:
		_self_pad = result_bits - self.bits
		qubit_array[result_bits + self.bits:2*result_bits] = _self_pad_qint.qubits[64 - _self_pad:64]

	if type(other) == int:
		# Classical-quantum AND
		if _controlled:
			raise NotImplementedError("Controlled classical-quantum AND not yet supported")
		else:
			seq = CQ_and(result_bits, other)
	else:
		# Quantum-quantum AND
		other_offset = 64 - (<qint>other).bits
		qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]
		# Zero-extend other if narrower: use pre-allocated padding for MSB
		if _other_pad_qint is not None:
			_other_pad = result_bits - (<qint>other).bits
			qubit_array[2*result_bits + (<qint>other).bits:3*result_bits] = _other_pad_qint.qubits[64 - _other_pad:64]

		if _controlled:
			raise NotImplementedError("Controlled quantum-quantum AND not yet supported")
		else:
			seq = Q_and(result_bits)

	arr = qubit_array
	run_instruction(seq, &arr[0], False, _circuit)

	# Capture end layer
	result._start_layer = start_layer
	result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

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

	# Determine result width
	if type(other) == int:
		classical_width = other.bit_length() if other > 0 else 1
		result_bits = max(self.bits, classical_width)
	elif isinstance(other, qint):
		result_bits = max(self.bits, (<qint>other).bits)
	else:
		raise TypeError("Operand must be qint or int")

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

	# Build qubit array
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
	run_instruction(seq, &arr[0], False, _circuit)

	# Capture end layer
	result._start_layer = start_layer
	result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

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
	cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
	cdef bint _circuit_initialized = _get_circuit_initialized()
	cdef bint _controlled = _get_controlled()

	# Phase 18: Check for use-after-uncompute
	self._check_not_uncomputed()
	if isinstance(other, qint):
		(<qint>other)._check_not_uncomputed()

	# Capture start layer
	start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

	# Determine result width
	if type(other) == int:
		classical_width = other.bit_length() if other > 0 else 1
		result_bits = max(self.bits, classical_width)
	elif isinstance(other, qint):
		result_bits = max(self.bits, (<qint>other).bits)
	else:
		raise TypeError("Operand must be qint or int")

	# Allocate result (ancilla qubits)
	result = qint(width=result_bits)

	# Register dependencies
	result.add_dependency(self)
	if type(other) != int:
		result.add_dependency(other)
	result.operation_type = 'XOR'

	# Copy self qubits to result using CNOT pattern
	self_offset = 64 - self.bits
	result_offset = 64 - result_bits

	# First, copy self to result by XORing self into result (result starts at 0)
	qubit_array[:self.bits] = result.qubits[result_offset:result_offset + self.bits]
	qubit_array[self.bits:2*self.bits] = self.qubits[self_offset:64]
	arr = qubit_array
	seq = Q_xor(self.bits)  # XOR self into result (copying self to result)
	run_instruction(seq, &arr[0], False, _circuit)

	# Now XOR other into result
	if type(other) == int:
		# Classical XOR: apply X gates where classical bits are 1
		if _controlled:
			raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
		else:
			for i in range(result_bits):
				if (other >> i) & 1:
					qubit_array[0] = result.qubits[64 - result_bits + i]
					arr = qubit_array
					seq = Q_not(1)
					run_instruction(seq, &arr[0], False, _circuit)
	else:
		# Quantum-quantum XOR: result ^= other
		other_offset = 64 - (<qint>other).bits
		qubit_array[:(<qint>other).bits] = result.qubits[result_offset:result_offset + (<qint>other).bits]
		qubit_array[(<qint>other).bits:2*(<qint>other).bits] = (<qint>other).qubits[other_offset:64]

		if _controlled:
			raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")
		else:
			seq = Q_xor((<qint>other).bits)

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)

	# Capture end layer
	result._start_layer = start_layer
	result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

	return result

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
	cdef int self_offset, other_offset
	cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
	cdef bint _controlled = _get_controlled()

	# XOR can be done truly in-place since target ^= source modifies target
	self_offset = 64 - self.bits

	if type(other) == int:
		# Classical XOR: apply X gates where classical bits are 1
		if _controlled:
			raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
		else:
			for i in range(self.bits):
				if (other >> i) & 1:
					qubit_array[0] = self.qubits[64 - self.bits + i]
					arr = qubit_array
					seq = Q_not(1)
					run_instruction(seq, &arr[0], False, _circuit)
	elif isinstance(other, qint):
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
	run_instruction(seq, &arr[0], False, _circuit)

	return self

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
	bit_list = np.zeros(64)
	bit_list[-1] = self.qubits[item]
	a = qbool(create_new = False, bit_list = bit_list)
	return a
