from libc.stdlib cimport free, malloc, calloc
from libc.string cimport memcpy, memset
from libc.stdint cimport int64_t

# Core types from types.h -- gate_t with full field access for capture-replay
cdef extern from "types.h":
	ctypedef unsigned int qubit_t
	ctypedef enum Standardgate_t:
		X, Y, Z, R, H, Rx, Ry, Rz, P, M, T_GATE, TDG_GATE

	ctypedef struct gate_t:
		qubit_t Control[2]  # MAXCONTROLS = 2
		qubit_t *large_control
		unsigned int NumControls
		Standardgate_t Gate
		double GateValue
		qubit_t Target
		unsigned int NumBasisGates

	ctypedef struct sequence_t:
		unsigned int num_layer
		unsigned int used_layer
		unsigned int total_gate_count

cdef extern from "arithmetic_ops.h":
	# Addition operations
	sequence_t *CC_add();
	sequence_t *CQ_add(int bits, long long value);
	sequence_t *QQ_add(int bits);
	sequence_t *cCQ_add(int bits, long long value);
	sequence_t *cQQ_add(int bits);

	# Multiplication operations
	sequence_t *CC_mul();
	sequence_t *CQ_mul(int bits, long long value);
	sequence_t *QQ_mul(int bits);
	sequence_t *cCQ_mul(int bits, long long value);
	sequence_t *cQQ_mul(int bits);

cdef extern from "arithmetic_ops.h":
	# Split-register arithmetic (Phase 4: In-Place Comparison Operators)
	sequence_t *split_CQ_add(int bits, int64_t value)
	sequence_t *split_CQ_sub(int bits, int64_t value)
	sequence_t *split_toffoli_CQ_add(int bits, int64_t value)
	sequence_t *split_toffoli_CQ_sub(int bits, int64_t value)

cdef extern from "toffoli_arithmetic_ops.h":
	sequence_t *toffoli_QQ_add(int bits)
	sequence_t *toffoli_CQ_add(int bits, int64_t value)
	sequence_t *toffoli_cQQ_add(int bits)
	sequence_t *toffoli_cCQ_add(int bits, int64_t value)
	sequence_t *toffoli_QQ_add_bk(int bits)
	sequence_t *toffoli_QQ_add_ks(int bits)
	sequence_t *toffoli_CQ_add_bk(int bits, int64_t value)
	sequence_t *toffoli_CQ_add_ks(int bits, int64_t value)
	sequence_t *toffoli_cQQ_add_bk(int bits)
	sequence_t *toffoli_cQQ_add_ks(int bits)
	sequence_t *toffoli_cCQ_add_bk(int bits, int64_t value)
	sequence_t *toffoli_cCQ_add_ks(int bits, int64_t value)
	void toffoli_sequence_free(sequence_t *seq)
	int bk_cla_ancilla_count(int bits)

cdef extern from "toffoli_sequences.h":
	int TOFFOLI_HARDCODED_MAX_WIDTH
	const sequence_t *get_hardcoded_toffoli_clifft_QQ_add(int bits)
	const sequence_t *get_hardcoded_toffoli_clifft_cQQ_add(int bits)
	const sequence_t *get_hardcoded_toffoli_clifft_CQ_inc(int bits)
	const sequence_t *get_hardcoded_toffoli_clifft_cCQ_inc(int bits)
	const sequence_t *get_hardcoded_toffoli_clifft_cla_QQ_add(int bits)
	const sequence_t *get_hardcoded_toffoli_clifft_cla_cQQ_add(int bits)
	const sequence_t *get_hardcoded_toffoli_clifft_cla_CQ_inc(int bits)
	const sequence_t *get_hardcoded_toffoli_clifft_cla_cCQ_inc(int bits)

cdef extern from "toffoli_addition_internal.h":
	sequence_t *copy_hardcoded_sequence(const sequence_t *src)

cdef extern from "gate.h":
	void x(gate_t *g, qubit_t target)
	void cx(gate_t *g, qubit_t target, qubit_t control)

