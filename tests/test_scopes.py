import asyncio
from contextlib import nullcontext
from itertools import count

import pytest

from tinydi.exceptions import InvalidOperation
from tinydi.scopes import Context, Factory, Singleton


@pytest.fixture
def counter():
    cnt = count()

    def f():
        return next(cnt)

    return f


@pytest.fixture
async def counter_async(counter):
    async def f():
        return counter()

    return f


@pytest.mark.parametrize("scope_cls, results", [(Factory, [0, 1, 2, 3]), (Singleton, [0, 0, 0, 0])])
def test_scope(scope_cls, results, counter):
    scope = scope_cls(counter)
    scope_call_results = []
    for _ in range(4):
        val = scope()
        scope_call_results.append(val)
    assert scope_call_results == results


async def test_context_scope(counter_async):
    scope = Context(counter_async)

    async def f1(counter):
        f1_res = await counter()
        f2_res = await f2(counter)
        return f1_res, f2_res

    async def f2(counter):
        return await counter()

    assert await asyncio.Task(f1(scope)) == (0, 0)
    assert await asyncio.Task(f1(scope)) == (1, 1)


def f(): ...
async def f2(): ...


class A: ...


@pytest.mark.parametrize(
    "obj, error",
    [
        (f, None),
        (f2, None),
        (A, None),
        ("string", InvalidOperation),
        (1234, InvalidOperation),
    ],
)
def test_invalid_scope(obj, error):
    context = nullcontext() if error is None else pytest.raises(InvalidOperation)
    with context:
        Factory(obj)


def test_scope_repr():
    class A:
        def __repr__(self):
            return "A-class"

        def __call__(self):
            pass

    a = A()
    assert repr(Singleton(a)) == "Singleton(A-class)"
