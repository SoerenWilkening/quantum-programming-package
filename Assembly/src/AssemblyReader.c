//
// Created by Sören Wilkening on 20.11.24.
//

#include "AssemblyReader.h"

call_t calls[65536];
int counter = 0;
int total = 0;
int variable_counter = 0;
hash_element_t variables[hash_size];

// hashing functionality
unsigned int hash(const char *word) {
    unsigned int hash = 5381;
    while (*word) {
        hash = ((hash << 5) + hash) + *word;
        word++;
    }
    return hash % hash_size;
}

int label_index(char *label){
	for (int i = 0; i < label_counter; ++i) {
		if (strcmp(label, labels[i].label) == 0) return i;
	}
	return -1;
}

element_t *hash_element(char *word) {
    if (word == NULL) return NULL;
    unsigned int h = hash(word);
    while (variables[h].integer != NULL && strcmp(variables[h].word, word) != 0) {
        h++;
    }
    if (variables[h].integer != NULL && strcmp(variables[h].word, word) == 0) return variables[h].integer;

    int all_false = 1;
    if (strcmp(calls[counter].addon, "QUINT") == 0) {
        all_false = 0;
	    variables[h].integer = QUINT();
    }
    if (strcmp(calls[counter].addon, "QINT") == 0) {
        all_false = 0;
	    variables[h].integer = QINT();
    }
    if (strcmp(calls[counter].addon, "UINT") == 0) {
        all_false = 0;
	    variables[h].integer = INT(calls[counter].value);
    }
    if (strcmp(calls[counter].addon, "INT") == 0) {
        all_false = 0;
	    variables[h].integer = INT(calls[counter].value);
    }
    if (strcmp(calls[counter].addon, "QBOOL") == 0) {
        all_false = 0;
	    variables[h].integer = QBOOL();
    }
    if (strcmp(calls[counter].addon, "BOOL") == 0) {
        all_false = 0;
	    variables[h].integer = BOOL(calls[counter].value);
    }
    if (!all_false) {
	    variables[h].word = word;
        return variables[h].integer;
    }
    return NULL;
}

int is_instruction(char *word) {
	if (strcmp(word, "branch") == 0) return true;
	if (strcmp(word, "mov") == 0) return true;
	if (strcmp(word, "inc") == 0) return true;
	if (strcmp(word, "dcr") == 0) return true;
	if (strcmp(word, "padd") == 0) return true;

	if (strcmp(word, "add") == 0) return true;
	if (strcmp(word, "qadd") == 0) return true;
	if (strcmp(word, "qqadd") == 0) return true;
	if (strcmp(word, "cqadd") == 0) return true;
	if (strcmp(word, "cqqadd") == 0) return true;

	if (strcmp(word, "sub") == 0) return true;
	if (strcmp(word, "qsub") == 0) return true;
	if (strcmp(word, "qqsub") == 0) return true;
	if (strcmp(word, "cqsub") == 0) return true;
	if (strcmp(word, "cqqsub") == 0) return true;

	if (strcmp(word, "mul") == 0) return true;
	if (strcmp(word, "qmul") == 0) return true;
	if (strcmp(word, "qqmul") == 0) return true;
	if (strcmp(word, "cqmul") == 0) return true;
	if (strcmp(word, "cqqmul") == 0) return true;

	if (strcmp(word, "sdiv") == 0) return true;
	if (strcmp(word, "qsdiv") == 0) return true;
	if (strcmp(word, "qqsdiv") == 0) return true;
	if (strcmp(word, "cqsdiv") == 0) return true;
	if (strcmp(word, "cqqsdiv") == 0) return true;

	if (strcmp(word, "smod") == 0) return true;
	if (strcmp(word, "qsmod") == 0) return true;
	if (strcmp(word, "qqsmod") == 0) return true;
	if (strcmp(word, "cqsmod") == 0) return true;
	if (strcmp(word, "cqqsmod") == 0) return true;

	if (strcmp(word, "qqand") == 0) return true;
	if (strcmp(word, "qeq") == 0) return true;
	if (strcmp(word, "qgeq") == 0) return true;
	if (strcmp(word, "qleq") == 0) return true;
	if (strcmp(word, "MEASURE") == 0) return true;
	if (strcmp(word, "IF") == 0) return true;
	if (strcmp(word, "qnot") == 0) return true;
	if (strcmp(word, "jez") == 0) return true;
	if (strcmp(word, "jmp") == 0) return true;
	return false;
}

