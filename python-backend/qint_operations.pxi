# qint_operations.pxi - All qint operations and utility methods
# This file is included by quantum_language.pyx
# Do not import directly

# ====================================================================
# UTILITY AND TRACKING METHODS
# ====================================================================

	def add_dependency(self, parent):
		"""Register parent as dependency (weak reference).

		Parameters
		----------
		parent : qint
			Parent qint this value depends on.

		Raises
		------
		AssertionError
			If parent was created after self (cycle detection).
		"""
		if parent is None:
			return
		# Cycle prevention: parent must be older
		assert parent._creation_order < self._creation_order, \
			f"Cycle detected: dependency (order {parent._creation_order}) must be older than dependent (order {self._creation_order})"
		self.dependency_parents.append(weakref.ref(parent))

	def get_live_parents(self):
		"""Get list of parent dependencies that are still alive.

		Returns
		-------
		list
			List of parent qint objects (filtered for alive weakrefs).
		"""
		live = []
		for ref in self.dependency_parents:
			parent = ref()
			if parent is not None:
				live.append(parent)
		return live

	def _do_uncompute(self, bint from_del=False):
		"""Internal method to uncompute this qbool and cascade to dependencies.

		Called by __del__ (from_del=True) or explicit uncompute() (from_del=False).

		Parameters
		----------
		from_del : bool
			If True, suppress exceptions and only print warnings (Python __del__ best practice).
			If False, allow exceptions to propagate.
		"""
		global _circuit, _circuit_initialized
		cdef qubit_allocator_t *alloc

		# Idempotency check - already uncomputed
		if self._is_uncomputed:
			return

		# No allocated qubits means nothing to uncompute
		if not self.allocated_qubits:
			self._is_uncomputed = True
			return

		try:
			# 1. CASCADE: Get live parents and sort by creation order (descending = LIFO)
			live_parents = self.get_live_parents()
			# Sort by _creation_order descending for LIFO order
			live_parents.sort(key=lambda p: p._creation_order, reverse=True)

			# Recursively uncompute parents (they will cascade further if needed)
			for parent in live_parents:
				if not parent._is_uncomputed:
					parent._do_uncompute(from_del=from_del)

			# 2. REVERSE GATES: Only if there's a valid range
			if _circuit_initialized and self._end_layer > self._start_layer:
				reverse_circuit_range(_circuit, self._start_layer, self._end_layer)

			# 3. FREE QUBITS: Return to allocator
			if _circuit_initialized:
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					allocator_free(alloc, self.allocated_start, self.bits)

			# 4. Mark as uncomputed and clear ownership
			self._is_uncomputed = True
			self.allocated_qubits = False

		except Exception as e:
			if from_del:
				# Phase 18 decision: __del__ failures print warning only
				import sys
				print(f"Warning: Uncomputation failed: {e}", file=sys.stderr)
			else:
				raise

	def uncompute(self):
		"""Explicitly uncompute this qbool and its dependencies.

		Triggers uncomputation of this qbool and cascades through its
		dependency graph (intermediate qbools created during operations).

		Raises
		------
		ValueError
			If other references to this qbool still exist.

		Notes
		-----
		This method is idempotent: calling twice prints warning, not error.
		Not affected by .keep() flag - explicit uncompute always allowed.

		Examples
		--------
		>>> c = circuit()
		>>> a = qbool(True)
		>>> b = qbool(False)
		>>> result = a & b
		>>> result.uncompute()  # Explicit early cleanup
		>>> # result can no longer be used in operations
		"""
		import sys

		# Idempotent: repeated calls print warning
		if self._is_uncomputed:
			print("Warning: .uncompute() called on already-uncomputed qbool",
			      file=sys.stderr)
			return

		# Check reference count
		refcount = sys.getrefcount(self)
		if refcount > 2:  # self + getrefcount argument
			raise ValueError(
				f"Cannot uncompute: qbool still in use ({refcount - 1} references exist). "
				f"Delete other references first or let automatic cleanup handle it."
			)

		self._do_uncompute(from_del=False)

	def keep(self):
		"""Prevent automatic uncomputation in current scope.

		Marks this qbool to skip automatic cleanup when it goes out of
		scope or is garbage collected. Useful when you need a qbool to
		persist for later use, such as when returning from a function.

		Returns
		-------
		None

		Notes
		-----
		- Only affects automatic uncomputation (__del__)
		- Does not prevent explicit .uncompute() calls
		- Warning printed if called on already-uncomputed qbool

		Examples
		--------
		>>> result = a & b
		>>> result.keep()  # Don't auto-uncompute when scope exits
		>>> return result  # Can safely return
		"""
		if self._is_uncomputed:
			import sys
			print("Warning: .keep() called on already-uncomputed qbool",
			      file=sys.stderr)
			return

		self._keep_flag = True

	def _check_not_uncomputed(self):
		"""Raise if this qbool has been uncomputed.

		Called at the start of operations to prevent use-after-uncompute bugs.

		Raises
		------
		ValueError
			If qbool has been uncomputed.
		"""
		if self._is_uncomputed:
			raise ValueError(
				"Cannot use qbool: already uncomputed. "
				"Create a new qbool or call .keep() to prevent automatic cleanup."
			)

	def print_circuit(self):
		"""Print the current quantum circuit to stdout.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> a.print_circuit()
		"""
		print_circuit(_circuit)

	def __del__(self):
		"""Automatic uncomputation on garbage collection with mode awareness.

		When a qbool goes out of scope, automatically:
		1. Cascade uncomputation through dependencies (LIFO order)
		2. Reverse the gates that created this qbool
		3. Free the allocated qubits back to the pool

		Mode behavior:
		- EAGER mode (qubit_saving=True): Always uncompute immediately when GC runs.
		  This minimizes peak qubit count by freeing qubits as soon as possible.
		- LAZY mode (qubit_saving=False, default): Only uncompute when scope has exited.
		  This minimizes gate count by keeping intermediates alive longer (shared gates).

		Notes
		-----
		Follows Python best practice: exceptions in __del__ print warnings only.
		For deterministic cleanup, use explicit .uncompute() instead.
		"""
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits, _scope_stack

		# Existing Phase 18 checks (in _do_uncompute: _is_uncomputed, allocated_qubits)

		# Phase 20: Check .keep() flag (will be added in Plan 02)
		if hasattr(self, '_keep_flag') and self._keep_flag:
			return  # User opted out

		# Phase 20: Mode-based decision - EAGER vs LAZY have different behavior
		if self._uncompute_mode:
			# EAGER mode (qubit_saving=True): Always uncompute immediately when GC runs.
			# This minimizes peak qubit count by freeing qubits as soon as possible.
			self._do_uncompute(from_del=True)
		else:
			# LAZY mode (qubit_saving=False, default): Only uncompute when scope has exited.
			# This minimizes gate count by keeping intermediates alive longer (shared gates).
			# Use Phase 19's scope stack to check if we're still in the creation scope.
			current = current_scope_depth.get()
			if current <= self.creation_scope:
				# Scope has exited (depth decreased) - safe to uncompute
				self._do_uncompute(from_del=True)
			# else: Still in creation scope - defer uncomputation until scope exits
			# The qbool will be uncomputed later when its containing scope exits

		# Keep backward compat tracking (deprecated, but maintained for older code)
		if not self._is_uncomputed and self.bits > 0:
			_smallest_allocated_qubit -= self.bits
			ancilla -= self.bits

	def __str__(self):
		return f"{self.qubits}"

	# Context manager protocol
	def __enter__(self):
		"""Enter quantum conditional context.

		Enables conditional quantum operations controlled by this qint's value.

		Returns
		-------
		qint
			Self for use in with statement.

		Examples
		--------
		>>> flag = qbool(True)
		>>> result = qint(0, width=8)
		>>> with flag:
		...     result += 5  # Conditional addition

		Notes
		-----
		Creates controlled quantum gates where this qint acts as control.
		"""
		global _controlled, _control_bool, _scope_stack
		self._check_not_uncomputed()
		if not _controlled:
			_control_bool = self
		else:
			# TODO: and operation of self and qint._control_bool
			_list_of_controls.append(_control_bool)
			_control_bool &= self
			pass
		_controlled = True

		# Phase 19: Scope management - push new scope frame
		current_scope_depth.set(current_scope_depth.get() + 1)
		_scope_stack.append([])  # New empty scope frame

		return self

	def __exit__(self, exc__type, exc, tb):
		"""Exit quantum conditional context with scope cleanup.

		Parameters
		----------
		exc__type : type
			Exception type if raised.
		exc : Exception
			Exception instance if raised.
		tb : traceback
			Traceback if exception raised.

		Returns
		-------
		bool
			False (does not suppress exceptions).

		Examples
		--------
		>>> flag = qbool(True)
		>>> with flag:
		...     pass  # Controlled operations here
		"""
		global _controlled, _control_bool, ancilla, _smallest_allocated_qubit, _scope_stack

		# Phase 19: Uncompute scope-local qbools FIRST (while still controlled)
		# This ensures uncomputation gates are generated inside the controlled context
		if _scope_stack:
			scope_qbools = _scope_stack.pop()

			# Sort by _creation_order descending for LIFO (newest first)
			scope_qbools.sort(key=lambda q: q._creation_order, reverse=True)

			# Uncompute each qbool in scope (skip if already uncomputed)
			for qbool_obj in scope_qbools:
				if not qbool_obj._is_uncomputed:
					qbool_obj._do_uncompute(from_del=False)

		# Phase 19: Decrement scope depth
		current_scope_depth.set(current_scope_depth.get() - 1)

		# THEN restore control state (existing logic)
		_controlled = False
		_control_bool = None

		# undo logical and operations (TODO from original)
		return False  # do not suppress exceptions

	def measure(self):
		"""Measure quantum integer, collapsing to classical value.

		Returns
		-------
		int
			Measured classical value.

		Notes
		-----
		Measurement collapses quantum superposition to classical state.
		Currently returns initialization value (simulation placeholder).

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> result = a.measure()
		>>> result
		5
		"""
		return self.value

