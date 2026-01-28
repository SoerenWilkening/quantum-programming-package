import sys
import warnings
import weakref
import contextvars

import numpy as np
# cimport numpy as np

# Module version
__version__ = "0.1.0"

INTEGERSIZE = 8
NUMANCILLY = 2 * 64  # Max possible ancilla (2 * max_width)

# Module-level constant for available optimization passes
AVAILABLE_PASSES = ['merge', 'cancel_inverse']

# QPU_state removed (Phase 11) - global state no longer used
# All C functions now take explicit parameters instead of reading from registers

QUANTUM = 0
CLASSICAL = 1

cdef circuit_t *_circuit
cdef bint _circuit_initialized = False
cdef int _num_qubits = 0

cdef bint _controlled = False
cdef object _control_bool = None
cdef int _int_counter = 0
cdef object _list_of_controls = []

cdef unsigned int _smallest_allocated_qubit = 0

# Module-level context variable for scope depth (Phase 16: dependency tracking)
current_scope_depth = contextvars.ContextVar('scope_depth', default=0)

# Global creation counter for dependency cycle prevention
_global_creation_counter = 0

# cdef unsigned int * qubit_array = <unsigned int *> malloc(6 * INTEGERSIZE)

qubit_array = np.ndarray(4 * 64 + NUMANCILLY, dtype = np.uint32)  # Max width support
ancilla = np.ndarray(NUMANCILLY, dtype = np.uint32)
for i in range(NUMANCILLY):
	ancilla[i] = i


def array(dim: int | tuple[int, int] | list[int], dtype = qint) -> list[qint | qbool]:
	"""Create array of quantum integers or booleans.

	Parameters
	----------
	dim : int, tuple of int, or list of int
		Array dimensions:
		- int: 1D array of length dim
		- tuple (rows, cols): 2D array
		- list of int: 1D array with specified initial values
	dtype : type, optional
		Element type: qint or qbool (default qint).

	Returns
	-------
	list or list of list
		Array of quantum integers/booleans.

	Examples
	--------
	>>> arr = array(5)              # [qint(), qint(), qint(), qint(), qint()]
	>>> arr = array([1, 2, 3])      # [qint(1), qint(2), qint(3)]
	>>> arr = array((2, 3))         # 2x3 2D array
	>>> arr = array(3, dtype=qbool) # [qbool(), qbool(), qbool()]
	"""
	if type(dim) == list:
		return [dtype(j) for j in dim]
	if type(dim) == tuple:
		return [[dtype() for j in range(dim[1])] for i in range(dim[0])]

	return [dtype() for j in range(dim)]


