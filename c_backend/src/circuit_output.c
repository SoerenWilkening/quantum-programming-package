//
// circuit_output.c - Circuit visualization and export implementation
// Dependencies: circuit_output.h, QPU.h (for circuit_t definition), gate.h
//

#include "circuit_output.h"
#include "QPU.h"
#include "gate.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Printing functionality

int max(int *arr, int n) {
    int mi = 0;
    for (int i = 0; i < n; ++i) {
        if (mi < arr[i])
            mi = arr[i];
    }
    return mi;
}

bool value_in_array(const qubit_t *array, num_t num_values, qubit_t value) {
    if (array == NULL)
        return false;
    for (int i = 0; i < num_values; ++i)
        if (array[i] == value)
            return true;
    return false;
}

void print_circuit(circuit_t *circ) {
    printf("Number of gates =  %zu\n", circ->used);
    printf("Number of layers =  %u\n", circ->used_layer);
    printf("Number of qubits = %d\n\n", circ->used_qubits + 1);

    if (circ->used > 2000)
        return;
    // 3, 8

    // precompute, how wide is a layer
    //    int layer_width[circ->used_layer];
    //    int max_gates = max((int * ) circ->used_gates_per_layer, circ->used_layer);
    //
    //    int min_layer_in_layer[circ->used_qubits + 1][max_gates + 1];
    //    memset(min_layer_in_layer, 0, (circ->used_qubits + 1) * max_gates * sizeof(int));
    //
    //    for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {
    //
    //        for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index];
    //        ++gate_index) {
    ////            printf("%d %d %d\n", layer_index,
    /// min_qubit(&circ->sequence[layer_index][gate_index]),
    /// max_qubit(&circ->sequence[layer_index][gate_index]));
    //            int val = 2;
    //            switch (circ->sequence[layer_index][gate_index].Gate) {
    //                case P:
    //                    val = 6;
    //                    break;
    //            }
    //            for (int i = min_qubit(&circ->sequence[layer_index][gate_index]);
    //                 i < max_qubit(&circ->sequence[layer_index][gate_index]) + 1; ++i) {
    //                if (gate_index > 0)
    //                    min_layer_in_layer[i][gate_index] += min_layer_in_layer[i][gate_index - 1]
    //                    + val;
    //                else
    //                    min_layer_in_layer[i][gate_index] += val;
    //            }
    ////            for (int i = 0; i < circ->used_qubits + 1; ++i) {
    ////                printf("%d ", min_layer_in_layer[i]);
    ////            }
    ////            printf("\n");
    //        }
    ////        for (int i = 0; i < circ->used_qubits + 1; ++i) {
    ////                printf("%d ", min_layer_in_layer[i]);
    ////            }
    ////        printf("| %d \n", max(min_layer_in_layer, circ->used_qubits + 1));
    ////        layer_width[layer_index] = max(min_layer_in_layer, circ->used_qubits + 1);
    //    }
    //    for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {
    //        printf("%d| ", layer_index);
    //        for (int i = 0; i < circ->used_gates_per_layer[layer_index]; ++i) {
    //            printf("%d ", min_layer_in_layer[layer_index][i]);
    //        }
    //        printf("\n");
    //    }

    int width[circ->used];
    int counter = 0;
    for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {
        for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index];
             ++gate_index) {
            if (circ->sequence[layer_index][gate_index].Gate == P) {
                width[counter++] = 8;
            } else {
                width[counter++] = 3;
            }
        }
    }

    for (int qubit = 0; qubit < circ->used_qubits + 1; ++qubit) {
        if (circ->used_occupation_indices_per_qubit[qubit] != 0) {
            printf("%3d ", qubit);
            counter = 0;
            for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {

                // use to print beneath each other if possible
                int min_layer_in_layer[circ->used_qubits + 1];
                memset(min_layer_in_layer, 0, (circ->used_qubits + 1) * sizeof(int));

                for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index];
                     ++gate_index) {
                    int skip_dash = 0;
                    qubit_t *ctrl = circ->sequence[layer_index][gate_index].Control;
                    if (circ->sequence[layer_index][gate_index].NumControls > 2)
                        ctrl = circ->sequence[layer_index][gate_index].large_control;

                    if (value_in_array(ctrl, circ->sequence[layer_index][gate_index].NumControls,
                                       qubit)) {
                        //                        printf("\u25CF");
                        printf("@");
                    } else if (circ->sequence[layer_index][gate_index].Target == qubit) {
                        switch (circ->sequence[layer_index][gate_index].Gate) {
                        case P:
                            printf("P%4.1f", circ->sequence[layer_index][gate_index].GateValue);
                            print_dash(1);
                            skip_dash = 1;
                            break;
                        case X:
                            printf("X");
                            break;
                        case Y:
                            printf("Y");
                            break;
                        case Z:
                            printf("Z");
                            break;
                        case H:
                            printf("H");
                            break;
                        case M:
                            printf("M");
                            break;
                        case R:
                            break;
                        case Rx:
                            break;
                        case Ry:
                            break;
                        case Rz:
                            break;
                        }
                    } else if (qubit > min_qubit(&circ->sequence[layer_index][gate_index]) &&
                               qubit < max_qubit(&circ->sequence[layer_index][gate_index])) {
                        printf("\xE2\x94\x82");
                        //						printf("|");
                    } else
                        print_dash(1);
                    if (width[counter] == 3)
                        print_dash(1);
                    else if (skip_dash == 0)
                        print_dash(5);
                    counter++;
                }

                //				printf("|");
                printf("\u250A");
            }
            printf("\n");
            //            if (qubit % INTEGERSIZE == INTEGERSIZE - 1) printf("\n");
        }
    }
}

