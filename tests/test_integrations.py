from unittest.mock import Mock

import pytest

from dimi import _integrations
from dimi.exceptions import InvalidOperation


def test_fastapi_depends(monkeypatch, di):
    @di.dependency
    async def f():
        pass

    # Cannot import Depends
    monkeypatch.setattr(_integrations, "FADepends", None)
    with pytest.raises(InvalidOperation):
        assert di.fastapi(f)

    # Can import Depends
    monkeypatch.setattr(_integrations, "FADepends", Mock())
    di.fastapi(f)
    _integrations.FADepends.assert_called_once()
    expected_call = di.fn(f)
    actual_call = _integrations.FADepends.call_args.args[0]
    # functools.partial cannot be compared directly, so the params are compared
    assert expected_call.func == actual_call.func
    assert expected_call.args == actual_call.args
    assert expected_call.keywords == actual_call.keywords
