from dataclasses import dataclass
from typing import Annotated

import pytest


@pytest.fixture
def di_abc(di):
    @di.dependency
    class A:
        pass

    @di.dependency
    class B:
        def __init__(self, a: Annotated[A, ...]):
            self.a = a

    @di.dependency
    class C:
        def __init__(self, a: Annotated[A, ...], b: Annotated[B, ...]):
            self.a = a
            self.b = b

    di.A = A
    di.B = B
    di.C = C
    return di


def test_dependent_classes(di_abc):
    @di_abc.inject
    def func(c: Annotated[di_abc.C, ...]):
        return c

    c = func()
    assert isinstance(c, di_abc.C)
    assert isinstance(c.b, di_abc.B)
    assert isinstance(c.a, di_abc.A)
    assert isinstance(c.b.a, di_abc.A)
    assert c.a != c.b.a


@pytest.fixture
def di_fgh(di):
    @di.dependency
    def f():
        return "f"

    @di.dependency
    def g(ff: Annotated[str, f]):
        return ff + "g"

    @di.dependency
    def h(gg: Annotated[str, g]):
        return gg + "h"

    di.h = h

    return di


def test_dependent_functions(di_fgh):
    @di_fgh.inject
    def func(hh: Annotated[str, di_fgh.h]):
        return hh

    assert func() == "fgh"


@pytest.fixture
async def di_fgh_async(di):
    @di.dependency
    def f():
        return "f"

    @di.dependency
    async def F():
        return "F"

    @di.dependency
    async def g(ff: Annotated[str, f], FF: Annotated[str, F]):
        return FF + ff + "g"

    @di.dependency
    async def h(gg: Annotated[str, g]):
        return gg + "h"

    di.h = h

    return di


async def test_dependent_functions_async(di_fgh_async):
    @di_fgh_async.inject
    async def func(hh: Annotated[str, di_fgh_async.h]):
        return hh

    assert await func() == "Ffgh"


def test_dataclasses(di):
    @di.dependency
    @dataclass
    class A:
        arg: int = 10

    @di.dependency
    def get_a():
        return A(20)

    @di.dependency
    @dataclass
    class B:
        a1: Annotated[A, ...]
        a2: Annotated[A, get_a]

    @di.inject
    @dataclass
    class C:
        a: Annotated[A, ...]
        b: Annotated[B, ...]

    c = C()
    assert c.b.a2.arg == 20
    assert c.b.a1.arg == 10
    assert c.a.arg == 10
