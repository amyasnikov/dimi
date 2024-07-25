from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from contextvars import ContextVar


class Scope(ABC):
    __slots__ = ["func"]

    def __init__(self, func):
        self.func = func

    def __eq__(self, other):
        return type(self) == type(other) and self.func == other.func

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(self.func)})"

    @property
    def is_async(self):
        return iscoroutinefunction(self.func)

    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass


class Factory(Scope):
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class Singleton(Scope):
    _UNSET = object()
    __slots__ = ["func", "cached_value"]

    def __init__(self, func):
        super().__init__(func)
        self.cached_value = self._UNSET

    @property
    def __call__(self):
        return self._acall if self.is_async else self._call

    def _call(self, *args, **kwargs):
        if self.get_value() is self._UNSET:
            result = self.func(*args, **kwargs)
            self.set_value(result)
        return self.get_value()

    async def _acall(self, *args, **kwargs):
        if self.get_value() is self._UNSET:
            result = await self.func(*args, **kwargs)
            self.set_value(result)
        return self.get_value()

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
