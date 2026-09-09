#include "ht33k16.h"
#include "esphome/core/hal.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

namespace esphome {
namespace ht33k16 {

    static const char *const TAG = "HT33k16";

    void _set_bit(uint8_t *buffer, uint8_t pos, bool bit){
        if (bit){
            *buffer |= 1 << pos;
        }
        else {
            *buffer &= ~(1 << pos);
        }
    }

    void set_bit(uint8_t *buffer, uint8_t row, uint8_t col, bool bit){
        if (col >= 8)
            _set_bit(buffer+(row * 2 + 1), col - 8, bit);
        else {
            _set_bit(buffer+(row * 2), col, bit);
        }
    }

    void set_col(uint8_t *buffer, uint8_t col, uint8_t data){
        for (uint8_t i = 0 ; i < 8; i++){
            bool bit = (data >> i) & 0x01;
            set_bit(buffer, i, col, bit);
        }
    }

    void set_row(uint8_t* buffer, uint8_t row, uint16_t data){
        uint8_t d_high = data >> 8;
        uint8_t d_low = data & 0xFF;
        buffer[row * 2] = d_low;
        buffer[row * 2 + 1] = d_high;
    }

    // Physical digit order. The panel is built from two banks of four digits,
    // with the left-hand bank wired to ROW4-7 and the right-hand bank to
    // ROW0-3, so writing position 0 straight through would land it halfway
    // across the display. DIGIT_MAP[n] is the ROW output driving the n-th
    // digit counted from the left.
    static const uint8_t DIGIT_MAP[HT33K16Component::DISPLAY_POSITIONS] = {
         4,  5,  6,  7,  0,  1,  2,  3,
        12, 13, 14, 15,  8,  9, 10, 11,
    };

    uint8_t map_position(uint8_t pos){
        if (pos >= HT33K16Component::DISPLAY_POSITIONS)
            return pos;
        return DIGIT_MAP[pos];
    }

    uint8_t char_to_seg7(uint8_t c){
        switch (c){
            case '0':
                return 0b00111111;
            case '1':
                return 0b00000110;   //  1
            case '2':
                return 0b01011011;   //  2
            case '3':
                return 0b01001111;   //  3
            case '4':
                return 0b01100110;   //  4
            case '5':
                return 0b01101101;   //  5
            case '6':
                return 0b01111101;   //  6
            case '7':
                return 0b00000111;   //  7
            case '8':
                return 0b01111111;   //  8
            case '9':
                return 0b01101111;   //  9

            case '-':
                return 0b01000000;
            case '~': // placeholder for degree
                return 0b01100011;
            case 'c': // 'high' c, for degrees celcius
                return 0b01100001;
            case 'f':
                return 0b01110001;
            default:
                return 0b00000000;
        }
    }

    void HT33K16Component::setup() {
        fill(0x00);
        reg_system(true);
        reg_display(blinking, enabled);
        update();
    }

    void HT33K16Component::set_digits(uint8_t digits){
        if (digits == 0 || digits > DISPLAY_POSITIONS) {
            ESP_LOGW(TAG, "digits %u out of range, clamping to %u", digits, DISPLAY_POSITIONS);
            digits = DISPLAY_POSITIONS;
        }
        digits_ = digits;
    }

    void HT33K16Component::set_intensity(uint8_t dim){
        if (intensity_ != dim)
        {
            intensity_ = dim;
            intensity_changed_ = true;
        }
    }


    void HT33K16Component::update() {
        if (this->writer_.has_value())  // run lambda
            (*this->writer_)(*this);
        if (intensity_changed_)
            reg_dimming(intensity_);
        if (reg_display_changed)
            reg_display(blinking, enabled);
        this->display();
    }

    void HT33K16Component::set_enable(bool enable){
        enabled = enable;
        reg_display_changed = true;
    }

    void HT33K16Component::set_blink(blink b){
        if (blinking != b) {
            blinking = b;
            reg_display_changed = true;
        }
    }

    void HT33K16Component::fill(uint8_t c){
        for (int i = 0; i< 16 ;i++ )
            set_col(buffer_, i, c);
    }

    void HT33K16Component::display(){
        // write buffer to i2c
        write(databuffer, 17);
    }

    void HT33K16Component::reg_system(bool osc){
        u_int8_t data[] = {uint8_t(0x20 |  (osc & 0x01))};
        write(data, 1);
    }

    void HT33K16Component::reg_display(blink b, bool enable){
        u_int8_t data[] = {uint8_t(0x80 | (uint8_t(b)<< 1)| (enable))};
        reg_display_changed = false;
        write(data, 1);
    }

    void HT33K16Component::reg_dimming(uint8_t dim){
        u_int8_t data[] = {uint8_t(0xE0 | (dim & 0x0F))};
        intensity_changed_ = false;
        write(data,1);
    }

    uint8_t HT33K16Component::print(uint8_t start_pos, const char *str) {
        const char *text = str;  // kept for the truncation warning
        uint8_t pos = start_pos;
        uint8_t data = 0x00;
        for (; *str != '\0'; str++) { // iterate over str until eol
            if (*str == ':' || *str == '.')
            {
                data = 0x80;  // set dp and read next char
                continue;
            }
            if (pos >= digits_) {  // ran off the end of the panel
                ESP_LOGW(TAG, "'%s' does not fit in %u digits at position %u, truncated after %u",
                         text, digits_, start_pos, pos - start_pos);
                break;
            }
            data |= char_to_seg7(*str);  // translate ascii to 7 segements
            set_col(buffer_, map_position(pos), data);
            data = 0x00;
            pos++;
        }
        return pos - start_pos;
    }

    uint8_t HT33K16Component::print(const char *str) { return this->print(0, str); }

    uint8_t HT33K16Component::printf(const char *format, ...) {
        va_list arg;
        va_start(arg, format);
        char buffer[64];
        int ret = vsnprintf(buffer, sizeof(buffer), format, arg);
        va_end(arg);
        if (ret > 0)
            return this->print(buffer);
        return 0;
    }

    void HT33K16Component::dump_config() {
    ESP_LOGCONFIG(TAG,
                    "HT33K16 @ 0x%x  intensity: %u  digits: %u",
                    this->address_,
                    this->intensity_,
                    this->digits_
                );
    }

    void HT33K16Component::set_writer(ht33k16_writer_t &&writer) {
        this->writer_ = writer;
    }


}
}