#pragma once

#include "esphome/core/time.h"
#include "esphome/core/component.h"
#include "esphome/components/i2c/i2c.h"

namespace esphome {
namespace ht33k16 {

class HT33K16Component;

using ht33k16_writer_t = std::function<void(HT33K16Component &)>;

class HT33K16Component : public PollingComponent, public i2c::I2CDevice {
 public:
    enum class blink : uint8_t {OFF=0, HZ_2, HZ_1, HZ_05};

    void set_writer(ht33k16_writer_t &&writer);
    void setup() override;
    void dump_config() override;
    void update() override;
    void display();
    void fill(uint8_t c=0x00);

    void set_enable(bool);
    void set_blink(blink);
    void set_intensity(uint8_t);

    /// Evaluate the printf-format and print the result at position 0.
    uint8_t printf(const char *format, ...) __attribute__((format(printf, 2, 3)));
    /// Print `str` at the given position.
    uint8_t print(uint8_t pos, const char *str);
    /// Print `str` at position 0.
    uint8_t print(const char *str);

 protected:
    void reg_system(bool osc);
    void reg_display(blink b, bool enable);
    void reg_dimming(uint8_t dim);

    bool enabled;
    blink blinking;
    bool reg_display_changed;

    uint8_t intensity_{15};     // Intensity of the display from 0 to 15 (most)
    bool intensity_changed_{true};  // True if we need to re-send the intensity
    uint8_t databuffer[17] = {}; // control byte and 16 display bytes

    uint8_t* buffer_ = databuffer + 1; // pointer to display bytes
    
    optional<ht33k16_writer_t> writer_{};

    enum ErrorCode { NONE = 0, COMMUNICATION_FAILED } error_code_{NONE};
};

}
}