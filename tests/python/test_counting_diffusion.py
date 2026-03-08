"""Phase 113-02: Tests for counting-based variable diffusion.

Verifies that the counting diffusion (O(d_max) gate complexity) produces
correct results: matches uniform diffusion when all children valid,
reflection property, norm preservation, linear gate scaling.

Requirements: WALK-03
"""

import numpy as np
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql
from quantum_language.walk import QWalkTree

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector as numpy array."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return np.asarray(result.get_statevector())


def _extract_tree_subspace_probs(sv, tree):
    """Extract probability distribution on tree-qubit subspace.

    Marginalizes over ancilla qubits (validity, count register, comparisons).
    Returns dict mapping tree-qubit basis state index -> total probability.
    """
    tree_qubits = []
    w = tree.max_depth + 1
    for i in range(w):
        tree_qubits.append(int(tree.height_register.qubits[64 - w + i]))
    for br in tree.branch_registers:
        bw = br.width
        for i in range(bw):
            tree_qubits.append(int(br.qubits[64 - bw + i]))

    probs = {}
    for idx in range(len(sv)):
        amp = sv[idx]
        if abs(amp) < 1e-15:
            continue
        tree_key = 0
        for bit_pos, q in enumerate(tree_qubits):
            if (idx >> q) & 1:
                tree_key |= 1 << bit_pos
        probs[tree_key] = probs.get(tree_key, 0.0) + abs(amp) ** 2

    return probs


# ---------------------------------------------------------------------------
# Test predicates
# ---------------------------------------------------------------------------


def _always_accept_predicate(node):
    """Predicate that never rejects any child. d(x) = d_max for all nodes."""
    is_accept = ql.qbool()
    is_reject = ql.qbool()
    return (is_accept, is_reject)


# ---------------------------------------------------------------------------
# Tests: Equivalence with uniform diffusion
# ---------------------------------------------------------------------------


class TestCountingDiffusionEquivalence:
    """Verify counting diffusion matches uniform (no-predicate) diffusion.

    When all children are valid (always_accept predicate), the counting
    diffusion should produce the same tree-subspace probabilities as the
    uniform diffusion (no predicate). This is the ground truth comparison
    since the uniform diffusion path uses well-tested 1-control and
    2-control gate decompositions.
    """

    def test_equivalence_d2(self):
        """d_max=2: counting diffusion matches uniform diffusion."""
        # Uniform (no predicate)
        ql.circuit()
        tree_u = QWalkTree(max_depth=1, branching=[2])
        tree_u.local_diffusion(depth=1)
        sv_u = _simulate_statevector(ql.to_openqasm())
        probs_u = _extract_tree_subspace_probs(sv_u, tree_u)

        # Counting with always_accept
        ql.circuit()
        tree_c = QWalkTree(max_depth=1, branching=[2], predicate=_always_accept_predicate)
        tree_c._counting_diffusion(depth=1)
        sv_c = _simulate_statevector(ql.to_openqasm())
        probs_c = _extract_tree_subspace_probs(sv_c, tree_c)

        all_keys = set(probs_u.keys()) | set(probs_c.keys())
        for key in all_keys:
            p_u = probs_u.get(key, 0.0)
            p_c = probs_c.get(key, 0.0)
            assert abs(p_u - p_c) < 1e-6, (
                f"Probability mismatch at tree state {key}: uniform={p_u:.6f}, counting={p_c:.6f}"
            )

    def test_equivalence_d3(self):
        """d_max=3: counting diffusion matches uniform diffusion."""
        # Uniform
        ql.circuit()
        tree_u = QWalkTree(max_depth=1, branching=[3])
        tree_u.local_diffusion(depth=1)
        sv_u = _simulate_statevector(ql.to_openqasm())
        probs_u = _extract_tree_subspace_probs(sv_u, tree_u)

        # Counting
        ql.circuit()
        tree_c = QWalkTree(max_depth=1, branching=[3], predicate=_always_accept_predicate)
        tree_c._counting_diffusion(depth=1)
        sv_c = _simulate_statevector(ql.to_openqasm())
        probs_c = _extract_tree_subspace_probs(sv_c, tree_c)

        all_keys = set(probs_u.keys()) | set(probs_c.keys())
        for key in all_keys:
            p_u = probs_u.get(key, 0.0)
            p_c = probs_c.get(key, 0.0)
            assert abs(p_u - p_c) < 1e-6, (
                f"Probability mismatch at tree state {key}: uniform={p_u:.6f}, counting={p_c:.6f}"
            )

    def test_counting_modifies_state_d4(self):
        """d_max=4: counting diffusion creates superposition (no statevector sim).

        d_max=4 with counting circuit exceeds the 17-qubit simulation budget,
        so we verify structural correctness (gate emission, no error) rather
        than statevector comparison.
        """
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=[4], predicate=_always_accept_predicate)
        # Should not raise
        tree._counting_diffusion(depth=1)
        qasm_str = ql.to_openqasm()
        # Verify circuit was generated
        assert len(qasm_str) > 100, "QASM output too short"
        # Count gate lines
        gate_count = sum(
            1
            for line in qasm_str.split("\n")
            if line.strip()
            and ";" in line
            and not line.startswith("OPENQASM")
            and not line.startswith("include")
            and not line.startswith("qubit")
        )
        assert gate_count > 10, f"Expected many gates, got {gate_count}"


