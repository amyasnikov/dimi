import operator
import sys
from asyncio import iscoroutinefunction
from dataclasses import dataclass, field, replace
from inspect import Parameter, signature
from typing import Any, Callable, ClassVar, Union

from .exceptions import InvalidDependency
from .scopes import Scope


__all__ = ["KWarg", "InjectKWarg", "PartResolvedDependency", "Dependency"]


_slots = {"slots": True} if sys.version_info >= (3, 10) else {}


class _IsAsyncMixin:
    @property
    def is_async(self) -> bool:
        return self.scope.is_async


class _KWargMixin:
    def copy(self, **overrides) -> "KWarg":
        return replace(self, **overrides)

    def getattrs(self, value) -> Any:
        return operator.attrgetter(self.extra_attrs)(value) if self.extra_attrs else value


@dataclass(**_slots, frozen=True)
class KWarg(_KWargMixin):
    name: str
    func: Callable
    extra_attrs: str = ""


@dataclass(**_slots)
class InjectKWarg(_KWargMixin):
    name: str
    func: Union[Callable, str]
    extra_attrs: str = ""


@dataclass(**_slots)
class PartResolvedDependency(_IsAsyncMixin):
    scope: Scope
    unresolved: tuple[KWarg, ...] = field(default_factory=tuple)
    under_resolving: list[KWarg] = field(default_factory=list)
    resolved: dict[str, Any] = field(default_factory=dict)

    def __call__(self) -> Any:
        return self.scope(**self.resolved)

    @property
    def is_resolved(self) -> bool:
        return not self.unresolved and not self.under_resolving


@dataclass(**_slots, frozen=True)
class Dependency(_IsAsyncMixin):
    scope: Scope
    subdeps: tuple[KWarg, ...]

    _partially_resolved_cls: ClassVar[type] = PartResolvedDependency

    def __post_init__(self):
        func_params = signature(self.scope.func).parameters.values()
        required_params = {
            param.name
            for param in func_params
            if param.default == Parameter.empty and param.kind not in (Parameter.VAR_KEYWORD, Parameter.VAR_POSITIONAL)
        }
        leftovers = required_params - {kwarg.name for kwarg in self.subdeps}
        leftovers |= {
            param.name
            for param in func_params
            if param.kind == Parameter.POSITIONAL_ONLY and param.default == Parameter.empty
        }
        if leftovers:
            raise InvalidDependency(f"{self.scope.func} has undefined params: {leftovers}")

        if self.has_async_deps and not self.is_async:
            raise InvalidDependency(f"Sync function {self.scope.func} cannot have async dependencies")

    def partially_resolved(self):
        return self._partially_resolved_cls(self.scope, unresolved=self.subdeps)

    @property
    def has_async_deps(self) -> bool:
        return any(iscoroutinefunction(kwarg.func) for kwarg in self.subdeps)
