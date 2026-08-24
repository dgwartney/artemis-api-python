"""Tests for artemis_api.api_reference."""

import ast
import importlib.util
from pathlib import Path

import pytest

from artemis_api import api_reference
from artemis_api.api_reference import SessionInfo
from artemis_api.exceptions import APIResponseError


def test_build_sessions_url():
    assert (
        api_reference.build_sessions_url("https://agents.kore.ai", "aa-1", "production")
        == "https://agents.kore.ai/api/v2/apps/aa-1/environments/production/sessions"
    )


def test_build_terminate_url():
    assert (
        api_reference.build_terminate_url("https://agents.kore.ai", "aa-1", "production")
        == "https://agents.kore.ai/api/v2/apps/aa-1/environments/production/sessions/terminate"
    )


def test_build_execute_url_has_no_api_v2_prefix():
    url = api_reference.build_execute_url("https://agents.kore.ai", "aa-1", "production")
    assert url == "https://agents.kore.ai/apps/aa-1/environments/production/runs/execute"
    assert "/api/v2/" not in url


def test_build_headers():
    assert api_reference.build_headers("secret") == {
        "x-api-key": "secret",
        "Content-Type": "application/json",
    }


def test_build_session_identity_user_reference_only():
    identity = api_reference.build_session_identity("u-1")
    assert identity == [{"type": "userReference", "value": "u-1"}]


def test_build_session_identity_prefers_session_id_over_reference():
    identity = api_reference.build_session_identity(
        "u-1", session_id="s-1", session_reference="ref-1"
    )
    assert identity == [
        {"type": "userReference", "value": "u-1"},
        {"type": "sessionId", "value": "s-1"},
    ]


def test_build_session_identity_falls_back_to_session_reference():
    identity = api_reference.build_session_identity("u-1", session_reference="ref-1")
    assert identity == [
        {"type": "userReference", "value": "u-1"},
        {"type": "sessionReference", "value": "ref-1"},
    ]


def test_build_input():
    assert api_reference.build_input("hello") == [{"type": "text", "content": "hello"}]


def test_normalize_session_response_flat_shape():
    payload = {
        "sessionId": "s-1",
        "sessionReference": "ref-1",
        "output": [{"type": "text", "content": "Welcome!"}],
    }
    info = api_reference.normalize_session_response(payload)
    assert info == SessionInfo(session_id="s-1", session_reference="ref-1", welcome_text="Welcome!")


def test_normalize_session_response_nested_under_session_key():
    payload = {
        "session": {"sessionId": "s-1", "sessionReference": "ref-1"},
        "output": [{"type": "text", "content": "Welcome!"}],
    }
    info = api_reference.normalize_session_response(payload)
    assert info.session_id == "s-1"
    assert info.session_reference == "ref-1"
    assert info.welcome_text == "Welcome!"


def test_normalize_session_response_null_session_reference():
    payload = {"sessionId": "s-1", "sessionReference": None}
    info = api_reference.normalize_session_response(payload)
    assert info.session_reference is None


def test_normalize_session_response_no_welcome_message():
    payload = {"sessionId": "s-1"}
    info = api_reference.normalize_session_response(payload)
    assert info.welcome_text is None


def test_normalize_session_response_ignores_non_text_output():
    payload = {"sessionId": "s-1", "output": [{"type": "other", "content": "ignored"}]}
    info = api_reference.normalize_session_response(payload)
    assert info.welcome_text is None


def test_normalize_session_response_raises_without_session_id():
    with pytest.raises(APIResponseError):
        api_reference.normalize_session_response({})


def test_normalize_session_response_null_session_key_falls_back_to_flat_shape():
    payload = {"session": None, "sessionId": "s-1", "sessionReference": "ref-1"}
    info = api_reference.normalize_session_response(payload)
    assert info.session_id == "s-1"
    assert info.session_reference == "ref-1"


def test_extract_output_text_joins_multiple_text_items():
    payload = {"output": [{"type": "text", "content": "a"}, {"type": "text", "content": "b"}]}
    assert api_reference.extract_output_text(payload) == "a\nb"


def test_extract_output_text_empty_when_no_output():
    assert api_reference.extract_output_text({}) == ""


def test_module_has_no_cli_dependency():
    """api_reference.py must stay importable without pulling in argparse/cli/repl."""
    source_path = Path(api_reference.__file__)
    tree = ast.parse(source_path.read_text())
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module.split(".")[0])

    assert "argparse" not in imported_names
    assert not any(name.endswith(("cli", "repl")) for name in imported_names)
    assert importlib.util.find_spec("artemis_api.api_reference") is not None
