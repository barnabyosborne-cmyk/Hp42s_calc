// Host stand-in for ESP-IDF's esp_timer.h, for sim/host.
#pragma once
#include <stdint.h>
int64_t esp_timer_get_time(void);
