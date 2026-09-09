# Host tests for the ht33k16 component

The driver is plain C++ with only a thin dependency on ESPHome, so it can be
compiled and tested on a normal machine — no ESP32, no flashing, no ESPHome
install.

## How it works

```
components/ht33k16/ht33k16.cpp
        │  compiled against tests/stubs/esphome/**  (fake Component / I2CDevice / logging)
        ▼
tests/build/libht33k16.a
        │  linked with shim.cpp (extern "C" wrapper) and i2c_stub.cpp (fake bus)
        ▼
tests/build/libht33k16_test.so
        │  loaded with ctypes
        ▼
tests/harness.py  →  test_*.py
```

The fake `I2CDevice::write()` never touches a bus; it appends every
transaction to a log. That is what lets the tests assert on the exact
register bytes the driver emits, e.g. `0x21` for "oscillator on" or
`0xE7` for "intensity 7".

`harness.py` also carries an independent Python reference implementation of
the 7-segment table and the framebuffer layout, so the C++ and the Python
have to agree rather than one just restating the other.

## Running

```sh
cd tests
pytest
```

`conftest.py` runs `make` for you, so there is no separate build step. To
build by hand:

```sh
make          # -> build/libht33k16.a and build/libht33k16_test.so
make clean
```

Set `-DHT33K16_TEST_VERBOSE_LOG` in `CXXFLAGS` to see `ESP_LOGx` output.

## Files

| file | purpose |
| --- | --- |
| `Makefile` | builds the static lib and the ctypes shared object |
| `stubs/esphome/**` | minimal stand-ins for the ESPHome headers |
| `stubs/i2c_stub.cpp` | fake i2c bus that records transactions |
| `shim.cpp` | `extern "C"` wrapper; subclasses the component to expose protected state |
| `harness.py` | ctypes bindings, `Display` wrapper, reference 7-segment model |
| `conftest.py` | builds the lib, provides the `display` fixture |
| `test_buffer.py` | `set_bit` / `set_col` / `set_row` framebuffer layout |
| `test_segments.py` | ascii → 7-segment conversion |
| `test_print.py` | `print()` / `printf()`, decimal points, positioning |
| `test_registers.py` | i2c command bytes, `setup()`, `update()` change tracking |

## Adding a test

Most tests just need the `display` fixture, which is a fresh component at
address `0x70` with an empty i2c log:

```python
def test_intensity_is_sent_once(display):
    display.setup()
    display.clear_i2c()
    display.set_intensity(3)
    display.update()
    assert display.commands == [0xE3]
    display.clear_i2c()
    display.update()
    assert display.commands == []
```

`display.commands` is the list of single-byte register writes;
`display.buffer` is the 16 display bytes; `display.i2c` is every transaction
including the 17-byte framebuffer transfer.

If you add a method to `HT33K16Component`, export it in `shim.cpp` and add
its signature to the `signatures` dict in `harness.py`.
