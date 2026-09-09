#pragma once
// Host-side stub of esphome/core/time.h.

#include <cstdint>
#include <ctime>

namespace esphome {

struct ESPTime {
  uint8_t second;
  uint8_t minute;
  uint8_t hour;
  uint8_t day_of_week;
  uint16_t day_of_year;
  uint8_t day_of_month;
  uint8_t month;
  uint16_t year;
  bool is_dst;
  time_t timestamp;

  bool is_valid() const { return this->year >= 2019; }
};

}  // namespace esphome
