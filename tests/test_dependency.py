from contextlib import nullcontext

import pytest

from dimi.dependency import Dependency, KWarg
from dimi.exceptions import InvalidDependency
from dimi.scopes import Factory


def sync_f(c, d=4): ...
async def async_f(a): ...
def f_args(*args): ...
def f_kwargs(**kwargs): ...
def f_full(a, *args, b=4, **kwargs): ...
def f_empty(): ...
def f_pos_only(a, /): ...


@pytest.mark.parametrize(
    "func, keywords, error",
    [
        pytest.param(sync_f, {"c": lambda: None}, None, id="simple"),
        pytest.param(sync_f, {}, InvalidDependency, id="sync-missing-var"),
        pytest.param(async_f, {}, InvalidDependency, id="async-missing-var"),
        pytest.param(sync_f, {"a": 1, "b": 2, "c": sync_f}, None, id="sync-sync-subdep"),
        pytest.param(async_f, {"a": 1, "b": 2, "c": sync_f}, None, id="async-sync-subdep"),
        pytest.param(async_f, {"a": 1, "b": 2, "c": async_f}, None, id="async-async-subdep"),
        pytest.param(sync_f, {"a": 1, "b": 2, "c": async_f}, InvalidDependency, id="sync-async-subdep"),
        pytest.param(f_empty, {}, None, id="no-args"),
        pytest.param(f_args, {}, None, id="star-args"),
        pytest.param(f_kwargs, {}, None, id="star-kwargs"),
        pytest.param(f_full, {"a": 1}, None, id="all-kind-of-args"),
        pytest.param(f_pos_only, {"a": 1}, InvalidDependency, id="positional-only-error"),
    ],
)
def test_dependency_instantiation(func, keywords, error):
    kwargs = (KWarg(k, v) for k, v in keywords.items())
    scope = Factory(func)
    context = pytest.raises(error) if error is not None else nullcontext()
    with context:
        Dependency(scope, tuple(kwargs))
