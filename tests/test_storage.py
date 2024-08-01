import string
from collections import namedtuple
from unittest.mock import Mock

import pytest

from dimi._storage import DepStorage
from dimi.dependency import Dependency, KWarg
from dimi.exceptions import InvalidOperation, UnknownDependency
from dimi.scopes import Factory


@pytest.fixture
def storage():
    return DepStorage()


@pytest.fixture
def storage_with_deps(storage):
    def f_a():
        return "a"

    def f_b(arg="b"):
        return arg

    def f_ab(a, b):
        return a + b

    async def f_c():
        return "c"

    async def f_abc(ab, c):
        return ab + c

    kwargs = {
        f_a: (),
        f_b: (),
        f_ab: (KWarg("a", f_a), KWarg("b", f_b)),
        f_c: (),
        f_abc: (KWarg("ab", f_ab), KWarg("c", f_c)),
    }
    for func, subdeps in kwargs.items():
        storage[func] = Dependency(Factory(func), subdeps)
        setattr(storage, func.__name__, func)
    return storage


@pytest.fixture
def storage_from_graph(storage):
    """
    Make storage dependency graph based on standard number-based one
    """

    def mkgraph(graph, start_num):
        functions = {}
        for num in graph:

            def func(**kwargs): ...

            func.__name__ = f"f{num}"
            functions[num] = func

        name_it = iter(string.ascii_letters)
        for num, subnums in graph.items():
            fn = functions[num]
            subfns = (functions[subnum] for subnum in subnums)
            storage[fn] = Dependency(Factory(fn), tuple(KWarg(next(name_it), subfn) for subfn in subfns))
        return storage, functions[start_num]

    return mkgraph


def test_getitem(storage):
    def f(): ...

    def f2(): ...

    dep = Dependency(Factory(f), ())
    storage[f] = Dependency(Factory(f), ())

    assert storage[f] == dep
    with pytest.raises(UnknownDependency):
        storage[f2]


def test_setitem(storage, monkeypatch):
    monkeypatch.setattr(DepStorage, "_has_cycle", Mock(return_value=True))

    def f(): ...

    dep = Dependency(Factory(f), ())
    with pytest.raises(InvalidOperation):
        storage[f] = dep
    assert f not in storage

    storage._has_cycle.return_value = False
    storage[f] = dep
    assert f in storage


@pytest.mark.parametrize(
    "graph, start_num, has_cycle",
    [
        pytest.param({1: []}, 1, False, id="single_node_no_edges"),
        pytest.param({1: [1]}, 1, True, id="single_node_self_loop"),
        pytest.param({1: [2], 2: []}, 1, False, id="two_nodes_no_cycle"),
        pytest.param({1: [2], 2: [1]}, 1, True, id="two_nodes_with_cycle"),
        pytest.param({1: [2], 2: [3], 3: [4], 4: []}, 1, False, id="multiple_nodes_no_cycle"),
        pytest.param({1: [2], 2: [3], 3: [4], 4: [1]}, 1, True, id="multiple_nodes_with_cycle"),
        pytest.param({1: [2], 2: [3, 4], 3: [5], 4: [5], 5: [2]}, 1, True, id="complex_graph_with_cycle"),
        pytest.param({1: [2, 3], 2: [4], 3: [4], 4: [5], 5: []}, 1, False, id="complex_graph_no_cycles"),
        pytest.param({1: [2, 3], 2: [4], 3: [4, 3], 4: []}, 3, True, id="self_loop_larger_graph"),
        pytest.param({1: [2], 2: [3], 3: [4], 4: [2]}, 1, True, id="adding_node_creates_cycle"),
        pytest.param({1: [2], 2: [3], 3: [4], 4: []}, 1, False, id="adding_node_no_cycle"),
        pytest.param({1: [2, 3], 2: [4], 3: [4], 4: []}, 1, False, id="double_visit_no_cycle"),
    ],
)
def test_cycle_detection(graph, start_num, has_cycle, storage_from_graph, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(DepStorage, "_has_cycle", lambda *_: False)
        fn_graph, start_fn = storage_from_graph(graph, start_num)
    assert fn_graph._has_cycle(start_fn) == has_cycle


async def test_resolve(storage_with_deps, subtests):
    sync_resolve = ["f_a", "f_b", "f_ab"]
    async_resolve = ["f_c", "f_abc"]

    for func_name in sync_resolve:
        with subtests.test(id=func_name):
            func = getattr(storage_with_deps, func_name)
            assert storage_with_deps.resolve(func) == func_name.split("_")[1]

    for func_name in async_resolve:
        with subtests.test(id=func_name):
            func = getattr(storage_with_deps, func_name)
            assert await storage_with_deps.aresolve(func) == func_name.split("_")[1]


async def test_resolve_with_attrs(storage):
    def dep():
        return namedtuple("SomeDep", "arg")("a")

    def f_ab_sync(a):
        return a + "b"

    async def f_ac_async(a):
        return a + "c"

    storage[dep] = Dependency(Factory(dep), ())
    storage[f_ab_sync] = Dependency(Factory(f_ab_sync), (KWarg("a", dep, "arg"),))
    storage[f_ac_async] = Dependency(Factory(f_ac_async), (KWarg("a", dep, "arg"),))

    assert storage.resolve(f_ab_sync) == "ab"
    assert await storage.aresolve(f_ac_async) == "ac"
