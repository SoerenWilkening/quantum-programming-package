import sys

import numpy as np
# cimport numpy as np

INTEGERSIZE = 8
NUMANCILLY = 2 * INTEGERSIZE

QPU_state[0].R0 = <int *> malloc(sizeof(int))

QUANTUM = 0
CLASSICAL = 1

cdef circuit_t *_circuit
cdef bint _circuit_initialized = False
cdef int _num_qubits = 0

cdef bint _controlled = False
cdef object _control_bool = None
cdef int _int_counter = 0
cdef object list_of_constrols = []

cdef unsigned int _smallest_allocated_qubit = 0

# cdef unsigned int * qubit_array = <unsigned int *> malloc(6 * INTEGERSIZE)

qubit_array = np.ndarray(4 * INTEGERSIZE + NUMANCILLY, dtype = np.uint32)
ancilla = np.ndarray(NUMANCILLY, dtype = np.uint32)
for i in range(NUMANCILLY):
	ancilla[i] = i


def array(dim: int | tuple[int, int] | list[int], dtype = qint) -> list[qint | qbool]:
	if type(dim) == list:
		return [dtype(j) for j in dim]
	if type(dim) == tuple:
		return [[dtype() for j in range(dim[1])] for i in range(dim[0])]

	return [dtype() for j in range(dim)]