cdef class circuit:
	def __init__(self):
		"""Initialize quantum circuit.

		Creates a new quantum circuit instance. The circuit tracks gate
		operations and qubit allocations for quantum computations.

		Examples
		--------
		>>> c = circuit()
		>>> a = qint(5)
		>>> b = qint(3)
		>>> result = a + b
		"""
		global _circuit_initialized, _circuit, _num_qubits
		if not _circuit_initialized:
			_circuit = init_circuit()
		_circuit_initialized = True

	def add_qubits(self, qubits):
		"""Allocate additional qubits to the circuit.

		Parameters
		----------
		qubits : int
			Number of qubits to allocate.

		Examples
		--------
		>>> c = circuit()
		>>> c.add_qubits(5)
		"""
		global _num_qubits
		_num_qubits += qubits

	def visualize(self):
		"""Print circuit visualization to stdout.

		Shows horizontal layout with qubit indices, layer numbers, and gate
		symbols. Multi-qubit gates are connected with vertical lines.

		Notes
		-----
		Gate symbols: H (Hadamard), X/Y/Z (Pauli), P (Phase), @ (control), + (target)

		Examples
		--------
		>>> c = circuit()
		>>> a = qint(5, width=4)
		>>> b = qint(3, width=4)
		>>> _ = a + b
		>>> c.visualize()
		     0        5        10
		q0   ---H--@-------P--...
		q1   ------+--H--------...
		...
		"""
		circuit_visualize(<circuit_t*>_circuit)

	@property
	def gate_count(self):
		"""Total number of gates in circuit.

		Returns
		-------
		int
			Total gate count.

		Examples
		--------
		>>> c = circuit()
		>>> a = qint(5)
		>>> b = qint(3)
		>>> c = a + b
		>>> circuit().gate_count
		42
		"""
		return circuit_gate_count(<circuit_s*>_circuit)

	@property
	def depth(self):
		"""Circuit depth (number of layers).

		Each layer can execute in parallel on quantum hardware.

		Returns
		-------
		int
			Number of layers.

		Examples
		--------
		>>> c = circuit()
		>>> a = qint(5)
		>>> circuit().depth
		12
		"""
		return circuit_depth(<circuit_s*>_circuit)

	@property
	def qubit_count(self):
		"""Number of qubits used in circuit.

		Returns
		-------
		int
			Number of qubits.

		Examples
		--------
		>>> c = circuit()
		>>> a = qint(5, width=8)
		>>> circuit().qubit_count
		8
		"""
		return circuit_qubit_count(<circuit_s*>_circuit)

	@property
	def gate_counts(self):
		"""Breakdown of gate types in circuit.

		Returns
		-------
		dict
			Gate type to count mapping with keys 'X', 'Y', 'Z', 'H', 'P',
			'CNOT', 'CCX', 'other'.

		Examples
		--------
		>>> c = circuit()
		>>> a = qint(5)
		>>> circuit().gate_counts
		{'X': 3, 'H': 8, 'CNOT': 12, ...}
		"""
		cdef gate_counts_t counts = circuit_gate_counts(<circuit_s*>_circuit)
		return {
			'X': counts.x_gates,
			'Y': counts.y_gates,
			'Z': counts.z_gates,
			'H': counts.h_gates,
			'P': counts.p_gates,
			'CNOT': counts.cx_gates,
			'CCX': counts.ccx_gates,
			'other': counts.other_gates
		}

	@property
	def available_passes(self):
		"""List of available optimization passes.

		Returns
		-------
		list of str
			Pass names that can be used with optimize().

		Examples
		--------
		>>> c = circuit()
		>>> c.available_passes
		['merge', 'cancel_inverse']
		"""
		return AVAILABLE_PASSES.copy()

	def optimize(self, passes=None):
		"""Optimize circuit in-place and return before/after statistics.

		Modifies the current circuit by applying optimization passes.

		Parameters
		----------
		passes : list of str, optional
			Pass names to apply. Available: 'merge', 'cancel_inverse'.
			If None, applies all passes.

		Returns
		-------
		dict
			Statistics comparison with 'before' and 'after' dicts, each
			containing gate_count, depth, qubit_count, gate_counts.

		Raises
		------
		ValueError
			If any pass name is not in available_passes.
		RuntimeError
			If optimization fails.

		Examples
		--------
		>>> c = circuit()
		>>> a = qint(5, width=8)
		>>> # ... operations ...
		>>> stats = c.optimize()  # Run all passes
		>>> print(f"Reduced gates: {stats['before']['gate_count']} -> {stats['after']['gate_count']}")

		>>> stats = c.optimize(passes=['cancel_inverse'])  # Specific pass
		"""
		global _circuit

		cdef circuit_s *opt_circ

		# Capture stats BEFORE optimization
		before_stats = {
			'gate_count': self.gate_count,
			'depth': self.depth,
			'qubit_count': self.qubit_count,
			'gate_counts': self.gate_counts.copy()
		}

		# Validate pass names if provided
		if passes is not None:
			for p in passes:
				if p not in AVAILABLE_PASSES:
					raise ValueError(f"Unknown pass '{p}'. Available: {AVAILABLE_PASSES}")

		# Run optimization - creates optimized copy
		opt_circ = circuit_optimize(<circuit_s*>_circuit)

		if opt_circ == NULL:
			raise RuntimeError("Optimization failed")

		# Free the old circuit and replace with optimized one
		# Note: circuit_optimize creates a new circuit, we need to swap
		free_circuit(<circuit_t*>_circuit)
		_circuit = <circuit_t*>opt_circ

		# Capture stats AFTER optimization
		after_stats = {
			'gate_count': self.gate_count,
			'depth': self.depth,
			'qubit_count': self.qubit_count,
			'gate_counts': self.gate_counts.copy()
		}

		return {
			'before': before_stats,
			'after': after_stats
		}

	def can_optimize(self):
		"""Check if optimization would have any effect.

		Returns
		-------
		bool
			True if optimization would reduce circuit size.

		Examples
		--------
		>>> c = circuit()
		>>> if c.can_optimize():
		...     stats = c.optimize()
		"""
		return circuit_can_optimize(<circuit_s*>_circuit) != 0

	# def __str__(self):
	# 	print_circuit(_circuit)
	# 	return ""

	def __dealloc__(self):
		pass


