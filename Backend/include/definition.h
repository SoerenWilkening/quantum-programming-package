//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_DEFINITION_H
#define CQ_BACKEND_IMPROVED_DEFINITION_H

#include <stdlib.h>

#define INTEGERSIZE 64
#define QBITSIZE 1
#define QBYTESIZE 8
#define QHWORDSIZE 16
#define QWORDSIZE 32
#define QDWORDSIZE 64

#define POINTER 1
#define VALUE 0

#define Qu 0
#define Cl 1

// desired functionality for storing all the gates and operations ======================================================
#define MAXCONTROLS 2

#define INVERTED 1
#define NOTINVERTED 0

#define DECOMPOSETOFFOLI 1
#define DONTDECOMPOSETOFFOLI 0
typedef char decompose_toffoli_t;

typedef unsigned int qubit_t;
typedef size_t layer_t;
typedef unsigned int num_t;

#endif //CQ_BACKEND_IMPROVED_DEFINITION_H