void circuit_visualize(circuit_t *circ) {
    if (circ == NULL) {
        printf("Circuit is NULL\n");
        return;
    }

    // Print summary header
    printf("Circuit: %zu gates, %u layers, %d qubits\n\n", circ->used, circ->used_layer,
           circ->used_qubits + 1);

    if (circ->used == 0) {
        printf("(empty circuit)\n");
        return;
    }

    // Limit display for very wide circuits
    int max_display_layers = circ->used_layer > 60 ? 60 : circ->used_layer;
    if (circ->used_layer > 60) {
        printf("(showing first 60 of %u layers)\n\n", circ->used_layer);
    }

    // Print layer number header
    printf("     "); // Space for qubit labels
    for (int layer = 0; layer < max_display_layers; layer++) {
        if (layer % 5 == 0) {
            printf("%-3d", layer);
        } else {
            printf("   ");
        }
    }
    printf("\n");

    // Print each qubit row
    for (int qubit = 0; qubit <= circ->used_qubits; qubit++) {
        if (circ->used_occupation_indices_per_qubit[qubit] == 0) {
            continue; // Skip unused qubits
        }

        printf("q%-3d ", qubit); // Qubit label

        for (int layer = 0; layer < max_display_layers; layer++) {
            // Check if this qubit has a gate in this layer
            int gate_idx = circ->gate_index_of_layer_and_qubits[layer][qubit];

            if (gate_idx >= 0) {
                gate_t *g = &circ->sequence[layer][gate_idx];

                // Check if this qubit is the target or a control
                if (g->Target == qubit) {
                    // Print gate symbol
                    switch (g->Gate) {
                    case X:
                        printf(g->NumControls > 0 ? " + " : " X ");
                        break;
                    case H:
                        printf(" H ");
                        break;
                    case Z:
                        printf(" Z ");
                        break;
                    case Y:
                        printf(" Y ");
                        break;
                    case P:
                        printf(" P ");
                        break;
                    case M:
                        printf(" M ");
                        break;
                    default:
                        printf(" ? ");
                        break;
                    }
                } else {
                    // This is a control qubit
                    printf(" @ ");
                }
            } else {
                // Check if wire passes through (between control and target)
                bool is_between = false;
                for (int gi = 0; gi < circ->used_gates_per_layer[layer]; gi++) {
                    gate_t *g = &circ->sequence[layer][gi];
                    int min_q = min_qubit(g);
                    int max_q = max_qubit(g);
                    if (qubit > min_q && qubit < max_q) {
                        is_between = true;
                        break;
                    }
                }
                if (is_between) {
                    printf(" | "); // Vertical connection
                } else {
                    printf("---"); // Wire continues
                }
            }
        }
        printf("\n");
    }
    printf("\n");
}

void circuit_to_opanqasm(circuit_t *circ, char *path) {
    // Delegate to fixed implementation (ignores return value for backward compat)
    circuit_to_openqasm(circ, path);
}

// ======================================================
// OpenQASM 3.0 String Export Implementation
// ======================================================

// Normalize angle to [0, 2π)
static double normalize_angle(double theta) {
    double result = fmod(theta, 2.0 * M_PI);
    if (result < 0.0) {
        result += 2.0 * M_PI;
    }
    return result;
}

// Get control qubit at index, handling large_control array
static qubit_t _get_control_qubit(gate_t *g, int index) {
    if (g->NumControls > MAXCONTROLS && g->large_control != NULL) {
        return g->large_control[index];
    }
    return g->Control[index];
}

