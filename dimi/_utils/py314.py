from typing import Annotated, Any, ForwardRef, get_args, get_origin


def drop_string_generics(hints: dict[str, Any]) -> dict[str, Any]:
    """
    Drop generic part from string annotatiions
    Annotated["Cls[int]", ...] -> Annotated["Cls", ...]
    """
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