// Function to check if a string is a valid integer
bool is_integer(const char* str) {
	if (!str || *str == '\0') {
		return false; // Null or empty string is qnot an integer
	}

	// Optional leading sign
	if (*str == '+' || *str == '-') {
		str++; // Skip the sign
	}

	// Ensure there's at least one digit
	if (!isdigit((unsigned char)*str)) {
		return false; // No digits after the sign
	}

	// Check remaining characters are all digits
	for (; *str != '\0'; str++) {
		if (!isdigit((unsigned char)*str)) {
			return false; // Non-digit character found
		}
	}

	return true; // All checks passed
}
int is_addon(char *word) {
    if (strcmp(word, "inv") == 0) return true;
    if (strcmp(word, "QUINT") == 0) return true;
    if (strcmp(word, "QINT") == 0) return true;
    if (strcmp(word, "UINT") == 0) return true;
    if (strcmp(word, "INT") == 0) return true;
    if (strcmp(word, "QBOOL") == 0) return true;
    if (strcmp(word, "BOOL") == 0) return true;
    return false;
}
int is_label(char *str){
	bool only_spaces;
	char *cleaned_line;
	if (!str) {
		cleaned_line = NULL;
		only_spaces = true; // Treat null string as only spaces
		return 0; // No spaces
	}

	// Count leading spaces
	int leading_spaces = 0;
	while (str[leading_spaces] && isspace((unsigned char)str[leading_spaces])) {
		leading_spaces++;
	}

	// Pointer to the cleaned line (skipping leading spaces)
	cleaned_line = str + leading_spaces;

	// Remove trailing spaces or non-printable characters
	char* end = cleaned_line + strlen(cleaned_line) - 1;
	while (end >= cleaned_line && isspace((unsigned char)*end)) {
		*end = '\0';
		end--;
	}

	// Detect if the line contains only spaces
	only_spaces = (*cleaned_line == '\0');

//	printf("%s %d\n", str, leading_spaces == 0 && !only_spaces);
	return leading_spaces == 0 && !only_spaces;
}

void word_to_call(char *word) {
    if (is_integer(word)) return;
    if (is_addon(word)) calls[counter].addon = word;
    else if (is_instruction(word)) calls[counter].instruction = word;
    else {
        if (variable_counter == 0) calls[counter].var1 = word;
        if (variable_counter == 1) calls[counter].var2 = word;
        if (variable_counter == 2) calls[counter].var3 = word;
        if (variable_counter == 3) calls[counter].var4 = word;
        variable_counter++;
    }
}
void value_to_call(char *word) {
    if (!is_integer(word)) return;
    char *succ;
    calls[counter].value = (int) strtol(word, &succ, 10);
}

