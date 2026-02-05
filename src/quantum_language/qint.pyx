# NOTE: This file is intentionally large (~2800 lines). Cython cdef classes
# cannot be split across files (no include/mixin support in cdef class bodies).
# See .planning/quick/004-consolidate-qint-pxi-includes-to-remove-/004-SUMMARY.md
"""Quantum integer type with arithmetic, bitwise, and comparison operations."""

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
)

# Python-level imports for global state access via accessor functions
from ._core import (
    _get_circuit, _get_circuit_initialized, _set_circuit_initialized,
    _get_num_qubits, _set_num_qubits,
    _get_int_counter, _set_int_counter, _increment_int_counter,
    _get_controlled, _set_controlled,
    _get_control_bool, _set_control_bool,
    _get_list_of_controls, _set_list_of_controls,
    _get_smallest_allocated_qubit, _set_smallest_allocated_qubit,
    _get_qubit_saving_mode, _set_qubit_saving_mode,
    _get_global_creation_counter, _increment_global_creation_counter,
    _get_scope_stack,
    _get_ancilla, _increment_ancilla, _decrement_ancilla,
    qubit_array,
    current_scope_depth,
)


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
		_controlled = _get_controlled()
		_control_bool = _get_control_bool()
		_list_of_controls = _get_list_of_controls()
		_scope_stack = _get_scope_stack()

		if not _controlled:
			_set_control_bool(self)
		else:
			# TODO: and operation of self and qint._control_bool
			_list_of_controls.append(_control_bool)
			_control_bool &= self
			pass
		_set_controlled(True)

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

		# Phase 19: Decrement scope depth
		current_scope_depth.set(current_scope_depth.get() - 1)

		# THEN restore control state (existing logic)
		_set_controlled(False)
		_set_control_bool(None)

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

	# --- Operation sections (inlined by build_preprocessor.py) ---
	include "qint_arithmetic.pxi"
	include "qint_bitwise.pxi"
	include "qint_comparison.pxi"
	include "qint_division.pxi"
