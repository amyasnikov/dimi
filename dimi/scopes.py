import copy
from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from contextvars import ContextVar
from threading import RLock

from .exceptions import InvalidOperation


class Scope(ABC):
    """
    Wrapper for a callable which may optionally cache its value (see implementations)
    """

    __slots__ = ["func"]

    def __init__(self, func):
        self.func = func
        if not callable(func):
            raise InvalidOperation(f"Cannot make Scope out of a non-callable object: {func}")

    def __eq__(self, other):
        return type(self) == type(other) and self.func == other.func

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(self.func)})"

    @property
    def is_async(self):
        return iscoroutinefunction(self.func)

    @abstractmethod
    def __call__(self, *args, **kwargs): ...


class Factory(Scope):
    """
    Default wrapper. Does nothing
    """

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class Cacheable(Scope):
    _UNSET = object()
    __slots__ = ["func", "_cached_value"]

    def __init__(self, func):
        super().__init__(func)
        self._cached_value = self.setup_init_value()

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

    @abstractmethod
    def setup_init_value(self):
        """
        Set the initial value for the cached variable
        """

    @abstractmethod
    def get_value(self):
        """
        Retrieve the value for the cached variable
        """

    @abstractmethod
    def set_value(self, value):
        """
        Set the value for the cached variable
        """


class LockedCacheable(Cacheable):
    __slots__ = ["func", "_cached_value", "_lock"]

    def __init__(self, func):
        super().__init__(func)
        self._lock = RLock()

    def _call(self, *args, **kwargs):
        with self._lock:
            return super()._call(*args, **kwargs)

    async def _acall(self, *args, **kwargs):
        with self._lock:
            return await super()._acall(*args, **kwargs)

    def __deepcopy__(self, memo):
        result = type(self)(func=copy.deepcopy(self.func, memo))
        result._cached_value = copy.deepcopy(self._cached_value, memo)
        return result


class Singleton(LockedCacheable):
    """
    Caches first result of a function call for the whole lifetime of the app
    """

    def setup_init_value(self):
        return self._UNSET

    def set_value(self, value):
        self._cached_value = value

    def get_value(self):
        return self._cached_value


class Context(Cacheable):
    """
    Caches the result of a function call into `contextvars.ContextVar`
    """

    def setup_init_value(self):
        return ContextVar("_cached_value", default=self._UNSET)

    def get_value(self):
        return self._cached_value.get()

    def set_value(self, value):
        self._cached_value.set(value)
