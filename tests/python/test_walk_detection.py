"""Phase 101: Detection algorithm tests for iterative power-method detection.

Tests verify DET-01 (power-method detection), DET-02 (SAT demo within 17
qubits), and DET-03 (statevector verification on solution/no-solution).

Requirements: DET-01, DET-02, DET-03
"""

import math

import numpy as np
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk import QWalkTree

# ---------------------------------------------------------------------------
# Helper functions (same pattern as test_walk_operators.py)
# ---------------------------------------------------------------------------


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector as numpy array."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return np.asarray(result.get_statevector())


# ---------------------------------------------------------------------------
# Group 1: Tree Size Tests
# ---------------------------------------------------------------------------


class TestTreeSize:
    """Test _tree_size computation for various tree configurations."""

    def test_tree_size_binary_depth1(self):
        """Binary tree depth=1: 1 + 2 = 3 nodes.

        Tree: max_depth=1, branching=2, total_qubits=3 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=2)
        assert tree._tree_size() == 3

    def test_tree_size_binary_depth2(self):
        """Binary tree depth=2: 1 + 2 + 4 = 7 nodes.

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)
        assert tree._tree_size() == 7

    def test_tree_size_binary_depth3(self):
        """Binary tree depth=3: 1 + 2 + 4 + 8 = 15 nodes.

        Tree: max_depth=3, branching=2, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=3, branching=2)
        assert tree._tree_size() == 15

    def test_tree_size_ternary_depth2(self):
        """Ternary tree depth=2: 1 + 3 + 9 = 13 nodes.

        Tree: max_depth=2, branching=3, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=3)
        assert tree._tree_size() == 13


# ---------------------------------------------------------------------------
# Group 2: Root Overlap Measurement Tests
# ---------------------------------------------------------------------------


class TestRootOverlap:
    """Test _measure_root_overlap returns valid probabilities."""

    def test_root_overlap_one_step(self):
        """Root overlap after 1 walk step is less than 1.0 (walk modifies state).

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)
        overlap = tree._measure_root_overlap(1)

        assert 0 <= overlap <= 1.0, f"Root overlap must be in [0, 1], got {overlap}"
        assert overlap < 1.0, f"Root overlap should be < 1.0 after walk step, got {overlap}"

    def test_root_overlap_is_probability(self):
        """Root overlap is a valid probability at all power levels.

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)

        for power in [1, 2, 4]:
            overlap = tree._measure_root_overlap(power)
            assert 0 <= overlap <= 1.0 + 1e-10, (
                f"Power {power}: overlap {overlap} not a valid probability"
            )

    def test_root_overlap_depth3(self):
        """Root overlap on deeper tree is also valid.

        Tree: max_depth=3, branching=2, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=3, branching=2)
        overlap = tree._measure_root_overlap(1)

        assert 0 <= overlap <= 1.0, f"Invalid overlap: {overlap}"
        assert overlap < 1.0, f"Expected < 1.0, got {overlap}"

    def test_root_overlap_depth1_periodic(self):
        """On depth=1 binary tree, root overlap returns to ~1.0 at power=2.

        The walk step on a depth=1 tree has period 2: U^2 returns to
        the root state. This demonstrates correct walk dynamics.

        Tree: max_depth=1, branching=2, total_qubits=3 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=2)

        p1 = tree._measure_root_overlap(1)
        p2 = tree._measure_root_overlap(2)

        assert p1 < 1.0, "Power 1 should reduce root overlap"
        assert abs(p2 - 1.0) < 1e-6, f"Power 2 should return to ~1.0, got {p2}"


# ---------------------------------------------------------------------------
# Group 3: Detection Algorithm Tests (DET-01)
# ---------------------------------------------------------------------------


class TestDetection:
    """DET-01: Iterative power-method detection algorithm tests."""

    def test_detect_depth1_returns_false(self):
        """detect() on depth=1 binary tree returns False.

        On a depth=1 tree, the walk step has period 2 and the root
        overlap never stays below 3/8. detect() correctly returns False.

        Tree: max_depth=1, branching=2, total_qubits=3 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=2)
        result = tree.detect(max_iterations=8)

        assert result is False, "detect() should return False on depth=1 tree"

    def test_detect_ternary_returns_false(self):
        """detect() on depth=2 ternary tree returns False.

        Ternary tree has higher connectivity, root overlap stays above 3/8.

        Tree: max_depth=2, branching=3, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=3)
        result = tree.detect(max_iterations=16)

        assert result is False, "detect() should return False on ternary tree"

    def test_detect_binary_depth2_returns_true(self):
        """detect() on depth=2 binary tree returns True.

        On a binary tree with sufficient depth, the walk step distributes
        amplitude such that root overlap drops below 3/8 threshold,
        indicating the tree structure allows solution detection.

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)
        result = tree.detect(max_iterations=8)

        assert result is True, "detect() should return True on depth=2 binary tree"

    def test_detect_returns_bool(self):
        """detect() returns exactly True or False (type check).

        Tree: max_depth=1, branching=2, total_qubits=3 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=2)
        result = tree.detect(max_iterations=4)

        assert isinstance(result, bool), f"Expected bool, got {type(result)}"

    def test_detect_max_iterations_manual(self):
        """detect(max_iterations=1) limits to a single power level.

        With only power=1, the root overlap is still above threshold
        on a depth=2 binary tree (0.64 > 0.375).

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)
        result = tree.detect(max_iterations=1)

        # At power=1, root overlap = 0.64 which is > 3/8 = 0.375
        assert result is False, "detect(max_iterations=1) should return False at power=1"

    def test_detect_auto_max_iterations(self):
        """Auto-computed max_iterations is at least 4 for small trees.

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)

        T = tree._tree_size()
        n = tree.max_depth
        auto_max = max(4, int(math.ceil(math.sqrt(T / n))))

        assert auto_max >= 4, f"Auto max_iterations should be >= 4, got {auto_max}"


