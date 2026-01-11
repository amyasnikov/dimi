import inspect
import sys
from collections import defaultdict
from contextlib import suppress
from types import FunctionType
from typing import (
    Annotated,
    Callable,
    ForwardRef,
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
    def __init__(self, *args, **kwargs):
        pass

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

    def __contains__(self, key):
        return True


def _get_type_hints(kallable, names=None) -> dict[str, type]:
    def drop_string_generics(hints):
        res = hints.copy()
        for key, value in res.items():
            if not get_origin(value) == Annotated:
                continue
            type_, *rest = get_args(value)
            if not isinstance(type_, ForwardRef):
                continue
            type_ = type_.__forward_arg__
            if isinstance(type_, str) and type_.endswith("]"):
                new_type = ForwardRef(type_.split("[", maxsplit=1)[0])
                res[key] = Annotated[new_type, *rest]
        return res

    names_dict = _DefaultTypeDict(names or {})
    with suppress(TypeError):
        # Python 3.14 get_type_hints() breaks on undefined string genererics like Annotated["Cls[int]", ...]
        # so we need to create a dummy function with the same annotations but without generics
        if sys.version_info >= (3, 14):
            f = lambda: 1  # noqa: E731
            f.__annotations__ = drop_string_generics(getattr(kallable, "__annotations__", {}))
            return get_type_hints(f, localns=None, globalns=names_dict, include_extras=True)
        else:
            return get_type_hints(kallable, localns=names_dict, include_extras=True)
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
    annotations = _get_type_hints(kallable, names=named_deps)
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
