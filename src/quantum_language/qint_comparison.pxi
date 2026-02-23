	# ====================================================================
	# COMPARISON OPERATIONS
	# Phase 41: Added layer tracking for uncomputation support
	# ====================================================================

	def __eq__(self, other):
		"""Equality comparison: self == other

		Uses C-level CQ_equal_width for qint == int (O(n) gates).
		Uses subtract-add-back pattern for qint == qint.

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating equality.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(5, width=8)
		>>> result = (a == b)
		>>> # result is qbool representing |True>

		Notes
		-----
		qint == int: Uses C-level CQ_equal_width circuit.
		qint == qint: Uses subtract-add-back pattern (a-=b, check a==0, a+=b).
		Phase 74-03: AND-ancilla allocated for MCX decomposition (bits>=3 uncontrolled,
		bits>=2 controlled).
		"""
		from .qbool import qbool
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset
		cdef int start
		cdef int start_layer
		cdef int num_and_anc
		cdef unsigned int and_anc_start
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef qubit_allocator_t *alloc

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Phase 41: Capture start layer for uncomputation
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Quick-013: Save and set layer floor to prevent optimizer from placing gates before start_layer
		cdef unsigned int _saved_floor = (<circuit_s*>_circuit).layer_floor if _circuit_initialized else 0
		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = start_layer

		# Handle qint == qint case first (must come before int check)
		if type(other) == qint:
			# Self-comparison optimization: a == a is always True
			if self is other:
				if _circuit_initialized:
					(<circuit_s*>_circuit).layer_floor = _saved_floor
				return qbool(True)

			# Subtract-add-back pattern: (a - b) == 0, then restore a
			# 1. In-place subtraction: self -= other
			self -= other

			# 2. Compare to zero: result = (self == 0)
			result = self == 0  # Recursive call uses qint == int path

			# 3. Restore operand: self += other
			self += other

			# Track dependencies on compared qints
			# Clear dependencies from recursive (self == 0) call, replace with actual operands
			result.dependency_parents = []
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'EQ'

			# Phase 41: Layer tracking for uncomputation
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor
			return result

		# Handle qint == int case using C-level CQ_equal_width
		if type(other) == int:
			# Phase 84: Validate qubit_array bounds before writes
			# eq uses up to 1 + self.bits + 1 + (self.bits - 1) slots
			validate_qubit_slots(2 * self.bits + 2, "__eq__")

			# Classical overflow check: if value doesn't fit in bits, not equal
			# For unsigned interpretation: value must be in [0, 2^bits - 1]
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0 or other > max_val:
				# Overflow: value outside range - definitely not equal
				# Return qbool initialized to |0> (False)
				if _circuit_initialized:
					(<circuit_s*>_circuit).layer_floor = _saved_floor
				return qbool(False)

			# Get comparison sequence from C
			if _controlled:
				seq = cCQ_equal_width(self.bits, other)
			else:
				seq = CQ_equal_width(self.bits, other)

			if seq == NULL:
				raise RuntimeError(f"CQ_equal_width failed for bits={self.bits}, value={other}")

			# Check for overflow (empty sequence returned by C)
			if seq.num_layer == 0:
				# Overflow detected by C layer - definitely not equal
				if _circuit_initialized:
					(<circuit_s*>_circuit).layer_floor = _saved_floor
				return qbool(False)

			# Allocate result qbool
			result = qbool()

			# Build qubit array: [0] = result, [1:bits+1] = operand
			# Result qubit (from qbool, stored at index 63 in right-aligned storage)
			qubit_array[0] = (<qint>result).qubits[63]

			# Self operand qubits (right-aligned)
			# C backend expects MSB-first, so reverse bit order
			self_offset = 64 - self.bits
			for i in range(self.bits):
				qubit_array[1 + i] = self.qubits[self_offset + (self.bits - 1 - i)]

			start = 1 + self.bits

			# Add control qubit if controlled context
			if _controlled:
				qubit_array[start] = (<qint>_control_bool).qubits[63]
				start += 1

			# Phase 74-03: Allocate AND-ancilla for MCX decomposition
			# Uncontrolled bits >= 3: needs (bits - 2) AND-ancilla at [bits+1 .. 2*bits-2]
			# Controlled bits >= 2: needs (bits - 1) AND-ancilla at [bits+2 .. 2*bits]
			num_and_anc = 0
			and_anc_start = 0
			if _controlled and self.bits >= 2:
				num_and_anc = self.bits - 1
			elif not _controlled and self.bits >= 3:
				num_and_anc = self.bits - 2

			if num_and_anc > 0 and _circuit_initialized:
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					and_anc_start = allocator_alloc(alloc, num_and_anc, True)
					if and_anc_start != <unsigned int>(-1):
						for i in range(num_and_anc):
							qubit_array[start + i] = and_anc_start + i

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)

			# Free AND-ancilla after use
			if num_and_anc > 0 and _circuit_initialized and and_anc_start != <unsigned int>(-1):
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					allocator_free(alloc, and_anc_start, num_and_anc)

			# Track dependency on compared qint (classical doesn't need tracking)
			result.add_dependency(self)
			result.operation_type = 'EQ'

			# Phase 41: Layer tracking for uncomputation
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor
			return result

		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = _saved_floor
		raise TypeError("Comparison requires qint or int")

	def __ne__(self, other):
		"""Inequality comparison: self != other

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating inequality.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> result = (a != b)
		>>> # result is qbool representing |True>
		"""
		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()
		return ~(self == other)

	def __lt__(self, other):
		"""Less-than comparison: self < other

		Uses widened (n+1)-bit subtraction and sign bit check. Preserves inputs.

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self < other.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = qint(5, width=8)
		>>> result = (a < b)
		>>> # result is qbool representing |True>

		Notes
		-----
		Uses widened temporaries (n+1 bits) to handle MSB boundary cases correctly.
		"""
		from .qbool import qbool
		cdef int comp_width
		cdef int operand_bits, i_bit
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer for uncomputation tracking
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_lt = (<circuit_s*>_circuit).layer_floor if _circuit_initialized else 0
		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = start_layer

		# Self-comparison optimization
		if self is other:
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_lt
			return qbool(False)  # x < x is always false

		# Handle qint operand
		if type(other) == qint:
			# Phase 84: Validate qubit_array bounds before writes
			# lt uses 2 slots per CNOT copy (qubit_array[0], qubit_array[1])
			validate_qubit_slots(2, "__lt__")

			# a < b means (a - b) is negative in signed interpretation.
			# To handle full unsigned range, use (n+1)-bit subtraction:
			# extend both operands by 1 bit (MSB=0 = unsigned) so the sign bit
			# is never polluted by valid data bits.
			comp_width = max(self.bits, (<qint>other).bits) + 1
			# Create widened copies (zero-extended to comp_width)
			temp_self = qint(0, width=comp_width)
			temp_other = qint(0, width=comp_width)

			# Copy operand bits to temp using LSB-aligned CNOT (upper bits stay 0 = zero-extension)
			# CRITICAL: Cannot use ^= operator here because __ixor__ misaligns qubits when widths differ.

			# Copy self's bits to temp_self (LSB-aligned)
			operand_bits = self.bits
			for i_bit in range(operand_bits):
				qubit_array[0] = (<qint>temp_self).qubits[64 - comp_width + i_bit]
				qubit_array[1] = self.qubits[64 - operand_bits + i_bit]
				arr = qubit_array
				seq = Q_xor(1)
				run_instruction(seq, &arr[0], False, _circuit)

			# Copy other's bits to temp_other (LSB-aligned)
			operand_bits = (<qint>other).bits
			for i_bit in range(operand_bits):
				qubit_array[0] = (<qint>temp_other).qubits[64 - comp_width + i_bit]
				qubit_array[1] = (<qint>other).qubits[64 - operand_bits + i_bit]
				arr = qubit_array
				seq = Q_xor(1)
				run_instruction(seq, &arr[0], False, _circuit)

			# Subtract: temp_self -= temp_other
			temp_self -= temp_other
			# MSB of widened result is the true sign bit
			msb = temp_self[comp_width - 1]
			result = qbool()
			result ^= msb
			# Track dependencies on original operands
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'LT'
			# Phase 41 gap closure: Add layer tracking so widened-temp gates are
			# reversed when result is uncomputed. The widened temps themselves have
			# no layer tracking, so there is no double-reversal risk.
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_lt
			return result

		# Handle int operand
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0:
				if _circuit_initialized:
					(<circuit_s*>_circuit).layer_floor = _saved_floor_lt
				return qbool(False)  # qint always >= 0, so qint < negative is false
			if other > max_val:
				if _circuit_initialized:
					(<circuit_s*>_circuit).layer_floor = _saved_floor_lt
				return qbool(True)  # qint always < large value that doesn't fit

			# Create temp qint to use the qint-qint __lt__ path
			temp = qint(other, width=self.bits)
			_result = self < temp
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_lt
			return _result

		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = _saved_floor_lt
		raise TypeError("Comparison requires qint or int")

	def __gt__(self, other):
		"""Greater-than comparison: self > other

		Uses widened (n+1)-bit subtraction for qint operands.
		For int operands, creates temp qint and delegates.

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self > other.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> result = (a > b)
		>>> # result is qbool representing |True>
		"""
		from .qbool import qbool
		cdef int comp_width
		cdef int operand_bits, i_bit
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer for uncomputation tracking
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_gt = (<circuit_s*>_circuit).layer_floor if _circuit_initialized else 0
		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = start_layer

		# Self-comparison optimization
		if self is other:
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_gt
			return qbool(False)  # x > x is always false

		# Handle qint operand
		if type(other) == qint:
			# Phase 84: Validate qubit_array bounds before writes
			validate_qubit_slots(2, "__gt__")

			# a > b means (b - a) is negative in signed interpretation.
			comp_width = max(self.bits, (<qint>other).bits) + 1
			# Create widened copies (zero-extended to comp_width)
			temp_other = qint(0, width=comp_width)
			temp_self = qint(0, width=comp_width)

			# Copy operand bits to temp using LSB-aligned CNOT
			# Copy other's bits to temp_other (LSB-aligned)
			operand_bits = (<qint>other).bits
			for i_bit in range(operand_bits):
				qubit_array[0] = (<qint>temp_other).qubits[64 - comp_width + i_bit]
				qubit_array[1] = (<qint>other).qubits[64 - operand_bits + i_bit]
				arr = qubit_array
				seq = Q_xor(1)
				run_instruction(seq, &arr[0], False, _circuit)

			# Copy self's bits to temp_self (LSB-aligned)
			operand_bits = self.bits
			for i_bit in range(operand_bits):
				qubit_array[0] = (<qint>temp_self).qubits[64 - comp_width + i_bit]
				qubit_array[1] = self.qubits[64 - operand_bits + i_bit]
				arr = qubit_array
				seq = Q_xor(1)
				run_instruction(seq, &arr[0], False, _circuit)

			# Subtract: temp_other -= temp_self
			temp_other -= temp_self
			# MSB of widened result is the true sign bit
			msb = temp_other[comp_width - 1]
			result = qbool()
			result ^= msb
			# Track dependencies on original operands
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'GT'
			# Phase 41 gap closure: Add layer tracking so widened-temp gates are
			# reversed when result is uncomputed. The widened temps themselves have
			# no layer tracking, so there is no double-reversal risk.
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_gt
			return result

		# Handle int operand
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0:
				if _circuit_initialized:
					(<circuit_s*>_circuit).layer_floor = _saved_floor_gt
				return qbool(True)  # qint always >= 0, so qint > negative is true
			if other > max_val:
				if _circuit_initialized:
					(<circuit_s*>_circuit).layer_floor = _saved_floor_gt
				return qbool(False)  # qint always < large value, so not >

			# Create temp qint to use the qint-qint __gt__ path
			temp = qint(other, width=self.bits)
			_result = self > temp
			if _circuit_initialized:
				(<circuit_s*>_circuit).layer_floor = _saved_floor_gt
			return _result

		if _circuit_initialized:
			(<circuit_s*>_circuit).layer_floor = _saved_floor_gt
		raise TypeError("Comparison requires qint or int")

	def __le__(self, other):
		"""Less-than-or-equal comparison: self <= other

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self <= other.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = qint(5, width=8)
		>>> result = (a <= b)
		>>> # result is qbool representing |True>

		Notes
		-----
		a <= b is equivalent to NOT(a > b).
		"""
		from .qbool import qbool

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(True)  # x <= x is always true

		# Handle qint operand
		if type(other) == qint:
			# a <= b is equivalent to NOT(a > b)
			return ~(self > other)

		# Handle int operand
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(False)  # qint >= 0, so qint <= negative is false
			if other > max_val:
				return qbool(True)  # qint always <= large value

			# a <= b is equivalent to NOT(a > b)
			return ~(self > other)

		raise TypeError("Comparison requires qint or int")

	def __ge__(self, other):
		"""Greater-than-or-equal comparison: self >= other

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self >= other.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> result = (a >= b)
		>>> # result is qbool representing |True>

		Notes
		-----
		Delegates to NOT(self < other) which uses widened-temp pattern.
		"""
		from .qbool import qbool

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(True)  # x >= x is always true
		# self >= other is equivalent to NOT (self < other)
		return ~(self < other)

