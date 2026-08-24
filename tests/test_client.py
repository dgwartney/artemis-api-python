"""Tests for artemis_api.client."""

import urllib.error

import pytest

from artemis_api.exceptions import (
    APIRequestError,
    APIResponseError,
    ArtemisTimeoutError,
    AuthenticationError,
    ValidationError,
)

from .conftest import make_http_error


def test_create_session_success(client, fake_urlopen):
    fake_urlopen(
        {
            "sessionId": "s-1",
            "sessionReference": "ref-1",
            "output": [{"type": "text", "content": "Welcome!"}],
        }
    )
    session = client.create_session()
    assert session.session_id == "s-1"
    assert session.welcome_text == "Welcome!"


def test_execute_turn_success(client, fake_urlopen):
    fake_urlopen({"output": [{"type": "text", "content": "Hi there"}]})
    reply = client.execute_turn("s-1", "hello")
    assert reply == "Hi there"


def test_execute_turn_raises_validation_error_on_blank_text(client):
    with pytest.raises(ValidationError):
        client.execute_turn("s-1", "   ")


def test_execute_turn_raises_validation_error_on_empty_text(client):
    with pytest.raises(ValidationError):
        client.execute_turn("s-1", "")


def test_terminate_session_success(client, fake_urlopen):
    fake_urlopen({})
    client.terminate_session("s-1")  # should not raise


def test_terminate_session_swallows_errors(client, monkeypatch):
    def raise_error(request, timeout=None):
        raise make_http_error("https://example.kore.ai", 500)

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    client.terminate_session("s-1")  # should not raise


def test_post_maps_401_to_authentication_error(client, monkeypatch):
    def raise_error(request, timeout=None):
        raise make_http_error("https://example.kore.ai", 401, {"error": {"message": "bad key"}})

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    with pytest.raises(AuthenticationError, match="bad key"):
        client.create_session()


def test_post_maps_429_to_api_request_error(client, monkeypatch):
    def raise_error(request, timeout=None):
        raise make_http_error("https://example.kore.ai", 429)

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    with pytest.raises(APIRequestError, match="Rate limited"):
        client.create_session()


def test_post_maps_404_with_message_to_api_response_error(client, monkeypatch):
    def raise_error(request, timeout=None):
        raise make_http_error("https://example.kore.ai", 404, {"error": {"message": "not found"}})

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    with pytest.raises(APIResponseError, match="not found"):
        client.create_session()


def test_post_maps_500_without_body_to_api_request_error(client, monkeypatch):
    def raise_error(request, timeout=None):
        raise make_http_error("https://example.kore.ai", 500)

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    with pytest.raises(APIRequestError, match="status 500"):
        client.create_session()


def test_post_maps_error_with_unparseable_body(client, monkeypatch):
    import io

    def raise_error(request, timeout=None):
        raise urllib.error.HTTPError(
            url="https://example.kore.ai",
            code=500,
            msg="error",
            hdrs=None,
            fp=io.BytesIO(b"not json"),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    with pytest.raises(APIRequestError, match="status 500"):
        client.create_session()


def test_post_maps_timeout_error(client, monkeypatch):
    def raise_timeout(request, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr("urllib.request.urlopen", raise_timeout)
    with pytest.raises(ArtemisTimeoutError):
        client.create_session()


def test_post_maps_urlerror_wrapping_timeout(client, monkeypatch):
    def raise_wrapped_timeout(request, timeout=None):
        raise urllib.error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr("urllib.request.urlopen", raise_wrapped_timeout)
    with pytest.raises(ArtemisTimeoutError):
        client.create_session()


def test_post_maps_connection_error(client, monkeypatch):
    def raise_url_error(request, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", raise_url_error)
    with pytest.raises(APIRequestError, match="Failed to reach"):
        client.create_session()


def test_client_as_context_manager(client, fake_urlopen):
    fake_urlopen({"sessionId": "s-1"})
    with client as ctx_client:
        assert ctx_client is client
        ctx_client.create_session()
