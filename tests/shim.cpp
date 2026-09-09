// extern "C" shim around HT33K16Component so the driver can be driven from
// Python via ctypes. Nothing here is part of the firmware build.

#include "ht33k16.h"
#include "esphome/components/i2c/i2c.h"

#include <cstring>
#include <string>
#include <vector>

namespace esphome {
namespace ht33k16 {
// Free helpers defined in ht33k16.cpp but not declared in the header.
void set_bit(uint8_t *buffer, uint8_t row, uint8_t col, bool bit);
void set_col(uint8_t *buffer, uint8_t col, uint8_t data);
void set_row(uint8_t *buffer, uint8_t row, uint16_t data);
uint8_t char_to_seg7(uint8_t c);
uint8_t map_position(uint8_t pos);
}  // namespace ht33k16
}  // namespace esphome

using esphome::ht33k16::HT33K16Component;

namespace {

/// Subclass purely to widen access to the protected state the tests inspect.
class Harness : public HT33K16Component {
 public:
  const uint8_t *databuffer_ptr() const { return this->databuffer; }
  uint8_t intensity() const { return this->intensity_; }
  uint8_t digits() const { return this->digits_; }
  bool intensity_changed() const { return this->intensity_changed_; }
  bool enabled_flag() const { return this->enabled; }
  uint8_t blink_mode() const { return static_cast<uint8_t>(this->blinking); }
  bool display_reg_dirty() const { return this->reg_display_changed; }

  using HT33K16Component::reg_display;
  using HT33K16Component::reg_dimming;
  using HT33K16Component::reg_system;
};

}  // namespace

extern "C" {

// --- lifecycle ---------------------------------------------------------

void *ht_new(uint8_t address) {
  auto *h = new Harness();
  h->set_i2c_address(address);
  return h;
}

void ht_free(void *handle) { delete static_cast<Harness *>(handle); }

// --- component API -----------------------------------------------------

void ht_setup(void *handle) { static_cast<Harness *>(handle)->setup(); }
void ht_update(void *handle) { static_cast<Harness *>(handle)->update(); }
void ht_display(void *handle) { static_cast<Harness *>(handle)->display(); }
void ht_dump_config(void *handle) { static_cast<Harness *>(handle)->dump_config(); }
void ht_fill(void *handle, uint8_t c) { static_cast<Harness *>(handle)->fill(c); }

void ht_set_intensity(void *handle, uint8_t dim) { static_cast<Harness *>(handle)->set_intensity(dim); }
void ht_set_digits(void *handle, uint8_t digits) { static_cast<Harness *>(handle)->set_digits(digits); }
uint8_t ht_get_digits(void *handle) { return static_cast<Harness *>(handle)->digits(); }
void ht_set_enable(void *handle, bool enable) { static_cast<Harness *>(handle)->set_enable(enable); }
void ht_set_blink(void *handle, uint8_t b) {
  static_cast<Harness *>(handle)->set_blink(static_cast<HT33K16Component::blink>(b));
}

uint8_t ht_print_at(void *handle, uint8_t pos, const char *str) {
  return static_cast<Harness *>(handle)->print(pos, str);
}

uint8_t ht_print(void *handle, const char *str) { return static_cast<Harness *>(handle)->print(str); }

/// printf() with a fixed arity of three ints, enough to exercise the
/// "%3i.c%2i:%02i" style formats the YAML configs use.
uint8_t ht_printf3i(void *handle, const char *format, int a, int b, int c) {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
#pragma GCC diagnostic ignored "-Wformat-security"
  return static_cast<Harness *>(handle)->printf(format, a, b, c);
#pragma GCC diagnostic pop
}

// --- register writes (protected on the component) ----------------------

void ht_reg_system(void *handle, bool osc) { static_cast<Harness *>(handle)->reg_system(osc); }
void ht_reg_display(void *handle, uint8_t b, bool enable) {
  static_cast<Harness *>(handle)->reg_display(static_cast<HT33K16Component::blink>(b), enable);
}
void ht_reg_dimming(void *handle, uint8_t dim) { static_cast<Harness *>(handle)->reg_dimming(dim); }

// --- state inspection --------------------------------------------------

/// Copies the full 17-byte transfer (control byte + 16 display bytes).
void ht_get_databuffer(void *handle, uint8_t *out) {
  memcpy(out, static_cast<Harness *>(handle)->databuffer_ptr(), 17);
}

uint8_t ht_get_intensity(void *handle) { return static_cast<Harness *>(handle)->intensity(); }
bool ht_get_intensity_changed(void *handle) { return static_cast<Harness *>(handle)->intensity_changed(); }
bool ht_get_enabled(void *handle) { return static_cast<Harness *>(handle)->enabled_flag(); }
uint8_t ht_get_blink(void *handle) { return static_cast<Harness *>(handle)->blink_mode(); }
bool ht_get_display_reg_dirty(void *handle) { return static_cast<Harness *>(handle)->display_reg_dirty(); }

// --- free buffer helpers ----------------------------------------------

void ht_set_bit(uint8_t *buffer, uint8_t row, uint8_t col, bool bit) {
  esphome::ht33k16::set_bit(buffer, row, col, bit);
}
void ht_set_col(uint8_t *buffer, uint8_t col, uint8_t data) { esphome::ht33k16::set_col(buffer, col, data); }
void ht_set_row(uint8_t *buffer, uint8_t row, uint16_t data) { esphome::ht33k16::set_row(buffer, row, data); }
uint8_t ht_char_to_seg7(uint8_t c) { return esphome::ht33k16::char_to_seg7(c); }
uint8_t ht_map_position(uint8_t pos) { return esphome::ht33k16::map_position(pos); }
uint8_t ht_display_positions() { return HT33K16Component::DISPLAY_POSITIONS; }

// --- captured i2c traffic ---------------------------------------------

void ht_i2c_clear() { esphome::i2c::transaction_log().clear(); }

int ht_i2c_count() { return static_cast<int>(esphome::i2c::transaction_log().size()); }

int ht_i2c_address(int index) {
  auto &log = esphome::i2c::transaction_log();
  if (index < 0 || index >= static_cast<int>(log.size()))
    return -1;
  return log[index].address;
}

/// Writes up to max_len bytes of transaction `index` into out.
/// Returns the transaction's real length, or -1 if the index is out of range.
int ht_i2c_data(int index, uint8_t *out, int max_len) {
  auto &log = esphome::i2c::transaction_log();
  if (index < 0 || index >= static_cast<int>(log.size()))
    return -1;
  const auto &data = log[index].data;
  int n = static_cast<int>(data.size());
  if (max_len < n)
    n = max_len;
  memcpy(out, data.data(), n);
  return static_cast<int>(data.size());
}

}  // extern "C"
