"""ctypes bindings for the host build of the ht33k16 driver.

The C++ in ``components/ht33k16`` is compiled by ``tests/Makefile`` into
``build/libht33k16.a`` and linked, together with a fake i2c bus, into
``build/libht33k16_test.so``. This module wraps that shared object in
something pleasant to assert against.
"""

from __future__ import annotations

import ctypes
import subprocess
from pathlib import Path

TESTS_DIR = Path(__file__).parent
LIB_PATH = TESTS_DIR / "build" / "libht33k16_test.so"

# Number of display bytes; the transfer adds a leading control byte.
DISPLAY_BYTES = 16
TRANSFER_BYTES = DISPLAY_BYTES + 1

# Blink modes, mirroring HT33K16Component::blink.
BLINK_OFF = 0
BLINK_2HZ = 1
BLINK_1HZ = 2
BLINK_05HZ = 3

# Expected 7-segment patterns, written out independently of the C switch
# statement so that the two have to agree. Bit 0 is segment A .. bit 6 is
# segment G, bit 7 is the decimal point.
#
#      --A--
#     |     |
#     F     B
#     |     |
#      --G--
#     |     |
#     E     C
#     |     |
#      --D--   (DP)
SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G, SEG_DP = (1 << i for i in range(8))

SEG7 = {
    "0": SEG_A | SEG_B | SEG_C | SEG_D | SEG_E | SEG_F,
    "1": SEG_B | SEG_C,
    "2": SEG_A | SEG_B | SEG_D | SEG_E | SEG_G,
    "3": SEG_A | SEG_B | SEG_C | SEG_D | SEG_G,
    "4": SEG_B | SEG_C | SEG_F | SEG_G,
    "5": SEG_A | SEG_C | SEG_D | SEG_F | SEG_G,
    "6": SEG_A | SEG_C | SEG_D | SEG_E | SEG_F | SEG_G,
    "7": SEG_A | SEG_B | SEG_C,
    "8": SEG_A | SEG_B | SEG_C | SEG_D | SEG_E | SEG_F | SEG_G,
    "9": SEG_A | SEG_B | SEG_C | SEG_D | SEG_F | SEG_G,
    "-": SEG_G,
    "~": SEG_A | SEG_B | SEG_F | SEG_G,  # degree sign
    # 'high' C and F, drawn in the top half so they line up with the degree
    # sign in "~c" / "~f" rather than sitting on the baseline.
    "c": SEG_A | SEG_F | SEG_G,
    "f": SEG_A | SEG_E | SEG_F | SEG_G,
}

DP_CHARS = ":."


def build() -> Path:
    """(Re)build the shared object. Cheap and idempotent; make handles it."""
    subprocess.run(["make", "--silent"], cwd=TESTS_DIR, check=True)
    return LIB_PATH


