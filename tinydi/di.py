import inspect
from asyncio import iscoroutinefunction
from collections import ChainMap
from contextlib import contextmanager, suppress
from functools import wraps
from threading import Lock
from types import FunctionType
from typing import Annotated, get_args, get_origin

from .dependency import Dependency
from .exceptions import InvalidOperation, UnknownDependency
from .integrations import fastapi_depends
from .scopes import Factory, Scope


class TinyDI:
    default_scope_class = Factory
    fastapi = fastapi_depends

    def __init__(self):
        self._deps = ChainMap()
        self.lock = Lock()

    def _get(self, key):
        with suppress(KeyError):
            return self._deps[key]
        raise UnknownDependency(key)

    def __contains__(self, key):
        return key in self._deps

    def __setitem__(self, key, value):
        if not callable(key):
            raise InvalidOperation(f"Cannot add non-callable object to the DI container: {key}")
        with self.lock:
            if not isinstance(value, Scope):
                value = self.default_scope_class(value)
            injectables = self._get_factories_for_func(value.func)
            kwargs = dict(self._kwargs_to_inject(value.func, (), {}, injectables))
            self._deps[key] = Dependency(value, kwargs)

    def __getitem__(self, key):
        return self.fn(key)()

    def fn(self, key):
        return self._get(key).fn()

    def _get_factories_for_func(self, callable):
        injectable_factories = []
        if isinstance(callable, type):
            if not isinstance(callable.__init__, FunctionType):
                return []
            callable = callable.__init__
        for arg, annotation in callable.__annotations__.items():
            if get_origin(annotation) is Annotated:
                annotation_args = get_args(annotation)
                factory = annotation_args[1] if annotation_args[1] != ... else annotation_args[0]
                injectable_factories.append((arg, self._get(factory)))
        return injectable_factories

    @staticmethod
    def _kwargs_to_inject(func, args, kwargs, factories):
        bound_args = inspect.signature(func).bind_partial(*args, **kwargs)
        arguments = bound_args.arguments
        return ((k, v) for k, v in factories if k not in arguments)

    @property
    def inject(self):
        def decorator(func):
            def sync_wrapper(*args, **kwargs):
                injectables = self._kwargs_to_inject(func, args, kwargs, injectable_factories)
                kwargs |= {param: dependency.call() for param, dependency in injectables}
                return func(*args, **kwargs)

            async def async_wrapper(*args, **kwargs):
                injectables = self._kwargs_to_inject(func, args, kwargs, injectable_factories)
                kwargs |= {param: await dependency.acall() for param, dependency in injectables}
                return await func(*args, **kwargs)

            injectable_factories = self._get_factories_for_func(func)
            return wraps(func)(async_wrapper if iscoroutinefunction(func) else sync_wrapper)

        return decorator

    @property
    def dependency(self):
        def outer(func=None, *, scope=self.default_scope_class):
            def decorator(f):
                self[f] = scope(f)
                return f

            if func is None:
                return decorator
            self[func] = scope(func)
            return func

        return outer

    @contextmanager
    def override(self):
        self._deps = self._deps.new_child()
        try:
            yield
        finally:
            self._deps = self._deps.parents
