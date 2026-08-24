"""Shared pytest fixtures for artemis_api's test suite."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

import pytest

from artemis_api.client import ArtemisClient
from artemis_api.config import Config
from artemis_api.profiles import ProfileManager


class FakeHTTPResponse:
    """A minimal stand-in for the object returned by ``urlopen``."""

    def __init__(self, body: dict, status: int = 200) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self._status = status

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self._status


@pytest.fixture
def profiles_path(tmp_path):
    """Return a throwaway path for a profiles.json file."""
    return tmp_path / "profiles.json"


@pytest.fixture
def profile_manager(profiles_path):
    """A ProfileManager backed by a temporary file."""
    return ProfileManager(path=profiles_path)


@pytest.fixture
def config():
    """A Config with dummy values and no profile lookup."""
    return Config(
        host="https://example.kore.ai",
        app_id="aa-test",
        env_name="production",
        api_key="kg-testkey1234567890",
        user_reference="u-test",
        timeout=5,
    )


@pytest.fixture
def client(config):
    """An ArtemisClient built from the dummy config fixture."""
    return ArtemisClient(config)


@pytest.fixture
def fake_urlopen():
    """Patch urllib.request.urlopen; yields a function to set the next response."""
    responses = []

    def _urlopen(request, timeout=None):
        return responses.pop(0)

    def _queue(body: dict, status: int = 200) -> None:
        responses.append(FakeHTTPResponse(body, status))

    with patch("urllib.request.urlopen", side_effect=_urlopen):
        yield _queue


def make_http_error(url, code, body: dict | None = None):
    """Build a urllib.error.HTTPError with an optional JSON body."""
    import urllib.error

    fp = BytesIO(json.dumps(body).encode("utf-8")) if body is not None else BytesIO(b"")
    return urllib.error.HTTPError(url=url, code=code, msg="error", hdrs=None, fp=fp)
