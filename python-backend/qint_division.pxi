# qint_division.pxi - Division operations for qint class
# This file is included by quantum_language.pyx
# Do not import directly

	def __floordiv__(self, divisor):
		"""Floor division: self // divisor

		Uses restoring division algorithm (repeated subtraction).

		Parameters
		----------
		divisor : int or qint
			Divisor.

		Returns
		-------
		qint
			Quotient.

		Raises
		------
		ZeroDivisionError
			If divisor is zero (classical only).
		TypeError
			If divisor is not int or qint.

		Examples
		--------
		>>> a = qint(17, width=8)
		>>> q = a // 5
		>>> # q represents |3>

		Notes
		-----
		Classical divisor: O(width) circuit via bit-level algorithm.
		Quantum divisor: O(quotient) circuit via repeated subtraction.
		"""
		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Division by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			# Allocate quotient and remainder
			quotient = qint(0, width=self.bits)
			remainder = qint(0, width=self.bits)

			# Copy self to remainder via XOR (remainder starts at 0)
			remainder ^= self

			# Special case: power of 2 division (just right shift)
			# For Phase 7, use general algorithm - optimization later

			# Restoring division: try subtracting divisor * 2^bit for each bit position
			for bit_pos in range(self.bits - 1, -1, -1):
				# Try subtracting divisor << bit_pos
				trial_value = divisor << bit_pos

				# Check if remainder >= trial_value
				can_subtract = remainder >= trial_value

				# Conditional subtraction and quotient bit set
				with can_subtract:
					remainder -= trial_value
					quotient += (1 << bit_pos)

			return quotient

		elif type(divisor) == qint:
			# Quantum divisor - delegate to quantum division method
			return self._floordiv_quantum(divisor)
		else:
			raise TypeError("Divisor must be int or qint")

	def _floordiv_quantum(self, divisor: qint):
		"""Floor division with quantum divisor: self // divisor

		Uses repeated quantum comparison and conditional subtraction.
		Per arXiv:1809.09732, implements restoring division algorithm.

		Args:
			divisor: qint divisor

		Returns:
			qint quotient

		Note:
			For quantum divisor, we cannot use bit-level algorithm
			(shifting quantum values is expensive). Instead, we use
			repeated subtraction: while remainder >= divisor, subtract.
			This creates a circuit with O(quotient) iterations.
		"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		# Allocate quotient and remainder
		quotient = qint(0, width=comp_bits)
		remainder = qint(0, width=comp_bits)

		# Copy self to remainder via XOR (remainder starts at 0)
		remainder ^= self

		# Repeated conditional subtraction
		# Maximum possible quotient is 2^comp_bits - 1
		# We need to iterate enough times to complete division
		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			# Check if remainder >= divisor
			can_subtract = remainder >= divisor

			# Conditional subtraction and increment
			with can_subtract:
				remainder -= divisor
				quotient += 1

		return quotient

	def __mod__(self, divisor):
		"""Modulo operation: self % divisor

		Computes remainder via restoring division.

		Parameters
		----------
		divisor : int or qint
			Divisor.

		Returns
		-------
		qint
			Remainder.

		Raises
		------
		ZeroDivisionError
			If divisor is zero (classical only).
		TypeError
			If divisor is not int or qint.

		Examples
		--------
		>>> a = qint(17, width=8)
		>>> r = a % 5
		>>> # r represents |2>
		"""
		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Modulo by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			# Allocate remainder
			remainder = qint(0, width=self.bits)

			# Copy self to remainder via XOR (remainder starts at 0)
			remainder ^= self

			# Efficient modulo: just compute remainder, no quotient needed
			# Use same restoring division but only track remainder
			for bit_pos in range(self.bits - 1, -1, -1):
				trial_value = divisor << bit_pos

				# Check if remainder >= trial_value
				can_subtract = remainder >= trial_value

				# Conditional subtraction (no quotient tracking)
				with can_subtract:
					remainder -= trial_value

			return remainder

		elif type(divisor) == qint:
			# Quantum divisor - use quantum modulo
			return self._mod_quantum(divisor)
		else:
			raise TypeError("Divisor must be int or qint")

	def _mod_quantum(self, divisor: qint):
		"""Modulo with quantum divisor: self % divisor

		Args:
			divisor: qint divisor

		Returns:
			qint remainder
		"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		# Allocate remainder
		remainder = qint(0, width=comp_bits)

		# Copy self to remainder via XOR
		remainder ^= self

		# Repeated conditional subtraction (same as division but no quotient)
		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			# Check if remainder >= divisor
			can_subtract = remainder >= divisor

			# Conditional subtraction
			with can_subtract:
				remainder -= divisor

		return remainder

	def __divmod__(self, divisor):
		"""Divmod operation: divmod(self, divisor)

		Computes both quotient and remainder in single pass.

		Parameters
		----------
		divisor : int or qint
			Divisor.

		Returns
		-------
		tuple of qint
			(quotient, remainder).

		Raises
		------
		ZeroDivisionError
			If divisor is zero (classical only).
		TypeError
			If divisor is not int or qint.

		Examples
		--------
		>>> a = qint(17, width=8)
		>>> q, r = divmod(a, 5)
		>>> # q represents |3>, r represents |2>
		"""
		# Classical divisor case
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Divmod by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")

			# Allocate quotient and remainder
			quotient = qint(0, width=self.bits)
			remainder = qint(0, width=self.bits)

			# Copy self to remainder via XOR
			remainder ^= self

			# Restoring division: compute both quotient and remainder
			for bit_pos in range(self.bits - 1, -1, -1):
				trial_value = divisor << bit_pos

				# Check if remainder >= trial_value
				can_subtract = remainder >= trial_value

				# Conditional subtraction and quotient bit set
				with can_subtract:
					remainder -= trial_value
					quotient += (1 << bit_pos)

			return (quotient, remainder)

		elif type(divisor) == qint:
			# Quantum divisor - compute both
			return self._divmod_quantum(divisor)
		else:
			raise TypeError("Divisor must be int or qint")

	def _divmod_quantum(self, divisor: qint):
		"""Divmod with quantum divisor: divmod(self, divisor)

		Args:
			divisor: qint divisor

		Returns:
			tuple (quotient, remainder) where both are qint
		"""
		cdef int comp_bits = max(self.bits, (<qint>divisor).bits)

		# Allocate quotient and remainder
		quotient = qint(0, width=comp_bits)
		remainder = qint(0, width=comp_bits)

		# Copy self to remainder via XOR
		remainder ^= self

		# Repeated conditional subtraction (compute both quotient and remainder)
		max_iterations = (1 << comp_bits)

		for _ in range(max_iterations):
			# Check if remainder >= divisor
			can_subtract = remainder >= divisor

			# Conditional subtraction and increment
			with can_subtract:
				remainder -= divisor
				quotient += 1

		return (quotient, remainder)

	def __rfloordiv__(self, other):
		"""Reverse floor division: other // self

		Parameters
		----------
		other : int
			Dividend (numerator).

		Returns
		-------
		qint
			Quotient.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> q = 17 // a
		>>> # q represents |3>
		"""
		# Convert int to qint and perform division
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint // self
		else:
			# For qint // qint, __floordiv__ should be called, not __rfloordiv__
			raise TypeError("Reverse floor division requires int divisor")

	def __rmod__(self, other):
		"""Reverse modulo: other % self

		Parameters
		----------
		other : int
			Dividend (numerator).

		Returns
		-------
		qint
			Remainder.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> r = 17 % a
		>>> # r represents |2>
		"""
		# Convert int to qint and perform modulo
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint % self
		else:
			# For qint % qint, __mod__ should be called, not __rmod__
			raise TypeError("Reverse modulo requires int divisor")

	def __rdivmod__(self, other):
		"""Reverse divmod: divmod(other, self)

		Parameters
		----------
		other : int
			Dividend (numerator).

		Returns
		-------
		tuple of qint
			(quotient, remainder).

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> q, r = divmod(17, a)
		>>> # q represents |3>, r represents |2>
		"""
		# Convert int to qint and perform divmod
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return divmod(other_qint, self)
		else:
			# For qint divmod qint, __divmod__ should be called
			raise TypeError("Reverse divmod requires int divisor")

