from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from contextvars import ContextVar
from functools import wraps


class Scope(ABC):
    __slots__ = ["func"]

    def __init__(self, func):
        self.func = func

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(self.func)})"

    @property
    def is_async(self):
        return iscoroutinefunction(self.func)

    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass

    @abstractmethod
    def set_value(self, value):
        pass


class Factory(Scope):
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def set_value(self, value): ...


class Singleton(Scope):
    _UNSET = object()
    __slots__ = ["func", "cached_value"]

    def __init__(self, func):
        super().__init__(func)
        self.cached_value = self._UNSET

    def __call__(self, *args, **kwargs):
        if (value := self.get_value()) is self._UNSET:
            return self.func(*args, **kwargs)
        if self.is_async:

            async def f():
                return value

            return wraps(self.func)(f)()
        return value

    def set_value(self, value):
        self.cached_value = value

    def get_value(self):
        return self.cached_value


class Context(Singleton):
    def __init__(self, func):
        Scope.__init__(self, func)
        self.cached_value = ContextVar("cached_value", default=self._UNSET)

    def get_value(self):
        return self.cached_value.get()

    def set_value(self, value):
        self.cached_value.set(value)
