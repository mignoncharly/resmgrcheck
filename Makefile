QCC ?= qcc
QNX_VARIANT ?= gcc_ntox86_64
BUILD_DIR := build/qnx-x86_64
SMOKE := $(BUILD_DIR)/hello
CAPABILITIES := $(BUILD_DIR)/capabilities
PHASE2 := $(BUILD_DIR)/sensor-fixture $(BUILD_DIR)/sensor-client $(BUILD_DIR)/phase2-supervisor

.PHONY: all qnx check-qnx
all: qnx

qnx: $(SMOKE) $(CAPABILITIES) $(PHASE2)

check-qnx:
	python3 scripts/check-qnx-build.py

$(SMOKE): native/spikes/hello.c Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(CAPABILITIES): native/spikes/capabilities.c Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR)/sensor-fixture: native/fixtures/sensor.c native/spikes/phase2.h Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR)/sensor-client: native/spikes/sensor_client.c native/spikes/phase2.h Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR)/phase2-supervisor: native/spikes/phase2_supervisor.c native/spikes/phase2.h Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR):
	mkdir -p "$@"

