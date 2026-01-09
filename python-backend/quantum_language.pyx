import numpy as np
# cimport numpy as np

INTEGERSIZE = 64
NUMANCILLY = 2 * INTEGERSIZE

QUANTUM = 0
CLASSICAL = 1

cdef circuit_t *_circuit
cdef bool _circuit_initialized = False
cdef int _num_qubits = 0

cdef bool _controlled = False
cdef object _control_bool = None
cdef int _int_counter = 0

cdef unsigned int _smallest_allocated_qubit = 0


# cdef unsigned int * qubit_array = <unsigned int *> malloc(6 * INTEGERSIZE)

qubit_array = np.ndarray(6 * INTEGERSIZE, dtype = np.uint32)
ancilla = np.ndarray(NUMANCILLY, dtype = np.uint32)
for i in range(NUMANCILLY):
	ancilla[i] = i

cdef class circuit:
	def __init__(self):
		global _circuit_initialized, _circuit, _num_qubits
		if not _circuit_initialized:
			_circuit = init_circuit()
		_circuit_initialized = True

	def add_qubits(self, qubits):
		global _num_qubits
		_num_qubits += qubits

	def __str__(self):
		print_circuit(_circuit)
		return ""

	def __dealloc__(self):
		pass


cdef class qint(circuit):
	cdef int counter
	cdef int bits
	cdef int value
	cdef int _type
	cdef object qubits

	def __init__(self, value = 0, bits = 64, classical = True):
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits
		super().__init__()
		_int_counter += 1
		self.counter = _int_counter
		self.bits : int = bits
		self.value: int | bool = value
		self._type: bool = classical

		_num_qubits += bits

		self.qubits = np.ndarray(INTEGERSIZE, dtype = np.uint32)
		for i in range(bits):
			self.qubits[INTEGERSIZE - bits + i] = _smallest_allocated_qubit + i

		_smallest_allocated_qubit += bits
		ancilla += bits

	def print_circuit(self):
		print_circuit(_circuit)

	def __str__(self):
		print(INTEGERSIZE)
		print(self.qubits)
		# print_circuit(_circuit)
		return f"int {self.counter} -> {self.bits} bits"

	# Context manager protocol
	def __enter__(self):
		global _controlled, _control_bool
		if not _controlled:
			_control_bool = self
		else:
			# TODO: and operation of self and qint._control_bool
			_control_bool &= self
			pass
		_controlled = True
		return self

	def __exit__(self, exc__type, exc, tb):
		global _controlled, _control_bool
		_controlled = False

		# undo logical and operations
		_control_bool = None
		return False  # do not suppress exceptions

	cdef addition_quantum(self, other: qint | int):
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr

		qubit_array[:INTEGERSIZE] = self.qubits
		# memcpy(qubit_array, <const void *>self.qubits, INTEGERSIZE * sizeof(int))

		if type(other) == int:
			# add classical value to structure
			if self._type == CLASSICAL:
				# value is classical at the moment
				# a = qint(self.value + other, self.bits)
				print(f"{self.value} + {other}")
				self.value += other
				return self
			else:
				# value is a quantum integer
				# TODO: include quantum operations
				if _controlled:
					print("cqadd")
				else:
					print("qadd")
				return self

		if type(other) == qint:
			qubit_array[INTEGERSIZE: 2 * INTEGERSIZE] = (<qint> other).qubits

		if type(other) == qint and (<qint> other)._type == CLASSICAL:
			# add qint to structure that is classical
			if self._type == CLASSICAL:
				# value is classical at the moment
				# a = qint(self.value + other.value, self.bits)
				print(f"{self.value} + {other.value}")
				self.value += other.value
				return self
			else:
				# value is a quantum integer
				# TODO: include quantum operations
				if _controlled:
					print("cqadd")
				else:
					print("qadd")
				return self

		if type(other) == qint and (<qint> other)._type == QUANTUM:
			# add qint to structure that is quantum
			if self._type == CLASSICAL:
				# value is a quantum integer
				# TODO: include quantum operations
				if _controlled:
					print("cqadd")
				else:
					print("qadd")
				return other
			if self._type == QUANTUM:
				# value is a quantum integer
				# TODO: include quantum operations

				qubit_array[2 * INTEGERSIZE: 3 * INTEGERSIZE] = (<qint> other).qubits

				if _controlled:
					print("cqqadd")
					qubit_array[3 * INTEGERSIZE: 4 * INTEGERSIZE] = (<qbool> _control_bool).qubits
					qubit_array[4 * INTEGERSIZE: 4 * INTEGERSIZE + NUMANCILLY] = ancilla
					seq = cQQ_add()
				else:
					print("qqadd")
					qubit_array[3 * INTEGERSIZE: 3 * INTEGERSIZE + NUMANCILLY] = ancilla
					seq = QQ_add()

				arr = qubit_array
				run_instruction(seq, &arr[0], False, _circuit)
				return self

	def __add__(self, other):
		# out of place addition
		a = qint(value = self.value, bits = self.bits, classical = self._type)
		a += other
		return a

	def __radd__(self, other):
		# out of place addition
		a = qint(value = self.value, bits = self.bits, classical = self._type)
		a += other
		return a

	def __iadd__(self, other):
		# in place addition
		return self.addition_quantum(other)

	def __and__(self, other):
		a = qbool()
		print("and")
		# TODO: include quantum functionality
		return a

	def __iand__(self, other):
		a = qbool()
		print("and")
		# TODO: include quantum functionality
		return a

	def __or__(self, other):
		a = qbool()
		print("or")
		# TODO: include quantum functionality
		return a

	def __ior__(self, other):
		a = qbool()
		print("or")
		# TODO: include quantum functionality
		return a

	def __xor__(self, other):
		a = qbool()
		print("xor")
		# TODO: include quantum functionality
		return a

	def __ixor__(self, other):
		a = qbool()
		print("inplace xor")
		# TODO: include quantum functionality
		return a

	def __invert__(self):
		a = qbool()
		print("not")
		# TODO: include quantum functionality
		return a


cdef class qbool(qint):

	def __init__(self, value: bool = False, classical: bool = True):
		super().__init__(value, bits = 1, classical = classical)