# ====================================================================
# ARITHMETIC OPERATIONS
# ====================================================================

# qint_arithmetic.pxi - Arithmetic operations for qint class
# This file is included by quantum_language.pyx
# Do not import directly

	cdef addition_inplace(self, other: qint | int, invert: int  = False):
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int other_bits
		cdef int self_offset
		cdef int other_offset

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
				qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
				qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
				seq = cCQ_add(self.bits, other)
			else:
				qubit_array[start: start + NUMANCILLY] = ancilla
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
			qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
			qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
			seq = cQQ_add(result_bits)
		else:
			qubit_array[start: start + NUMANCILLY] = ancilla
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
		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(value = self.value, width = result_width)
		a += other
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
		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(value = self.value, width = result_width)
		a += other
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
		# out of place subtraction - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(value = self.value, width = result_width)
		a -= other
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


	cdef multiplication_inplace(self, other: qint | int, ret: qint):
			global _controlled, _control_bool, qubit_array
			cdef sequence_t *seq
			cdef unsigned int[:] arr
			cdef int result_bits
			cdef int other_bits
			cdef int self_offset
			cdef int ret_offset
			cdef int other_offset

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
					qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
					qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
					seq = cCQ_mul(result_bits, other)  # Pass bits parameter
				else:
					qubit_array[start: start + NUMANCILLY] = ancilla
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
				qubit_array[start: start + 1] = (<qbool> _control_bool).qubits[63:64]
				qubit_array[start + 1: start + 1 + NUMANCILLY] = ancilla
				seq = cQQ_mul(result_bits)  # Pass bits parameter
			else:
				qubit_array[start: start + NUMANCILLY] = ancilla
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

		Args:
			other: qint or int to multiply by

		Returns:
			New qint containing product

		Examples:
			>>> a = qint(3, width=8)
			>>> b = qint(4, width=16)
			>>> c = a * b
			>>> c.width
			16
		"""
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

		return result

	def __rmul__(self, other):
		"""Reverse multiplication: other * self (for int * qint).

		Args:
			other: int to multiply by (qint * qint uses __mul__)

		Returns:
			New qint containing product

		Examples:
			>>> a = qint(5, width=8)
			>>> b = 3 * a  # Uses __rmul__
			>>> b.width
			8
		"""
		# For int * qint, result width is qint's width
		if type(other) == int:
			result_width = self.bits
		else:
			# qint * qint should use __mul__, not __rmul__
			result_width = max(self.bits, (<qint>other).bits)

		result = qint(width=result_width)
		self.multiplication_inplace(other, result)
		return result

	def __imul__(self, other):
		"""In-place multiplication: self *= other

		Note: Due to quantum mechanics, in-place multiplication allocates
		new qubits for the result and swaps qubit references.

		Args:
			other: qint or int to multiply by

		Returns:
			self (with swapped qubit references)

		Examples:
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
# qint_bitwise.pxi - Bitwise operations for qint class
# This file is included by quantum_language.pyx
# Do not import directly

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
		global _controlled, _control_bool, qubit_array, _circuit_initialized, _circuit
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef int start_layer

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
		elif type(other) == qint or type(other) == qbool:
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Allocate result (ancilla qubits)
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:  # Don't track classical operands
			result.add_dependency(other)
		result.operation_type = 'AND'

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_and expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		# Self qubits (zero-extended if smaller) - at position result_bits
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]

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
			qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]

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
		global _controlled, _control_bool, qubit_array, _circuit_initialized, _circuit
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef int start_layer

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
		elif type(other) == qint or type(other) == qbool:
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Allocate result (ancilla qubits)
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:
			result.add_dependency(other)
		result.operation_type = 'OR'

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_or expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		# Self qubits (zero-extended if smaller) - at position result_bits
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]

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
		global _controlled, _control_bool, qubit_array, _circuit_initialized, _circuit
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef int start_layer

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
		elif type(other) == qint or type(other) == qbool:
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

		# Q_xor expects: [0:bits] = target, [bits:2*bits] = source
		# XOR modifies target in-place: target ^= source
		# So we need to first copy self to result, then XOR other into result

		# Copy self qubits to result using CNOT pattern
		# For now, we do out-of-place: result = self, then result ^= other
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# First, copy self to result by XORing self into result (result starts at 0)
		# Copy self qubits into result: result ^= self (where result is 0, so result = self)
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]
		arr = qubit_array
		seq = Q_xor(self.bits)  # XOR self into result (copying self to result)
		run_instruction(seq, &arr[0], False, _circuit)

		# Now XOR other into result
		if type(other) == int:
			# Classical XOR: apply X gates where classical bits are 1
			# We don't have CQ_xor, so we'll apply X gates manually
			# Actually, Q_xor with a classical value is just applying X where bit=1
			# For now, we use a simple loop pattern via existing NOT functionality
			# This is a limitation - we don't have CQ_xor exposed
			# We can simulate: for each bit i where (other >> i) & 1, apply X to result[i]
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
			else:
				# Apply X gates for each 1 bit in the classical value
				# Note: We need to do this at Python level since CQ_xor is not exposed
				# For now, apply individual X gates through Q_not on single bits
				# This is inefficient but works
				for i in range(result_bits):
					if (other >> i) & 1:
						# Apply X to result bit i (from LSB)
						# result.qubits[63-i] is the i-th bit from LSB
						qubit_array[0] = result.qubits[64 - result_bits + (result_bits - 1 - i)]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)
		else:
			# Quantum-quantum XOR: result ^= other
			other_offset = 64 - (<qint>other).bits
			qubit_array[:result_bits] = result.qubits[result_offset:64]
			qubit_array[result_bits:result_bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]

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
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset, other_offset

		# XOR can be done truly in-place since target ^= source modifies target
		self_offset = 64 - self.bits

		if type(other) == int:
			# Classical XOR: apply X gates where classical bits are 1
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
			else:
				for i in range(self.bits):
					if (other >> i) & 1:
						# Apply X to self bit i (from LSB)
						qubit_array[0] = self.qubits[64 - self.bits + (self.bits - 1 - i)]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)
		elif type(other) == qint or type(other) == qbool:
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
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()

		# Use width-parameterized NOT for multi-bit qints
		self_offset = 64 - self.bits

		if _controlled:
			# Controlled NOT: [0:bits] = target, [bits] = control
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			qubit_array[self.bits] = (<qbool> _control_bool).qubits[63]
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
		bit_list = np.zeros(64)
		bit_list[-1] = self.qubits[item]
		a = qbool(create_new = False, bit_list = bit_list)
		return a
