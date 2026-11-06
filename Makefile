QCC ?= qcc
QNX_VARIANT ?= gcc_ntox86_64
BUILD_DIR := build/qnx-x86_64
SMOKE := $(BUILD_DIR)/hello
CAPABILITIES := $(BUILD_DIR)/capabilities

.PHONY: all qnx check-qnx
all: qnx

qnx: $(SMOKE) $(CAPABILITIES)

check-qnx:
	python3 scripts/check-qnx-build.py

$(SMOKE): native/spikes/hello.c Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(CAPABILITIES): native/spikes/capabilities.c Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR):
	mkdir -p "$@"

