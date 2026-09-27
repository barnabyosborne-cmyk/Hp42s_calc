# The Wokwi test firmware: firmware/main/keypad.c and epd.c, unmodified, under
# a small app that reports every key on the serial port. Built separately from
# the calculator so a simulation run needs neither Plus42 nor the decimal
# library.
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(hp42s_sim)
