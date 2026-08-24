"""HTTP client for the Kore.ai Agent Platform (Artemis) Agentic App API.

Uses only :mod:`urllib.request` from the standard library -- no third-party
HTTP library is required.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from artemis_api import api_reference
from artemis_api.config import Config
from artemis_api.exceptions import (
    APIRequestError,
    APIResponseError,
    ArtemisTimeoutError,
    AuthenticationError,
    ValidationError,
)
from artemis_api.logging_config import get_logger, log_api_request, log_api_response

_logger = get_logger("client")


class ArtemisClient:
    """Client for creating sessions and executing conversational turns.

    Example:
        >>> from artemis_api import ArtemisClient, Config
        >>> config = Config(host="https://agents.kore.ai", app_id="aa-1", api_key="kg-1")
        >>> client = ArtemisClient(config)  # doctest: +SKIP
        >>> session = client.create_session()  # doctest: +SKIP
        >>> client.execute_turn(session.session_id, "Hello!")  # doctest: +SKIP
    """

    def __init__(self, config: Config) -> None:
        """Initialize the client.

        Args:
            config: Resolved connection configuration.
        """
        self.config = config

    def __enter__(self) -> ArtemisClient:
        """Enter the runtime context; returns ``self``.

        ``urllib.request`` has no persistent connection object to open, so
        this exists purely for symmetry with :meth:`__exit__`.
        """
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Exit the runtime context. No resources need releasing."""
        return None

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST a JSON body and return the parsed JSON response.

        Args:
            url: The full request URL.
            body: The JSON-serializable request body.

        Returns:
            The parsed JSON response body.

        Raises:
            AuthenticationError: On an HTTP 401 response.
            APIResponseError: On any other HTTP >= 400 response with a
                recognizable error body.
            APIRequestError: On any other HTTP >= 400 response, or a
                connection-level failure.
            ArtemisTimeoutError: If the request exceeds ``config.timeout``.
        """
        headers = api_reference.build_headers(self.config.api_key)
        log_api_request(url, "POST", body)

        request = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                status_code = response.getcode()
                raw = response.read()
        except urllib.error.HTTPError as exc:
            self._raise_for_http_error(exc)
        except TimeoutError as exc:
            raise ArtemisTimeoutError(f"Request to {url} timed out") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ArtemisTimeoutError(f"Request to {url} timed out") from exc
            raise APIRequestError(f"Failed to reach {url}: {exc.reason}") from exc

        data = json.loads(raw) if raw else {}
        log_api_response(status_code, data)
        return data

    @staticmethod
    def _raise_for_http_error(exc: urllib.error.HTTPError) -> None:
        """Map an :class:`urllib.error.HTTPError` to an :mod:`artemis_api` exception.

        Args:
            exc: The HTTP error raised by ``urlopen``.

        Raises:
            AuthenticationError: On HTTP 401.
            APIResponseError: When the body contains a recognizable
                ``{"error": {"message": ...}}`` shape.
            APIRequestError: For every other status code.
        """
        raw_body = exc.read()
        message = None
        if raw_body:
            try:
                parsed = json.loads(raw_body)
                message = parsed.get("error", {}).get("message")
            except (json.JSONDecodeError, AttributeError):
                message = None

        if exc.code == 401:
            raise AuthenticationError(message or "Authentication failed", status_code=401) from exc
        if exc.code == 429:
            raise APIRequestError(
                message or "Rate limited; please retry later", status_code=429
            ) from exc
        if message:
            raise APIResponseError(message, status_code=exc.code) from exc
        raise APIRequestError(
            f"Request failed with status {exc.code}", status_code=exc.code
        ) from exc

    def create_session(self) -> api_reference.SessionInfo:
        """Create a new session for this client's configured user reference.

        Returns:
            Normalized session information, including any welcome message.
        """
        url = api_reference.build_sessions_url(
            self.config.host, self.config.app_id, self.config.env_name
        )
        body: dict[str, Any] = {
            "sessionIdentity": api_reference.build_session_identity(self.config.user_reference)
        }
        response = self._post(url, body)
        return api_reference.normalize_session_response(response)

    def execute_turn(self, session_id: str, text: str) -> str:
        """Send one turn of conversation and return the agent's text reply.

        Args:
            session_id: The session ID to execute against (from :meth:`create_session`).
            text: The user's input text.

        Returns:
            The joined text of the agent's response.

        Raises:
            ValidationError: If ``text`` is empty or whitespace-only.
        """
        if not text or not text.strip():
            raise ValidationError("Input text must not be empty.")

        url = api_reference.build_execute_url(
            self.config.host, self.config.app_id, self.config.env_name
        )
        body: dict[str, Any] = {
            "sessionIdentity": api_reference.build_session_identity(
                self.config.user_reference, session_id=session_id
            ),
            "input": api_reference.build_input(text),
        }
        response = self._post(url, body)
        return api_reference.extract_output_text(response)

    def terminate_session(self, session_id: str) -> None:
        """Best-effort session termination; never raises.

        Args:
            session_id: The session ID to terminate.
        """
        url = api_reference.build_terminate_url(
            self.config.host, self.config.app_id, self.config.env_name
        )
        body: dict[str, Any] = {
            "sessionIdentity": api_reference.build_session_identity(
                self.config.user_reference, session_id=session_id
            )
        }
        try:
            self._post(url, body)
        except Exception as exc:  # noqa: BLE001 - deliberately broad; termination is best-effort
            _logger.warning("Failed to terminate session %s: %s", session_id, exc)
