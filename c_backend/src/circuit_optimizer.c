//
// circuit_optimizer.c - Post-construction circuit optimization
// Dependencies: circuit_optimizer.h, circuit.h, gate.h
//

#include "circuit_optimizer.h"
#include "circuit.h"
#include "gate.h"
#include <string.h>

// Forward declarations for internal helpers
static circuit_t *copy_circuit(circuit_t *src);
static int apply_cancel_inverse(circuit_t *circ);
static int apply_merge(circuit_t *circ);

// Deep copy a circuit (simplified - rebuilds via add_gate)
static circuit_t *copy_circuit(circuit_t *src) {
    if (src == NULL)
        return NULL;

    circuit_t *dst = init_circuit();
    if (dst == NULL)
        return NULL;

    // Copy gates layer by layer
    for (num_t layer = 0; layer < src->used_layer; layer++) {
        for (num_t gi = 0; gi < src->used_gates_per_layer[layer]; gi++) {
            gate_t g_copy = src->sequence[layer][gi];
            add_gate(dst, &g_copy);
        }
    }

    return dst;
}

// Cancel inverse gate pairs (X-X, H-H on same qubit)
// Returns count of gates removed
static int apply_cancel_inverse(circuit_t *circ) {
    if (circ == NULL || circ->used == 0)
        return 0;

    int removed = 0;

    // For each qubit, scan for consecutive inverse pairs
    for (int qubit = 0; qubit <= circ->used_qubits; qubit++) {
        // Track last gate on this qubit
        layer_t last_layer = 0;
        gate_t *last_gate = NULL;

        for (num_t layer = 0; layer < circ->used_layer; layer++) {
            int gate_idx = circ->gate_index_of_layer_and_qubits[layer][qubit];
            if (gate_idx < 0)
                continue;

            gate_t *g = &circ->sequence[layer][gate_idx];

            // Only check single-qubit gates
            if (g->NumControls > 0) {
                last_gate = g;
                last_layer = layer;
                continue;
            }

            // Check if this gate is inverse of last gate
            if (last_gate != NULL && last_gate->NumControls == 0) {
                if (gates_are_inverse(last_gate, g)) {
                    // These cancel - mark for removal by setting gate type to invalid
                    // (Full removal would require layer restructuring - defer)
                    // For now, we rely on add_gate's merge behavior during copy
                    removed += 2;
                }
            }

            last_gate = g;
            last_layer = layer;
        }
    }

    return removed;
}

// Merge consecutive same-type gates (placeholder for phase rotation merging)
static int apply_merge(circuit_t *circ) {
    // Future: merge consecutive P gates by adding angles
    // For now, return 0 (no merging implemented beyond inverse cancellation)
    return 0;
}

circuit_t *circuit_optimize(circuit_t *circ) {
    if (circ == NULL)
        return NULL;

    // Copy circuit - add_gate already handles inverse cancellation
    // So copying rebuilds with optimization applied
    circuit_t *opt = copy_circuit(circ);

    return opt;
}

circuit_t *circuit_optimize_pass(circuit_t *circ, opt_pass_t pass) {
    if (circ == NULL)
        return NULL;

    // For now, all passes go through copy which applies add_gate's
    // built-in inverse cancellation
    switch (pass) {
    case OPT_PASS_CANCEL_INVERSE:
    case OPT_PASS_MERGE:
        return copy_circuit(circ);
    default:
        return copy_circuit(circ);
    }
}

int circuit_can_optimize(circuit_t *circ) {
    if (circ == NULL || circ->used == 0)
        return 0;

    // Simple heuristic: check if any optimization possible
    // For now, always return 1 if circuit has gates
    // (Real check would scan for cancellable pairs)
    return circ->used > 0 ? 1 : 0;
}
