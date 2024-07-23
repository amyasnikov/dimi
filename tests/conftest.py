import pytest

from tinydi import TinyDI


@pytest.fixture
def di():
    return TinyDI()
