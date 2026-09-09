# Builds the ht33k16 driver for the host so it can be unit tested from Python.
#
#   libht33k16.a       - the driver itself, compiled against the stub headers
#   libht33k16_test.so - that archive plus the ctypes shim and the i2c fake
#
# Run `make` here, or just run pytest (conftest.py invokes this Makefile).

CXX ?= g++
COMPONENT_DIR := ../components/ht33k16
BUILD_DIR := build

CXXFLAGS := -std=c++17 -g -O0 -fPIC -Wall -Wextra -Wno-unused-parameter \
            -I$(COMPONENT_DIR) -Istubs
LDFLAGS := -shared

LIB := $(BUILD_DIR)/libht33k16.a
SO := $(BUILD_DIR)/libht33k16_test.so

LIB_OBJS := $(BUILD_DIR)/ht33k16.o
SO_OBJS := $(BUILD_DIR)/shim.o $(BUILD_DIR)/i2c_stub.o

.PHONY: all clean
all: $(SO)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/ht33k16.o: $(COMPONENT_DIR)/ht33k16.cpp $(COMPONENT_DIR)/ht33k16.h | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(BUILD_DIR)/shim.o: shim.cpp $(COMPONENT_DIR)/ht33k16.h | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(BUILD_DIR)/i2c_stub.o: stubs/i2c_stub.cpp stubs/esphome/components/i2c/i2c.h | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(LIB): $(LIB_OBJS)
	$(AR) rcs $@ $^

$(SO): $(SO_OBJS) $(LIB)
	$(CXX) $(LDFLAGS) -o $@ $(SO_OBJS) -Wl,--whole-archive $(LIB) -Wl,--no-whole-archive

clean:
	rm -rf $(BUILD_DIR)
