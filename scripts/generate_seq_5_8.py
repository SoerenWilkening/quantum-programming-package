#!/usr/bin/env python3
"""Generate add_seq_5_8.c with hardcoded QQ_add and cQQ_add sequences for widths 5-8."""

import math
from dataclasses import dataclass


@dataclass
class Gate:
    gate_type: str  # H, P, X
    target: int
    control: int | None
    value: float

    def to_c(self) -> str:
        if self.gate_type == "H":
            return f"""{{.Gate = H,
                                      .Target = {self.target},
                                      .NumControls = 0,
                                      .Control = {{0}},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}}"""
        elif self.gate_type == "P":
            return f"""{{.Gate = P,
                                      .Target = {self.target},
                                      .NumControls = 1,
                                      .Control = {{{self.control}}},
                                      .large_control = NULL,
                                      .GateValue = {self.format_angle()},
                                      .NumBasisGates = 0}}"""
        elif self.gate_type == "X":
            return f"""{{.Gate = X,
                                      .Target = {self.target},
                                      .NumControls = 1,
                                      .Control = {{{self.control}}},
                                      .large_control = NULL,
                                      .GateValue = 1,
                                      .NumBasisGates = 0}}"""

    def format_angle(self) -> str:
        """Format angle as SEQ_PI expression."""
        if self.value == 0:
            return "0"

        # Try to express as simple fraction of PI
        ratio = self.value / math.pi

        # Check common fractions
        for denom in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
            for numer in range(-denom * 2, denom * 2 + 1):
                if numer == 0:
                    continue
                if abs(ratio - numer / denom) < 1e-10:
                    if numer == 1 and denom == 1:
                        return "SEQ_PI"
                    elif numer == -1 and denom == 1:
                        return "-SEQ_PI"
                    elif numer == 1:
                        return f"SEQ_PI / {denom}"
                    elif numer == -1:
                        return f"-SEQ_PI / {denom}"
                    elif denom == 1:
                        return f"{numer} * SEQ_PI"
                    else:
                        return f"{numer} * SEQ_PI / {denom}"

        # Fallback to decimal
        return f"{self.value}"


def generate_qq_add(bits: int) -> list[list[Gate]]:
    """Generate QQ_add gate sequence matching IntegerAddition.c dynamic generation."""
    layers = []

    # QFT on target register [0, bits-1]
    # MSB-first processing (textbook QFT without swaps)
    for target in range(bits - 1, -1, -1):
        # H gate
        layers.append([Gate("H", target, None, 0)])

        # Controlled phase rotations from lower target bits
        for ctrl in range(target - 1, -1, -1):
            angle = math.pi / (2 ** (target - ctrl))
            layers.append([Gate("P", target, ctrl, angle)])

    # Addition phase: controlled rotations from control register [bits, 2*bits-1]
    rounds = 0
    for bit in range(bits - 1, -1, -1):
        for i in range(bits - rounds):
            target = rounds + i
            control = bits + (bits - 1 - bit)  # = 2*bits - 1 - bit
            value = 2 * math.pi / (2 ** (i + 1))
            layers.append([Gate("P", target, control, value)])
        rounds += 1

    # Inverse QFT on target register
    for target in range(bits):
        # Inverse controlled phase rotations
        for ctrl in range(target):
            angle = -math.pi / (2 ** (target - ctrl))
            layers.append([Gate("P", target, ctrl, angle)])
        # H gate
        layers.append([Gate("H", target, None, 0)])

    return layers


def generate_cqq_add(bits: int) -> list[list[Gate]]:
    """Generate cQQ_add gate sequence matching IntegerAddition.c dynamic generation."""
    layers = []
    control = 2 * bits  # Conditional control qubit (immediately after both operands)

    # QFT on target register [0, bits-1]
    for target in range(bits - 1, -1, -1):
        layers.append([Gate("H", target, None, 0)])
        for ctrl in range(target - 1, -1, -1):
            angle = math.pi / (2 ** (target - ctrl))
            layers.append([Gate("P", target, ctrl, angle)])

    # Block 1: unconditional half-rotations on Fourier qubits
    for bit in range(bits - 1, -1, -1):
        target_q = bits - 1 - bit  # reversed for textbook QFT
        value = 0
        for i in range(bits - bit):
            value += 2 * math.pi / (2 ** (i + 1)) / 2
        layers.append([Gate("P", target_q, control, value)])

    # Block 2: CNOT + negative half-rotations + CNOT
    rounds = 0
    for bit in range(bits - 1, -1, -1):
        # CNOT
        layers.append([Gate("X", bits + bit, control, 1)])
        # Negative half-rotations
        for i in range(bits - rounds):
            value = 2 * math.pi / (2 ** (i + 1)) / 2
            target_q = rounds + i
            layers.append([Gate("P", target_q, bits + bit, -value)])
        # CNOT
        layers.append([Gate("X", bits + bit, control, 1)])
        rounds += 1

    # Block 3: controlled rotations from b register
    # These can be parallelized
    rounds = 0
    for bit in range(bits - 1, -1, -1):
        parallel_gates = []
        for i in range(bits - rounds):
            value = 2 * math.pi / (2 ** (i + 1)) / 2
            target_q = rounds + i
            parallel_gates.append(Gate("P", target_q, bits + bit, value))
        layers.append(parallel_gates)
        rounds += 1

    # Inverse QFT on target register
    for target in range(bits):
        for ctrl in range(target):
            angle = -math.pi / (2 ** (target - ctrl))
            layers.append([Gate("P", target, ctrl, angle)])
        layers.append([Gate("H", target, None, 0)])

    return layers


