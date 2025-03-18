import inspect
from dataclasses import dataclass
from typing import Annotated, Callable, ForwardRef, Generic, TypeVar

import pytest

from dimi._utils import cleanup_signature, get_declared_dependencies


@pytest.fixture
def named_deps_extra():
    class A:
        pass

    return {"A": A}


T = TypeVar("T")


class AddedClass(Generic[T]): ...


def f_cls(arg: Annotated[AddedClass, ...]): ...
def f_cls_postponed(arg: Annotated["AddedClass", ...]): ...
def f_cls_postponed_nonexisting(arg: Annotated["DontExist", ...]): ...  # noqa
def f_cls_forwardref(arg: Annotated[ForwardRef("AddedClass"), ...]): ...
def f_cls_postponed_class(arg: Annotated["PostponedClass", ...]): ...
def f_cls_explicit(arg: Annotated[AddedClass, "AddedClass"]): ...
def f_a(arg: Annotated["A", ...]): ...  # noqa
def f_callable(arg: Annotated[Callable, AddedClass]): ...
def f_generic_class(arg: Annotated[AddedClass[int], ...]): ...


class PostponedClass: ...


def f_func(arg: Annotated[int, f_cls]): ...


@pytest.mark.parametrize(
    "func, named_deps, result",
    [
        (f_cls, {}, AddedClass),
        (f_cls_postponed, {"AddedClass": AddedClass}, AddedClass),
        (f_cls_postponed, {}, "AddedClass"),
        (f_cls_postponed_nonexisting, {}, "DontExist"),
        (f_cls_forwardref, {"AddedClass": AddedClass}, AddedClass),
        (f_cls_forwardref, {}, "AddedClass"),
        (f_cls_explicit, {}, "AddedClass"),
        (f_cls_postponed_class, {}, "PostponedClass"),
        (f_a, {}, ".A"),
        (f_func, {}, f_cls),
        (f_callable, {}, AddedClass),
        (f_generic_class, {}, AddedClass),
    ],
)
def test_get_declared_deps(func, named_deps, result, named_deps_extra):
    if isinstance(result, str) and result.startswith("."):
        result = named_deps_extra[result[1:]]
    named_deps |= named_deps_extra
    assert dict(get_declared_dependencies(func, named_deps)) == {"arg": result}


def f_annotated_no_args(arg: Annotated): ...
def f_many_args(a: int, b: Annotated[AddedClass, ...], c: Annotated[int, "some_string"]): ...


class SomeClass:
    def __init__(self, arg1: Annotated[AddedClass, ...], arg2: Annotated["NotExisting", ...]): ...  # noqa


@dataclass
class SomeDataClass:
    arg1: Annotated[AddedClass, ...]
    arg2: Annotated["NotExisting", ...]  # noqa


@pytest.mark.parametrize(
    "func, named_deps, result",
    [
        (f_annotated_no_args, {}, {}),
        (f_many_args, {}, {"b": AddedClass, "c": "some_string"}),
        (SomeClass, {}, {"arg1": AddedClass, "arg2": "NotExisting"}),
        (SomeDataClass, {}, {"arg1": AddedClass, "arg2": "NotExisting"}),
    ],
)
def test_declared_deps_specialcases(func, named_deps, result):
    assert dict(get_declared_dependencies(func, named_deps)) == result


def test_generic_class_string():
    def f_generic_class_string(arg: Annotated["SomeGenericClass[int]", ...]): ...  # noqa

    declared_deps = dict(get_declared_dependencies(f_generic_class_string, {}))

    assert declared_deps == {"arg": "SomeGenericClass"}


def no_annotated(param1, param2: int, param3: SomeDataClass): ...
def simple_annotated(param1, param2: Annotated[int, ...]): ...
def many_annotated(p1: Annotated[str, ...], p2: Annotated[int, ...], p3: int) -> str: ...
def annotated_args_kwargs(p1, *args: Annotated[int, int], **kwargs: Annotated[str, ...]): ...


@pytest.mark.parametrize(
    "kallable, arguments",
    [
        (no_annotated, ["param1", "param2", "param3"]),
        (simple_annotated, ["param1"]),
        (many_annotated, ["p3"]),
        (annotated_args_kwargs, ["p1"]),
        (SomeDataClass, []),
    ],
)
def test_cleanup_singature(kallable, arguments, preserve_signature):
    preserve_signature(kallable)
    cleanup_signature(kallable)
    assert inspect.signature(kallable).parameters.keys() == set(arguments)
