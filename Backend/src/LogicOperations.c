//
// Created by Sören Wilkening on 05.11.24.
//

#include "LogicOperations.h"

sequence_t *void_seq() {
	return NULL;
}

sequence_t *jmp_seq() {
	if (*QPU_state->R0 == 0) QPU_state = QPU_state->next_instruction;
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
	*(QPU_state->R0) = !(*(QPU_state->R0));
	return NULL;
}
sequence_t *q_not_seq() {
	int number = QPU_state->Q0->MSB + 1;

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
sequence_t *cq_not_seq() {
	int number = QPU_state->Q0->MSB + 1;

	sequence_t *seq = malloc(sizeof(sequence_t));

	for (int i = 0; i < INTEGERSIZE; ++i) seq->gates_per_layer[i] = 0;
	seq->used_layer = 0;
	seq->num_layer = INTEGERSIZE;
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		cx(&seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++], i, 2 * INTEGERSIZE - 1);
		seq->used_layer++;
	}
	return seq;
}

sequence_t *and_seq() {
	// classical and
	*(QPU_state->R0) = *(QPU_state->R1) & *(QPU_state->R2);
	return NULL;
}
sequence_t *q_and_seq() {
	// semiclassical and
	// -> GRP2 always has to be the quantum element
	int number = QPU_state->Q0->MSB + 1;

	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->used_layer = 1;
	seq->num_layer = 1;
	for (int i = 0; i < INTEGERSIZE; ++i) seq->gates_per_layer[i] = 0;

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
sequence_t *qq_and_seq() {
	// pure quantum
	sequence_t *seq = malloc(sizeof(sequence_t));

	int number = QPU_state->Q0->MSB + 1;
	printf("%d\n", number);

	seq->used_layer = 1;
	seq->num_layer = 1;
	seq->gates_per_layer[0] = INTEGERSIZE - number + 1;
	int counter = 0;
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		ccx(&seq->seq[0][counter++], i, INTEGERSIZE + i, 2 * INTEGERSIZE + i);
	}

	return seq;
}
sequence_t *cq_and_seq() {
	// semiclassical and
	// -> GRP2 always has to be the quantum element
	int number = QPU_state->Q0->MSB + 1;

	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->used_layer = 0;
	seq->num_layer = INTEGERSIZE;

	for (int i = 0; i < INTEGERSIZE; ++i) seq->gates_per_layer[i] = 0;

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		if (bin[i] == 1) {
			gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
			ccx(g, i, INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
			seq->used_layer++;
		}
	}
	free(bin);
	return seq;
}
sequence_t *cqq_and_seq() {
	// pure quantum
	sequence_t *seq = malloc(sizeof(sequence_t));

	int number = QPU_state->Q0->MSB + 1;

	seq->used_layer = 0;
	seq->num_layer = 3 * INTEGERSIZE;

	for (int i = 0; i < 3 * INTEGERSIZE; ++i) seq->gates_per_layer[i] = 0;

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		seq->used_layer++;
		ccx(g, 4 * INTEGERSIZE, INTEGERSIZE + i, 2 * INTEGERSIZE);

		g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		seq->used_layer++;
		ccx(g, i, 4 * INTEGERSIZE, 4 * INTEGERSIZE - 1);

		g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		seq->used_layer++;
		ccx(g, 4 * INTEGERSIZE, INTEGERSIZE + i, 2 * INTEGERSIZE);
	}

	return seq;
}

