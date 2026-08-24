"""Tests for artemis_api.repl."""

from unittest.mock import MagicMock

import pytest

from artemis_api.api_reference import SessionInfo
from artemis_api.exceptions import APIRequestError
from artemis_api.repl import ArtemisChatRepl


def make_client(user_reference="u-test", welcome_text=None):
    client = MagicMock()
    client.config.user_reference = user_reference
    client.create_session.return_value = SessionInfo(
        session_id="s-1", session_reference=None, welcome_text=welcome_text
    )
    return client


def test_run_prints_welcome_and_connected_banner(monkeypatch, capsys):
    client = make_client(welcome_text="Hi there!")
    monkeypatch.setattr("builtins.input", MagicMock(side_effect=EOFError))
    ArtemisChatRepl(client).run()
    out = capsys.readouterr().out
    assert "Connected as u-test" in out
    assert "Agent: Hi there!" in out
    client.terminate_session.assert_called_once_with("s-1")


def test_run_without_welcome_message(monkeypatch, capsys):
    client = make_client(welcome_text=None)
    monkeypatch.setattr("builtins.input", MagicMock(side_effect=EOFError))
    ArtemisChatRepl(client).run()
    out = capsys.readouterr().out
    assert "Agent:" not in out


def test_run_sends_plain_text_and_prints_reply(monkeypatch, capsys):
    client = make_client()
    client.execute_turn.return_value = "General Kenobi"
    inputs = iter(["Hello there", EOFError()])

    def fake_input(prompt=""):
        value = next(inputs)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr("builtins.input", fake_input)
    ArtemisChatRepl(client).run()
    out = capsys.readouterr().out
    assert "Agent: General Kenobi" in out
    client.execute_turn.assert_called_once_with("s-1", "Hello there")


@pytest.mark.parametrize("exit_word", ["exit", "quit", "EXIT", "Quit"])
def test_run_exits_on_exit_words(monkeypatch, exit_word):
    client = make_client()
    monkeypatch.setattr("builtins.input", MagicMock(return_value=exit_word))
    ArtemisChatRepl(client).run()
    client.terminate_session.assert_called_once_with("s-1")


def test_run_skips_blank_lines(monkeypatch):
    client = make_client()
    inputs = iter(["", "  ", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    ArtemisChatRepl(client).run()
    client.execute_turn.assert_not_called()


def test_run_help_command_prints_help(monkeypatch, capsys):
    client = make_client()
    inputs = iter(["/help", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    ArtemisChatRepl(client).run()
    out = capsys.readouterr().out
    assert "Available commands" in out


def test_run_reset_command_creates_new_session(monkeypatch, capsys):
    client = make_client()
    client.create_session.side_effect = [
        SessionInfo(session_id="s-1", session_reference=None, welcome_text=None),
        SessionInfo(session_id="s-2", session_reference=None, welcome_text="Fresh start"),
    ]
    inputs = iter(["/reset", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    ArtemisChatRepl(client).run()
    out = capsys.readouterr().out
    assert "Started a new session." in out
    assert "Agent: Fresh start" in out
    assert client.terminate_session.call_args_list[0].args == ("s-1",)


def test_run_unknown_slash_command_is_sent_as_text(monkeypatch):
    client = make_client()
    client.execute_turn.return_value = "reply"
    inputs = iter(["/unknown", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    ArtemisChatRepl(client).run()
    client.execute_turn.assert_called_once_with("s-1", "/unknown")


def test_run_failed_turn_does_not_kill_loop(monkeypatch, capsys):
    client = make_client()
    client.execute_turn.side_effect = APIRequestError("boom")
    inputs = iter(["hello", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    ArtemisChatRepl(client).run()
    out = capsys.readouterr().out
    assert "Error: boom" in out
    client.terminate_session.assert_called_once_with("s-1")


def test_run_keyboard_interrupt_continues_loop(monkeypatch, capsys):
    client = make_client()
    inputs = iter([KeyboardInterrupt(), "exit"])

    def fake_input(prompt=""):
        value = next(inputs)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr("builtins.input", fake_input)
    ArtemisChatRepl(client).run()
    client.terminate_session.assert_called_once_with("s-1")
