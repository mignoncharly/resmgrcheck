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

$(BUILD_DIR)/sensor-fixture: native/fixtures/sensor.c native/spikes/phase2.h $(wildcard native/fixtures/*.h) Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR)/sensor-client: native/spikes/sensor_client.c native/spikes/phase2.h Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR)/phase2-supervisor: native/spikes/phase2_supervisor.c native/spikes/phase2.h Makefile | check-qnx $(BUILD_DIR)
	$(QCC) -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror "$<" -o "$@"

$(BUILD_DIR):
	mkdir -p "$@"


# Phase 3 generic execution path; the Phase 2 spike remains a regression reference.
V1_COMMON := native/common/event.c native/common/plan.c native/common/result.c native/common/persistence.c native/common/lab.c native/common/journal.c native/common/process.c native/common/protocol.c third_party/cjson/cJSON.c
V1_ADAPTERS := $(wildcard native/adapters/*.c)
V1_FLAGS := -V$(QNX_VARIANT) -std=c11 -Wall -Wextra -Werror -DRMC_EVENT_V1 -DCJSON_NESTING_LIMIT=12 -Ithird_party/cjson
V1_HEADERS := $(wildcard native/common/*.h native/fixtures/*.h native/adapters/*.h) native/adapter_v1.h native/spikes/phase2.h third_party/cjson/cJSON.h
qnx: $(BUILD_DIR)/runner $(BUILD_DIR)/worker $(BUILD_DIR)/sensor-v1-fixture $(BUILD_DIR)/job-v1-fixture $(BUILD_DIR)/targetctl
qnx: $(BUILD_DIR)/mailbox-v1-fixture

$(BUILD_DIR)/targetctl: native/targetctl.c $(V1_COMMON) $(V1_ADAPTERS) $(V1_HEADERS) Makefile | check-qnx $(BUILD_DIR)
	$(QCC) $(V1_FLAGS) $< $(V1_COMMON) $(V1_ADAPTERS) -lm -o $@

$(BUILD_DIR)/runner: native/runner.c $(V1_COMMON) $(V1_ADAPTERS) $(V1_HEADERS) Makefile | check-qnx $(BUILD_DIR)
	$(QCC) $(V1_FLAGS) $< $(V1_COMMON) $(V1_ADAPTERS) -lm -o $@

$(BUILD_DIR)/worker: native/worker.c $(V1_COMMON) $(V1_ADAPTERS) $(V1_HEADERS) Makefile | check-qnx $(BUILD_DIR)
	$(QCC) $(V1_FLAGS) $< $(V1_COMMON) $(V1_ADAPTERS) -lm -o $@

$(BUILD_DIR)/sensor-v1-fixture: native/fixtures/sensor.c native/common/event.c third_party/cjson/cJSON.c $(V1_HEADERS) Makefile | check-qnx $(BUILD_DIR)
	$(QCC) $(V1_FLAGS) $< native/common/event.c third_party/cjson/cJSON.c -lm -o $@

$(BUILD_DIR)/job-v1-fixture: native/fixtures/job.c native/common/event.c third_party/cjson/cJSON.c $(V1_HEADERS) Makefile | check-qnx $(BUILD_DIR)
	$(QCC) $(V1_FLAGS) $< native/common/event.c third_party/cjson/cJSON.c -lm -o $@

$(BUILD_DIR)/mailbox-v1-fixture: native/fixtures/mailbox.c native/common/event.c third_party/cjson/cJSON.c $(V1_HEADERS) Makefile | check-qnx $(BUILD_DIR)
	$(QCC) $(V1_FLAGS) $< native/common/event.c third_party/cjson/cJSON.c -lm -o $@

qnx:
	python3 scripts/record-build.py
