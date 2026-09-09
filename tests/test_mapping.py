"""Tests for the logical position -> ROW output mapping and print() bounds.

The panel is two banks of four digits: the left-hand bank is wired to ROW4-7
and the right-hand bank to ROW0-3. Without remapping, printing "tt.c HH:MM"
came out as "HH:MM ttc" on the glass.
"""

import pytest

from harness import DIGIT_MAP, DISPLAY_POSITIONS, display_positions, encode, map_position

# The number that appeared at boot: INT_MAX rendered through "%3i", read off
# a panel whose halves are swapped.
INT_MAX = 2147483647


def test_display_positions_matches_the_driver():
    assert display_positions() == DISPLAY_POSITIONS


@pytest.mark.parametrize("pos", range(DISPLAY_POSITIONS))
def test_map_position_matches_the_expected_wiring(pos):
    assert map_position(pos) == DIGIT_MAP[pos]


def test_map_is_a_permutation():
    """Every ROW output must be reachable exactly once, or digits collide."""
    assert sorted(map_position(p) for p in range(DISPLAY_POSITIONS)) == list(
        range(DISPLAY_POSITIONS)
    )


def test_map_swaps_the_two_banks_of_four():
    assert [map_position(p) for p in range(8)] == [4, 5, 6, 7, 0, 1, 2, 3]


def test_map_is_its_own_inverse():
    for pos in range(DISPLAY_POSITIONS):
        assert map_position(map_position(pos)) == pos


def test_out_of_range_positions_pass_through_unmapped():
    """Guards the table lookup; print() never calls this, but be safe."""
    for pos in (DISPLAY_POSITIONS, DISPLAY_POSITIONS + 1, 255):
        assert map_position(pos) == pos


# --- what the mapping actually buys us ---------------------------------


def test_first_digit_lands_on_the_leftmost_row(display):
    """Position 0 must drive ROW4, the leftmost physical digit."""
    display.print("1")
    lit = [byte for byte, value in enumerate(display.buffer) if value]
    # '1' is segments B and C, i.e. segments 1 and 2 -> bytes 2 and 4,
    # and ROW4 is bit 4 of the even byte of each segment.
    assert lit == [2, 4]
    assert display.buffer[2] == 1 << 4
    assert display.buffer[4] == 1 << 4


def test_clock_format_reads_left_to_right(display):
    """The wekker layout must come out as temperature first, then time."""
    display.printf("%3i.c%2i:%02i", 12, 14, 5)
    assert display.buffer == encode(" 12.c14:05")


def test_positions_zero_to_three_are_the_high_bank(display):
    """The first four digits live in the upper nibble of each even byte."""
    display.print("8888")
    for byte in range(0, 14, 2):  # segments 0-6 of '8'
        assert display.buffer[byte] == 0b11110000


def test_positions_four_to_seven_are_the_low_bank(display):
    display.print("8888", pos=4)
    for byte in range(0, 14, 2):
        assert display.buffer[byte] == 0b00001111


# --- print() bounds ----------------------------------------------------


def test_print_stops_at_the_last_position(display):
    assert display.print("12345678901234567890") == DISPLAY_POSITIONS


def test_print_truncates_rather_than_wrapping(display):
    display.print("12345678901234567890")
    assert display.buffer == encode("1234567890123456")


def test_print_past_the_end_writes_nothing(display):
    display.print("1", pos=DISPLAY_POSITIONS)
    assert display.buffer == bytes(16)


def test_print_past_the_end_returns_zero(display):
    assert display.print("123", pos=DISPLAY_POSITIONS) == 0
    assert display.print("123", pos=255) == 0


def test_print_from_a_late_offset_writes_only_what_fits(display):
    assert display.print("1234", pos=14) == 2
    assert display.buffer == encode("12", start=14)


def test_overflow_does_not_corrupt_earlier_positions(display):
    display.print("8", pos=15)
    before = display.buffer
    display.print("111", pos=15)  # only the first '1' fits
    assert display.buffer == encode("1", start=15)
    assert display.buffer != before


def test_overflow_leaves_the_framebuffer_intact(display):
    """Nothing may be written outside the 16 display bytes."""
    display.print("8" * 64)
    assert len(display.transfer) == 17
    assert display.transfer[0] == 0x00  # control byte untouched


def test_the_boot_bug_overflows_the_panel_but_not_the_buffer(display):
    """`int temp = NAN` gave INT_MAX, and "%3i" is a minimum width, so the
    lambda emitted 15 positions instead of 8.

    15 is still inside the 16-position buffer, so the bounds check does NOT
    catch this: the driver has no way to know the panel only has 8 digits.
    Keeping the text short enough is the lambda's job.
    """
    written = display.printf("%3i.c%2i:%02i", INT_MAX, 1, 0)
    assert written == 15
    assert written > 8, "overflows the 8-digit panel"
    assert written <= DISPLAY_POSITIONS, "but stays inside the buffer"
    assert display.buffer == encode(f"{INT_MAX}.c 1:00")


def test_a_sane_temperature_still_fits_in_eight_digits(display):
    for temp in (-99, -5, 0, 12, 100, 999):
        display.fill(0x00)
        assert display.printf("%3i.c%2i:%02i", temp, 14, 5) == 8
