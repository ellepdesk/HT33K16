#pragma once
// Host-side stub of esphome/core/hal.h.

#include <cstdint>

namespace esphome {

inline uint32_t millis() { return 0; }
inline uint32_t micros() { return 0; }
inline void delay(uint32_t ms) { (void) ms; }

}  // namespace esphome
