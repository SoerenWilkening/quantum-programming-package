import sys
import warnings
import weakref
import contextvars

import numpy as np

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


# Accessor functions for global state - other modules use these
def _get_circuit():
	"""Return pointer to current circuit (as Python int for C interop)."""
	return <unsigned long long>_circuit

def _get_circuit_initialized():
	"""Check if circuit is initialized."""
	return _circuit_initialized

def _set_circuit_initialized(bint value):
	"""Set circuit initialization flag."""
	global _circuit_initialized
	_circuit_initialized = value

def _get_num_qubits():
	"""Get current qubit count."""
	return _num_qubits

def _set_num_qubits(int value):
	"""Set qubit count."""
	global _num_qubits
	_num_qubits = value

def _get_int_counter():
	"""Get integer counter for qint naming."""
	return _int_counter

def _set_int_counter(int value):
	"""Set integer counter."""
	global _int_counter
	_int_counter = value

def _increment_int_counter():
	"""Increment and return integer counter."""
	global _int_counter
	_int_counter += 1
	return _int_counter

def _get_controlled():
	"""Check if in controlled context."""
	return _controlled

def _set_controlled(bint value):
	"""Set controlled context flag."""
	global _controlled
	_controlled = value

def _get_control_bool():
	"""Get current control boolean."""
	return _control_bool

def _set_control_bool(value):
	"""Set control boolean."""
	global _control_bool
	_control_bool = value

def _get_list_of_controls():
	"""Get list of control qubits."""
	return _list_of_controls

def _set_list_of_controls(value):
	"""Set list of control qubits."""
	global _list_of_controls
	_list_of_controls = value

def _get_smallest_allocated_qubit():
	"""Get smallest allocated qubit index."""
	return _smallest_allocated_qubit

def _set_smallest_allocated_qubit(unsigned int value):
	"""Set smallest allocated qubit index."""
	global _smallest_allocated_qubit
	_smallest_allocated_qubit = value

def _get_qubit_saving_mode():
	"""Check if qubit saving mode is enabled."""
	return _qubit_saving_mode

def _set_qubit_saving_mode(bint value):
	"""Set qubit saving mode."""
	global _qubit_saving_mode
	_qubit_saving_mode = value

def _get_global_creation_counter():
	"""Get global creation counter."""
	return _global_creation_counter

def _increment_global_creation_counter():
	"""Increment and return global creation counter."""
	global _global_creation_counter
	_global_creation_counter += 1
	return _global_creation_counter

def _get_scope_stack():
	"""Get scope stack reference."""
	return _scope_stack

def _get_ancilla():
	"""Get ancilla array reference."""
	return ancilla

def _increment_ancilla(int amount):
	"""Increment ancilla[0] by amount (legacy compatibility)."""
	global ancilla
	ancilla[0] += amount

def _decrement_ancilla(int amount):
	"""Decrement ancilla[0] by amount (legacy compatibility)."""
	global ancilla
	ancilla[0] -= amount


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


qubit_array = np.ndarray(4 * 64 + NUMANCILLY, dtype = np.uint32)  # Max width support
ancilla = np.ndarray(NUMANCILLY, dtype = np.uint32)
for i in range(NUMANCILLY):
	ancilla[i] = i


def array(dim: int | tuple[int, int] | list[int], dtype=None):
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
		NOTE: When called from _core module directly, dtype must be provided.
		      Use quantum_language.array() for default dtype behavior.

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
	if dtype is None:
		raise RuntimeError("dtype must be specified - use quantum_language.array() not _core.array()")

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
		global _circuit_initialized, _circuit, _num_qubits, _int_counter, _smallest_allocated_qubit, _controlled, _control_bool, _list_of_controls, _global_creation_counter, _scope_stack
		# Only reset circuit when called directly as circuit(), not from subclass super().__init__()
		if type(self) is circuit:
			if _circuit_initialized:
				# Free the old circuit before creating a new one
				free_circuit(<circuit_t*>_circuit)
			_circuit = init_circuit()
			_circuit_initialized = True
			# Reset all Python-level global state
			_num_qubits = 0
			_int_counter = 0
			_smallest_allocated_qubit = 0
			_controlled = False
			_control_bool = None
			_list_of_controls = []
			_global_creation_counter = 0
			_scope_stack = []
			# Reset legacy ancilla tracking
			for i in range(NUMANCILLY):
				ancilla[i] = i
		elif not _circuit_initialized:
			# First-time init from subclass (should not normally happen)
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

	def __dealloc__(self):
		pass


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


circuit()
