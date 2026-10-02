from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        yield c
