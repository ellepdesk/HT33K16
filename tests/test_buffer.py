"""Tests for the low-level framebuffer helpers.

Buffer layout of the HT16K33: 16 bytes, two per COM line. COM `row` lives in
bytes [row * 2] (ROW outputs 0-7) and [row * 2 + 1] (ROW outputs 8-15).
The driver drives digits off the ROW outputs, so a digit position is a
"column" and a segment is a "row".
"""

import pytest

from harness import set_bit, set_col, set_row

EMPTY = bytearray(16)


@pytest.mark.parametrize(
    "row, col, expected_byte, expected_bit",
    [
        (0, 0, 0, 0),
        (0, 7, 0, 7),
        (0, 8, 1, 0),  # columns 8-15 spill into the odd byte
        (0, 15, 1, 7),
        (1, 0, 2, 0),
        (7, 15, 15, 7),
    ],
)
def test_set_bit_targets_the_right_byte(row, col, expected_byte, expected_bit):
    result = set_bit(EMPTY, row, col, True)
    expected = bytearray(16)
    expected[expected_byte] = 1 << expected_bit
    assert result == expected


def test_set_bit_clears():
    full = bytearray(b"\xff" * 16)
    result = set_bit(full, 3, 9, False)
    expected = bytearray(b"\xff" * 16)
    expected[7] = 0xFF & ~(1 << 1)
    assert result == expected


def test_set_col_writes_one_digit_across_all_segment_bytes():
    # 0b10100101 -> segments 0, 2, 5 and 7 lit at column 3.
    result = set_col(EMPTY, 3, 0b10100101)
    expected = bytearray(16)
    for segment in (0, 2, 5, 7):
        expected[segment * 2] = 1 << 3
    assert result == expected


def test_set_col_overwrites_rather_than_ors():
    """A column must be fully rewritten, otherwise digits smear together."""
    filled = set_col(EMPTY, 0, 0xFF)
    result = set_col(filled, 0, 0b00000001)
    assert result == set_col(EMPTY, 0, 0b00000001)


def test_set_col_leaves_neighbouring_columns_alone():
    result = set_col(set_col(EMPTY, 0, 0xFF), 1, 0x00)
    assert result == set_col(EMPTY, 0, 0xFF)


def test_set_row_splits_data_low_byte_first():
    """Regression: set_row used to do pointer arithmetic instead of indexing.

    `buffer + (row / 2) = d_low` does not even compile, and the /2 was the
    wrong stride: COM `row` starts at byte row * 2, not row / 2.
    """
    result = set_row(EMPTY, 3, 0xBEEF)
    expected = bytearray(16)
    expected[6] = 0xEF  # low byte -> ROW 0-7
    expected[7] = 0xBE  # high byte -> ROW 8-15
    assert result == expected


@pytest.mark.parametrize("row", range(8))
def test_set_row_is_the_inverse_of_set_bit(row):
    """Lighting every column of a row via set_bit must equal set_row(0xFFFF)."""
    by_bit = bytearray(16)
    for col in range(16):
        by_bit = set_bit(by_bit, row, col, True)
    assert by_bit == set_row(EMPTY, row, 0xFFFF)


@pytest.mark.parametrize("row", range(8))
def test_set_row_only_touches_its_own_row(row):
    result = set_row(EMPTY, row, 0xFFFF)
    for byte, value in enumerate(result):
        expected = 0xFF if byte // 2 == row else 0x00
        assert value == expected, f"byte {byte} of row {row}"
