"""Command-line entry point for artemis_api.

Provides the ``artemis`` console script: a ``chat`` subcommand (also the
default when no subcommand is given) that runs the REPL, and a ``profile``
subcommand for managing named connection profiles.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Sequence

from artemis_api import __version__
from artemis_api.client import ArtemisClient
from artemis_api.config import Config
from artemis_api.exceptions import ArtemisAPIError, ConfigurationError
from artemis_api.logging_config import setup_logging
from artemis_api.profiles import ProfileManager, mask_api_key
from artemis_api.repl import ArtemisChatRepl

_PROFILE_ARG_FIELDS = ("host", "app_id", "env_name", "api_key", "user_reference", "timeout")


def _build_parent_parser() -> argparse.ArgumentParser:
    """Build the parent parser carrying global options shared by all subcommands.

    Returns:
        An ``add_help=False`` parser meant to be used via ``parents=[...]``.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--host", default=None, help="Agent Platform host (default: agents.kore.ai)"
    )
    parser.add_argument("--app-id", default=None, help="Agentic App ID")
    parser.add_argument("--env-name", default=None, help="Deployment environment name")
    parser.add_argument("--api-key", default=None, help="API key")
    parser.add_argument("--user-reference", default=None, help="Stable client/user identifier")
    parser.add_argument("--timeout", type=float, default=None, help="Request timeout in seconds")
    parser.add_argument("--profile", default=None, help="Named profile to use")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-level", default="WARNING", help="Logging level")
    parser.add_argument("--log-file", default=None, help="Optional path to a log file")
    return parser


def _build_parser() -> argparse.ArgumentParser:
    """Build the full ``artemis`` argument parser with its subcommands.

    Returns:
        The top-level parser.
    """
    parent = _build_parent_parser()
    parser = argparse.ArgumentParser(prog="artemis", parents=[parent])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("chat", parents=[parent], help="Start an interactive chat session")

    profile_parser = subparsers.add_parser("profile", help="Manage connection profiles")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)

    add_parser = profile_subparsers.add_parser("add", help="Create or update a profile")
    add_parser.add_argument("name")
    add_parser.add_argument("--host", default=None)
    add_parser.add_argument("--app-id", default=None)
    add_parser.add_argument("--env-name", default=None)
    add_parser.add_argument("--api-key", default=None)
    add_parser.add_argument("--user-reference", default=None)
    add_parser.add_argument("--timeout", type=float, default=None)

    list_parser = profile_subparsers.add_parser("list", help="List saved profiles")
    list_parser.add_argument("--show-keys", action="store_true", help="Show unmasked API keys")

    delete_parser = profile_subparsers.add_parser("delete", help="Delete a profile")
    delete_parser.add_argument("name")

    set_default_parser = profile_subparsers.add_parser(
        "set-default", help="Set the default profile"
    )
    set_default_parser.add_argument("name")

    return parser


_PROMPT_REQUIRED_FIELDS = ("app_id", "api_key")


def _handle_profile_add(args: argparse.Namespace, manager: ProfileManager) -> int:
    """Handle ``profile add``, prompting interactively for required fields not given on the CLI.

    ``app_id`` and ``api_key`` are prompted for if missing (the API key via
    ``getpass`` so it isn't echoed to the terminal or shell history).
    Optional fields (``host``, ``env_name``, ``user_reference``, ``timeout``)
    are only stored if explicitly passed as flags, since they already have
    sane defaults in :class:`~artemis_api.config.Config`.

    Args:
        args: Parsed CLI arguments.
        manager: The profile manager to write to.

    Returns:
        Process exit code.
    """
    fields = {}
    for field in _PROFILE_ARG_FIELDS:
        value = getattr(args, field, None)
        if value is None and field in _PROMPT_REQUIRED_FIELDS:
            value = getpass.getpass("api_key: ") if field == "api_key" else input(f"{field}: ")
        if value:
            fields[field] = value
    manager.add_profile(args.name, **fields)
    print(f"Saved profile {args.name!r}.")
    return 0


def _handle_profile_list(args: argparse.Namespace, manager: ProfileManager) -> int:
    """Handle ``profile list``.

    Args:
        args: Parsed CLI arguments.
        manager: The profile manager to read from.

    Returns:
        Process exit code.
    """
    profiles = manager.list_profiles()
    default_name = manager.get_default_profile_name()
    if not profiles:
        print("No profiles saved.")
        return 0
    for name, fields in profiles.items():
        marker = " (default)" if name == default_name else ""
        api_key = fields.get("api_key")
        key_display = api_key if args.show_keys else mask_api_key(api_key)
        print(
            f"{name}{marker}: host={fields.get('host')} "
            f"app_id={fields.get('app_id')} api_key={key_display}"
        )
    return 0


def _handle_profile_command(args: argparse.Namespace) -> int:
    """Dispatch a ``profile`` subcommand.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Process exit code.
    """
    manager = ProfileManager()
    try:
        if args.profile_command == "add":
            return _handle_profile_add(args, manager)
        if args.profile_command == "list":
            return _handle_profile_list(args, manager)
        if args.profile_command == "delete":
            manager.delete_profile(args.name)
            print(f"Deleted profile {args.name!r}.")
            return 0
        if args.profile_command == "set-default":
            manager.set_default(args.name)
            print(f"Default profile set to {args.name!r}.")
            return 0
    except ConfigurationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1  # pragma: no cover - unreachable: argparse enforces a valid profile_command choice


def _handle_chat_command(args: argparse.Namespace) -> int:
    """Build a :class:`Config`/:class:`ArtemisClient` and run the REPL.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Process exit code.
    """
    try:
        config = Config(
            profile=args.profile,
            host=args.host,
            app_id=args.app_id,
            env_name=args.env_name,
            api_key=args.api_key,
            user_reference=args.user_reference,
            timeout=args.timeout,
        )
        config.validate()
    except ConfigurationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    client = ArtemisClient(config)
    try:
        ArtemisChatRepl(client).run()
    except ArtemisAPIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``artemis`` CLI.

    Args:
        argv: Command-line arguments, excluding the program name. Defaults
            to ``sys.argv[1:]``.

    Returns:
        The process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        args.command = "chat"

    setup_logging(log_level=args.log_level, log_file=args.log_file, verbose=args.verbose)

    try:
        if args.command == "profile":
            return _handle_profile_command(args)
        return _handle_chat_command(args)
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
