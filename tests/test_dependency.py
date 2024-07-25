import copy
from contextlib import nullcontext
from itertools import count

import pytest

from tinydi.dependency import Dependency
from tinydi.exceptions import InvalidDependency
from tinydi.scopes import Factory, Singleton


def sync_f(a, b, c, d=4):
    pass


async def async_f(a, b, c):
    pass


sync_dep = Dependency(Factory(lambda: None), {})

async_dep = Dependency(Factory(async_f), {"a": 1, "b": 1, "c": 1})


@pytest.mark.parametrize(
    "func, keywords, error",
    [
        pytest.param(sync_f, {"a": 1, "b": 2, "c": 3}, None, id="simple-sync"),
        pytest.param(async_f, {"a": 1, "b": 2, "c": 3}, None, id="simple-async"),
        pytest.param(sync_f, {"a": 1, "b": 2, "d": 3}, InvalidDependency, id="sync-missing-var"),
        pytest.param(async_f, {"a": 1, "b": 2}, InvalidDependency, id="async-missing-var"),
        pytest.param(sync_f, {"a": 1, "b": 2, "c": sync_dep}, None, id="sync-sync-subdep"),
        pytest.param(async_f, {"a": 1, "b": 2, "c": sync_dep}, None, id="async-sync-subdep"),
        pytest.param(async_f, {"a": 1, "b": 2, "c": async_dep}, None, id="async-async-subdep"),
        pytest.param(sync_f, {"a": 1, "b": 2, "c": async_dep}, InvalidDependency, id="sync-async-subdep"),
    ],
)
def test_dependency_instantiation(func, keywords, error):
    scope = Factory(func)
    context = pytest.raises(error) if error is not None else nullcontext()
    with context:
        Dependency(scope, keywords)


@pytest.fixture
def sync_dependency():
    counter = count()
    d1 = Dependency(Singleton(lambda: str(next(counter))), keywords={})
    d2 = Dependency(Singleton(lambda a, b: a + b), keywords={"a": "|", "b": d1})
    d3 = Dependency(Singleton(lambda a, b: a + b), keywords={"a": d1, "b": d2})
    d4 = Dependency(Singleton(lambda c, d: f"{c},{d}"), keywords={"c": d3, "d": d2})
    return d4


@pytest.fixture
def async_dependency():
    counter = count()

    async def f11():
        return str(next(counter))

    async def f2(a, b):
        return a + b

    async def f4(c, d):
        return f"{c},{d}"

    d1 = Dependency(Singleton(lambda: str(next(counter))), keywords={})
    d11 = Dependency(Singleton(f11), keywords={})

    d2 = Dependency(Singleton(f2), keywords={"a": d1, "b": d11})
    d3 = Dependency(Singleton(f2), keywords={"a": d2, "b": "|"})
    d4 = Dependency(Singleton(f4), keywords={"c": d2, "d": d3})
    return d4


def test_dependency_call(sync_dependency):
    dependency_copy = copy.deepcopy(sync_dependency)
    result = sync_dependency.call()
    assert result == "0|0,|0"
    assert sync_dependency == dependency_copy


async def test_dependency_acall(async_dependency):
    dependency_copy = copy.deepcopy(async_dependency)
    result = await async_dependency.acall()
    assert result == "01,01|"
    assert async_dependency == dependency_copy
