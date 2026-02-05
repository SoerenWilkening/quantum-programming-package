from ._core cimport circuit

cdef class qint(circuit):
	cdef int counter
	cdef int bits
	cdef int value
	cdef public object qubits
	cdef public bint allocated_qubits
	cdef public unsigned int allocated_start
	cdef object __weakref__
	cdef public object dependency_parents
	cdef public int _creation_order
	cdef public object operation_type
	cdef public int creation_scope
	cdef public object control_context
	cdef public bint _is_uncomputed
	cdef public int _start_layer
	cdef public int _end_layer
	cdef public bint _uncompute_mode
	cdef bint _keep_flag

	# cdef method declarations
	cdef addition_inplace(self, other, int invert=*)
	cdef multiplication_inplace(self, other, qint ret)
