import inspect
from dataclasses import dataclass, field

from .exceptions import InvalidDependency
from .scopes import Scope


@dataclass(slots=True)
class Dependency:
    scope: Scope
    keywords: dict
    has_async_deps: bool = False
    _copied: bool = field(default=False, repr=False)

    def __post_init__(self):
        if self._copied:
            return
        self.has_async_deps = any(isinstance(dep, Dependency) and dep.is_async for dep in self.keywords.values())
        if not self.is_async and self.has_async_deps:
            raise InvalidDependency(f"Sync callable {self.scope.func} cannot have async dependencies")
        required_params = {
            param.name
            for param in inspect.signature(self.scope.func).parameters.values()
            if param.default == inspect.Parameter.empty
        }
        if leftovers := required_params - self.keywords.keys():
            raise InvalidDependency(f"{self.scope.func} has undefined params: {leftovers}")

    def __call__(self):
        return self.scope(**self.keywords)

    def copy(self):
        return type(self)(self.scope, self.keywords.copy(), self.has_async_deps, True)

    @property
    def is_async(self):
        return self.scope.is_async

    def _resolve_sync(self):
        def dfs(dependency, top=False):
            for param, value in dependency.keywords.items():
                if isinstance(value, Dependency):
                    dependency.keywords[param] = dfs(value.copy())
            if not dependency.is_async and not dependency.has_async_deps and not top:
                return dependency()
            return dependency

        return dfs(self.copy(), top=True)

    async def _resolve_async(self):
        async def dfs(dependency, top=False):
            for param, value in dependency.keywords.items():
                if isinstance(value, Dependency) and value.is_async:
                    dependency.keywords[param] = await dfs(value)
            if not top:
                return await dependency()
            return dependency

        return await dfs(self, top=True)

    def call(self):
        result = self._resolve_sync()()
        self.scope.set_value(result)
        return result

    async def acall(self):
        resolved = await self._resolve_sync()._resolve_async()
        result = await resolved()
        self.scope.set_value(result)
        return result
