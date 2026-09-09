"""Tests for the `digits:` option: how many digits the panel actually has.

The driver drives 16 ROW outputs, but a panel may be fitted with fewer.
Without knowing the real count it cannot tell an over-long string from a
legitimate one, which is how "%3i" quietly emitted 15 positions onto an
8-digit panel at boot.
"""

import pytest

from harness import DISPLAY_POSITIONS, encode

INT_MAX = 2147483647


def test_defaults_to_the_full_width(display):
    assert display.digits == DISPLAY_POSITIONS


@pytest.mark.parametrize("digits", range(1, 17))
def test_set_digits_accepts_the_valid_range(display, digits):
    display.set_digits(digits)
    assert display.digits == digits


@pytest.mark.parametrize("digits", [0, 17, 100, 255])
def test_set_digits_clamps_nonsense(display, digits):
    display.set_digits(digits)
    assert display.digits == DISPLAY_POSITIONS


def test_print_stops_at_the_configured_width(display):
    display.set_digits(8)
    assert display.print("0123456789") == 8


def test_print_truncates_to_the_configured_width(display):
    display.set_digits(8)
    display.print("0123456789")
    assert display.buffer == encode("01234567")


def test_narrower_panel_leaves_the_unused_rows_dark(display):
    display.set_digits(4)
    display.print("88888888")
    assert display.buffer == encode("8888")


def test_the_boot_bug_is_now_caught(display):
    """With digits: 8, the INT_MAX render stops at the panel edge instead of
    scribbling 15 positions and dropping the time entirely."""
    display.set_digits(8)
    written = display.printf("%3i.c%2i:%02i", INT_MAX, 1, 0)
    assert written == 8
    assert display.buffer == encode("21474836")


def test_a_sane_reading_is_unaffected_by_the_limit(display):
    display.set_digits(8)
    assert display.printf("%3i.c%2i:%02i", 12, 14, 5) == 8
    assert display.buffer == encode(" 12.c14:05")


def test_changing_digits_does_not_move_existing_content(display):
    display.print("1234")
    before = display.buffer
    display.set_digits(8)
    assert display.buffer == before


def test_print_at_an_offset_respects_the_limit(display):
    display.set_digits(8)
    assert display.print("999", pos=6) == 2
    assert display.buffer == encode("99", start=6)


def test_print_beyond_the_limit_writes_nothing(display):
    display.set_digits(8)
    assert display.print("1", pos=8) == 0
    assert display.buffer == bytes(16)


def test_widening_re_enables_the_upper_positions(display):
    display.set_digits(4)
    assert display.print("88888888") == 4
    display.fill(0x00)
    display.set_digits(16)
    assert display.print("88888888") == 8


def test_fill_still_covers_every_row(display):
    """fill() addresses ROW outputs directly, so it is not limited by
    digits: -- clearing must always blank the whole chip."""
    display.set_digits(4)
    display.fill(0xFF)
    assert display.buffer == b"\xff" * 16