char **extract_items_from_line(const char *line, size_t *item_count) {
    if (!line || !item_count) return NULL;

    *item_count = 0; // Initialize the item count

    size_t capacity = 10; // Initial capacity for the array of items
    char **items = malloc(capacity * sizeof(char *));

    // Create a modifiable copy of the input line
    char *line_copy = strdup(line);

    // Tokenize the line
    char *token = strtok(line_copy, " \t\n");
    while (token) {
        // Reallocate if the array is full
        if (*item_count >= capacity) {
            capacity *= 2;
            char **temp = realloc(items, capacity * sizeof(char *));
            items = temp;
        }

        // Duplicate the token and store it
        items[*item_count] = strdup(token);

        (*item_count)++;
        token = strtok(NULL, " \t\n"); // Get the next token
        if (token == NULL) break;
    }
    free(line_copy); // Free the duplicated line
    return items;
}
void lines_to_call(char *line) {
    if (line[0] == *"/" || line[5] == *"/") return;

    calls[counter].value = 0;
    calls[counter].addon = NULL;
    calls[counter].label = NULL;
    calls[counter].instruction = NULL;
    calls[counter].var1 = NULL;
    calls[counter].var2 = NULL;
    calls[counter].var3 = NULL;
    calls[counter].var4 = NULL;
    calls[counter].ptr = NULL;
    size_t count = 0;

	// check if label
	if (is_label(line)){
		calls[counter].label = line;
	}

    char **words = extract_items_from_line(line, &count);
    if (count == 0) return;
    int comment = 0;
    for (int j = 0; j < count; ++j) {
        if (words[j][0] != *"/" && !comment) {
//	        printf("%s %d ", words[j], is_integer(words[j]));
            word_to_call(words[j]);
            value_to_call(words[j]);
        } else { comment = 1; }
    }

    // store all the variables in a hash table
    counter++;
}

void ReadAssembly(char *asmb[], int num) {
    for (int i = 0; i < hash_size; ++i) variables[i].integer = NULL;

    for (int i = 0; i < num; ++i) {
        variable_counter = 0;

        // go through every line
        lines_to_call(asmb[i]);
    }
}

