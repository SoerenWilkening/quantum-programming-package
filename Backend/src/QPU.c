//
// Created by Sören Wilkening on 27.10.24.
//
#include "QPU.h"

circuit_t *init_circuit() {
	circuit_t *circ = malloc(sizeof(circuit_t));
	circ->used = 0;
	circ->used_layer = 0;
	circ->toff_decomp = DONTDECOMPOSETOFFOLI;

	// allocate sequence structures
	circ->allocated_layer = LAYERBLOCK;
	circ->used_gates_per_layer = calloc(LAYERBLOCK, sizeof(num_t));
	circ->allocated_gates_per_layer = malloc(LAYERBLOCK * sizeof(num_t));
	for (int i = 0; i < LAYERBLOCK; ++i) {
		circ->allocated_gates_per_layer[i] = GATESPERLAYERBLOCK;
	}
	circ->sequence = malloc(LAYERBLOCK * sizeof(gate_t *));
	for (int i = 0; i < LAYERBLOCK; ++i) {
		circ->sequence[i] = malloc(GATESPERLAYERBLOCK * sizeof(gate_t));
	}

	// allocate layer informations
	circ->used_layer_per_qubit = calloc(QUBITBLOCK, sizeof(num_t));
	circ->allocated_layer_per_qubit = malloc(LAYERBLOCK * sizeof(num_t));

	circ->layer_on_qubit = malloc(QUBITBLOCK * sizeof(layer_t *));
	for (int i = 0; i < QUBITBLOCK; ++i) {
		circ->layer_on_qubit[i] = malloc(LAYERQUBITBLOCK * sizeof(layer_t));
		circ->allocated_layer_per_qubit[i] = LAYERQUBITBLOCK;
	}
	memset(circ->used_gates_per_layer, 0, LAYERBLOCK * sizeof(num_t));

	circ->allocated_qubits = QUBITBLOCK;
	circ->used_qubits = 0;

	// initialize all the qubit indices and the ancilla register
	for (int i = 0; i < MAXQUBITS; ++i) {
		circ->qubit_indices[i] = i;
	}
	circ->used_qubit_indices = 0;
	circ->ancilla = &circ->qubit_indices[0];

	return circ;
}


bool ValueInArray(const qubit_t *Array, num_t NumValues, qubit_t Value) {
	if (Array == NULL) return false;
	for (int i = 0; i < NumValues; ++i) if (Array[i] == Value) return true;
	return false;
}

