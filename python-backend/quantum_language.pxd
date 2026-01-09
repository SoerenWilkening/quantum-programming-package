from libc.stdlib cimport free, malloc, calloc
from libc.string cimport memcpy

# cdef int INTEGERSIZE = 64

cdef extern from "Integer.h":
	ctypedef struct gate_t:
		pass

	ctypedef struct sequence_t:
		pass

	sequence_t *CC_mul();
	sequence_t *CQ_mul();
	sequence_t *QQ_mul();
	sequence_t *cCQ_mul();
	sequence_t *cQQ_mul();

	sequence_t *CC_add();
	sequence_t *CQ_add();
	sequence_t *QQ_add();
	sequence_t *cCQ_add();
	sequence_t *cQQ_add();


cdef extern from "QPU.h":
	ctypedef struct circuit_t:
		pass

	ctypedef struct quantum_int_t:
		pass

	circuit_t *init_circuit();
	void print_circuit(circuit_t *circ);
	void free_circuit(circuit_t *circ);

cdef extern from "execution.h":
	void qubit_mapping(unsigned int qubit_arrray[], circuit_t *circ);
	void run_instruction(sequence_t *res, const unsigned int qubit_array[], bool invert, circuit_t *circ);


