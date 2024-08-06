from dataclasses import dataclass
from itertools import count
from typing import Annotated, Any

import pytest

from dimi import Container, Singleton


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


@dataclass
class D:
    arg: Any = 100


@pytest.fixture
def di_subdep_d():
    di = Container()

    di.dependency(D)

    @di.dependency
    def get_d_sync():
        return D(200)

    @di.dependency
    async def get_d_async():
        return D(300)

    @di.dependency
    def get_d_complex():
        return D(15 + 3j)

    return di


@pytest.mark.parametrize(
    "string_annotation, result",
    [
        ("D", D()),
        ("D.arg", 100),
        ("get_d_sync", D(200)),
        ("get_d_sync.arg", 200),
        ("get_d_async", D(300)),
        ("get_d_async.arg", 300),
        ("get_d_complex.arg.real", 15.0),
    ],
)
async def test_string_dependency(string_annotation, result, di_subdep_d):
    @di_subdep_d.inject
    def func_sync(arg: Annotated[Any, string_annotation]):
        return arg

    @di_subdep_d.inject
    async def func_async(arg: Annotated[Any, string_annotation]):
        return arg

    if "async" not in string_annotation:
        assert func_sync() == result

    assert await func_async() == result


@pytest.mark.parametrize(
    "string_annotation, result",
    [
        ("D", D()),
        ("D.arg", 100),
        ("get_d_sync", D(200)),
        ("get_d_sync.arg", 200),
        ("get_d_async", D(300)),
        ("get_d_async.arg", 300),
        ("get_d_complex.arg.real", 15.0),
    ],
)
async def test_string_dependency_lazy(string_annotation, result, di_subdep_d, di):
    assert not di._deps

    @di.inject
    def func_sync(arg: Annotated[Any, string_annotation]):
        return arg

    @di.inject
    async def func_async(arg: Annotated[Any, string_annotation]):
        return arg

    for func in di_subdep_d._deps:
        di.dependency(func)

    if "async" not in string_annotation:
        assert func_sync() == result

    assert await func_async() == result


@pytest.mark.parametrize(
    "string_annotation, result",
    [
        ("D", D()),
        ("D.arg", 100),
        ("get_d_sync", D(200)),
        ("get_d_sync.arg", 200),
        ("get_d_async", D(300)),
        ("get_d_async.arg", 300),
        ("get_d_complex.arg.real", 15.0),
    ],
)
async def test_string_subdependency(string_annotation, result, di_subdep_d):
    @di_subdep_d.dependency
    async def subdep_async(arg: Annotated[Any, string_annotation]):
        return arg

    assert await di_subdep_d[subdep_async] == result

    if "async" not in string_annotation:

        @di_subdep_d.dependency
        def subdep_sync(arg: Annotated[Any, string_annotation]):
            return arg

        assert di_subdep_d[subdep_sync] == result


def test_singleton_scope(di):
    counter = count()

    @di.dependency
    def regular_dep():
        return next(counter)

    @di.dependency(scope=Singleton)
    def singleton_dep():
        return next(counter)

    for _ in range(4):
        assert di[singleton_dep] == 0

    for i in range(1, 5):
        assert di[regular_dep] == i
