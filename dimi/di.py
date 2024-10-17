import inspect
from asyncio import iscoroutinefunction
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from typing import Any, Callable, Iterator, Optional, Union

from ._integrations import fastapi_depends
from ._storage import DepChainMap, DepStorage
from ._utils import get_declared_dependencies
from .dependency import Dependency, InjectKWarg, KWarg
from .exceptions import InvalidOperation
from .scopes import Factory, Scope


__all__ = ["Container"]


class Container:
    """
    Dependency Injection container
    """

    default_scope_class = Factory
    fastapi = fastapi_depends

    def __init__(self):
        self._deps = DepStorage()
        self._named_deps = DepChainMap()
        self.lock = Lock()

    def __contains__(self, key: Callable) -> bool:
        return key in self._deps

    def __setitem__(self, key: Callable, value: Callable) -> None:
        """
        Add the dependency to the container
        """
        if not callable(key):
            raise InvalidOperation(f"Cannot add non-callable object to the DI container: {key}")
        with self.lock:
            if not isinstance(value, Scope):
                value = self.default_scope_class(value)
            kwargs = self._get_kwargs_for_func(value.func, kwarg_cls=KWarg)
            self._deps[key] = Dependency(value, tuple(kwargs))
            if key_name := self._get_func_name(key):
                if key_name in self._named_deps and len(self._named_deps.maps) == 1:
                    raise InvalidOperation("The container already contains the dependency with the name {key_name}")
                self._named_deps[key_name] = key

    def __getitem__(self, key: Union[Callable, str]) -> Any:
        """
        Retrieve the dependency from the container, resolve sub-dependencies and return the call result
        """
        if isinstance(key, str):
            if "." in key:
                raise InvalidOperation("Retrieving of properties through __getitem__ is not supported")
            key = self._named_deps[key]
        return self.fn(key)()

    def fn(self, key: Callable) -> Callable[[], Any]:
        """
        Retrieve the dependency from the container, resolve sub-dependencies
        and return it in a form of a callable object with no arguments
        """
        return self._deps.fn(key)

    @staticmethod
    def _get_func_name(func: Callable) -> Optional[str]:
        if not (name := getattr(func, "__name__", None)):
            return None
        return name if not name == "<lambda>" else None

    def _make_kwarg(self, param_name, dependency, kwarg_cls):
        extra_attrs = ""
        if isinstance(dependency, str):
            dependency, *attrs = dependency.split(".", maxsplit=1)
            dependency = self._named_deps.get(dependency, dependency)
            extra_attrs = attrs[0] if attrs else ""
        elif dependency not in self._deps and (dep_name := self._get_func_name(dependency)):
            dependency = dep_name
        return kwarg_cls(param_name, dependency, extra_attrs)

    def _get_kwargs_for_func(self, kallable, kwarg_cls):
        for arg, dependency in get_declared_dependencies(kallable, self._named_deps):
            yield self._make_kwarg(arg, dependency, kwarg_cls)

    def _select_kwargs(self, func, func_args, func_kwargs, kwargs):
        arguments = inspect.signature(func).bind_partial(*func_args, **func_kwargs).arguments
        for kwarg in kwargs:
            if kwarg.name not in arguments:
                if isinstance(kwarg.func, str):
                    kwarg.func = self._named_deps[kwarg.func]
                yield kwarg

    @property
    def inject(self):
        """
        Resolve and inject the dependencies defined via `Annotated[SomeType, some_callable]`
        at the time of a function call
        """

        def decorator(func):
            def sync_wrapper(*args, **kwargs):
                extra_kwargs = self._select_kwargs(func, args, kwargs, di_keys)
                kwargs |= {kw.name: kw.getattrs(self._deps.resolve(kw.func)) for kw in extra_kwargs}
                return func(*args, **kwargs)

            async def async_wrapper(*args, **kwargs):
                extra_kwargs = self._select_kwargs(func, args, kwargs, di_keys)
                kwargs |= {kw.name: kw.getattrs(await self._deps.aresolve(kw.func)) for kw in extra_kwargs}
                return await func(*args, **kwargs)

            di_keys = list(self._get_kwargs_for_func(func, kwarg_cls=InjectKWarg))
            return wraps(func)(async_wrapper if iscoroutinefunction(func) else sync_wrapper)

        return decorator

    @property
    def dependency(self):
        """
        Put the dependency (callable) into the DI container and bind it with sub-dependencies
        marked via `Annotated[SomeType, some_callable]`
        """

        def outer(func=None, *, scope: type[Scope] = self.default_scope_class):
            def decorator(f):
                self[f] = scope(f)
                return f

            if func is None:
                return decorator
            self[func] = scope(func)
            return func

        return outer

    @contextmanager
    def override(self, overridings: Union[dict[Callable, Callable], None] = None) -> Iterator[None]:
        """
        Make the snapshot of the container, apply overridings and restore the state at exit
        """
        with self.lock:
            self._deps = self._deps.new_child()
            self._named_deps = self._named_deps.new_child()
        try:
            if overridings:
                for dep_key, dep_value in overridings.items():
                    self[dep_key] = dep_value
            yield
        finally:
            with self.lock:
                self._named_deps = self._named_deps.parents
                self._deps = self._deps.parents
