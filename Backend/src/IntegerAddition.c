//
// Created by Sören Wilkening on 05.11.24.
//

#include "Integer.h"

sequence_t *CC_add() {
	*(QPU_state->R0) += *(QPU_state->R1);
	return NULL;
}
sequence_t *CQ_add() {
	// Compute rotation angles
	int NonZeroCount = 0;
	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	// Compute rotations for addition
	double *rotations = calloc(INTEGERSIZE, sizeof(double));
	for (int i = 0; i < INTEGERSIZE; ++i) {
		for (int j = 0; j < INTEGERSIZE - i; ++j) {
			rotations[j + i] += bin[INTEGERSIZE - i - 1] * 2 * M_PI / (pow(2, j + 1));
		}
		if (rotations[i] != 0) NonZeroCount++;
	}
	free(bin);
	int start_layer = INTEGERSIZE;

	if (precompiled_CQ_add != NULL) {
		sequence_t *add = precompiled_CQ_add;

		for (int i = 0; i < INTEGERSIZE; ++i) {
			add->seq[start_layer + i][add->gates_per_layer[start_layer + i] - 1].GateValue = rotations[INTEGERSIZE - i - 1];
		}
		free(rotations);
		return add;
	}

	sequence_t *add = malloc(sizeof(sequence_t));
	// allocate exact number of layer and enough gates per layer
	add->used_layer = 0;
	add->num_layer = 4 * INTEGERSIZE - 1;
	memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));
	QFT(add);

	for (int i = 0; i < INTEGERSIZE; ++i) {
		p(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i, rotations[INTEGERSIZE - i - 1]);
	}
	free(rotations);
	add->used_layer++;

	QFT_inverse(add);

	precompiled_CQ_add = add;
	return add;
}
sequence_t *QQ_add() {
	if (precompiled_QQ_add != NULL) return precompiled_QQ_add;

	sequence_t *add = malloc(sizeof(sequence_t));

	// allocate exact number of layer and enough gates per layer
	add->used_layer = 0;
	add->num_layer = 4 * INTEGERSIZE - 2 + INTEGERSIZE;
	memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));
	QFT(add);
	int rounds = 0;
	for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
		for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
			num_t layer = 2 * INTEGERSIZE + i + 2 * rounds - 1;
			num_t target = INTEGERSIZE - i - 1 - rounds;
			num_t control = INTEGERSIZE + bit;
			double value = 2 * M_PI / (pow(2, i + 1));
			gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
			cp(g, target, control, value);
		}
		rounds++;
	}
	add->used_layer += INTEGERSIZE;
	QFT_inverse(add);
	precompiled_QQ_add = add;

	return add;
}
sequence_t *cCQ_add() {
	// Compute rotation angles
	int NonZeroCount = 0;
	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	// Compute rotations for addition
	double *rotations = calloc(INTEGERSIZE, sizeof(double));
	for (int i = 0; i < INTEGERSIZE; ++i) {
		for (int j = 0; j < INTEGERSIZE - i; ++j) {
			rotations[j + i] += bin[INTEGERSIZE - i - 1] * 2 * M_PI / (pow(2, j + 1));
		}
		if (rotations[i] != 0) NonZeroCount++;
	}
	free(bin);
	int start_layer = INTEGERSIZE;

	if (precompiled_cCQ_add) {
		sequence_t *add = precompiled_cCQ_add;

		for (int i = 0; i < INTEGERSIZE; ++i) {
			add->seq[start_layer + i][add->gates_per_layer[start_layer + i] - 1].GateValue = rotations[i];
		}
		free(rotations);
		return add;
	}

	sequence_t *add = malloc(sizeof(sequence_t));
	// allocate exact number of layer and enough gates per layer
	add->used_layer = 0;
	add->num_layer = 4 * INTEGERSIZE - 1;
	memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));
	QFT(add);

	for (int i = 0; i < INTEGERSIZE; ++i) {
		cp(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i, 2 * INTEGERSIZE - 1, rotations[INTEGERSIZE - i - 1]);
	}
	free(rotations);
	add->used_layer++;

	QFT_inverse(add);

	precompiled_cCQ_add = add;
	return add;
}
sequence_t *cQQ_add() {
	if (precompiled_cQQ_add != NULL) return precompiled_cQQ_add;

	sequence_t *add = malloc(sizeof(sequence_t));

	// allocate exact number of layer and enough gates per layer
	add->used_layer = 0;
	add->num_layer = INTEGERSIZE * (INTEGERSIZE + 1) / 2 * 4 + 4 * INTEGERSIZE - 2 - INTEGERSIZE / 4 * 4 + 3;
	memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));

	QFT(add);

	int control = 3 * INTEGERSIZE - 1;
	int rounds;
	int layer = 2 * INTEGERSIZE - 1;

	// block 1
	for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
		double value = 0;
		for (int i = 0; i < INTEGERSIZE - bit; ++i) {
			value += 2 * M_PI / (pow(2, i + 1)) / 2;
		}
		gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
		cp(g, bit, control, value);
		layer++;
	}


	// block 2
	rounds = 0;
	for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
		gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
		cx(g, control, INTEGERSIZE + bit);
		layer++;
		for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
			double value = 2 * M_PI / (pow(2, i + 1)) / 2;
			g = &add->seq[layer][add->gates_per_layer[layer]++];
			cp(g, bit - i, control, -value);
			layer++;
		}
		g = &add->seq[layer][add->gates_per_layer[layer]++];
		cx(g, control, INTEGERSIZE + bit);
		layer++;
		rounds++;
	}

	// block 3
	rounds = 0;
	for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
		for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
			double value = 2 * M_PI / (pow(2, i + 1)) / 2;
			gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
			cp(g, bit - i, INTEGERSIZE + bit, value);
			layer++;
		}
		layer -= INTEGERSIZE - rounds;
		rounds++;
	}
	add->used_layer = layer + 1;
	QFT_inverse(add);
	precompiled_cQQ_add = add;

	return add;
}

sequence_t *P_add() {
	sequence_t *seq = malloc(sizeof(sequence_t));

	seq->gates_per_layer[0] = 1;
	seq->used_layer = 1;
	seq->num_layer = 1;
	// implement correct phase multiplication
	p(&seq->seq[0][0], 0, *(QPU_state->R0));

	return seq;
}
sequence_t *cP_add() {
	sequence_t *seq = malloc(sizeof(sequence_t));

	seq->gates_per_layer[0] = 1;
	seq->used_layer = 1;
	seq->num_layer = 1;
	// implement correct phase multiplication
	cp(&seq->seq[0][0], 0, 1, *(QPU_state->R0));

	return seq;
}