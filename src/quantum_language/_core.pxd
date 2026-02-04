from libc.stdlib cimport free, malloc, calloc
from libc.string cimport memcpy
from libc.stdint cimport int64_t

cdef extern from "arithmetic_ops.h":
	ctypedef struct gate_t:
		pass

	ctypedef struct sequence_t:
		unsigned int num_layer
		unsigned int used_layer

	# Addition operations
	sequence_t *CC_add();
	sequence_t *CQ_add(int bits, long long value);
	sequence_t *QQ_add(int bits);
	sequence_t *cCQ_add(int bits, long long value);
	sequence_t *cQQ_add(int bits);

	# Multiplication operations
	sequence_t *CC_mul();
	sequence_t *CQ_mul(int bits, long long value);
	sequence_t *QQ_mul(int bits);
	sequence_t *cCQ_mul(int bits, long long value);
	sequence_t *cQQ_mul(int bits);

cdef extern from "Integer.h":
	# Type creation and manipulation (non-arithmetic functions only)
	pass  # Arithmetic functions moved to arithmetic_ops.h block


cdef extern from "bitwise_ops.h":
	# Width-parameterized bitwise operations (Phase 6)
	sequence_t *Q_not(int bits)
	sequence_t *cQ_not(int bits)
	sequence_t *Q_xor(int bits)
	sequence_t *cQ_xor(int bits)
	sequence_t *Q_and(int bits)
	sequence_t *CQ_and(int bits, int64_t value)
	sequence_t *Q_or(int bits)
	sequence_t *CQ_or(int bits, int64_t value)

cdef extern from "comparison_ops.h":
	# Width-parameterized comparison operations (Phase 12)
	sequence_t *CQ_equal_width(int bits, int64_t value)
	sequence_t *cCQ_equal_width(int bits, int64_t value)

cdef extern from "LogicOperations.h":
	# Legacy qbool operations
	sequence_t *q_and_seq();
	sequence_t *cq_and_seq();
	sequence_t *qq_and_seq();
	sequence_t *cqq_and_seq();

	sequence_t *q_not_seq();
	sequence_t *cq_not_seq();

	sequence_t *qq_or_seq();


cdef extern from "QPU.h":
	ctypedef struct circuit_t:
		pass

	ctypedef struct quantum_int_t:
		pass

	# instruction_t and QPU_state removed in Phase 11
	# Backend is now stateless - all functions take explicit parameters

	circuit_t *init_circuit();
	void print_circuit(circuit_t *circ);
	void free_circuit(circuit_t *circ);

cdef extern from "circuit_output.h":
	void circuit_visualize(circuit_t *circ)

	ctypedef struct draw_data_t:
		unsigned int num_layers
		unsigned int num_qubits
		unsigned int num_gates
		unsigned int *gate_layer
		unsigned int *gate_target
		unsigned int *gate_type
		double *gate_angle
		unsigned int *gate_num_ctrl
		unsigned int *ctrl_qubits
		unsigned int *ctrl_offsets
		unsigned int *qubit_map

	draw_data_t *circuit_to_draw_data(circuit_t *circ)
	void free_draw_data(draw_data_t *data);

cdef extern from "execution.h":
	void qubit_mapping(unsigned int qubit_arrray[], circuit_t *circ);
	void run_instruction(sequence_t *res, const unsigned int qubit_array[], int invert, circuit_t *circ);
	void reverse_circuit_range(circuit_t *circ, int start_layer, int end_layer);

cdef extern from "qubit_allocator.h":
	# Forward declaration to match C header
	cdef struct circuit_s:
		unsigned int used_layer
		unsigned int used_qubits
		unsigned int layer_floor

	ctypedef struct allocator_stats_t:
		unsigned int peak_allocated
		unsigned int total_allocations
		unsigned int total_deallocations
		unsigned int current_in_use
		unsigned int ancilla_allocations

	ctypedef struct qubit_allocator_t:
		allocator_stats_t stats
		# Other fields are internal, we only need stats access

	qubit_allocator_t *allocator_create(unsigned int initial_capacity)
	void allocator_destroy(qubit_allocator_t *alloc)
	unsigned int allocator_alloc(qubit_allocator_t *alloc, unsigned int count, bint is_ancilla)
	int allocator_free(qubit_allocator_t *alloc, unsigned int start, unsigned int count)
	allocator_stats_t allocator_get_stats(qubit_allocator_t *alloc)

	# Accessor function to get allocator from opaque circuit_t
	# Note: C signature uses struct circuit_s*, but circuit_t* works due to cast in C
	qubit_allocator_t *circuit_get_allocator(circuit_s *circ)

cdef extern from "circuit_stats.h":
	ctypedef struct gate_counts_t:
		size_t x_gates
		size_t y_gates
		size_t z_gates
		size_t h_gates
		size_t p_gates
		size_t cx_gates
		size_t ccx_gates
		size_t other_gates

	size_t circuit_gate_count(circuit_s *circ)
	unsigned int circuit_depth(circuit_s *circ)
	unsigned int circuit_qubit_count(circuit_s *circ)
	gate_counts_t circuit_gate_counts(circuit_s *circ)

cdef extern from "circuit_optimizer.h":
	ctypedef enum opt_pass_t:
		OPT_PASS_MERGE
		OPT_PASS_CANCEL_INVERSE

	circuit_s *circuit_optimize(circuit_s *circ)
	circuit_s *circuit_optimize_pass(circuit_s *circ, opt_pass_t pass_type)
	int circuit_can_optimize(circuit_s *circ)


# Module constants
cdef int INTEGERSIZE
cdef int NUMANCILLY
cdef int QUANTUM
cdef int CLASSICAL

# Global state variables (not cimportable - use accessor functions instead)
# These are defined in _core.pyx but not exposed via cimport

# circuit class declaration
cdef class circuit:
	pass
