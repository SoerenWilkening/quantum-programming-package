# NOTE: This file is intentionally large (~2800 lines). Cython cdef classes
# cannot be split across files (no include/mixin support in cdef class bodies).
# See .planning/quick/004-consolidate-qint-pxi-includes-to-remove-/004-SUMMARY.md
"""Quantum integer type with arithmetic, bitwise, and comparison operations."""

cimport cython
from libc.stdint cimport int64_t
from libc.string cimport memset

import sys
import warnings

import numpy as np

# C-level imports for type declarations
from ._core cimport (
    circuit, circuit_t, circuit_s, sequence_t, gate_t,
    gate_counts_t, circuit_gate_counts_range,
    INTEGERSIZE, NUMANCILLY,
    init_circuit, Q_not, run_instruction,
    circuit_get_allocator, allocator_alloc, allocator_free,
    qubit_allocator_t,
    CQ_add, QQ_add, cCQ_add, cQQ_add,
    CQ_mul, QQ_mul, cCQ_mul, cQQ_mul,
    Q_and, CQ_and, cQ_and, cCQ_and, Q_or, CQ_or, cQ_or, cCQ_or, Q_xor, cQ_xor,
    cQ_not,
    CQ_equal_width, cCQ_equal_width,
    CQ_less_than, cCQ_less_than, CQ_greater_than, cCQ_greater_than,
    QQ_less_than, cQQ_less_than,
    print_circuit as c_print_circuit,
    toffoli_mul_qq, toffoli_mul_cq, toffoli_cmul_qq, toffoli_cmul_cq,
    toffoli_divmod_cq, toffoli_divmod_qq,
    toffoli_QQ_add, toffoli_CQ_add, toffoli_cQQ_add, toffoli_cCQ_add,
    toffoli_QQ_add_bk, toffoli_QQ_add_ks,
    toffoli_CQ_add_bk, toffoli_CQ_add_ks,
    toffoli_cQQ_add_bk, toffoli_cQQ_add_ks,
    toffoli_cCQ_add_bk, toffoli_cCQ_add_ks,
    toffoli_sequence_free,
    bk_cla_ancilla_count,
    TOFFOLI_HARDCODED_MAX_WIDTH,
    get_hardcoded_toffoli_clifft_QQ_add, get_hardcoded_toffoli_clifft_cQQ_add,
    get_hardcoded_toffoli_clifft_CQ_inc, get_hardcoded_toffoli_clifft_cCQ_inc,
    get_hardcoded_toffoli_clifft_cla_QQ_add, get_hardcoded_toffoli_clifft_cla_cQQ_add,
    get_hardcoded_toffoli_clifft_cla_CQ_inc, get_hardcoded_toffoli_clifft_cla_cCQ_inc,
    copy_hardcoded_sequence,
    add_gate,
    x as gate_x, cx as gate_cx,
    split_CQ_add, split_CQ_sub,
    split_toffoli_CQ_add, split_toffoli_CQ_sub,
)

# Python-level imports for global state access via accessor functions
from ._core import (
    _get_circuit, _get_circuit_initialized, _set_circuit_initialized,
    _get_circuit_active,
    _get_num_qubits, _set_num_qubits,
    _get_int_counter, _set_int_counter, _increment_int_counter,
    _get_controlled, _set_controlled,
    _get_control_bool, _set_control_bool,
    _get_list_of_controls, _set_list_of_controls,
    _push_control, _pop_control,
    _get_smallest_allocated_qubit, _set_smallest_allocated_qubit,
    _get_qubit_saving_mode, _set_qubit_saving_mode,
    _get_global_creation_counter, _increment_global_creation_counter,
    _get_scope_stack,
    _get_ancilla, _increment_ancilla, _decrement_ancilla,
    qubit_array,
    current_scope_depth,
    validate_circuit, validate_qubit_slots,
    _mark_arithmetic_performed,
)


import math
from ._gates import emit_p, emit_p_raw, _toffoli_and, _uncompute_toffoli_and
from ._core import _get_control_stack
from .call_graph import record_operation as _record_operation
from ._compile_state import _is_compile_mode, _record_instruction
from .history_graph import HistoryGraph


def _run_inverted_on_circuit(seq_ptr, qubit_mapping, int num_ancilla=0):
	"""Run a sequence inverted on the active circuit.

	Called by ``HistoryGraph.uncompute()`` to replay a single operation
	in reverse.  Takes Python int arguments and casts internally to
	C pointers.

	When *num_ancilla* > 0, fresh ancilla qubits are allocated, appended
	to the mapping, and freed after the inverse call.  This is needed
	for operations like CQ equality whose forward path allocates
	AND-decomposition ancilla that are freed immediately after use.

	Parameters
	----------
	seq_ptr : int
		Pointer to ``sequence_t`` as a Python int.
	qubit_mapping : tuple[int, ...]
		Core qubit indices (result + operand + optional control).
	num_ancilla : int, optional
		Number of ancilla to allocate and append (default 0).
	"""
	cdef sequence_t *_seq = <sequence_t*><unsigned long long>seq_ptr
	cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
	cdef unsigned int _qa[256]
	cdef int _i
	cdef int _n = len(qubit_mapping)
	cdef int _total = _n + num_ancilla
	cdef qubit_allocator_t *_alloc
	cdef unsigned int _anc_start = 0
	cdef bint _anc_ok = True

	# Bounds check: mapping + ancilla must fit in stack buffer
	if _total > 256:
		import sys
		print(f"Warning: _run_inverted_on_circuit: mapping size {_total} exceeds buffer (256), skipping",
		      file=sys.stderr)
		return

	for _i in range(_n):
		_qa[_i] = qubit_mapping[_i]

	# Allocate fresh ancilla for MCX decomposition replay
	if num_ancilla > 0:
		_anc_ok = False
		_alloc = circuit_get_allocator(<circuit_s*>_circ)
		if _alloc != NULL:
			_anc_start = allocator_alloc(_alloc, num_ancilla, True)
			if _anc_start != <unsigned int>(-1):
				for _i in range(num_ancilla):
					_qa[_n + _i] = _anc_start + _i
				_anc_ok = True

	# Skip run_instruction if ancilla allocation was required but failed
	if not _anc_ok:
		return

	run_instruction(_seq, _qa, True, _circ)

	# Free ancilla after inverse call
	if num_ancilla > 0 and _anc_start != <unsigned int>(-1):
		_alloc = circuit_get_allocator(<circuit_s*>_circ)
		if _alloc != NULL:
			allocator_free(_alloc, _anc_start, num_ancilla)


class _PhaseProxy:
	"""Proxy object returned by qint.phase / qarray.phase property.

	Supports += theta (phase shift) and *= -1 (phase flip).
	When uncontrolled: emits no gate (global phase is unobservable).
	When controlled (inside `with` block): emits CP(theta) on the control qubit.
	"""
	__slots__ = ('_owner',)

	def __init__(self, owner):
		self._owner = owner

	def __iadd__(self, theta):
		if _get_controlled():
			ctrl = _get_control_bool()
			# Use emit_p_raw to avoid double-control: emit_p would check
			# _get_controlled() again and wrap with CP, producing
			# cp(ctrl, ctrl) -- a self-controlled gate with no search
			# register effect. Instead, emit P directly on the control
			# qubit. P(theta) on a qubit in |1> adds phase e^{i*theta}
			# to all basis states where that qubit is |1>, which is
			# exactly the controlled global phase we want.
			emit_p_raw(ctrl.qubits[63], theta)
		# Uncontrolled: no gate (global phase is unobservable)
		return self

	def __imul__(self, factor):
		if factor == -1:
			return self.__iadd__(math.pi)
		raise ValueError("phase *= only supports -1")


# BEGIN include "toffoli_dispatch.pxi"
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
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
					run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ)
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
				run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ)
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
				if not circ.simulate:
					circ.gate_count += 1
				else:
					add_gate(<circuit_t*>circ, &xg)
			for i in range(cla_ancilla_count):
				tqa[2 * result_bits + i] = cla_ancilla + i
			if circ.qubit_saving:
				toff_seq = toffoli_QQ_add_bk(result_bits)
			else:
				toff_seq = toffoli_QQ_add_ks(result_bits)
			if toff_seq != NULL:
				run_instruction(toff_seq, tqa, 0, <circuit_t*>circ)
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
						run_instruction(inc_seq, inc_qa, 0, <circuit_t*>circ)
						toffoli_sequence_free(inc_seq)
					allocator_free(alloc, inc_ancilla, self_bits + 1)
				for i in range(other_bits):
					memset(&xg, 0, sizeof(gate_t))
					gate_x(&xg, other_qubits[i])
					if not circ.simulate:
						circ.gate_count += 1
					else:
						add_gate(<circuit_t*>circ, &xg)
				return
			allocator_free(alloc, cla_ancilla, cla_ancilla_count)
			for i in range(other_bits):
				memset(&xg, 0, sizeof(gate_t))
				gate_x(&xg, other_qubits[i])
				if not circ.simulate:
					circ.gate_count += 1
				else:
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
				run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
				run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ)
				return

		toff_seq = toffoli_cQQ_add(result_bits)
		if toff_seq == NULL:
			return
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
					run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ)
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
				run_instruction(<sequence_t*>cached_seq, tqa, invert, <circuit_t*>circ)
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
				if not circ.simulate:
					circ.gate_count += 1
				else:
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
				run_instruction(toff_seq, tqa, 0, <circuit_t*>circ)
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
						run_instruction(inc_seq, inc_qa, 0, <circuit_t*>circ)
						toffoli_sequence_free(inc_seq)
					allocator_free(alloc, inc_ancilla, self_bits + 2)
				for i in range(other_bits):
					memset(&cxg, 0, sizeof(gate_t))
					gate_cx(&cxg, other_qubits[i], control_qubit)
					if not circ.simulate:
						circ.gate_count += 1
					else:
						add_gate(<circuit_t*>circ, &cxg)
				return
			allocator_free(alloc, cla_ancilla, cla_ancilla_count + 1)
			for i in range(other_bits):
				memset(&cxg, 0, sizeof(gate_t))
				gate_cx(&cxg, other_qubits[i], control_qubit)
				if not circ.simulate:
					circ.gate_count += 1
				else:
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
				run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
						run_instruction(copy_seq, tqa, invert, <circuit_t*>circ)
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
					run_instruction(copy_seq, tqa, invert, <circuit_t*>circ)
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
				run_instruction(toff_seq, tqa, 0, <circuit_t*>circ)
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
				run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
		run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
						run_instruction(copy_seq, cla_qa, invert, <circuit_t*>circ)
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
					run_instruction(copy_seq, tqa, invert, <circuit_t*>circ)
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
				run_instruction(toff_seq, cla_qa, 0, <circuit_t*>circ)
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
				run_instruction(toff_seq, cla_qa, invert, <circuit_t*>circ)
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
	run_instruction(toff_seq, tqa, invert, <circuit_t*>circ)
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
# END include "toffoli_dispatch.pxi"