cdef class circuit:
	def __init__(self):
		global _circuit_initialized, _circuit, _num_qubits
		if not _circuit_initialized:
			_circuit = init_circuit()
		_circuit_initialized = True

	def add_qubits(self, qubits):
		global _num_qubits
		_num_qubits += qubits

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

	def __init__(self, value = 0, bits = INTEGERSIZE, classical = False, create_new = True, bit_list = None):
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits
		super().__init__()

		if create_new:
			_int_counter += 1
			self.counter = _int_counter
			self.bits : int = bits
			self.value: int | bool = value

			_num_qubits += bits

			self.qubits = np.ndarray(INTEGERSIZE, dtype = np.uint32)
			for i in range(bits):
				self.qubits[INTEGERSIZE - bits + i] = _smallest_allocated_qubit + i

			_smallest_allocated_qubit += bits
			ancilla += bits
			self.allocated_qubits = True
		else:
			self.bits = bits
			self.qubits = bit_list
			self.allocated_qubits = False

	def print_circuit(self):
		print_circuit(_circuit)

	def __del__(self):
		global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
		global _num_qubits
		if self.allocated_qubits:
			_smallest_allocated_qubit -= self.bits
			ancilla -= self.bits

	def __str__(self):
		return f"{self.qubits}"

	# Context manager protocol
	def __enter__(self):
		global _controlled, _control_bool
		if not _controlled:
			_control_bool = self
		else:
			# TODO: and operation of self and qint._control_bool
			list_of_constrols.append(_control_bool)
			_control_bool &= self
			pass
		_controlled = True
		return self

	def __exit__(self, exc__type, exc, tb):
		global _controlled, _control_bool, ancilla, _smallest_allocated_qubit
		_controlled = False
		_control_bool = None

		# undo logical and operations
		return False  # do not suppress exceptions

	cdef addition_inplace(self, other: qint | int, invert: int  = False):
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr

		start = 0

		qubit_array[:INTEGERSIZE] = self.qubits
		start += INTEGERSIZE

		if type(other) == int:
			# value is a quantum integer
			QPU_state[0].R0[0] = other
			if _controlled:
				qubit_array[start: start + INTEGERSIZE] = (<qbool> _control_bool).qubits
				qubit_array[start + INTEGERSIZE: start + INTEGERSIZE + NUMANCILLY] = ancilla
				seq = cCQ_add(self.bits)
			else:
				qubit_array[start: start + NUMANCILLY] = ancilla
				seq = CQ_add(self.bits)


			arr = qubit_array
			run_instruction(seq, &arr[0], invert, _circuit)

			return self
		if type(other) != qint:
			raise ValueError()


		# other type is qint as well
		qubit_array[start: start + INTEGERSIZE] = (<qint> other).qubits
		start += INTEGERSIZE


		if _controlled:
			qubit_array[2 * INTEGERSIZE: 3 * INTEGERSIZE] = (<qbool> _control_bool).qubits
			qubit_array[3 * INTEGERSIZE: 3 * INTEGERSIZE + NUMANCILLY] = ancilla
			seq = cQQ_add()
		else:
			qubit_array[2 * INTEGERSIZE: 2 * INTEGERSIZE + NUMANCILLY] = ancilla
			seq = QQ_add()

		arr = qubit_array
		run_instruction(seq, &arr[0], invert, _circuit)
		return self

	def __add__(self, other: qint | int):
		# out of place addition
		a = qint(value = self.value, bits = self.bits)
		a += other
		return a

	def __radd__(self, other: qint | int):
		# out of place addition
		a = qint(value = self.value, bits = self.bits)
		a += other
		return a

	def __iadd__(self, other: qint | int):
		# in place addition
		return self.addition_inplace(other)

	def __sub__(self, other: qint | int):
		# in place addition
		a = qint(value = self.value, bits = self.bits)
		a -= other
		return a

	def __isub__(self, other: qint | int):
		# in place addition
		return self.addition_inplace(other, invert = True)


	cdef multiplication_inplace(self, other: qint | int, ret: qint):
			global _controlled, _control_bool, qubit_array
			cdef sequence_t *seq
			cdef unsigned int[:] arr

			start = 0

			qubit_array[INTEGERSIZE: 2 * INTEGERSIZE] = self.qubits
			start += INTEGERSIZE

			if type(other) == int:
				# value is a quantum integer
				QPU_state[0].R0[0] = other
				qubit_array[: INTEGERSIZE] = (<qint> ret).qubits
				if _controlled:
					qubit_array[2 * INTEGERSIZE: 3 * INTEGERSIZE] = (<qbool> _control_bool).qubits
					qubit_array[3 * INTEGERSIZE: 3 * INTEGERSIZE + NUMANCILLY] = ancilla
					seq = cCQ_mul()
				else:
					qubit_array[2 * INTEGERSIZE: 2 * INTEGERSIZE + NUMANCILLY] = ancilla
					seq = CQ_mul()

				arr = qubit_array
				run_instruction(seq, &arr[0], False, _circuit)

				return ret

			if type(other) != qint:
				raise ValueError()

			qubit_array[start + INTEGERSIZE: start + 2 * INTEGERSIZE] = (<qint> other).qubits
			start += INTEGERSIZE

			# value is a quantum integer

			if _controlled:
				qubit_array[2 * INTEGERSIZE: 3 * INTEGERSIZE] = (<qbool> _control_bool).qubits
				qubit_array[3 * INTEGERSIZE: 3 * INTEGERSIZE + NUMANCILLY] = ancilla
				seq = cQQ_add()
			else:
				qubit_array[2 * INTEGERSIZE: 2 * INTEGERSIZE + NUMANCILLY] = ancilla
				seq = QQ_add()

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)
			return self

	def __mul__(self, other):
		a = qint(bits = self.bits)
		self.multiplication_inplace(other, a)
		return a

	def __rmul__(self, other):
		a = qint(bits = self.bits)
		self.multiplication_inplace(other, a)
		return a

	cdef and_functionality(self, other, ret):
		cdef sequence_t *seq;
		cdef unsigned int[:] arr

		qubit_array[: INTEGERSIZE] = (<qbool> ret).qubits
		qubit_array[INTEGERSIZE: 2 * INTEGERSIZE] = self.qubits
		qubit_array[2 * INTEGERSIZE: 3 * INTEGERSIZE] = (<qbool> other).qubits

		seq = qq_and_seq()

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)
		free(seq)

	def measure(self):
		return self.value

	def __and__(self, other):
		a = qbool()
		# print("and")
		# TODO: include quantum functionality
		self.and_functionality(other, a)
		return a

	def __iand__(self, other):
		a = qbool()
		print("iand")
		self.and_functionality(other, a)
		return a

	def __or__(self, other):
		global _smallest_allocated_qubit, ancilla
		a = qbool()
		cdef sequence_t *seq;
		cdef unsigned int[:] arr

		qubit_array[: INTEGERSIZE] = a.qubits
		qubit_array[INTEGERSIZE: 2 * INTEGERSIZE] = self.qubits
		qubit_array[2 * INTEGERSIZE: 3 * INTEGERSIZE] = (<qbool> other).qubits

		seq = qq_or_seq()

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)
		free(seq)
		_smallest_allocated_qubit += 1
		ancilla += 1
		return a

	def __ior__(self, other):

		return

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
		global _controlled, _control_bool, qubit_array
		cdef sequence_t *seq
		cdef unsigned int[:] arr

		if _controlled:
			qubit_array[INTEGERSIZE: 2 * INTEGERSIZE] = (<qbool> _control_bool).qubits
			qubit_array[: INTEGERSIZE] = self.qubits
			seq = cq_not_seq()
		else:
			qubit_array[: INTEGERSIZE] = self.qubits
			seq = q_not_seq()

		arr = qubit_array
		run_instruction(seq, &arr[0], False, _circuit)

		free(seq)

		# TODO: include quantum functionality
		return self

	def __getitem__(self, item: int):
		bit_list = np.zeros(INTEGERSIZE)
		bit_list[-1] = self.qubits[item]
		a = qbool(create_new = False, bit_list = bit_list)
		return a

	def __gt__(self, other):
		global _smallest_allocated_qubit, ancilla
		a = self[INTEGERSIZE - self.bits]
		self.addition_inplace(other, True)
		c = qbool()
		c = ~c

		with a:
			c = ~c

		self.addition_inplace(other, False)
		return c

	def __ge__(self, other):
		return self > other - 1

	def __lt__(self, other):
		global _smallest_allocated_qubit, ancilla
		a = self[INTEGERSIZE - self.bits]
		self.addition_inplace(other, True)
		c = qbool()
		with a:
			c = ~c

		self.addition_inplace(other, False)
		return c

	def __le__(self, other):
		return self < other + 1



cdef class qbool(qint):

	def __init__(self, value: bool = False, classical: bool = False, create_new = True, bit_list = None):
		super().__init__(value, bits = 1, classical = classical, create_new = create_new, bit_list=bit_list)
