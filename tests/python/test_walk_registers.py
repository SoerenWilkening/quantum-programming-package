"""Tests for walk_registers: WalkRegisters allocation and management.

Verifies register allocation, init_root() behavior, branch access, qubit
counts, and cleanup.  All tests stay within the 21-qubit simulation limit.

Requirements from acceptance criteria:
- Register allocation matches WalkConfig qubit counts
- init_root() sets height[max_depth] = 1
- Branches start zeroed
"""

import gc

import pytest
import qiskit.qasm3
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk_core import WalkConfig
from quantum_language.walk_registers import WalkRegisters

# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------


def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM qubit[N] declaration."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise ValueError("Could not find qubit count in QASM")


def _simulate_statevector(qasm_str):
    """Simulate QASM and return the statevector as a list of complex."""
    circuit = qiskit.qasm3.loads(qasm_str)
    simulator = AerSimulator(method="statevector")
    circuit.save_statevector()
    job = simulator.run(circuit, shots=0)
    result = job.result()
    sv = result.get_statevector()
    return sv.data


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width):
    """Simulate QASM and extract integer from result register."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(method="statevector", max_parallel_threads=4)
    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos : lsb_pos + 1]
    return int(result_bits, 2)


def _init_circuit():
    """Initialize a fresh circuit."""
    gc.collect()
    ql.circuit()
    ql.option("simulate", True)


# ---------------------------------------------------------------------------
# Group 1: Construction Validation
# ---------------------------------------------------------------------------


class TestConstruction:
    """Validate WalkRegisters construction."""

    def test_rejects_non_walkconfig(self):
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            WalkRegisters("not a config")

    def test_rejects_dict(self):
        with pytest.raises(TypeError, match="config must be a WalkConfig"):
            WalkRegisters({"max_depth": 2, "num_moves": 2})

    def test_creates_with_valid_config(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        assert regs.config is cfg

    def test_height_length(self):
        """Height register has max_depth + 1 elements."""
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        assert len(regs.height) == 4  # max_depth + 1

    def test_branches_length(self):
        """Branch registers list has max_depth elements."""
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        assert len(regs.branches) == 3  # max_depth

    def test_branch_widths(self):
        """Each branch register has branch_width qubits."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=3)
        regs = WalkRegisters(cfg)
        for br in regs.branches:
            assert br.width == cfg.bw

    def test_count_width(self):
        """Count register has count_width qubits."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=3)
        regs = WalkRegisters(cfg)
        assert regs.count.width == cfg.cw


# ---------------------------------------------------------------------------
# Group 2: Total Qubit Count
# ---------------------------------------------------------------------------


class TestTotalQubits:
    """Verify total qubit count matches WalkConfig.total_walk_qubits()."""

    def test_binary_depth2(self):
        """Binary tree depth 2: height=3, branch=1*2=2, count=2 -> 7."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        assert regs.total_qubits() == cfg.total_walk_qubits()

    def test_binary_depth3(self):
        """Binary tree depth 3: height=4, branch=1*3=3, count=2 -> 9."""
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        assert regs.total_qubits() == cfg.total_walk_qubits()

    def test_ternary_depth2(self):
        """Ternary tree depth 2: height=3, branch=2*2=4, count=2 -> 9."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=3)
        regs = WalkRegisters(cfg)
        assert regs.total_qubits() == cfg.total_walk_qubits()

    def test_four_moves_depth1(self):
        """4 moves depth 1: height=2, branch=2*1=2, count=3 -> 7."""
        _init_circuit()
        cfg = WalkConfig(max_depth=1, num_moves=4)
        regs = WalkRegisters(cfg)
        assert regs.total_qubits() == cfg.total_walk_qubits()

    def test_single_move_depth1(self):
        """1 move depth 1: height=2, branch=1*1=1, count=1 -> 4."""
        _init_circuit()
        cfg = WalkConfig(max_depth=1, num_moves=1)
        regs = WalkRegisters(cfg)
        assert regs.total_qubits() == cfg.total_walk_qubits()


# ---------------------------------------------------------------------------
# Group 3: init_root() State
# ---------------------------------------------------------------------------


class TestInitRoot:
    """Verify init_root() sets the correct height qubit."""

    def test_init_root_sets_height_max_depth(self):
        """After init_root(), only height[max_depth] is |1>."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.init_root()

        # Export QASM and simulate to check state
        _keepalive = [regs.height, regs.branches, regs.count]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21, f"Circuit uses {nq} qubits (limit: 21)"

        sv = _simulate_statevector(qasm)

        # The root qubit should be |1>. Find the statevector index
        # where only the root height qubit is set.
        root_qbool = regs.height_qubit(cfg.max_depth)
        root_qubit = int(root_qbool.qubits[63])
        expected_idx = 1 << root_qubit
        prob = abs(sv[expected_idx]) ** 2
        assert prob > 0.999, (
            f"Expected root state at index {expected_idx} (qubit {root_qubit}), "
            f"got probability {prob}"
        )

    def test_init_root_double_call_raises(self):
        """Calling init_root() twice raises RuntimeError."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.init_root()
        with pytest.raises(RuntimeError, match="already been called"):
            regs.init_root()

    def test_init_root_depth3(self):
        """init_root() for depth 3: height[3] = |1>."""
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.init_root()

        _keepalive = [regs.height, regs.branches, regs.count]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21, f"Circuit uses {nq} qubits (limit: 21)"

        sv = _simulate_statevector(qasm)
        root_qbool = regs.height_qubit(cfg.max_depth)
        root_qubit = int(root_qbool.qubits[63])
        expected_idx = 1 << root_qubit
        prob = abs(sv[expected_idx]) ** 2
        assert prob > 0.999


# ---------------------------------------------------------------------------
# Group 4: Branches Start Zeroed
# ---------------------------------------------------------------------------


class TestBranchesZeroed:
    """Verify all branch registers start at 0."""

    def test_branches_zeroed_binary_depth2(self):
        """Binary depth 2: both branches measure 0."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.init_root()

        for i, br in enumerate(regs.branches):
            br_start = br.allocated_start
            br_width = br.width
            _keepalive = [regs.height, regs.branches, regs.count]
            qasm = ql.to_openqasm()
            nq = _get_num_qubits(qasm)
            assert nq <= 21

            extracted = _simulate_and_extract(qasm, nq, br_start, br_width)
            assert extracted == 0, f"Branch {i} should be 0, got {extracted}"

    def test_branches_zeroed_ternary_depth2(self):
        """Ternary depth 2: both 2-qubit branches measure 0."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=3)
        regs = WalkRegisters(cfg)
        regs.init_root()

        for i, br in enumerate(regs.branches):
            br_start = br.allocated_start
            br_width = br.width
            _keepalive = [regs.height, regs.branches, regs.count]
            qasm = ql.to_openqasm()
            nq = _get_num_qubits(qasm)
            assert nq <= 21

            extracted = _simulate_and_extract(qasm, nq, br_start, br_width)
            assert extracted == 0, f"Branch {i} should be 0, got {extracted}"


# ---------------------------------------------------------------------------
# Group 5: branch_at() Access
# ---------------------------------------------------------------------------


class TestBranchAt:
    """Verify branch_at() returns the correct register."""

    def test_branch_at_returns_same_object(self):
        """branch_at(d) returns the same object as branches[d]."""
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        for d in range(cfg.max_depth):
            assert regs.branch_at(d) is regs.branches[d]

    def test_branch_at_negative_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        with pytest.raises(IndexError, match="depth must be in"):
            regs.branch_at(-1)

    def test_branch_at_too_large_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        with pytest.raises(IndexError, match="depth must be in"):
            regs.branch_at(2)

    def test_branch_at_float_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        with pytest.raises(TypeError, match="depth must be an int"):
            regs.branch_at(1.0)


# ---------------------------------------------------------------------------
# Group 6: height_qubit() Access
# ---------------------------------------------------------------------------


class TestHeightQubit:
    """Verify height_qubit() returns qbool objects."""

    def test_height_qubit_returns_qbool(self):
        """height_qubit() returns qbool, not int."""
        from quantum_language.qbool import qbool

        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        for d in range(cfg.hw):
            q = regs.height_qubit(d)
            assert isinstance(q, qbool)

    def test_height_qubit_is_same_object(self):
        """height_qubit(d) returns the same qbool as height[d]."""
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        for d in range(cfg.hw):
            assert regs.height_qubit(d) is regs.height[d]

    def test_height_qubits_unique(self):
        """All height qubits have distinct physical indices."""
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        qubits = [int(regs.height_qubit(d).qubits[63]) for d in range(cfg.hw)]
        assert len(set(qubits)) == cfg.hw

    def test_height_qubit_negative_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        with pytest.raises(IndexError, match="depth must be in"):
            regs.height_qubit(-1)

    def test_height_qubit_too_large_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        with pytest.raises(IndexError, match="depth must be in"):
            regs.height_qubit(3)

    def test_height_qubit_float_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        with pytest.raises(TypeError, match="depth must be an int"):
            regs.height_qubit(0.5)


# ---------------------------------------------------------------------------
# Group 7: current_depth()
# ---------------------------------------------------------------------------


class TestCurrentDepth:
    """Verify current_depth() returns the height list."""

    def test_current_depth_returns_height(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        assert regs.current_depth() is regs.height

    def test_current_depth_length(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        assert len(regs.current_depth()) == cfg.hw


# ---------------------------------------------------------------------------
# Group 8: Cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    """Verify cleanup releases registers."""

    def test_cleanup_clears_height(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        assert regs.height == []

    def test_cleanup_clears_branches(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        assert regs.branches == []

    def test_cleanup_clears_count(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        assert regs.count is None

    def test_cleanup_sets_cleaned_up_flag(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.init_root()
        regs.cleanup()
        assert regs._cleaned_up is True


# ---------------------------------------------------------------------------
# Group 8b: Post-Cleanup Error Behavior
# ---------------------------------------------------------------------------


class TestPostCleanupErrors:
    """Verify all methods raise RuntimeError after cleanup()."""

    def test_total_qubits_after_cleanup_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        with pytest.raises(RuntimeError, match="registers have been cleaned up"):
            regs.total_qubits()

    def test_branch_at_after_cleanup_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        with pytest.raises(RuntimeError, match="registers have been cleaned up"):
            regs.branch_at(0)

    def test_height_qubit_after_cleanup_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        with pytest.raises(RuntimeError, match="registers have been cleaned up"):
            regs.height_qubit(0)

    def test_current_depth_after_cleanup_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        with pytest.raises(RuntimeError, match="registers have been cleaned up"):
            regs.current_depth()

    def test_init_root_after_cleanup_raises(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.cleanup()
        with pytest.raises(RuntimeError, match="registers have been cleaned up"):
            regs.init_root()


# ---------------------------------------------------------------------------
# Group 9: Qubit Budget
# ---------------------------------------------------------------------------


class TestQubitBudget:
    """Verify register allocation stays within 21-qubit limit for test sizes."""

    def test_binary_depth2_within_budget(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.init_root()
        _keepalive = [regs.height, regs.branches, regs.count]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21, f"Circuit uses {nq} qubits (limit: 21)"

    def test_ternary_depth2_within_budget(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=2, num_moves=3)
        regs = WalkRegisters(cfg)
        regs.init_root()
        _keepalive = [regs.height, regs.branches, regs.count]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21, f"Circuit uses {nq} qubits (limit: 21)"

    def test_binary_depth3_within_budget(self):
        _init_circuit()
        cfg = WalkConfig(max_depth=3, num_moves=2)
        regs = WalkRegisters(cfg)
        regs.init_root()
        _keepalive = [regs.height, regs.branches, regs.count]
        qasm = ql.to_openqasm()
        nq = _get_num_qubits(qasm)
        assert nq <= 21, f"Circuit uses {nq} qubits (limit: 21)"
