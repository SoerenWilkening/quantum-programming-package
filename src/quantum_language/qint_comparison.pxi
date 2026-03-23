	# ====================================================================
	# COMPARISON OPERATIONS
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
		cdef int num_and_anc
		cdef unsigned int and_anc_start
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef qubit_allocator_t *alloc
		cdef size_t gc_before_eq, gc_delta_eq
		cdef unsigned int layer_before_eq
		cdef gate_counts_t range_counts_eq

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Handle qint == qint case first (must come before int check)
		if type(other) == qint:
			# Self-comparison optimization: a == a is always True
			if self is other:
				return qbool(True)

			# Subtract-add-back pattern: (a - b) == 0, then restore a
			# Save history length so we can trim entries added by internal -= / +=
			_eq_hist_len = len(self.history)
			# 1. In-place subtraction: self -= other
			self -= other

			# 2. Compare to zero: result = (self == 0)
			result = self == 0  # Recursive call uses qint == int path

			# 3. Restore operand: self += other
			self += other
			# Trim internal in-place history entries (Step 6.4 transparency)
			del self.history.entries[_eq_hist_len:]

			# Track dependencies on compared qints
			# Clear dependencies from recursive (self == 0) call, replace with actual operands
			result.dependency_parents = []
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'EQ'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_other_offset_h = 64 - (<qint>other).bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operands reference the result
			self.history.add_blocker(result)
			(<qint>other).history.add_blocker(result)

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
				return qbool(False)

			# Compile-mode: record IR entry, skip gate emission
			if _is_compile_mode():
				result = qbool()
				_uc_seq = CQ_equal_width(self.bits, other)
				_cc_seq = cCQ_equal_width(self.bits, other)
				self_offset = 64 - self.bits
				regs = ((<qint>result).qubits[63],)
				regs = regs + tuple(
					self.qubits[self_offset + (self.bits - 1 - i)]
					for i in range(self.bits)
				)
				_record_instruction(
					"eq_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				result.add_dependency(self)
				result.operation_type = 'EQ'
				self.history.add_blocker(result)
				return result

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
			gc_before_eq = (<circuit_s*>_circuit).gate_count
			layer_before_eq = (<circuit_s*>_circuit).used_layer
			run_instruction(seq, &arr[0], False, _circuit)
			gc_delta_eq = (<circuit_s*>_circuit).gate_count - gc_before_eq
			if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_eq:
				range_counts_eq = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_eq, (<circuit_s*>_circuit).used_layer)
			else:
				range_counts_eq.t_count = 0
			_record_operation(
				"eq_cq",
				tuple(qubit_array[i] for i in range(start)),
				sequence_ptr=<unsigned long long>seq,
				gate_count=gc_delta_eq,
				controlled=bool(_controlled),
				depth=(<circuit_s*>_circuit).used_layer - layer_before_eq,
				t_count=range_counts_eq.t_count,
			)

			# Free AND-ancilla after use
			if num_and_anc > 0 and _circuit_initialized and and_anc_start != <unsigned int>(-1):
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					allocator_free(alloc, and_anc_start, num_and_anc)

			# Track dependency on compared qint (classical doesn't need tracking)
			result.add_dependency(self)
			result.operation_type = 'EQ'

			# Step 1.2: Record operation into result's per-variable history
			# Must match the exact qubit_array layout passed to run_instruction:
			# [0]=result, [1..bits]=operand (MSB-first), [opt ctrl], then AND-ancilla.
			# Store core qubits (no ancilla) and num_and_anc so the inverse path
			# can allocate fresh ancilla at replay time.
			_qm = tuple(qubit_array[i] for i in range(start))
			result.history.append(<unsigned long long>seq, _qm, num_and_anc)

			# Step 6.2: Blocker insertion — source operand references the result
			self.history.add_blocker(result)

			return result

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

		Uses borrow-ancilla pattern with split-register arithmetic.
		Allocates a single ancilla qubit as borrow bit, performs (n+1)-bit
		subtraction across [a, ancilla], extracts borrow into result qbool,
		restores via addition, and deallocates ancilla.

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
		"""
		from .qbool import qbool
		cdef int comp_width, i
		cdef sequence_t *seq
		cdef sequence_t *seq_add
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef circuit_s *_circ = <circuit_s*>_circuit
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef qubit_allocator_t *alloc
		cdef unsigned int borrow_ancilla, zero_ext, toff_ancilla
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int other_bits, other_offset

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(False)  # x < x is always false

		# Compile-mode: record "lt" IR entry with sequence pointers (Phase 11.5)
		# QFT mode only — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			self_offset = 64 - self.bits
			alloc = circuit_get_allocator(_circ)
			if type(other) == int:
				# Classical overflow checks (must match non-compile path)
				max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
				if other < 0:
					return qbool(False)
				if other == 0:
					return qbool(False)
				if other > max_val:
					return qbool(True)
				result = qbool()
				# CQ lt: sequence layout [0]=result, [1..bits]=A, [bits+1]=borrow
				_uc_seq = CQ_less_than(self.bits, <int64_t>other)
				_cc_seq = cCQ_less_than(self.bits, <int64_t>other)
				# Allocate borrow ancilla for IR execution during capture
				_lt_borrow = allocator_alloc(alloc, 1, True)
				regs = ((<qint>result).qubits[63],)
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
				regs = regs + (_lt_borrow,)
				_record_instruction(
					"lt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _lt_borrow, 1)
				result.add_dependency(self)
				result.operation_type = 'LT'
				self.history.add_blocker(result)
				return result
			elif type(other) == qint:
				# QQ lt: sequence layout [0]=result, [1.._comp_bits]=A,
				# [_comp_bits+1..2*_comp_bits]=B, [2*_comp_bits+1]=borrow,
				# [2*_comp_bits+2]=zero_ext
				# Total abstract qubits: 2*_comp_bits + 3
				_comp_bits = self.bits if self.bits >= (<qint>other).bits else (<qint>other).bits
				_uc_seq = QQ_less_than(_comp_bits)
				_cc_seq = cQQ_less_than(_comp_bits)
				other_offset = 64 - (<qint>other).bits
				# Pad slots needed for shorter operand + borrow + zero_ext
				_self_pad = _comp_bits - self.bits
				_other_pad = _comp_bits - (<qint>other).bits
				_lt_anc = allocator_alloc(alloc, 2 + _self_pad + _other_pad, True)
				result = qbool()
				regs = ((<qint>result).qubits[63],)
				# A: self qubits padded to _comp_bits with zero-init ancilla
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
				for _p in range(_self_pad):
					regs = regs + (_lt_anc + 2 + _p,)
				# B: other qubits padded to _comp_bits with zero-init ancilla
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
				for _p in range(_other_pad):
					regs = regs + (_lt_anc + 2 + _self_pad + _p,)
				regs = regs + (_lt_anc, _lt_anc + 1)
				_record_instruction(
					"lt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _lt_anc, 2 + _self_pad + _other_pad)
				result.add_dependency(self)
				result.add_dependency(other)
				result.operation_type = 'LT'
				self.history.add_blocker(result)
				(<qint>other).history.add_blocker(result)
				return result

		# Handle qint operand: borrow-ancilla via (n+1)-bit QQ addition
		if type(other) == qint:
			other_bits = (<qint>other).bits
			other_offset = 64 - other_bits
			comp_width = (self_bits if self_bits > other_bits else other_bits) + 1

			# Save history length so we can trim entries added by internal -= / +=
			_lt_hist_len = len(self.history)
			# 1. In-place mod-n subtraction: self -= other
			self -= other

			# 2. Allocate borrow ancilla + zero-extension ancilla
			alloc = circuit_get_allocator(_circ)
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					borrow_ancilla = allocator_alloc(alloc, 2, True)
					zero_ext = borrow_ancilla + 1
				else:
					# Toffoli QQ_add(n) needs 1 carry ancilla for n>=2
					borrow_ancilla = allocator_alloc(alloc, 3, True)
					zero_ext = borrow_ancilla + 1
					toff_ancilla = borrow_ancilla + 2
			else:
				borrow_ancilla = allocator_alloc(alloc, 2, True)
				zero_ext = borrow_ancilla + 1

			# 3. Build qubit array for (comp_width)-bit QQ addition
			#    After mod-n sub, self holds (self_orig - other) mod 2^n.
			#    Adding other back in (n+1)-bit: carry into borrow_ancilla
			#    iff self_orig < other (wrapping occurred).
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					# toffoli_QQ_add(1): [target, other]
					qa[0] = borrow_ancilla  # target = borrow (MSB of extended self)
					qa[1] = zero_ext        # other = zero-ext MSB of other
				else:
					# toffoli_QQ_add(n>=2): [other, target, carry_ancilla]
					# other = [other_qubits..., zero_ext]
					for i in range(other_bits):
						qa[i] = (<qint>other).qubits[other_offset + i]
					qa[other_bits] = zero_ext
					# Pad if other_bits < comp_width - 1 (handled by zero_ext at MSB)
					# target = [self_qubits..., borrow_ancilla]
					for i in range(self_bits):
						qa[comp_width + i] = self.qubits[self_offset + i]
					qa[comp_width + self_bits] = borrow_ancilla
					# carry ancilla
					qa[2 * comp_width] = toff_ancilla
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
			else:
				# QFT QQ_add(n): [target(n), other(n)]
				# target = [self_qubits..., borrow_ancilla]
				for i in range(self_bits):
					qa[i] = self.qubits[self_offset + i]
				qa[self_bits] = borrow_ancilla
				# other = [other_qubits..., zero_ext]
				for i in range(other_bits):
					qa[comp_width + i] = (<qint>other).qubits[other_offset + i]
				qa[comp_width + other_bits] = zero_ext
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)

			# 4. Extract borrow into result qbool
			result = qbool()
			qubit_array[0] = (<qint>result).qubits[63]
			qubit_array[1] = borrow_ancilla
			arr = qubit_array
			seq_add = Q_xor(1)
			run_instruction(seq_add, &arr[0], False, _circuit)

			# 5. Undo the (n+1)-bit addition (inverse)
			if _circ.arithmetic_mode == 1:  # Toffoli
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)
			else:
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)

			# 6. Restore self: self += other
			self += other
			# Trim internal in-place history entries (Step 6.4 transparency)
			del self.history.entries[_lt_hist_len:]

			# 7. Deallocate ancilla
			if _circ.arithmetic_mode == 1 and comp_width > 1:
				allocator_free(alloc, borrow_ancilla, 3)
			else:
				allocator_free(alloc, borrow_ancilla, 2)

			# Track dependencies on original operands
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'LT'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_other_offset_h = 64 - (<qint>other).bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operands reference the result
			self.history.add_blocker(result)
			(<qint>other).history.add_blocker(result)

			return result

		# Handle int operand: borrow-ancilla via split-register CQ subtraction
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(False)  # qint always >= 0, so qint < negative is false
			if other == 0:
				return qbool(False)  # unsigned qint is never < 0
			if other > max_val:
				return qbool(True)  # qint always < large value that doesn't fit

			alloc = circuit_get_allocator(_circ)

			if _circ.arithmetic_mode == 1:  # Toffoli
				# split_toffoli_CQ_sub qubit layout:
				# [0..bits] = temp, [bits+1..2*bits+1] = target [a, msb], [2*(bits+1)] = carry
				borrow_ancilla = allocator_alloc(alloc, 1, True)
				toff_ancilla = allocator_alloc(alloc, self_bits + 2, True)

				# Build qubit array: temp register, target=[self, borrow], carry
				for i in range(self_bits + 1):
					qa[i] = toff_ancilla + i
				for i in range(self_bits):
					qa[self_bits + 1 + i] = self.qubits[self_offset + i]
				qa[self_bits + 1 + self_bits] = borrow_ancilla
				qa[2 * (self_bits + 1)] = toff_ancilla + self_bits + 1

				# Subtract
				seq = split_toffoli_CQ_sub(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				# Extract borrow
				result = qbool()
				qubit_array[0] = (<qint>result).qubits[63]
				qubit_array[1] = borrow_ancilla
				arr = qubit_array
				seq_add = Q_xor(1)
				run_instruction(seq_add, &arr[0], False, _circuit)

				# Restore via addition
				seq = split_toffoli_CQ_add(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				allocator_free(alloc, toff_ancilla, self_bits + 2)
				allocator_free(alloc, borrow_ancilla, 1)
			else:
				# QFT split-register: qubit layout [0..bits-1] = a, [bits] = msb
				borrow_ancilla = allocator_alloc(alloc, 1, True)

				for i in range(self_bits):
					qa[i] = self.qubits[self_offset + i]
				qa[self_bits] = borrow_ancilla

				# Subtract
				seq = split_CQ_sub(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				# Extract borrow
				result = qbool()
				qubit_array[0] = (<qint>result).qubits[63]
				qubit_array[1] = borrow_ancilla
				arr = qubit_array
				seq_add = Q_xor(1)
				run_instruction(seq_add, &arr[0], False, _circuit)

				# Restore via addition
				seq = split_CQ_add(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				allocator_free(alloc, borrow_ancilla, 1)

			# Track dependencies
			result.add_dependency(self)
			result.operation_type = 'LT'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operand references the result
			self.history.add_blocker(result)

			return result

		raise TypeError("Comparison requires qint or int")

	def __gt__(self, other):
		"""Greater-than comparison: self > other

		Uses borrow-ancilla pattern with split-register arithmetic.
		a > b is computed as b < a: subtract self from other's extended
		register and check the borrow bit.

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
		cdef int comp_width, i
		cdef sequence_t *seq
		cdef sequence_t *seq_add
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef circuit_s *_circ = <circuit_s*>_circuit
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef qubit_allocator_t *alloc
		cdef unsigned int borrow_ancilla, zero_ext, toff_ancilla
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int other_bits, other_offset

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(False)  # x > x is always false

		# Compile-mode: record "gt" IR entry with sequence pointers (Phase 11.5)
		# QFT mode only — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			alloc = circuit_get_allocator(_circ)
			if type(other) == int:
				# Classical overflow checks (must match non-compile path)
				max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
				if other < 0:
					return qbool(True)
				if other >= max_val:
					return qbool(False)
				result = qbool()
				# gt CQ: a > value, uses CQ_greater_than = CQ_less_than(value+1)
				_uc_seq = CQ_greater_than(self.bits, <int64_t>other)
				_cc_seq = cCQ_greater_than(self.bits, <int64_t>other)
				_gt_borrow = allocator_alloc(alloc, 1, True)
				regs = ((<qint>result).qubits[63],)
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self_bits))
				regs = regs + (_gt_borrow,)
				_record_instruction(
					"gt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _gt_borrow, 1)
				result.add_dependency(self)
				result.operation_type = 'GT'
				self.history.add_blocker(result)
				return result
			elif type(other) == qint:
				# gt QQ: a > b = b < a. Use QQ_less_than with swapped operands.
				# Qubit layout: [0]=result, [1.._comp_bits]=A(=other),
				# [_comp_bits+1..2*_comp_bits]=B(=self), [2*_comp_bits+1]=borrow,
				# [2*_comp_bits+2]=zero_ext
				other_bits = (<qint>other).bits
				other_offset = 64 - other_bits
				_comp_bits = self_bits if self_bits >= other_bits else other_bits
				_uc_seq = QQ_less_than(_comp_bits)
				_cc_seq = cQQ_less_than(_comp_bits)
				# Pad slots for shorter operand + borrow + zero_ext
				_other_pad = _comp_bits - other_bits
				_self_pad = _comp_bits - self_bits
				_gt_anc = allocator_alloc(alloc, 2 + _other_pad + _self_pad, True)
				result = qbool()
				# Swapped: A=other, B=self (since we want other < self)
				regs = ((<qint>result).qubits[63],)
				# A: other qubits padded to _comp_bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range(other_bits)
				)
				for _p in range(_other_pad):
					regs = regs + (_gt_anc + 2 + _p,)
				# B: self qubits padded to _comp_bits
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self_bits))
				for _p in range(_self_pad):
					regs = regs + (_gt_anc + 2 + _other_pad + _p,)
				regs = regs + (_gt_anc, _gt_anc + 1)
				_record_instruction(
					"gt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _gt_anc, 2 + _other_pad + _self_pad)
				result.add_dependency(self)
				result.add_dependency(other)
				result.operation_type = 'GT'
				self.history.add_blocker(result)
				(<qint>other).history.add_blocker(result)
				return result

		# Handle qint operand: a > b computed as b < a via borrow-ancilla
		if type(other) == qint:
			other_bits = (<qint>other).bits
			other_offset = 64 - other_bits
			comp_width = (self_bits if self_bits > other_bits else other_bits) + 1

			# Save history length so we can trim entries added by internal -= / +=
			_gt_hist_len = len((<qint>other).history)
			# 1. In-place mod-n subtraction: other -= self
			(<qint>other).__isub__(self)

			# 2. Allocate borrow ancilla + zero-extension ancilla
			alloc = circuit_get_allocator(_circ)
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					borrow_ancilla = allocator_alloc(alloc, 2, True)
					zero_ext = borrow_ancilla + 1
				else:
					borrow_ancilla = allocator_alloc(alloc, 3, True)
					zero_ext = borrow_ancilla + 1
					toff_ancilla = borrow_ancilla + 2
			else:
				borrow_ancilla = allocator_alloc(alloc, 2, True)
				zero_ext = borrow_ancilla + 1

			# 3. Build qubit array for (comp_width)-bit QQ addition
			#    After mod-n sub, other holds (other_orig - self) mod 2^n.
			#    Adding self back in (n+1)-bit: carry into borrow_ancilla
			#    iff other_orig < self (wrapping occurred), i.e. self > other.
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					qa[0] = borrow_ancilla
					qa[1] = zero_ext
				else:
					# toffoli_QQ_add(n>=2): [self_ext, other_ext, carry]
					for i in range(self_bits):
						qa[i] = self.qubits[self_offset + i]
					qa[self_bits] = zero_ext
					for i in range(other_bits):
						qa[comp_width + i] = (<qint>other).qubits[other_offset + i]
					qa[comp_width + other_bits] = borrow_ancilla
					qa[2 * comp_width] = toff_ancilla
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
			else:
				# QFT QQ_add(n): [target(n), other(n)]
				# target = [other_qubits..., borrow_ancilla]
				for i in range(other_bits):
					qa[i] = (<qint>other).qubits[other_offset + i]
				qa[other_bits] = borrow_ancilla
				# other_operand = [self_qubits..., zero_ext]
				for i in range(self_bits):
					qa[comp_width + i] = self.qubits[self_offset + i]
				qa[comp_width + self_bits] = zero_ext
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)

			# 4. Extract borrow into result qbool
			result = qbool()
			qubit_array[0] = (<qint>result).qubits[63]
			qubit_array[1] = borrow_ancilla
			arr = qubit_array
			seq_add = Q_xor(1)
			run_instruction(seq_add, &arr[0], False, _circuit)

			# 5. Undo the (n+1)-bit addition (inverse)
			if _circ.arithmetic_mode == 1:  # Toffoli
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)
			else:
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)

			# 6. Restore other: other += self
			(<qint>other).__iadd__(self)
			# Trim internal in-place history entries (Step 6.4 transparency)
			del (<qint>other).history.entries[_gt_hist_len:]

			# 7. Deallocate ancilla
			if _circ.arithmetic_mode == 1 and comp_width > 1:
				allocator_free(alloc, borrow_ancilla, 3)
			else:
				allocator_free(alloc, borrow_ancilla, 2)

			# Track dependencies on original operands
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'GT'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_other_offset_h = 64 - (<qint>other).bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operands reference the result
			self.history.add_blocker(result)
			(<qint>other).history.add_blocker(result)

			return result

		# Handle int operand: borrow-ancilla via split-register CQ subtraction
		# a > b (int) is equivalent to b < a, i.e., classical < quantum.
		# We compute self < (other+1) is wrong. Instead:
		# self > other iff NOT(self <= other) iff NOT(self < other+1) for int.
		# Simpler: self > other iff other < self. For CQ: subtract self_value
		# from other... but self is quantum. Use: self > other iff NOT(self <= other).
		# But <=  delegates to ~(self > other) creating recursion.
		# Direct approach: self > int_val iff self >= int_val + 1 iff NOT(self < int_val + 1).
		# Or: create temp qint and use QQ path.
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(True)  # qint always >= 0, so qint > negative is true
			if other >= max_val:
				return qbool(False)  # qint can't exceed max_val, so not >

			# self > other iff NOT(self < other + 1)
			# (since self and other are integers, self > other <=> self >= other+1 <=> NOT(self < other+1))
			return ~(self < (other + 1))

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
		Delegates to NOT(self < other) which uses borrow-ancilla pattern.
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