// Count measurement gates in circuit
static int _count_measurements(circuit_t *circ) {
    int count = 0;
    for (int layer = 0; layer < circ->used_layer; layer++) {
        for (int gate_idx = 0; gate_idx < circ->used_gates_per_layer[layer]; gate_idx++) {
            if (circ->sequence[layer][gate_idx].Gate == M) {
                count++;
            }
        }
    }
    return count;
}

// Export a single gate to buffer
// Returns new offset, or (size_t)-1 on buffer overflow
static size_t _export_gate(gate_t *g, char *buffer, size_t buf_size, size_t offset,
                           int *measurement_idx) {
    // Safety check: ensure we have at least 200 bytes left
    if (offset > buf_size - 200) {
        return (size_t)-1;
    }

    int written = 0;

    if (g->NumControls == 0) {
        // No controls - simple gate
        switch (g->Gate) {
        case X:
            written = sprintf(buffer + offset, "x q[%d];\n", g->Target);
            break;
        case Y:
            written = sprintf(buffer + offset, "y q[%d];\n", g->Target);
            break;
        case Z:
            written = sprintf(buffer + offset, "z q[%d];\n", g->Target);
            break;
        case H:
            written = sprintf(buffer + offset, "h q[%d];\n", g->Target);
            break;
        case P:
            written = sprintf(buffer + offset, "p(%.17g) q[%d];\n", normalize_angle(g->GateValue),
                              g->Target);
            break;
        case Rx:
            written = sprintf(buffer + offset, "rx(%.17g) q[%d];\n", normalize_angle(g->GateValue),
                              g->Target);
            break;
        case Ry:
            written = sprintf(buffer + offset, "ry(%.17g) q[%d];\n", normalize_angle(g->GateValue),
                              g->Target);
            break;
        case Rz:
            written = sprintf(buffer + offset, "rz(%.17g) q[%d];\n", normalize_angle(g->GateValue),
                              g->Target);
            break;
        case M:
            written =
                sprintf(buffer + offset, "c[%d] = measure q[%d];\n", *measurement_idx, g->Target);
            (*measurement_idx)++;
            break;
        case R:
            written = sprintf(buffer + offset, "reset q[%d];\n", g->Target);
            break;
        default:
            written = sprintf(buffer + offset, "// unknown gate %d\n", g->Gate);
            break;
        }
    } else if (g->NumControls == 1) {
        // Single control - use c-prefix
        qubit_t ctrl = _get_control_qubit(g, 0);
        switch (g->Gate) {
        case X:
            written = sprintf(buffer + offset, "cx q[%d], q[%d];\n", ctrl, g->Target);
            break;
        case Y:
            written = sprintf(buffer + offset, "cy q[%d], q[%d];\n", ctrl, g->Target);
            break;
        case Z:
            written = sprintf(buffer + offset, "cz q[%d], q[%d];\n", ctrl, g->Target);
            break;
        case H:
            written = sprintf(buffer + offset, "ch q[%d], q[%d];\n", ctrl, g->Target);
            break;
        case P:
            written = sprintf(buffer + offset, "cp(%.17g) q[%d], q[%d];\n",
                              normalize_angle(g->GateValue), ctrl, g->Target);
            break;
        case Rx:
            written = sprintf(buffer + offset, "crx(%.17g) q[%d], q[%d];\n",
                              normalize_angle(g->GateValue), ctrl, g->Target);
            break;
        case Ry:
            written = sprintf(buffer + offset, "cry(%.17g) q[%d], q[%d];\n",
                              normalize_angle(g->GateValue), ctrl, g->Target);
            break;
        case Rz:
            written = sprintf(buffer + offset, "crz(%.17g) q[%d], q[%d];\n",
                              normalize_angle(g->GateValue), ctrl, g->Target);
            break;
        case M:
        case R:
            // M and R are not meaningfully controlled - skip
            written = sprintf(buffer + offset, "// skipped controlled %s\n",
                              g->Gate == M ? "measure" : "reset");
            break;
        default:
            written = sprintf(buffer + offset, "// unknown controlled gate %d\n", g->Gate);
            break;
        }
    } else if (g->NumControls == 2) {
        // Two controls - use cc-prefix or special syntax
        qubit_t ctrl0 = _get_control_qubit(g, 0);
        qubit_t ctrl1 = _get_control_qubit(g, 1);

        if (g->Gate == X) {
            // Toffoli gate has dedicated ccx syntax
            written =
                sprintf(buffer + offset, "ccx q[%d], q[%d], q[%d];\n", ctrl0, ctrl1, g->Target);
        } else {
            // Other 2-control gates use ctrl(2) @ syntax
            const char *gate_name = "";
            char param_str[64] = "";
            switch (g->Gate) {
            case Y:
                gate_name = "y";
                break;
            case Z:
                gate_name = "z";
                break;
            case H:
                gate_name = "h";
                break;
            case P:
                gate_name = "p";
                sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
                break;
            case Rx:
                gate_name = "rx";
                sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
                break;
            case Ry:
                gate_name = "ry";
                sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
                break;
            case Rz:
                gate_name = "rz";
                sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
                break;
            default:
                gate_name = "unknown";
                break;
            }
            written = sprintf(buffer + offset, "ctrl(2) @ %s%s q[%d], q[%d], q[%d];\n", gate_name,
                              param_str, ctrl0, ctrl1, g->Target);
        }
    } else {
        // More than 2 controls - use ctrl(n) @ syntax
        const char *gate_name = "";
        char param_str[64] = "";

        switch (g->Gate) {
        case X:
            gate_name = "x";
            break;
        case Y:
            gate_name = "y";
            break;
        case Z:
            gate_name = "z";
            break;
        case H:
            gate_name = "h";
            break;
        case P:
            gate_name = "p";
            sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
            break;
        case Rx:
            gate_name = "rx";
            sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
            break;
        case Ry:
            gate_name = "ry";
            sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
            break;
        case Rz:
            gate_name = "rz";
            sprintf(param_str, "(%.17g)", normalize_angle(g->GateValue));
            break;
        default:
            gate_name = "unknown";
            break;
        }

        written =
            sprintf(buffer + offset, "ctrl(%d) @ %s%s ", g->NumControls, gate_name, param_str);
        offset += written;

        // Write all control qubits
        for (int i = 0; i < g->NumControls; i++) {
            written = sprintf(buffer + offset, "q[%d], ", _get_control_qubit(g, i));
            offset += written;
        }

        // Write target
        written = sprintf(buffer + offset, "q[%d];\n", g->Target);
    }

    return offset + written;
}

