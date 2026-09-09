"""Tests for the i2c command bytes the driver puts on the bus.

HT16K33 command bytes:
  0x20 | osc            system setup (oscillator off/on)
  0x80 | blink<<1 | on  display setup
  0xE0 | dim            dimming set
  0x00 + 16 bytes       display data, written from address 0
"""

import pytest

from harness import BLINK_05HZ, BLINK_1HZ, BLINK_2HZ, BLINK_OFF

SYSTEM_ON = 0x21
SYSTEM_OFF = 0x20
DISPLAY_ON = 0x81
DISPLAY_OFF = 0x80


def test_reg_system_encoding(display):
    display.reg_system(True)
    display.reg_system(False)
    assert display.commands == [SYSTEM_ON, SYSTEM_OFF]


@pytest.mark.parametrize(
    "blink, enable, expected",
    [
        (BLINK_OFF, False, 0x80),
        (BLINK_OFF, True, 0x81),
        (BLINK_2HZ, True, 0x83),
        (BLINK_1HZ, True, 0x85),
        (BLINK_05HZ, True, 0x87),
        (BLINK_05HZ, False, 0x86),
    ],
)
def test_reg_display_encoding(display, blink, enable, expected):
    display.reg_display(blink, enable)
    assert display.commands == [expected]


@pytest.mark.parametrize("dim", range(16))
def test_reg_dimming_encoding(display, dim):
    display.reg_dimming(dim)
    assert display.commands == [0xE0 | dim]


def test_reg_dimming_masks_out_of_range_values(display):
    display.reg_dimming(0xFF)
    assert display.commands == [0xEF]


# --- setup() -----------------------------------------------------------


def test_setup_starts_the_oscillator(display):
    display.setup()
    assert SYSTEM_ON in display.commands


def test_setup_turns_the_display_on(display):
    """Regression: setup() used to send reg_display(OFF, false).

    That left the HT16K33 display driver disabled, and since nothing in the
    YAML calls set_enable(), the panel stayed dark forever.
    """
    display.setup()
    assert DISPLAY_ON in display.commands
    assert DISPLAY_OFF not in display.commands


def test_setup_sends_the_intensity(display):
    display.setup()
    assert 0xEF in display.commands  # default intensity 15


def test_setup_order_is_oscillator_then_display_then_data(display):
    display.setup()
    commands = display.commands
    assert commands.index(SYSTEM_ON) < commands.index(DISPLAY_ON)
    # The last transaction is the 17-byte framebuffer transfer.
    assert len(display.i2c[-1].data) == 17


def test_setup_writes_a_blank_framebuffer(display):
    display.setup()
    assert display.i2c[-1].data == bytes(17)


def test_every_transaction_goes_to_the_configured_address(display):
    display.setup()
    assert {t.address for t in display.i2c} == {0x70}


# --- update() ----------------------------------------------------------


def test_update_always_writes_the_framebuffer(display):
    display.setup()
    display.clear_i2c()
    display.update()
    assert len(display.i2c) == 1
    assert len(display.i2c[0].data) == 17


def test_update_writes_the_control_byte_then_the_display_bytes(display):
    display.setup()
    display.print("1234")
    display.clear_i2c()
    display.update()
    assert display.i2c[-1].data == bytes([0x00]) + display.buffer


def test_update_resends_intensity_only_after_a_change(display):
    display.setup()
    display.clear_i2c()

    display.update()
    assert display.commands == []

    display.set_intensity(7)
    display.update()
    assert display.commands == [0xE7]

    display.clear_i2c()
    display.update()
    assert display.commands == []


def test_set_intensity_to_the_same_value_is_a_no_op(display):
    display.setup()
    display.clear_i2c()
    display.set_intensity(display.intensity)
    display.update()
    assert display.commands == []


def test_update_resends_display_register_only_after_a_change(display):
    display.setup()
    display.clear_i2c()

    display.update()
    assert display.commands == []

    display.set_blink(BLINK_1HZ)
    display.update()
    assert display.commands == [0x85]

    display.clear_i2c()
    display.update()
    assert display.commands == []


def test_set_blink_to_the_same_mode_is_a_no_op(display):
    """Regression: `blinking` was uninitialised, so the != guard on the very
    first set_blink() could go either way."""
    display.setup()
    display.clear_i2c()
    display.set_blink(display.blink)
    display.update()
    assert display.commands == []


def test_set_blink_from_the_default_is_not_swallowed(display):
    display.setup()
    display.clear_i2c()
    display.set_blink(BLINK_2HZ)
    assert display.display_reg_dirty
    display.update()
    assert display.commands == [0x83]


def test_set_enable_false_then_update_turns_the_display_off(display):
    display.setup()
    display.clear_i2c()
    display.set_enable(False)
    display.update()
    assert display.commands == [DISPLAY_OFF]


def test_set_enable_and_blink_are_combined_in_one_write(display):
    display.setup()
    display.clear_i2c()
    display.set_blink(BLINK_2HZ)
    display.set_enable(True)
    display.update()
    assert display.commands == [0x83]


def test_blink_survives_a_toggle_of_enable(display):
    display.setup()
    display.set_blink(BLINK_1HZ)
    display.update()
    display.clear_i2c()

    display.set_enable(False)
    display.update()
    assert display.commands == [0x84]  # 1Hz blink, display off


# --- default state -----------------------------------------------------


def test_default_state_is_deterministic(display):
    """Regression: enabled / blinking / reg_display_changed had no
    initialiser, so a fresh component started from whatever was on the heap."""
    assert display.enabled is True
    assert display.blink == BLINK_OFF
    assert display.display_reg_dirty is True
    assert display.intensity == 15
    assert display.intensity_changed is True


def test_a_fresh_component_writes_nothing_before_setup(display):
    assert display.i2c == []


def test_framebuffer_starts_blank(display):
    assert display.transfer == bytes(17)