cdef class qint(circuit):
	"""Quantum integer with arithmetic, bitwise, and comparison operations.

	A quantum integer represents an integer value in quantum superposition,
	encoded in computational basis using qubits. Supports standard arithmetic
	and bitwise operations that compile to quantum circuits.

	Parameters
	----------
	value : int, optional
		Initial value (default 0). Encoded into quantum state |value>.
	width : int, optional
		Bit width (1-64, default 8). Determines range: [-2^(w-1), 2^(w-1)-1].
		If None and value != 0, auto-determines width from value (unsigned mode).
	bits : int, optional
		Alias for width (backward compatibility).
	classical : bool, optional
		Whether this is a classical integer (default False).
	create_new : bool, optional
		Whether to allocate new qubits (default True).
	bit_list : array-like, optional
		External qubit list (when create_new=False).

	Attributes
	----------
	width : int
		Bit width (read-only property).

	Examples
	--------
	>>> a = qint(5)           # Auto-width (3-bit) quantum integer, value 5
	>>> b = qint(5, width=16) # 16-bit quantum integer, value 5
	>>> c = a + b             # Quantum addition
	>>> d = a & b             # Quantum AND
	>>> flag = (a == 5)       # Quantum comparison (returns qbool)

	Notes
	-----
	Creates quantum state |value> using computational basis encoding.
	Auto-width mode uses unsigned representation (minimum bits for magnitude).
	All operations preserve quantum coherence and support superposition.
	"""
	# Attribute declarations are in qint.pxd

	def __init__(self, value = 0, width = None, bits = None, classical = False, create_new = True, bit_list = None):
		"""Create a quantum integer.

		Allocates qubits and initializes to specified value in superposition.

		Parameters
		----------
		value : int, optional
			Initial value (default 0). Encoded into quantum state |value>.
		width : int, optional
			Bit width (1-64, default 8). Determines range: [-2^(w-1), 2^(w-1)-1].
			If None and value != 0, auto-determines width from value (unsigned mode).
		bits : int, optional
			Alias for width (backward compatibility).
		classical : bool, optional
			Whether this is a classical integer (default False).
		create_new : bool, optional
			Whether to allocate new qubits (default True).
		bit_list : array-like, optional
			External qubit list (when create_new=False).

		Raises
		------
		ValueError
			If width < 1 or width > 64.
		UserWarning
			If value exceeds width range (modular arithmetic applies).

		Examples
		--------
		>>> a = qint(5)           # Auto-width (3-bit) quantum integer, value 5
		>>> b = qint(5, width=16) # 16-bit quantum integer, value 5
		>>> c = qint(5, bits=16)  # Backward compatible alias
		>>> d = qint(0)           # Default 8-bit quantum integer, value 0

		Notes
		-----
		Creates quantum state |value> using computational basis encoding.
		Auto-width mode uses unsigned representation (minimum bits for magnitude).
		"""
		cdef qubit_allocator_t *alloc
		cdef unsigned int start
		cdef int actual_width
		cdef unsigned int[:] arr
		cdef sequence_t *seq
		cdef int bit_pos, qubit_idx
		cdef long long masked_value
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		super().__init__()

		# Handle int-like values (objects with __int__ method)
		if hasattr(value, '__int__'):
			value = int(value)

		# Handle width/bits parameter with auto-width support
		if width is None and bits is None:
			# Auto-width mode: determine width from value
			if value == 0:
				actual_width = INTEGERSIZE  # Default 8 bits for zero
			elif value > 0:
				# Positive: unsigned bit count (no sign bit)
				actual_width = value.bit_length()
			else:
				# Negative: two's complement formula
				# -1 needs 1 bit, other negatives depend on magnitude
				if value == -1:
					actual_width = 1
				else:
					mag = -value
					# If magnitude is power of 2, use mag.bit_length() bits
					# Otherwise use mag.bit_length() + 1 bits
					if (mag & (mag - 1)) == 0:  # Power of 2 check
						actual_width = mag.bit_length()
					else:
						actual_width = mag.bit_length() + 1
		elif width is not None:
			actual_width = width
		else:
			actual_width = bits  # Backward compatibility

		# Width validation
		if actual_width < 1 or actual_width > 64:
			raise ValueError(f"Width must be 1-64, got {actual_width}")

		if create_new:
			self.counter = _increment_int_counter()
			self.bits = actual_width
			self.value = value

			# Warn if value exceeds width (two's complement range)
			# Only warn when width was explicitly specified (not auto-width mode)
			# Note: For 1-bit (qbool), treat as unsigned [0,1] for clarity
			if value != 0 and (width is not None or bits is not None):
				if actual_width == 1:
					# Single bit: unsigned range [0, 1]
					max_value = 1
					min_value = 0
				else:
					# Multi-bit: signed range
					max_value = (1 << (actual_width - 1)) - 1
					min_value = -(1 << (actual_width - 1))
				if value > max_value or value < min_value:
					warnings.warn(
						f"Value {value} exceeds {actual_width}-bit range [{min_value}, {max_value}]. "
						f"Value will truncate (modular arithmetic).",
						UserWarning
					)

			_set_num_qubits(_get_num_qubits() + actual_width)

			self.qubits = np.ndarray(64, dtype = np.uint32)  # Max width support

			# NEW: Allocate qubits through circuit's allocator
			alloc = circuit_get_allocator(<circuit_s*>_circuit)
			if alloc == NULL:
				raise RuntimeError("Circuit allocator not initialized")

			start = allocator_alloc(alloc, actual_width, True)  # is_ancilla=True
			if start == <unsigned int>-1:
				raise MemoryError("Qubit allocation failed - limit exceeded")

			# Ensure circuit tracks all allocated qubits for QASM export
			# Without this, qubits with no gates (e.g., CQ AND where classical bit=0)
			# won't appear in the exported circuit
			if start + actual_width - 1 > (<circuit_s*>_circuit).used_qubits:
				(<circuit_s*>_circuit).used_qubits = start + actual_width - 1

			# Right-aligned qubit storage: indices [64-width] through [63]
			for i in range(actual_width):
				self.qubits[64 - actual_width + i] = start + i

			self.allocated_start = start  # Track for deallocation
			self.allocated_qubits = True

			# Phase 16: Initialize dependency tracking
			self._creation_order = _increment_global_creation_counter()
			self.dependency_parents = []
			self.operation_type = None
			self.creation_scope = current_scope_depth.get()
			# Capture control context
			_control_bool = _get_control_bool()
			if _control_bool is not None:
				self.control_context = [(<qint>_control_bool).qubits[63]]
			else:
				self.control_context = []

			# Phase 19: Register with active scope if inside a with block
			_scope_stack = _get_scope_stack()
			if _scope_stack and self.creation_scope == current_scope_depth.get() and current_scope_depth.get() > 0:
				_scope_stack[-1].append(self)

			# Phase 18: Initialize uncomputation tracking
			self._is_uncomputed = False
			self._keep_flag = False

			# Per-variable history graph for automatic uncomputation
			self.history = HistoryGraph()

			# Apply X gates based on binary representation of value
			# Phase 15: Classical initialization via X gate application
			if value != 0:
				# Mask value to width (handles both positive and negative via two's complement)
				masked_value = value & ((1 << actual_width) - 1)

				# Apply X gate for each 1 bit
				for bit_pos in range(actual_width):
					if (masked_value >> bit_pos) & 1:
						# Qubit index for bit_pos (right-aligned storage)
						# Bit 0 (LSB) is at qubits[64-width], bit (width-1) is at qubits[63]
						qubit_idx = 64 - actual_width + bit_pos
						qubit_array[0] = self.qubits[qubit_idx]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)

			# Keep backward compat tracking (deprecated, remove later)
			# Note: _smallest_allocated_qubit and ancilla numpy array still updated
			# for any code that might still use them
			_set_smallest_allocated_qubit(_get_smallest_allocated_qubit() + actual_width)
			_increment_ancilla(actual_width)
		else:
			self.bits = actual_width
			self.qubits = bit_list
			self.allocated_qubits = False

			# Phase 16: Initialize dependency tracking for bit_list path
			self._creation_order = _increment_global_creation_counter()
			self.dependency_parents = []
			self.operation_type = None
			self.creation_scope = current_scope_depth.get()
			# Capture control context
			_control_bool = _get_control_bool()
			if _control_bool is not None:
				self.control_context = [(<qint>_control_bool).qubits[63]]
			else:
				self.control_context = []

			# Phase 19: Register with active scope if inside a with block
			_scope_stack = _get_scope_stack()
			if _scope_stack and self.creation_scope == current_scope_depth.get() and current_scope_depth.get() > 0:
				_scope_stack[-1].append(self)

			# Phase 18: Initialize uncomputation tracking
			self._is_uncomputed = False
			self._keep_flag = False

			# Per-variable history graph for automatic uncomputation
			self.history = HistoryGraph()

	@property
	def qubits_allocated(self):
		"""True if this qint still has live qubit assignments."""
		return self.allocated_qubits

	@property
	def width(self):
		"""Get the bit width of this quantum integer (read-only).

		Returns
		-------
		int
			Bit width (1-64).

		Examples
		--------
		>>> a = qint(5, width=16)
		>>> a.width
		16
		"""
		return self.bits

	@property
	def phase(self):
		"""Get a phase proxy for controlled global phase operations.

		Returns a proxy object supporting ``x.phase += theta`` and
		``x.phase *= -1``.

		When uncontrolled: emits no gate (global phase is unobservable).
		When controlled (inside ``with`` block): emits CP(theta) on the
		control qubit.

		Returns
		-------
		_PhaseProxy
			Phase proxy object.

		Examples
		--------
		>>> with flag:
		...     x.phase += math.pi  # CP(pi) on control qubit
		>>> x.phase *= -1  # Equivalent to x.phase += pi
		"""
		return _PhaseProxy(self)

	@phase.setter
	def phase(self, value):
		# No-op setter: absorbs re-assignment from x.phase += theta
		# (Python desugars += to x.phase = x.phase.__iadd__(theta))
		pass

	# ====================================================================
	# UTILITY AND TRACKING METHODS
	# ====================================================================

	def add_dependency(self, parent):
		"""Register parent as dependency (strong reference).

		Strong references ensure parents stay alive until this object is
		uncomputed, preventing premature garbage collection of intermediates
		in expression chains like ``(arr == 1).all()``.

		Parameters
		----------
		parent : qint
			Parent qint this value depends on.

		Raises
		------
		AssertionError
			If parent was created after self (cycle detection).
		"""
		if parent is None:
			return
		# Cycle prevention: parent must be older
		assert parent._creation_order < self._creation_order, \
			f"Cycle detected: dependency (order {parent._creation_order}) must be older than dependent (order {self._creation_order})"
		self.dependency_parents.append(parent)

	def get_live_parents(self):
		"""Get list of parent dependencies that are still alive.

		Returns
		-------
		list
			List of parent qint objects.
		"""
		return [p for p in self.dependency_parents if not p._is_uncomputed]

	def _do_uncompute(self, bint from_del=False):
		"""Internal method to uncompute this qbool and cascade to dependencies.

		Called by __del__ (from_del=True) or explicit uncompute() (from_del=False).

		Parameters
		----------
		from_del : bool
			If True, suppress exceptions and only print warnings (Python __del__ best practice).
			If False, allow exceptions to propagate.
		"""
		cdef qubit_allocator_t *alloc
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		# Idempotency check - already uncomputed
		if self._is_uncomputed:
			return

		# No allocated qubits means nothing to uncompute
		if not self.allocated_qubits:
			self._is_uncomputed = True
			return

		try:
			# 1. CASCADE: Get live parents and sort by creation order (descending = LIFO)
			live_parents = self.get_live_parents()
			live_parents.sort(key=lambda p: p._creation_order, reverse=True)

			# Recursively uncompute parents that are intermediates (have operation_type).
			# Skip user-created variables (operation_type is None) — they must not
			# be destroyed by cascade uncomputation of expressions that use them.
			for parent in live_parents:
				if not parent._is_uncomputed and parent.operation_type is not None:
					parent._do_uncompute(from_del=from_del)

			# 2. FREE QUBITS: Return to allocator
			if _circuit_initialized:
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					allocator_free(alloc, self.allocated_start, self.bits)

			# 3. Mark as uncomputed, clear ownership and release parent refs
			self._is_uncomputed = True
			self.allocated_qubits = False
			self.dependency_parents = []

		except Exception as e:
			if from_del:
				# Phase 18 decision: __del__ failures print warning only
				import sys
				print(f"Warning: Uncomputation failed: {e}", file=sys.stderr)
			else:
				raise

	def uncompute(self):
		"""Explicitly uncompute this qbool and its dependencies.

		Triggers uncomputation of this qbool and cascades through its
		dependency graph (intermediate qbools created during operations).

		Raises
		------
		ValueError
			If other references to this qbool still exist.

		Notes
		-----
		This method is idempotent: calling twice prints warning, not error.
		Not affected by .keep() flag - explicit uncompute always allowed.

		Examples
		--------
		>>> c = circuit()
		>>> a = qbool(True)
		>>> b = qbool(False)
		>>> result = a & b
		>>> result.uncompute()  # Explicit early cleanup
		>>> # result can no longer be used in operations
		"""
		import sys

		# Idempotent: repeated calls print warning
		if self._is_uncomputed:
			print("Warning: .uncompute() called on already-uncomputed qbool",
			      file=sys.stderr)
			return

		# NOTE: Deliberately NOT checking _keep_flag here.
		# Design: .keep() only affects automatic uncomputation in __del__.
		# Explicit .uncompute() always allowed (gives user full control).

		# Check reference count
		refcount = sys.getrefcount(self)
		if refcount > 2:  # self + getrefcount argument
			raise ValueError(
				f"Cannot uncompute: qbool still in use ({refcount - 1} references exist). "
				f"Delete other references first or let automatic cleanup handle it."
			)

		self._do_uncompute(from_del=False)

	def keep(self):
		"""Prevent automatic uncomputation in current scope.

		Marks this qbool to skip automatic cleanup when it goes out of
		scope or is garbage collected. Useful when you need a qbool to
		persist for later use, such as when returning from a function.

		Returns
		-------
		None

		Notes
		-----
		- Only affects automatic uncomputation (__del__)
		- Does not prevent explicit .uncompute() calls
		- Warning printed if called on already-uncomputed qbool

		Examples
		--------
		>>> result = a & b
		>>> result.keep()  # Don't auto-uncompute when scope exits
		>>> return result  # Can safely return
		"""
		if self._is_uncomputed:
			import sys
			print("Warning: .keep() called on already-uncomputed qbool",
			      file=sys.stderr)
			return

		self._keep_flag = True

	def _check_not_uncomputed(self):
		"""Raise if this qbool has been uncomputed.

		Called at the start of operations to prevent use-after-uncompute bugs.

		Raises
		------
		ValueError
			If qbool has been uncomputed.
		"""
		if self._is_uncomputed:
			raise ValueError(
				"Cannot use qbool: already uncomputed. "
				"Create a new qbool or call .keep() to prevent automatic cleanup."
			)

	cpdef branch(self, double prob=0.5):
		"""Apply Ry rotation to create superposition.

		Creates quantum superposition by applying Ry(theta) rotation to all
		qubits in this qint. The angle theta is computed from the desired
		probability of measuring |1>:

		    theta = 2 * arcsin(sqrt(probability))

		Parameters
		----------
		prob : float, optional
		    Probability of |1> state (default 0.5 for equal superposition).
		    Must be in range [0, 1].

		Returns
		-------
		None
		    Mutates self; does not return new qint.

		Raises
		------
		ValueError
		    If prob is outside [0, 1] range.

		Examples
		--------
		>>> x = qint(0, width=4)
		>>> x.branch()        # Equal superposition on all 4 qubits
		>>> x[0].branch(0.3)  # 30% probability on LSB only

		Notes
		-----
		- Calling branch() multiple times accumulates rotations
		- Works inside `with qbool:` blocks (emits CRy gates)
		- Supports uncomputation via scope exit (inverse is Ry(-theta))
		"""
		cdef int self_offset
		cdef int i
		cdef double theta

		import math

		# Validate probability range (per user decision)
		if not 0.0 <= prob <= 1.0:
			raise ValueError(f"Probability must be in [0, 1], got {prob}")

		# Check not uncomputed (existing pattern)
		self._check_not_uncomputed()

		# Convert probability to Ry angle
		# For Ry(theta) on |0>: P(|1>) = sin^2(theta/2) = prob
		# Therefore: theta = 2 * arcsin(sqrt(prob))
		theta = 2.0 * math.asin(math.sqrt(prob))

		# Import emit_ry from _gates module
		from quantum_language._gates import emit_ry

		# Apply Ry to each qubit (right-aligned storage)
		self_offset = 64 - self.bits
		for i in range(self.bits):
			emit_ry(self.qubits[self_offset + i], theta)

		# Return None per user decision (mutation, no chaining)
		return None

	def print_circuit(self):
		"""Print the current quantum circuit to stdout.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> a.print_circuit()
		"""
		cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
		c_print_circuit(circ)

	def __del__(self):
		"""Automatic uncomputation on garbage collection with circuit guard.

		When a qint/qbool's refcount hits zero mid-circuit, __del__
		triggers uncomputation via the per-variable history graph.
		A circuit-active guard prevents firing during Python shutdown
		or after circuit finalization.

		Notes
		-----
		Follows Python best practice: exceptions in __del__ print warnings only.
		For deterministic cleanup, use explicit .uncompute() instead.
		"""
		# Circuit guard: skip uncomputation when circuit is not active
		# (during Python shutdown or after circuit finalization)
		if not _get_circuit_active():
			return

		# Phase 20: Check .keep() flag
		if hasattr(self, '_keep_flag') and self._keep_flag:
			return  # User opted out

		# Step 1.4: History-based uncomputation via __del__
		# If this variable has history entries, uncompute them in reverse
		# and cascade to orphaned children.
		if hasattr(self, 'history') and self.history:
			try:
				self.history.uncompute(_run_inverted_on_circuit)
			except Exception as e:
				import sys
				print(f"Warning: __del__ history uncomputation failed: {e}",
				      file=sys.stderr)

		# Mode-based decision - EAGER vs LAZY have different behavior
		if _get_qubit_saving_mode():
			# EAGER mode (qubit_saving=True): Always uncompute immediately when GC runs.
			# This minimizes peak qubit count by freeing qubits as soon as possible.
			self._do_uncompute(from_del=True)
		else:
			# LAZY mode (qubit_saving=False, default): Only uncompute when scope has exited.
			# This minimizes gate count by keeping intermediates alive longer (shared gates).
			# Use Phase 19's scope stack to check if we're still in the creation scope.
			# Phase 41: Use strict < instead of <= so that scope-0 qints (top-level)
			# don't auto-uncompute on GC. Only qints created inside with-blocks
			# (scope > 0) auto-uncompute when their scope exits.
			current = current_scope_depth.get()
			if current < self.creation_scope:
				# Scope has exited (depth decreased below creation scope) - safe to uncompute
				self._do_uncompute(from_del=True)
			# else: Still in or at creation scope - defer uncomputation
			# Scope-internal qints are uncomputed by __exit__ scope cleanup

		# Keep backward compat tracking (deprecated, but maintained for older code)
		# Guard against underflow when replaying inverse functions (Phase 51)
		if not self._is_uncomputed and self.bits > 0:
			current_smallest = _get_smallest_allocated_qubit()
			if current_smallest >= self.bits:
				_set_smallest_allocated_qubit(current_smallest - self.bits)
			_decrement_ancilla(self.bits)

	def __str__(self):
		return f"{self.qubits}"

	# Context manager protocol
	def __enter__(self):
		"""Enter quantum conditional context.

		Enables conditional quantum operations controlled by this qint's value.

		Returns
		-------
		qint
			Self for use in with statement.

		Examples
		--------
		>>> flag = qbool(True)
		>>> result = qint(0, width=8)
		>>> with flag:
		...     result += 5  # Conditional addition

		Notes
		-----
		Creates controlled quantum gates where this qint acts as control.
		"""
		self._check_not_uncomputed()

		# Phase 118: Enforce qbool-only (width=1) for with-block conditions
		if self.bits != 1:
			raise TypeError(
				f"with-block condition must be a qbool (1-bit), "
				f"got {self.bits}-bit qint"
			)

		_scope_stack = _get_scope_stack()

		# Phase 118: AND-composition at depth >= 1
		if _get_controlled():
			current_ctrl = _get_control_bool()
			and_ancilla = _toffoli_and(current_ctrl.qubits[63], self.qubits[63])
			_push_control(self, and_ancilla)
		else:
			# Single-level: no AND needed (backward compatible)
			_push_control(self, None)

		# Phase 19: Scope management - push new scope frame
		current_scope_depth.set(current_scope_depth.get() + 1)
		_scope_stack.append([])  # New empty scope frame

		# Update creation_scope for intermediate expressions used as conditions.
		# Python evaluates `with EXPR:` BEFORE calling __enter__, so the expression's
		# temporaries are created at the outer scope (often scope 0) and never
		# registered in any scope frame. By bumping creation_scope to the new inner
		# scope depth, the LAZY __del__ check (current < creation_scope) will trigger
		# uncomputation when the with-statement drops its reference. User-created
		# variables (operation_type=None) are left unchanged.
		if self.operation_type is not None:
			self.creation_scope = current_scope_depth.get()

		return self

	def __exit__(self, exc__type, exc, tb):
		"""Exit quantum conditional context with scope cleanup.

		Parameters
		----------
		exc__type : type
			Exception type if raised.
		exc : Exception
			Exception instance if raised.
		tb : traceback
			Traceback if exception raised.

		Returns
		-------
		bool
			False (does not suppress exceptions).

		Examples
		--------
		>>> flag = qbool(True)
		>>> with flag:
		...     pass  # Controlled operations here
		"""
		_scope_stack = _get_scope_stack()

		# Phase 19: Uncompute scope-local qbools FIRST (while still controlled)
		# This ensures uncomputation gates are generated inside the controlled context
		if _scope_stack:
			scope_qbools = _scope_stack.pop()

			# Sort by _creation_order descending for LIFO (newest first)
			scope_qbools.sort(key=lambda q: q._creation_order, reverse=True)

			# Uncompute each qbool in scope (skip if already uncomputed)
			for qbool_obj in scope_qbools:
				if not qbool_obj._is_uncomputed:
					qbool_obj._do_uncompute(from_del=False)

		# Phase 118: Uncompute AND-ancilla if present
		_cs = _get_control_stack()
		qbool_ref, and_ancilla = _cs[-1]
		if and_ancilla is not None:
			outer_entry = _cs[-2]
			outer_ctrl = outer_entry[1] if outer_entry[1] is not None else outer_entry[0]
			_uncompute_toffoli_and(and_ancilla, outer_ctrl.qubits[63], qbool_ref.qubits[63])

		# Phase 19: Decrement scope depth
		current_scope_depth.set(current_scope_depth.get() - 1)

		# Phase 117: Pop control entry from stack
		_pop_control()

		# Step 1.3: Uncompute the condition qbool's history graph
		# After restoring control context, reverse the operations that
		# produced this qbool (e.g., the comparison gates).  This must
		# happen AFTER popping the control so the inverse gates are not
		# controlled by the condition itself.
		if self.history:
			self.history.uncompute(_run_inverted_on_circuit)

		return False  # do not suppress exceptions

	def measure(self):
		"""Measure quantum integer, collapsing to classical value.

		Returns
		-------
		int
			Measured classical value.

		Notes
		-----
		Measurement collapses quantum superposition to classical state.
		Currently returns initialization value (simulation placeholder).
		Discards the history graph since qubits have collapsed and
		uncomputation is physically meaningless.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> result = a.measure()
		>>> result
		5
		"""
		self.history.discard()
		return self.value

	# --- Operation sections (inlined by build_preprocessor.py) ---
	# BEGIN include "qint_arithmetic.pxi"
	# ====================================================================
	# ARITHMETIC OPERATIONS
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef addition_inplace(self, other, int invert=False):
		# Cython-level addition: calls sequence generators directly,
		# with Toffoli dispatch (CLA/RCA, BK/KS, Clifford+T) handled
		# in toffoli_dispatch.pxi. No C hot path -- all logic in Cython.
		_mark_arithmetic_performed()
		cdef circuit_s *_circ = <circuit_s*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef unsigned int[:] control_qubits
		cdef sequence_t *seq
		cdef int result_bits
		cdef int pos
		cdef size_t gc_before, gc_delta
		cdef unsigned int layer_before
		cdef gate_counts_t range_counts

		# Extract self qubits (right-aligned in 64-element array)
		for i in range(self_bits):
			self_qa[i] = self.qubits[self_offset + i]

		# Extract control qubit if controlled
		if _controlled:
			control_qubits = (<qint> _control_bool).qubits
			control_qubit = control_qubits[63]

		if type(other) == int:
			classical_value = <int64_t>other

			# Compile-mode: record IR entry, skip gate emission.
			# Only for QFT mode — Toffoli mode falls through to direct dispatch
			# which produces correct gate types (X/CX/CCX instead of QFT rotations).
			if _is_compile_mode() and _circ.arithmetic_mode != 1:
				regs = tuple(self_qa[i] for i in range(self_bits))
				if _controlled:
					regs = regs + (control_qubit,)
				_uc_seq = CQ_add(self_bits, classical_value)
				_cc_seq = cCQ_add(self_bits, classical_value)
				_record_instruction(
					"add_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
					invert=bool(invert),
				)
				return self

			# Toffoli dispatch for CQ
			if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
				gc_before = _circ.gate_count
				layer_before = _circ.used_layer
				_toffoli_dispatch_cq(_circ, self_qa, self_bits,
				                     classical_value, invert,
				                     _controlled, control_qubit)
				gc_delta = _circ.gate_count - gc_before
				if _circ.simulate and _circ.used_layer > layer_before:
					range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
				else:
					range_counts.t_count = 0
				# Resolve both UC/CC gate counts from sequence generators
				_uc_seq_add = CQ_add(self_bits, classical_value)
				_cc_seq_add = cCQ_add(self_bits, classical_value)
				_uc_gc_add = <int>_uc_seq_add.total_gate_count if _uc_seq_add != NULL else 0
				_cc_gc_add = <int>_cc_seq_add.total_gate_count if _cc_seq_add != NULL else 0
				_record_operation(
					"add_cq",
					tuple(self_qa[i] for i in range(self_bits))
					+ ((control_qubit,) if _controlled else ()),
					gate_count=gc_delta,
					invert=bool(invert),
					controlled=bool(_controlled),
					depth=_circ.used_layer - layer_before,
					t_count=range_counts.t_count,
					uncontrolled_gate_count=_uc_gc_add,
					controlled_gate_count=_cc_gc_add,
				)
				return self

			# QFT path: build qubit array and call sequence generator
			pos = 0
			for i in range(self_bits):
				qa[pos] = self_qa[i]
				pos += 1
			if _controlled:
				qa[pos] = control_qubit
				pos += 1
				seq = cCQ_add(self_bits, classical_value)
			else:
				seq = CQ_add(self_bits, classical_value)
			if seq == NULL:
				return self
			layer_before = _circ.used_layer
			run_instruction(seq, qa, invert, <circuit_t*>_circ)
			if _circ.simulate and _circ.used_layer > layer_before:
				range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
			else:
				range_counts.t_count = 0
			# Resolve both UC/CC gate counts from sequence generators
			_uc_seq_add = CQ_add(self_bits, classical_value)
			_cc_seq_add = cCQ_add(self_bits, classical_value)
			_uc_gc_add = <int>_uc_seq_add.total_gate_count if _uc_seq_add != NULL else 0
			_cc_gc_add = <int>_cc_seq_add.total_gate_count if _cc_seq_add != NULL else 0
			_record_operation(
				"add_cq",
				tuple(qa[i] for i in range(pos)),
				gate_count=seq.total_gate_count,
				sequence_ptr=<unsigned long long>seq,
				invert=bool(invert),
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before,
				t_count=range_counts.t_count,
				uncontrolled_gate_count=_uc_gc_add,
				controlled_gate_count=_cc_gc_add,
			)
			return self

		if not isinstance(other, qint):
			raise ValueError()

		# Extract other qubits for quantum-quantum addition
		cdef int other_bits = (<qint> other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint> other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		result_bits = self_bits if self_bits > other_bits else other_bits

		# Compile-mode: record IR entry, skip gate emission.
		# Only for QFT mode — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			regs = (tuple(self_qa[i] for i in range(self_bits))
			        + tuple(other_qa[i] for i in range(other_bits)))
			if _controlled:
				regs = regs + (control_qubit,)
			_uc_seq = QQ_add(result_bits)
			_cc_seq = cQQ_add(result_bits)
			_record_instruction(
				"add_qq", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				invert=bool(invert),
			)
			return self

		# Toffoli dispatch for QQ
		if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
			gc_before = _circ.gate_count
			layer_before = _circ.used_layer
			_toffoli_dispatch_qq(_circ, self_qa, self_bits,
			                     other_qa, other_bits, invert,
			                     _controlled, control_qubit, result_bits)
			gc_delta = _circ.gate_count - gc_before
			if _circ.simulate and _circ.used_layer > layer_before:
				range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
			else:
				range_counts.t_count = 0
			# Resolve both UC/CC gate counts from sequence generators
			_uc_seq_add = QQ_add(result_bits)
			_cc_seq_add = cQQ_add(result_bits)
			_uc_gc_add = <int>_uc_seq_add.total_gate_count if _uc_seq_add != NULL else 0
			_cc_gc_add = <int>_cc_seq_add.total_gate_count if _cc_seq_add != NULL else 0
			_record_operation(
				"add_qq",
				tuple(self_qa[i] for i in range(self_bits))
				+ tuple(other_qa[i] for i in range(other_bits))
				+ ((control_qubit,) if _controlled else ()),
				gate_count=gc_delta,
				invert=bool(invert),
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before,
				t_count=range_counts.t_count,
				uncontrolled_gate_count=_uc_gc_add,
				controlled_gate_count=_cc_gc_add,
			)
			return self

		# QFT path: build qubit array and call sequence generator
		pos = 0
		for i in range(self_bits):
			qa[pos] = self_qa[i]
			pos += 1
		for i in range(other_bits):
			qa[pos] = other_qa[i]
			pos += 1
		if _controlled:
			qa[2 * result_bits] = control_qubit
			seq = cQQ_add(result_bits)
		else:
			seq = QQ_add(result_bits)
		if seq == NULL:
			return self
		layer_before = _circ.used_layer
		run_instruction(seq, qa, invert, <circuit_t*>_circ)
		if _circ.simulate and _circ.used_layer > layer_before:
			range_counts = circuit_gate_counts_range(_circ, layer_before, _circ.used_layer)
		else:
			range_counts.t_count = 0
		# Resolve both UC/CC gate counts from sequence generators
		_uc_seq_add = QQ_add(result_bits)
		_cc_seq_add = cQQ_add(result_bits)
		_uc_gc_add = <int>_uc_seq_add.total_gate_count if _uc_seq_add != NULL else 0
		_cc_gc_add = <int>_cc_seq_add.total_gate_count if _cc_seq_add != NULL else 0
		_record_operation(
			"add_qq",
			tuple(qa[i] for i in range(pos + (1 if _controlled else 0))),
			gate_count=seq.total_gate_count,
			sequence_ptr=<unsigned long long>seq,
			invert=bool(invert),
			controlled=bool(_controlled),
			depth=_circ.used_layer - layer_before,
			t_count=range_counts.t_count,
			uncontrolled_gate_count=_uc_gc_add,
			controlled_gate_count=_cc_gc_add,
		)
		return self

	def __add__(self, other: qint | int):
		"""Add quantum integers: self + other

		Result width is max(self.width, other.width). Overflow wraps (modular).

		Parameters
		----------
		other : qint or int
			Value to add.

		Returns
		-------
		qint
			New quantum integer containing sum.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> c = a + b
		>>> c.width
		8
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		# BUG-04 fix: zero-extend narrower operand so QQ_add gets result_width
		# qubits for both registers
		if type(other) == qint and (<qint>other).bits < result_width:
			padded_other = qint(width=result_width)
			padded_other ^= other
			a += padded_other
		else:
			a += other

		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= and += (Step 6.4 transparency)
		del (<qint>a).history.entries[:]
		_self_offset_h = 64 - self.bits
		_a_offset_h = 64 - (<qint>a).bits
		_qm = tuple((<qint>a).qubits[_a_offset_h + i] for i in range((<qint>a).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>a).history.append(0, _qm)
		if type(other) == qint and (<qint>other).bits < result_width:
			(<qint>a).history.add_child(padded_other)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(a)
		if type(other) == qint:
			(<qint>other).history.add_blocker(a)

		return a

	def __radd__(self, other: qint | int):
		"""Reverse addition: other + self (for int + qint).

		Parameters
		----------
		other : int
			Classical value to add.

		Returns
		-------
		qint
			New quantum integer containing sum.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = 3 + a  # Uses __radd__
		>>> b.width
		8
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# out of place addition - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		# BUG-04 fix: zero-extend narrower operand so QQ_add gets result_width
		# qubits for both registers
		if type(other) == qint and (<qint>other).bits < result_width:
			padded_other = qint(width=result_width)
			padded_other ^= other
			a += padded_other
		else:
			a += other

		a.operation_type = 'ADD'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= and += (Step 6.4 transparency)
		del (<qint>a).history.entries[:]
		_self_offset_h = 64 - self.bits
		_a_offset_h = 64 - (<qint>a).bits
		_qm = tuple((<qint>a).qubits[_a_offset_h + i] for i in range((<qint>a).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>a).history.append(0, _qm)
		if type(other) == qint and (<qint>other).bits < result_width:
			(<qint>a).history.add_child(padded_other)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(a)
		if type(other) == qint:
			(<qint>other).history.add_blocker(a)

		return a

	def __iadd__(self, other: qint | int):
		"""In-place addition: self += other

		Parameters
		----------
		other : qint or int
			Value to add.

		Returns
		-------
		qint
			Self (modified in-place via quantum gates).

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> a += 3
		>>> # a now represents |5+3> = |8>
		"""
		# Step 6.2: Blocker insertion — source operand references dest
		if type(other) == qint and other is not self:
			(<qint>other).history.add_blocker(self)
		# in place addition
		self.addition_inplace(other)
		# Step 6.4: Record history with kind for inverse cancellation
		_ia_offset = 64 - self.bits
		if type(other) == int:
			_ia_qm = tuple(self.qubits[_ia_offset + i] for i in range(self.bits)) + (int(other),)
		else:
			_ia_other_offset = 64 - (<qint>other).bits
			_ia_qm = tuple(self.qubits[_ia_offset + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_ia_other_offset + i] for i in range((<qint>other).bits))
		self.history.append(0, _ia_qm, kind='add')
		return self

	def __sub__(self, other: qint | int):
		"""Subtract quantum integers: self - other

		Result width is max(self.width, other.width). Underflow wraps (modular).

		Parameters
		----------
		other : qint or int
			Value to subtract.

		Returns
		-------
		qint
			New quantum integer containing difference.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> c = a - b
		>>> c.width
		8
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# out of place subtraction - result width is max of operands
		if type(other) == qint:
			result_width = max(self.bits, (<qint>other).bits)
		else:
			result_width = self.bits
		a = qint(width=result_width)
		a ^= self
		# BUG-04 fix: zero-extend narrower operand so QQ_add gets result_width
		# qubits for both registers
		if type(other) == qint and (<qint>other).bits < result_width:
			padded_other = qint(width=result_width)
			padded_other ^= other
			a -= padded_other
		else:
			a -= other

		a.operation_type = 'SUB'
		a.add_dependency(self)
		if type(other) == qint:
			a.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= and -= (Step 6.4 transparency)
		del (<qint>a).history.entries[:]
		_self_offset_h = 64 - self.bits
		_a_offset_h = 64 - (<qint>a).bits
		_qm = tuple((<qint>a).qubits[_a_offset_h + i] for i in range((<qint>a).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>a).history.append(0, _qm)
		if type(other) == qint and (<qint>other).bits < result_width:
			(<qint>a).history.add_child(padded_other)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(a)
		if type(other) == qint:
			(<qint>other).history.add_blocker(a)

		return a

	def __isub__(self, other: qint | int):
		"""In-place subtraction: self -= other

		Parameters
		----------
		other : qint or int
			Value to subtract.

		Returns
		-------
		qint
			Self (modified in-place via quantum gates).

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> a -= 3
		>>> # a now represents |5-3> = |2>
		"""
		# Step 6.2: Blocker insertion — source operand references dest
		if type(other) == qint and other is not self:
			(<qint>other).history.add_blocker(self)
		# in place subtraction (addition with invert)
		self.addition_inplace(other, invert = True)
		# Step 6.4: Record history with kind for inverse cancellation
		_is_offset = 64 - self.bits
		if type(other) == int:
			_is_qm = tuple(self.qubits[_is_offset + i] for i in range(self.bits)) + (int(other),)
		else:
			_is_other_offset = 64 - (<qint>other).bits
			_is_qm = tuple(self.qubits[_is_offset + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_is_other_offset + i] for i in range((<qint>other).bits))
		self.history.append(0, _is_qm, kind='sub')
		return self

	def __neg__(self):
		"""Two's complement negation: -self

		Returns a new qint whose value is (-self) % (2**width).

		Returns
		-------
		qint
			New quantum integer with negated value.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> b = -a
		>>> # b represents |(-5) % 16> = |11>
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		result -= self  # 0 - self = two's complement negation

		result.operation_type = 'NEG'
		result.add_dependency(self)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from -= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operand references the result
		self.history.add_blocker(result)

		return result

	def __rsub__(self, other):
		"""Reverse subtraction: other - self

		Handles the case where Python dispatches int - qint to qint.__rsub__.

		Parameters
		----------
		other : int or qint
			Left operand.

		Returns
		-------
		qint
			New quantum integer with value (other - self) % (2**width).

		Examples
		--------
		>>> a = qint(3, width=4)
		>>> b = 10 - a
		>>> # b represents |7>
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		if type(other) == int:
			result += other   # classical add into zero-init (OK, other is classical)
		else:
			result ^= other   # quantum copy other
		result -= self         # result = other - self

		result.operation_type = 'SUB'
		result.add_dependency(self)
		if type(other) == qint:
			result.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from +=, ^=, -= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) == qint:
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) == qint:
			(<qint>other).history.add_blocker(result)

		return result

	def __lshift__(self, int other):
		"""Left shift: self << other (other must be classical int).

		Implements left shift as multiplication by 2^other.

		Parameters
		----------
		other : int
			Shift amount (must be non-negative).

		Returns
		-------
		qint
			New quantum integer with value (self << other) % (2**width).

		Raises
		------
		ValueError
			If other is negative.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = a << 2
		>>> # b represents |12>
		"""
		if other < 0:
			raise ValueError("Negative shift count")
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result *= (1 << other)

		result.operation_type = 'LSHIFT'
		result.add_dependency(self)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operand references the result
		self.history.add_blocker(result)

		return result

	def __ilshift__(self, int other):
		"""In-place left shift: self <<= other"""
		result = self << other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __rshift__(self, int other):
		"""Right shift: self >> other (other must be classical int).

		Implements right shift as floor division by 2^other.

		Parameters
		----------
		other : int
			Shift amount (must be non-negative).

		Returns
		-------
		qint
			New quantum integer with value self >> other.

		Raises
		------
		ValueError
			If other is negative.

		Examples
		--------
		>>> a = qint(12, width=8)
		>>> b = a >> 2
		>>> # b represents |3>
		"""
		if other < 0:
			raise ValueError("Negative shift count")
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()
		result = qint(width=self.bits)
		result ^= self  # quantum copy
		if other > 0:
			result //= (1 << other)

		result.operation_type = 'RSHIFT'
		result.add_dependency(self)

		# Step 1.2: Record operation into result's per-variable history
		# Clear internal in-place entries from ^= (Step 6.4 transparency)
		del (<qint>result).history.entries[:]
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operand references the result
		self.history.add_blocker(result)

		return result

	def __irshift__(self, int other):
		"""In-place right shift: self >>= other"""
		result = self >> other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self


	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef multiplication_inplace(self, other, qint ret):
		# Cython-level multiplication: calls sequence generators directly,
		# with Toffoli path calling toffoli_mul_qq/cq directly.
		# No C hot path -- all logic in Cython.
		_mark_arithmetic_performed()
		cdef circuit_s *_circ = <circuit_s*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef unsigned int self_qa[64]
		cdef unsigned int ret_qa[64]
		cdef unsigned int other_qa[64]
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int ret_offset = 64 - (<qint>ret).bits
		cdef int i
		cdef int64_t classical_value = 0
		cdef unsigned int control_qubit = 0
		cdef unsigned int[:] control_qubits
		cdef unsigned int[:] ret_qubits_mv = (<qint>ret).qubits
		cdef int result_bits = (<qint>ret).bits
		cdef sequence_t *seq
		cdef int pos
		cdef size_t gc_before, gc_delta
		cdef unsigned int layer_before_mul
		cdef gate_counts_t range_counts_mul

		# Extract ret qubits (right-aligned in 64-element array)
		for i in range(result_bits):
			ret_qa[i] = ret_qubits_mv[ret_offset + i]

		# Extract self qubits
		for i in range(self_bits):
			self_qa[i] = self.qubits[self_offset + i]

		# Extract control qubit if controlled
		if _controlled:
			control_qubits = (<qint>_control_bool).qubits
			control_qubit = control_qubits[63]

		if type(other) == int:
			classical_value = <int64_t>other

			# Compile-mode: record IR entry, skip gate emission.
			# Only for QFT mode — Toffoli mode falls through to direct dispatch.
			if _is_compile_mode() and _circ.arithmetic_mode != 1:
				regs = (tuple(ret_qa[i] for i in range(result_bits))
				        + tuple(self_qa[i] for i in range(self_bits)))
				if _controlled:
					regs = regs + (control_qubit,)
				_uc_seq = CQ_mul(result_bits, classical_value)
				_cc_seq = cCQ_mul(result_bits, classical_value)
				_record_instruction(
					"mul_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				return ret

			# Toffoli dispatch for CQ
			if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
				gc_before = _circ.gate_count
				layer_before_mul = _circ.used_layer
				if _controlled:
					toffoli_cmul_cq(<circuit_t*>_circ, ret_qa, result_bits,
					                self_qa, self_bits, classical_value,
					                control_qubit)
				else:
					toffoli_mul_cq(<circuit_t*>_circ, ret_qa, result_bits,
					               self_qa, self_bits, classical_value)
				gc_delta = _circ.gate_count - gc_before
				if _circ.simulate and _circ.used_layer > layer_before_mul:
					range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
				else:
					range_counts_mul.t_count = 0
				_record_operation(
					"mul_cq",
					tuple(ret_qa[i] for i in range(result_bits))
					+ tuple(self_qa[i] for i in range(self_bits))
					+ ((control_qubit,) if _controlled else ()),
					gate_count=gc_delta,
					controlled=bool(_controlled),
					depth=_circ.used_layer - layer_before_mul,
					t_count=range_counts_mul.t_count,
				)
				return ret

			# QFT path: build qubit array and call sequence generator
			pos = 0
			for i in range(result_bits):
				qa[pos] = ret_qa[i]
				pos += 1
			for i in range(self_bits):
				qa[pos] = self_qa[i]
				pos += 1
			if _controlled:
				qa[pos] = control_qubit
				pos += 1
				seq = cCQ_mul(result_bits, classical_value)
			else:
				seq = CQ_mul(result_bits, classical_value)
			if seq == NULL:
				return ret
			layer_before_mul = _circ.used_layer
			run_instruction(seq, qa, 0, <circuit_t*>_circ)
			if _circ.simulate and _circ.used_layer > layer_before_mul:
				range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
			else:
				range_counts_mul.t_count = 0
			_record_operation(
				"mul_cq",
				tuple(qa[i] for i in range(pos)),
				gate_count=seq.total_gate_count,
				sequence_ptr=<unsigned long long>seq,
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before_mul,
				t_count=range_counts_mul.t_count,
			)
			return ret

		if not isinstance(other, qint):
			raise TypeError("Multiplication requires qint or int")

		# Extract other qubits for quantum-quantum multiplication
		cdef int other_bits = (<qint>other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits_mv = (<qint>other).qubits
		for i in range(other_bits):
			other_qa[i] = other_qubits_mv[other_offset + i]

		# Compile-mode: record IR entry, skip gate emission.
		# Only for QFT mode — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			regs = (tuple(ret_qa[i] for i in range(result_bits))
			        + tuple(self_qa[i] for i in range(self_bits))
			        + tuple(other_qa[i] for i in range(other_bits)))
			if _controlled:
				regs = regs + (control_qubit,)
			_uc_seq = QQ_mul(result_bits)
			_cc_seq = cQQ_mul(result_bits)
			_record_instruction(
				"mul_qq", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
			)
			return ret

		# Toffoli dispatch for QQ
		if _circ.arithmetic_mode == 1:  # ARITH_TOFFOLI
			gc_before = _circ.gate_count
			layer_before_mul = _circ.used_layer
			if _controlled:
				toffoli_cmul_qq(<circuit_t*>_circ, ret_qa, result_bits,
				                self_qa, self_bits, other_qa, other_bits,
				                control_qubit)
			else:
				toffoli_mul_qq(<circuit_t*>_circ, ret_qa, result_bits,
				               self_qa, self_bits, other_qa, other_bits)
			gc_delta = _circ.gate_count - gc_before
			if _circ.simulate and _circ.used_layer > layer_before_mul:
				range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
			else:
				range_counts_mul.t_count = 0
			_record_operation(
				"mul_qq",
				tuple(ret_qa[i] for i in range(result_bits))
				+ tuple(self_qa[i] for i in range(self_bits))
				+ tuple(other_qa[i] for i in range(other_bits))
				+ ((control_qubit,) if _controlled else ()),
				gate_count=gc_delta,
				controlled=bool(_controlled),
				depth=_circ.used_layer - layer_before_mul,
				t_count=range_counts_mul.t_count,
			)
			return ret

		# QFT path: build qubit array and call sequence generator
		pos = 0
		for i in range(result_bits):
			qa[pos] = ret_qa[i]
			pos += 1
		for i in range(self_bits):
			qa[pos] = self_qa[i]
			pos += 1
		for i in range(other_bits):
			qa[pos] = other_qa[i]
			pos += 1
		if _controlled:
			qa[pos] = control_qubit
			pos += 1
			seq = cQQ_mul(result_bits)
		else:
			seq = QQ_mul(result_bits)
		if seq == NULL:
			return ret
		layer_before_mul = _circ.used_layer
		run_instruction(seq, qa, 0, <circuit_t*>_circ)
		if _circ.simulate and _circ.used_layer > layer_before_mul:
			range_counts_mul = circuit_gate_counts_range(_circ, layer_before_mul, _circ.used_layer)
		else:
			range_counts_mul.t_count = 0
		# Resolve both UC/CC gate counts from sequence generators
		_record_operation(
			"mul_qq",
			tuple(qa[i] for i in range(pos)),
			gate_count=seq.total_gate_count,
			sequence_ptr=<unsigned long long>seq,
			controlled=bool(_controlled),
			depth=_circ.used_layer - layer_before_mul,
			t_count=range_counts_mul.t_count,
		)
		return ret

	def __mul__(self, other):
		"""Multiply quantum integers.

		Result width is max(self.width, other.width) per CONTEXT.md.
		Overflow wraps silently (modular arithmetic).

		Parameters
		----------
		other : qint or int
			Value to multiply by.

		Returns
		-------
		qint
			New qint containing product.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = qint(4, width=16)
		>>> c = a * b
		>>> c.width
		16
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# Determine result width
		if isinstance(other, qint):  # Includes qint subclasses like qint_mod
			result_width = max(self.bits, (<qint>other).bits)
		elif type(other) == int:
			result_width = self.bits
		else:
			raise TypeError("Multiplication requires qint or int")

		# BUG-COND-MUL-01 fix: prevent result registration in scope frame.
		# Multiplication results should never be auto-uncomputed by scope exit.
		# The user explicitly assigns them; cleanup is handled by GC, not scope.
		_saved_scope = current_scope_depth.get()
		current_scope_depth.set(0)

		# Allocate result with correct width
		result = qint(width=result_width)

		# Restore scope depth after result allocation
		current_scope_depth.set(_saved_scope)

		# Perform multiplication into result
		self.multiplication_inplace(other, result)

		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if isinstance(other, qint):
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	def __rmul__(self, other):
		"""Reverse multiplication: other * self (for int * qint).

		Parameters
		----------
		other : int
			Classical value to multiply by.

		Returns
		-------
		qint
			New qint containing product.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = 3 * a  # Uses __rmul__
		>>> b.width
		8
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circ_init = _get_circuit_initialized()

		# For int * qint, result width is qint's width
		if type(other) == int:
			result_width = self.bits
		else:
			# qint * qint should use __mul__, not __rmul__
			result_width = max(self.bits, (<qint>other).bits)

		# BUG-COND-MUL-01 fix: prevent result registration in scope frame
		_saved_scope_rmul = current_scope_depth.get()
		current_scope_depth.set(0)

		result = qint(width=result_width)

		current_scope_depth.set(_saved_scope_rmul)

		self.multiplication_inplace(other, result)

		result.operation_type = 'MUL'
		result.add_dependency(self)
		if isinstance(other, qint):
			result.add_dependency(other)

		# Step 1.2: Record operation into result's per-variable history
		_self_offset_h = 64 - self.bits
		_r_offset_h = 64 - (<qint>result).bits
		_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if isinstance(other, qint):
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		(<qint>result).history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	def __imul__(self, other):
		"""In-place multiplication: self *= other

		Note: Due to quantum mechanics, in-place multiplication allocates
		new qubits for the result and swaps qubit references.

		Parameters
		----------
		other : qint or int
			Value to multiply by.

		Returns
		-------
		qint
			Self (with swapped qubit references).

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> a *= 4
		>>> # a now references new qubits containing 3*4
		"""
		# Perform out-of-place multiplication
		result = self * other

		# Swap qubit arrays (like __iand__ pattern from Phase 6)
		cdef qint result_qint = <qint>result

		# Swap qubit references
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits

		# BUG-02 defensive fix: prevent GC from uncomputing/freeing the swapped-out
		# qubits when result_qint goes out of scope. The multiplication gates now
		# belong to self; result_qint holds self's old (input) qubits which should
		# not be reversed or freed by result_qint's destructor.
		result_qint._is_uncomputed = True
		result_qint.allocated_qubits = False

		return self

	# END include "qint_arithmetic.pxi"
	# BEGIN include "qint_bitwise.pxi"
	# ====================================================================
	# BITWISE OPERATIONS
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	def __and__(self, other):
		"""Bitwise AND: self & other

		Result width is max(self.width, other.width).

		Parameters
		----------
		other : qint or int
			Value to AND with.

		Returns
		-------
		qint
			New quantum integer containing bitwise AND result.

		Examples
		--------
		>>> a = qint(0b1101, width=4)
		>>> b = qint(0b1011, width=4)
		>>> c = a & b
		>>> # c represents |1001>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef int i
		cdef int _self_pad, _other_pad
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int[:] result_qubits
		cdef unsigned int[:] other_qubits
		cdef unsigned int[:] pad_qubits
		cdef size_t gc_before_and, gc_delta_and
		cdef unsigned int layer_before_and
		cdef gate_counts_t range_counts_and

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			result = qint(width=result_bits)
			result.add_dependency(self)
			if type(other) != int:
				result.add_dependency(other)
			result.operation_type = 'AND'
			self_offset = 64 - self.bits
			result_offset = 64 - result_bits
			regs = tuple((<qint>result).qubits[result_offset + i] for i in range(result_bits))
			regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
			if type(other) != int and isinstance(other, qint):
				other_offset = 64 - (<qint>other).bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
			if type(other) == int:
				_uc_seq = CQ_and(result_bits, other)
				_cc_seq = cCQ_and(result_bits, other)
				_record_instruction(
					"and_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			else:
				_uc_seq = Q_and(result_bits)
				_cc_seq = cQ_and(result_bits)
				_record_instruction(
					"and_qq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			self.history.add_blocker(result)
			if type(other) != int and isinstance(other, qint):
				(<qint>other).history.add_blocker(result)
			return result

		# Phase 84: Validate qubit_array bounds before writes
		# AND uses up to 3*result_bits slots: [output:N], [self:N], [other:N]
		validate_qubit_slots(3 * result_bits, "__and__")

		# Allocate padding ancilla BEFORE result so result gets highest qubit indices
		# (result must be last-allocated for bitstring[:width] extraction to work)
		_self_pad_qint = None
		_other_pad_qint = None
		if self.bits < result_bits:
			_self_pad_qint = qint(width=result_bits - self.bits)
		if type(other) != int and isinstance(other, qint):
			if (<qint>other).bits < result_bits:
				_other_pad_qint = qint(width=result_bits - (<qint>other).bits)

		# Allocate result (ancilla qubits) -- must be last for extraction
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:  # Don't track classical operands
			result.add_dependency(other)
		result.operation_type = 'AND'

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_and expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		# Qubit storage is LSB-first: index 0 = LSB
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		# CYT-03: Replace slice with explicit loop for memory view optimization
		result_qubits = result.qubits
		for i in range(result_bits):
			qubit_array[i] = result_qubits[result_offset + i]
		# Self qubits (LSB positions) - at position result_bits
		for i in range(self.bits):
			qubit_array[result_bits + i] = self.qubits[self_offset + i]
		# Zero-extend self if narrower: use pre-allocated padding for MSB
		if _self_pad_qint is not None:
			_self_pad = result_bits - self.bits
			pad_qubits = _self_pad_qint.qubits
			for i in range(_self_pad):
				qubit_array[result_bits + self.bits + i] = pad_qubits[64 - _self_pad + i]

		if type(other) == int:
			# Classical-quantum AND
			# CQ_and expects: [0:bits] = output, [bits:2*bits] = quantum operand
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum AND not yet supported")
			else:
				seq = CQ_and(result_bits, other)
		else:
			# Quantum-quantum AND
			other_offset = 64 - (<qint>other).bits
			other_qubits = (<qint>other).qubits
			for i in range((<qint>other).bits):
				qubit_array[2*result_bits + i] = other_qubits[other_offset + i]
			# Zero-extend other if narrower: use pre-allocated padding for MSB
			if _other_pad_qint is not None:
				_other_pad = result_bits - (<qint>other).bits
				pad_qubits = _other_pad_qint.qubits
				for i in range(_other_pad):
					qubit_array[2*result_bits + (<qint>other).bits + i] = pad_qubits[64 - _other_pad + i]

			if _controlled:
				# Controlled quantum-quantum AND: decompose C-CCX into
				# standard Toffolis + ancilla.
				# For each bit i, C-CCX(output[i], A[i], B[i], ext_ctrl)
				# decomposes as:
				#   CCX(ancilla, A[i], ext_ctrl)  -- partial AND
				#   CCX(output[i], ancilla, B[i]) -- use partial AND
				#   CCX(ancilla, A[i], ext_ctrl)  -- uncompute ancilla
				_control_bool = _get_control_bool()
				_ctrl_qubit = (<qint>_control_bool).qubits[63]
				from quantum_language._gates import emit_ccx as _emit_ccx
				from quantum_language.qbool import qbool as _qbool_cls
				gc_before_and = (<circuit_s*>_circuit).gate_count
				layer_before_and = (<circuit_s*>_circuit).used_layer
				_and_ancilla = _qbool_cls()
				_anc_qubit = _and_ancilla.qubits[63]
				for i in range(result_bits):
					_a_qubit = qubit_array[result_bits + i]
					_b_qubit = qubit_array[2 * result_bits + i]
					_out_qubit = qubit_array[i]
					_emit_ccx(_anc_qubit, _a_qubit, _ctrl_qubit)
					_emit_ccx(_out_qubit, _anc_qubit, _b_qubit)
					_emit_ccx(_anc_qubit, _a_qubit, _ctrl_qubit)
				# Free ancilla
				_and_ancilla._is_uncomputed = True
				_and_ancilla.allocated_qubits = False
				from ._core import _deallocate_qubits
				_deallocate_qubits(_and_ancilla.allocated_start, 1)
				gc_delta_and = (<circuit_s*>_circuit).gate_count - gc_before_and
				if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_and:
					range_counts_and = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_and, (<circuit_s*>_circuit).used_layer)
				else:
					range_counts_and.t_count = 0
				_total_and = 3 * result_bits
				_record_operation(
					"and",
					tuple(qubit_array[i] for i in range(_total_and)),
					gate_count=gc_delta_and,
					controlled=bool(_controlled),
					depth=(<circuit_s*>_circuit).used_layer - layer_before_and,
					t_count=range_counts_and.t_count,
				)
				_qm = tuple(qubit_array[i] for i in range(_total_and))
				result.history.append(0, _qm)
				# Step 6.2: Blocker insertion — source operands reference the result
				self.history.add_blocker(result)
				if type(other) != int and isinstance(other, qint):
					(<qint>other).history.add_blocker(result)
				return result
			else:
				seq = Q_and(result_bits)

		arr = qubit_array
		gc_before_and = (<circuit_s*>_circuit).gate_count
		layer_before_and = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		gc_delta_and = (<circuit_s*>_circuit).gate_count - gc_before_and
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_and:
			range_counts_and = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_and, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_and.t_count = 0
		_record_operation(
			"and",
			tuple(qubit_array[i] for i in range(3 * result_bits if type(other) != int else 2 * result_bits)),
			sequence_ptr=<unsigned long long>seq,
			gate_count=gc_delta_and,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_and,
			t_count=range_counts_and.t_count,
		)

		# Step 1.2: Record operation into result's per-variable history
		# Must match the exact qubit_array layout passed to run_instruction,
		# including zero-extension padding qubits for narrower operands.
		_total_and = 3 * result_bits if (type(other) != int and isinstance(other, qint)) else 2 * result_bits
		_qm = tuple(qubit_array[i] for i in range(_total_and))
		result.history.append(<unsigned long long>seq, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) != int and isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	def __iand__(self, other):
		"""In-place AND: self &= other

		Parameters
		----------
		other : qint or int
			Value to AND with.

		Returns
		-------
		qint
			Self (with swapped qubit references).

		Examples
		--------
		>>> a = qint(0b1101, width=4)
		>>> a &= 0b1011
		>>> # a now represents |1001>
		"""
		cdef qint result_qint
		result = self & other
		result_qint = <qint>result
		# Swap qubit arrays using cdef access
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __rand__(self, other):
		"""Reverse AND for int & qint."""
		return self & other

	def __or__(self, other):
		"""Bitwise OR: self | other

		Result width is max(self.width, other.width).

		Parameters
		----------
		other : qint or int
			Value to OR with.

		Returns
		-------
		qint
			New quantum integer containing bitwise OR result.

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> b = qint(0b0011, width=4)
		>>> c = a | b
		>>> # c represents |1111>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef size_t gc_before_or, gc_delta_or
		cdef unsigned int layer_before_or
		cdef gate_counts_t range_counts_or

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			result = qint(width=result_bits)
			result.add_dependency(self)
			if type(other) != int:
				result.add_dependency(other)
			result.operation_type = 'OR'
			self_offset = 64 - self.bits
			result_offset = 64 - result_bits
			regs = tuple((<qint>result).qubits[result_offset + i] for i in range(result_bits))
			regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
			if type(other) != int and isinstance(other, qint):
				other_offset = 64 - (<qint>other).bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
			if type(other) == int:
				_uc_seq = CQ_or(result_bits, other)
				_cc_seq = cCQ_or(result_bits, other)
				_record_instruction(
					"or_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			else:
				_uc_seq = Q_or(result_bits)
				_cc_seq = cQ_or(result_bits)
				_record_instruction(
					"or_qq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			self.history.add_blocker(result)
			if type(other) != int and isinstance(other, qint):
				(<qint>other).history.add_blocker(result)
			return result

		# Phase 84: Validate qubit_array bounds before writes
		# OR uses up to 3*result_bits slots: [output:N], [self:N], [other:N]
		validate_qubit_slots(3 * result_bits, "__or__")

		# Allocate padding ancilla BEFORE result so result gets highest qubit indices
		_self_pad_qint = None
		_other_pad_qint = None
		if self.bits < result_bits:
			_self_pad_qint = qint(width=result_bits - self.bits)
		if type(other) != int and isinstance(other, qint):
			if (<qint>other).bits < result_bits:
				_other_pad_qint = qint(width=result_bits - (<qint>other).bits)

		# Allocate result (ancilla qubits) -- must be last for extraction
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:
			result.add_dependency(other)
		result.operation_type = 'OR'

		# Build qubit array: [output:N], [self:N], [other:N]
		# Q_or expects: [0:bits] = output, [bits:2*bits] = A, [2*bits:3*bits] = B
		# Qubit storage is LSB-first: index 0 = LSB
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Output qubits (result) - at position 0
		qubit_array[:result_bits] = result.qubits[result_offset:64]
		# Self qubits (LSB positions) - at position result_bits
		qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]
		# Zero-extend self if narrower
		if _self_pad_qint is not None:
			_self_pad = result_bits - self.bits
			qubit_array[result_bits + self.bits:2*result_bits] = _self_pad_qint.qubits[64 - _self_pad:64]

		if type(other) == int:
			# Classical-quantum OR
			# CQ_or expects: [0:bits] = output, [bits:2*bits] = quantum operand
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum OR not yet supported")
			else:
				seq = CQ_or(result_bits, other)
		else:
			# Quantum-quantum OR
			other_offset = 64 - (<qint>other).bits
			qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = (<qint>other).qubits[other_offset:64]
			# Zero-extend other if narrower
			if _other_pad_qint is not None:
				_other_pad = result_bits - (<qint>other).bits
				qubit_array[2*result_bits + (<qint>other).bits:3*result_bits] = _other_pad_qint.qubits[64 - _other_pad:64]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum OR not yet supported")
			else:
				seq = Q_or(result_bits)

		arr = qubit_array
		gc_before_or = (<circuit_s*>_circuit).gate_count
		layer_before_or = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		gc_delta_or = (<circuit_s*>_circuit).gate_count - gc_before_or
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_or:
			range_counts_or = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_or, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_or.t_count = 0
		_record_operation(
			"or",
			tuple(qubit_array[i] for i in range(3 * result_bits if type(other) != int else 2 * result_bits)),
			sequence_ptr=<unsigned long long>seq,
			gate_count=gc_delta_or,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_or,
			t_count=range_counts_or.t_count,
		)

		# Step 1.2: Record operation into result's per-variable history
		# Must match the exact qubit_array layout passed to run_instruction,
		# including zero-extension padding qubits for narrower operands.
		_total_or = 3 * result_bits if (type(other) != int and isinstance(other, qint)) else 2 * result_bits
		_qm = tuple(qubit_array[i] for i in range(_total_or))
		result.history.append(<unsigned long long>seq, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) != int and isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	def __ior__(self, other):
		"""In-place OR: self |= other

		Parameters
		----------
		other : qint or int
			Value to OR with.

		Returns
		-------
		qint
			Self (with swapped qubit references).

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> a |= 0b0011
		>>> # a now represents |1111>
		"""
		cdef qint result_qint
		result = self | other
		result_qint = <qint>result
		# Swap qubit arrays using cdef access
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __ror__(self, other):
		"""Reverse OR for int | qint."""
		return self | other

	@cython.boundscheck(False)
	@cython.wraparound(False)
	def __xor__(self, other):
		"""Bitwise XOR: self ^ other

		Result width is max(self.width, other.width).

		Parameters
		----------
		other : qint or int
			Value to XOR with.

		Returns
		-------
		qint
			New quantum integer containing bitwise XOR result.

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> b = qint(0b0110, width=4)
		>>> c = a ^ b
		>>> # c represents |1010>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int result_bits
		cdef int self_offset, result_offset, other_offset
		cdef int classical_width
		cdef int i
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef unsigned int[:] result_qubits
		cdef unsigned int[:] other_qubits
		cdef size_t gc_before_xor, gc_delta_xor
		cdef unsigned int layer_before_xor
		cdef gate_counts_t range_counts_xor

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Determine result width
		if type(other) == int:
			classical_width = other.bit_length() if other > 0 else 1
			result_bits = max(self.bits, classical_width)
		elif isinstance(other, qint):
			result_bits = max(self.bits, (<qint>other).bits)
		else:
			raise TypeError("Operand must be qint or int")

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			result = qint(width=result_bits)
			result.add_dependency(self)
			if type(other) != int:
				result.add_dependency(other)
			result.operation_type = 'XOR'
			self_offset = 64 - self.bits
			result_offset = 64 - result_bits
			regs = tuple((<qint>result).qubits[result_offset + i] for i in range(result_bits))
			regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
			if type(other) != int and isinstance(other, qint):
				other_offset = 64 - (<qint>other).bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
			_uc_seq = Q_xor(self.bits)
			_cc_seq = cQ_xor(self.bits)
			_record_instruction(
				"xor", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
			)
			self.history.add_blocker(result)
			if type(other) != int and isinstance(other, qint):
				(<qint>other).history.add_blocker(result)
			return result

		# Phase 84: Validate qubit_array bounds before writes
		# XOR uses up to 2*result_bits slots: [target:N], [source:N]
		validate_qubit_slots(2 * result_bits, "__xor__")

		# Allocate result (ancilla qubits)
		result = qint(width=result_bits)

		# Register dependencies
		result.add_dependency(self)
		if type(other) != int:
			result.add_dependency(other)
		result.operation_type = 'XOR'

		# Q_xor expects: [0:bits] = target, [bits:2*bits] = source
		# XOR modifies target in-place: target ^= source
		# So we need to first copy self to result, then XOR other into result

		# Copy self qubits to result using CNOT pattern
		self_offset = 64 - self.bits
		result_offset = 64 - result_bits

		# Capture gate_count before multi-step XOR
		gc_before_xor = (<circuit_s*>_circuit).gate_count
		layer_before_xor = (<circuit_s*>_circuit).used_layer

		# First, copy self to result by XORing self into result (result starts at 0)
		# CYT-03: Replace slice with explicit loop for memory view optimization
		result_qubits = result.qubits
		for i in range(self.bits):
			qubit_array[i] = result_qubits[result_offset + i]
		for i in range(self.bits):
			qubit_array[self.bits + i] = self.qubits[self_offset + i]
		arr = qubit_array
		seq = Q_xor(self.bits)  # XOR self into result (copying self to result)
		run_instruction(seq, &arr[0], False, _circuit)

		# Now XOR other into result
		if type(other) == int:
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")
			else:
				for i in range(result_bits):
					if (other >> i) & 1:
						qubit_array[0] = result_qubits[64 - result_bits + i]
						arr = qubit_array
						seq = Q_not(1)
						run_instruction(seq, &arr[0], False, _circuit)
		else:
			other_offset = 64 - (<qint>other).bits
			for i in range((<qint>other).bits):
				qubit_array[i] = result_qubits[result_offset + i]
			other_qubits = (<qint>other).qubits
			for i in range((<qint>other).bits):
				qubit_array[(<qint>other).bits + i] = other_qubits[other_offset + i]

			if _controlled:
				raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")
			else:
				seq = Q_xor((<qint>other).bits)

			arr = qubit_array
			run_instruction(seq, &arr[0], False, _circuit)

		# Record XOR operation on the DAG
		gc_delta_xor = (<circuit_s*>_circuit).gate_count - gc_before_xor
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_xor:
			range_counts_xor = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_xor, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_xor.t_count = 0
		_record_operation(
			"xor",
			tuple(result_qubits[result_offset + i] for i in range(result_bits))
			+ tuple(self.qubits[self_offset + i] for i in range(self.bits))
			+ (tuple((<qint>other).qubits[64 - (<qint>other).bits + i]
			         for i in range((<qint>other).bits))
			   if type(other) != int else ()),
			gate_count=gc_delta_xor,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_xor,
			t_count=range_counts_xor.t_count,
		)

		# Step 1.2: Record operation into result's per-variable history
		_self_offset_h = 64 - self.bits
		_qm = tuple(result_qubits[result_offset + i] for i in range(result_bits)) \
			+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
		if type(other) != int and isinstance(other, qint):
			_other_offset_h = 64 - (<qint>other).bits
			_qm = _qm + tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
		result.history.append(0, _qm)

		# Step 6.2: Blocker insertion — source operands reference the result
		self.history.add_blocker(result)
		if type(other) != int and isinstance(other, qint):
			(<qint>other).history.add_blocker(result)

		return result

	@cython.boundscheck(False)
	@cython.wraparound(False)
	def __ixor__(self, other):
		"""In-place XOR: self ^= other

		Modifies qubits directly (true in-place operation).

		Parameters
		----------
		other : qint or int
			Value to XOR with.

		Returns
		-------
		qint
			Self (modified in-place).

		Examples
		--------
		>>> a = qint(0b1100, width=4)
		>>> a ^= 0b0110
		>>> # a now represents |1010>
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int i
		cdef int xor_bits
		cdef size_t gc_before_ixor, gc_delta_ixor
		cdef unsigned int layer_before_ixor
		cdef gate_counts_t range_counts_ixor

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			regs = tuple(self.qubits[self_offset + i] for i in range(self_bits))
			if type(other) == int:
				_uc_seq = Q_not(1)
				_cc_seq = cQ_not(1)
				_record_instruction(
					"ixor_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			elif isinstance(other, qint):
				if other is not self:
					(<qint>other).history.add_blocker(self)
				_cm_other_offset = 64 - (<qint>other).bits
				_cm_xor_bits = self_bits if self_bits < (<qint>other).bits else (<qint>other).bits
				regs = tuple(self.qubits[self_offset + i] for i in range(_cm_xor_bits))
				regs = regs + tuple(
					(<qint>other).qubits[_cm_other_offset + i]
					for i in range(_cm_xor_bits)
				)
				_uc_seq = Q_xor(_cm_xor_bits)
				_cc_seq = cQ_xor(_cm_xor_bits)
				_record_instruction(
					"ixor_qq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
			return self

		if type(other) == int:
			if _controlled:
				raise NotImplementedError("Controlled classical-quantum XOR not yet supported")

			# CQ path: for each set bit in classical value, apply Q_not(1)
			gc_before_ixor = (<circuit_s*>_circuit).gate_count
			layer_before_ixor = (<circuit_s*>_circuit).used_layer
			for i in range(self_bits):
				if ((<int64_t>other) >> i) & 1:
					qubit_array[0] = self.qubits[self_offset + i]
					arr = qubit_array
					seq = Q_not(1)
					run_instruction(seq, &arr[0], False, _circuit)
			gc_delta_ixor = (<circuit_s*>_circuit).gate_count - gc_before_ixor
			if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_ixor:
				range_counts_ixor = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_ixor, (<circuit_s*>_circuit).used_layer)
			else:
				range_counts_ixor.t_count = 0
			_record_operation(
				"ixor_cq",
				tuple(self.qubits[self_offset + i] for i in range(self_bits)),
				gate_count=gc_delta_ixor,
				controlled=bool(_controlled),
				depth=(<circuit_s*>_circuit).used_layer - layer_before_ixor,
				t_count=range_counts_ixor.t_count,
			)
			# Step 6.4: Record history with kind for inverse cancellation
			_ixor_qm = tuple(self.qubits[self_offset + i] for i in range(self_bits)) + (int(other),)
			self.history.append(0, _ixor_qm, kind='xor')
			return self

		if not isinstance(other, qint):
			raise TypeError("Operand must be qint or int")

		if _controlled:
			raise NotImplementedError("Controlled quantum-quantum XOR not yet supported")

		# Step 6.2: Blocker insertion — source operand references dest
		if other is not self:
			(<qint>other).history.add_blocker(self)

		# QQ path: self ^= other using Q_xor
		# Layout: [0..xor_bits-1] = self (target), [xor_bits..2*xor_bits-1] = other (source)
		cdef int other_bits = (<qint>other).bits
		cdef int other_offset = 64 - other_bits
		cdef unsigned int[:] other_qubits = (<qint>other).qubits
		xor_bits = self_bits if self_bits < other_bits else other_bits

		# Phase 84: Validate qubit_array bounds before writes
		validate_qubit_slots(2 * xor_bits, "__ixor__")

		for i in range(xor_bits):
			qubit_array[i] = self.qubits[self_offset + i]
		for i in range(xor_bits):
			qubit_array[xor_bits + i] = other_qubits[other_offset + i]

		arr = qubit_array
		seq = Q_xor(xor_bits)
		gc_before_ixor = (<circuit_s*>_circuit).gate_count
		layer_before_ixor = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		gc_delta_ixor = (<circuit_s*>_circuit).gate_count - gc_before_ixor
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_ixor:
			range_counts_ixor = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_ixor, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_ixor.t_count = 0
		_record_operation(
			"ixor_qq",
			tuple(qubit_array[i] for i in range(2 * xor_bits)),
			sequence_ptr=<unsigned long long>seq,
			gate_count=gc_delta_ixor,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_ixor,
			t_count=range_counts_ixor.t_count,
		)
		# Step 6.4: Record history with kind for inverse cancellation
		_ixor_qm = tuple(self.qubits[self_offset + i] for i in range(xor_bits)) \
			+ tuple(other_qubits[other_offset + i] for i in range(xor_bits))
		self.history.append(0, _ixor_qm, kind='xor')
		return self

	def __rxor__(self, other):
		"""Reverse XOR for int ^ qint."""
		return self ^ other

	def __invert__(self):
		"""Bitwise NOT: ~self

		Inverts all bits in-place.

		Returns
		-------
		qint
			Self (modified in-place).

		Examples
		--------
		>>> a = qint(0b1010, width=4)
		>>> ~a
		>>> # a now represents |0101>

		Notes
		-----
		Applies X gate to each qubit (parallel execution).
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef size_t gc_before_not, gc_delta_not
		cdef unsigned int layer_before_not
		cdef gate_counts_t range_counts_not

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()

		# Compile-mode: record IR entry, skip gate emission
		if _is_compile_mode():
			self_offset = 64 - self.bits
			regs = tuple(self.qubits[self_offset + i] for i in range(self.bits))
			_uc_seq = Q_not(self.bits)
			_cc_seq = cQ_not(self.bits)
			_record_instruction(
				"not", regs,
				uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
				controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
			)
			return self

		# Phase 84: Validate qubit_array bounds before writes
		# NOT uses up to self.bits + 1 slots (controlled case)
		validate_qubit_slots(self.bits + 1, "__invert__")

		# Use width-parameterized NOT for multi-bit qints
		self_offset = 64 - self.bits

		if _controlled:
			# Controlled NOT: [0:bits] = target, [bits] = control
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			qubit_array[self.bits] = (<qint> _control_bool).qubits[63]
			seq = cQ_not(self.bits)
		else:
			# Uncontrolled NOT: [0:bits] = target
			qubit_array[:self.bits] = self.qubits[self_offset:64]
			seq = Q_not(self.bits)

		arr = qubit_array
		gc_before_not = (<circuit_s*>_circuit).gate_count
		layer_before_not = (<circuit_s*>_circuit).used_layer
		run_instruction(seq, &arr[0], False, _circuit)
		gc_delta_not = (<circuit_s*>_circuit).gate_count - gc_before_not
		if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_not:
			range_counts_not = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_not, (<circuit_s*>_circuit).used_layer)
		else:
			range_counts_not.t_count = 0
		_record_operation(
			"not",
			tuple(qubit_array[i] for i in range(self.bits + (1 if _controlled else 0))),
			sequence_ptr=<unsigned long long>seq,
			gate_count=gc_delta_not,
			controlled=bool(_controlled),
			depth=(<circuit_s*>_circuit).used_layer - layer_before_not,
			t_count=range_counts_not.t_count,
		)

		return self

	# ====================================================================
	# QUANTUM COPY OPERATIONS
	# Phase 42: CNOT-based state copying for quantum expressions
	# ====================================================================

	def copy(self):
		"""Create a quantum copy of this integer.

		Allocates fresh qubits and applies CNOT gates from each source qubit
		to the corresponding target qubit, producing a new qint whose
		computational-basis measurement outcome matches the source.

		Returns
		-------
		qint
			New quantum integer with CNOT-entangled fresh qubits.

		Raises
		------
		ValueError
			If this qint has been uncomputed.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> b = a.copy()
		>>> b.width
		4

		Notes
		-----
		The copy has distinct qubits from the source (no shared references).
		The copy participates in scope-based automatic uncomputation.
		For computational basis states, the copy measures to the same value.
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset, result_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()

		self._check_not_uncomputed()

		# Phase 84: Validate qubit_array bounds before writes
		# copy uses 2*self.bits slots: [target:N], [source:N]
		validate_qubit_slots(2 * self.bits, "copy")

		# Allocate fresh result qint with |0> qubits
		result = qint(width=self.bits)

		# Apply CNOTs: source -> result (XOR pattern, result starts at 0)
		self_offset = 64 - self.bits
		result_offset = 64 - result.bits
		qubit_array[:self.bits] = result.qubits[result_offset:result_offset + self.bits]
		qubit_array[self.bits:2*self.bits] = self.qubits[self_offset:64]
		arr = qubit_array
		seq = Q_xor(self.bits)
		run_instruction(seq, &arr[0], False, _circuit)

		result.operation_type = 'COPY'
		result.add_dependency(self)

		return result

	def copy_onto(self, target):
		"""XOR-copy this integer's state onto an existing target.

		Applies CNOT gates from each source qubit to the corresponding
		target qubit: target ^= self. If target starts at |0>, this
		produces a copy of self. If target is non-zero, this XORs self
		into target.

		Parameters
		----------
		target : qint
			Target quantum integer to copy onto. Must have same bit width.

		Raises
		------
		ValueError
			If target width does not match source width.
		ValueError
			If this qint has been uncomputed.
		TypeError
			If target is not a qint.

		Examples
		--------
		>>> a = qint(5, width=4)
		>>> b = qint(width=4)
		>>> a.copy_onto(b)
		>>> # b now holds a copy of a's state

		Notes
		-----
		This is a raw CNOT operation. The caller manages the target's
		lifecycle and uncomputation. No layer tracking or dependency
		is set on the target by this method.
		"""
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset, target_offset
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()

		self._check_not_uncomputed()

		if not isinstance(target, qint):
			raise TypeError("copy_onto target must be a qint")

		if (<qint>target).bits != self.bits:
			raise ValueError(
				f"Width mismatch: source has {self.bits} bits, "
				f"target has {(<qint>target).bits} bits"
			)

		# Phase 84: Validate qubit_array bounds before writes
		# copy_onto uses 2*self.bits slots: [target:N], [source:N]
		validate_qubit_slots(2 * self.bits, "copy_onto")

		# Apply CNOTs: source -> target
		self_offset = 64 - self.bits
		target_offset = 64 - (<qint>target).bits
		qubit_array[:self.bits] = (<qint>target).qubits[target_offset:target_offset + self.bits]
		qubit_array[self.bits:2*self.bits] = self.qubits[self_offset:64]
		arr = qubit_array
		seq = Q_xor(self.bits)
		run_instruction(seq, &arr[0], False, _circuit)

	def __getitem__(self, item: int):
		"""Access individual qubit as qbool: self[index]

		Parameters
		----------
		item : int
			Qubit index (right-aligned, 0 = LSB).

		Returns
		-------
		qbool
			Single-qubit quantum boolean.

		Examples
		--------
		>>> a = qint(0b1010, width=4)
		>>> bit1 = a[1]  # Second bit from right (LSB=0)
		>>> # bit1 is qbool representing |1>
		"""
		from quantum_language.qbool import qbool
		if item < 0 or item >= self.bits:
			raise IndexError(f"qubit index {item} out of range for qint with width {self.bits}")
		# Use uint32 dtype to match qint.qubits memory view type
		bit_list = np.zeros(64, dtype=np.uint32)
		bit_list[-1] = self.qubits[64 - self.bits + item]
		a = qbool(create_new = False, bit_list = bit_list)
		return a

	# END include "qint_bitwise.pxi"
	# BEGIN include "qint_comparison.pxi"
	# ====================================================================
	# COMPARISON OPERATIONS
	# ====================================================================

	def __eq__(self, other):
		"""Equality comparison: self == other

		Uses C-level CQ_equal_width for qint == int (O(n) gates).
		Uses subtract-add-back pattern for qint == qint.

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating equality.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(5, width=8)
		>>> result = (a == b)
		>>> # result is qbool representing |True>

		Notes
		-----
		qint == int: Uses C-level CQ_equal_width circuit.
		qint == qint: Uses subtract-add-back pattern (a-=b, check a==0, a+=b).
		Phase 74-03: AND-ancilla allocated for MCX decomposition (bits>=3 uncontrolled,
		bits>=2 controlled).
		"""
		from .qbool import qbool
		cdef sequence_t *seq
		cdef unsigned int[:] arr
		cdef int self_offset
		cdef int start
		cdef int num_and_anc
		cdef unsigned int and_anc_start
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef bint _controlled = _get_controlled()
		cdef object _control_bool = _get_control_bool()
		cdef qubit_allocator_t *alloc
		cdef size_t gc_before_eq, gc_delta_eq
		cdef unsigned int layer_before_eq
		cdef gate_counts_t range_counts_eq

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Handle qint == qint case first (must come before int check)
		if type(other) == qint:
			# Self-comparison optimization: a == a is always True
			if self is other:
				return qbool(True)

			# Subtract-add-back pattern: (a - b) == 0, then restore a
			# Save history length so we can trim entries added by internal -= / +=
			_eq_hist_len = len(self.history)
			# 1. In-place subtraction: self -= other
			self -= other

			# 2. Compare to zero: result = (self == 0)
			result = self == 0  # Recursive call uses qint == int path

			# 3. Restore operand: self += other
			self += other
			# Trim internal in-place history entries (Step 6.4 transparency)
			del self.history.entries[_eq_hist_len:]

			# Track dependencies on compared qints
			# Clear dependencies from recursive (self == 0) call, replace with actual operands
			result.dependency_parents = []
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'EQ'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_other_offset_h = 64 - (<qint>other).bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operands reference the result
			self.history.add_blocker(result)
			(<qint>other).history.add_blocker(result)

			return result

		# Handle qint == int case using C-level CQ_equal_width
		if type(other) == int:
			# Phase 84: Validate qubit_array bounds before writes
			# eq uses up to 1 + self.bits + 1 + (self.bits - 1) slots
			validate_qubit_slots(2 * self.bits + 2, "__eq__")

			# Classical overflow check: if value doesn't fit in bits, not equal
			# For unsigned interpretation: value must be in [0, 2^bits - 1]
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0 or other > max_val:
				# Overflow: value outside range - definitely not equal
				# Return qbool initialized to |0> (False)
				return qbool(False)

			# Compile-mode: record IR entry, skip gate emission
			if _is_compile_mode():
				result = qbool()
				_uc_seq = CQ_equal_width(self.bits, other)
				_cc_seq = cCQ_equal_width(self.bits, other)
				self_offset = 64 - self.bits
				regs = ((<qint>result).qubits[63],)
				regs = regs + tuple(
					self.qubits[self_offset + (self.bits - 1 - i)]
					for i in range(self.bits)
				)
				_record_instruction(
					"eq_cq", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				result.add_dependency(self)
				result.operation_type = 'EQ'
				self.history.add_blocker(result)
				return result

			# Get comparison sequence from C
			if _controlled:
				seq = cCQ_equal_width(self.bits, other)
			else:
				seq = CQ_equal_width(self.bits, other)

			if seq == NULL:
				raise RuntimeError(f"CQ_equal_width failed for bits={self.bits}, value={other}")

			# Check for overflow (empty sequence returned by C)
			if seq.num_layer == 0:
				# Overflow detected by C layer - definitely not equal
				return qbool(False)

			# Allocate result qbool
			result = qbool()

			# Build qubit array: [0] = result, [1:bits+1] = operand
			# Result qubit (from qbool, stored at index 63 in right-aligned storage)
			qubit_array[0] = (<qint>result).qubits[63]

			# Self operand qubits (right-aligned)
			# C backend expects MSB-first, so reverse bit order
			self_offset = 64 - self.bits
			for i in range(self.bits):
				qubit_array[1 + i] = self.qubits[self_offset + (self.bits - 1 - i)]

			start = 1 + self.bits

			# Add control qubit if controlled context
			if _controlled:
				qubit_array[start] = (<qint>_control_bool).qubits[63]
				start += 1

			# Phase 74-03: Allocate AND-ancilla for MCX decomposition
			# Uncontrolled bits >= 3: needs (bits - 2) AND-ancilla at [bits+1 .. 2*bits-2]
			# Controlled bits >= 2: needs (bits - 1) AND-ancilla at [bits+2 .. 2*bits]
			num_and_anc = 0
			and_anc_start = 0
			if _controlled and self.bits >= 2:
				num_and_anc = self.bits - 1
			elif not _controlled and self.bits >= 3:
				num_and_anc = self.bits - 2

			if num_and_anc > 0 and _circuit_initialized:
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					and_anc_start = allocator_alloc(alloc, num_and_anc, True)
					if and_anc_start != <unsigned int>(-1):
						for i in range(num_and_anc):
							qubit_array[start + i] = and_anc_start + i

			arr = qubit_array
			gc_before_eq = (<circuit_s*>_circuit).gate_count
			layer_before_eq = (<circuit_s*>_circuit).used_layer
			run_instruction(seq, &arr[0], False, _circuit)
			gc_delta_eq = (<circuit_s*>_circuit).gate_count - gc_before_eq
			if (<circuit_s*>_circuit).simulate and (<circuit_s*>_circuit).used_layer > layer_before_eq:
				range_counts_eq = circuit_gate_counts_range(<circuit_s*>_circuit, layer_before_eq, (<circuit_s*>_circuit).used_layer)
			else:
				range_counts_eq.t_count = 0
			_record_operation(
				"eq_cq",
				tuple(qubit_array[i] for i in range(start)),
				sequence_ptr=<unsigned long long>seq,
				gate_count=gc_delta_eq,
				controlled=bool(_controlled),
				depth=(<circuit_s*>_circuit).used_layer - layer_before_eq,
				t_count=range_counts_eq.t_count,
			)

			# Free AND-ancilla after use
			if num_and_anc > 0 and _circuit_initialized and and_anc_start != <unsigned int>(-1):
				alloc = circuit_get_allocator(<circuit_s*>_circuit)
				if alloc != NULL:
					allocator_free(alloc, and_anc_start, num_and_anc)

			# Track dependency on compared qint (classical doesn't need tracking)
			result.add_dependency(self)
			result.operation_type = 'EQ'

			# Step 1.2: Record operation into result's per-variable history
			# Must match the exact qubit_array layout passed to run_instruction:
			# [0]=result, [1..bits]=operand (MSB-first), [opt ctrl], then AND-ancilla.
			# Store core qubits (no ancilla) and num_and_anc so the inverse path
			# can allocate fresh ancilla at replay time.
			_qm = tuple(qubit_array[i] for i in range(start))
			result.history.append(<unsigned long long>seq, _qm, num_and_anc)

			# Step 6.2: Blocker insertion — source operand references the result
			self.history.add_blocker(result)

			return result

		raise TypeError("Comparison requires qint or int")

	def __ne__(self, other):
		"""Inequality comparison: self != other

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating inequality.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> result = (a != b)
		>>> # result is qbool representing |True>
		"""
		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()
		return ~(self == other)

	def __lt__(self, other):
		"""Less-than comparison: self < other

		Uses borrow-ancilla pattern with split-register arithmetic.
		Allocates a single ancilla qubit as borrow bit, performs (n+1)-bit
		subtraction across [a, ancilla], extracts borrow into result qbool,
		restores via addition, and deallocates ancilla.

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self < other.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = qint(5, width=8)
		>>> result = (a < b)
		>>> # result is qbool representing |True>
		"""
		from .qbool import qbool
		cdef int comp_width, i
		cdef sequence_t *seq
		cdef sequence_t *seq_add
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef circuit_s *_circ = <circuit_s*>_circuit
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef qubit_allocator_t *alloc
		cdef unsigned int borrow_ancilla, zero_ext, toff_ancilla
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int other_bits, other_offset

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(False)  # x < x is always false

		# Compile-mode: record "lt" IR entry with sequence pointers (Phase 11.5)
		# QFT mode only — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			self_offset = 64 - self.bits
			alloc = circuit_get_allocator(_circ)
			if type(other) == int:
				# Classical overflow checks (must match non-compile path)
				max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
				if other < 0:
					return qbool(False)
				if other == 0:
					return qbool(False)
				if other > max_val:
					return qbool(True)
				result = qbool()
				# CQ lt: sequence layout [0]=result, [1..bits]=A, [bits+1]=borrow
				_uc_seq = CQ_less_than(self.bits, <int64_t>other)
				_cc_seq = cCQ_less_than(self.bits, <int64_t>other)
				# Allocate borrow ancilla for IR execution during capture
				_lt_borrow = allocator_alloc(alloc, 1, True)
				regs = ((<qint>result).qubits[63],)
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
				regs = regs + (_lt_borrow,)
				_record_instruction(
					"lt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _lt_borrow, 1)
				result.add_dependency(self)
				result.operation_type = 'LT'
				self.history.add_blocker(result)
				return result
			elif type(other) == qint:
				# QQ lt: sequence layout [0]=result, [1.._comp_bits]=A,
				# [_comp_bits+1..2*_comp_bits]=B, [2*_comp_bits+1]=borrow,
				# [2*_comp_bits+2]=zero_ext
				# Total abstract qubits: 2*_comp_bits + 3
				_comp_bits = self.bits if self.bits >= (<qint>other).bits else (<qint>other).bits
				_uc_seq = QQ_less_than(_comp_bits)
				_cc_seq = cQQ_less_than(_comp_bits)
				other_offset = 64 - (<qint>other).bits
				# Pad slots needed for shorter operand + borrow + zero_ext
				_self_pad = _comp_bits - self.bits
				_other_pad = _comp_bits - (<qint>other).bits
				_lt_anc = allocator_alloc(alloc, 2 + _self_pad + _other_pad, True)
				result = qbool()
				regs = ((<qint>result).qubits[63],)
				# A: self qubits padded to _comp_bits with zero-init ancilla
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self.bits))
				for _p in range(_self_pad):
					regs = regs + (_lt_anc + 2 + _p,)
				# B: other qubits padded to _comp_bits with zero-init ancilla
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range((<qint>other).bits)
				)
				for _p in range(_other_pad):
					regs = regs + (_lt_anc + 2 + _self_pad + _p,)
				regs = regs + (_lt_anc, _lt_anc + 1)
				_record_instruction(
					"lt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _lt_anc, 2 + _self_pad + _other_pad)
				result.add_dependency(self)
				result.add_dependency(other)
				result.operation_type = 'LT'
				self.history.add_blocker(result)
				(<qint>other).history.add_blocker(result)
				return result

		# Handle qint operand: borrow-ancilla via (n+1)-bit QQ addition
		if type(other) == qint:
			other_bits = (<qint>other).bits
			other_offset = 64 - other_bits
			comp_width = (self_bits if self_bits > other_bits else other_bits) + 1

			# Save history length so we can trim entries added by internal -= / +=
			_lt_hist_len = len(self.history)
			# 1. In-place mod-n subtraction: self -= other
			self -= other

			# 2. Allocate borrow ancilla + zero-extension ancilla
			alloc = circuit_get_allocator(_circ)
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					borrow_ancilla = allocator_alloc(alloc, 2, True)
					zero_ext = borrow_ancilla + 1
				else:
					# Toffoli QQ_add(n) needs 1 carry ancilla for n>=2
					borrow_ancilla = allocator_alloc(alloc, 3, True)
					zero_ext = borrow_ancilla + 1
					toff_ancilla = borrow_ancilla + 2
			else:
				borrow_ancilla = allocator_alloc(alloc, 2, True)
				zero_ext = borrow_ancilla + 1

			# 3. Build qubit array for (comp_width)-bit QQ addition
			#    After mod-n sub, self holds (self_orig - other) mod 2^n.
			#    Adding other back in (n+1)-bit: carry into borrow_ancilla
			#    iff self_orig < other (wrapping occurred).
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					# toffoli_QQ_add(1): [target, other]
					qa[0] = borrow_ancilla  # target = borrow (MSB of extended self)
					qa[1] = zero_ext        # other = zero-ext MSB of other
				else:
					# toffoli_QQ_add(n>=2): [other, target, carry_ancilla]
					# other = [other_qubits..., zero_ext]
					for i in range(other_bits):
						qa[i] = (<qint>other).qubits[other_offset + i]
					qa[other_bits] = zero_ext
					# Pad if other_bits < comp_width - 1 (handled by zero_ext at MSB)
					# target = [self_qubits..., borrow_ancilla]
					for i in range(self_bits):
						qa[comp_width + i] = self.qubits[self_offset + i]
					qa[comp_width + self_bits] = borrow_ancilla
					# carry ancilla
					qa[2 * comp_width] = toff_ancilla
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
			else:
				# QFT QQ_add(n): [target(n), other(n)]
				# target = [self_qubits..., borrow_ancilla]
				for i in range(self_bits):
					qa[i] = self.qubits[self_offset + i]
				qa[self_bits] = borrow_ancilla
				# other = [other_qubits..., zero_ext]
				for i in range(other_bits):
					qa[comp_width + i] = (<qint>other).qubits[other_offset + i]
				qa[comp_width + other_bits] = zero_ext
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)

			# 4. Extract borrow into result qbool
			result = qbool()
			qubit_array[0] = (<qint>result).qubits[63]
			qubit_array[1] = borrow_ancilla
			arr = qubit_array
			seq_add = Q_xor(1)
			run_instruction(seq_add, &arr[0], False, _circuit)

			# 5. Undo the (n+1)-bit addition (inverse)
			if _circ.arithmetic_mode == 1:  # Toffoli
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)
			else:
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)

			# 6. Restore self: self += other
			self += other
			# Trim internal in-place history entries (Step 6.4 transparency)
			del self.history.entries[_lt_hist_len:]

			# 7. Deallocate ancilla
			if _circ.arithmetic_mode == 1 and comp_width > 1:
				allocator_free(alloc, borrow_ancilla, 3)
			else:
				allocator_free(alloc, borrow_ancilla, 2)

			# Track dependencies on original operands
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'LT'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_other_offset_h = 64 - (<qint>other).bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operands reference the result
			self.history.add_blocker(result)
			(<qint>other).history.add_blocker(result)

			return result

		# Handle int operand: borrow-ancilla via split-register CQ subtraction
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(False)  # qint always >= 0, so qint < negative is false
			if other == 0:
				return qbool(False)  # unsigned qint is never < 0
			if other > max_val:
				return qbool(True)  # qint always < large value that doesn't fit

			alloc = circuit_get_allocator(_circ)

			if _circ.arithmetic_mode == 1:  # Toffoli
				# split_toffoli_CQ_sub qubit layout:
				# [0..bits] = temp, [bits+1..2*bits+1] = target [a, msb], [2*(bits+1)] = carry
				borrow_ancilla = allocator_alloc(alloc, 1, True)
				toff_ancilla = allocator_alloc(alloc, self_bits + 2, True)

				# Build qubit array: temp register, target=[self, borrow], carry
				for i in range(self_bits + 1):
					qa[i] = toff_ancilla + i
				for i in range(self_bits):
					qa[self_bits + 1 + i] = self.qubits[self_offset + i]
				qa[self_bits + 1 + self_bits] = borrow_ancilla
				qa[2 * (self_bits + 1)] = toff_ancilla + self_bits + 1

				# Subtract
				seq = split_toffoli_CQ_sub(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				# Extract borrow
				result = qbool()
				qubit_array[0] = (<qint>result).qubits[63]
				qubit_array[1] = borrow_ancilla
				arr = qubit_array
				seq_add = Q_xor(1)
				run_instruction(seq_add, &arr[0], False, _circuit)

				# Restore via addition
				seq = split_toffoli_CQ_add(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				allocator_free(alloc, toff_ancilla, self_bits + 2)
				allocator_free(alloc, borrow_ancilla, 1)
			else:
				# QFT split-register: qubit layout [0..bits-1] = a, [bits] = msb
				borrow_ancilla = allocator_alloc(alloc, 1, True)

				for i in range(self_bits):
					qa[i] = self.qubits[self_offset + i]
				qa[self_bits] = borrow_ancilla

				# Subtract
				seq = split_CQ_sub(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				# Extract borrow
				result = qbool()
				qubit_array[0] = (<qint>result).qubits[63]
				qubit_array[1] = borrow_ancilla
				arr = qubit_array
				seq_add = Q_xor(1)
				run_instruction(seq_add, &arr[0], False, _circuit)

				# Restore via addition
				seq = split_CQ_add(self_bits, <int64_t>other)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
					toffoli_sequence_free(seq)

				allocator_free(alloc, borrow_ancilla, 1)

			# Track dependencies
			result.add_dependency(self)
			result.operation_type = 'LT'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operand references the result
			self.history.add_blocker(result)

			return result

		raise TypeError("Comparison requires qint or int")

	def __gt__(self, other):
		"""Greater-than comparison: self > other

		Uses borrow-ancilla pattern with split-register arithmetic.
		a > b is computed as b < a: subtract self from other's extended
		register and check the borrow bit.

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self > other.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> result = (a > b)
		>>> # result is qbool representing |True>
		"""
		from .qbool import qbool
		cdef int comp_width, i
		cdef sequence_t *seq
		cdef sequence_t *seq_add
		cdef unsigned int[:] arr
		cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
		cdef circuit_s *_circ = <circuit_s*>_circuit
		cdef bint _circuit_initialized = _get_circuit_initialized()
		cdef qubit_allocator_t *alloc
		cdef unsigned int borrow_ancilla, zero_ext, toff_ancilla
		cdef unsigned int qa[256]
		cdef int self_bits = self.bits
		cdef int self_offset = 64 - self_bits
		cdef int other_bits, other_offset

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(False)  # x > x is always false

		# Compile-mode: record "gt" IR entry with sequence pointers (Phase 11.5)
		# QFT mode only — Toffoli mode falls through to direct dispatch.
		if _is_compile_mode() and _circ.arithmetic_mode != 1:
			alloc = circuit_get_allocator(_circ)
			if type(other) == int:
				# Classical overflow checks (must match non-compile path)
				max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
				if other < 0:
					return qbool(True)
				if other >= max_val:
					return qbool(False)
				result = qbool()
				# gt CQ: a > value, uses CQ_greater_than = CQ_less_than(value+1)
				_uc_seq = CQ_greater_than(self.bits, <int64_t>other)
				_cc_seq = cCQ_greater_than(self.bits, <int64_t>other)
				_gt_borrow = allocator_alloc(alloc, 1, True)
				regs = ((<qint>result).qubits[63],)
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self_bits))
				regs = regs + (_gt_borrow,)
				_record_instruction(
					"gt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _gt_borrow, 1)
				result.add_dependency(self)
				result.operation_type = 'GT'
				self.history.add_blocker(result)
				return result
			elif type(other) == qint:
				# gt QQ: a > b = b < a. Use QQ_less_than with swapped operands.
				# Qubit layout: [0]=result, [1.._comp_bits]=A(=other),
				# [_comp_bits+1..2*_comp_bits]=B(=self), [2*_comp_bits+1]=borrow,
				# [2*_comp_bits+2]=zero_ext
				other_bits = (<qint>other).bits
				other_offset = 64 - other_bits
				_comp_bits = self_bits if self_bits >= other_bits else other_bits
				_uc_seq = QQ_less_than(_comp_bits)
				_cc_seq = cQQ_less_than(_comp_bits)
				# Pad slots for shorter operand + borrow + zero_ext
				_other_pad = _comp_bits - other_bits
				_self_pad = _comp_bits - self_bits
				_gt_anc = allocator_alloc(alloc, 2 + _other_pad + _self_pad, True)
				result = qbool()
				# Swapped: A=other, B=self (since we want other < self)
				regs = ((<qint>result).qubits[63],)
				# A: other qubits padded to _comp_bits
				regs = regs + tuple(
					(<qint>other).qubits[other_offset + i]
					for i in range(other_bits)
				)
				for _p in range(_other_pad):
					regs = regs + (_gt_anc + 2 + _p,)
				# B: self qubits padded to _comp_bits
				regs = regs + tuple(self.qubits[self_offset + i] for i in range(self_bits))
				for _p in range(_self_pad):
					regs = regs + (_gt_anc + 2 + _other_pad + _p,)
				regs = regs + (_gt_anc, _gt_anc + 1)
				_record_instruction(
					"gt", regs,
					uncontrolled_seq=<unsigned long long>_uc_seq if _uc_seq != NULL else 0,
					controlled_seq=<unsigned long long>_cc_seq if _cc_seq != NULL else 0,
				)
				allocator_free(alloc, _gt_anc, 2 + _other_pad + _self_pad)
				result.add_dependency(self)
				result.add_dependency(other)
				result.operation_type = 'GT'
				self.history.add_blocker(result)
				(<qint>other).history.add_blocker(result)
				return result

		# Handle qint operand: a > b computed as b < a via borrow-ancilla
		if type(other) == qint:
			other_bits = (<qint>other).bits
			other_offset = 64 - other_bits
			comp_width = (self_bits if self_bits > other_bits else other_bits) + 1

			# Save history length so we can trim entries added by internal -= / +=
			_gt_hist_len = len((<qint>other).history)
			# 1. In-place mod-n subtraction: other -= self
			(<qint>other).__isub__(self)

			# 2. Allocate borrow ancilla + zero-extension ancilla
			alloc = circuit_get_allocator(_circ)
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					borrow_ancilla = allocator_alloc(alloc, 2, True)
					zero_ext = borrow_ancilla + 1
				else:
					borrow_ancilla = allocator_alloc(alloc, 3, True)
					zero_ext = borrow_ancilla + 1
					toff_ancilla = borrow_ancilla + 2
			else:
				borrow_ancilla = allocator_alloc(alloc, 2, True)
				zero_ext = borrow_ancilla + 1

			# 3. Build qubit array for (comp_width)-bit QQ addition
			#    After mod-n sub, other holds (other_orig - self) mod 2^n.
			#    Adding self back in (n+1)-bit: carry into borrow_ancilla
			#    iff other_orig < self (wrapping occurred), i.e. self > other.
			if _circ.arithmetic_mode == 1:  # Toffoli
				if comp_width == 1:
					qa[0] = borrow_ancilla
					qa[1] = zero_ext
				else:
					# toffoli_QQ_add(n>=2): [self_ext, other_ext, carry]
					for i in range(self_bits):
						qa[i] = self.qubits[self_offset + i]
					qa[self_bits] = zero_ext
					for i in range(other_bits):
						qa[comp_width + i] = (<qint>other).qubits[other_offset + i]
					qa[comp_width + other_bits] = borrow_ancilla
					qa[2 * comp_width] = toff_ancilla
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)
			else:
				# QFT QQ_add(n): [target(n), other(n)]
				# target = [other_qubits..., borrow_ancilla]
				for i in range(other_bits):
					qa[i] = (<qint>other).qubits[other_offset + i]
				qa[other_bits] = borrow_ancilla
				# other_operand = [self_qubits..., zero_ext]
				for i in range(self_bits):
					qa[comp_width + i] = self.qubits[self_offset + i]
				qa[comp_width + self_bits] = zero_ext
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, False, _circuit)

			# 4. Extract borrow into result qbool
			result = qbool()
			qubit_array[0] = (<qint>result).qubits[63]
			qubit_array[1] = borrow_ancilla
			arr = qubit_array
			seq_add = Q_xor(1)
			run_instruction(seq_add, &arr[0], False, _circuit)

			# 5. Undo the (n+1)-bit addition (inverse)
			if _circ.arithmetic_mode == 1:  # Toffoli
				seq = toffoli_QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)
			else:
				seq = QQ_add(comp_width)
				if seq != NULL:
					run_instruction(seq, qa, True, _circuit)

			# 6. Restore other: other += self
			(<qint>other).__iadd__(self)
			# Trim internal in-place history entries (Step 6.4 transparency)
			del (<qint>other).history.entries[_gt_hist_len:]

			# 7. Deallocate ancilla
			if _circ.arithmetic_mode == 1 and comp_width > 1:
				allocator_free(alloc, borrow_ancilla, 3)
			else:
				allocator_free(alloc, borrow_ancilla, 2)

			# Track dependencies on original operands
			result.add_dependency(self)
			result.add_dependency(other)
			result.operation_type = 'GT'

			# Step 1.2: Record operation into result's per-variable history
			_r_offset_h = 64 - (<qint>result).bits
			_self_offset_h = 64 - self.bits
			_other_offset_h = 64 - (<qint>other).bits
			_qm = tuple((<qint>result).qubits[_r_offset_h + i] for i in range((<qint>result).bits)) \
				+ tuple(self.qubits[_self_offset_h + i] for i in range(self.bits)) \
				+ tuple((<qint>other).qubits[_other_offset_h + i] for i in range((<qint>other).bits))
			result.history.append(0, _qm)

			# Step 6.2: Blocker insertion — source operands reference the result
			self.history.add_blocker(result)
			(<qint>other).history.add_blocker(result)

			return result

		# Handle int operand: borrow-ancilla via split-register CQ subtraction
		# a > b (int) is equivalent to b < a, i.e., classical < quantum.
		# We compute self < (other+1) is wrong. Instead:
		# self > other iff NOT(self <= other) iff NOT(self < other+1) for int.
		# Simpler: self > other iff other < self. For CQ: subtract self_value
		# from other... but self is quantum. Use: self > other iff NOT(self <= other).
		# But <=  delegates to ~(self > other) creating recursion.
		# Direct approach: self > int_val iff self >= int_val + 1 iff NOT(self < int_val + 1).
		# Or: create temp qint and use QQ path.
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self_bits) - 1 if self_bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(True)  # qint always >= 0, so qint > negative is true
			if other >= max_val:
				return qbool(False)  # qint can't exceed max_val, so not >

			# self > other iff NOT(self < other + 1)
			# (since self and other are integers, self > other <=> self >= other+1 <=> NOT(self < other+1))
			return ~(self < (other + 1))

		raise TypeError("Comparison requires qint or int")

	def __le__(self, other):
		"""Less-than-or-equal comparison: self <= other

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self <= other.

		Examples
		--------
		>>> a = qint(3, width=8)
		>>> b = qint(5, width=8)
		>>> result = (a <= b)
		>>> # result is qbool representing |True>

		Notes
		-----
		a <= b is equivalent to NOT(a > b).
		"""
		from .qbool import qbool

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(True)  # x <= x is always true

		# Handle qint operand
		if type(other) == qint:
			# a <= b is equivalent to NOT(a > b)
			return ~(self > other)

		# Handle int operand
		if type(other) == int:
			# Classical overflow checks
			max_val = (1 << self.bits) - 1 if self.bits < 64 else (1 << 63) - 1
			if other < 0:
				return qbool(False)  # qint >= 0, so qint <= negative is false
			if other > max_val:
				return qbool(True)  # qint always <= large value

			# a <= b is equivalent to NOT(a > b)
			return ~(self > other)

		raise TypeError("Comparison requires qint or int")

	def __ge__(self, other):
		"""Greater-than-or-equal comparison: self >= other

		Parameters
		----------
		other : qint or int
			Value to compare with.

		Returns
		-------
		qbool
			Quantum boolean indicating self >= other.

		Examples
		--------
		>>> a = qint(5, width=8)
		>>> b = qint(3, width=8)
		>>> result = (a >= b)
		>>> # result is qbool representing |True>

		Notes
		-----
		Delegates to NOT(self < other) which uses borrow-ancilla pattern.
		"""
		from .qbool import qbool

		# Phase 18: Check for use-after-uncompute
		self._check_not_uncomputed()
		if isinstance(other, qint):
			(<qint>other)._check_not_uncomputed()

		# Self-comparison optimization
		if self is other:
			return qbool(True)  # x >= x is always true
		# self >= other is equivalent to NOT (self < other)
		return ~(self < other)
	# END include "qint_comparison.pxi"
	# BEGIN include "qint_division.pxi"
	# ====================================================================
	# DIVISION OPERATIONS
	# Phase 41: Added layer tracking for uncomputation support
	# Phase 91: Rewired to C-level restoring divmod (fixes BUG-DIV-02, BUG-QFT-DIV)
	# ====================================================================

	@cython.boundscheck(False)
	@cython.wraparound(False)
	cdef _divmod_c(self, divisor, bint need_quotient, bint need_remainder):
		"""Internal: call C-level divmod and return (quotient, remainder).

		Dispatches to toffoli_divmod_cq (classical divisor) or
		toffoli_divmod_qq (quantum divisor). All ancillae are managed
		internally by the C functions.

		Parameters
		----------
		divisor : int or qint
		    Divisor value.
		need_quotient : bool
		    If True, return quotient; if False, quotient register is unused.
		need_remainder : bool
		    If True, return remainder; if False, remainder register is unused.

		Returns
		-------
		tuple of (qint or None, qint or None)
		    (quotient, remainder), either may be None if not needed.
		"""
		cdef circuit_t *_circ = <circuit_t*><unsigned long long>_get_circuit()
		cdef int i
		cdef int n = self.bits
		cdef int self_offset = 64 - n
		cdef unsigned int dividend_qa[64]
		cdef unsigned int quotient_qa[64]
		cdef unsigned int remainder_qa[64]
		cdef unsigned int divisor_qa[64]
		cdef int div_bits = 0
		cdef int d_offset = 0
		cdef size_t gc_before_div, gc_delta_div
		cdef unsigned int layer_before_div
		cdef gate_counts_t range_counts_div

		# Extract dividend qubits (LSB-first for C convention)
		# Python qint right-aligned layout: qubits[64-bits] = LSB (bit 0), qubits[63] = MSB
		# C expects LSB-first: index 0 = LSB, index n-1 = MSB
		# So qa[i] = qubits[self_offset + i] gives qa[0]=LSB, qa[n-1]=MSB
		for i in range(n):
			dividend_qa[i] = self.qubits[self_offset + i]

		# Allocate output registers
		quotient = qint(0, width=n)
		remainder = qint(0, width=n)

		cdef int q_offset = 64 - (<qint>quotient).bits
		cdef int r_offset = 64 - (<qint>remainder).bits

		# Extract output qubits (LSB-first)
		for i in range(n):
			quotient_qa[i] = (<qint>quotient).qubits[q_offset + i]
			remainder_qa[i] = (<qint>remainder).qubits[r_offset + i]

		if type(divisor) == int:
			gc_before_div = (<circuit_s*>_circ).gate_count
			layer_before_div = (<circuit_s*>_circ).used_layer
			toffoli_divmod_cq(_circ, dividend_qa, n,
			                  <int64_t>divisor,
			                  quotient_qa, remainder_qa)
			gc_delta_div = (<circuit_s*>_circ).gate_count - gc_before_div
			if (<circuit_s*>_circ).simulate and (<circuit_s*>_circ).used_layer > layer_before_div:
				range_counts_div = circuit_gate_counts_range(<circuit_s*>_circ, layer_before_div, (<circuit_s*>_circ).used_layer)
			else:
				range_counts_div.t_count = 0
			_record_operation(
				"divmod_cq",
				tuple(dividend_qa[i] for i in range(n))
				+ tuple(quotient_qa[i] for i in range(n))
				+ tuple(remainder_qa[i] for i in range(n)),
				gate_count=gc_delta_div,
				controlled=False,
				depth=(<circuit_s*>_circ).used_layer - layer_before_div,
				t_count=range_counts_div.t_count,
			)
		elif type(divisor) == qint:
			div_bits = (<qint>divisor).bits
			d_offset = 64 - div_bits
			for i in range(div_bits):
				divisor_qa[i] = (<qint>divisor).qubits[d_offset + i]

			gc_before_div = (<circuit_s*>_circ).gate_count
			layer_before_div = (<circuit_s*>_circ).used_layer
			toffoli_divmod_qq(_circ, dividend_qa, n,
			                  divisor_qa, div_bits,
			                  quotient_qa, remainder_qa)
			gc_delta_div = (<circuit_s*>_circ).gate_count - gc_before_div
			if (<circuit_s*>_circ).simulate and (<circuit_s*>_circ).used_layer > layer_before_div:
				range_counts_div = circuit_gate_counts_range(<circuit_s*>_circ, layer_before_div, (<circuit_s*>_circ).used_layer)
			else:
				range_counts_div.t_count = 0
			_record_operation(
				"divmod_qq",
				tuple(dividend_qa[i] for i in range(n))
				+ tuple(divisor_qa[i] for i in range(div_bits))
				+ tuple(quotient_qa[i] for i in range(n))
				+ tuple(remainder_qa[i] for i in range(n)),
				gate_count=gc_delta_div,
				controlled=False,
				depth=(<circuit_s*>_circ).used_layer - layer_before_div,
				t_count=range_counts_div.t_count,
			)
		else:
			raise TypeError("Divisor must be int or qint")

		return (quotient, remainder)

	def __floordiv__(self, divisor):
		"""Floor division: self // divisor

		Uses C-level restoring division algorithm (Phase 91).

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
		Phase 91: Rewired to C-level toffoli_divmod_cq/qq.
		Classical divisor: O(width) circuit via bit-level restoring division.
		Quantum divisor: O(2^width) circuit via repeated subtraction.
		"""
		from quantum_language.qbool import qbool

		# Validation
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Division by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, True, False)

		quotient.operation_type = 'DIV'
		quotient.add_dependency(self)
		if type(divisor) == qint:
			quotient.add_dependency(divisor)

		return quotient

	def __ifloordiv__(self, other):
		"""In-place floor division: self //= other"""
		result = self // other
		cdef qint result_qint = <qint>result
		self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
		self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
		self.bits = result_qint.bits
		return self

	def __mod__(self, divisor):
		"""Modulo operation: self % divisor

		Computes remainder via C-level restoring division (Phase 91).

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
		# Validation
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Modulo by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, False, True)

		remainder.operation_type = 'MOD'
		remainder.add_dependency(self)
		if type(divisor) == qint:
			remainder.add_dependency(divisor)

		return remainder

	def __divmod__(self, divisor):
		"""Divmod operation: divmod(self, divisor)

		Computes both quotient and remainder in single pass via C-level
		restoring division (Phase 91).

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
		# Validation
		if type(divisor) == int:
			if divisor == 0:
				raise ZeroDivisionError("Divmod by zero")
			if divisor < 0:
				raise NotImplementedError("Negative divisor not yet supported")
		elif type(divisor) != qint:
			raise TypeError("Divisor must be int or qint")

		# Call C-level divmod
		quotient, remainder = self._divmod_c(divisor, True, True)

		quotient.operation_type = 'DIVMOD'
		quotient.add_dependency(self)
		remainder.operation_type = 'DIVMOD'
		remainder.add_dependency(self)
		if type(divisor) == qint:
			quotient.add_dependency(divisor)
			remainder.add_dependency(divisor)

		return (quotient, remainder)

	def __rfloordiv__(self, other):
		"""Reverse floor division: other // self"""
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint // self
		else:
			raise TypeError("Reverse floor division requires int divisor")

	def __rmod__(self, other):
		"""Reverse modulo: other % self"""
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return other_qint % self
		else:
			raise TypeError("Reverse modulo requires int divisor")

	def __rdivmod__(self, other):
		"""Reverse divmod: divmod(other, self)"""
		if type(other) == int:
			other_qint = qint(other, width=self.bits)
			return divmod(other_qint, self)
		else:
			raise TypeError("Reverse divmod requires int divisor")
	# END include "qint_division.pxi"
