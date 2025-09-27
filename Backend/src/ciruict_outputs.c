//
// Created by Sören Wilkening on 27.09.25.
//

#include "QPU.h"



// Printing functionality

bool value_in_array(const qubit_t *array, num_t num_values, qubit_t value) {
    if (array == NULL) return false;
    for (int i = 0; i < num_values; ++i) if (array[i] == value) return true;
    return false;
}

void print_circuit(circuit_t *circ) {
    printf("Number of gates =  %zu\n", circ->used);
    printf("Number of layers =  %u\n", circ->used_layer);
    printf("Number of qubits = %d\n\n", circ->used_qubits + 1);
    
    if (circ->used > 2000) return;
    // 3, 8
    int width[circ->used];
    int counter = 0;
    for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {
        for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index]; ++gate_index) {
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
                for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index]; ++gate_index) {
                    int skip_dash = 0;
                    qubit_t *ctrl = circ->sequence[layer_index][gate_index].Control;
                    if (circ->sequence[layer_index][gate_index].NumControls > 2)
                        ctrl = circ->sequence[layer_index][gate_index].large_control;
                    
                    if (value_in_array(ctrl, circ->sequence[layer_index][gate_index].NumControls, qubit)) {
//                        printf("\u25CF");
                        printf("@");
                    } else if (circ->sequence[layer_index][gate_index].Target == qubit) {
                        switch (circ->sequence[layer_index][gate_index].Gate) {
                            case P: printf("P%4.1f", circ->sequence[layer_index][gate_index].GateValue);
                                print_dash(1);
                                skip_dash = 1;
                                break;
                            case X: printf("X");
                                break;
                            case Y: printf("Y");
                                break;
                            case Z: printf("Z");
                                break;
                            case H: printf("H");
                                break;
                            case M: printf("M");
                                break;
                            case R: break;
                            case Rx: break;
                            case Ry: break;
                            case Rz: break;
                        }
                    } else if (qubit > min_qubit(&circ->sequence[layer_index][gate_index]) &&
                        qubit < max_qubit(&circ->sequence[layer_index][gate_index])) {
                        printf("\xE2\x94\x82");
//						printf("|");
                    } else print_dash(1);
                    if (width[counter] == 3) print_dash(1);
                    else if (skip_dash == 0) print_dash(5);
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


void circuit_to_opanqasm(circuit_t *circ, char *path) {
    char p[512];
    sprintf(p, "%s/circuit.qasm", path);
    FILE *oq_file = fopen(p, "w");
    fprintf(oq_file, "// Version declaration\n"
                     "OPENQASM 3.0;\n\n"
                     "// Include standard Library\n"
                     "include \"stdgates.inc\";\n\n"
                     "// Initialize Registers\n"
                     "qubit[%d] q;\n\n"
                     "// The quantum Circuit\n", circ->used_qubits + 1);
    
    for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {
        for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index]; ++gate_index) {
            gate_t g = circ->sequence[layer_index][gate_index];
            for (int i = 0; i < g.NumControls; i++)
                fprintf(oq_file, "c");
            switch (g.Gate) {
                case P: fprintf(oq_file, "p(%.20f) ", g.GateValue);
                    break;
                case X: fprintf(oq_file, "x ");
                    break;
                case H: fprintf(oq_file, "h ");
                    break;
                case Z: fprintf(oq_file, "z ");
                    break;
                case M: fprintf(oq_file, "m ");
                    break;
                case Y:break;
                case R:break;
                case Rx:break;
                case Ry:break;
                case Rz:break;
            }
            for (int i = 0; i < g.NumControls; i++)
                fprintf(oq_file, "q[%d],", g.Control[i]);
            fprintf(oq_file, "q[%d];\n", g.Target);
        }
    }
}