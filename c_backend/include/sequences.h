//
// sequences.h - Hardcoded gate sequences for common quantum operations
//
// This module provides pre-computed static gate sequences for arithmetic
// operations up to 8-bit width. These avoid runtime allocation overhead
// for the most common integer sizes.
//
// PUBLIC API:
//   get_hardcoded_QQ_add(bits)  - Returns static QQ_add sequence or NULL
//   get_hardcoded_cQQ_add(bits) - Returns static cQQ_add sequence or NULL
//
// These functions return NULL for widths > HARDCODED_MAX_WIDTH (8).
// Caller must fall back to dynamic generation (QQ_add(), cQQ_add()) for NULL returns.
//
// IMPLEMENTATION:
//   - Public functions are implemented in add_seq_5_8.c (unified dispatch)
//   - Static helpers _1_4 are implemented in add_seq_1_4.c
//   - Static helpers _5_8 are implemented in add_seq_5_8.c
//

#ifndef QUANTUM_SEQUENCES_H
#define QUANTUM_SEQUENCES_H

#include "types.h"

// Maximum width for which hardcoded sequences are available
#define HARDCODED_MAX_WIDTH 8

// ======================================================
// PUBLIC API - Use these functions
// ======================================================

// Returns pre-computed QQ_add sequence for given bit width
// Returns NULL if bits > HARDCODED_MAX_WIDTH or bits < 1
const sequence_t *get_hardcoded_QQ_add(int bits);

// Returns pre-computed cQQ_add (controlled QQ_add) sequence for given bit width
// Returns NULL if bits > HARDCODED_MAX_WIDTH or bits < 1
const sequence_t *get_hardcoded_cQQ_add(int bits);

// ======================================================
// INTERNAL HELPERS - Called by public API
// ======================================================

// Dispatch helpers for 1-4 bit widths (implemented in add_seq_1_4.c)
const sequence_t *get_hardcoded_QQ_add_1_4(int bits);
const sequence_t *get_hardcoded_cQQ_add_1_4(int bits);

// Dispatch helpers for 5-8 bit widths (implemented in add_seq_5_8.c)
const sequence_t *get_hardcoded_QQ_add_5_8(int bits);
const sequence_t *get_hardcoded_cQQ_add_5_8(int bits);

#endif // QUANTUM_SEQUENCES_H
