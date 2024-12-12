//
// Created by Sören Wilkening on 05.11.24.
//
#include "Integer.h"


void CP_sequence(sequence_t *mul, num_t *layer, int rounds, num_t control, double multiplyer, int inverted) {
    int l1 = 0, l2 = INTEGERSIZE - rounds;
    int fac = 1;
    if (inverted) {
        l1 = INTEGERSIZE - 1;
        l2 = 0;
        fac = -1;
    }
	for (int i = l1; i < l2; i += fac) {
	    num_t target = INTEGERSIZE - i - 1 - rounds;
	    double value = M_PI / (pow(2, i + 1)) * multiplyer;
	    gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        cp(g, target, control, value);
        (*layer)++;
    }
}
void CX_sequence(sequence_t *mul, num_t *layer, int bit_int2){
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        num_t control = INTEGERSIZE + bit;
        gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        cx(g, control, 3 * INTEGERSIZE + bit_int2 - 1);
        (*layer)++;
    }
}
void CX2_sequence(sequence_t *mul, num_t *layer, int bit_int2){
	for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
		num_t control = 2 * INTEGERSIZE + bit;
		gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
		cx(g, control, 3 * INTEGERSIZE + bit_int2 - 1);
		(*layer)++;
	}
}
void CCX_sequence(sequence_t *mul, num_t *layer, int bit_int2){
	for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
		num_t control = INTEGERSIZE + bit;
		gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
		ccx(g, control, 3 * INTEGERSIZE + bit_int2 - 1, 4 * INTEGERSIZE - 1);
		(*layer)++;
	}
}
void all_rot(sequence_t *mul, num_t *layer, int inverted, double multiplyer){
    int rounds = 0;
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        num_t control = INTEGERSIZE + bit;
//        CP_sequence(mul, layer, rounds, control, -(pow(2, INTEGERSIZE) - 1) / 2 * multiplyer, inverted);
        CP_sequence(mul, layer, rounds, control, - multiplyer / 2, inverted);
        *layer -= INTEGERSIZE - rounds;
        rounds++;
    }
    *layer += INTEGERSIZE;
}
void all_rot_final_block(sequence_t *mul, num_t *layer, int rounds, num_t control, double multiplyer, int inverted){

}

sequence_t *CC_mul(){
	*((int *) stack.R0) = *((int *) stack.R1) * *((int *) stack.R2);
	return NULL;
}
sequence_t *CQ_mul() {
	int *bin = two_complement(*(stack.R0), INTEGERSIZE);

	sequence_t *mul = malloc(sizeof(sequence_t));
	mul->used_layer = 0;
	mul->num_layer = INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
	memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));

	QFT(mul);
	num_t layer = 2 * INTEGERSIZE - 1;
	int rounds = 0;

	// all the CP block of the first decomp step can be merged
	for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
		layer = 2 * INTEGERSIZE + 2 * rounds - 1;
		num_t control = INTEGERSIZE + bit;
		for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
//			num_t target = i + rounds;
			num_t target = INTEGERSIZE - i - 1 - rounds;
			double value = 0;
			for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
//				printf("%d ", bin[bit_int2]);
				value += bin[bit_int2] * 2 * M_PI / (pow(2, i + 1)) * pow(2, INTEGERSIZE - bit_int2 - 1);
				printf("%d %f ", bit_int2, 2 * M_PI / (pow(2, i + 1)) * pow(2, INTEGERSIZE - bit_int2 - 1));
			}
			printf("\n");
			gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
			cp(g, target, control, value);
			layer++;
		}
		rounds++;
	}

	mul->used_layer = layer;
	QFT_inverse(mul);

	return mul;
}
sequence_t *QQ_mul() {
    if (precompiled_QQ_mul != NULL) return precompiled_QQ_mul;

    sequence_t *mul = malloc(sizeof(sequence_t));

    mul->used_layer = 0;
    mul->num_layer = INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
    memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));

    QFT(mul);
    num_t layer = INTEGERSIZE;

	// block 1
    int rounds = 0;
    // First blocks of CCP decompositions
    // all the CP block of the first decomp step can be merged
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        layer = 2 * INTEGERSIZE + 2 * rounds - 1;
        CP_sequence(mul, &layer, rounds, INTEGERSIZE + bit, pow(2, INTEGERSIZE) - 1, false);
        rounds++;
    }
	layer++;

	// block 2
    // intermediate step, C1X0 C0P_2(value/2)C1X0
    for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
		layer -= INTEGERSIZE;
        CX_sequence(mul, &layer, - bit_int2);

        all_rot(mul, &layer, false, pow(2, 1 + bit_int2));

        CX_sequence(mul, &layer, - bit_int2);

	    for (int i = 0; i < INTEGERSIZE; ++i) {
			gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
//		    printf("%d %d %f %f\n", bit_int2, i, pow(2, i + 1) - 1, pow(2, bit_int2));
			double value = pow(2, - i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2);
		    cp(g, INTEGERSIZE - i - 1, 3 * INTEGERSIZE - bit_int2 - 1, value);
			layer++;
	    }
    }
	layer++;