void print_circuit(circuit_t *circ) {
	printf("Number of gates =  %zu\n", circ->used);
	printf("Number of layers =  %u\n", circ->used_layer);
	printf("Number of qubits = %d\n\n", circ->used_qubits);

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
		if (circ->used_layer_per_qubit[qubit] != 0) {
			printf("%3d ", qubit);
			counter = 0;
			for (int layer_index = 0; layer_index < circ->used_layer; ++layer_index) {
				for (int gate_index = 0; gate_index < circ->used_gates_per_layer[layer_index]; ++gate_index) {
					int skip_dash = 0;
					qubit_t *ctrl = circ->sequence[layer_index][gate_index].Control;
					if (circ->sequence[layer_index][gate_index].NumControls > 2)
						ctrl = circ->sequence[layer_index][gate_index].large_control;

					if (ValueInArray(ctrl, circ->sequence[layer_index][gate_index].NumControls, qubit)) {
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
							case H:
								printf("H");
								break;
							case Z:
								printf("Z");
								break;
							case M:
								printf("M");
								break;
						}
					} else if (qubit > MinQubit(&circ->sequence[layer_index][gate_index]) &&
					           qubit < MaxQubit(&circ->sequence[layer_index][gate_index])) {
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

void IncreaseQubitRegister(circuit_t *circ, gate_t *g) {
	qubit_t *ctrl = g->Control;
//    if (g->NumControls > 2) ctrl = g->large_control;
	int max = MaxQubit(g);
	if (max >= circ->used_qubits) circ->used_qubits = max;
	max++;
	if (max <= circ->allocated_qubits) return;


	int factor = ceil((double) max / QUBITBLOCK);

	// increase the register storing how many layers are assigned to qubit
	circ->used_layer_per_qubit = realloc(circ->used_layer_per_qubit, factor * QUBITBLOCK * sizeof(num_t));
	memset(circ->used_layer_per_qubit + circ->allocated_qubits, 0,
	       (factor * QUBITBLOCK - circ->allocated_qubits) * sizeof(num_t));

	// increase register storing which layers occupy qubits
	circ->layer_on_qubit = realloc(circ->layer_on_qubit, factor * QUBITBLOCK * sizeof(layer_t *));
	circ->allocated_layer_per_qubit = realloc(circ->allocated_layer_per_qubit, factor * QUBITBLOCK * sizeof(layer_t *));
	for (int i = circ->allocated_qubits; i < factor * QUBITBLOCK; ++i) {
		circ->layer_on_qubit[i] = malloc(LAYERQUBITBLOCK * sizeof(layer_t));
		circ->allocated_layer_per_qubit[i] = LAYERQUBITBLOCK;
	}

	circ->allocated_qubits = factor * QUBITBLOCK;

}

layer_t MinimumLayer(circuit_t *circ, gate_t *g) {
	qubit_t *ctrl = g->Control;
//    if (g->NumControls > 2) ctrl = g->large_control;
	// Determine the minimal possible layer where gate can be applied
	layer_t MinPossibleLayer = 0;
	for (int j = 0; j < g->NumControls; ++j) {
		layer_t pos = ctrl[j];
		layer_t l_pos = circ->used_layer_per_qubit[pos];

		if (l_pos > 0 && circ->layer_on_qubit[pos][l_pos - 1] > MinPossibleLayer) {
			MinPossibleLayer = circ->layer_on_qubit[pos][l_pos - 1];
		}
	}
	layer_t pos = g->Target;
	layer_t l_pos = circ->used_layer_per_qubit[pos];
	if (l_pos > 0 && circ->layer_on_qubit[pos][l_pos - 1] > MinPossibleLayer)
		MinPossibleLayer = circ->layer_on_qubit[pos][l_pos - 1];

	return MinPossibleLayer;
}

int merge_gates(circuit_t *circ, gate_t *g, layer_t MinPossibleLayer) {
	if (MinPossibleLayer == 0) return true;
	qubit_t *ctrl = g->Control;
	for (int i = circ->used_gates_per_layer[MinPossibleLayer - 1] - 1; i >= 0; --i) {
		int comp = is_inverse(g, &circ->sequence[MinPossibleLayer - 1][i]);
		if (comp) {
			for (int k = 0; k < g->NumControls; ++k) {
				circ->used_layer_per_qubit[ctrl[k]]--;
			}
			circ->layer_on_qubit[g->Target][circ->used_layer_per_qubit[g->Target] - 1] = 0;
			circ->used_layer_per_qubit[g->Target]--;
			// swap gate to the end of layer to be reused
			for (int k = i; k < circ->used_gates_per_layer[MinPossibleLayer - 1]; ++k)
				circ->sequence[MinPossibleLayer - 1][k] = circ->sequence[MinPossibleLayer - 1][k + 1];
			// layer contains less gates
			circ->used_gates_per_layer[MinPossibleLayer - 1]--;
			circ->used--;

			// remove layer, if last gate was removed
			if (circ->used_gates_per_layer[MinPossibleLayer - 1] == 0) {
				for (int j = MinPossibleLayer - 1; j < circ->used_layer - 1; ++j) {
					*circ->sequence[j] = *circ->sequence[j + 1];
				}
				circ->used_layer--;
			}
			return false;
		}
	}
	return true;
}

void apply_layer(circuit_t *circ, gate_t *g, layer_t MinPossibleLayer) {
	for (int j = 0; j < g->NumControls; ++j) {
		qubit_t loc = g->Control[j];
		if (circ->used_layer_per_qubit[loc] == circ->allocated_layer_per_qubit[loc]) {
			circ->layer_on_qubit[loc] = realloc(
					circ->layer_on_qubit[loc],
					(circ->allocated_layer_per_qubit[loc] + LAYERQUBITBLOCK) * sizeof(layer_t)
			);
			circ->allocated_layer_per_qubit[loc] += LAYERQUBITBLOCK;
		}
		circ->layer_on_qubit[loc][circ->used_layer_per_qubit[loc]++] = MinPossibleLayer + 1;
	}
	qubit_t loc = g->Target;
	if (circ->used_layer_per_qubit[loc] == circ->allocated_layer_per_qubit[loc]) {
		circ->layer_on_qubit[loc] = realloc(
				circ->layer_on_qubit[loc],
				(circ->allocated_layer_per_qubit[loc] + LAYERQUBITBLOCK) * sizeof(layer_t)
		);
		circ->allocated_layer_per_qubit[loc] += LAYERQUBITBLOCK;
	}
	circ->layer_on_qubit[loc][circ->used_layer_per_qubit[loc]++] = MinPossibleLayer + 1;
	circ->used_gates_per_layer[MinPossibleLayer]++; // layer contains more gates
	if (MinPossibleLayer + 1 > circ->used_layer) circ->used_layer = MinPossibleLayer + 1;
}

int AppendGate(circuit_t *circ, gate_t *g, layer_t MinPossibleLayer) {
//	qubit_t *ctrl = g->Control;
	int added = merge_gates(circ, g, MinPossibleLayer);
//	int added = true;
	// check every gate within the previous layer to check, if gates will eradicate themselves
	if (!added) return added;

	// gate will be added to MinPossibleLayer
	// assign layer
	layer_t pos = circ->used_gates_per_layer[MinPossibleLayer];
	increase_gates_per_layer(circ, MinPossibleLayer, pos);

	// increase the number of storable gates on MinPossibleLayer if needed
	if (pos >= circ->allocated_gates_per_layer[MinPossibleLayer]) {
		circ->sequence[MinPossibleLayer] = realloc(
				circ->sequence[MinPossibleLayer],
				(circ->allocated_gates_per_layer[MinPossibleLayer] + GATESPERLAYERBLOCK) * sizeof(gate_t)
		);
		circ->allocated_gates_per_layer[MinPossibleLayer] += GATESPERLAYERBLOCK;
	}

	gate_t *store = &circ->sequence[MinPossibleLayer][pos];
	memcpy(store, g, sizeof(gate_t));
//    copy_basis_gate(store, g, NOTFREED);

	apply_layer(circ, g, MinPossibleLayer);

	circ->used++;

	return added;
}

void increase_sequence_layers(circuit_t *circ, layer_t MinPossibleLayer) {
	// include sequence increase
	if (MinPossibleLayer < circ->allocated_layer) return;

	num_t new = circ->allocated_layer + LAYERBLOCK;
	circ->used_gates_per_layer = realloc(circ->used_gates_per_layer, new * sizeof(num_t));
	memset(&circ->used_gates_per_layer[circ->allocated_layer], 0, LAYERBLOCK * sizeof(num_t));
	circ->allocated_gates_per_layer = realloc(circ->allocated_gates_per_layer, new * sizeof(num_t));
	for (int i = circ->allocated_layer; i < new; ++i) {
		circ->allocated_gates_per_layer[i] = GATESPERLAYERBLOCK;
	}

	// increase sequence layers
	circ->sequence = realloc(circ->sequence, new * sizeof(gate_t *));
	for (int i = circ->allocated_layer; i < new; ++i) {
		circ->sequence[i] = malloc(GATESPERLAYERBLOCK * sizeof(gate_t));
	}

	circ->allocated_layer = new;
}

void increase_gates_per_layer(circuit_t *circ, layer_t layer, layer_t pos) {
	if (pos < circ->allocated_gates_per_layer[layer]) return;

	num_t new_size = circ->allocated_gates_per_layer[layer] + GATESPERLAYERBLOCK;
	circ->sequence[layer] = realloc(circ->sequence[layer], new_size * sizeof(gate_t));
	circ->allocated_gates_per_layer[layer] = new_size;
}

void add_gate(circuit_t *circ, gate_t *g) {
//    num_t number_gates = g->NumBasisGates;
	num_t number_gates = 1;
	for (int i = 0; i < number_gates; ++i) {
		// Before adding gate, check if multicontrolled gate needs to be decomposed
		// Currently: Toffoli (CCX) and every single control single qubit gate (CU) is allowed
		// Determine the minimal possible layer where gate can be applied
		IncreaseQubitRegister(circ, &g[i]);
		layer_t MinPossibleLayer = MinimumLayer(circ, &g[i]);
//            layer_t MinPossibleLayer = circ->used_layer;
		increase_sequence_layers(circ, MinPossibleLayer);
		AppendGate(circ, &g[i], MinPossibleLayer);
//        }
	}
//    free(g);
}


void CircuitToOPANQASM(circuit_t *circuit, char *path) {
	char p[512];
	sprintf(p, "%s/circuit.qasm", path);
	FILE *OQFile = fopen(p, "w");
	fprintf(OQFile, "// Version declaration\n"
	                "OPENQASM 3.0;\n\n"
	                "// Include standard Library\n"
	                "include \"stdgates.inc\";\n\n"
	                "// Initialize Registers\n"
	                "qubit[%d] q;\n\n"
	                "// The quantum Circuit\n", circuit->used_qubits + 1);

	for (int layer_index = 0; layer_index < circuit->used_layer; ++layer_index) {
		for (int gate_index = 0; gate_index < circuit->used_gates_per_layer[layer_index]; ++gate_index) {
			gate_t g = circuit->sequence[layer_index][gate_index];
			for (int i = 0; i < g.NumControls; i++)
				fprintf(OQFile, "c");
			switch (g.Gate) {
				case P:
					fprintf(OQFile, "p(%.20f) ", g.GateValue);
					break;
				case X:
					fprintf(OQFile, "x ");
					break;
				case H:
					fprintf(OQFile, "h ");
					break;
				case Z:
					fprintf(OQFile, "z ");
					break;
				case M:
					fprintf(OQFile, "m ");
					break;
			}
			for (int i = 0; i < g.NumControls; i++)
				fprintf(OQFile, "q[%d],", g.Control[i]);
			fprintf(OQFile, "q[%d];\n", g.Target);
		}
	}
}