void create_instruction() {
	if (calls[counter].instruction == NULL) return;
//    printf("%s %s, %s, %s, %d\n", calls[counter].instruction, calls[counter].var1, calls[counter].var2, calls[counter].var3, calls[counter].value);
	if (strcmp(calls[counter].instruction, "branch") == 0) branch(hash_element(calls[counter].var1), calls[counter].value);
	if (strcmp(calls[counter].instruction, "inc") == 0)  inc(hash_element(calls[counter].var1));
	if (strcmp(calls[counter].instruction, "dcr") == 0)  dcr(hash_element(calls[counter].var1));

	if (strcmp(calls[counter].instruction, "add") == 0) add(hash_element(calls[counter].var1), hash_element(calls[counter].var2));
	if (strcmp(calls[counter].instruction, "qadd") == 0) qadd(hash_element(calls[counter].var1), hash_element(calls[counter].var2));
	if (strcmp(calls[counter].instruction, "qqadd") == 0) qqadd(hash_element(calls[counter].var1), hash_element(calls[counter].var2));
	if (strcmp(calls[counter].instruction, "cqadd") == 0) cqadd(hash_element(calls[counter].var1), hash_element(calls[counter].var2), hash_element(calls[counter].var3));
	if (strcmp(calls[counter].instruction, "cqqadd") == 0) cqqadd(hash_element(calls[counter].var1), hash_element(calls[counter].var2), hash_element(calls[counter].var3));

	if (strcmp(calls[counter].instruction, "qqsub") == 0) qqsub(hash_element(calls[counter].var1), hash_element(calls[counter].var2));

	if (strcmp(calls[counter].instruction, "padd") == 0) padd(hash_element(calls[counter].var1), INT(calls[counter].value));

	if (strcmp(calls[counter].instruction, "sdiv") == 0) sdiv(hash_element(calls[counter].var1), hash_element(calls[counter].var2));
	if (strcmp(calls[counter].instruction, "qsdiv") == 0) qsdiv(hash_element(calls[counter].var1), INT(calls[counter].value), hash_element(calls[counter].var2));
	if (strcmp(calls[counter].instruction, "qqsdiv") == 0) qqsdiv(hash_element(calls[counter].var1), hash_element(calls[counter].var2), hash_element(calls[counter].var3));
	if (strcmp(calls[counter].instruction, "cqsdiv") == 0) cqsdiv(hash_element(calls[counter].var1), INT(calls[counter].value), hash_element(calls[counter].var2), hash_element(calls[counter].var3));
	if (strcmp(calls[counter].instruction, "cqqsdiv") == 0) cqqsdiv(hash_element(calls[counter].var1), hash_element(calls[counter].var2), hash_element(calls[counter].var3), hash_element(calls[counter].var4));

	if (strcmp(calls[counter].instruction, "qqsmod") == 0) qqsmod(hash_element(calls[counter].var1), hash_element(calls[counter].var2), hash_element(calls[counter].var3));

	if (strcmp(calls[counter].instruction, "qeq") == 0) {
		element_t *el3 = hash_element(calls[counter].var3);
		if (el3 == NULL) el3 = INT(calls[counter].value);
		qeq(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
	}
	if (strcmp(calls[counter].instruction, "qgeq") == 0) {
		element_t *el3 = hash_element(calls[counter].var3);
		if (el3 == NULL) {
			el3 = INT(calls[counter].value);
			el3->qualifier = Cl;
		}
		qgeq(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
	}
	if (strcmp(calls[counter].instruction, "qleq") == 0) {
		element_t *el3 = hash_element(calls[counter].var3);
		if (el3 == NULL) el3 = INT(calls[counter].value);
		qleq(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
	}
	if (strcmp(calls[counter].instruction, "qqand") == 0) {
		element_t *el3 = hash_element(calls[counter].var3);
		if (el3 == NULL) el3 = INT(calls[counter].value);
		qqand(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
	}
	if (strcmp(calls[counter].instruction, "qnot") == 0) qnot(hash_element(calls[counter].var1));
	if (strcmp(calls[counter].instruction, "jez") == 0) jez(hash_element(calls[counter].var1));
	if (strcmp(calls[counter].instruction, "jmp") == 0) jmp();
	calls[counter].ptr = &stack.instruction_list[stack.instruction_counter - 1];
}
void create_label(){
	if (calls[counter].label == NULL) return;
	label(calls[counter].label);
}
void apply_label(){
	for (int i = 0; i < counter; ++i) {
		if (calls[i].instruction != NULL) {
			if (strcmp(calls[i].instruction, "jez") == 0) {
				printf("label_ptr = %p\n", labels[label_index(calls[i].var2)].ins_ptr);
				calls[i].ptr->next_instruction = (struct instruction_t *) labels[label_index(calls[i].var2)].ins_ptr;
			}
			if (strcmp(calls[i].instruction, "jmp") == 0) {
				calls[i].ptr->next_instruction = (struct instruction_t *) labels[label_index(calls[i].var1)].ins_ptr;
			}
		}
	}
}

void create_executable() {
	total = counter;
	counter = 0;

	for (int i = 0; i < total; ++i) {
		// create the variables and store in hash table
		element_t *var = NULL;
		if (calls[counter].addon != NULL) var = hash_element(calls[counter].var1);

		// run instructions ------------------------------------

		// call inverse
		if (calls[counter].addon != NULL) if (strcmp(calls[counter].addon, "inv") == 0) inv();

		// run instruction
		create_instruction();

		create_label();

		counter++;
	}
}

void AsmbFromFile() {

    FILE *file = fopen("../assembly.pqsm", "r");
    int line_count = 0;

    size_t capacity = 256; // Initial capacity for the array of lines
    char **lines = malloc(capacity * sizeof(char *));

    char buffer[MAX_LINE_LENGTH];
    while (fgets(buffer, sizeof(buffer), file)) {
        // Remove the newline character if present
        buffer[strcspn(buffer, "\n")] = '\0';

        // Reallocate if the array is full
        if (line_count >= capacity) {
            capacity *= 2;
            char **temp = realloc(lines, capacity * sizeof(char *));
            lines = temp;
        }

        // Allocate memory for the line and copy the buffer
        lines[line_count] = strdup(buffer);

        line_count++;
    }
    ReadAssembly(lines, line_count);

	create_executable();

	// apply labels to jumps
	apply_label();

}