def optimize_layers(layers: list[list[Gate]]) -> list[list[Gate]]:
    """Merge consecutive layers with non-overlapping qubits."""
    if not layers:
        return layers

    optimized = []
    current = list(layers[0])
    current_qubits = set()
    for g in current:
        current_qubits.add(g.target)
        if g.control is not None:
            current_qubits.add(g.control)

    for layer in layers[1:]:
        layer_qubits = set()
        for g in layer:
            layer_qubits.add(g.target)
            if g.control is not None:
                layer_qubits.add(g.control)

        # Can merge if no qubit overlap
        if not current_qubits & layer_qubits:
            current.extend(layer)
            current_qubits.update(layer_qubits)
        else:
            optimized.append(current)
            current = list(layer)
            current_qubits = layer_qubits

    optimized.append(current)
    return optimized


def generate_c_sequence(name: str, layers: list[list[Gate]], width: int) -> str:
    """Generate C code for a sequence."""
    lines = []

    # Generate layer arrays
    for i, layer in enumerate(layers):
        gates_str = ",\n                                     ".join(g.to_c() for g in layer)
        lines.append(f"static const gate_t {name}_{width}_L{i}[] = {{{gates_str}}};")
        lines.append("")

    # Generate layers array
    layer_names = ", ".join(f"{name}_{width}_L{i}" for i in range(len(layers)))
    # Split long lines
    if len(layers) > 6:
        layer_chunks = [layers[i : i + 6] for i in range(0, len(layers), 6)]
        layer_lines = []
        for chunk_idx, chunk in enumerate(layer_chunks):
            start_idx = chunk_idx * 6
            chunk_names = ", ".join(f"{name}_{width}_L{start_idx + i}" for i in range(len(chunk)))
            layer_lines.append(f"    {chunk_names}")
        layers_str = ",\n".join(layer_lines)
        lines.append(f"static const gate_t *{name}_{width}_LAYERS[] = {{\n{layers_str}}};")
    else:
        lines.append(f"static const gate_t *{name}_{width}_LAYERS[] = {{{layer_names}}};")

    # Generate gates per layer array
    gpl = [len(layer) for layer in layers]
    gpl_str = ", ".join(str(g) for g in gpl)
    if len(gpl) > 20:
        gpl_chunks = [gpl[i : i + 20] for i in range(0, len(gpl), 20)]
        gpl_lines = [", ".join(str(g) for g in chunk) for chunk in gpl_chunks]
        gpl_str = ",\n                                      ".join(gpl_lines)
    lines.append(f"static const num_t {name}_{width}_GPL[] = {{{gpl_str}}};")
    lines.append("")

    # Generate sequence struct
    lines.append(
        f"static const sequence_t HARDCODED_{name}_{width} = {{.seq = (gate_t **){name}_{width}_LAYERS,"
    )
    lines.append(f"                                              .num_layer = {len(layers)},")
    lines.append(f"                                              .used_layer = {len(layers)},")
    lines.append(
        f"                                              .gates_per_layer = (num_t *){name}_{width}_GPL}};"
    )

    return "\n".join(lines)


