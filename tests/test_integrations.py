from unittest.mock import Mock

import pytest

from dimi import integrations
from dimi.exceptions import InvalidOperation


def test_fastapi_depends(monkeypatch, di):
    @di.dependency
    async def f():
        pass

    # Cannot import Depends
    monkeypatch.setattr(integrations, "FADepends", None)
    with pytest.raises(InvalidOperation):
        assert di.fastapi(f)

    # Can import Depends
    monkeypatch.setattr(integrations, "FADepends", Mock())
    di.fastapi(f)
    integrations.FADepends.assert_called_once_with(di.fn(f))
