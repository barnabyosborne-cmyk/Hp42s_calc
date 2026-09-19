// board.h -- every pin on the HP-42S clone, in one place.
//
// These are not choices to make here. They come out of elec/src/hp42s.ato and
// are fixed by the schematic; docs/connections.md is the readable version of
// the same table. If a pin moves on the board it moves here, and nowhere else.
#pragma once

#include "driver/gpio.h"

// --- keypad: 6 columns x 7 rows, 37 keys, no diodes ------------------------
// Rows are driven, columns are read. Columns sit on RTC-capable GPIOs so they
// can wake the chip from deep sleep through ext1 with no scanner and no
// standing current; that is most of the battery life.
#define KP_COLS 6
#define KP_ROWS 7

static const gpio_num_t kp_col[KP_COLS] = {
    GPIO_NUM_1, GPIO_NUM_2, GPIO_NUM_4, GPIO_NUM_5, GPIO_NUM_6, GPIO_NUM_7,
};
static const gpio_num_t kp_row[KP_ROWS] = {
    GPIO_NUM_8,  GPIO_NUM_9,  GPIO_NUM_10, GPIO_NUM_11,
    GPIO_NUM_12, GPIO_NUM_13, GPIO_NUM_14,
};

// --- e-paper panel, GDEY0266T90 / SSD1680 ----------------------------------
#define EPD_CS   GPIO_NUM_33
#define EPD_DC   GPIO_NUM_34
#define EPD_RST  GPIO_NUM_35
#define EPD_BUSY GPIO_NUM_36
#define EPD_SCK  GPIO_NUM_37
#define EPD_MOSI GPIO_NUM_38

// --- everything else -------------------------------------------------------
#define PIN_SOUNDER   GPIO_NUM_21   // 1k in series into the piezo element
#define PIN_IR_LED    GPIO_NUM_47   // FET gate, HP-82240 printing
#define PIN_LED_RED   GPIO_NUM_16   // common anode: LOW lights it
#define PIN_LED_GREEN GPIO_NUM_39
#define PIN_I2C_SDA   GPIO_NUM_17   // MAX17048 fuel gauge, 4k7 pull-ups
#define PIN_I2C_SCL   GPIO_NUM_18
#define PIN_CHG_STAT1 GPIO_NUM_48   // BQ25185, open drain, 100k pull-ups
#define PIN_CHG_STAT2 GPIO_NUM_15
#define PIN_BOOT      GPIO_NUM_0    // BOOT button and its test pad

// The status LED is common anode, so it lights on a LOW.
#define LED_ON  0
#define LED_OFF 1
