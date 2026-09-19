idf_component_register(
    SRCS "main.c" "epd.c" "keypad.c" "bidtest.c" "shell.cc"
    INCLUDE_DIRS "."
    REQUIRES libbid plus42core driver esp_driver_gpio esp_driver_spi esp_timer
)

target_compile_definitions(${COMPONENT_LIB} PRIVATE
  BCD_MATH=1
  DECIMAL_CALL_BY_REFERENCE=1
  DECIMAL_GLOBAL_ROUNDING=1
  DECIMAL_GLOBAL_ROUNDING_ACCESS_FUNCTIONS=1
  DECIMAL_GLOBAL_EXCEPTION_FLAGS=1
  DECIMAL_GLOBAL_EXCEPTION_FLAGS_ACCESS_FUNCTIONS=1
)

target_compile_options(${COMPONENT_LIB} PRIVATE -include fenv.h -Wno-error=all -w)
