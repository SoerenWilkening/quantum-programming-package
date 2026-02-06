//
// sequences.h - Hardcoded gate sequences for common quantum operations
//
// This module provides pre-computed static gate sequences for arithmetic
// operations up to 16-bit width. These avoid runtime allocation overhead
// for the most common integer sizes.
//
// Four addition variants are supported:
//   QQ_add  - Quantum-quantum addition (static const sequence)
//   cQQ_add - Controlled quantum-quantum addition (static const sequence)
//   CQ_add  - Classical-quantum addition (template-init, angles injected at runtime)
//   cCQ_add - Controlled classical-quantum addition (template-init, angles injected at runtime)
//
// PUBLIC API:
//   get_hardcoded_QQ_add(bits)  - Returns static QQ_add sequence or NULL
//   get_hardcoded_cQQ_add(bits) - Returns static cQQ_add sequence or NULL
//   get_hardcoded_CQ_add(bits)  - Returns template CQ_add sequence or NULL
//   get_hardcoded_cCQ_add(bits) - Returns template cCQ_add sequence or NULL
//
// These functions return NULL for widths > HARDCODED_MAX_WIDTH (16).
// Caller must fall back to dynamic generation for NULL returns.
//
// IMPLEMENTATION:
//   - Per-width files: add_seq_N.c (N=1..16), conditionally compiled via #ifdef SEQ_WIDTH_N
//   - Unified dispatch: add_seq_dispatch.c routes to per-width implementations
//   - Define SEQ_NO_WIDTH_N before including this header to disable width N
//

#ifndef QUANTUM_SEQUENCES_H
#define QUANTUM_SEQUENCES_H

#include "types.h"

// ======================================================
// PREPROCESSOR GUARDS - All widths enabled by default
// Define SEQ_NO_WIDTH_N before including to disable width N
// ======================================================

#ifndef SEQ_NO_WIDTH_1
#define SEQ_WIDTH_1
#endif
#ifndef SEQ_NO_WIDTH_2
#define SEQ_WIDTH_2
#endif
#ifndef SEQ_NO_WIDTH_3
#define SEQ_WIDTH_3
#endif
#ifndef SEQ_NO_WIDTH_4
#define SEQ_WIDTH_4
#endif
#ifndef SEQ_NO_WIDTH_5
#define SEQ_WIDTH_5
#endif
#ifndef SEQ_NO_WIDTH_6
#define SEQ_WIDTH_6
#endif
#ifndef SEQ_NO_WIDTH_7
#define SEQ_WIDTH_7
#endif
#ifndef SEQ_NO_WIDTH_8
#define SEQ_WIDTH_8
#endif
#ifndef SEQ_NO_WIDTH_9
#define SEQ_WIDTH_9
#endif
#ifndef SEQ_NO_WIDTH_10
#define SEQ_WIDTH_10
#endif
#ifndef SEQ_NO_WIDTH_11
#define SEQ_WIDTH_11
#endif
#ifndef SEQ_NO_WIDTH_12
#define SEQ_WIDTH_12
#endif
#ifndef SEQ_NO_WIDTH_13
#define SEQ_WIDTH_13
#endif
#ifndef SEQ_NO_WIDTH_14
#define SEQ_WIDTH_14
#endif
#ifndef SEQ_NO_WIDTH_15
#define SEQ_WIDTH_15
#endif
#ifndef SEQ_NO_WIDTH_16
#define SEQ_WIDTH_16
#endif

// Maximum width for which hardcoded sequences are available
#define HARDCODED_MAX_WIDTH 16

// ======================================================
// PUBLIC API - 4 dispatch functions
// ======================================================

// Returns pre-computed QQ_add sequence for given bit width
// Returns NULL if bits > HARDCODED_MAX_WIDTH or bits < 1
const sequence_t *get_hardcoded_QQ_add(int bits);

// Returns pre-computed cQQ_add (controlled QQ_add) sequence for given bit width
// Returns NULL if bits > HARDCODED_MAX_WIDTH or bits < 1
const sequence_t *get_hardcoded_cQQ_add(int bits);

// Returns template CQ_add sequence for given bit width (mutable for angle injection)
// Returns NULL if bits > HARDCODED_MAX_WIDTH or bits < 1
sequence_t *get_hardcoded_CQ_add(int bits);

// Returns template cCQ_add sequence for given bit width (mutable for angle injection)
// Returns NULL if bits > HARDCODED_MAX_WIDTH or bits < 1
sequence_t *get_hardcoded_cCQ_add(int bits);

#endif // QUANTUM_SEQUENCES_H
