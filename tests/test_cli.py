"""Tests for artemis_api.cli."""

import runpy
import sys
from unittest.mock import MagicMock

import pytest

from artemis_api import __version__
from artemis_api.cli import main
from artemis_api.exceptions import ArtemisAPIError
from artemis_api.profiles import ProfileManager


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_help_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    assert "usage: artemis" in capsys.readouterr().out


def test_missing_config_returns_exit_code_1(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ARTEMIS_APP_ID", raising=False)
    monkeypatch.delenv("ARTEMIS_API_KEY", raising=False)
    monkeypatch.setattr(
        "artemis_api.cli.Config",
        lambda **kwargs: _raise_configuration_error(),
    )
    code = main(["chat"])
    assert code == 1
    assert "Error:" in capsys.readouterr().err


def _raise_configuration_error():
    from artemis_api.exceptions import ConfigurationError

    raise ConfigurationError("missing stuff")


def test_default_command_is_chat(monkeypatch):
    mock_repl = MagicMock()
    monkeypatch.setattr("artemis_api.cli.ArtemisChatRepl", lambda client: mock_repl)
    monkeypatch.setattr("artemis_api.cli.ArtemisClient", MagicMock())
    monkeypatch.setattr(
        "artemis_api.cli.Config",
        lambda **kwargs: MagicMock(validate=MagicMock()),
    )
    code = main(["--app-id", "aa-1", "--api-key", "kg-1"])
    assert code == 0
    mock_repl.run.assert_called_once()


def test_chat_command_explicit(monkeypatch):
    mock_repl = MagicMock()
    monkeypatch.setattr("artemis_api.cli.ArtemisChatRepl", lambda client: mock_repl)
    monkeypatch.setattr("artemis_api.cli.ArtemisClient", MagicMock())
    monkeypatch.setattr(
        "artemis_api.cli.Config",
        lambda **kwargs: MagicMock(validate=MagicMock()),
    )
    code = main(["chat", "--app-id", "aa-1", "--api-key", "kg-1"])
    assert code == 0


def test_chat_command_propagates_api_error(monkeypatch, capsys):
    mock_repl = MagicMock()
    mock_repl.run.side_effect = ArtemisAPIError("network down")
    monkeypatch.setattr("artemis_api.cli.ArtemisChatRepl", lambda client: mock_repl)
    monkeypatch.setattr("artemis_api.cli.ArtemisClient", MagicMock())
    monkeypatch.setattr(
        "artemis_api.cli.Config",
        lambda **kwargs: MagicMock(validate=MagicMock()),
    )
    code = main(["chat", "--app-id", "aa-1", "--api-key", "kg-1"])
    assert code == 1
    assert "network down" in capsys.readouterr().err


def test_keyboard_interrupt_returns_130(monkeypatch):
    monkeypatch.setattr(
        "artemis_api.cli._handle_chat_command", MagicMock(side_effect=KeyboardInterrupt)
    )
    code = main(["chat", "--app-id", "aa-1", "--api-key", "kg-1"])
    assert code == 130


def test_profile_add_with_all_flags(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: ProfileManager(path=manager_path))
    code = main(
        [
            "profile",
            "add",
            "work",
            "--app-id",
            "aa-1",
            "--api-key",
            "kg-1",
            "--host",
            "https://example.com",
        ]
    )
    assert code == 0
    assert "Saved profile 'work'" in capsys.readouterr().out
    manager = ProfileManager(path=manager_path)
    assert manager.get_profile("work")["app_id"] == "aa-1"


def test_profile_add_preserves_explicit_zero_timeout(tmp_path, monkeypatch):
    manager_path = tmp_path / "profiles.json"
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: ProfileManager(path=manager_path))
    code = main(
        ["profile", "add", "work", "--app-id", "aa-1", "--api-key", "kg-1", "--timeout", "0"]
    )
    assert code == 0
    manager = ProfileManager(path=manager_path)
    assert manager.get_profile("work")["timeout"] == 0.0


def test_profile_command_reports_oserror_as_clean_message(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    manager = ProfileManager(path=manager_path)
    manager.add_profile("work", app_id="aa-1")

    def raise_oserror(name):
        raise OSError("disk full")

    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: manager)
    monkeypatch.setattr(manager, "delete_profile", raise_oserror)
    code = main(["profile", "delete", "work"])
    assert code == 1
    assert "disk full" in capsys.readouterr().err


def test_profile_add_prompts_for_missing_required_fields(tmp_path, monkeypatch):
    manager_path = tmp_path / "profiles.json"
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: ProfileManager(path=manager_path))
    monkeypatch.setattr("builtins.input", MagicMock(return_value="aa-prompted"))
    monkeypatch.setattr("getpass.getpass", MagicMock(return_value="kg-prompted"))
    code = main(["profile", "add", "work"])
    assert code == 0
    manager = ProfileManager(path=manager_path)
    profile = manager.get_profile("work")
    assert profile["app_id"] == "aa-prompted"
    assert profile["api_key"] == "kg-prompted"


def test_profile_list_masks_keys_by_default(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    manager = ProfileManager(path=manager_path)
    manager.add_profile("work", app_id="aa-1", api_key="kg-1234567890")
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: manager)
    code = main(["profile", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "kg-1234567890" not in out
    assert "kg-12345****" in out


def test_profile_list_shows_keys_with_flag(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    manager = ProfileManager(path=manager_path)
    manager.add_profile("work", app_id="aa-1", api_key="kg-1234567890")
    manager.set_default("work")
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: manager)
    code = main(["profile", "list", "--show-keys"])
    assert code == 0
    out = capsys.readouterr().out
    assert "kg-1234567890" in out
    assert "(default)" in out


def test_profile_list_empty(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: ProfileManager(path=manager_path))
    code = main(["profile", "list"])
    assert code == 0
    assert "No profiles saved." in capsys.readouterr().out


def test_profile_delete(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    manager = ProfileManager(path=manager_path)
    manager.add_profile("work", app_id="aa-1")
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: manager)
    code = main(["profile", "delete", "work"])
    assert code == 0
    assert "Deleted profile 'work'" in capsys.readouterr().out


def test_profile_delete_unknown_returns_error(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: ProfileManager(path=manager_path))
    code = main(["profile", "delete", "missing"])
    assert code == 1
    assert "Error:" in capsys.readouterr().err


def test_profile_set_default(tmp_path, monkeypatch, capsys):
    manager_path = tmp_path / "profiles.json"
    manager = ProfileManager(path=manager_path)
    manager.add_profile("work", app_id="aa-1")
    monkeypatch.setattr("artemis_api.cli.ProfileManager", lambda: manager)
    code = main(["profile", "set-default", "work"])
    assert code == 0
    assert "Default profile set to 'work'" in capsys.readouterr().out
    assert manager.get_default_profile_name() == "work"


def test_main_module_invocation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["artemis", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("artemis_api", run_name="__main__")
    assert exc_info.value.code == 0
