from pydoc import locate

from tinydi.exceptions import InvalidOperation


FADepends = locate("fastapi.Depends")


def fastapi_depends(container, key, **kwargs):
    """
    Wraps TinyDI dependency with fastapi.Depends
    """
    if FADepends is None:
        raise InvalidOperation("Cannot import Depends from fastapi. Make sure Fastapi is installed")
    return FADepends(container.fn(key), **kwargs)
