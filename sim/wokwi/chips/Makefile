# Builds the SSD1680 custom chip for Wokwi.
#
# Needs clang with the wasm32 target, a WASI libc and the wasm32 compiler-rt
# builtins. On Debian or Ubuntu:
#   apt install clang lld wasi-libc libclang-rt-18-dev-wasm32
# With the wasi-sdk instead, point SYSROOT at its share/wasi-sysroot.

SYSROOT ?= /usr
CFLAGS  = --target=wasm32-unknown-wasi --sysroot=$(SYSROOT) \
          -isystem $(SYSROOT)/include/wasm32-wasi -L$(SYSROOT)/lib/wasm32-wasi \
          -O2 -Wall -Werror -Wno-unused-function -nostartfiles \
          -Wl,--import-memory -Wl,--export-table -Wl,--no-entry

ssd1680.chip.wasm: ssd1680.chip.c wokwi-api.h
	clang $(CFLAGS) -o $@ ssd1680.chip.c

clean:
	rm -f ssd1680.chip.wasm