def main():
    output = []

    # Header
    output.append("//")
    output.append("// add_seq_5_8.c - Hardcoded QQ_add and cQQ_add sequences for 5-8 bit widths")
    output.append("//")
    output.append("// This file contains statically-defined gate sequences that match the")
    output.append(
        "// dynamically-generated sequences from QQ_add() and cQQ_add() in IntegerAddition.c"
    )
    output.append("//")
    output.append("")
    output.append('#include "sequences.h"')
    output.append("")
    output.append("// SEQ_PI as compile-time constant for static initializers")
    output.append("// (math.h M_PI is not a constant expression in standard C)")
    output.append("#ifndef SEQ_PI")
    output.append("#define SEQ_PI 3.14159265358979323846")
    output.append("#endif")
    output.append("")

    # Generate QQ_add for widths 5-8
    for width in [5, 6, 7, 8]:
        layers = generate_qq_add(width)
        layers = optimize_layers(layers)
        output.append(
            "// ============================================================================"
        )
        output.append(f"// QQ_ADD WIDTH {width} ({len(layers)} layers)")
        output.append(
            f"// Qubit layout: [0,{width - 1}] = target, [{width},{2 * width - 1}] = control"
        )
        output.append(
            "// ============================================================================"
        )
        output.append("")
        output.append(generate_c_sequence("QQ_ADD", layers, width))
        output.append("")

    # QQ_add dispatch helper for 5-8
    output.append("// ============================================================================")
    output.append("// QQ_ADD DISPATCH HELPER FOR 5-8")
    output.append("// ============================================================================")
    output.append("")
    output.append("const sequence_t *get_hardcoded_QQ_add_5_8(int bits) {")
    output.append("    switch (bits) {")
    output.append("    case 5:")
    output.append("        return &HARDCODED_QQ_ADD_5;")
    output.append("    case 6:")
    output.append("        return &HARDCODED_QQ_ADD_6;")
    output.append("    case 7:")
    output.append("        return &HARDCODED_QQ_ADD_7;")
    output.append("    case 8:")
    output.append("        return &HARDCODED_QQ_ADD_8;")
    output.append("    default:")
    output.append("        return NULL;")
    output.append("    }")
    output.append("}")
    output.append("")

    # Generate cQQ_add for widths 5-8
    for width in [5, 6, 7, 8]:
        layers = generate_cqq_add(width)
        layers = optimize_layers(layers)
        control_qubit = 2 * width
        output.append(
            "// ============================================================================"
        )
        output.append(f"// cQQ_ADD WIDTH {width} ({len(layers)} layers)")
        output.append(
            f"// Qubit layout: [0,{width - 1}] = target, [{width},{2 * width - 1}] = b, [{control_qubit}] = control"
        )
        output.append(
            "// ============================================================================"
        )
        output.append("")
        output.append(generate_c_sequence("cQQ_ADD", layers, width))
        output.append("")

    # cQQ_add dispatch helper for 5-8
    output.append("// ============================================================================")
    output.append("// cQQ_ADD DISPATCH HELPER FOR 5-8")
    output.append("// ============================================================================")
    output.append("")
    output.append("const sequence_t *get_hardcoded_cQQ_add_5_8(int bits) {")
    output.append("    switch (bits) {")
    output.append("    case 5:")
    output.append("        return &HARDCODED_cQQ_ADD_5;")
    output.append("    case 6:")
    output.append("        return &HARDCODED_cQQ_ADD_6;")
    output.append("    case 7:")
    output.append("        return &HARDCODED_cQQ_ADD_7;")
    output.append("    case 8:")
    output.append("        return &HARDCODED_cQQ_ADD_8;")
    output.append("    default:")
    output.append("        return NULL;")
    output.append("    }")
    output.append("}")
    output.append("")

    # Unified public dispatch functions
    output.append("// ============================================================================")
    output.append("// UNIFIED PUBLIC DISPATCH FUNCTIONS (covers all 1-8)")
    output.append("// ============================================================================")
    output.append("")
    output.append("const sequence_t *get_hardcoded_QQ_add(int bits) {")
    output.append("    if (bits >= 1 && bits <= 4) {")
    output.append("        return get_hardcoded_QQ_add_1_4(bits);")
    output.append("    } else if (bits >= 5 && bits <= 8) {")
    output.append("        return get_hardcoded_QQ_add_5_8(bits);")
    output.append("    }")
    output.append("    return NULL;  // > 8 or < 1: caller must use dynamic generation")
    output.append("}")
    output.append("")
    output.append("const sequence_t *get_hardcoded_cQQ_add(int bits) {")
    output.append("    if (bits >= 1 && bits <= 4) {")
    output.append("        return get_hardcoded_cQQ_add_1_4(bits);")
    output.append("    } else if (bits >= 5 && bits <= 8) {")
    output.append("        return get_hardcoded_cQQ_add_5_8(bits);")
    output.append("    }")
    output.append("    return NULL;")
    output.append("}")
    output.append("")

    print("\n".join(output))


if __name__ == "__main__":
    main()
