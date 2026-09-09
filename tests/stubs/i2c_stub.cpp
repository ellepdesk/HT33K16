#include "esphome/components/i2c/i2c.h"

namespace esphome {
namespace i2c {

std::vector<Transaction> &transaction_log() {
  static std::vector<Transaction> log;
  return log;
}

ErrorCode I2CDevice::write(const uint8_t *data, size_t len, bool stop) {
  (void) stop;
  transaction_log().push_back(Transaction{this->address_, std::vector<uint8_t>(data, data + len)});
  return ERROR_OK;
}

}  // namespace i2c
}  // namespace esphome
