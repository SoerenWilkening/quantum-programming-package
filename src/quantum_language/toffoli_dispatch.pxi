# ====================================================================
# TOFFOLI ADDITION DISPATCH
# Ported from hot_path_add_toffoli.c (Phase 74) to Cython.
# Handles CLA vs RCA, BK vs KS, Clifford+T, and two's complement
# CLA subtraction dispatch for Toffoli-mode addition.
# ====================================================================

# Clifford+T sequence caches (module-level, like C statics)
# Each cache maps width -> const sequence_t* (lazily populated as int)
_clifft_cache_qq = {}
_clifft_cache_cqq = {}
_clifft_cache_cq_inc = {}
_clifft_cache_ccq_inc = {}
_clifft_cache_cla_qq = {}
_clifft_cache_cla_cqq = {}
_clifft_cache_cla_cq_inc = {}
_clifft_cache_cla_ccq_inc = {}

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline int _ks_cla_ancilla_estimate(int bits):
	cdef int log_n = 0
	cdef int tmp = bits
	while tmp > 1:
		log_n += 1
		tmp = (tmp + 1) >> 1
	return (bits - 1) + (bits - 1) * log_n

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline int _compute_cla_ancilla_count(circuit_s *circ, int bits):
	if circ.qubit_saving:
		return bk_cla_ancilla_count(bits)
	else:
		return _ks_cla_ancilla_estimate(bits)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef _toffoli_qq_uncont(circuit_s *circ, const unsigned int *self_qubits,
                        int self_bits, const unsigned int *other_qubits,
                        int other_bits, int invert, int result_bits):
	cdef unsigned int tqa[256]
	cdef sequence_t *toff_seq
	cdef const sequence_t *cached_seq
	cdef int i
	cdef int cla_ancilla_count
	cdef unsigned int cla_ancilla, ancilla_qubit
	cdef unsigned int ct_ancilla
	cdef qubit_allocator_t *alloc = circuit_get_allocator(circ)
	cdef unsigned int inc_qa[256]
	cdef unsigned int inc_ancilla
	cdef sequence_t *inc_seq
	cdef gate_t xg

	if result_bits == 1:
		tqa[0] = self_qubits[0]
		tqa[1] = other_qubits[0]
		toff_seq = toffoli_QQ_add(result_bits)
		if toff_seq == NULL:
			return
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
		return

	# n >= 2: swap register positions for CDKM adder layout
	for i in range(other_bits):
		tqa[i] = other_qubits[i]
	for i in range(self_bits):
		tqa[result_bits + i] = self_qubits[i]

	# Clifford+T hardcoded dispatch (toffoli_decompose=1, widths 1-8)
	if circ.toffoli_decompose and result_bits <= TOFFOLI_HARDCODED_MAX_WIDTH:
		# CLA Clifford+T path (forward only)
		if not invert and circ.cla_override == 0 and result_bits >= circ.tradeoff_auto_threshold:
			cla_ancilla_count = _compute_cla_ancilla_count(circ, result_bits)
			cla_ancilla = allocator_alloc(alloc, cla_ancilla_count, True)
			if cla_ancilla != <unsigned int>(-1):
				for i in range(cla_ancilla_count):
					tqa[2 * result_bits + i] = cla_ancilla + i
				if result_bits not in _clifft_cache_cla_qq:
					cached_seq = get_hardcoded_toffoli_clifft_cla_QQ_add(result_bits)
					if cached_seq != NULL:
						_clifft_cache_cla_qq[result_bits] = <unsigned long long>cached_seq
				if result_bits in _clifft_cache_cla_qq:
					cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_cla_qq[result_bits]
					run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ, 0)
					allocator_free(alloc, cla_ancilla, cla_ancilla_count)
					return
				allocator_free(alloc, cla_ancilla, cla_ancilla_count)
		# RCA Clifford+T path
		ct_ancilla = allocator_alloc(alloc, 1, True)
		if ct_ancilla != <unsigned int>(-1):
			tqa[2 * result_bits] = ct_ancilla
			if result_bits not in _clifft_cache_qq:
				cached_seq = get_hardcoded_toffoli_clifft_QQ_add(result_bits)
				if cached_seq != NULL:
					_clifft_cache_qq[result_bits] = <unsigned long long>cached_seq
			if result_bits in _clifft_cache_qq:
				cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_qq[result_bits]
				run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ, 0)
				allocator_free(alloc, ct_ancilla, 1)
				return
			allocator_free(alloc, ct_ancilla, 1)

	# Two's complement CLA subtraction for min_depth mode
	if invert and circ.tradeoff_min_depth and circ.cla_override == 0 and result_bits >= circ.tradeoff_auto_threshold:
		cla_ancilla_count = _compute_cla_ancilla_count(circ, result_bits)
		cla_ancilla = allocator_alloc(alloc, cla_ancilla_count, True)
		if cla_ancilla != <unsigned int>(-1):
			for i in range(other_bits):
				memset(&xg, 0, sizeof(gate_t))
				gate_x(&xg, other_qubits[i])
				add_gate(<circuit_t*>circ, &xg)
			for i in range(cla_ancilla_count):
				tqa[2 * result_bits + i] = cla_ancilla + i
			if circ.qubit_saving:
				toff_seq = toffoli_QQ_add_bk(result_bits)
			else:
				toff_seq = toffoli_QQ_add_ks(result_bits)
			if toff_seq != NULL:
				run_instruction(toff_seq, tqa, 0, <circuit_t*>circ, 0)
				allocator_free(alloc, cla_ancilla, cla_ancilla_count)
				inc_ancilla = allocator_alloc(alloc, self_bits + 1, True)
				if inc_ancilla != <unsigned int>(-1):
					for i in range(self_bits):
						inc_qa[i] = inc_ancilla + i
					for i in range(self_bits):
						inc_qa[self_bits + i] = self_qubits[i]
					inc_qa[2 * self_bits] = inc_ancilla + self_bits
					inc_seq = toffoli_CQ_add(self_bits, 1)
					if inc_seq != NULL:
						run_instruction(inc_seq, inc_qa, 0, <circuit_t*>circ, 0)
						toffoli_sequence_free(inc_seq)
					allocator_free(alloc, inc_ancilla, self_bits + 1)
				for i in range(other_bits):
					memset(&xg, 0, sizeof(gate_t))
					gate_x(&xg, other_qubits[i])
					add_gate(<circuit_t*>circ, &xg)
				return
			allocator_free(alloc, cla_ancilla, cla_ancilla_count)
			for i in range(other_bits):
				memset(&xg, 0, sizeof(gate_t))
				gate_x(&xg, other_qubits[i])
				add_gate(<circuit_t*>circ, &xg)

	# CLA dispatch: forward only
	if not invert and circ.cla_override == 0 and result_bits >= circ.tradeoff_auto_threshold:
		cla_ancilla_count = _compute_cla_ancilla_count(circ, result_bits)
		cla_ancilla = allocator_alloc(alloc, cla_ancilla_count, True)
		if cla_ancilla != <unsigned int>(-1):
			for i in range(cla_ancilla_count):
				tqa[2 * result_bits + i] = cla_ancilla + i
			if circ.qubit_saving:
				toff_seq = toffoli_QQ_add_bk(result_bits)
			else:
				toff_seq = toffoli_QQ_add_ks(result_bits)
			if toff_seq != NULL:
				run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
				allocator_free(alloc, cla_ancilla, cla_ancilla_count)
				return
			allocator_free(alloc, cla_ancilla, cla_ancilla_count)

	# RCA (CDKM) path: 1 ancilla qubit
	ancilla_qubit = allocator_alloc(alloc, 1, True)
	if ancilla_qubit == <unsigned int>(-1):
		return
	tqa[2 * result_bits] = ancilla_qubit
	toff_seq = toffoli_QQ_add(result_bits)
	if toff_seq == NULL:
		allocator_free(alloc, ancilla_qubit, 1)
		return
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
	allocator_free(alloc, ancilla_qubit, 1)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef _toffoli_qq_cont(circuit_s *circ, const unsigned int *self_qubits,
                      int self_bits, const unsigned int *other_qubits,
                      int other_bits, int invert,
                      unsigned int control_qubit, int result_bits):
	cdef unsigned int tqa[256]
	cdef sequence_t *toff_seq
	cdef const sequence_t *cached_seq
	cdef int i
	cdef int cla_ancilla_count
	cdef unsigned int cla_ancilla, ancilla_qubit
	cdef unsigned int ct_ancilla
	cdef qubit_allocator_t *alloc = circuit_get_allocator(circ)
	cdef unsigned int inc_qa[256]
	cdef unsigned int inc_ancilla
	cdef sequence_t *inc_seq
	cdef gate_t cxg

	if result_bits == 1:
		tqa[0] = self_qubits[0]
		tqa[1] = other_qubits[0]
		tqa[2] = control_qubit

		if circ.toffoli_decompose:
			if 1 not in _clifft_cache_cqq:
				cached_seq = get_hardcoded_toffoli_clifft_cQQ_add(1)
				if cached_seq != NULL:
					_clifft_cache_cqq[1] = <unsigned long long>cached_seq
			if 1 in _clifft_cache_cqq:
				cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_cqq[1]
				run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ, 0)
				return

		toff_seq = toffoli_cQQ_add(result_bits)
		if toff_seq == NULL:
			return
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
		return

	# n >= 2: swap registers + ancilla + control
	for i in range(other_bits):
		tqa[i] = other_qubits[i]
	for i in range(self_bits):
		tqa[result_bits + i] = self_qubits[i]

	# Clifford+T hardcoded dispatch for controlled QQ
	if circ.toffoli_decompose and result_bits <= TOFFOLI_HARDCODED_MAX_WIDTH:
		# Controlled CLA Clifford+T path (forward only)
		if not invert and circ.cla_override == 0 and result_bits >= circ.tradeoff_auto_threshold:
			cla_ancilla_count = _compute_cla_ancilla_count(circ, result_bits)
			cla_ancilla = allocator_alloc(alloc, cla_ancilla_count + 1, True)
			if cla_ancilla != <unsigned int>(-1):
				for i in range(cla_ancilla_count):
					tqa[2 * result_bits + i] = cla_ancilla + i
				tqa[2 * result_bits + cla_ancilla_count] = control_qubit
				tqa[2 * result_bits + cla_ancilla_count + 1] = cla_ancilla + cla_ancilla_count
				if result_bits not in _clifft_cache_cla_cqq:
					cached_seq = get_hardcoded_toffoli_clifft_cla_cQQ_add(result_bits)
					if cached_seq != NULL:
						_clifft_cache_cla_cqq[result_bits] = <unsigned long long>cached_seq
				if result_bits in _clifft_cache_cla_cqq:
					cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_cla_cqq[result_bits]
					run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ, 0)
					allocator_free(alloc, cla_ancilla, cla_ancilla_count + 1)
					return
				allocator_free(alloc, cla_ancilla, cla_ancilla_count + 1)
		# Controlled RCA Clifford+T path
		ct_ancilla = allocator_alloc(alloc, 2, True)
		if ct_ancilla != <unsigned int>(-1):
			tqa[2 * result_bits] = ct_ancilla
			tqa[2 * result_bits + 1] = control_qubit
			tqa[2 * result_bits + 2] = ct_ancilla + 1
			if result_bits not in _clifft_cache_cqq:
				cached_seq = get_hardcoded_toffoli_clifft_cQQ_add(result_bits)
				if cached_seq != NULL:
					_clifft_cache_cqq[result_bits] = <unsigned long long>cached_seq
			if result_bits in _clifft_cache_cqq:
				cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_cqq[result_bits]
				run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ, 0)
				allocator_free(alloc, ct_ancilla, 2)
				return
			allocator_free(alloc, ct_ancilla, 2)

	# Controlled two's complement CLA subtraction for min_depth mode
	if invert and circ.tradeoff_min_depth and circ.cla_override == 0 and result_bits >= circ.tradeoff_auto_threshold:
		cla_ancilla_count = _compute_cla_ancilla_count(circ, result_bits)
		cla_ancilla = allocator_alloc(alloc, cla_ancilla_count + 1, True)
		if cla_ancilla != <unsigned int>(-1):
			for i in range(other_bits):
				memset(&cxg, 0, sizeof(gate_t))
				gate_cx(&cxg, other_qubits[i], control_qubit)
				add_gate(<circuit_t*>circ, &cxg)
			for i in range(cla_ancilla_count):
				tqa[2 * result_bits + i] = cla_ancilla + i
			tqa[2 * result_bits + cla_ancilla_count] = control_qubit
			tqa[2 * result_bits + cla_ancilla_count + 1] = cla_ancilla + cla_ancilla_count
			if circ.qubit_saving:
				toff_seq = toffoli_cQQ_add_bk(result_bits)
			else:
				toff_seq = toffoli_cQQ_add_ks(result_bits)
			if toff_seq != NULL:
				run_instruction(toff_seq, tqa, 0, <circuit_t*>circ, 0)
				allocator_free(alloc, cla_ancilla, cla_ancilla_count + 1)
				inc_ancilla = allocator_alloc(alloc, self_bits + 2, True)
				if inc_ancilla != <unsigned int>(-1):
					for i in range(self_bits):
						inc_qa[i] = inc_ancilla + i
					for i in range(self_bits):
						inc_qa[self_bits + i] = self_qubits[i]
					inc_qa[2 * self_bits] = inc_ancilla + self_bits
					inc_qa[2 * self_bits + 1] = control_qubit
					inc_qa[2 * self_bits + 2] = inc_ancilla + self_bits + 1
					inc_seq = toffoli_cCQ_add(self_bits, 1)
					if inc_seq != NULL:
						run_instruction(inc_seq, inc_qa, 0, <circuit_t*>circ, 0)
						toffoli_sequence_free(inc_seq)
					allocator_free(alloc, inc_ancilla, self_bits + 2)
				for i in range(other_bits):
					memset(&cxg, 0, sizeof(gate_t))
					gate_cx(&cxg, other_qubits[i], control_qubit)
					add_gate(<circuit_t*>circ, &cxg)
				return
			allocator_free(alloc, cla_ancilla, cla_ancilla_count + 1)
			for i in range(other_bits):
				memset(&cxg, 0, sizeof(gate_t))
				gate_cx(&cxg, other_qubits[i], control_qubit)
				add_gate(<circuit_t*>circ, &cxg)

	# Controlled CLA dispatch: forward only
	if not invert and circ.cla_override == 0 and result_bits >= circ.tradeoff_auto_threshold:
		cla_ancilla_count = _compute_cla_ancilla_count(circ, result_bits)
		cla_ancilla = allocator_alloc(alloc, cla_ancilla_count + 1, True)
		if cla_ancilla != <unsigned int>(-1):
			for i in range(cla_ancilla_count):
				tqa[2 * result_bits + i] = cla_ancilla + i
			tqa[2 * result_bits + cla_ancilla_count] = control_qubit
			tqa[2 * result_bits + cla_ancilla_count + 1] = cla_ancilla + cla_ancilla_count
			if circ.qubit_saving:
				toff_seq = toffoli_cQQ_add_bk(result_bits)
			else:
				toff_seq = toffoli_cQQ_add_ks(result_bits)
			if toff_seq != NULL:
				run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
				allocator_free(alloc, cla_ancilla, cla_ancilla_count + 1)
				return
			allocator_free(alloc, cla_ancilla, cla_ancilla_count + 1)

	# Controlled RCA (CDKM) path: 1 carry ancilla + 1 AND-ancilla
	ancilla_qubit = allocator_alloc(alloc, 2, True)
	if ancilla_qubit == <unsigned int>(-1):
		return
	tqa[2 * result_bits] = ancilla_qubit
	tqa[2 * result_bits + 1] = control_qubit
	tqa[2 * result_bits + 2] = ancilla_qubit + 1
	toff_seq = toffoli_cQQ_add(result_bits)
	if toff_seq == NULL:
		allocator_free(alloc, ancilla_qubit, 2)
		return
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
	allocator_free(alloc, ancilla_qubit, 2)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef _toffoli_dispatch_qq(circuit_s *circ, const unsigned int *self_qubits,
                          int self_bits, const unsigned int *other_qubits,
                          int other_bits, int invert, int controlled,
                          unsigned int control_qubit, int result_bits):
	if controlled:
		_toffoli_qq_cont(circ, self_qubits, self_bits, other_qubits, other_bits,
		                 invert, control_qubit, result_bits)
	else:
		_toffoli_qq_uncont(circ, self_qubits, self_bits, other_qubits, other_bits,
		                   invert, result_bits)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef _toffoli_cq_uncont(circuit_s *circ, const unsigned int *self_qubits,
                        int self_bits, int64_t classical_value, int invert):
	cdef sequence_t *toff_seq
	cdef const sequence_t *cached_seq
	cdef sequence_t *copy_seq
	cdef int i
	cdef int cla_ancilla_count, total_ancilla
	cdef unsigned int cq_cla_ancilla, ct_temp, temp_start
	cdef unsigned int tqa[256]
	cdef qubit_allocator_t *alloc = circuit_get_allocator(circ)
	cdef int64_t negated

	if self_bits == 1:
		tqa[0] = self_qubits[0]
		toff_seq = toffoli_CQ_add(self_bits, classical_value)
		if toff_seq == NULL:
			return
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
		toffoli_sequence_free(toff_seq)
		return

	# Clifford+T CQ increment dispatch (value==1, widths 1-8)
	if circ.toffoli_decompose and classical_value == 1 and self_bits <= TOFFOLI_HARDCODED_MAX_WIDTH:
		# CLA Clifford+T CQ increment (forward only)
		if not invert and circ.cla_override == 0 and self_bits >= circ.tradeoff_auto_threshold:
			cla_ancilla_count = _compute_cla_ancilla_count(circ, self_bits)
			total_ancilla = self_bits + cla_ancilla_count
			cq_cla_ancilla = allocator_alloc(alloc, total_ancilla, True)
			if cq_cla_ancilla != <unsigned int>(-1):
				for i in range(self_bits):
					tqa[i] = cq_cla_ancilla + i
				for i in range(self_bits):
					tqa[self_bits + i] = self_qubits[i]
				for i in range(cla_ancilla_count):
					tqa[2 * self_bits + i] = cq_cla_ancilla + self_bits + i
				if self_bits not in _clifft_cache_cla_cq_inc:
					cached_seq = get_hardcoded_toffoli_clifft_cla_CQ_inc(self_bits)
					if cached_seq != NULL:
						_clifft_cache_cla_cq_inc[self_bits] = <unsigned long long>cached_seq
				if self_bits in _clifft_cache_cla_cq_inc:
					cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_cla_cq_inc[self_bits]
					copy_seq = copy_hardcoded_sequence(cached_seq)
					if copy_seq != NULL:
						run_instruction(copy_seq, tqa, invert, <circuit_t*>circ, 0)
						toffoli_sequence_free(copy_seq)
						allocator_free(alloc, cq_cla_ancilla, total_ancilla)
						return
				allocator_free(alloc, cq_cla_ancilla, total_ancilla)
		# RCA Clifford+T CQ increment
		ct_temp = allocator_alloc(alloc, self_bits + 1, True)
		if ct_temp != <unsigned int>(-1):
			for i in range(self_bits):
				tqa[i] = ct_temp + i
			for i in range(self_bits):
				tqa[self_bits + i] = self_qubits[i]
			tqa[2 * self_bits] = ct_temp + self_bits
			if self_bits not in _clifft_cache_cq_inc:
				cached_seq = get_hardcoded_toffoli_clifft_CQ_inc(self_bits)
				if cached_seq != NULL:
					_clifft_cache_cq_inc[self_bits] = <unsigned long long>cached_seq
			if self_bits in _clifft_cache_cq_inc:
				cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_cq_inc[self_bits]
				copy_seq = copy_hardcoded_sequence(cached_seq)
				if copy_seq != NULL:
					run_instruction(copy_seq, tqa, invert, <circuit_t*>circ, 0)
					toffoli_sequence_free(copy_seq)
					allocator_free(alloc, ct_temp, self_bits + 1)
					return
			allocator_free(alloc, ct_temp, self_bits + 1)

	# CQ two's complement CLA subtraction for min_depth mode
	if invert and circ.tradeoff_min_depth and circ.cla_override == 0 and self_bits >= circ.tradeoff_auto_threshold:
		negated = (<int64_t>1 << self_bits) - classical_value
		cla_ancilla_count = _compute_cla_ancilla_count(circ, self_bits)
		total_ancilla = self_bits + cla_ancilla_count
		cq_cla_ancilla = allocator_alloc(alloc, total_ancilla, True)
		if cq_cla_ancilla != <unsigned int>(-1):
			for i in range(self_bits):
				tqa[i] = cq_cla_ancilla + i
			for i in range(self_bits):
				tqa[self_bits + i] = self_qubits[i]
			for i in range(cla_ancilla_count):
				tqa[2 * self_bits + i] = cq_cla_ancilla + self_bits + i
			if circ.qubit_saving:
				toff_seq = toffoli_CQ_add_bk(self_bits, negated)
			else:
				toff_seq = toffoli_CQ_add_ks(self_bits, negated)
			if toff_seq != NULL:
				run_instruction(toff_seq, tqa, 0, <circuit_t*>circ, 0)
				toffoli_sequence_free(toff_seq)
				allocator_free(alloc, cq_cla_ancilla, total_ancilla)
				return
			allocator_free(alloc, cq_cla_ancilla, total_ancilla)

	# CQ CLA dispatch: forward only
	if not invert and circ.cla_override == 0 and self_bits >= circ.tradeoff_auto_threshold:
		cla_ancilla_count = _compute_cla_ancilla_count(circ, self_bits)
		total_ancilla = self_bits + cla_ancilla_count
		cq_cla_ancilla = allocator_alloc(alloc, total_ancilla, True)
		if cq_cla_ancilla != <unsigned int>(-1):
			for i in range(self_bits):
				tqa[i] = cq_cla_ancilla + i
			for i in range(self_bits):
				tqa[self_bits + i] = self_qubits[i]
			for i in range(cla_ancilla_count):
				tqa[2 * self_bits + i] = cq_cla_ancilla + self_bits + i
			if circ.qubit_saving:
				toff_seq = toffoli_CQ_add_bk(self_bits, classical_value)
			else:
				toff_seq = toffoli_CQ_add_ks(self_bits, classical_value)
			if toff_seq != NULL:
				run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
				toffoli_sequence_free(toff_seq)
				allocator_free(alloc, cq_cla_ancilla, total_ancilla)
				return
			allocator_free(alloc, cq_cla_ancilla, total_ancilla)

	# RCA (CDKM) CQ path: self_bits + 1 ancilla
	temp_start = allocator_alloc(alloc, self_bits + 1, True)
	if temp_start == <unsigned int>(-1):
		return
	for i in range(self_bits):
		tqa[i] = temp_start + i
	for i in range(self_bits):
		tqa[self_bits + i] = self_qubits[i]
	tqa[2 * self_bits] = temp_start + self_bits
	toff_seq = toffoli_CQ_add(self_bits, classical_value)
	if toff_seq == NULL:
		allocator_free(alloc, temp_start, self_bits + 1)
		return
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
	toffoli_sequence_free(toff_seq)
	allocator_free(alloc, temp_start, self_bits + 1)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef _toffoli_cq_cont(circuit_s *circ, const unsigned int *self_qubits,
                      int self_bits, int64_t classical_value, int invert,
                      unsigned int control_qubit):
	cdef sequence_t *toff_seq
	cdef const sequence_t *cached_seq
	cdef sequence_t *copy_seq
	cdef int i
	cdef int cla_ancilla_count, total_cla_ancilla
	cdef unsigned int cla_start, ct_temp, temp_start
	cdef unsigned int tqa[256]
	cdef unsigned int cla_qa[256]
	cdef qubit_allocator_t *alloc = circuit_get_allocator(circ)
	cdef int64_t negated

	if self_bits == 1:
		tqa[0] = self_qubits[0]
		tqa[1] = control_qubit
		toff_seq = toffoli_cCQ_add(self_bits, classical_value)
		if toff_seq == NULL:
			return
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
		toffoli_sequence_free(toff_seq)
		return

	# Clifford+T cCQ increment dispatch (value==1, widths 1-8)
	if circ.toffoli_decompose and classical_value == 1 and self_bits <= TOFFOLI_HARDCODED_MAX_WIDTH:
		# Controlled CLA Clifford+T cCQ increment (forward only)
		if not invert and circ.cla_override == 0 and self_bits >= circ.tradeoff_auto_threshold:
			cla_ancilla_count = _compute_cla_ancilla_count(circ, self_bits)
			total_cla_ancilla = self_bits + cla_ancilla_count + 1
			cla_start = allocator_alloc(alloc, total_cla_ancilla, True)
			if cla_start != <unsigned int>(-1):
				for i in range(self_bits):
					cla_qa[i] = cla_start + i
				for i in range(self_bits):
					cla_qa[self_bits + i] = self_qubits[i]
				for i in range(cla_ancilla_count):
					cla_qa[2 * self_bits + i] = cla_start + self_bits + i
				cla_qa[2 * self_bits + cla_ancilla_count] = control_qubit
				cla_qa[2 * self_bits + cla_ancilla_count + 1] = cla_start + self_bits + cla_ancilla_count
				if self_bits not in _clifft_cache_cla_ccq_inc:
					cached_seq = get_hardcoded_toffoli_clifft_cla_cCQ_inc(self_bits)
					if cached_seq != NULL:
						_clifft_cache_cla_ccq_inc[self_bits] = <unsigned long long>cached_seq
				if self_bits in _clifft_cache_cla_ccq_inc:
					cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_cla_ccq_inc[self_bits]
					copy_seq = copy_hardcoded_sequence(cached_seq)
					if copy_seq != NULL:
						run_instruction(copy_seq, cla_qa, invert, <circuit_t*>circ, 0)
						toffoli_sequence_free(copy_seq)
						allocator_free(alloc, cla_start, total_cla_ancilla)
						return
				allocator_free(alloc, cla_start, total_cla_ancilla)
		# Controlled RCA Clifford+T cCQ increment
		ct_temp = allocator_alloc(alloc, self_bits + 2, True)
		if ct_temp != <unsigned int>(-1):
			for i in range(self_bits):
				tqa[i] = ct_temp + i
			for i in range(self_bits):
				tqa[self_bits + i] = self_qubits[i]
			tqa[2 * self_bits] = ct_temp + self_bits
			tqa[2 * self_bits + 1] = control_qubit
			tqa[2 * self_bits + 2] = ct_temp + self_bits + 1
			if self_bits not in _clifft_cache_ccq_inc:
				cached_seq = get_hardcoded_toffoli_clifft_cCQ_inc(self_bits)
				if cached_seq != NULL:
					_clifft_cache_ccq_inc[self_bits] = <unsigned long long>cached_seq
			if self_bits in _clifft_cache_ccq_inc:
				cached_seq = <const sequence_t*><unsigned long long>_clifft_cache_ccq_inc[self_bits]
				copy_seq = copy_hardcoded_sequence(cached_seq)
				if copy_seq != NULL:
					run_instruction(copy_seq, tqa, invert, <circuit_t*>circ, 0)
					toffoli_sequence_free(copy_seq)
					allocator_free(alloc, ct_temp, self_bits + 2)
					return
			allocator_free(alloc, ct_temp, self_bits + 2)

	# Controlled CQ two's complement CLA subtraction for min_depth mode
	if invert and circ.tradeoff_min_depth and circ.cla_override == 0 and self_bits >= circ.tradeoff_auto_threshold:
		negated = (<int64_t>1 << self_bits) - classical_value
		cla_ancilla_count = _compute_cla_ancilla_count(circ, self_bits)
		total_cla_ancilla = self_bits + cla_ancilla_count + 1
		cla_start = allocator_alloc(alloc, total_cla_ancilla, True)
		if cla_start != <unsigned int>(-1):
			for i in range(self_bits):
				cla_qa[i] = cla_start + i
			for i in range(self_bits):
				cla_qa[self_bits + i] = self_qubits[i]
			for i in range(cla_ancilla_count):
				cla_qa[2 * self_bits + i] = cla_start + self_bits + i
			cla_qa[2 * self_bits + cla_ancilla_count] = control_qubit
			cla_qa[2 * self_bits + cla_ancilla_count + 1] = cla_start + self_bits + cla_ancilla_count
			if circ.qubit_saving:
				toff_seq = toffoli_cCQ_add_bk(self_bits, negated)
			else:
				toff_seq = toffoli_cCQ_add_ks(self_bits, negated)
			if toff_seq != NULL:
				run_instruction(toff_seq, cla_qa, 0, <circuit_t*>circ, 0)
				toffoli_sequence_free(toff_seq)
				allocator_free(alloc, cla_start, total_cla_ancilla)
				return
			allocator_free(alloc, cla_start, total_cla_ancilla)

	# Controlled CQ CLA dispatch: forward only
	if not invert and circ.cla_override == 0 and self_bits >= circ.tradeoff_auto_threshold:
		cla_ancilla_count = _compute_cla_ancilla_count(circ, self_bits)
		total_cla_ancilla = self_bits + cla_ancilla_count + 1
		cla_start = allocator_alloc(alloc, total_cla_ancilla, True)
		if cla_start != <unsigned int>(-1):
			for i in range(self_bits):
				cla_qa[i] = cla_start + i
			for i in range(self_bits):
				cla_qa[self_bits + i] = self_qubits[i]
			for i in range(cla_ancilla_count):
				cla_qa[2 * self_bits + i] = cla_start + self_bits + i
			cla_qa[2 * self_bits + cla_ancilla_count] = control_qubit
			cla_qa[2 * self_bits + cla_ancilla_count + 1] = cla_start + self_bits + cla_ancilla_count
			if circ.qubit_saving:
				toff_seq = toffoli_cCQ_add_bk(self_bits, classical_value)
			else:
				toff_seq = toffoli_cCQ_add_ks(self_bits, classical_value)
			if toff_seq != NULL:
				run_instruction(toff_seq, cla_qa, invert, <circuit_t*>circ, 0)
				toffoli_sequence_free(toff_seq)
				allocator_free(alloc, cla_start, total_cla_ancilla)
				return
			allocator_free(alloc, cla_start, total_cla_ancilla)

	# Controlled RCA (CDKM) CQ path: self_bits + 2 ancilla
	temp_start = allocator_alloc(alloc, self_bits + 2, True)
	if temp_start == <unsigned int>(-1):
		return
	for i in range(self_bits):
		tqa[i] = temp_start + i
	for i in range(self_bits):
		tqa[self_bits + i] = self_qubits[i]
	tqa[2 * self_bits] = temp_start + self_bits
	tqa[2 * self_bits + 1] = control_qubit
	tqa[2 * self_bits + 2] = temp_start + self_bits + 1
	toff_seq = toffoli_cCQ_add(self_bits, classical_value)
	if toff_seq == NULL:
		allocator_free(alloc, temp_start, self_bits + 2)
		return
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ, 0)
	toffoli_sequence_free(toff_seq)
	allocator_free(alloc, temp_start, self_bits + 2)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef _toffoli_dispatch_cq(circuit_s *circ, const unsigned int *self_qubits,
                          int self_bits, int64_t classical_value, int invert,
                          int controlled, unsigned int control_qubit):
	if controlled:
		_toffoli_cq_cont(circ, self_qubits, self_bits, classical_value, invert, control_qubit)
	else:
		_toffoli_cq_uncont(circ, self_qubits, self_bits, classical_value, invert)
