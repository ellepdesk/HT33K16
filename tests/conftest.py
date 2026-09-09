import pytest

from harness import Display, build


@pytest.fixture(scope="session", autouse=True)
def built_library():
    """Compile components/ht33k16 into build/libht33k16_test.so once per run."""
    return build()


@pytest.fixture
def display():
    """A fresh HT33K16Component at 0x70, with an empty i2c capture log."""
    with Display(address=0x70) as d:
        yield d
