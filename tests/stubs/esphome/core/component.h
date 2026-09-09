#pragma once
// Host-side stub of esphome/core/component.h, just enough of the API surface
// for ht33k16.cpp to compile and run off-target under a unit test.

#include <cstdarg>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <optional>
#include <sys/types.h>  // u_int8_t, as used by ht33k16.cpp

namespace esphome {

template<typename T> using optional = std::optional<T>;

class Component {
 public:
  virtual ~Component() = default;
  virtual void setup() {}
  virtual void loop() {}
  virtual void dump_config() {}
  virtual float get_setup_priority() const { return 0.0f; }
};

class PollingComponent : public Component {
 public:
  PollingComponent() = default;
  explicit PollingComponent(uint32_t update_interval) : update_interval_(update_interval) {}

  virtual void update() = 0;

  uint32_t get_update_interval() const { return this->update_interval_; }
  void set_update_interval(uint32_t update_interval) { this->update_interval_ = update_interval; }

 protected:
  uint32_t update_interval_{60000};
};

}  // namespace esphome
