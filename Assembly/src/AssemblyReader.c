//
// Created by Sören Wilkening on 20.11.24.
//

#include "AssemblyReader.h"

call_t calls[1024];
int counter = 0;
int total = 0;
int variable_counter = 0;
hash_element_t hash_elements[hash_size];

// hashing functionality
unsigned int hash(const char *word) {
    unsigned int hash = 5381;
    while (*word) {
        hash = ((hash << 5) + hash) + *word;
        word++;
    }
    return hash % hash_size;
}

element_t *hash_element(char *word) {
    if (word == NULL) return NULL;
    unsigned int h = hash(word);
    while (hash_elements[h].integer != NULL && strcmp(hash_elements[h].word, word) != 0) {
        h++;
    }
    if (hash_elements[h].integer != NULL && strcmp(hash_elements[h].word, word) == 0) return hash_elements[h].integer;

    int all_false = 1;
    if (strcmp(calls[counter].addon, "QUINT") == 0) {
        all_false = 0;
        hash_elements[h].integer = QUINT();
    }
    if (strcmp(calls[counter].addon, "QINT") == 0) {
        all_false = 0;
        hash_elements[h].integer = QINT();
    }
    if (strcmp(calls[counter].addon, "UINT") == 0) {
        all_false = 0;
        hash_elements[h].integer = INT(calls[counter].value);
    }
    if (strcmp(calls[counter].addon, "INT") == 0) {
        all_false = 0;
        hash_elements[h].integer = INT(calls[counter].value);
    }
    if (strcmp(calls[counter].addon, "QBOOL") == 0) {
        all_false = 0;
        hash_elements[h].integer = QBOOL();
    }
    if (strcmp(calls[counter].addon, "BOOL") == 0) {
        all_false = 0;
        hash_elements[h].integer = INT(calls[counter].value);
    }
    if (!all_false) {
        hash_elements[h].word = word;
        return hash_elements[h].integer;
    }
    return NULL;
}

// Function to check if the string is a word (alphabetic characters only)
bool is_word(const char *str) {
    if (!str || *str == '\0') {
        return false; // Empty or null string is not a word
    }
    bool has_alpha = false;

    for (size_t i = 0; str[i] != '\0'; i++) {
        if (!isalnum((unsigned char) str[i])) {
            return false; // Contains non-alphanumeric characters
        }
        if (isalpha((unsigned char) str[i])) {
            has_alpha = true; // Contains at least one alphabetic character
        }
    }
    return has_alpha;
}

int is_addon(char *word) {
    if (strcmp(word, "INV") == 0) return true;
    if (strcmp(word, "QUINT") == 0) return true;
    if (strcmp(word, "QINT") == 0) return true;
    if (strcmp(word, "UINT") == 0) return true;
    if (strcmp(word, "INT") == 0) return true;
    if (strcmp(word, "QBOOL") == 0) return true;
    if (strcmp(word, "BOOL") == 0) return true;
    return false;
}

int is_instruction(char *word) {
    if (strcmp(word, "BRANCH") == 0) return true;
    if (strcmp(word, "MOV") == 0) return true;
    if (strcmp(word, "IADD") == 0) return true;
    if (strcmp(word, "PADD") == 0) return true;
    if (strcmp(word, "ISUB") == 0) return true;
    if (strcmp(word, "IMUL") == 0) return true;
    if (strcmp(word, "IDIV") == 0) return true;
    if (strcmp(word, "MOD") == 0) return true;
    if (strcmp(word, "AND") == 0) return true;
    if (strcmp(word, "EQ") == 0) return true;
    if (strcmp(word, "GEQ") == 0) return true;
    if (strcmp(word, "LEQ") == 0) return true;
    if (strcmp(word, "MEASURE") == 0) return true;
    if (strcmp(word, "IF") == 0) return true;
    return false;
}

void word_to_call(char *word) {
    if (!is_word(word)) return;
    if (is_addon(word)) calls[counter].addon = word;
    else if (is_instruction(word)) calls[counter].instruction = word;
    else {
        if (variable_counter == 0) calls[counter].var1 = word;
        if (variable_counter == 1) calls[counter].var2 = word;
        if (variable_counter == 2) calls[counter].var3 = word;
        variable_counter++;
    }
}

void value_to_call(char *word) {
    if (is_word(word)) return;
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
    if (line[0] == *"/" || line[1] == *"/") return;

    calls[counter].value = 0;
    calls[counter].addon = NULL;
    calls[counter].instruction = NULL;
    calls[counter].var1 = NULL;
    calls[counter].var2 = NULL;
    calls[counter].var3 = NULL;
    size_t count = 0;

    char **words = extract_items_from_line(line, &count);
    if (count == 0) return;
    int comment = 0;
    for (int j = 0; j < count; ++j) {
        if (words[j][0] != *"/" && !comment) {
            word_to_call(words[j]);
            value_to_call(words[j]);
        } else { comment = 1; }
    }

    // store all the variables in a hash table
    counter++;
}

void run_instr() {
    if (calls[counter].instruction == NULL) return;
//    printf("%s %s, %s, %s, %d\n", calls[counter].instruction, calls[counter].var1, calls[counter].var2, calls[counter].var3, calls[counter].value);
    if (strcmp(calls[counter].instruction, "BRANCH") == 0) {
        BRANCH(hash_element(calls[counter].var1), calls[counter].value);
    }
    if (strcmp(calls[counter].instruction, "IADD") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        IADD(hash_element(calls[counter].var1), el3);
    }
    if (strcmp(calls[counter].instruction, "ISUB") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        ISUB(hash_element(calls[counter].var1), el3);
    }
    if (strcmp(calls[counter].instruction, "PADD") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        PADD(hash_element(calls[counter].var1), el3);
    }
    if (strcmp(calls[counter].instruction, "MOD") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        IMOD(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
    }
    if (strcmp(calls[counter].instruction, "EQ") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        EQ(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
    }
    if (strcmp(calls[counter].instruction, "GEQ") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        GEQ(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
    }
    if (strcmp(calls[counter].instruction, "LEQ") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        LEQ(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
    }
    if (strcmp(calls[counter].instruction, "AND") == 0) {
        element_t *el3 = hash_element(calls[counter].var3);
        if (el3 == NULL) el3 = INT(calls[counter].value);
        AND(hash_element(calls[counter].var1), hash_element(calls[counter].var2), el3);
    }
    if (strcmp(calls[counter].instruction, "IF") == 0) {
        IF(hash_element(calls[counter].var1));
    }
}

void execute_assembly() {
    total = counter;
    counter = 0;

    for (int i = 0; i < total; ++i) {
        // create the variables and store in hash table
        element_t *var = NULL;
        if (calls[counter].addon != NULL) var = hash_element(calls[counter].var1);

        // run instructions ------------------------------------

        // call inverse
        if (calls[counter].addon != NULL) if (strcmp(calls[counter].addon, "INV") == 0) INV();

        // run instruction
        run_instr();

        counter++;
    }
}

void ReadAssembly(char *asmb[], int num) {
    for (int i = 0; i < hash_size; ++i) hash_elements[i].integer = NULL;
    for (int i = 0; i < num; ++i) {
        variable_counter = 0;
        // go through every line
        lines_to_call(asmb[i]);
    }
}

void AsmbFromFile() {

    FILE *file = fopen("../assembly.pqsm", "r");
    int line_count = 0;

    size_t capacity = 128; // Initial capacity for the array of lines
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

    execute_assembly();
}
