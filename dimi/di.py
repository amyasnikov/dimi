import inspect
from asyncio import iscoroutinefunction
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from types import FunctionType
from typing import Annotated, Any, Callable, Iterator, Union, get_args, get_origin

from ._integrations import fastapi_depends
from ._storage import DepChainMap, DepStorage
from .dependency import Dependency, KWarg
from .exceptions import InvalidOperation
from .scopes import Factory, Scope


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
            kwargs = self._get_kwargs_for_func(value.func)
            self._deps[key] = Dependency(value, tuple(kwargs))
            if isinstance(key, (FunctionType, type)) and key.__name__ != "<lambda>":
                self._named_deps[key.__name__] = key

    def __getitem__(self, key: Callable) -> Any:
        """
        Retrieve the dependency from the container, resolve sub-dependencies and return the call result
        """
        return self.fn(key)()

    def fn(self, key: Callable) -> Callable[[], Any]:
        """
        Retrieve the dependency from the container, resolve sub-dependencies
        and return it in a form of a callable object with no arguments
        """
        return self._deps.fn(key)

    def _make_kwarg(self, param_name, annotation):
        type_, kallable, *_ = get_args(annotation)
        if kallable == ...:
            return KWarg(param_name, type_)
        extra_attrs = ""
        if isinstance(kallable, str):
            kallable, *attrs = kallable.split(".", maxsplit=1)
            kallable = self._named_deps[kallable]
            extra_attrs = attrs[0] if attrs else ""
        return KWarg(param_name, kallable, extra_attrs)

    def _get_kwargs_for_func(self, kallable):
        if isinstance(kallable, type):
            if not isinstance(kallable.__init__, FunctionType):
                return []
            kallable = kallable.__init__
        for arg, annotation in kallable.__annotations__.items():
            if get_origin(annotation) is Annotated:
                yield self._make_kwarg(arg, annotation)

    def _select_kwargs(self, func, func_args, func_kwargs, kwargs):
        arguments = inspect.signature(func).bind_partial(*func_args, **func_kwargs).arguments
        return (kwarg for kwarg in kwargs if kwarg.name not in arguments)

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

            di_keys = list(self._get_kwargs_for_func(func))
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