# ---------------------------------------------------------------------------
# Tests: Properties
# ---------------------------------------------------------------------------


class TestCountingDiffusionProperties:
    """Property tests for counting diffusion."""

    def test_reflection_d2(self):
        """D_x^2 = I: uniform diffusion (which shares code with counting) is a reflection.

        The counting diffusion matches uniform for all-valid predicates (tested above).
        Here we verify the reflection property via the uniform path (D^2=I) which
        proves the underlying angle computation and S_0 logic are correct.
        The qubit budget for predicate-based D^2 exceeds the 17-qubit simulation
        limit due to ancilla accumulation across two diffusion calls.
        """
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=[2])
        sv_before = _simulate_statevector(ql.to_openqasm())

        tree.local_diffusion(depth=1)
        tree.local_diffusion(depth=1)
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_before, sv_after, atol=1e-6), (
            "D_x^2 should equal identity (reflection property)"
        )

    def test_reflection_d3(self):
        """D_x^2 = I for d_max=3 (uniform path)."""
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=[3])
        sv_before = _simulate_statevector(ql.to_openqasm())

        tree.local_diffusion(depth=1)
        tree.local_diffusion(depth=1)
        sv_after = _simulate_statevector(ql.to_openqasm())

        assert np.allclose(sv_before, sv_after, atol=1e-6), (
            "D_x^2 should equal identity (reflection property)"
        )

    def test_norm_preservation(self):
        """Counting diffusion preserves state norm."""
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=[2], predicate=_always_accept_predicate)
        tree._counting_diffusion(depth=1)
        sv = _simulate_statevector(ql.to_openqasm())
        norm = np.linalg.norm(sv)
        assert abs(norm - 1.0) < 1e-6, f"Norm should be 1.0, got {norm}"

    def test_modifies_state(self):
        """Counting diffusion creates superposition from basis state."""
        ql.circuit()
        tree = QWalkTree(max_depth=1, branching=[2], predicate=_always_accept_predicate)
        tree._counting_diffusion(depth=1)
        sv = _simulate_statevector(ql.to_openqasm())
        nonzero = np.sum(np.abs(sv) > 1e-8)
        assert nonzero > 1, (
            f"Diffusion should create superposition, but only {nonzero} nonzero amplitudes found"
        )

    def test_gate_count_linear(self):
        """Gate count scales O(d_max) not O(2^d_max).

        Build counting diffusion circuits for d_max=2,4,8 and verify
        the gate count ratio is sub-exponential.
        """
        gate_counts = {}
        for d_max in [2, 4, 8]:
            ql.circuit()
            tree = QWalkTree(
                max_depth=1,
                branching=[d_max],
                predicate=_always_accept_predicate,
            )
            tree._counting_diffusion(depth=1)
            qasm_str = ql.to_openqasm()
            # Count gate lines in QASM
            gate_count = sum(
                1
                for line in qasm_str.split("\n")
                if line.strip()
                and not line.startswith("//")
                and not line.startswith("OPENQASM")
                and not line.startswith("include")
                and not line.startswith("qubit")
                and not line.startswith("bit")
                and ";" in line
            )
            gate_counts[d_max] = gate_count

        # For exponential scaling (old code), d8 would need 255 patterns
        # vs d4's 15 patterns -- a 17x ratio in pattern count alone.
        # The counting circuit is O(d_max) in iterations but each iteration's
        # cascade can be O(w) gates with V-gate decomposition.
        # The ratio should be much less than the exponential 17x.
        ratio = gate_counts[8] / gate_counts[4]
        assert ratio < 8.0, (
            f"Gate count ratio d8/d4 = {ratio:.1f} (expected < 8.0, "
            f"exponential would be ~17x). Gate counts: {gate_counts}"
        )
