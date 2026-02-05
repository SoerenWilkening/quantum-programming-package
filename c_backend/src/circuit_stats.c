//
// circuit_stats.c - Circuit statistics implementation
// Dependencies: circuit_stats.h, circuit.h
//

#include "circuit_stats.h"
#include "circuit.h"

size_t circuit_gate_count(circuit_t *circ) {
    if (circ == NULL)
        return 0;
    return circ->used; // Already tracked in circuit structure
}

num_t circuit_depth(circuit_t *circ) {
    if (circ == NULL)
        return 0;
    return circ->used_layer; // Already tracked
}

num_t circuit_qubit_count(circuit_t *circ) {
    if (circ == NULL)
        return 0;
    return circ->used_qubits + 1; // +1 because 0-indexed
}

gate_counts_t circuit_gate_counts(circuit_t *circ) {
    gate_counts_t counts = {0};

    if (circ == NULL)
        return counts;

    // Iterate through all layers and gates
    for (num_t layer = 0; layer < circ->used_layer; layer++) {
        for (num_t gate_idx = 0; gate_idx < circ->used_gates_per_layer[layer]; gate_idx++) {
            gate_t *g = &circ->sequence[layer][gate_idx];

            // Count by gate type and control count
            switch (g->Gate) {
            case X:
                if (g->NumControls == 0)
                    counts.x_gates++;
                else if (g->NumControls == 1)
                    counts.cx_gates++;
                else
                    counts.ccx_gates++; // 2+ controls = Toffoli variant
                break;
            case Y:
                counts.y_gates++;
                break;
            case Z:
                counts.z_gates++;
                break;
            case H:
                counts.h_gates++;
                break;
            case P:
                counts.p_gates++;
                break;
            default:
                counts.other_gates++;
                break;
            }
        }
    }

    return counts;
}