def encode(text: str, start: int = 0) -> bytes:
    """Reference implementation of what print() should leave in the buffer.

    Deliberately written in the flat, obvious way (byte = segment * 2 +
    column // 8) rather than mirroring the driver's set_col/set_bit
    recursion, so that agreement between the two means something.
    """
    buf = bytearray(DISPLAY_BYTES)
    pos = start
    data = 0
    for char in text:
        if char in DP_CHARS:
            data = SEG_DP  # set dp and read next char
            continue
        data |= SEG7.get(char, 0)
        for segment in range(8):
            if (data >> segment) & 1:
                buf[segment * 2 + (pos // 8)] |= 1 << (pos % 8)
        data = 0
        pos += 1
    return bytes(buf)


class I2CTransaction:
    """One captured write() on the fake bus."""

    def __init__(self, address: int, data: bytes):
        self.address = address
        self.data = data

    def __repr__(self) -> str:
        return f"I2CTransaction(address=0x{self.address:02x}, data={self.data.hex(' ')})"

    def __eq__(self, other) -> bool:
        if isinstance(other, (bytes, bytearray)):
            return self.data == bytes(other)
        if isinstance(other, int):
            return self.data == bytes([other])
        if isinstance(other, I2CTransaction):
            return (self.address, self.data) == (other.address, other.data)
        return NotImplemented


class _Lib:
    """Lazily-loaded singleton around the shared object."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        self.dll = ctypes.CDLL(str(build()))
        u8, u16, i32, b, vp, cp, u8p = (
            ctypes.c_uint8,
            ctypes.c_uint16,
            ctypes.c_int,
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint8),
        )
        signatures = {
            "ht_new": ([u8], vp),
            "ht_free": ([vp], None),
            "ht_setup": ([vp], None),
            "ht_update": ([vp], None),
            "ht_display": ([vp], None),
            "ht_dump_config": ([vp], None),
            "ht_fill": ([vp, u8], None),
            "ht_set_intensity": ([vp, u8], None),
            "ht_set_enable": ([vp, b], None),
            "ht_set_blink": ([vp, u8], None),
            "ht_print_at": ([vp, u8, cp], u8),
            "ht_print": ([vp, cp], u8),
            "ht_printf3i": ([vp, cp, i32, i32, i32], u8),
            "ht_reg_system": ([vp, b], None),
            "ht_reg_display": ([vp, u8, b], None),
            "ht_reg_dimming": ([vp, u8], None),
            "ht_get_databuffer": ([vp, u8p], None),
            "ht_get_intensity": ([vp], u8),
            "ht_get_intensity_changed": ([vp], b),
            "ht_get_enabled": ([vp], b),
            "ht_get_blink": ([vp], u8),
            "ht_get_display_reg_dirty": ([vp], b),
            "ht_set_bit": ([u8p, u8, u8, b], None),
            "ht_set_col": ([u8p, u8, u8], None),
            "ht_set_row": ([u8p, u8, u16], None),
            "ht_char_to_seg7": ([u8], u8),
            "ht_i2c_clear": ([], None),
            "ht_i2c_count": ([], i32),
            "ht_i2c_address": ([i32], i32),
            "ht_i2c_data": ([i32, u8p, i32], i32),
        }
        for name, (argtypes, restype) in signatures.items():
            fn = getattr(self.dll, name)
            fn.argtypes = argtypes
            fn.restype = restype


def char_to_seg7(char: str) -> int:
    """Call the driver's ascii -> 7-segment conversion."""
    return _Lib().dll.ht_char_to_seg7(ord(char))


def set_bit(buffer: bytearray, row: int, col: int, bit: bool) -> bytearray:
    """Call the driver's set_bit on a copy of `buffer` and return the result."""
    return _call_buffer_helper("ht_set_bit", buffer, row, col, bit)


def set_col(buffer: bytearray, col: int, data: int) -> bytearray:
    return _call_buffer_helper("ht_set_col", buffer, col, data)


def set_row(buffer: bytearray, row: int, data: int) -> bytearray:
    return _call_buffer_helper("ht_set_row", buffer, row, data)


def _call_buffer_helper(name: str, buffer: bytes, *args) -> bytearray:
    buf = (ctypes.c_uint8 * len(buffer)).from_buffer_copy(bytes(buffer))
    getattr(_Lib().dll, name)(buf, *args)
    return bytearray(buf)


class Display:
    """A HT33K16Component instance plus the i2c traffic it produced."""

    def __init__(self, address: int = 0x70):
        self._lib = _Lib()
        self.address = address
        self._handle = self._lib.dll.ht_new(address)
        self.clear_i2c()

    def close(self):
        if self._handle is not None:
            self._lib.dll.ht_free(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- component API --------------------------------------------------

    def setup(self):
        self._lib.dll.ht_setup(self._handle)

    def update(self):
        self._lib.dll.ht_update(self._handle)

    def display(self):
        self._lib.dll.ht_display(self._handle)

    def dump_config(self):
        self._lib.dll.ht_dump_config(self._handle)

    def fill(self, c: int = 0x00):
        self._lib.dll.ht_fill(self._handle, c)

    def set_intensity(self, dim: int):
        self._lib.dll.ht_set_intensity(self._handle, dim)

    def set_enable(self, enable: bool):
        self._lib.dll.ht_set_enable(self._handle, enable)

    def set_blink(self, mode: int):
        self._lib.dll.ht_set_blink(self._handle, mode)

    def print(self, text: str, pos: int | None = None) -> int:
        encoded = text.encode()
        if pos is None:
            return self._lib.dll.ht_print(self._handle, encoded)
        return self._lib.dll.ht_print_at(self._handle, pos, encoded)

    def printf(self, fmt: str, a: int = 0, b: int = 0, c: int = 0) -> int:
        return self._lib.dll.ht_printf3i(self._handle, fmt.encode(), a, b, c)

    def reg_system(self, osc: bool):
        self._lib.dll.ht_reg_system(self._handle, osc)

    def reg_display(self, blink: int, enable: bool):
        self._lib.dll.ht_reg_display(self._handle, blink, enable)

    def reg_dimming(self, dim: int):
        self._lib.dll.ht_reg_dimming(self._handle, dim)

    # -- state ----------------------------------------------------------

    @property
    def transfer(self) -> bytes:
        """The full 17-byte i2c payload: control byte + 16 display bytes."""
        buf = (ctypes.c_uint8 * TRANSFER_BYTES)()
        self._lib.dll.ht_get_databuffer(self._handle, buf)
        return bytes(buf)

    @property
    def buffer(self) -> bytes:
        """Just the 16 display bytes."""
        return self.transfer[1:]

    @property
    def intensity(self) -> int:
        return self._lib.dll.ht_get_intensity(self._handle)

    @property
    def intensity_changed(self) -> bool:
        return self._lib.dll.ht_get_intensity_changed(self._handle)

    @property
    def enabled(self) -> bool:
        return self._lib.dll.ht_get_enabled(self._handle)

    @property
    def blink(self) -> int:
        return self._lib.dll.ht_get_blink(self._handle)

    @property
    def display_reg_dirty(self) -> bool:
        return self._lib.dll.ht_get_display_reg_dirty(self._handle)

    # -- captured bus traffic -------------------------------------------

    def clear_i2c(self):
        self._lib.dll.ht_i2c_clear()

    @property
    def i2c(self) -> list[I2CTransaction]:
        out = []
        for i in range(self._lib.dll.ht_i2c_count()):
            buf = (ctypes.c_uint8 * 64)()
            length = self._lib.dll.ht_i2c_data(i, buf, 64)
            address = self._lib.dll.ht_i2c_address(i)
            out.append(I2CTransaction(address, bytes(buf[:length])))
        return out

    @property
    def commands(self) -> list[int]:
        """Single-byte register writes, as ints, in order."""
        return [t.data[0] for t in self.i2c if len(t.data) == 1]
