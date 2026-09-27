# The calculator in Wokwi: Plus42 and the real shell, keypad and panel code
# from firmware/, under a small loop that logs the X register after every key.
# Built with HP42S_WOKWI for the DevKitC-1's pins, like ../firmware.
cmake_minimum_required(VERSION 3.16)
set(EXTRA_COMPONENT_DIRS ${CMAKE_CURRENT_LIST_DIR}/../../../firmware/components)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(hp42s_calc)
