from types import FunctionType

import pytest

from dimi import Container


@pytest.fixture
def di():
    return Container()


@pytest.fixture
def preserve_signature():
    NOT_DEFINED = object()

    signatures = {}

    def _fixture(func):
        if isinstance(func, type):
            if not isinstance(func.__init__, FunctionType):
                return
            func = func.__init__
        signatures[func] = getattr(func, "__signature__", NOT_DEFINED)

    yield _fixture

    for f, sig in signatures.items():
        if sig == NOT_DEFINED:
            delattr(f, "__signature__")
        else:
            f.__signature__ = sig
