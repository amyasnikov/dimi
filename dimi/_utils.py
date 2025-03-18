import inspect
from collections import defaultdict
from contextlib import suppress
from types import FunctionType
from typing import (
    Annotated,
    Callable,
    Hashable,
    Iterable,
    Iterator,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)


__all__ = ["cleanup_signature", "get_declared_dependencies", "graph_from_edges"]


class _BaseUnknownType:
    def __class_getitem__(cls, item):
        """
        Resolves MyClass[int] to just MyClass
        """
        return cls.name


class _DefaultTypeDict(dict):
    _absent = object()

    @staticmethod
    def _get_unknown_type(key):
        return type("UnknownType", (_BaseUnknownType,), {"name": key})

    def __getitem__(self, key):
        if (item := super().get(key, self._absent)) == self._absent:
            return self._get_unknown_type(key)
        return item


def _get_type_hints(kallable, localns=None, globalns=None) -> dict[str, type]:
    localns = _DefaultTypeDict(localns or {})
    with suppress(TypeError):
        return get_type_hints(kallable, localns=localns, globalns=globalns, include_extras=True)
    return {}


def get_declared_dependencies(
    kallable: Callable, named_deps: dict[str, Callable]
) -> Iterator[tuple[str, Union[str, Callable]]]:
    """
    Extract all the dependencies defined via Annotated[] from a function/class
    String-based dependency will be converted to python object if possible
    """
    if isinstance(kallable, type):
        if not isinstance(kallable.__init__, FunctionType):
            return
        kallable = kallable.__init__
    annotations = _get_type_hints(kallable, localns=named_deps)
    for arg, annotation in annotations.items():
        if arg == "return" or get_origin(annotation) != Annotated or not (args := get_args(annotation)):
            continue
        type_, meta, *_ = args
        if isinstance(meta, str):
            yield arg, meta
            continue
        if is_subclass(type_, _BaseUnknownType):
            type_ = type_.name
        if meta == ...:
            meta = origin if (origin := get_origin(type_)) else type_
        yield arg, meta


def is_subclass(cls: type, class_or_tuple: Union[type, tuple]) -> bool:
    return issubclass(cls, class_or_tuple) if isinstance(cls, type) else False


def graph_from_edges(edges: Iterable[tuple[Hashable, Hashable]]) -> dict[Hashable, list[Hashable]]:
    """
    Build a dict-based graph from a group of (A, B) edges
    """
    graph = defaultdict(list)
    for start, end in edges:
        graph[start].append(end)
    return graph


def cleanup_signature(kallable: Callable) -> None:
    """
    Removes all Annotated[] arguments from kallable.__signature__
    """
    if isinstance(kallable, type):
        if not isinstance(kallable.__init__, FunctionType):
            return
        kallable = kallable.__init__

    original_sig = inspect.signature(kallable)
    new_params = [param for param in original_sig.parameters.values() if not get_origin(param.annotation) == Annotated]
    new_sig = inspect.Signature(new_params)
    kallable.__signature__ = new_sig
