# keypad.c and epd.c come straight from the real firmware, so the simulation
# tests the code that goes on the board rather than a copy of it.
set(fw ${CMAKE_CURRENT_LIST_DIR}/../../../../firmware/main)

idf_component_register(
    SRCS "sim_main.c" "${fw}/keypad.c" "${fw}/epd.c"
    INCLUDE_DIRS "${fw}"
    REQUIRES driver esp_driver_gpio esp_driver_spi
)

# Moves the panel's CS and DC onto pins the DevKitC-1 brings out. See board.h.
target_compile_definitions(${COMPONENT_LIB} PRIVATE HP42S_WOKWI=1)
