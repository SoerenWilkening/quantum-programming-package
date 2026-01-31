# ====================================================================
# COMPARISON OPERATIONS (Cython include file for qint class)
# ====================================================================
# This file is included into qint.pyx via "include" directive.
# Do NOT add imports, cdef class declarations, or standalone code.
# Methods are indented at class level (one tab).

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
	"""
	from quantum_language.qbool import qbool
	cdef sequence_t *seq
	cdef unsigned int[:] arr
	cdef int self_offset
	cdef int start
	cdef int start_layer
	cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
	cdef bint _circuit_initialized = _get_circuit_initialized()
	cdef bint _controlled = _get_controlled()
	cdef object _control_bool = _get_control_bool()

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
		qubit_array[0] = (<qint>result).qubits[63]

		# Self operand qubits (right-aligned)
		self_offset = 64 - self.bits
		for i in range(self.bits):
			qubit_array[1 + i] = self.qubits[self_offset + i]

		start = 1 + self.bits

		# Add control qubit if controlled context
		if _controlled:
			qubit_array[start] = (<qint>_control_bool).qubits[63]

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
	from quantum_language.qbool import qbool
	cdef int start_layer
	cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
	cdef bint _circuit_initialized = _get_circuit_initialized()

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
	from quantum_language.qbool import qbool
	cdef int start_layer
	cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
	cdef bint _circuit_initialized = _get_circuit_initialized()

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
	from quantum_language.qbool import qbool
	cdef int start_layer
	cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
	cdef bint _circuit_initialized = _get_circuit_initialized()

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
	from quantum_language.qbool import qbool

	# Phase 18: Check for use-after-uncompute
	self._check_not_uncomputed()
	if isinstance(other, qint):
		(<qint>other)._check_not_uncomputed()

	# Self-comparison optimization
	if self is other:
		return qbool(True)  # x >= x is always true
	# self >= other is equivalent to NOT (self < other)
	return ~(self < other)
