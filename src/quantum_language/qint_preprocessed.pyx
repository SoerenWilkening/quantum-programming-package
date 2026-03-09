# NOTE: This file is intentionally large (~2800 lines). Cython cdef classes
# cannot be split across files (no include/mixin support in cdef class bodies).
# See .planning/quick/004-consolidate-qint-pxi-includes-to-remove-/004-SUMMARY.md
"""Quantum integer type with arithmetic, bitwise, and comparison operations."""

cimport cython
from libc.stdint cimport int64_t

import sys
import warnings

import numpy as np

# C-level imports for type declarations
from ._core cimport (
    circuit, circuit_t, circuit_s, sequence_t,
    INTEGERSIZE, NUMANCILLY,
    init_circuit, Q_not, run_instruction,
    circuit_get_allocator, allocator_alloc, allocator_free,
    reverse_circuit_range,
    qubit_allocator_t,
    CQ_add, QQ_add, cCQ_add, cQQ_add,
    CQ_mul, QQ_mul, cCQ_mul, cQQ_mul,
    Q_and, CQ_and, Q_or, CQ_or, Q_xor,
    cQ_not,
    CQ_equal_width, cCQ_equal_width,
    print_circuit as c_print_circuit,
    hot_path_mul_qq, hot_path_mul_cq,
    hot_path_add_qq, hot_path_add_cq,
    hot_path_ixor_qq, hot_path_ixor_cq,
    toffoli_divmod_cq, toffoli_divmod_qq,
)

# Python-level imports for global state access via accessor functions
from ._core import (
    _get_circuit, _get_circuit_initialized, _set_circuit_initialized,
    _get_num_qubits, _set_num_qubits,
    _get_int_counter, _set_int_counter, _increment_int_counter,
    _get_controlled, _set_controlled,
    _get_control_bool, _set_control_bool,
    _get_list_of_controls, _set_list_of_controls,
    _push_control, _pop_control,
    _get_smallest_allocated_qubit, _set_smallest_allocated_qubit,
    _get_qubit_saving_mode, _set_qubit_saving_mode,
    _get_global_creation_counter, _increment_global_creation_counter,
    _get_scope_stack,
    _get_ancilla, _increment_ancilla, _decrement_ancilla,
    qubit_array,
    current_scope_depth,
    validate_circuit, validate_qubit_slots,
    _mark_arithmetic_performed,
)


import math
from ._gates import emit_p, emit_p_raw, _toffoli_and, _uncompute_toffoli_and
from ._core import _get_control_stack


cpdef void _set_layer_floor_to_used():
	"""Set circuit layer_floor to used_layer (force next gate into new layer).

	This ensures the next gate added via add_gate() is placed in a new layer
	at or after used_layer, preventing the optimizer from sharing a layer with
	preceding gates. Used by _PhaseProxy.__iadd__ to keep the P gate outside
	the comparison's layer range during phase kickback.
	"""
	cdef circuit_t *_circuit
	cdef bint _circuit_initialized = _get_circuit_initialized()
	if _circuit_initialized:
		_circuit = <circuit_t*><unsigned long long>_get_circuit()
		(<circuit_s*>_circuit).layer_floor = (<circuit_s*>_circuit).used_layer

cpdef void _restore_layer_floor(unsigned int floor):
	"""Restore layer_floor to a saved value."""
	cdef circuit_t *_circuit
	cdef bint _circuit_initialized = _get_circuit_initialized()
	if _circuit_initialized:
		_circuit = <circuit_t*><unsigned long long>_get_circuit()
		(<circuit_s*>_circuit).layer_floor = floor

cpdef unsigned int _get_layer_floor():
	"""Get current layer_floor value."""
	cdef circuit_t *_circuit
	cdef bint _circuit_initialized = _get_circuit_initialized()
	if _circuit_initialized:
		_circuit = <circuit_t*><unsigned long long>_get_circuit()
		return (<circuit_s*>_circuit).layer_floor
	return 0


