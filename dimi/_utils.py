from types import FunctionType
from typing import Annotated, Callable, Iterator, Union, get_args, get_origin, get_type_hints


__all__ = ["get_declared_dependencies"]


class _BaseUnknownType:
    pass


class _DefaultTypeDict(dict):
    _absent = object()

    @staticmethod
    def _get_unknown_type(key):
        return type("UnknownType", (_BaseUnknownType,), {"name": key})

    def __getitem__(self, key):
        if (item := super().get(key, self._absent)) == self._absent:
            return self._get_unknown_type(key)
        return item


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
    dep_locals = _DefaultTypeDict(named_deps)
    annotations = get_type_hints(kallable, localns=dep_locals, include_extras=True)
    for arg, annotation in annotations.items():
        if arg == "return" or get_origin(annotation) != Annotated or not (args := get_args(annotation)):
            continue
        type_, meta, *_ = args
        if isinstance(meta, str):
            yield arg, meta
            continue
        if issubclass(type_, _BaseUnknownType):
            type_ = type_.name
        if meta == ...:
            meta = type_
        yield arg, meta