cdef class qint(circuit):
	cdef int counter
	cdef int bits
	cdef int value
	cdef object qubits
	cdef bint allocated_qubits
	cdef unsigned int allocated_start  # Starting qubit index from allocator

	# Phase 16: Dependency tracking attributes
	cdef object dependency_parents  # list[weakref.ref[qint]]
	cdef int _creation_order
	cdef object operation_type  # str: 'AND', 'OR', 'XOR', 'EQ', 'LT', 'GT', 'LE', 'GE'
	cdef int creation_scope  # scope depth when created
	cdef object control_context  # list of control qubit indices when created

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
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits, qubit_array
		cdef qubit_allocator_t *alloc
		cdef unsigned int start
		cdef int actual_width
		cdef unsigned int[:] arr
		cdef sequence_t *seq
		cdef int bit_pos, qubit_idx
		cdef long long masked_value

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
			_int_counter += 1
			self.counter = _int_counter
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

			_num_qubits += actual_width

			self.qubits = np.ndarray(64, dtype = np.uint32)  # Max width support

			# NEW: Allocate qubits through circuit's allocator
			alloc = circuit_get_allocator(<circuit_s*>_circuit)
			if alloc == NULL:
				raise RuntimeError("Circuit allocator not initialized")

			start = allocator_alloc(alloc, actual_width, True)  # is_ancilla=True
			if start == <unsigned int>-1:
				raise MemoryError("Qubit allocation failed - limit exceeded")

			# Right-aligned qubit storage: indices [64-width] through [63]
			for i in range(actual_width):
				self.qubits[64 - actual_width + i] = start + i

			self.allocated_start = start  # Track for deallocation
			self.allocated_qubits = True

			# Phase 16: Initialize dependency tracking
			global _global_creation_counter, _control_bool
			_global_creation_counter += 1
			self._creation_order = _global_creation_counter
			self.dependency_parents = []
			self.operation_type = None
			self.creation_scope = current_scope_depth.get()
			# Capture control context
			if _control_bool is not None:
				self.control_context = [(<qint>_control_bool).qubits[63]]
			else:
				self.control_context = []

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
			_smallest_allocated_qubit += actual_width
			ancilla += actual_width
		else:
			self.bits = actual_width
			self.qubits = bit_list
			self.allocated_qubits = False

			# Phase 16: Initialize dependency tracking for bit_list path
			global _global_creation_counter, _control_bool
			_global_creation_counter += 1
			self._creation_order = _global_creation_counter
			self.dependency_parents = []
			self.operation_type = None
			self.creation_scope = current_scope_depth.get()
			# Capture control context
			if _control_bool is not None:
				self.control_context = [(<qint>_control_bool).qubits[63]]
			else:
				self.control_context = []

	@property
	def width(self):
		"""Get the bit width of this quantum integer (read-only).

		Returns:
			int: Bit width (1-64)

		Examples:
			>>> a = qint(5, width=16)
			>>> a.width
			16
		"""
		return self.bits

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

	def print_circuit(self):
		"""Print the current quantum circuit to stdout.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> a.print_circuit()
		"""
		print_circuit(_circuit)

	def __del__(self):
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits
		cdef qubit_allocator_t *alloc

		if self.allocated_qubits:
			# NEW: Return qubits to allocator
			alloc = circuit_get_allocator(<circuit_s*>_circuit)
			if alloc != NULL:
				allocator_free(alloc, self.allocated_start, self.bits)

			# Keep backward compat tracking (deprecated)
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
		global _controlled, _control_bool
		if not _controlled:
			_control_bool = self
		else:
			# TODO: and operation of self and qint._control_bool
			_list_of_controls.append(_control_bool)
			_control_bool &= self
			pass
		_controlled = True
		return self

	def __exit__(self, exc__type, exc, tb):
		"""Exit quantum conditional context.

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
		global _controlled, _control_bool, ancilla, _smallest_allocated_qubit
		_controlled = False
		_control_bool = None

		# undo logical and operations
		return False  # do not suppress exceptions

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
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width

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
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width

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
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width

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
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset
		cdef int start

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
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'EQ'

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
		# Self-comparison optimization
		if self is other:
			return qbool(True)  # x >= x is always true
		# self >= other is equivalent to NOT (self < other)
		return ~(self < other)

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



cdef class qbool(qint):
	"""Quantum boolean - a 1-bit quantum integer.

	qbool is syntactic sugar for qint with width=1. All qint operations
	apply to qbool with single-bit semantics.

	Parameters
	----------
	value : bool, optional
		Initial value (default False). Encoded as |0> or |1>.
	classical : bool, optional
		Whether this is a classical boolean (default False).
	create_new : bool, optional
		Whether to allocate new qubit (default True).
	bit_list : array-like, optional
		External qubit (when create_new=False).

	Examples
	--------
	>>> b = qbool(True)   # Creates |1>
	>>> b.width
	1
	>>> c = qbool()       # Creates |0> (False by default)

	Notes
	-----
	Used for quantum conditionals via context manager (with statement).
	"""

	def __init__(self, value: bool = False, classical: bool = False, create_new = True, bit_list = None):
		"""Create quantum boolean.

		Parameters
		----------
		value : bool, optional
			Initial value (default False).
		classical : bool, optional
			Classical boolean flag (default False).
		create_new : bool, optional
			Allocate new qubit (default True).
		bit_list : array-like, optional
			External qubit array (when create_new=False).

		Examples
		--------
		>>> flag = qbool(True)
		>>> with flag:
		...     # Controlled operations
		"""
		super().__init__(value, width=1, classical=classical, create_new=create_new, bit_list=bit_list)


cdef class qint_mod(qint):
	"""Quantum integer with modular arithmetic.

	Modulus N is classical (Python int), known at circuit generation time.
	All operations automatically reduce result mod N.

	Parameters
	----------
	value : int, optional
		Initial value (reduced mod N classically before encoding).
	N : int
		Modulus (required, must be positive).
	width : int, optional
		Bit width (default: N.bit_length()).

	Attributes
	----------
	modulus : int
		The classical modulus N (read-only property).
	width : int
		Bit width (inherited from qint).

	Examples
	--------
	>>> x = qint_mod(5, N=17)
	>>> y = qint_mod(15, N=17)
	>>> z = x + y  # z = 20 mod 17 = 3
	>>> z.modulus
	17

	Notes
	-----
	Used for modular exponentiation in Shor's algorithm and other
	number-theoretic quantum algorithms.
	"""
	cdef int _modulus

	def __init__(self, value=0, N=None, width=None):
		"""Create quantum integer with classical modulus N.

		Parameters
		----------
		value : int, optional
			Initial value (reduced mod N before encoding, default 0).
		N : int
			Modulus (required, must be positive).
		width : int, optional
			Bit width (default: N.bit_length()).

		Raises
		------
		ValueError
			If N is None, non-positive, or not an integer.

		Examples
		--------
		>>> x = qint_mod(25, N=17)  # Creates qint with value 25 % 17 = 8
		>>> x.modulus
		17
		"""
		if N is None or not isinstance(N, int) or N <= 0:
			raise ValueError("Modulus N must be positive integer")

		# Default width: enough bits to represent N
		if width is None:
			width = N.bit_length()

		# Reduce value mod N classically (before quantum encoding)
		reduced_value = value % N

		# Initialize as regular qint
		super().__init__(reduced_value, width=width)

		# Store modulus
		self._modulus = N

	@property
	def modulus(self):
		"""Get the modulus N (read-only).

		Returns
		-------
		int
			The classical modulus N.

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> x.modulus
		17
		"""
		return self._modulus

	def __repr__(self):
		return f"qint_mod(modulus={self._modulus}, width={self.bits})"

	cdef _reduce_mod(self, qint value):
		"""Reduce value mod N via conditional subtraction.

		Uses quantum comparison and conditional subtraction.
		Classical N enables computing max iterations needed.
		"""
		# Max possible value before reduction
		max_val = 1 << value.bits

		# Max times we might need to subtract N
		max_subtractions = (max_val // self._modulus) + 1

		# Iteratively subtract N while value >= N
		# Number of iterations is log2(max_subtractions)
		iterations = max_subtractions.bit_length()

		for _ in range(iterations):
			# Compare: is value >= N?
			cmp = value >= self._modulus

			# Conditional subtraction
			with cmp:
				value -= self._modulus

		return value

	cdef qint_mod _wrap_result(self, qint result):
		"""Wrap plain qint result into qint_mod with same modulus."""
		# Create new qint_mod using existing qubits
		cdef qint_mod wrapped = qint_mod.__new__(qint_mod)

		# Manually copy qint fields (avoiding __init__ which would allocate qubits)
		wrapped.counter = result.counter
		wrapped.bits = result.bits
		wrapped.value = result.value
		wrapped.qubits = result.qubits
		wrapped.allocated_qubits = result.allocated_qubits
		wrapped.allocated_start = result.allocated_start

		# Set modulus (cdef attribute)
		wrapped._modulus = self._modulus

		return wrapped

	def __add__(self, other):
		"""Modular addition: (self + other) mod N

		Parameters
		----------
		other : qint_mod or int
			Value to add.

		Returns
		-------
		qint_mod
			Result reduced mod N.

		Raises
		------
		ValueError
			If other is qint_mod with different modulus.

		Examples
		--------
		>>> x = qint_mod(15, N=17)
		>>> y = qint_mod(5, N=17)
		>>> z = x + y  # (15 + 5) mod 17 = 3
		"""
		# Check modulus compatibility
		if isinstance(other, qint_mod):
			if (<qint_mod>other)._modulus != self._modulus:
				raise ValueError(
					f"Moduli must match: {self._modulus} != {(<qint_mod>other)._modulus}"
				)

		# Perform regular addition (using parent class)
		sum_val = qint.__add__(self, other)

		# Reduce mod N
		reduced = self._reduce_mod(sum_val)

		# Wrap result
		return self._wrap_result(reduced)

	def __sub__(self, other):
		"""Modular subtraction: (self - other) mod N

		Handles negative results by adding N to ensure [0, N) range.

		Parameters
		----------
		other : qint_mod or int
			Value to subtract.

		Returns
		-------
		qint_mod
			Result reduced mod N.

		Raises
		------
		ValueError
			If other is qint_mod with different modulus.

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> y = qint_mod(10, N=17)
		>>> z = x - y  # (5 - 10) mod 17 = 12
		"""
		if isinstance(other, qint_mod):
			if (<qint_mod>other)._modulus != self._modulus:
				raise ValueError(
					f"Moduli must match: {self._modulus} != {(<qint_mod>other)._modulus}"
				)

		# Perform regular subtraction
		diff = qint.__sub__(self, other)

		# If negative (MSB set), add N to make positive
		# Check sign via comparison or MSB
		is_negative = diff < 0
		with is_negative:
			diff += self._modulus

		# Reduce to ensure in range [0, N)
		reduced = self._reduce_mod(diff)

		return self._wrap_result(reduced)

	def __mul__(self, other):
		"""Modular multiplication: (self * other) mod N

		Parameters
		----------
		other : qint_mod or int
			Value to multiply by.

		Returns
		-------
		qint_mod
			Result reduced mod N.

		Raises
		------
		NotImplementedError
			If other is qint_mod (qint_mod * qint_mod not yet supported).
		ValueError
			If other is qint_mod with different modulus.

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> z = x * 7  # (5 * 7) mod 17 = 1
		"""
		# Check for qint_mod * qint_mod (not supported - causes C-layer segfault)
		if isinstance(other, qint_mod):
			raise NotImplementedError(
				"qint_mod * qint_mod multiplication is not yet supported. "
				"Use qint_mod * int instead (e.g., x * 5 instead of x * y)."
			)

		# Perform regular multiplication (qint_mod * int)
		product = qint.__mul__(self, other)

		# Reduce mod N (product may be much larger than N)
		reduced = self._reduce_mod(product)

		return self._wrap_result(reduced)

	def __iadd__(self, other):
		"""In-place modular addition: self += other mod N

		Parameters
		----------
		other : qint_mod or int
			Value to add.

		Returns
		-------
		qint_mod
			Self (with swapped qubit references).

		Examples
		--------
		>>> x = qint_mod(15, N=17)
		>>> x += 5  # (15 + 5) mod 17 = 3
		"""
		result = self + other
		cdef qint_mod result_mod = <qint_mod>result
		self.qubits, result_mod.qubits = result_mod.qubits, self.qubits
		self.allocated_start, result_mod.allocated_start = result_mod.allocated_start, self.allocated_start
		self.bits = result_mod.bits
		return self

	def __isub__(self, other):
		"""In-place modular subtraction: self -= other mod N

		Parameters
		----------
		other : qint_mod or int
			Value to subtract.

		Returns
		-------
		qint_mod
			Self (with swapped qubit references).

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> x -= 10  # (5 - 10) mod 17 = 12
		"""
		result = self - other
		cdef qint_mod result_mod = <qint_mod>result
		self.qubits, result_mod.qubits = result_mod.qubits, self.qubits
		self.allocated_start, result_mod.allocated_start = result_mod.allocated_start, self.allocated_start
		self.bits = result_mod.bits
		return self

	def __imul__(self, other):
		"""In-place modular multiplication: self *= other mod N

		Parameters
		----------
		other : qint_mod or int
			Value to multiply by.

		Returns
		-------
		qint_mod
			Self (with swapped qubit references).

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> x *= 7  # (5 * 7) mod 17 = 1
		"""
		result = self * other
		cdef qint_mod result_mod = <qint_mod>result
		self.qubits, result_mod.qubits = result_mod.qubits, self.qubits
		self.allocated_start, result_mod.allocated_start = result_mod.allocated_start, self.allocated_start
		self.bits = result_mod.bits
		return self


def circuit_stats():
	"""Get qubit allocation statistics for the current circuit.

	Returns
	-------
	dict or None
		Statistics dictionary with keys:
		- peak_allocated: Maximum qubits allocated simultaneously
		- total_allocations: Total allocation operations
		- total_deallocations: Total deallocation operations
		- current_in_use: Currently allocated qubits
		- ancilla_allocations: Ancilla qubit allocations
		Returns None if circuit not initialized.

	Examples
	--------
	>>> c = circuit()
	>>> a = qint(5, width=8)
	>>> stats = circuit_stats()
	>>> stats['current_in_use']
	8
	"""
	cdef qubit_allocator_t *alloc
	cdef allocator_stats_t stats

	if not _circuit_initialized:
		return None

	alloc = circuit_get_allocator(<circuit_s*>_circuit)
	if alloc == NULL:
		return None

	stats = allocator_get_stats(alloc)
	return {
		'peak_allocated': stats.peak_allocated,
		'total_allocations': stats.total_allocations,
		'total_deallocations': stats.total_deallocations,
		'current_in_use': stats.current_in_use,
		'ancilla_allocations': stats.ancilla_allocations
	}
