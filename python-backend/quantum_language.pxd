from libc.stdlib cimport free, malloc, calloc
from libc.string cimport memcpy
from libc.stdint cimport int64_t

# cdef int INTEGERSIZE = 64

cdef extern from "Integer.h":
	ctypedef struct gate_t:
		pass

	ctypedef struct sequence_t:
		pass

	sequence_t *CC_mul();
	sequence_t *CQ_mul(long long value);
	sequence_t *QQ_mul();
	sequence_t *cCQ_mul(long long value);
	sequence_t *cQQ_mul();

	sequence_t *CC_add();
	sequence_t *CQ_add(int bits, long long value);
	sequence_t *QQ_add(int bits);
	sequence_t *cCQ_add(int bits, long long value);
	sequence_t *cQQ_add(int bits);


cdef extern from "LogicOperations.h":
	sequence_t *q_and_seq();
	sequence_t *cq_and_seq();
	sequence_t *qq_and_seq();
	sequence_t *cqq_and_seq();

	sequence_t *q_not_seq();
	sequence_t *cq_not_seq();

	sequence_t *qq_or_seq();

	# Width-parameterized bitwise operations (Phase 6)
	sequence_t *Q_not(int bits)
	sequence_t *cQ_not(int bits)
	sequence_t *Q_xor(int bits)
	sequence_t *cQ_xor(int bits)
	sequence_t *Q_and(int bits)
	sequence_t *CQ_and(int bits, int64_t value)
	sequence_t *Q_or(int bits)
	sequence_t *CQ_or(int bits, int64_t value)


cdef extern from "QPU.h":
	ctypedef struct circuit_t:
		pass

	ctypedef struct quantum_int_t:
		pass

	ctypedef struct instruction_t:
		int *R0

	instruction_t *QPU_state

	circuit_t *init_circuit();
	void print_circuit(circuit_t *circ);
	void free_circuit(circuit_t *circ);

cdef extern from "execution.h":
	void qubit_mapping(unsigned int qubit_arrray[], circuit_t *circ);
	void run_instruction(sequence_t *res, const unsigned int qubit_array[], int invert, circuit_t *circ);

cdef extern from "qubit_allocator.h":
	# Forward declaration to match C header
	cdef struct circuit_s:
		pass

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


