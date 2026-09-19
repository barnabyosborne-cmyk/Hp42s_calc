idf_component_register(
  SRCS
    core_commands1.cc
    core_commands2.cc
    core_commands3.cc
    core_commands4.cc
    core_commands5.cc
    core_commands6.cc
    core_commands7.cc
    core_commands8.cc
    core_commands9.cc
    core_commandsa.cc
    core_display.cc
    core_equations.cc
    core_globals.cc
    core_helpers.cc
    core_keydown.cc
    core_linalg1.cc
    core_linalg2.cc
    core_main.cc
    core_math1.cc
    core_math2.cc
    core_parser.cc
    core_phloat.cc
    core_sto_rcl.cc
    core_tables.cc
    core_variables.cc
    shell_spool.cc
  INCLUDE_DIRS "."
  REQUIRES libbid
)

target_compile_definitions(${COMPONENT_LIB} PRIVATE
  BCD_MATH=1
  VERSION="1.3.15"
  VERSION_PLATFORM="ESP32-S3"
  DECIMAL_CALL_BY_REFERENCE=1
  DECIMAL_GLOBAL_ROUNDING=1
  DECIMAL_GLOBAL_ROUNDING_ACCESS_FUNCTIONS=1
  DECIMAL_GLOBAL_EXCEPTION_FLAGS=1
  DECIMAL_GLOBAL_EXCEPTION_FLAGS_ACCESS_FUNCTIONS=1
)

target_compile_options(${COMPONENT_LIB} PRIVATE
  -include fenv.h -fno-rtti
  -Wno-parentheses -Wno-sign-compare -Wno-format-truncation
  -Wno-unknown-pragmas -Wno-error=all -Wno-error=extra -w
)
