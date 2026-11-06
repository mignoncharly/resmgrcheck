QCC ?= qcc
QNX_VARIANT ?= gcc_ntox86_64
BUILD_DIR := build/qnx-x86_64
SMOKE := $(BUILD_DIR)/hello

.PHONY: all qnx
all: qnx

qnx: $(SMOKE)

$(SMOKE): native/spikes/hello.c Makefile | $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR):
	mkdir -p "$@"

