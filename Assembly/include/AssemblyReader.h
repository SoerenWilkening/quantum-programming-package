//
// Created by Sören Wilkening on 20.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYREADER_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYREADER_H

#include "AssemblyOperations.h"

#include <ctype.h>

#define MAX_LINE_LENGTH 1024 // Maximum length of a line
#define hash_size 4096

typedef struct {
	char *label;
    char *addon;
    char *instruction;
    char *var1;
    char *var2;
    char *var3;
    char *var4;
    int value;
	instruction_t *ptr;
} call_t;

typedef struct {
    quantum_int_t *integer;
    char *word;
} hash_element_t;

void ReadAssembly(char *asmb[], int num);

void AsmbFromFile();

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYREADER_H
