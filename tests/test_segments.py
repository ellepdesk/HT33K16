"""Tests for the ascii -> 7-segment conversion."""

import pytest

from harness import SEG7, char_to_seg7


@pytest.mark.parametrize("char", sorted(SEG7))
def test_known_characters_match_the_segment_table(char):
    assert char_to_seg7(char) == SEG7[char]


@pytest.mark.parametrize("char", ["a", "b", "Z", " ", "?", "*", "\x00", "C", "F"])
def test_unknown_characters_are_blank(char):
    assert char_to_seg7(char) == 0x00


def test_space_is_blank_not_a_stray_glyph():
    """Padding from "%3i" must clear the digit rather than draw something."""
    assert char_to_seg7(" ") == 0x00


def test_no_character_sets_the_decimal_point():
    """Bit 7 is reserved for the dp, which only ':' and '.' may set."""
    for code in range(256):
        assert not char_to_seg7(chr(code)) & 0x80, f"0x{code:02x} sets bit 7"


def test_digits_are_all_distinct():
    patterns = {char_to_seg7(str(d)) for d in range(10)}
    assert len(patterns) == 10


def test_eight_is_every_segment():
    assert char_to_seg7("8") == 0b01111111


def test_one_is_the_sparsest_digit():
    assert bin(char_to_seg7("1")).count("1") == 2
