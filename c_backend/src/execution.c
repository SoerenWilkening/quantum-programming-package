//
// Created by Sören Wilkening on 21.11.24.
//
// qubit_mapping() and execute() removed (Phase 11)
// Python layer passes qubit arrays directly to run_instruction().
// Test code in main.c now uses explicit qubit array initialization.
//

#include "execution.h"
#include "validation.h"
#include <assert.h>

// apply the sequences to the desired qubits
// tracking_only: when non-zero, counts gates in circ->gate_count without calling add_gate()
void run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert, circuit_t *circ,
                     int tracking_only) {

    if (res == NULL)
        return;

    // Fast path: count gates without building the circuit
    if (tracking_only) {
        for (int layer_index = 0; layer_index < res->used_layer; ++layer_index) {
            circ->gate_count += res->gates_per_layer[layer_index];
        }
        return;
    }

    int direction = (invert) ? -1 : 1;

    //    printf("%d %d\n", direction, invert);

    for (int layer_index = 0; layer_index < res->used_layer; ++layer_index) {
        layer_t layer = invert * res->used_layer + direction * layer_index - invert;
        for (int gate_index = 0; gate_index < res->gates_per_layer[layer]; ++gate_index) {
            layer_t gate = invert * res->gates_per_layer[layer] + direction * gate_index - invert;
            gate_t g; // Stack allocated -- no malloc, no leak (Phase 61)
            memcpy(&g, &res->seq[layer][gate], sizeof(gate_t));
            g.Target = qubit_array[g.Target];

            // Handle n-controlled gates (Phase 12): controls may be in large_control
            if (g.NumControls > 2 && res->seq[layer][gate].large_control != NULL) {
                // Allocate new large_control array for mapped qubits
                g.large_control = malloc(g.NumControls * sizeof(qubit_t));
                if (g.large_control != NULL) {
                    for (int i = 0; i < (int)g.NumControls; ++i) {
                        g.large_control[i] = qubit_array[res->seq[layer][gate].large_control[i]];
                    }
                    // Also update Control[0] and Control[1] for compatibility
                    g.Control[0] = g.large_control[0];
                    g.Control[1] = g.large_control[1];
                }
            } else {
                // Standard case: up to 2 controls in Control[] array
                for (int i = 0; i < (int)g.NumControls && i < MAXCONTROLS; ++i) {
                    g.Control[i] = qubit_array[g.Control[i]];
                }
            }
            // Invert gate value only for non-self-inverse gates (Phase 65)
            if (invert) {
                switch (g.Gate) {
                case X:
                case Y:
                case Z:
                case H:
                case M:
                    // Self-inverse gates: GateValue unchanged
                    break;
                default:
                    // Phase/rotation gates: negate for inversion
                    g.GateValue = -g.GateValue;
                    break;
                }
            }

            add_gate(circ, &g);
            circ->gate_count++;
            // NOTE: Do NOT free g.large_control here. The circuit takes ownership
            // of the allocated large_control via memcpy in append_gate (Phase 67).
            // free_circuit handles cleanup of all large_control arrays.
        }
    }
}

// Reverse a range of gates from the circuit in LIFO order (Phase 17)
// Used for automatic uncomputation of intermediate quantum values
void reverse_circuit_range(circuit_t *circ, int start_layer, int end_layer) {
    // Debug-mode assertion for NULL circuit
    assert(circ != NULL);

    // Empty range: no-op
    if (start_layer >= end_layer) {
        return;
    }

    // Iterate backwards from end_layer - 1 down to start_layer (LIFO order)
    for (int layer_index = end_layer - 1; layer_index >= start_layer; --layer_index) {
        // Iterate backwards through gates in this layer
        for (int gate_index = circ->used_gates_per_layer[layer_index] - 1; gate_index >= 0;
             --gate_index) {
            gate_t *original_gate = &circ->sequence[layer_index][gate_index];

            // Create a stack-allocated copy with inverted GateValue (Phase 61)
            gate_t g;
            memcpy(&g, original_gate, sizeof(gate_t));

            // Invert the gate value for rotation gates; self-inverse gates keep original value
            // Invert gate value only for non-self-inverse gates (Phase 65)
            switch (g.Gate) {
            case X:
            case Y:
            case Z:
            case H:
            case M:
                // Self-inverse gates: GateValue unchanged
                break;
            default:
                // Phase/rotation gates (P, Rx, Ry, Rz, R): negate for inversion
                g.GateValue = -g.GateValue;
                break;
            }

            // Handle n-controlled gates: allocate new large_control array
            if (g.NumControls > 2 && original_gate->large_control != NULL) {
                g.large_control = malloc(g.NumControls * sizeof(qubit_t));
                if (g.large_control != NULL) {
                    for (int i = 0; i < (int)g.NumControls; ++i) {
                        g.large_control[i] = original_gate->large_control[i];
                    }
                    // Update Control[0] and Control[1] for compatibility
                    g.Control[0] = g.large_control[0];
                    g.Control[1] = g.large_control[1];
                }
            }
            // For gates with <= 2 controls, memcpy already copied Control[] array

            // Append inverted gate to circuit
            add_gate(circ, &g);
            // NOTE: Do NOT free g.large_control here. The circuit takes ownership
            // of the allocated large_control via memcpy in append_gate (Phase 67).
            // free_circuit handles cleanup of all large_control arrays.
        }
    }
}

// Phase 84: Validated entry points for Cython boundary.
// These wrap the originals with NULL checks and return error codes.
// Internal C-to-C calls continue to use the originals directly.

int validated_run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert,
                              circuit_t *circ, int tracking_only) {
    if (circ == NULL)
        return QV_NULL_CIRC;
    // NULL res is already handled (no-op) by run_instruction, so no error
    run_instruction(res, qubit_array, invert, circ, tracking_only);
    return QV_OK;
}

int validated_reverse_circuit_range(circuit_t *circ, int start_layer, int end_layer) {
    if (circ == NULL)
        return QV_NULL_CIRC;
    reverse_circuit_range(circ, start_layer, end_layer);
    return QV_OK;
}
