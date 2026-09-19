// keypad.h -- 37 keys on a 6 x 7 matrix with no diodes.
//
// Key numbers are the calculator core's own ordering, so a scan hands the
// number straight to Plus42. ENTER is two domes wired in parallel and reports
// as one key. Matrix positions come from elec/src/keypad.ato.
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define KEY_NONE 0
#define KEY_MAX  37

// Set up the matrix for scanning: rows are outputs, columns are inputs with
// their pull-ups on.
void keypad_init(void);

// Returns the key held, or KEY_NONE. Debounced. With no diodes, three keys at
// once can alias into a fourth, so only the first key found is reported --
// two-key combinations such as SHIFT plus a key are unambiguous and work.
int keypad_scan(void);

// Waits for every key to come up, so a long press is one event and not a
// stream of them.
void keypad_wait_release(void);

// Arms the matrix as a deep-sleep wake source: every row driven low and held
// through sleep, every column pulled up and watched by ext1 for ANY_LOW. A
// keypress shorts a column to a row and wakes the chip. No scanner IC and no
// standing current, which is where the fifteen months comes from.
void keypad_arm_wake(void);

// Undoes the holds that keypad_arm_wake() left latched. Call it once after
// waking, before scanning again, or the rows stay stuck as they were.
void keypad_release_wake(void);

// Which key woke us, or KEY_NONE if something else did. Reads the ext1 status
// latched by the wake, so it must be called before anything re-drives the
// matrix.
int keypad_wake_key(void);
