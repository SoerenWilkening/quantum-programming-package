//
// Created by Sören Wilkening on 09.11.24.
//

#include "IntegerComparison.h"


sequence_t *QQ_equal() {
    sequence_t *eq = malloc(sizeof(sequence_t));

    return eq;
}

sequence_t *CQ_equal() {
    // the ancilla count starts at 2 * INTEGERSIZE
    int ancilla = 2 * INTEGERSIZE; // reference

    sequence_t *seq = malloc(sizeof(sequence_t));

	int factor = INTEGERSIZE;

    int *bin = two_complement(*(stack.R0), INTEGERSIZE);
    int Zeros = 0;
    for (int i = 0; i < INTEGERSIZE; ++i) Zeros += (1 - bin[i]);

    seq->used_layer = 0;
    seq->num_layer = 1;
    memset(seq->gates_per_layer, 0, ceil(log2(Zeros + 1)) * sizeof(num_t));

    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            x(g, factor + i);
        }
    }

    int ctrls[2 * Zeros];
    int index = 0;
    memset(ctrls, 0, 2 * Zeros * sizeof(int));
    seq->used_layer++;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[1][seq->gates_per_layer[1]++];
            cx(g, ancilla + index, factor + i);

            ctrls[index] = ancilla + index;
            ctrls[Zeros + index] = ancilla + Zeros + index;
            index++;
        }
    }
    seq->used_layer++;
    int Z = Zeros / 2;
    int Z1 = Zeros / 2;
    for (int i = 0; i < Zeros - 2; ++i) {
        layer_t layer = seq->used_layer;
        gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
        ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
        if (i == Z - 1){
            seq->used_layer++;
            Z1 /= 2;
            Z += Z1;
        }
    }

    ccx(&seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++], INTEGERSIZE - 1, ctrls[2 * Zeros - 4], ctrls[2 * Zeros - 3]);
    seq->used_layer++;


    for (int i = Zeros - 3; i >= 0; --i) {
        layer_t layer = seq->used_layer;
        gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
        ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
        if (i == Z - 1){
            seq->used_layer++;
            Z1 *= 2;
            Z -= Z1;
        }
    }
    seq->used_layer++;

    index = 0;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            cx(g, ancilla + index, factor + i);

            ctrls[index] = ancilla + index;
            ctrls[Zeros + index] = ancilla + Zeros + index;
            index++;
        }
    }
    seq->used_layer++;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            x(g, factor + i);
        }
    }
    seq->used_layer++;

    return seq;
}

sequence_t *cCQ_equal() {
	// the ancilla count starts at 2 * INTEGERSIZE
	int ancilla = 3 * INTEGERSIZE; // reference

	sequence_t *seq = malloc(sizeof(sequence_t));

	int factor = INTEGERSIZE;

	int *bin = two_complement(*(stack.R0), INTEGERSIZE);
	int Zeros = 0;
	for (int i = 0; i < INTEGERSIZE; ++i) Zeros += (1 - bin[i]);

	seq->used_layer = 0;
	seq->num_layer = 1;
	memset(seq->gates_per_layer, 0, ceil(log2(Zeros + 1) + 2) * sizeof(num_t));

	for (int i = 0; i < INTEGERSIZE; ++i) {
		if (bin[i] == 0) {
			gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
			x(g, factor + i);
		}
	}

	int ctrls[2 * Zeros + 2];
	int index = 0;
	memset(ctrls, 0, 2 * (Zeros + 1) * sizeof(int));
	seq->used_layer++;
	for (int i = 0; i < INTEGERSIZE; ++i) {
		if (bin[i] == 0) {
			gate_t *g = &seq->seq[1][seq->gates_per_layer[1]++];
			cx(g, ancilla + index, factor + i);

			ctrls[index] = ancilla + index;
			ctrls[Zeros + index] = ancilla + Zeros + index;
			index++;
		}
	}
	seq->used_layer++;
	int Z = Zeros / 2;
	int Z1 = Zeros / 2;
	for (int i = 0; i < Zeros - 1; ++i) {
		layer_t layer = seq->used_layer;
		gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
		ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
		if (i == Z - 1){
			seq->used_layer++;
			Z1 /= 2;
			Z += Z1;
		}
	}

	ccx(&seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++], INTEGERSIZE - 1, 3 * INTEGERSIZE - 1, ctrls[2 * Zeros - 2]);
	seq->used_layer++;


	for (int i = Zeros - 2; i >= 0; --i) {
		layer_t layer = seq->used_layer;
		gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
		ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
		if (i == Z - 1){
			seq->used_layer++;
			Z1 *= 2;
			Z -= Z1;
		}
	}
	seq->used_layer++;

	index = 0;
	for (int i = 0; i < INTEGERSIZE; ++i) {
		if (bin[i] == 0) {
			gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
			cx(g, ancilla + index, factor + i);

			ctrls[index] = ancilla + index;
			ctrls[Zeros + index] = ancilla + Zeros + index;
			index++;
		}
	}
	seq->used_layer++;
	for (int i = 0; i < INTEGERSIZE; ++i) {
		if (bin[i] == 0) {
			gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
			x(g, factor + i);
		}
	}
	seq->used_layer++;

	return seq;
}

sequence_t *CC_equal() {
    *((int *) stack.Q0) = *((int *) stack.Q1) == *((int *) stack.Q2);
    return NULL;
}