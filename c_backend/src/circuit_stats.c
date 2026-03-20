//
// circuit_stats.c - Circuit statistics implementation
// Dependencies: circuit_stats.h, circuit.h
//

#include "circuit_stats.h"
#include "circuit.h"

size_t circuit_gate_count(const circuit_t *circ) {
    if (circ == NULL)
        return 0;
    return circ->used; // Already tracked in circuit structure
}

num_t circuit_depth(const circuit_t *circ) {
    if (circ == NULL)
        return 0;
    return circ->used_layer; // Already tracked
}

num_t circuit_qubit_count(const circuit_t *circ) {
    if (circ == NULL)
        return 0;
    return circ->used_qubits + 1; // +1 because 0-indexed
}

gate_counts_t circuit_gate_counts(const circuit_t *circ) {
    gate_counts_t counts = {0};

    if (circ == NULL)
        return counts;

    // Iterate through all layers and gates
    for (num_t layer = 0; layer < circ->used_layer; layer++) {
        for (num_t gate_idx = 0; gate_idx < circ->used_gates_per_layer[layer]; gate_idx++) {
            const gate_t *g = &circ->sequence[layer][gate_idx];

            // Count by gate type and control count
            switch (g->Gate) {
            case X:
                if (g->NumControls == 0)
                    counts.x_gates++;
                else if (g->NumControls == 1)
                    counts.cx_gates++;
                else if (g->NumControls == 2)
                    counts.ccx_gates++; // Exactly 2 controls = Toffoli
                else
                    counts.other_gates++; // 3+ controls = other (MCX should not appear in
                                          // decomposed mode)
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
            case T_GATE:
                counts.t_gates++;
                break;
            case TDG_GATE:
                counts.tdg_gates++;
                break;
            default:
                counts.other_gates++;
                break;
            }
        }
    }

    // T-count: actual T/Tdg gates if present, otherwise estimate from CCX count
    if (counts.t_gates > 0 || counts.tdg_gates > 0) {
        // Actual T/Tdg gates present (toffoli_decompose was on)
        counts.t_count = counts.t_gates + counts.tdg_gates;
    } else {
        // Estimate from CCX count (each CCX = 7 T gates)
        counts.t_count = 7 * counts.ccx_gates;
    }

    return counts;
}

gate_counts_t circuit_gate_counts_range(const circuit_t *circ, num_t start_layer, num_t end_layer) {
    gate_counts_t counts = {0};

    if (circ == NULL)
        return counts;

    if (start_layer >= end_layer)
        return counts;

    if (end_layer > circ->used_layer)
        end_layer = circ->used_layer;

    for (num_t layer = start_layer; layer < end_layer; layer++) {
        for (num_t gate_idx = 0; gate_idx < circ->used_gates_per_layer[layer]; gate_idx++) {
            const gate_t *g = &circ->sequence[layer][gate_idx];

            switch (g->Gate) {
            case X:
                if (g->NumControls == 0)
                    counts.x_gates++;
                else if (g->NumControls == 1)
                    counts.cx_gates++;
                else if (g->NumControls == 2)
                    counts.ccx_gates++;
                else
                    counts.other_gates++;
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
            case T_GATE:
                counts.t_gates++;
                break;
            case TDG_GATE:
                counts.tdg_gates++;
                break;
            default:
                counts.other_gates++;
                break;
            }
        }
    }

    if (counts.t_gates > 0 || counts.tdg_gates > 0) {
        counts.t_count = counts.t_gates + counts.tdg_gates;
    } else {
        counts.t_count = 7 * counts.ccx_gates;
    }

    return counts;
}