cdef extern from "toffoli_arithmetic_ops.h":
	# Toffoli Division (Phase 91)
	void toffoli_divmod_cq(circuit_t *circ, const unsigned int *dividend_qubits,
	                       int dividend_bits, int64_t divisor,
	                       const unsigned int *quotient_qubits,
	                       const unsigned int *remainder_qubits)
	void toffoli_divmod_qq(circuit_t *circ, const unsigned int *dividend_qubits,
	                       int dividend_bits, const unsigned int *divisor_qubits,
	                       int divisor_bits, const unsigned int *quotient_qubits,
	                       const unsigned int *remainder_qubits)
	void toffoli_cdivmod_cq(circuit_t *circ, const unsigned int *dividend_qubits,
	                        int dividend_bits, int64_t divisor,
	                        const unsigned int *quotient_qubits,
	                        const unsigned int *remainder_qubits,
	                        unsigned int ext_ctrl)
	void toffoli_cdivmod_qq(circuit_t *circ, const unsigned int *dividend_qubits,
	                        int dividend_bits, const unsigned int *divisor_qubits,
	                        int divisor_bits, const unsigned int *quotient_qubits,
	                        const unsigned int *remainder_qubits,
	                        unsigned int ext_ctrl)

	# Toffoli Modular CQ Addition/Subtraction (Phase 92)
	void toffoli_mod_add_cq(circuit_t *circ, const unsigned int *value_qubits,
	                        int value_bits, int64_t addend, int64_t modulus)
	void toffoli_cmod_add_cq(circuit_t *circ, const unsigned int *value_qubits,
	                         int value_bits, int64_t addend, int64_t modulus,
	                         unsigned int ext_ctrl)
	void toffoli_mod_sub_cq(circuit_t *circ, const unsigned int *value_qubits,
	                        int value_bits, int64_t subtrahend, int64_t modulus)
	void toffoli_cmod_sub_cq(circuit_t *circ, const unsigned int *value_qubits,
	                         int value_bits, int64_t subtrahend, int64_t modulus,
	                         unsigned int ext_ctrl)

	# Toffoli Modular QQ Addition/Subtraction (Phase 92)
	void toffoli_mod_add_qq(circuit_t *circ, const unsigned int *value_qubits,
	                        int value_bits, const unsigned int *other_qubits,
	                        int other_bits, int64_t modulus)
	void toffoli_cmod_add_qq(circuit_t *circ, const unsigned int *value_qubits,
	                         int value_bits, const unsigned int *other_qubits,
	                         int other_bits, int64_t modulus, unsigned int ext_ctrl)
	void toffoli_mod_sub_qq(circuit_t *circ, const unsigned int *value_qubits,
	                        int value_bits, const unsigned int *other_qubits,
	                        int other_bits, int64_t modulus)
	void toffoli_cmod_sub_qq(circuit_t *circ, const unsigned int *value_qubits,
	                         int value_bits, const unsigned int *other_qubits,
	                         int other_bits, int64_t modulus, unsigned int ext_ctrl)

	# Toffoli Modular Multiplication (Phase 92)
	void toffoli_mod_mul_cq(circuit_t *circ, const unsigned int *value_qubits,
	                        int value_bits, const unsigned int *result_qubits,
	                        int result_bits, int64_t multiplier, int64_t modulus)
	void toffoli_cmod_mul_cq(circuit_t *circ, const unsigned int *value_qubits,
	                         int value_bits, const unsigned int *result_qubits,
	                         int result_bits, int64_t multiplier, int64_t modulus,
	                         unsigned int ext_ctrl)
	void toffoli_mod_mul_qq(circuit_t *circ, const unsigned int *a_qubits,
	                        int a_bits, const unsigned int *b_qubits, int b_bits,
	                        const unsigned int *result_qubits, int result_bits,
	                        int64_t modulus)
	void toffoli_cmod_mul_qq(circuit_t *circ, const unsigned int *a_qubits,
	                         int a_bits, const unsigned int *b_qubits, int b_bits,
	                         const unsigned int *result_qubits, int result_bits,
	                         int64_t modulus, unsigned int ext_ctrl)

cdef extern from "Integer.h":
	# Type creation and manipulation (non-arithmetic functions only)
	pass  # Arithmetic functions moved to arithmetic_ops.h block


cdef extern from "bitwise_ops.h":
	# Width-parameterized bitwise operations (Phase 6)
	sequence_t *Q_not(int bits)
	sequence_t *cQ_not(int bits)
	sequence_t *Q_xor(int bits)
	sequence_t *cQ_xor(int bits)
	sequence_t *Q_and(int bits)
	sequence_t *CQ_and(int bits, int64_t value)
	sequence_t *Q_or(int bits)
	sequence_t *CQ_or(int bits, int64_t value)

cdef extern from "comparison_ops.h":
	# Width-parameterized comparison operations (Phase 12)
	sequence_t *CQ_equal_width(int bits, int64_t value)
	sequence_t *cCQ_equal_width(int bits, int64_t value)

cdef extern from "LogicOperations.h":
	# Legacy qbool operations
	sequence_t *q_and_seq();
	sequence_t *cq_and_seq();
	sequence_t *qq_and_seq();
	sequence_t *cqq_and_seq();

	sequence_t *q_not_seq();
	sequence_t *cq_not_seq();

	sequence_t *qq_or_seq();