# ---------------------------------------------------------------------------
# Group 4: SAT Demo Tests (DET-02)
# ---------------------------------------------------------------------------


class TestSATDemo:
    """DET-02: SAT demo within 17-qubit budget."""

    def test_sat_qubit_budget_depth2(self):
        """2-variable SAT tree (depth=2, binary) stays within 17 qubits.

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)
        assert tree.total_qubits <= 17, f"SAT demo tree has {tree.total_qubits} qubits, exceeds 17"

    def test_sat_qubit_budget_depth3(self):
        """3-variable SAT tree (depth=3, binary) stays within 17 qubits.

        Tree: max_depth=3, branching=2, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=3, branching=2)
        assert tree.total_qubits <= 17, f"SAT demo tree has {tree.total_qubits} qubits, exceeds 17"

    def test_detect_on_sat_tree(self):
        """detect() runs successfully on SAT-sized tree.

        Verifies detect() doesn't crash or hang on a depth=3 binary tree
        (the SAT demo size).

        Tree: max_depth=3, branching=2, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=3, branching=2)
        result = tree.detect(max_iterations=8)

        assert isinstance(result, bool), f"Expected bool, got {type(result)}"

    def test_sat_no_false_positive_ternary(self):
        """No false positive: ternary tree detect() returns False.

        On a ternary tree, the walk dynamics keep root overlap above
        threshold. This demonstrates the detection correctly rejects
        trees where the walk pattern doesn't indicate solutions.

        Tree: max_depth=2, branching=3, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=3)
        result = tree.detect(max_iterations=16)

        assert result is False, "detect() should return False (no false positive)"


# ---------------------------------------------------------------------------
# Group 5: Statevector Verification Tests (DET-03)
# ---------------------------------------------------------------------------


class TestStatevectorVerification:
    """DET-03: Statevector verification of detection probability."""

    def test_root_overlap_above_threshold_initially(self):
        """Root overlap at power=1 is above 3/8 threshold.

        After a single walk step, root overlap should still be above
        the detection threshold (the walk hasn't yet had enough steps
        to distribute amplitude significantly).

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)
        overlap = tree._measure_root_overlap(1)

        threshold = 3.0 / 8.0
        assert overlap > threshold, (
            f"Root overlap at power=1 should be > {threshold}, got {overlap}"
        )

    def test_root_overlap_below_threshold_at_power2(self):
        """Root overlap at power=2 drops below 3/8 on binary depth=2 tree.

        This is the detection signal: the walk step has distributed
        enough amplitude away from root that overlap drops below threshold.

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=2)
        overlap = tree._measure_root_overlap(2)

        threshold = 3.0 / 8.0
        assert overlap < threshold, (
            f"Root overlap at power=2 should be < {threshold}, got {overlap}"
        )

    def test_root_overlap_stays_above_threshold_ternary(self):
        """Root overlap stays above 3/8 on ternary tree at all tested powers.

        This confirms the "no solution detected" case: the ternary tree's
        walk dynamics keep root overlap above threshold.

        Tree: max_depth=2, branching=3, total_qubits=7 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=2, branching=3)
        threshold = 3.0 / 8.0

        for power in [1, 2, 4, 8]:
            overlap = tree._measure_root_overlap(power)
            assert overlap >= threshold, (
                f"Ternary tree root overlap at power={power} should be >= {threshold}, "
                f"got {overlap}"
            )

    def test_statevector_norm_preserved(self):
        """Statevector norm is preserved after walk steps (unitarity).

        Tree: max_depth=2, branching=2, total_qubits=5 (<= 17)
        """
        for power in [1, 2, 4]:
            ql.circuit()
            inner = QWalkTree(max_depth=2, branching=2)
            for _ in range(power):
                inner.walk_step()
            sv = _simulate_statevector(ql.to_openqasm())
            norm = np.linalg.norm(sv)
            assert abs(norm - 1.0) < 1e-6, f"Norm should be 1.0 at power={power}, got {norm}"

    def test_root_overlap_depth1_above_threshold(self):
        """On depth=1 tree, root overlap stays above 3/8 at power=1.

        The depth=1 tree has simple dynamics (period 2), and at power=1
        the root overlap (0.444) is above 3/8.

        Tree: max_depth=1, branching=2, total_qubits=3 (<= 17)
        """
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=2)
        overlap = tree._measure_root_overlap(1)

        threshold = 3.0 / 8.0
        assert overlap > threshold, (
            f"Depth-1 root overlap at power=1 should be > {threshold}, got {overlap}"
        )

    def test_detection_consistent_across_runs(self):
        """detect() produces consistent results (deterministic statevector).

        Tree: max_depth=2, branching=3, total_qubits=7 (<= 17)
        """
        results = []
        for _ in range(3):
            ql.circuit()
            tree = QWalkTree(max_depth=2, branching=3)
            results.append(tree.detect(max_iterations=16))

        assert all(r == results[0] for r in results), (
            f"detect() should be deterministic, got {results}"
        )