# qint_comparison.pxi - Comparison operations for qint class
# This file is included by quantum_language.pyx
# Do not import directly

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
		"""
		global _controlled, _control_bool, qubit_array, _circuit_initialized, _circuit
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset
		cdef int start
		cdef int start_layer

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Handle qint == qint case first (must come before int check)
		if type(other) == qint:
			# Self-comparison optimization: a == a is always True
			if self is other:
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

			# Capture layer boundaries
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

			return result

		# Handle qint == int case using C-level CQ_equal_width
		if type(other) == int:
			# Classical overflow check: if value doesn't fit in bits, not equal
			# For unsigned interpretation: value must be in [0, 2^bits - 1]
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0 or other > max_val:
				# Overflow: value outside range - definitely not equal
				# Return qbool initialized to |0> (False)
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
				return qbool(False)

			# Allocate result qbool
			result = qbool()

			# Build qubit array: [0] = result, [1:bits+1] = operand
			# Result qubit (from qbool, stored at index 63 in right-aligned storage)
			qubit_array[0] = (<qbool>result).qubits[63]

			# Self operand qubits (right-aligned)
			self_offset = 64 - self.bits
			for i in range(self.bits):
				qubit_array[1 + i] = self.qubits[self_offset + i]

			start = 1 + self.bits

			# Add control qubit if controlled context
			if _controlled:
				qubit_array[start] = (<qbool>_control_bool).qubits[63]

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)

			# Note: seq is caller-owned per comparison_ops.h, but we don't have
			# a free_sequence binding exposed. This is consistent with existing
			# codebase patterns where sequences are not explicitly freed.

			# Track dependency on compared qint (classical doesn't need tracking)
			result.add_dependency(self)
			result.operation_type = 'EQ'

			# Capture layer boundaries
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

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

		Uses in-place subtraction and sign bit check. Preserves inputs.

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
		Computes self - other in-place, checks MSB (sign bit), then restores self.
		Phase 14: Refactored to use in-place subtract-add-back pattern without temporary qint allocation.
		"""
		global _circuit_initialized, _circuit
		cdef int start_layer

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Self-comparison optimization
		if self is other:
			return qbool(False)  # x < x is always false

		# Handle qint operand
		if type(other) == qint:
			# In-place subtraction on self
			self -= other
			# Check MSB (sign bit) - if 1, result is negative (self < other)
			msb = self[64 - self.bits]
			result = qbool()
			result ^= msb  # Copy MSB to result
			# Restore operand
			self += other
			# Track dependencies
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'LT'
			# Capture layer boundaries
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
			return result

		# Handle int operand
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(False)  # qint always >= 0, so qint < negative is false
			if other > max_val:
				return qbool(True)  # qint always < large value that doesn't fit

			# In-place subtraction with classical value
			self -= other
			msb = self[64 - self.bits]
			result = qbool()
			result ^= msb
			# Restore operand
			self += other
			# Track dependency on qint
			result.add_dependency(self)
			result.operation_type = 'LT'
			# Capture layer boundaries
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
			return result

		raise TypeError("Comparison requires qint or int")

	def __gt__(self, other):
		"""Greater-than comparison: self > other

		Uses in-place subtraction on other operand or delegates to <= for ints.

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

		Notes
		-----
		Phase 14: Refactored to use in-place pattern for qint operands.
		For int operands, uses NOT(self <= other) for efficiency.
		"""
		global _circuit_initialized, _circuit
		cdef int start_layer

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Self-comparison optimization
		if self is other:
			return qbool(False)  # x > x is always false

		# Handle qint operand
		if type(other) == qint:
			# a > b means (b - a) is negative
			# Subtract self from other (in-place on other, then restore)
			other -= self
			msb = other[64 - (<qint>other).bits]
			result = qbool()
			result ^= msb
			# Restore operand
			other += self
			# Track dependencies
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'GT'
			# Capture layer boundaries
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
			return result

		# Handle int operand
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(True)  # qint always >= 0, so qint > negative is true
			if other > max_val:
				return qbool(False)  # qint always < large value, so not >

			# For int: a > b is NOT(a <= b)
			return ~(self <= other)

		raise TypeError("Comparison requires qint or int")

	def __le__(self, other):
		"""Less-than-or-equal comparison: self <= other

		Uses in-place subtraction to check if result is negative or zero.

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
		Phase 14: Refactored to use in-place subtract-add-back pattern.
		a <= b means (a - b) is negative OR zero.
		"""
		global _circuit_initialized, _circuit
		cdef int start_layer

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Capture start layer
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Self-comparison optimization
		if self is other:
			return qbool(True)  # x <= x is always true

		# Handle qint operand
		if type(other) == qint:
			self -= other
			# Check MSB (negative)
			is_negative = self[64 - self.bits]
			# Check zero using Phase 13 pattern
			is_zero = (self == 0)
			# OR combination: result = is_negative | is_zero
			result = qbool()
			result ^= is_negative
			temp_zero = qbool()
			temp_zero ^= is_zero
			result |= temp_zero
			# Restore operand
			self += other
			# Track dependencies
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'LE'
			# Capture layer boundaries
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
			return result

		# Handle int operand
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(False)  # qint >= 0, so qint <= negative is false
			if other > max_val:
				return qbool(True)  # qint always <= large value

			self -= other
			is_negative = self[64 - self.bits]
			is_zero = (self == 0)
			result = qbool()
			result ^= is_negative
			temp_zero = qbool()
			temp_zero ^= is_zero
			result |= temp_zero
			# Restore operand
			self += other
			# Track dependency on qint
			result.add_dependency(self)
			result.operation_type = 'LE'
			# Capture layer boundaries
			result._start_layer = start_layer
			result._end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
			return result

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
		Phase 14: Added self-comparison optimization.
		Delegates to NOT(self < other) which uses in-place pattern.
		"""
		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(True)  # x >= x is always true
		# self >= other is equivalent to NOT (self < other)
		return ~(self < other)

# qint_division.pxi - Division operations for qint class
# This file is included by quantum_language.pyx
# Do not import directly

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

			# Special case: power of 2 division (just right shift)
			# For Phase 7, use general algorithm - optimization later

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

			return quotient

		elif type(divisor) == qint:
			# Quantum divisor - delegate to quantum division method
			return self._floordiv_quantum(divisor)
		else:
			raise TypeError("Divisor must be int or qint")

	def _floordiv_quantum(self, divisor: qint):
		"""Floor division with quantum divisor: self // divisor

		Uses repeated quantum comparison and conditional subtraction.
		Per arXiv:1809.09732, implements restoring division algorithm.

		Args:
			divisor: qint divisor

		Returns:
			qint quotient

		Note:
			For quantum divisor, we cannot use bit-level algorithm
			(shifting quantum values is expensive). Instead, we use
			repeated subtraction: while remainder >= divisor, subtract.
			This creates a circuit with O(quotient) iterations.
		"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		# Allocate quotient and remainder
		quotient = qint(0, width=comp_bits)
		remainder = qint(0, width=comp_bits)

		# Copy self to remainder via XOR (remainder starts at 0)
		remainder ^= self

		# Repeated conditional subtraction
		# Maximum possible quotient is 2^comp_bits - 1
		# We need to iterate enough times to complete division
		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			# Check if remainder >= divisor
			can_subtract = remainder >= divisor

			# Conditional subtraction and increment
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
		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Modulo by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			# Allocate remainder
			remainder = qint(0, width=self.bits)

			# Copy self to remainder via XOR (remainder starts at 0)
			remainder ^= self

			# Efficient modulo: just compute remainder, no quotient needed
			# Use same restoring division but only track remainder
			for bit_pos in range(self.bits - 1, -1, -1):
				trial_value = divisor << bit_pos

				# Check if remainder >= trial_value
				can_subtract = remainder >= trial_value

				# Conditional subtraction (no quotient tracking)
				with can_subtract:
					remainder -= trial_value

			return remainder

		elif type(divisor) == qint:
			# Quantum divisor - use quantum modulo
			return self._mod_quantum(divisor)
		else:
			raise TypeError("Divisor must be int or qint")

	def _mod_quantum(self, divisor: qint):
		"""Modulo with quantum divisor: self % divisor

		Args:
			divisor: qint divisor

		Returns:
			qint remainder
		"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		# Allocate remainder
		remainder = qint(0, width=comp_bits)

		# Copy self to remainder via XOR
		remainder ^= self

		# Repeated conditional subtraction (same as division but no quotient)
		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			# Check if remainder >= divisor
			can_subtract = remainder >= divisor

			# Conditional subtraction
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
		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Divmod by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			# Allocate quotient and remainder
			quotient = qint(0, width=self.bits)
			remainder = qint(0, width=self.bits)

			# Copy self to remainder via XOR
			remainder ^= self

			# Restoring division: compute both quotient and remainder
			for bit_pos in range(self.bits - 1, -1, -1):
				trial_value = divisor << bit_pos

				# Check if remainder >= trial_value
				can_subtract = remainder >= trial_value

				# Conditional subtraction and quotient bit set
				with can_subtract:
					remainder -= trial_value
					quotient += (1 << bit_pos)

			return (quotient, remainder)

		elif type(divisor) == qint:
			# Quantum divisor - compute both
			return self._divmod_quantum(divisor)
		else:
			raise TypeError("Divisor must be int or qint")

	def _divmod_quantum(self, divisor: qint):
		"""Divmod with quantum divisor: divmod(self, divisor)

		Args:
			divisor: qint divisor

		Returns:
			tuple (quotient, remainder) where both are qint
		"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		# Allocate quotient and remainder
		quotient = qint(0, width=comp_bits)
		remainder = qint(0, width=comp_bits)

		# Copy self to remainder via XOR
		remainder ^= self

		# Repeated conditional subtraction (compute both quotient and remainder)
		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			# Check if remainder >= divisor
			can_subtract = remainder >= divisor

			# Conditional subtraction and increment
			with can_subtract:
				remainder -= divisor
				quotient += 1

		return (quotient, remainder)

	def __rfloordiv__(self, other):
		"""Reverse floor division: other // self

		Parameters
		----------
		other : int
			Dividend (numerator).

		Returns
		-------
		qint
			Quotient.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> q = 17 // a
		>>> # q represents |3>
		"""
		# Convert int to qint and perform division
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint // self
		else:
			# For qint // qint, __floordiv__ should be called, not __rfloordiv__
			raise TypeError("Reverse floor division requires int divisor")

	def __rmod__(self, other):
		"""Reverse modulo: other % self

		Parameters
		----------
		other : int
			Dividend (numerator).

		Returns
		-------
		qint
			Remainder.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> r = 17 % a
		>>> # r represents |2>
		"""
		# Convert int to qint and perform modulo
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint % self
		else:
			# For qint % qint, __mod__ should be called, not __rmod__
			raise TypeError("Reverse modulo requires int divisor")

	def __rdivmod__(self, other):
		"""Reverse divmod: divmod(other, self)

		Parameters
		----------
		other : int
			Dividend (numerator).

		Returns
		-------
		tuple of qint
			(quotient, remainder).

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> q, r = divmod(17, a)
		>>> # q represents |3>, r represents |2>
		"""
		# Convert int to qint and perform divmod
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return divmod(other_qint, self)
		else:
			# For qint divmod qint, __divmod__ should be called
			raise TypeError("Reverse divmod requires int divisor")

