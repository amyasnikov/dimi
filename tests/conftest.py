import pytest

from dimi import Container


@pytest.fixture
def di():
    return Container()