cdef extern from "circuit.h":
	ctypedef struct circuit_t:
		pass

	ctypedef struct quantum_int_t:
		pass

	# Backend is stateless - all functions take explicit parameters

	circuit_t *init_circuit();
	void print_circuit(circuit_t *circ);
	void free_circuit(circuit_t *circ);

cdef extern from "circuit_output.h":
	void circuit_visualize(circuit_t *circ)

	ctypedef struct draw_data_t:
		unsigned int num_layers
		unsigned int num_qubits
		unsigned int num_gates
		unsigned int *gate_layer
		unsigned int *gate_target
		unsigned int *gate_type
		double *gate_angle
		unsigned int *gate_num_ctrl
		unsigned int *ctrl_qubits
		unsigned int *ctrl_offsets
		unsigned int *qubit_map

	draw_data_t *circuit_to_draw_data(circuit_t *circ)
	void free_draw_data(draw_data_t *data);

cdef extern from "validation.h":
	int QV_OK
	int QV_NULL_CIRC
	int QV_NULL_SEQ
	int QV_NULL_ARG
	int QV_MAX_QUBIT_SLOTS

cdef extern from "execution.h":
	void qubit_mapping(unsigned int qubit_arrray[], circuit_t *circ);
	void run_instruction(sequence_t *res, const unsigned int qubit_array[], int invert, circuit_t *circ);
	void reverse_circuit_range(circuit_t *circ, int start_layer, int end_layer);
	# Validated entry points for Cython boundary (Phase 84)
	int validated_run_instruction(sequence_t *res, const unsigned int qubit_array[], int invert, circuit_t *circ);
	int validated_reverse_circuit_range(circuit_t *circ, int start_layer, int end_layer);

cdef extern from "qubit_allocator.h":
	# Forward declaration to match C header
	# Expanded for capture-replay: sequence, used_gates_per_layer access
	cdef struct circuit_s:
		gate_t **sequence           # [layer][gate_index]
		unsigned int used_layer
		unsigned int *used_gates_per_layer  # [layer]
		unsigned int used_qubits
		unsigned int layer_floor
		unsigned int arithmetic_mode    # 0=ARITH_QFT, 1=ARITH_TOFFOLI
		int cla_override               # 0=auto CLA, 1=force RCA
		int qubit_saving               # 0=off (KS), 1=on (BK)
		int toffoli_decompose          # 0=off (CCX in output), 1=on (decompose to Clifford+T)
		int tradeoff_auto_threshold    # Width threshold for auto CLA
		int tradeoff_min_depth         # 1 = min_depth mode (CLA subtraction enabled)
		int simulate                   # 0 = tracking-only (count gates), 1 = full simulation
		size_t gate_count              # Running gate count (both modes)

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

cdef extern from "circuit_stats.h":
	ctypedef struct gate_counts_t:
		size_t x_gates
		size_t y_gates
		size_t z_gates
		size_t h_gates
		size_t p_gates
		size_t cx_gates
		size_t ccx_gates
		size_t t_gates
		size_t tdg_gates
		size_t other_gates
		size_t t_count

	size_t circuit_gate_count(circuit_s *circ)
	unsigned int circuit_depth(circuit_s *circ)
	unsigned int circuit_qubit_count(circuit_s *circ)
	gate_counts_t circuit_gate_counts(circuit_s *circ)

cdef extern from "optimizer.h":
	# Gate injection for capture-replay
	void add_gate(circuit_t *circ, gate_t *g)


cdef extern from "toffoli_arithmetic_ops.h":
	# Toffoli Multiplication (Phase 68/69)
	void toffoli_mul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
	                    const unsigned int *self_qubits, int self_bits,
	                    const unsigned int *other_qubits, int other_bits)
	void toffoli_mul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
	                    const unsigned int *self_qubits, int self_bits, int64_t classical_value)
	void toffoli_cmul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
	                     const unsigned int *self_qubits, int self_bits,
	                     const unsigned int *other_qubits, int other_bits, unsigned int ext_ctrl)
	void toffoli_cmul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
	                     const unsigned int *self_qubits, int self_bits, int64_t classical_value,
	                     unsigned int ext_ctrl)

cdef extern from "circuit_optimizer.h":
	ctypedef enum opt_pass_t:
		OPT_PASS_MERGE
		OPT_PASS_CANCEL_INVERSE

	circuit_s *circuit_optimize(circuit_s *circ)
	circuit_s *circuit_optimize_pass(circuit_s *circ, opt_pass_t pass_type)
	int circuit_can_optimize(circuit_s *circ)


# Module constants
cdef int INTEGERSIZE
cdef int NUMANCILLY
cdef int QUANTUM
cdef int CLASSICAL

# Global state variables (not cimportable - use accessor functions instead)
# These are defined in _core.pyx but not exposed via cimport

# circuit class declaration
cdef class circuit:
	pass
