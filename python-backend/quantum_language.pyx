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

# Phase 19: Scope stack for context manager integration
# Each entry is a list of qbools created in that scope
_scope_stack = []  # List[List[qint]]

# Phase 20: Global uncomputation mode flag
_qubit_saving_mode = False  # Default: lazy mode


def option(key: str, value=None):
	"""Get or set quantum language options.

	Parameters
	----------
	key : str
		Option name. Currently supported:
		- 'qubit_saving': Enable eager uncomputation (bool)
	value : bool, optional
		New value for option. If None, returns current value.

	Returns
	-------
	bool or None
		Current value if value=None, otherwise None.

	Examples
	--------
	>>> ql.option('qubit_saving')
	False
	>>> ql.option('qubit_saving', True)
	>>> ql.option('qubit_saving')
	True

	Notes
	-----
	Mode changes affect newly created qbools only. Existing qbools
	retain their creation-time mode.
	"""
	global _qubit_saving_mode

	if key == 'qubit_saving':
		if value is None:
			return _qubit_saving_mode
		if not isinstance(value, bool):
			raise ValueError("qubit_saving option requires bool value")
		_qubit_saving_mode = value
	else:
		raise ValueError(f"Unknown option: {key}")


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


# Circuit class - handles quantum circuit initialization and optimization
include "circuit_class.pxi"

cdef class qint(circuit):
	cdef int counter
	cdef int bits
	cdef int value
	cdef object qubits
	cdef bint allocated_qubits
	cdef unsigned int allocated_start  # Starting qubit index from allocator

	# Enable weak references for dependency tracking
	cdef object __weakref__

	# Phase 16: Dependency tracking attributes (public for Python access)
	cdef public object dependency_parents  # list[weakref.ref[qint]]
	cdef public int _creation_order
	cdef public object operation_type  # str: 'AND', 'OR', 'XOR', 'EQ', 'LT', 'GT', 'LE', 'GE'
	cdef public int creation_scope  # scope depth when created
	cdef public object control_context  # list of control qubit indices when created

	# Phase 18: Uncomputation tracking attributes
	cdef public bint _is_uncomputed  # Idempotency flag
	cdef public int _start_layer     # Layer before operation (for reversal range)
	cdef public int _end_layer       # Layer after operation (for reversal range)

	# Phase 20: Mode capture attribute
	cdef public bint _uncompute_mode  # True = eager, False = lazy

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

			# Phase 19: Register with active scope if inside a with block
			global _scope_stack
			if _scope_stack and self.creation_scope == current_scope_depth.get() and current_scope_depth.get() > 0:
				_scope_stack[-1].append(self)

			# Phase 18: Initialize uncomputation tracking
			self._is_uncomputed = False
			self._start_layer = 0
			self._end_layer = 0

			# Phase 20: Capture uncomputation mode at creation
			global _qubit_saving_mode
			self._uncompute_mode = _qubit_saving_mode

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

			# Phase 19: Register with active scope if inside a with block
			global _scope_stack
			if _scope_stack and self.creation_scope == current_scope_depth.get() and current_scope_depth.get() > 0:
				_scope_stack[-1].append(self)

			# Phase 18: Initialize uncomputation tracking
			self._is_uncomputed = False
			self._start_layer = 0
			self._end_layer = 0

			# Phase 20: Capture uncomputation mode at creation
			global _qubit_saving_mode
			self._uncompute_mode = _qubit_saving_mode

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

	# All qint operations and utility methods (dependency tracking, uncomputation, context manager)
	include "qint_operations.pxi"





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



# Modular arithmetic class
include "qint_modular.pxi"


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


def get_current_layer():
	"""Get current layer count in circuit.

	Returns
	-------
	int
		Number of used layers in circuit.

	Examples
	--------
	>>> c = circuit()
	>>> a = qint(5, width=4)
	>>> layer = get_current_layer()
	>>> b = qint(3, width=4)
	>>> new_layer = get_current_layer()
	>>> new_layer > layer
	True
	"""
	cdef circuit_s *circ
	global _circuit
	if not _circuit_initialized:
		return 0
	circ = <circuit_s*>_circuit
	return circ.used_layer


def reverse_instruction_range(int start_layer, int end_layer):
	"""Reverse gates in circuit from start_layer to end_layer (exclusive).

	Parameters
	----------
	start_layer : int
		Starting layer index (inclusive)
	end_layer : int
		Ending layer index (exclusive)

	Notes
	-----
	Reverses gates in LIFO order, appending adjoint gates to circuit.
	Phase gates have their angles negated. Self-adjoint gates (X, H, CX)
	are their own inverses.

	Examples
	--------
	>>> c = circuit()
	>>> start = get_current_layer()
	>>> a = qint(5, width=4)
	>>> end = get_current_layer()
	>>> reverse_instruction_range(start, end)
	"""
	global _circuit
	if not _circuit_initialized:
		raise RuntimeError("Circuit not initialized")
	reverse_circuit_range(_circuit, start_layer, end_layer)
