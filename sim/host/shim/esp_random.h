// Host stand-in for ESP-IDF's esp_random.h, for sim/host.
#pragma once
#include <stdint.h>
uint32_t esp_random(void);
