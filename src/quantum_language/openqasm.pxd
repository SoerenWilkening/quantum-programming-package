from libc.stdlib cimport free

cdef extern from "QPU.h":
    ctypedef struct circuit_t:
        pass

cdef extern from "circuit_output.h":
    char *circuit_to_qasm_string(circuit_t *circ)
