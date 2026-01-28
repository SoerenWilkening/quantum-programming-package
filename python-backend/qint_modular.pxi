# qint_modular.pxi - qint_mod class for modular arithmetic
# This file is included by quantum_language.pyx
# Do not import directly

cdef class qint_mod(qint):
	"""Quantum integer with modular arithmetic.

	Modulus N is classical (Python int), known at circuit generation time.
	All operations automatically reduce result mod N.

	Parameters
	----------
	value : int, optional
		Initial value (reduced mod N classically before encoding).
	N : int
		Modulus (required, must be positive).
	width : int, optional
		Bit width (default: N.bit_length()).

	Attributes
	----------
	modulus : int
		The classical modulus N (read-only property).
	width : int
		Bit width (inherited from qint).

	Examples
	--------
	>>> x = qint_mod(5, N=17)
	>>> y = qint_mod(15, N=17)
	>>> z = x + y  # z = 20 mod 17 = 3
	>>> z.modulus
	17

	Notes
	-----
	Used for modular exponentiation in Shor's algorithm and other
	number-theoretic quantum algorithms.
	"""
	cdef int _modulus

	def __init__(self, value=0, N=None, width=None):
		"""Create quantum integer with classical modulus N.

		Parameters
		----------
		value : int, optional
			Initial value (reduced mod N before encoding, default 0).
		N : int
			Modulus (required, must be positive).
		width : int, optional
			Bit width (default: N.bit_length()).

		Raises
		------
		ValueError
			If N is None, non-positive, or not an integer.

		Examples
		--------
		>>> x = qint_mod(25, N=17)  # Creates qint with value 25 % 17 = 8
		>>> x.modulus
		17
		"""
		if N is None or not isinstance(N, int) or N <= 0:
			raise ValueError("Modulus N must be positive integer")

		# Default width: enough bits to represent N
		if width is None:
			width = N.bit_length()

		# Reduce value mod N classically (before quantum encoding)
		reduced_value = value % N

		# Initialize as regular qint
		super().__init__(reduced_value, width=width)

		# Store modulus
		self._modulus = N

	@property
	def modulus(self):
		"""Get the modulus N (read-only).

		Returns
		-------
		int
			The classical modulus N.

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> x.modulus
		17
		"""
		return self._modulus

	def __repr__(self):
		return f"qint_mod(modulus={self._modulus}, width={self.bits})"

	cdef _reduce_mod(self, qint value):
		"""Reduce value mod N via conditional subtraction.

		Uses quantum comparison and conditional subtraction.
		Classical N enables computing max iterations needed.
		"""
		# Max possible value before reduction
		max_val = 1 << value.bits

		# Max times we might need to subtract N
		max_subtractions = (max_val // self._modulus) + 1

		# Iteratively subtract N while value >= N
		# Number of iterations is log2(max_subtractions)
		iterations = max_subtractions.bit_length()

		for _ in range(iterations):
			# Compare: is value >= N?
			cmp = value >= self._modulus

			# Conditional subtraction
			with cmp:
				value -= self._modulus

		return value

	cdef qint_mod _wrap_result(self, qint result):
		"""Wrap plain qint result into qint_mod with same modulus."""
		# Create new qint_mod using existing qubits
		cdef qint_mod wrapped = qint_mod.__new__(qint_mod)

		# Manually copy qint fields (avoiding __init__ which would allocate qubits)
		wrapped.counter = result.counter
		wrapped.bits = result.bits
		wrapped.value = result.value
		wrapped.qubits = result.qubits
		wrapped.allocated_qubits = result.allocated_qubits
		wrapped.allocated_start = result.allocated_start

		# Set modulus (cdef attribute)
		wrapped._modulus = self._modulus

		return wrapped

	def __add__(self, other):
		"""Modular addition: (self + other) mod N

		Parameters
		----------
		other : qint_mod or int
			Value to add.

		Returns
		-------
		qint_mod
			Result reduced mod N.

		Raises
		------
		ValueError
			If other is qint_mod with different modulus.

		Examples
		--------
		>>> x = qint_mod(15, N=17)
		>>> y = qint_mod(5, N=17)
		>>> z = x + y  # (15 + 5) mod 17 = 3
		"""
		# Check modulus compatibility
		if isinstance(other, qint_mod):
			if (<qint_mod>other)._modulus != self._modulus:
				raise ValueError(
					f"Moduli must match: {self._modulus} != {(<qint_mod>other)._modulus}"
				)

		# Perform regular addition (using parent class)
		sum_val = qint.__add__(self, other)

		# Reduce mod N
		reduced = self._reduce_mod(sum_val)

		# Wrap result
		return self._wrap_result(reduced)

	def __sub__(self, other):
		"""Modular subtraction: (self - other) mod N

		Handles negative results by adding N to ensure [0, N) range.

		Parameters
		----------
		other : qint_mod or int
			Value to subtract.

		Returns
		-------
		qint_mod
			Result reduced mod N.

		Raises
		------
		ValueError
			If other is qint_mod with different modulus.

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> y = qint_mod(10, N=17)
		>>> z = x - y  # (5 - 10) mod 17 = 12
		"""
		if isinstance(other, qint_mod):
			if (<qint_mod>other)._modulus != self._modulus:
				raise ValueError(
					f"Moduli must match: {self._modulus} != {(<qint_mod>other)._modulus}"
				)

		# Perform regular subtraction
		diff = qint.__sub__(self, other)

		# If negative (MSB set), add N to make positive
		# Check sign via comparison or MSB
		is_negative = diff < 0
		with is_negative:
			diff += self._modulus

		# Reduce to ensure in range [0, N)
		reduced = self._reduce_mod(diff)

		return self._wrap_result(reduced)

	def __mul__(self, other):
		"""Modular multiplication: (self * other) mod N

		Parameters
		----------
		other : qint_mod or int
			Value to multiply by.

		Returns
		-------
		qint_mod
			Result reduced mod N.

		Raises
		------
		NotImplementedError
			If other is qint_mod (qint_mod * qint_mod not yet supported).
		ValueError
			If other is qint_mod with different modulus.

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> z = x * 7  # (5 * 7) mod 17 = 1
		"""
		# Check for qint_mod * qint_mod (not supported - causes C-layer segfault)
		if isinstance(other, qint_mod):
			raise NotImplementedError(
				"qint_mod * qint_mod multiplication is not yet supported. "
				"Use qint_mod * int instead (e.g., x * 5 instead of x * y)."
			)

		# Perform regular multiplication (qint_mod * int)
		product = qint.__mul__(self, other)

		# Reduce mod N (product may be much larger than N)
		reduced = self._reduce_mod(product)

		return self._wrap_result(reduced)

	def __iadd__(self, other):
		"""In-place modular addition: self += other mod N

		Parameters
		----------
		other : qint_mod or int
			Value to add.

		Returns
		-------
		qint_mod
			Self (with swapped qubit references).

		Examples
		--------
		>>> x = qint_mod(15, N=17)
		>>> x += 5  # (15 + 5) mod 17 = 3
		"""
		result = self + other
		cdef qint_mod result_mod = <qint_mod>result
		self.qubits, result_mod.qubits = result_mod.qubits, self.qubits
		self.allocated_start, result_mod.allocated_start = result_mod.allocated_start, self.allocated_start
		self.bits = result_mod.bits
		return self

	def __isub__(self, other):
		"""In-place modular subtraction: self -= other mod N

		Parameters
		----------
		other : qint_mod or int
			Value to subtract.

		Returns
		-------
		qint_mod
			Self (with swapped qubit references).

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> x -= 10  # (5 - 10) mod 17 = 12
		"""
		result = self - other
		cdef qint_mod result_mod = <qint_mod>result
		self.qubits, result_mod.qubits = result_mod.qubits, self.qubits
		self.allocated_start, result_mod.allocated_start = result_mod.allocated_start, self.allocated_start
		self.bits = result_mod.bits
		return self

	def __imul__(self, other):
		"""In-place modular multiplication: self *= other mod N

		Parameters
		----------
		other : qint_mod or int
			Value to multiply by.

		Returns
		-------
		qint_mod
			Self (with swapped qubit references).

		Examples
		--------
		>>> x = qint_mod(5, N=17)
		>>> x *= 7  # (5 * 7) mod 17 = 1
		"""
		result = self * other
		cdef qint_mod result_mod = <qint_mod>result
		self.qubits, result_mod.qubits = result_mod.qubits, self.qubits
		self.allocated_start, result_mod.allocated_start = result_mod.allocated_start, self.allocated_start
		self.bits = result_mod.bits
		return self


