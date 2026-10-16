"""The exact formats wekker.yaml prints, on an 8-digit panel.

Each branch of that lambda must fill all 8 positions: if a format is one
position short the leftover digit keeps whatever was there before, and if it
is one too long the trailing 'c' falls off the panel.
"""

import pytest

from harness import encode

CLOCK_AND_TEMP = "%2i:%02i%4.1f.c"
CLOCK_AND_WHOLE_TEMP = "%2i:%02i%3.0f.c"
CLOCK_ONLY = "%2i:%02i---.c"
NOTHING = "--:-----.c"


@pytest.fixture
def panel(display):
    """The panel as wekker.yaml configures it."""
    display.set_digits(8)
    return display


def test_no_time_and_no_temperature_fills_the_panel(panel):
    assert panel.print(NOTHING) == 8


def test_temperature_unavailable_keeps_the_clock(panel):
    """An unavailable weather sensor must not blank the time."""
    assert panel.printf(CLOCK_ONLY, 14, 5) == 8


def test_temperature_unavailable_renders_the_clock_digits(panel):
    panel.printf(CLOCK_ONLY, 14, 5)
    assert panel.buffer == encode("14:05---.c")


@pytest.mark.parametrize("temp", [0.0, 9.9, -9.9, 23.4, 99.9])
def test_tenths_format_fills_the_panel(panel, temp):
    assert panel.printf_f(CLOCK_AND_TEMP, 14, 5, temp) == 8


@pytest.mark.parametrize("temp", [-10.0, -23.4, 100.0, -99.9])
def test_whole_degree_format_fills_the_panel(panel, temp):
    """Outside -10..100 the tenths are dropped to keep the 'c' on the panel."""
    assert panel.printf_f(CLOCK_AND_WHOLE_TEMP, 14, 5, temp) == 8


def test_midnight_and_single_digit_hours_fill_the_panel(panel):
    assert panel.printf(CLOCK_ONLY, 0, 0) == 8
    assert panel.printf_f(CLOCK_AND_TEMP, 9, 5, 7.3) == 8
