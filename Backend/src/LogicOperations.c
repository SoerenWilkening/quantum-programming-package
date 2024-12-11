//
// Created by Sören Wilkening on 05.11.24.
//

#include "LogicOperations.h"

sequence_t *void_seq() {
	return NULL;
}

sequence_t *branch_seq() {
	sequence_t *seq = malloc(sizeof(sequence_t *));

	seq->used_layer = 1;
	seq->num_layer = 1;
	seq->gates_per_layer[0] = 1;

	seq->seq[0][0].Gate = H;
	seq->seq[0][0].Target = INTEGERSIZE - 1;
	seq->seq[0][0].NumControls = 0;
	return seq;
}

sequence_t *ctrl_branch_seq() {
	sequence_t *seq = malloc(sizeof(sequence_t *));

	seq->used_layer = 1;
	seq->num_layer = 1;
	seq->gates_per_layer[0] = 1;

	seq->seq[0][0].Gate = H;
	seq->seq[0][0].Target = INTEGERSIZE - 1;
	seq->seq[0][0].NumControls = 2 * INTEGERSIZE - 1;
	seq->seq[0][0].Control[0] = 1;
	return seq;
}

sequence_t *not_seq() {
	int number = INTEGERSIZE;

	sequence_t *seq = malloc(sizeof(sequence_t));

	seq->gates_per_layer[0] = INTEGERSIZE - number + 1;
	seq->used_layer = 1;
	seq->num_layer = 1;
	int counter = 0;
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		x(&seq->seq[0][counter++], i);
	}
	return seq;
}

sequence_t *ctrl_not_seq() {
	int number = INTEGERSIZE;
	if (stack.Q0->type != BOOLEAN) number = 1;

	sequence_t *seq = malloc(sizeof(sequence_t));

	seq->gates_per_layer[0] = INTEGERSIZE - number + 1;
	seq->used_layer = 1;
	seq->num_layer = 1;
	int counter = 0;
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
//		printf("%d\n", i);
		cx(&seq->seq[0][counter++], i, 2 * INTEGERSIZE - 1);
	}
	return seq;
}


sequence_t *and_seq() {
	// classical and
	*((int *) stack.Q0) = *((int *) stack.Q1) & *((int *) stack.Q2);
	return NULL;
}

sequence_t *q_and_seq() {
	// semiclassical and
	// -> GRP2 always has to be the quantum element
	int number = INTEGERSIZE;
	if (stack.Q0->type != BOOLEAN) number = 1;

	int *bin = two_complement(*(stack.R0), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t *));
	seq->used_layer = 1;
	seq->num_layer = 1;
	seq->gates_per_layer[0] = 0;

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		int control = INTEGERSIZE + i;
		int target = i;
		if (bin[i] == 1) {
			gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
			cx(g, target, control);
		}
	}
	free(bin);
	return seq;
}

sequence_t *ctrl_q_and_seq() {
	// semiclassical and
	// -> GRP2 always has to be the quantum element
	int number = INTEGERSIZE;
	if (stack.Q0->type != BOOLEAN) number = 1;

	int *bin = two_complement(*((int *) stack.Q2), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t *));
	seq->used_layer = 1;
	seq->num_layer = 1;
	seq->gates_per_layer[0] = 0;

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		int control = INTEGERSIZE + i;
		int target = i;
		if (bin[i] == 1) {
			gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
			ccx(g, target, control, 2 * INTEGERSIZE);
		}
	}
	free(bin);
	return seq;
}

sequence_t *qq_and_seq() {
	// pure quantum
	sequence_t *seq = malloc(sizeof(sequence_t *));

	int number = INTEGERSIZE;
	if (stack.Q0->type != BOOLEAN) number = 1;

	seq->used_layer = 1;
	seq->num_layer = 1;

	seq->gates_per_layer[0] = INTEGERSIZE - number + 1;
	int counter = 0;
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		ccx(&seq->seq[0][counter++], i, number + i, 2 * number + i);
	}

	return seq;
}