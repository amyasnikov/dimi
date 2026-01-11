from collections import ChainMap, defaultdict
from contextlib import suppress
from functools import partial
from inspect import iscoroutinefunction
from typing import Any, Callable, Iterator

from ._utils import graph_from_edges
from .dependency import Dependency, PartResolvedDependency
from .exceptions import InvalidOperation, UnknownDependency


class DepChainMap(ChainMap):
    def __missing__(self, key):
        raise UnknownDependency(key)


class DepStorage(DepChainMap):
    partial_dependency_cls = PartResolvedDependency

    def __setitem__(self, key: Callable, value: Dependency) -> None:
        copy = self.new_child({key: value})
        if copy._has_cycle(key):
            raise InvalidOperation(f"Cannot add dependency {key}, it causes a cycle")
        return super().__setitem__(key, value)

    def _resolve_sync(self, key) -> PartResolvedDependency:
        def dfs(dependency, top=False):
            for kwarg in dependency.unresolved:
                subdep = dfs(self[kwarg.func].partially_resolved())
                if isinstance(subdep, self.partial_dependency_cls):
                    dependency.under_resolving.append(kwarg.copy(func=subdep))
                else:
                    dependency.resolved[kwarg.name] = kwarg.getattrs(subdep)
            dependency.unresolved = ()
            return dependency if top or dependency.is_async or not dependency.is_resolved else dependency()

        return dfs(self[key].partially_resolved(), top=True)

    async def _resolve_async(self, key: Callable) -> PartResolvedDependency:
        async def dfs(dependency, top=False):
            for kwarg in dependency.under_resolving:
                resolved = await dfs(kwarg.func)
                dependency.resolved[kwarg.name] = kwarg.getattrs(resolved)
            dependency.under_resolving = []
            if not top:
                return await dependency()
            return dependency

        dependency = self._resolve_sync(key)
        return await dfs(dependency, top=True)

    def _has_cycle(self, key) -> bool:
        colors = defaultdict(int)

        def dfs(key):
            if (color := colors[key]) == 1:
                raise ValueError
            if color == 2:
                return
            colors[key] = 1
            for kwarg in self[key].subdeps:
                dfs(kwarg.func)
            colors[key] = 2

        with suppress(ValueError):
            dfs(key)
            return False
        return True

    def _graph_edges(self) -> Iterator[tuple[Callable, Callable]]:
        for func, dep in self.items():
            for kwarg in dep.subdeps:
                yield func, kwarg.func

    def resolve(self, key: Callable) -> Any:
        return self._resolve_sync(key)()

    async def aresolve(self, key: Callable) -> Any:
        dep = await self._resolve_async(key)
        return await dep() if dep.is_async else dep()

    def fn(self, key):
        func = self.aresolve if iscoroutinefunction(key) else self.resolve
        return partial(func, key=key)

    def clear_cache(self, *keys: Callable) -> None:
        def dfs(func):
            if func not in visited and (dep := self.get(func)):
                visited.add(func)
                for subdep in reversed_graph.get(func, []):
                    dfs(subdep)
                dep.scope.clear_cache()

        visited = set()

        reversed_graph = graph_from_edges((b, a) for a, b in self._graph_edges())
        for key in keys:
            dfs(key)