// Export circuit to OpenQASM 3.0 string
char *circuit_to_qasm_string(circuit_t *circ) {
    if (circ == NULL) {
        return NULL;
    }

    // Count measurements for classical register declaration
    int num_measurements = _count_measurements(circ);

    // Allocate initial buffer (512 bytes header + 100 bytes per gate estimate)
    size_t buf_size = 512 + (circ->used * 100);
    char *buffer = malloc(buf_size);
    if (buffer == NULL) {
        return NULL;
    }

    size_t offset = 0;

    // Write header
    int written = sprintf(buffer + offset,
                          "OPENQASM 3.0;\n"
                          "include \"stdgates.inc\";\n"
                          "\n"
                          "qubit[%d] q;\n",
                          circ->used_qubits + 1);
    offset += written;

    // Write classical register declaration if there are measurements
    if (num_measurements > 0) {
        written = sprintf(buffer + offset, "bit[%d] c;\n", num_measurements);
        offset += written;
    }

    // Write separator
    written = sprintf(buffer + offset, "\n");
    offset += written;

    // Export all gates
    int measurement_idx = 0;
    for (int layer = 0; layer < circ->used_layer; layer++) {
        for (int gate_idx = 0; gate_idx < circ->used_gates_per_layer[layer]; gate_idx++) {
            gate_t *g = &circ->sequence[layer][gate_idx];

            // Try to export gate
            size_t new_offset = _export_gate(g, buffer, buf_size, offset, &measurement_idx);

            // If buffer overflow, reallocate and retry
            while (new_offset == (size_t)-1) {
                buf_size *= 2;
                char *tmp = realloc(buffer, buf_size);
                if (tmp == NULL) {
                    free(buffer);
                    return NULL;
                }
                buffer = tmp;

                // Retry the same gate
                new_offset = _export_gate(g, buffer, buf_size, offset, &measurement_idx);
            }

            offset = new_offset;
        }
    }

    // Null-terminate
    buffer[offset] = '\0';

    return buffer;
}

// Export circuit to OpenQASM 3.0 file (fixed version)
int circuit_to_openqasm(circuit_t *circ, const char *path) {
    if (circ == NULL || path == NULL) {
        return -1;
    }

    // Get QASM string using the string export function
    char *qasm = circuit_to_qasm_string(circ);
    if (qasm == NULL) {
        return -1;
    }

    // Build file path
    char filepath[512];
    snprintf(filepath, sizeof(filepath), "%s/circuit.qasm", path);

    // Write to file
    FILE *f = fopen(filepath, "w");
    if (f == NULL) {
        free(qasm);
        return -1;
    }

    fputs(qasm, f);
    fclose(f);
    free(qasm);
    return 0;
}