QCC ?= qcc
QNX_VARIANT ?= gcc_ntox86_64
ROOT := ../..
CACHE := $(ROOT)/.local/qfuse-review
BUILD := $(ROOT)/build/qfuse-integration
FLAGS := -V$(QNX_VARIANT) -std=c11 -D_QNX_SOURCE -D_FILE_OFFSET_BITS=64 -Wall -Wextra -Werror -g -O1 -I$(CACHE)/include -I$(CACHE)/libfuse/include -I$(CACHE)/generated
.PHONY: all prepare
all: prepare
	$(MAKE) $(BUILD)/probe
	python3 record_build.py $(QNX_VARIANT)
prepare:
	python3 prepare.py
$(BUILD):
	mkdir -p $@
$(BUILD)/core.o: $(CACHE)/src/core.c sources.lock.json $(wildcard $(CACHE)/include/qfuse/*.h) | $(BUILD)
	$(QCC) $(FLAGS) -c $< -o $@
$(BUILD)/backend.o: $(CACHE)/src/qnx_backend.c sources.lock.json $(wildcard $(CACHE)/src/*.inc) $(wildcard $(CACHE)/include/qfuse/*.h) | $(BUILD)
	$(QCC) $(FLAGS) -c $< -o $@
$(BUILD)/opt.o: $(CACHE)/generated/fuse_opt.c | $(BUILD)
	$(QCC) $(FLAGS) -c $< -o $@
$(BUILD)/log.o: $(CACHE)/libfuse/lib/fuse_log.c | $(BUILD)
	$(QCC) $(FLAGS) -c $< -o $@
$(BUILD)/probe: probe.c $(BUILD)/core.o $(BUILD)/backend.o $(BUILD)/opt.o $(BUILD)/log.o
	$(QCC) $(FLAGS) $^ -o $@