//	layer -= INTEGERSIZE - 1;
    mul->used_layer = layer - 1;
    QFT_inverse(mul);

    precompiled_QQ_mul = mul;
    return mul;
}
sequence_t *cCQ_mul() {
    int *bin = two_complement(*(stack.R0), INTEGERSIZE);

    sequence_t *mul = malloc(sizeof(sequence_t));
    mul->used_layer = 0;
    mul->num_layer = INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
    memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));

    QFT(mul);

	int control = 3 * INTEGERSIZE - 1;
    // precompute all the rotation angles
    double values[INTEGERSIZE];
    memset(values, 0, INTEGERSIZE * sizeof(double));
    for (int i = 0; i < INTEGERSIZE; ++i) {
        for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
            values[i] += bin[bit_int2] * 2 * M_PI / (pow(2, i + 1)) * pow(2, INTEGERSIZE - bit_int2 - 1);
        }
    }

	// block 1
    int rounds;
    int layer = 2 * INTEGERSIZE - 1;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        double value = 0;
        for (int i = 0; i < INTEGERSIZE - bit; ++i) {
            value += values[i] / 2;
        }
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cp(g, bit, control, value);
        layer++;
    }

	// block 2
    rounds = 0;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, INTEGERSIZE + bit);
        layer++;
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, bit - i, control, -values[i] / 2);
            layer++;
        }
        g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, INTEGERSIZE + bit);
        layer++;
        rounds++;
    }

	// block 3
    rounds = 0;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, bit - i, INTEGERSIZE + bit, values[i] / 2);
            layer++;
        }
        layer -= INTEGERSIZE - rounds;
        rounds++;
    }
    mul->used_layer = layer + 1;

    QFT_inverse(mul);

    return mul;
}
sequence_t *cQQ_mul() {

	if (precompiled_cQQ_mul != NULL) return precompiled_cQQ_mul;

	sequence_t *mul = malloc(sizeof(sequence_t));

	mul->used_layer = 0;
//	mul->num_layer = 20 * INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
	mul->num_layer = MAXLAYERINSEQUENCE;
	memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));

	QFT(mul);
	// start after qft
	num_t layer = 2 * INTEGERSIZE - 1;

	double values[INTEGERSIZE];
	memset(values, 0, INTEGERSIZE * sizeof(double));

	// First blocks : decompose the controlled QQadd block from the first block in qq_mul
	int rounds = 0;
	for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
		num_t control = INTEGERSIZE + bit;
		CP_sequence(mul, &layer, rounds, control, (pow(2, INTEGERSIZE) - 1) / 2, false);
		rounds++;
	}
	layer -= INTEGERSIZE - 1;
	CX_sequence(mul, &layer, INTEGERSIZE);
	all_rot(mul, &layer, false, (pow(2, INTEGERSIZE) - 1));
	CX_sequence(mul, &layer, INTEGERSIZE);

	for (int bit = 0; bit < INTEGERSIZE; ++bit) {
		gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
		double value = M_PI / 2 * (pow(2, INTEGERSIZE) - 1) * pow(2, - bit - 1) * (pow(2, bit + 1) - 1);
		cp(g, INTEGERSIZE - bit - 1, 4 * INTEGERSIZE - 1, value);
		layer++;
	}

	// block 2 and 3
	for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
		CCX_sequence(mul, &layer, -bit_int2);
		all_rot(mul, &layer, false, pow(2, bit_int2));
		CX_sequence(mul, &layer, INTEGERSIZE);
		all_rot(mul, &layer, false, -pow(2, bit_int2));
		CX_sequence(mul, &layer, INTEGERSIZE);

		// culmination of controlled rotation gates
		for (int bit = 0; bit < INTEGERSIZE; ++bit) {
			gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
			double value = -M_PI * pow(2, bit_int2) * (pow(2, bit + 1) - 1) * pow(2, -bit - 1) / 2;
			cp(g, INTEGERSIZE - bit - 1, 4 * INTEGERSIZE - 1, value);
			layer++;
		}
		CCX_sequence(mul, &layer, -bit_int2);

		// decomposition of the culminations from the QQ_mul
		for (int i = 0; i < INTEGERSIZE; ++i) {
			gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
			double value = pow(2, - i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2) / 2;
			cp(g, INTEGERSIZE - i - 1, 3 * INTEGERSIZE - bit_int2 - 1, value);
			layer++;
		}

		gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
		cx(g, 3 * INTEGERSIZE - bit_int2 - 1, 4 * INTEGERSIZE - 1);
		layer++;

		for (int i = 0; i < INTEGERSIZE; ++i) {
			gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
			double value = -pow(2, - i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2) / 2;
			cp(g, INTEGERSIZE - i - 1, 3 * INTEGERSIZE - bit_int2 - 1, value);
			layer++;
		}
		g = &mul->seq[layer][mul->gates_per_layer[layer]++];
		cx(g, 3 * INTEGERSIZE - bit_int2 - 1, 4 * INTEGERSIZE - 1);
		layer++;

		for (int i = 0; i < INTEGERSIZE; ++i) {
			gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
			double value = pow(2, - i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2) / 2;
			cp(g, INTEGERSIZE - i - 1, 4 * INTEGERSIZE - 1, value);
			layer++;
		}
	}

	mul->used_layer = layer;
	QFT_inverse(mul);

	precompiled_cQQ_mul = mul;
	return mul;
}
