#pragma once
// Host-side stub of esphome/components/i2c/i2c.h.
//
// I2CDevice::write() does not touch a bus; it appends the transaction to a
// global log that the test shim can read back. That is what lets the tests
// assert on the exact register bytes the component puts on the wire.

#include <cstddef>
#include <cstdint>
#include <vector>

namespace esphome {
namespace i2c {

enum ErrorCode {
  NO_ERROR = 0,
  ERROR_OK = 0,
  ERROR_INVALID_ARGUMENT = 1,
  ERROR_NOT_ACKNOWLEDGED = 2,
  ERROR_TIMEOUT = 3,
  ERROR_NOT_INITIALIZED = 4,
  ERROR_TOO_LARGE = 5,
  ERROR_UNKNOWN = 6,
  ERROR_CRC = 7,
};

struct Transaction {
  uint8_t address;
  std::vector<uint8_t> data;
};

/// Every write() performed by any I2CDevice, in order.
std::vector<Transaction> &transaction_log();

class I2CDevice {
 public:
  virtual ~I2CDevice() = default;

  void set_i2c_address(uint8_t address) { this->address_ = address; }
  uint8_t get_i2c_address() const { return this->address_; }

  ErrorCode write(const uint8_t *data, size_t len, bool stop = true);

 protected:
  uint8_t address_{0x00};
};

}  // namespace i2c
}  // namespace esphome
