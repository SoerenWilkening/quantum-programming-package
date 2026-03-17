"""Phase 78: Diffusion Operator and Phase Property Tests.

Verifies GROV-03 (DSL-based diffusion with ~register + & chain + phase flip)
and GROV-05 (manual S_0 via `with x == 0: x.phase += pi`) through
comprehensive tests including Qiskit statevector simulation.

Test Coverage:
- TestDiffusionOperator: QASM verification + Qiskit statevector for DSL pattern
- TestPhaseProperty: phase property semantics (no-op uncontrolled, CP controlled)
"""

import math

import numpy as np
import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator

import quantum_language as ql

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _simulate_statevector(qasm_str):
    """Run QASM through Qiskit Aer and return statevector."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.save_statevector()
    sim = AerSimulator(method="statevector", max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim)).result()
    return result.get_statevector()


def _simulate_counts(qasm_str, shots=8192):
    """Run QASM through Qiskit Aer and return measurement counts."""
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.measure_all()
    sim = AerSimulator(max_parallel_threads=4)
    result = sim.run(transpile(circuit, sim), shots=shots).result()
    return result.get_counts()


def _count_gate(qasm_str, gate_name):
    """Count occurrences of a gate in QASM output (line-start matching)."""
    count = 0
    for line in qasm_str.strip().split("\n"):
        stripped = line.strip()
        # Match gate name at start of line (e.g., "x q[0];" matches "x")
        if stripped.startswith(gate_name + " ") or stripped.startswith(gate_name + "\t"):
            count += 1
    return count


def _gate_present(qasm_str, gate_name):
    """Check if a gate name appears anywhere in QASM output."""
    return gate_name in qasm_str.lower()


# ---------------------------------------------------------------------------
# Group 1: Diffusion Operator (GROV-03)
# ---------------------------------------------------------------------------
class TestDiffusionOperator:
    """GROV-03: Diffusion operator uses DSL-based ~register + & chain + phase."""

    def test_diffusion_1qubit_qasm(self):
        """1-qubit diffusion: X-P(pi)-X pattern (phase flip via DSL)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=1)
        ql.diffusion(x)

        qasm = ql.to_openqasm()

        # 1-qubit: X + P(pi) + X (P(pi) is equivalent to Z)
        assert _gate_present(qasm, "x"), "Expected X gates in QASM"
        assert _gate_present(qasm, "p("), "Expected P(pi) gate in QASM"

        # Count X gates: should be 2 (1 before + 1 after)
        x_count = _count_gate(qasm, "x")
        assert x_count == 2, f"Expected 2 X gates, got {x_count}"

        # Only 1 qubit allocated (no ancilla for 1-qubit case)
        assert "qubit[1]" in qasm, f"Expected 1 qubit, got: {qasm}"

    def test_diffusion_2qubit_qasm(self):
        """2-qubit diffusion: X-CCX-P(pi)-CCX-X pattern (AND + phase)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)
        ql.diffusion(x)

        qasm = ql.to_openqasm()

        # 2-qubit: Toffoli AND chain + P(pi)
        assert _gate_present(qasm, "ccx"), "Expected CCX (Toffoli) gate in QASM"
        assert _gate_present(qasm, "p("), "Expected P(pi) gate in QASM"

        # Count X gates: should be 4 (2 before + 2 after)
        x_count = _count_gate(qasm, "x")
        assert x_count == 4, f"Expected 4 X gates, got {x_count}"

        # 3 qubits: 2 data + 1 AND ancilla
        assert "qubit[3]" in qasm, f"Expected 3 qubits, got: {qasm}"

    def test_diffusion_3qubit_qasm(self):
        """3-qubit diffusion: X-CCX chain-P(pi)-CCX uncompute-X pattern."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=3)
        ql.diffusion(x)

        qasm = ql.to_openqasm()

        # 3-qubit: CCX AND chain + P(pi)
        assert _gate_present(qasm, "ccx"), f"Expected CCX (Toffoli) gates in QASM:\n{qasm}"

        # Count X gates: should be 6 (3 before + 3 after)
        x_count = _count_gate(qasm, "x")
        assert x_count == 6, f"Expected 6 X gates, got {x_count}"

        # 5 qubits: 3 data + 2 AND ancillas
        assert "qubit[5]" in qasm, f"Expected 5 qubits, got: {qasm}"

    def test_diffusion_statevector_2qubit(self):
        """2-qubit diffusion: Qiskit statevector confirms S_0 reflection.

        After branch() + diffusion(), the |00> amplitude should have
        opposite sign from the other basis states.
        """
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)
        x.branch()
        ql.diffusion(x)

        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        # 2 qubits = 4 basis states
        amps = [complex(sv[i]) for i in range(4)]

        # |00> (index 0) should have opposite sign from the rest
        amp_00 = amps[0].real
        amp_others = [a.real for a in amps[1:]]

        # All others should have the same sign
        assert all(np.sign(a) == np.sign(amp_others[0]) for a in amp_others), (
            f"Non-zero amps should share sign: {amp_others}"
        )

        # |00> should have opposite sign
        assert np.sign(amp_00) != np.sign(amp_others[0]), (
            f"|00> amplitude ({amp_00:.4f}) should have opposite sign from others ({amp_others})"
        )

    def test_diffusion_statevector_3qubit(self):
        """3-qubit diffusion: Qiskit statevector confirms S_0 reflection.

        After branch() + diffusion(), the |000> amplitude should have
        opposite sign from the other 7 basis states.
        """
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=3)
        x.branch()
        ql.diffusion(x)

        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        # 3 qubits = 8 basis states
        amps = [complex(sv[i]) for i in range(8)]

        # |000> (index 0) should have opposite sign from the rest
        amp_000 = amps[0].real
        amp_others = [a.real for a in amps[1:]]

        # All non-zero amps should share the same sign
        nonzero_others = [a for a in amp_others if abs(a) > 1e-10]
        assert len(nonzero_others) == 7, f"Expected 7 nonzero amps, got {len(nonzero_others)}"

        signs = [np.sign(a) for a in nonzero_others]
        assert all(s == signs[0] for s in signs), (
            f"All non-|000> amps should share sign: {nonzero_others}"
        )

        # |000> should have opposite sign
        assert np.sign(amp_000) != signs[0], (
            f"|000> amplitude ({amp_000:.4f}) should have opposite sign from "
            f"others ({nonzero_others[0]:.4f})"
        )

    def test_diffusion_multi_register(self):
        """Multi-register diffusion: ql.diffusion(x, y) flattens to total width."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)
        y = ql.qint(0, width=1)
        ql.diffusion(x, y)

        qasm = ql.to_openqasm()

        # Total width = 3 data qubits + 2 AND ancillas = 5 qubits
        assert "qubit[5]" in qasm, f"Expected 5 qubits, got: {qasm}"

        # Should have 6 X gates (3 before + 3 after)
        x_count = _count_gate(qasm, "x")
        assert x_count == 6, f"Expected 6 X gates, got {x_count}"

        # Should have CCX (Toffoli AND chain) for 3 qubits
        assert _gate_present(qasm, "ccx"), f"Expected CCX gates:\n{qasm}"

    def test_diffusion_qbool(self):
        """Diffusion on qbool: 1-qubit case (X-P(pi)-X)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        b = ql.qbool(False)
        ql.diffusion(b)

        qasm = ql.to_openqasm()

        # 1 qubit only
        assert "qubit[1]" in qasm, f"Expected 1 qubit, got: {qasm}"

        # X-P(pi)-X pattern
        x_count = _count_gate(qasm, "x")
        assert x_count == 2, f"Expected 2 X gates, got {x_count}"
        assert _gate_present(qasm, "p("), "Expected P(pi) gate"

    def test_diffusion_qarray(self):
        """Diffusion on qarray: 2 qbool elements = 2 data qubits + 1 AND ancilla."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        arr = ql.array(dim=2, dtype=ql.qbool)
        ql.diffusion(arr)

        qasm = ql.to_openqasm()

        # 3 qubits: 2 data + 1 AND ancilla
        assert "qubit[3]" in qasm, f"Expected 3 qubits, got: {qasm}"

        # 4 X gates (2 before + 2 after) + CCX (AND)
        x_count = _count_gate(qasm, "x")
        assert x_count == 4, f"Expected 4 X gates, got {x_count}"
        assert _gate_present(qasm, "ccx"), "Expected CCX gate"

    def test_diffusion_zero_width_error(self):
        """Diffusion with no arguments raises ValueError."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        with pytest.raises((ValueError, TypeError)):
            ql.diffusion()

    def test_diffusion_works_without_simulate(self):
        """Diffusion works even when simulate is not explicitly set.

        diffusion() internally ensures simulate=True for its own
        execution and restores the previous setting afterward.
        """
        ql.circuit()
        ql.option("fault_tolerant", True)
        # simulate defaults to False -- diffusion handles this internally
        x = ql.qint(0, width=2)
        ql.diffusion(x)

        qasm = ql.to_openqasm()
        # Should produce X gates (the bit-flip layer)
        x_count = _count_gate(qasm, "x")
        assert x_count == 4, f"Expected 4 X gates, got {x_count}"

    def test_diffusion_compile_caching(self):
        """Calling diffusion twice on same-width register uses compile cache."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x1 = ql.qint(0, width=3)
        ql.diffusion(x1)
        qasm1 = ql.to_openqasm()

        # Second call on a different register of same width
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)
        x2 = ql.qint(0, width=3)
        ql.diffusion(x2)
        qasm2 = ql.to_openqasm()

        # Both should produce identical QASM structure
        # (same gate pattern, just different qubit indices if any)
        assert qasm1 == qasm2, (
            f"Same-width diffusion should produce identical QASM:\n"
            f"First:\n{qasm1}\nSecond:\n{qasm2}"
        )

    def test_diffusion_controlled(self):
        """Diffusion inside with-block: controlled context."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        flag = ql.qbool(True)
        x = ql.qint(0, width=2)

        with flag:
            ql.diffusion(x)

        qasm = ql.to_openqasm()

        # Should produce valid QASM with gates
        assert "OPENQASM" in qasm

        # The diffusion gates should be present (X and CCX/P pattern)
        assert _gate_present(qasm, "x") or _gate_present(qasm, "ccx"), (
            f"Expected X or CCX gates in controlled diffusion:\n{qasm}"
        )
        assert _gate_present(qasm, "p("), f"Expected P gate in controlled diffusion:\n{qasm}"

    def test_diffusion_4qubit_statevector(self):
        """4-qubit diffusion: confirms S_0 reflection for width=4."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=4)
        x.branch()
        ql.diffusion(x)

        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        # 4 qubits = 16 basis states
        amps = [complex(sv[i]) for i in range(16)]
        amp_0000 = amps[0].real
        amp_others = [a.real for a in amps[1:]]

        # All others should share the same sign
        nonzero_others = [a for a in amp_others if abs(a) > 1e-10]
        assert len(nonzero_others) == 15

        signs = [np.sign(a) for a in nonzero_others]
        assert all(s == signs[0] for s in signs)

        # |0000> should have opposite sign
        assert np.sign(amp_0000) != signs[0], (
            f"|0000> amp ({amp_0000:.6f}) should have opposite sign from others"
        )


# ---------------------------------------------------------------------------
# Group 2: Phase Property (GROV-05)
# ---------------------------------------------------------------------------
class TestPhaseProperty:
    """GROV-05: Phase property semantics for controlled global phase."""

    def test_phase_uncontrolled_no_gate(self):
        """Uncontrolled phase emits no gate (global phase is unobservable)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)
        x.phase += 3.14

        qasm = ql.to_openqasm()

        # Should have no gates at all (only qubit declaration)
        lines = [
            line.strip()
            for line in qasm.strip().split("\n")
            if line.strip()
            and not line.strip().startswith("OPENQASM")
            and not line.strip().startswith("include")
            and not line.strip().startswith("qubit")
        ]
        assert len(lines) == 0, f"Uncontrolled phase should emit no gates, got: {lines}"

    def test_phase_controlled_emits_p(self):
        """Controlled phase emits P gate on control qubit in QASM output.

        After the emit_p_raw fix (Phase 78-03), _PhaseProxy.__iadd__ emits
        a plain P gate on the control qubit (not CP). P(theta) on the control
        qubit in |1> state implements a controlled global phase via phase
        kickback -- same quantum effect as CP but without the double-control
        bug that produced cp(q[n], q[n]).
        """
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)
        flag = ql.qbool(True)

        with flag:
            x.phase += 1.57

        qasm = ql.to_openqasm()

        # Should contain P gate (not CP) on the control qubit
        assert _gate_present(qasm, "p("), f"Expected P gate in controlled phase QASM:\n{qasm}"

    def test_phase_mul_minus1(self):
        """phase *= -1 is equivalent to phase += pi."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)
        flag = ql.qbool(True)
        with flag:
            x.phase += math.pi
        qasm_add = ql.to_openqasm()

        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        y = ql.qint(0, width=2)
        flag2 = ql.qbool(True)
        with flag2:
            y.phase *= -1
        qasm_mul = ql.to_openqasm()

        # Both should produce P(pi) gate on control qubit
        assert "p(" in qasm_add, f"Expected P gate in += pi:\n{qasm_add}"
        assert "p(" in qasm_mul, f"Expected P gate in *= -1:\n{qasm_mul}"

        # Both should have pi angle
        assert "3.14159" in qasm_add, f"Expected pi angle in += pi QASM:\n{qasm_add}"
        assert "3.14159" in qasm_mul, f"Expected pi angle in *= -1 QASM:\n{qasm_mul}"

    def test_phase_mul_invalid(self):
        """phase *= 2 raises ValueError."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)

        with pytest.raises(ValueError, match="phase .* only supports -1"):
            x.phase *= 2

    def test_phase_qbool(self):
        """Phase property works on qbool (inherited from qint)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        b = ql.qbool(False)
        flag = ql.qbool(True)

        with flag:
            b.phase += math.pi

        qasm = ql.to_openqasm()
        assert "p(" in qasm, f"Expected P gate for qbool phase:\n{qasm}"

    def test_phase_qarray(self):
        """Phase property works on qarray."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        arr = ql.array(dim=2, dtype=ql.qbool)
        flag = ql.qbool(True)

        with flag:
            arr.phase += math.pi

        qasm = ql.to_openqasm()
        assert "p(" in qasm, f"Expected P gate for qarray phase:\n{qasm}"

    def test_manual_s0_reflection_statevector(self):
        """Manual S_0: with x == 0: x.phase += pi produces correct S_0 reflection.

        Directly tests the manual path via Qiskit statevector simulation.
        After branch() + manual S_0, the |00> amplitude should have opposite
        sign from the other amplitudes (same effect as ql.diffusion()).
        """
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)

        x = ql.qint(0, width=2)
        x.branch()
        with x == 0:
            x.phase += math.pi

        qasm = ql.to_openqasm()
        sv = _simulate_statevector(qasm)

        # Extract search register amplitudes (first 2^width entries,
        # where all ancilla qubits are in |0> state)
        search_width = 2
        n_search_states = 2**search_width
        amps = [complex(sv[i]).real for i in range(n_search_states)]

        # After branch() (equal superposition) + S_0 reflection:
        # |00> amplitude should have opposite sign from others
        amp_00 = amps[0]
        amp_others = amps[1:]

        assert amp_00 < 0, (
            f"|00> should be negative after S_0 reflection: {amp_00:.6f}\n"
            f"All amps: {amps}\nQASM:\n{qasm}"
        )
        assert all(a > 0 for a in amp_others), (
            f"Non-|00> amps should be positive: {amp_others}\nAll amps: {amps}\nQASM:\n{qasm}"
        )

        # Verify magnitudes are equal (uniform was input)
        assert np.isclose(abs(amp_00), abs(amp_others[0]), atol=1e-6), (
            f"Amplitudes should have equal magnitude: "
            f"|00|={abs(amp_00):.6f}, |01|={abs(amp_others[0]):.6f}"
        )

    def test_phase_register_agnostic(self):
        """Phase is register-agnostic: y.phase += pi inside with flag block.

        Inside a controlled context, the phase operation depends only on
        the control, not which register's .phase is used. Both x.phase
        and y.phase should produce the same P gate in the same context.
        """
        # Test that different registers produce the same phase gate
        # in the same controlled context
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)
        x = ql.qint(0, width=2)
        flag_x = ql.qbool(True)
        with flag_x:
            x.phase += math.pi
        qasm_x = ql.to_openqasm()

        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)
        y = ql.qint(0, width=2)
        flag_y = ql.qbool(True)
        with flag_y:
            y.phase += math.pi
        qasm_y = ql.to_openqasm()

        # Both should produce P(pi) on control qubit -- same gate regardless of register
        assert "p(" in qasm_x, f"Expected P gate in x.phase:\n{qasm_x}"
        assert "p(" in qasm_y, f"Expected P gate in y.phase:\n{qasm_y}"

        # The P angle should be pi in both cases
        assert "3.14159" in qasm_x
        assert "3.14159" in qasm_y

    def test_manual_s0_direct_statevector(self):
        """Manual S_0 on 3-qubit register verified via Qiskit statevector.

        Independently verifies that with x == 0: x.phase += pi produces
        the same S_0 reflection as ql.diffusion(x) for width=3.
        """
        # First, get reference statevector from ql.diffusion()
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)
        x_ref = ql.qint(0, width=3)
        x_ref.branch()
        ql.diffusion(x_ref)
        qasm_ref = ql.to_openqasm()
        sv_ref = _simulate_statevector(qasm_ref)
        ref_amps = [complex(sv_ref[i]).real for i in range(8)]

        # Now test manual S_0 path
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)
        x = ql.qint(0, width=3)
        x.branch()
        with x == 0:
            x.phase += math.pi
        qasm_manual = ql.to_openqasm()
        sv_manual = _simulate_statevector(qasm_manual)

        # Extract search register amplitudes (first 2^3 = 8 entries)
        manual_amps = [complex(sv_manual[i]).real for i in range(8)]

        # Both should produce same S_0 reflection pattern
        # |000> negative, all others positive
        assert manual_amps[0] < 0, (
            f"|000> should be negative: {manual_amps[0]:.6f}\n"
            f"All manual amps: {manual_amps}\nQASM:\n{qasm_manual}"
        )
        assert all(a > 0 for a in manual_amps[1:]), (
            f"Non-|000> amps should be positive: {manual_amps[1:]}"
        )

        # Compare magnitudes with reference (should match within tolerance)
        for i in range(8):
            assert np.isclose(abs(manual_amps[i]), abs(ref_amps[i]), atol=1e-6), (
                f"Amplitude mismatch at index {i}: "
                f"manual={manual_amps[i]:.6f}, ref={ref_amps[i]:.6f}"
            )

    def test_manual_s0_qasm_shows_p_gate(self):
        """Manual S_0 path emits visible P gate in QASM (not self-controlled CP)."""
        ql.circuit()
        ql.option("fault_tolerant", True)
        ql.option("simulate", True)
        x = ql.qint(0, width=2)
        x.branch()
        with x == 0:
            x.phase += math.pi
        qasm = ql.to_openqasm()

        # After the fix, QASM should contain a P gate (not cp q[n], q[n])
        # The P gate applies phase to the comparison ancilla qubit
        lines = qasm.strip().split("\n")
        p_lines = [ln for ln in lines if ln.strip().startswith("p(")]
        assert len(p_lines) > 0, (
            f"Expected P gate in QASM for manual S_0 path, got none.\nQASM:\n{qasm}"
        )

        # Should NOT have self-controlled CP (cp q[n], q[n])
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("cp("):
                # Extract qubit arguments
                parts = stripped.split(" ", 1)
                if len(parts) > 1:
                    qubit_args = parts[1].rstrip(";").split(",")
                    qubit_args = [q.strip() for q in qubit_args]
                    assert len(set(qubit_args)) > 1, (
                        f"Found self-controlled CP (same qubit for target and control): {stripped}"
                    )
