"""Tests for print() / printf() and how they land in the framebuffer."""

import pytest

from harness import SEG_DP, SEG7, bit_for, encode


def test_print_returns_number_of_digits_written(display):
    assert display.print("1234") == 4


def test_print_returns_zero_for_empty_string(display):
    assert display.print("") == 0


def test_dp_characters_do_not_consume_a_position(display):
    """':' and '.' set the dp of the *next* digit, they are not digits."""
    assert display.print("12:34") == 4
    assert display.print("1.2") == 2


def test_print_renders_digits(display):
    display.print("1234")
    assert display.buffer == encode("1234")


def test_print_at_offset(display):
    display.print("12", pos=4)
    assert display.buffer == encode("12", start=4)


def test_print_at_offset_returns_length_not_end_position(display):
    assert display.print("12", pos=4) == 2


def test_print_crosses_the_byte_boundary_at_column_8(display):
    display.print("0123456789")
    assert display.buffer == encode("0123456789")


def test_print_spans_all_sixteen_positions(display):
    text = "0123456789012345"
    assert display.print(text) == 16
    assert display.buffer == encode(text)


def test_colon_sets_the_decimal_point_of_the_following_digit(display):
    display.print("1:2")
    # '1' at position 0 plain, '2' at position 1 with dp.
    assert display.buffer == encode("1:2")
    # And concretely: the dp is segment 7, and position 1 is driven by ROW5.
    byte, bit = bit_for(1, 7)
    assert display.buffer[byte] == 1 << bit


def test_period_behaves_like_colon(display):
    display.print("1.2")
    assert display.buffer == encode("1.2")


def test_trailing_dp_is_dropped(display):
    """A dp with no digit after it has nowhere to go."""
    assert display.print("12.") == 2
    assert display.buffer == encode("12")


def test_dp_does_not_leak_into_later_digits(display):
    display.print("1.23")
    byte, bit = bit_for(1, 7)
    assert display.buffer[byte] == 1 << bit  # only position 1 has the dp


def test_unknown_characters_blank_their_position(display):
    display.print("1X2")
    assert display.buffer == encode("1X2")
    # 'X' occupies position 1 but lights nothing.
    for segment in range(8):
        byte, bit = bit_for(1, segment)
        assert not display.buffer[byte] & (1 << bit)


def test_print_overwrites_previous_content_at_the_same_position(display):
    display.print("8888")
    display.print("1111")
    assert display.buffer == encode("1111")


def test_print_leaves_untouched_positions_alone(display):
    display.print("88888888")
    display.print("11", pos=0)
    assert display.buffer == encode("11888888")


def test_fill_sets_every_position(display):
    display.fill(0xFF)
    assert display.buffer == b"\xff" * 16


def test_fill_zero_clears(display):
    display.print("8888")
    display.fill(0x00)
    assert display.buffer == bytes(16)


def test_fill_does_not_disturb_the_control_byte(display):
    display.fill(0xFF)
    assert display.transfer[0] == 0x00


def test_printf_formats_and_prints(display):
    assert display.printf("%i%i", 12, 34) == 4
    assert display.buffer == encode("1234")


def test_printf_wekker_clock_format(display):
    """The format used by wekker.yaml: ' 12.c14:05' -> 8 digits."""
    assert display.printf("%3i.c%2i:%02i", 12, 14, 5) == 8
    assert display.buffer == encode(" 12.c14:05")


def test_printf_negative_temperature(display):
    assert display.printf("%3i.c%2i:%02i", -5, 9, 30) == 8
    assert display.buffer == encode(" -5.c 9:30")


@pytest.mark.parametrize("text", ["0", "9", "-", "~", "c", "f", "8888", "1:2", "0.0"])
def test_print_matches_the_reference_encoder(display, text):
    display.fill(0x00)
    display.print(text)
    assert display.buffer == encode(text)


def test_segment_table_agrees_with_a_single_char_print(display):
    for char, pattern in SEG7.items():
        display.fill(0x00)
        display.print(char)
        for segment in range(8):
            byte, bit = bit_for(0, segment)
            lit = bool(display.buffer[byte] & (1 << bit))
            assert lit == bool(pattern >> segment & 1), f"{char!r} segment {segment}"


def test_decimal_point_is_bit_seven(display):
    display.print(".8")
    byte, bit = bit_for(0, 7)
    assert display.buffer[byte] & (1 << bit), "dp not set"
    assert SEG_DP == 0x80