sequence_t *xor_seq() {
	*(QPU_state->R0) = *(QPU_state->R1) ^ *(QPU_state->R2);
	return NULL;
}
sequence_t *q_xor_seq() {
	// pure quantum

	int number = QPU_state->Q0->MSB + 1;

	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->used_layer = 1;
	seq->num_layer = 1;

	seq->gates_per_layer[0] = 0;
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		if (bin[i] == 1) {
			gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
			x(g, i);
		}
	}

	free(bin);
	return seq;
}
sequence_t *cq_xor_seq() {
	// pure quantum

	int number = QPU_state->Q0->MSB + 1;
	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->used_layer = 0;
	seq->num_layer = INTEGERSIZE;

	for (int i = 0; i < INTEGERSIZE; ++i) seq->gates_per_layer[i] = 0;
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		if (bin[i] == 1) {
			gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
			cx(g, i, 2 * INTEGERSIZE - 1);
			seq->used_layer++;
		}
	}

	free(bin);
	return seq;
}
sequence_t *qq_xor_seq() {
	// pure quantum
	sequence_t *seq = malloc(sizeof(sequence_t *));

	int number = QPU_state->Q0->MSB + 1;

	seq->used_layer = 1;
	seq->num_layer = 1;

	seq->gates_per_layer[0] = INTEGERSIZE - number + 1;
	int counter = 0;
	for (int i = number - 1; i < INTEGERSIZE; ++i) cx(&seq->seq[0][counter++], i, INTEGERSIZE + i);

	return seq;
}
sequence_t *cqq_xor_seq() {
	// pure quantum
	sequence_t *seq = malloc(sizeof(sequence_t *));

	int number = QPU_state->Q0->MSB + 1;

	seq->used_layer = 0;
	seq->num_layer = INTEGERSIZE;

	for (int i = 0; i < INTEGERSIZE; ++i) {
		seq->gates_per_layer[i] = 0;
	}
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		ccx(&seq->seq[seq->used_layer][0], i, INTEGERSIZE + i, 3 * INTEGERSIZE - 1);
		seq->gates_per_layer[seq->used_layer]++;
		seq->used_layer++;
	}

	return seq;
}

sequence_t *or_seq() {
	*(QPU_state->R0) = *(QPU_state->R1) | *(QPU_state->R2);
	return NULL;
}
sequence_t *q_or_seq() {
	// pure quantum

	int number = QPU_state->Q0->MSB + 1;
	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->used_layer = 1;
	seq->num_layer = 1;

	seq->gates_per_layer[0] = 0;
	seq->gates_per_layer[1] = 0;
	seq->gates_per_layer[2] = 0;

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		if (bin[i] == 0) {
			gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
			cx(g, i, INTEGERSIZE + i);
		}
	}

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		if (bin[i] == 1) {
			gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
			x(g, i);
		}
	}
	free(bin);
	return seq;
}
sequence_t *qq_or_seq() {
	// pure quantum

	int number = QPU_state->Q0->MSB + 1;

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->used_layer = 3;
	seq->num_layer = 3;

	seq->gates_per_layer[0] = 0;
	seq->gates_per_layer[1] = 0;
	seq->gates_per_layer[2] = 0;

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
		cx(g, i, INTEGERSIZE + i);
	}

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		gate_t *g = &seq->seq[1][seq->gates_per_layer[1]++];
		cx(g, i, 2 * INTEGERSIZE + i);
	}
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		gate_t *g = &seq->seq[2][seq->gates_per_layer[2]++];
		ccx(g, i, INTEGERSIZE + i, 2 * INTEGERSIZE + i);
	}

	return seq;
}
sequence_t *cq_or_seq() {
	// pure quantum

	int number = QPU_state->Q0->MSB + 1;

	int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->num_layer = INTEGERSIZE;

	for (int i = 0; i < INTEGERSIZE; ++i) seq->gates_per_layer[i] = 0;

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		if (bin[i] == 0) {
			gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
			ccx(g, i, INTEGERSIZE + i, 2 * INTEGERSIZE - 1);
			seq->used_layer++;
		}
	}

	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		if (bin[i] == 1) {
			gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
			cx(g, i, 2 * INTEGERSIZE - 1);
			seq->used_layer++;
		}
	}
	free(bin);
	return seq;
}
sequence_t *cqq_or_seq() {
	// pure quantum

	int number = QPU_state->Q0->MSB + 1;

	sequence_t *seq = malloc(sizeof(sequence_t));
	seq->used_layer = 0;
	seq->num_layer = 5 * INTEGERSIZE;

	for (int i = 0; i < 5 * INTEGERSIZE; ++i) {
		seq->gates_per_layer[i] = 0;
	}
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		ccx(g, i, INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
		seq->used_layer++;
	}
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		ccx(g, i, 2 * INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
		seq->used_layer++;
	}
	for (int i = number - 1; i < INTEGERSIZE; ++i) {
		gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		ccx(g, 4 * INTEGERSIZE, 2 * INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
		seq->used_layer++;

		g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		ccx(g, i, 4 * INTEGERSIZE, INTEGERSIZE + i);
		seq->used_layer++;

		g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
		ccx(g, 4 * INTEGERSIZE, 2 * INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
		seq->used_layer++;
	}

	return seq;
}
