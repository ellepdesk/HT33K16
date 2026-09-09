#pragma once
// Host-side stub of esphome/core/helpers.h.

#include <cstdint>
#include <string>

namespace esphome {

template<typename T> constexpr const T &clamp(const T &v, const T &lo, const T &hi) {
  return v < lo ? lo : (hi < v ? hi : v);
}

}  // namespace esphome
