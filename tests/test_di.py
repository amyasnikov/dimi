from contextlib import nullcontext
from typing import Annotated

import pytest

from dimi.dependency import Dependency
from dimi.exceptions import InvalidOperation, UnknownDependency
from dimi.scopes import Singleton


@pytest.fixture
def di_with_deps(di):
    @di.dependency
    def f1():
        return 1

    @di.dependency
    def f2(f: Annotated[int, f1]):
        return f * 2

    @di.dependency
    async def f5(f: Annotated[int, f2]):
        return f * 5

    @di.dependency(scope=Singleton)
    async def f7(f: Annotated[int, f5]):
        return f * 7

    @di.dependency
    class A:
        pass

    @di.dependency(scope=Singleton)
    class B:
        def __init__(self, a: Annotated[A, ...], f: Annotated[int, f2]):
            self.arg = [a] * f

    di.f1 = f1
    di.f2 = f2
    di.f5 = f5
    di.f7 = f7
    di.A = A
    di.B = B
    return di


def func():
    return 1


async def async_func():
    return 2


class A:
    pass


@pytest.mark.parametrize("scope", [None, Singleton])
@pytest.mark.parametrize(
    "obj, error",
    [
        (func, None),
        (async_func, None),
        (A, None),
        (lambda: "string", None),
        ("string", InvalidOperation),
        (1234, InvalidOperation),
    ],
)
async def test_setitem(di, obj, scope, error):
    context = nullcontext() if error is None else pytest.raises(error)
    with context:
        di[obj] = obj if scope is None else scope(obj)
        assert isinstance(di._deps[obj], Dependency)
        target_scope_cls = scope if scope else di.default_scope_class
        assert isinstance(di._deps[obj].scope, target_scope_cls)
        assert obj in di


def test_get_sync(di_with_deps):
    assert di_with_deps[di_with_deps.f1] == 1
    assert di_with_deps[di_with_deps.f2] == 2
    with pytest.raises(UnknownDependency):
        di_with_deps[lambda: "not exist"]


def test_get_class(di_with_deps):
    b = di_with_deps[di_with_deps.B]
    assert isinstance(b, di_with_deps.B)
    assert len(b.arg) == 2
    assert isinstance(b.arg[0], di_with_deps.A) and isinstance(b.arg[1], di_with_deps.A)


async def test_get_async(di_with_deps):
    assert await di_with_deps[di_with_deps.f5] == 10
    assert await di_with_deps[di_with_deps.f7] == 70


def test_inject_sync(di_with_deps):
    @di_with_deps.inject
    def func(a: Annotated[int, di_with_deps.f2], b: Annotated[int, di_with_deps.f1]):
        return a + b

    @di_with_deps.inject
    def func2(a: Annotated[int, di_with_deps.f2], b=10):
        return a * b

    @di_with_deps.inject
    def func3(a, b: Annotated[int, di_with_deps.f2]):
        return a * b

    assert func() == 3
    assert func(5, 6) == 11
    assert func(5) == 6
    assert func(b=2) == 4

    assert func2() == 20
    assert func2(a=3, b=4) == 12
    assert func2(b=5) == 10

    assert func3(3) == func3(a=3) == 6
    with pytest.raises(TypeError):
        func3()


def test_inject_class(di_with_deps):
    class C:
        @di_with_deps.inject
        def __init__(self, a: Annotated[di_with_deps.A, ...], b: Annotated[int, di_with_deps.f2]):
            self.a = a
            self.b = b

    c = C()
    assert isinstance(c.a, di_with_deps.A)
    assert c.b == 2


async def test_inject_async(di_with_deps):
    @di_with_deps.inject
    async def func(a: Annotated[int, di_with_deps.f5], b: Annotated[int, di_with_deps.f2]):
        return a + b

    assert await func() == 12
    assert await func(b=3) == 13
    assert await func(3) == 5
    assert await func(10, 5) == 15


def test_inject_postponed(di):
    @di.inject
    def func(arg: Annotated[A, ...]):
        return arg

    di.dependency(A)

    assert isinstance(func(), A)


async def test_override(di_with_deps):
    async def async_f(a: Annotated[int, di_with_deps.f1]):
        return a + 1

    assert di_with_deps[di_with_deps.f2] == 2
    assert await di_with_deps[di_with_deps.f5] == 10

    with di_with_deps.override():
        di_with_deps[di_with_deps.f2] = lambda: 100
        di_with_deps[di_with_deps.f5] = async_f

        assert di_with_deps[di_with_deps.f2] == 100
        assert await di_with_deps[di_with_deps.f5] == 2

    assert di_with_deps[di_with_deps.f2] == 2
    assert await di_with_deps[di_with_deps.f5] == 10


async def test_override_with_inject(di_with_deps):
    @di_with_deps.inject
    async def async_f(f2: Annotated[int, di_with_deps.f2], f5: Annotated[int, di_with_deps.f5]):
        return f2 + f5

    assert await async_f() == 12

    with di_with_deps.override():
        di_with_deps[di_with_deps.f1] = lambda: 100

        assert await async_f() == 1200

    assert await async_f() == 12


async def test_override_overridings(di_with_deps):
    @di_with_deps.inject
    async def async_f(f2: Annotated[int, di_with_deps.f2], f5: Annotated[int, di_with_deps.f5]):
        return f2 + f5

    assert await async_f() == 12

    with di_with_deps.override({di_with_deps.f1: lambda: 100}):
        assert await async_f() == 1200

    assert await async_f() == 12


def test_error_on_two_same_deps(di):
    class A: ...

    class B: ...

    B.__name__ = "A"

    di.dependency(A)
    with pytest.raises(InvalidOperation):
        di.dependency(B)