class _PhaseProxy:
	"""Proxy object returned by qint.phase / qarray.phase property.

	Supports += theta (phase shift) and *= -1 (phase flip).
	When uncontrolled: emits no gate (global phase is unobservable).
	When controlled (inside `with` block): emits CP(theta) on the control qubit.
	"""
	__slots__ = ('_owner',)

	def __init__(self, owner):
		self._owner = owner

	def __iadd__(self, theta):
		if _get_controlled():
			ctrl = _get_control_bool()
			# Use emit_p_raw to avoid double-control: emit_p would check
			# _get_controlled() again and wrap with CP, producing
			# cp(ctrl, ctrl) -- a self-controlled gate with no search
			# register effect. Instead, emit P directly on the control
			# qubit. P(theta) on a qubit in |1> adds phase e^{i*theta}
			# to all basis states where that qubit is |1>, which is
			# exactly the controlled global phase we want.
			#
			# Set layer_floor to used_layer before emitting P to force it
			# into a NEW layer after the comparison gates. Without this,
			# the optimizer may share a layer with comparison gates,
			# causing the P gate to be inside the comparison's
			# [_start_layer, _end_layer) range and incorrectly reversed
			# during uncomputation.
			saved_floor = _get_layer_floor()
			_set_layer_floor_to_used()
			emit_p_raw(ctrl.qubits[63], theta)
			_restore_layer_floor(saved_floor)
		# Uncontrolled: no gate (global phase is unobservable)
		return self

	def __imul__(self, factor):
		if factor == -1:
			return self.__iadd__(math.pi)
		raise ValueError("phase *= only supports -1")


