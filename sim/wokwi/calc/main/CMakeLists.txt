set(fw ${CMAKE_CURRENT_LIST_DIR}/../../../../firmware/main)

idf_component_register(
    SRCS "calc_main.c" "${fw}/keypad.c" "${fw}/epd.c" "${fw}/shell.cc"
    INCLUDE_DIRS "${fw}"
    REQUIRES libbid plus42core driver esp_driver_gpio esp_driver_spi esp_timer
)

# The same flags firmware/main builds shell.cc with; see its CMakeLists.txt.
target_compile_definitions(${COMPONENT_LIB} PRIVATE
  HP42S_WOKWI=1
  BCD_MATH=1
  DECIMAL_CALL_BY_REFERENCE=1
  DECIMAL_GLOBAL_ROUNDING=1
  DECIMAL_GLOBAL_ROUNDING_ACCESS_FUNCTIONS=1
  DECIMAL_GLOBAL_EXCEPTION_FLAGS=1
  DECIMAL_GLOBAL_EXCEPTION_FLAGS_ACCESS_FUNCTIONS=1
)
target_compile_options(${COMPONENT_LIB} PRIVATE -include fenv.h -Wno-error=all -w)
