"""Kore.ai Agent Platform (Artemis) Agentic App API reference.

This module is intentionally free of any CLI/REPL-specific concerns (no
``argparse``, no ``print``/``input``, no logging side effects) so it can be
imported and used standalone by other projects to hand-build requests or
parse responses without pulling in the rest of :mod:`artemis_api`.

Covers the minimal contract needed for a REPL chat client: creating a
session, executing a conversational turn, and terminating a session.
Streaming, async execution, and file attachments are out of scope -- see
the project README for details.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypedDict


class SessionIdentityType(StrEnum):
    """Type discriminator for an item in a ``sessionIdentity`` array.

    Per Kore.ai's session resolution rules, the server checks these in
    priority order: ``SESSION_ID`` (highest) > ``SESSION_REFERENCE`` >
    ``USER_REFERENCE`` (lowest).
    """

    SESSION_ID = "sessionId"
    SESSION_REFERENCE = "sessionReference"
    USER_REFERENCE = "userReference"


class InputType(StrEnum):
    """Type discriminator for an item in an ``input`` array."""

    TEXT = "text"


class SessionIdentityItem(TypedDict):
    """A single entry in a ``sessionIdentity`` array.

    Attributes:
        type: One of the :class:`SessionIdentityType` values.
        value: The identity value (e.g. a session ID or user reference string).
    """

    type: str
    value: str


class InputItem(TypedDict):
    """A single entry in an ``input`` array.

    Attributes:
        type: Always ``"text"`` in this minimal implementation.
        content: The literal text content.
    """

    type: str
    content: str


class CreateSessionRequest(TypedDict, total=False):
    """Request body for ``POST {host}/api/v2/apps/{appId}/environments/{envName}/sessions``.

    Attributes:
        sessionIdentity: Identity items used to create (or resolve) a session.
    """

    sessionIdentity: list[SessionIdentityItem]


class TerminateSessionRequest(TypedDict):
    """Request body for ``POST {host}/api/v2/.../sessions/terminate``.

    Attributes:
        sessionIdentity: Identity items identifying the session to terminate.
    """

    sessionIdentity: list[SessionIdentityItem]


class ExecuteRunRequest(TypedDict, total=False):
    """Request body for ``POST {host}/apps/{appId}/environments/{envName}/runs/execute``.

    Attributes:
        sessionIdentity: Identity items identifying the session to use.
        input: The user's input for this turn.
    """

    sessionIdentity: list[SessionIdentityItem]
    input: list[InputItem]


@dataclass(frozen=True)
class SessionInfo:
    """Normalized result of a create-session call.

    Attributes:
        session_id: The server-assigned session identifier. Used as the
            highest-priority identity in subsequent calls.
        session_reference: The client-facing session reference, if the API
            returned one (it may be ``None``).
        welcome_text: Any welcome message text returned in the session's
            ``output`` array, if present.
    """

    session_id: str
    session_reference: str | None
    welcome_text: str | None


def build_sessions_url(host: str, app_id: str, env_name: str) -> str:
    """Build the URL for the create-session endpoint.

    Args:
        host: Base host for the Agent Platform environment, e.g.
            ``"https://agents.kore.ai"``.
        app_id: The Agentic App's ID.
        env_name: The deployment environment name (e.g. ``"production"``).

    Returns:
        The full URL for ``POST .../sessions``.

    Examples:
        >>> build_sessions_url("https://agents.kore.ai", "aa-1", "production")
        'https://agents.kore.ai/api/v2/apps/aa-1/environments/production/sessions'
    """
    return f"{host}/api/v2/apps/{app_id}/environments/{env_name}/sessions"


def build_terminate_url(host: str, app_id: str, env_name: str) -> str:
    """Build the URL for the terminate-session endpoint.

    Args:
        host: Base host for the Agent Platform environment.
        app_id: The Agentic App's ID.
        env_name: The deployment environment name.

    Returns:
        The full URL for ``POST .../sessions/terminate``.

    Examples:
        >>> build_terminate_url("https://agents.kore.ai", "aa-1", "production")
        'https://agents.kore.ai/api/v2/apps/aa-1/environments/production/sessions/terminate'
    """
    return f"{host}/api/v2/apps/{app_id}/environments/{env_name}/sessions/terminate"


def build_execute_url(host: str, app_id: str, env_name: str) -> str:
    """Build the URL for the execute-run endpoint.

    Note this endpoint deliberately has no ``/api/v2/`` prefix, unlike the
    sessions endpoints -- this matches the documented API contract.

    Args:
        host: Base host for the Agent Platform environment.
        app_id: The Agentic App's ID.
        env_name: The deployment environment name.

    Returns:
        The full URL for ``POST .../runs/execute``.

    Examples:
        >>> build_execute_url("https://agents.kore.ai", "aa-1", "production")
        'https://agents.kore.ai/apps/aa-1/environments/production/runs/execute'
    """
    return f"{host}/apps/{app_id}/environments/{env_name}/runs/execute"


def build_headers(api_key: str) -> dict[str, str]:
    """Build the standard headers used on every API request.

    Args:
        api_key: The scoped API key for the target Agentic App.

    Returns:
        A headers dict with ``x-api-key`` and ``Content-Type`` set.

    Examples:
        >>> build_headers("secret")
        {'x-api-key': 'secret', 'Content-Type': 'application/json'}
    """
    return {"x-api-key": api_key, "Content-Type": "application/json"}


def build_session_identity(
    user_reference: str,
    session_id: str | None = None,
    session_reference: str | None = None,
) -> list[SessionIdentityItem]:
    """Build a ``sessionIdentity`` array using Kore.ai's priority resolution rules.

    ``userReference`` is always included (needed for ownership validation on
    the server side). If a ``session_id`` is known it's included as the
    highest-priority identity; otherwise a ``session_reference`` is used if
    available.

    Args:
        user_reference: A stable client-generated identifier for the caller.
        session_id: The session ID returned by a prior create-session call, if known.
        session_reference: The session reference to use if ``session_id`` is not known.

    Returns:
        A list of session identity items, in the order the server expects.

    Examples:
        >>> build_session_identity("u-1", session_id="s-1")
        [{'type': 'userReference', 'value': 'u-1'}, {'type': 'sessionId', 'value': 's-1'}]
    """
    identity: list[SessionIdentityItem] = [
        {"type": SessionIdentityType.USER_REFERENCE.value, "value": user_reference}
    ]

    if session_id:
        identity.append({"type": SessionIdentityType.SESSION_ID.value, "value": session_id})
    elif session_reference:
        identity.append(
            {"type": SessionIdentityType.SESSION_REFERENCE.value, "value": session_reference}
        )

    return identity


def build_input(text: str) -> list[InputItem]:
    """Build an ``input`` array from a single piece of text.

    Args:
        text: The input text content.

    Returns:
        A one-item input list.

    Examples:
        >>> build_input("Hello!")
        [{'type': 'text', 'content': 'Hello!'}]
    """
    return [{"type": InputType.TEXT.value, "content": text}]


def _extract_welcome_text(output: list[dict[str, Any]] | None) -> str | None:
    """Extract welcome-message text from a session/execute response's ``output`` array.

    Args:
        output: The ``output`` array from an API response, if present.

    Returns:
        The joined text of every ``type: "text"`` item, or ``None`` if there
        was no text output.
    """
    if not output:
        return None
    texts = [item.get("content", "") for item in output if item.get("type") == "text"]
    joined = "\n".join(text for text in texts if text)
    return joined or None


def normalize_session_response(payload: dict[str, Any]) -> SessionInfo:
    """Normalize a create-session API response into a :class:`SessionInfo`.

    The API has been observed to sometimes nest session fields under a
    top-level ``"session"`` key and sometimes return them flat, and
    ``sessionReference`` may be ``null`` even when a session was created
    successfully. This function accounts for both shapes and always
    preserves any welcome message found in the response's ``output`` array.

    Args:
        payload: The parsed JSON response body from the create-session call.

    Returns:
        A :class:`SessionInfo` with the session ID, optional session
        reference, and optional welcome text.

    Raises:
        KeyError: If the response contains neither a top-level nor nested
            ``sessionId``.
    """
    session_obj = payload.get("session", payload)

    session_id = session_obj.get("sessionId") or payload.get("sessionId")
    if not session_id:
        raise KeyError("Response did not contain a sessionId")

    session_reference = session_obj.get("sessionReference") or payload.get("sessionReference")
    welcome_text = _extract_welcome_text(payload.get("output"))

    return SessionInfo(
        session_id=session_id,
        session_reference=session_reference,
        welcome_text=welcome_text,
    )


def extract_output_text(payload: dict[str, Any]) -> str:
    """Extract the joined text output from an execute-run API response.

    Args:
        payload: The parsed JSON response body from the execute-run call.

    Returns:
        The joined text of every ``type: "text"`` item in the response's
        ``output`` array, or an empty string if there was none.
    """
    return _extract_welcome_text(payload.get("output")) or ""
