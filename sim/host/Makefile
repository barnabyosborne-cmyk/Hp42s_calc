# Builds Plus42 and firmware/main/shell.cc for this computer, with a stand-in
# panel that writes each update as a picture. See host_main.cc.
#
#   bash ../../firmware/vendor/setup.sh   # once, lays out Intel's library
#   make                                  # builds $(BUILD)/hp42s_host
#   make frames KEYS="2 ENTER 3 ADD"      # runs it, then frames.py
#
# Builds outside the repo by default, because the project folder is mounted
# noexec and cannot take a thousand small writes quickly.

FW     ?= $(abspath ../../firmware)
BUILD  ?= /tmp/hp42s-host
OUT    ?= $(BUILD)/frames
KEYS   ?= 2 ENTER 3 ADD
CC     ?= cc
CXX    ?= c++

# Same decimal flags as the firmware (DECIMAL_* must agree on both sides), but
# efi2 rather than ia32: that is Intel's name for 64-bit x86.
DEC = -DDECIMAL_CALL_BY_REFERENCE=1 -DDECIMAL_GLOBAL_ROUNDING=1 \
      -DDECIMAL_GLOBAL_ROUNDING_ACCESS_FUNCTIONS=1 \
      -DDECIMAL_GLOBAL_EXCEPTION_FLAGS=1 \
      -DDECIMAL_GLOBAL_EXCEPTION_FLAGS_ACCESS_FUNCTIONS=1
BIDFLAGS  = -O1 -w -include fenv.h -DUSE_COMPILER_F128_TYPE=0 \
            -DUSE_COMPILER_F80_TYPE=0 -DUSE_NATIVE_QUAD_TYPE=0 \
            -DLINUX -Dlinux -Dgcc -Defi2 $(DEC) -I$(FW)/components/libbid/src \
            -I$(FW)/components/libbid/float128
COREFLAGS = -O1 -w -include fenv.h -DBCD_MATH=1 -DVERSION='"1.3.15"' \
            -DVERSION_PLATFORM='"host"' $(DEC) -I$(FW)/components/plus42core
MAINFLAGS = $(COREFLAGS) -I$(FW)/main -Ishim

# The source lists are the firmware's own, read out of its CMakeLists.txt.
srcs = $(shell grep -E '^[[:space:]]+[A-Za-z0-9_/.]+[.]cc?[[:space:]]*$$' $(1)/CMakeLists.txt)
BID_SRC  = $(call srcs,$(FW)/components/libbid)
CORE_SRC = $(call srcs,$(FW)/components/plus42core)
BID_OBJ  = $(patsubst %.c,$(BUILD)/bid/%.o,$(BID_SRC))
CORE_OBJ = $(patsubst %.cc,$(BUILD)/core/%.o,$(CORE_SRC))

$(BUILD)/hp42s_host: $(BID_OBJ) $(CORE_OBJ) $(BUILD)/shell.o $(BUILD)/host_main.o
	$(CXX) -o $@ $^ -lm

$(BUILD)/bid/%.o: $(FW)/components/libbid/%.c
	@mkdir -p $(dir $@)
	$(CC) $(BIDFLAGS) -c $< -o $@

$(BUILD)/core/%.o: $(FW)/components/plus42core/%.cc
	@mkdir -p $(dir $@)
	$(CXX) $(COREFLAGS) -c $< -o $@

$(BUILD)/shell.o: $(FW)/main/shell.cc
	@mkdir -p $(BUILD)
	$(CXX) $(MAINFLAGS) -c $< -o $@

$(BUILD)/host_main.o: host_main.cc
	@mkdir -p $(BUILD)
	$(CXX) $(MAINFLAGS) -c $< -o $@

frames: $(BUILD)/hp42s_host
	rm -rf $(OUT) && mkdir -p $(OUT)
	$(BUILD)/hp42s_host $(OUT) $(KEYS)
	python3 frames.py $(OUT)

.PHONY: frames
