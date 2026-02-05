from quantum_language.qint cimport qint

cdef class qarray:
    cdef list _elements      # Flattened list of qint/qbool objects
    cdef tuple _shape        # Shape tuple (e.g., (3,4) for 2D)
    cdef object _dtype       # qint or qbool type reference
    cdef int _width          # Element bit width (for qint arrays)