cdef class qint(circuit):
	"""Quantum integer with arithmetic, bitwise, and comparison operations.

	A quantum integer represents an integer value in quantum superposition,
	encoded in computational basis using qubits. Supports standard arithmetic
	and bitwise operations that compile to quantum circuits.

	Parameters
	----------
	value : int, optional
		Initial value (default 0). Encoded into quantum state |value>.
	width : int, optional
		Bit width (1-64, default 8). Determines range: [-2^(w-1), 2^(w-1)-1].
		If None and value != 0, auto-determines width from value (unsigned mode).
	bits : int, optional
		Alias for width (backward compatibility).
	classical : bool, optional
		Whether this is a classical integer (default False).
	create_new : bool, optional
		Whether to allocate new qubits (default True).
	bit_list : array-like, optional
		External qubit list (when create_new=False).

	Attributes
	----------
	width : int
		Bit width (read-only property).

	Examples
	--------
	>>> a = qint(5)           # Auto-width (3-bit) quantum integer, value 5
	>>> b = qint(5, width=16) # 16-bit quantum integer, value 5
	>>> c = a + b             # Quantum addition
	>>> d = a & b             # Quantum AND
	>>> flag = (a == 5)       # Quantum comparison (returns qbool)

	Notes
	-----
	Creates quantum state |value> using computational basis encoding.
	Auto-width mode uses unsigned representation (minimum bits for magnitude).
	All operations preserve quantum coherence and support superposition.
	"""
	# Attribute declarations are in qint.pxd

	def __init__(self, value = 0, width = None, bits = None, classical = False, create_new = True, bit_list = None):
		"""Create a quantum integer.

		Allocates qubits and initializes to specified value in superposition.

		Parameters
		----------
		value : int, optional
			Initial value (default 0). Encoded into quantum state |value>.
		width : int, optional
			Bit width (1-64, default 8). Determines range: [-2^(w-1), 2^(w-1)-1].
			If None and value != 0, auto-determines width from value (unsigned mode).
		bits : int, optional
			Alias for width (backward compatibility).
		classical : bool, optional
			Whether this is a classical integer (default False).
		create_new : bool, optional
			Whether to allocate new qubits (default True).
		bit_list : array-like, optional
			External qubit list (when create_new=False).

		Raises
		------
		ValueError
			If width < 1 or width > 64.
		UserWarning
			If value exceeds width range (modular arithmetic applies).

		Examples
		--------
		>>> a = qint(5)           # Auto-width (3-bit) quantum integer, value 5
		>>> b = qint(5, width=16) # 16-bit quantum integer, value 5
		>>> c = qint(5, bits=16)  # Backward compatible alias
		>>> d = qint(0)           # Default 8-bit quantum integer, value 0

		Notes
		-----
		Creates quantum state |value> using computational basis encoding.
		Auto-width mode uses unsigned representation (minimum bits for magnitude).
		"""
		cdef qubit_allocator_t *alloc
		cdef unsigned int start
		cdef int actual_width
		cdef unsigned int[:] arr
		cdef sequence_t *seq
		cdef int bit_pos, qubit_idx
		cdef long long masked_value
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		super().__init__()

		# Handle int-like values (objects with __int__ method)
		if hasattr(value, '__int__'):
			value = int(value)

		# Handle width/bits parameter with auto-width support
		if width is None and bits is None:
			# Auto-width mode: determine width from value
			if value == 0:
				actual_width = INTEGERSIZE  # Default 8 bits for zero
			elif value > 0:
				# Positive: unsigned bit count (no sign bit)
				actual_width = value.bit_length()
			else:
				# Negative: two's complement formula
				# -1 needs 1 bit, other negatives depend on magnitude
				if value == -1:
					actual_width = 1
				else:
					mag = -value
					# If magnitude is power of 2, use mag.bit_length() bits
					# Otherwise use mag.bit_length() + 1 bits
					if (mag & (mag - 1)) == 0:  # Power of 2 check
						actual_width = mag.bit_length()
					else:
						actual_width = mag.bit_length() + 1
		elif width is not None:
			actual_width = width
		else:
			actual_width = bits  # Backward compatibility

		# Width validation
		if actual_width < 1 or actual_width > 64:
			raise ValueError(f"Width must be 1-64, got {actual_width}")

		if create_new:
			self.counter = _increment_int_counter()
			self.bits = actual_width
			self.value = value

			# Warn if value exceeds width (two's complement range)
			# Only warn when width was explicitly specified (not auto-width mode)
			# Note: For 1-bit (qbool), treat as unsigned [0,1] for clarity
			if value != 0 and (width is not None or bits is not None):
				if actual_width == 1:
					# Single bit: unsigned range [0, 1]
					max_value = 1
					min_value = 0
				else:
					# Multi-bit: signed range
					max_value = (1 << (actual_width - 1)) - 1
					min_value = -(1 << (actual_width - 1))
				if value > max_value or value < min_value:
					warnings.warn(
						f"Value {value} exceeds {actual_width}-bit range [{min_value}, {max_value}]. "
						f"Value will truncate (modular arithmetic).",
						UserWarning
					)

			_set_num_qubits(_get_num_qubits() + actual_width)

			self.qubits = np.ndarray(64, dtype = np.uint32)  # Max width support

			# NEW: Allocate qubits through circuit's allocator
			alloc = circuit_get_allocator(<circuit_s*>_circuit)
			if alloc == NULL:
				raise RuntimeError("Circuit allocator not initialized")

			start = allocator_alloc(alloc, actual_width, True)  # is_ancilla=True
			if start == <unsigned int>-1:
				raise MemoryError("Qubit allocation failed - limit exceeded")

			# Ensure circuit tracks all allocated qubits for QASM export
			# Without this, qubits with no gates (e.g., CQ AND where classical bit=0)
			# won't appear in the exported circuit
			if start + actual_width - 1 > (<circuit_s*>_circuit).used_qubits:
				(<circuit_s*>_circuit).used_qubits = start + actual_width - 1

			# Right-aligned qubit storage: indices [64-width] through [63]
			for i in range(actual_width):
				self.qubits[64 - actual_width + i] = start + i

			self.allocated_start = start  # Track for deallocation
			self.allocated_qubits = True

			# Phase 16: Initialize dependency tracking
			self._creation_order = _increment_global_creation_counter()
			self.dependency_parents = []
			self.operation_type = None
			self.creation_scope = current_scope_depth.get()
			# Capture control context
			_control_bool = _get_control_bool()
			if _control_bool is not None:
				self.control_context = [(<qint>_control_bool).qubits[63]]
			else:
				self.control_context = []

			# Phase 19: Register with active scope if inside a with block
			_scope_stack = _get_scope_stack()
			if _scope_stack and self.creation_scope == current_scope_depth.get() and current_scope_depth.get() > 0:
				_scope_stack[-1].append(self)

			# Phase 18: Initialize uncomputation tracking
			self._is_uncomputed = False
			self._start_layer = 0
			self._end_layer = 0

			# Phase 20: Capture uncomputation mode at creation
			self._uncompute_mode = _get_qubit_saving_mode()
			self._keep_flag = False

			# Apply X gates based on binary representation of value
			# Phase 15: Classical initialization via X gate application
			if value != 0:
				# Mask value to width (handles both positive and negative via two's complement)
				masked_value = value & ((1 << actual_width) - 1)

				# Apply X gate for each 1 bit
				for bit_pos in range(actual_width):
					if (masked_value >> bit_pos) & 1:
						# Qubit index for bit_pos (right-aligned storage)
						# Bit 0 (LSB) is at qubits[64-width], bit (width-1) is at qubits[63]
						qubit_idx = 64 - actual_width + bit_pos
						qubit_array[0] = self.qubits[qubit_idx]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)

			# Keep backward compat tracking (deprecated, remove later)
			# Note: _smallest_allocated_qubit and ancilla numpy array still updated
			# for any code that might still use them
			_set_smallest_allocated_qubit(_get_smallest_allocated_qubit() + actual_width)
			_increment_ancilla(actual_width)
		else:
			self.bits = actual_width
			self.qubits = bit_list
			self.allocated_qubits = False

			# Phase 16: Initialize dependency tracking for bit_list path
			self._creation_order = _increment_global_creation_counter()
			self.dependency_parents = []
			self.operation_type = None
			self.creation_scope = current_scope_depth.get()
			# Capture control context
			_control_bool = _get_control_bool()
			if _control_bool is not None:
				self.control_context = [(<qint>_control_bool).qubits[63]]
			else:
				self.control_context = []

			# Phase 19: Register with active scope if inside a with block
			_scope_stack = _get_scope_stack()
			if _scope_stack and self.creation_scope == current_scope_depth.get() and current_scope_depth.get() > 0:
				_scope_stack[-1].append(self)

			# Phase 18: Initialize uncomputation tracking
			self._is_uncomputed = False
			self._start_layer = 0
			self._end_layer = 0

			# Phase 20: Capture uncomputation mode at creation
			self._uncompute_mode = _get_qubit_saving_mode()
			self._keep_flag = False

	@property
	def width(self):
		"""Get the bit width of this quantum integer (read-only).

		Returns
		-------
		int
			Bit width (1-64).

		Examples
		--------
		>>> a = qint(5, width=16)
		>>> a.width
		16
		"""
		return self.bits

	@property
	def phase(self):
		"""Get a phase proxy for controlled global phase operations.

		Returns a proxy object supporting ``x.phase += theta`` and
		``x.phase *= -1``.

		When uncontrolled: emits no gate (global phase is unobservable).
		When controlled (inside ``with`` block): emits CP(theta) on the
		control qubit.

		Returns
		-------
		_PhaseProxy
			Phase proxy object.

		Examples
		--------
		>>> with flag:
		...     x.phase += math.pi  # CP(pi) on control qubit
		>>> x.phase *= -1  # Equivalent to x.phase += pi
		"""
		return _PhaseProxy(self)

	@phase.setter
	def phase(self, value):
		# No-op setter: absorbs re-assignment from x.phase += theta
		# (Python desugars += to x.phase = x.phase.__iadd__(theta))
		pass

	# ====================================================================
	# UTILITY AND TRACKING METHODS
	# ====================================================================

	def add_dependency(self, parent):
		"""Register parent as dependency (strong reference).

		Strong references ensure parents stay alive until this object is
		uncomputed, preventing premature garbage collection of intermediates
		in expression chains like ``(arr == 1).all()``.

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
		self.dependency_parents.append(parent)

	def get_live_parents(self):
		"""Get list of parent dependencies that are still alive.

		Returns
		-------
		list
			List of parent qint objects.
		"""
		return [p for p in self.dependency_parents if not p._is_uncomputed]

	def _do_uncompute(self, bint from_del=False):
		"""Internal method to uncompute this qbool and cascade to dependencies.

		Called by __del__ (from_del=True) or explicit uncompute() (from_del=False).

		Parameters
		----------
		from_del : bool
			If True, suppress exceptions and only print warnings (Python __del__ best practice).
			If False, allow exceptions to propagate.
		"""
		cdef qubit_allocator_t *alloc
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		# Idempotency check - already uncomputed
		if self._is_uncomputed:
			return

		# No allocated qubits means nothing to uncompute
		if not self.allocated_qubits:
			self._is_uncomputed = True
			return

		try:
			# 1. REVERSE GATES: Undo this operation first, while inputs still exist.
			# Must happen before cascading to parents — our gates reference parent qubits.
			if _circuit_initialized and self._end_layer > self._start_layer:
				reverse_circuit_range(_circuit, self._start_layer, self._end_layer)

			# 2. CASCADE: Get live parents and sort by creation order (descending = LIFO)
			live_parents = self.get_live_parents()
			live_parents.sort(key=lambda p: p._creation_order, reverse=True)

			# Recursively uncompute parents that are intermediates (have operation_type).
			# Skip user-created variables (operation_type is None) — they must not
			# be destroyed by cascade uncomputation of expressions that use them.
			for parent in live_parents:
				if not parent._is_uncomputed and parent.operation_type is not None:
					parent._do_uncompute(from_del=from_del)

			# 3. FREE QUBITS: Return to allocator
			if _circuit_initialized:
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					allocator_free(alloc, self.allocated_start, self.bits)

			# 4. Mark as uncomputed, clear ownership and release parent refs
			self._is_uncomputed = True
			self.allocated_qubits = False
			self.dependency_parents = []

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

		# NOTE: Deliberately NOT checking _keep_flag here.
		# Design: .keep() only affects automatic uncomputation in __del__.
		# Explicit .uncompute() always allowed (gives user full control).

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

	cpdef branch(self, double prob=0.5):
		"""Apply Ry rotation to create superposition.

		Creates quantum superposition by applying Ry(theta) rotation to all
		qubits in this qint. The angle theta is computed from the desired
		probability of measuring |1>:

		    theta = 2 * arcsin(sqrt(probability))

		Parameters
		----------
		prob : float, optional
		    Probability of |1> state (default 0.5 for equal superposition).
		    Must be in range [0, 1].

		Returns
		-------
		None
		    Mutates self; does not return new qint.

		Raises
		------
		ValueError
		    If prob is outside [0, 1] range.

		Examples
		--------
		>>> x = qint(0, width=4)
		>>> x.branch()        # Equal superposition on all 4 qubits
		>>> x[0].branch(0.3)  # 30% probability on LSB only

		Notes
		-----
		- Calling branch() multiple times accumulates rotations
		- Works inside `with qbool:` blocks (emits CRy gates)
		- Supports uncomputation via scope exit (inverse is Ry(-theta))
		"""
		cdef circuit_t *_circuit
		cdef bint _circuit_initialized
		cdef int self_offset
		cdef int i
		cdef double theta
		cdef int start_layer

		import math

		# Validate probability range (per user decision)
		if not 0.0 <= prob <= 1.0:
			raise ValueError(f"Probability must be in [0, 1], got {prob}")

		# Check not uncomputed (existing pattern)
		self._check_not_uncomputed()

		# Convert probability to Ry angle
		# For Ry(theta) on |0>: P(|1>) = sin^2(theta/2) = prob
		# Therefore: theta = 2 * arcsin(sqrt(prob))
		theta = 2.0 * math.asin(math.sqrt(prob))

		# Import emit_ry from _gates module
		from quantum_language._gates import emit_ry

		# Get circuit for layer tracking
		_circuit = <circuit_t*><unsigned long long>_get_circuit()
		_circuit_initialized = _get_circuit_initialized()

		# Capture start layer for uncomputation
		start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0

		# Apply Ry to each qubit (right-aligned storage)
		self_offset = 64 - self.bits
		for i in range(self.bits):
			emit_ry(self.qubits[self_offset + i], theta)

		# Capture end layer for uncomputation support
		# Accumulate range across multiple branch() calls so _do_uncompute()
		# reverses ALL rotation gates, not just the last call.
		end_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0
		if self._start_layer == 0 and self._end_layer == 0:
			# First branch() call on this qint
			self._start_layer = start_layer
			self._end_layer = end_layer
		else:
			# Subsequent calls: expand tracked range
			self._start_layer = min(self._start_layer, start_layer)
			self._end_layer = max(self._end_layer, end_layer)

		# Return None per user decision (mutation, no chaining)
		return None

	def print_circuit(self):
		"""Print the current quantum circuit to stdout.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> a.print_circuit()
		"""
		cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
		c_print_circuit(circ)

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
		# Phase 20: Check .keep() flag
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
			# Phase 41: Use strict < instead of <= so that scope-0 qints (top-level)
			# don't auto-uncompute on GC. Only qints created inside with-blocks
			# (scope > 0) auto-uncompute when their scope exits.
			current = current_scope_depth.get()
			if current < self.creation_scope:
				# Scope has exited (depth decreased below creation scope) - safe to uncompute
				self._do_uncompute(from_del=True)
			# else: Still in or at creation scope - defer uncomputation
			# Scope-internal qints are uncomputed by __exit__ scope cleanup

		# Keep backward compat tracking (deprecated, but maintained for older code)
		# Guard against underflow when replaying inverse functions (Phase 51)
		if not self._is_uncomputed and self.bits > 0:
			current_smallest = _get_smallest_allocated_qubit()
			if current_smallest >= self.bits:
				_set_smallest_allocated_qubit(current_smallest - self.bits)
			_decrement_ancilla(self.bits)

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
		self._check_not_uncomputed()

		# Phase 118: Enforce qbool-only (width=1) for with-block conditions
		if self.bits != 1:
			raise TypeError(
				f"with-block condition must be a qbool (1-bit), "
				f"got {self.bits}-bit qint"
			)

		_scope_stack = _get_scope_stack()

		# Phase 118: AND-composition at depth >= 1
		if _get_controlled():
			current_ctrl = _get_control_bool()
			and_ancilla = _toffoli_and(current_ctrl.qubits[63], self.qubits[63])
			_push_control(self, and_ancilla)
		else:
			# Single-level: no AND needed (backward compatible)
			_push_control(self, None)

		# Phase 19: Scope management - push new scope frame
		current_scope_depth.set(current_scope_depth.get() + 1)
		_scope_stack.append([])  # New empty scope frame

		# Update creation_scope for intermediate expressions used as conditions.
		# Python evaluates `with EXPR:` BEFORE calling __enter__, so the expression's
		# temporaries are created at the outer scope (often scope 0) and never
		# registered in any scope frame. By bumping creation_scope to the new inner
		# scope depth, the LAZY __del__ check (current < creation_scope) will trigger
		# uncomputation when the with-statement drops its reference. User-created
		# variables (operation_type=None) are left unchanged.
		if self.operation_type is not None:
			self.creation_scope = current_scope_depth.get()

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
		_scope_stack = _get_scope_stack()

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

		# Phase 118: Uncompute AND-ancilla if present
		_cs = _get_control_stack()
		qbool_ref, and_ancilla = _cs[-1]
		if and_ancilla is not None:
			outer_entry = _cs[-2]
			outer_ctrl = outer_entry[1] if outer_entry[1] is not None else outer_entry[0]
			_uncompute_toffoli_and(and_ancilla, outer_ctrl.qubits[63], qbool_ref.qubits[63])

		# Phase 19: Decrement scope depth
		current_scope_depth.set(current_scope_depth.get() - 1)

		# Phase 117: Pop control entry from stack
		_pop_control()

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

	# --- Operation sections (inlined by build_preprocessor.py) ---
	# BEGIN include "qint_arithmetic.pxi"
	# ====================================================================
	# ARITHMETIC OPERATIONS
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef addition_inplace(self, other, int invert=False):
		# Phase 60-03: Thin Cython wrapper -- all hot-path logic moved to C
		# (hot_path_add.c). We only extract qubit indices from Python objects
		# here, then call the C function with nogil.
		# Phase 93: Mark that arithmetic has been performed (freezes tradeoff option)
		_mark_arithmetic_performed()
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int ancilla_qa[128]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef int num_ancilla = NUMANCILLY
		cdef unsigned int[:] ancilla_arr
		cdef unsigned int[:] control_qubits

		# Extract self qubits (right-aligned in 64-element array)
		for i in range(self_bits):
			self_qa[i] = self.qubits[self_offset + i]

		# Extract control qubit if controlled
		if _controlled:
			control_qubits = (<qint> _control_bool).qubits
			control_qubit = control_qubits[63]

		# Extract ancilla qubits
		ancilla_arr = _get_ancilla()
		for i in range(num_ancilla):
			ancilla_qa[i] = ancilla_arr[i]

		if type(other) == int:
			classical_value = <int64_t>other
			with nogil:
				hot_path_add_cq(_circuit, self_qa, self_bits,
								classical_value,
								invert, _controlled, control_qubit,
								ancilla_qa, num_ancilla)
			return self

		if not isinstance(other, qint):
			raise ValueError()

		# Extract other qubits for quantum-quantum addition
		cdef int other_bits = (<qint> other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint> other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		with nogil:
			hot_path_add_qq(_circuit, self_qa, self_bits,
							other_qa, other_bits,
							invert, _controlled, control_qubit,
							ancilla_qa, num_ancilla)
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_add = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

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

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_add
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_radd = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

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

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_radd
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_sub = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

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

		# Phase 41: Layer tracking for uncomputation
		a._start_layer = start_layer
		a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		a.operation_type = 'SUB'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_sub
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_neg = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		result = qint(width=self.bits)
		result -= self  # 0 - self = two's complement negation

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'NEG'
		result.add_dependency(self)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_neg
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_rsub = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		result = qint(width=self.bits)
		if type(other) == int:
			result += other   # classical add into zero-init (OK, other is classical)
		else:
			result ^= other   # quantum copy other
		result -= self         # result = other - self

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'SUB'
		result.add_dependency(self)
		if type(other) == qint:
			result.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_rsub
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_lsh = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result *= (1 << other)

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'LSHIFT'
		result.add_dependency(self)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_lsh
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_rsh = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result //= (1 << other)

		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'RSHIFT'
		result.add_dependency(self)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_rsh
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
		# Phase 60-02: Thin Cython wrapper -- all hot-path logic moved to C
		# (hot_path_mul.c). We only extract qubit indices from Python objects
		# here, then call the C function with nogil.
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int ret_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int ancilla_qa[128]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int ret_offset = 64 - (<qint>ret).bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef int num_ancilla = NUMANCILLY
		cdef unsigned int[:] ancilla_arr
		cdef unsigned int[:] control_qubits
		cdef unsigned int[:] ret_qubits_mv = (<qint>ret).qubits
		cdef int result_bits = (<qint>ret).bits

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

		# Extract ancilla qubits
		ancilla_arr = _get_ancilla()
		for i in range(num_ancilla):
			ancilla_qa[i] = ancilla_arr[i]

		if type(other) == int:
			classical_value = <int64_t>other
			with nogil:
				hot_path_mul_cq(_circuit, ret_qa, result_bits,
								self_qa, self_bits,
								classical_value,
								_controlled, control_qubit,
								ancilla_qa, num_ancilla)
			return ret

		if not isinstance(other, qint):
			raise TypeError("Multiplication requires qint or int")

		# Extract other qubits for quantum-quantum multiplication
		cdef int other_bits = (<qint>other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint>other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		with nogil:
			hot_path_mul_qq(_circuit, ret_qa, result_bits,
							self_qa, self_bits,
							other_qa, other_bits,
							_controlled, control_qubit,
							ancilla_qa, num_ancilla)
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_mul = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# Determine result width
		if isinstance(other, qint):  # Includes qint subclasses like qint_mod
			result_width = max(self.bits, (<qint>other).bits)
		elif type(other) == int:
			result_width = self.bits
		else:
			if _circ_init:
				(<circuit_s*>_circ).layer_floor = _saved_floor_mul
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

		# Phase 41: Layer tracking for uncomputation
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_mul
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer before any gates
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_rmul = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

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

		# Phase 41: Layer tracking for uncomputation
		result._start_layer = start_layer
		result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_rmul
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

	# END include "qint_arithmetic.pxi"
	# BEGIN include "qint_bitwise.pxi"
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
		run_instruction(seq, &arr[0], False, _circuit)

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
		run_instruction(seq, &arr[0], False, _circuit)

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
		run_instruction(seq, &arr[0], False, _circuit)

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
		run_instruction(seq, &arr[0], False, _circuit)

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

	# END include "qint_bitwise.pxi"
	# BEGIN include "qint_comparison.pxi"
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

	# END include "qint_comparison.pxi"
	# BEGIN include "qint_division.pxi"
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
			toffoli_divmod_cq(_circ, dividend_qa, n,
			                  <int64_t>divisor,
			                  quotient_qa, remainder_qa)
		elif type(divisor) == qint:
			div_bits = (<qint>divisor).bits
			d_offset = 64 - div_bits
			for i in range(div_bits):
				divisor_qa[i] = (<qint>divisor).qubits[d_offset + i]

			toffoli_divmod_qq(_circ, dividend_qa, n,
			                  divisor_qa, div_bits,
			                  quotient_qa, remainder_qa)
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_div = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# Validation
		if type(divisor) == int:
			if divisor == 0:
				if _circ_init:
					(<circuit_s*>_circ).layer_floor = _saved_floor_div
				raise ZeroDivisionError("Division by zero")
			if divisor < 0:
				if _circ_init:
					(<circuit_s*>_circ).layer_floor = _saved_floor_div
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			if _circ_init:
				(<circuit_s*>_circ).layer_floor = _saved_floor_div
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, True, False)

		# Phase 41: Layer tracking for uncomputation
		quotient._start_layer = start_layer
		quotient._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		quotient.operation_type = 'DIV'
		quotient.add_dependency(self)
		if type(divisor) == qint:
			quotient.add_dependency(divisor)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_div
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_mod = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# Validation
		if type(divisor) == int:
			if divisor == 0:
				if _circ_init:
					(<circuit_s*>_circ).layer_floor = _saved_floor_mod
				raise ZeroDivisionError("Modulo by zero")
			if divisor < 0:
				if _circ_init:
					(<circuit_s*>_circ).layer_floor = _saved_floor_mod
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			if _circ_init:
				(<circuit_s*>_circ).layer_floor = _saved_floor_mod
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, False, True)

		# Phase 41: Layer tracking for uncomputation
		remainder._start_layer = start_layer
		remainder._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
		remainder.operation_type = 'MOD'
		remainder.add_dependency(self)
		if type(divisor) == qint:
			remainder.add_dependency(divisor)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_mod
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
		cdef int start_layer
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Phase 41: Capture start layer
		start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

		# Quick-013: Save and set layer floor
		cdef unsigned int _saved_floor_dm = (<circuit_s*>_circ).layer_floor if _circ_init else 0
		if _circ_init:
			(<circuit_s*>_circ).layer_floor = start_layer

		# Validation
		if type(divisor) == int:
			if divisor == 0:
				if _circ_init:
					(<circuit_s*>_circ).layer_floor = _saved_floor_dm
				raise ZeroDivisionError("Divmod by zero")
			if divisor < 0:
				if _circ_init:
					(<circuit_s*>_circ).layer_floor = _saved_floor_dm
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			if _circ_init:
				(<circuit_s*>_circ).layer_floor = _saved_floor_dm
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, True, True)

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
		if type(divisor) == qint:
			quotient.add_dependency(divisor)
			remainder.add_dependency(divisor)

		if _circ_init:
			(<circuit_s*>_circ).layer_floor = _saved_floor_dm
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
	# END include "qint_division.pxi"
