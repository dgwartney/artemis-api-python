"""Interactive REPL chat loop for artemis_api."""

from __future__ import annotations

from collections.abc import Callable

from artemis_api.client import ArtemisClient
from artemis_api.exceptions import ArtemisAPIError

try:
    import readline  # noqa: F401  # enables arrow-key/history editing for input()
except ImportError:  # pragma: no cover - not available on some platforms (e.g. base Windows)
    pass

_EXIT_WORDS = {"exit", "quit"}
_HELP_TEXT = """\
Available commands:
  /help    Show this help message
  /reset   Terminate the current session and start a new one
  exit     End the chat session
  quit     End the chat session
Anything else you type is sent to the agent."""


class ArtemisChatRepl:
    """A REPL that maintains one Artemis session and forwards input to it.

    Attributes:
        client: The :class:`~artemis_api.client.ArtemisClient` used to talk to the API.
    """

    def __init__(self, client: ArtemisClient) -> None:
        """Initialize the REPL.

        Args:
            client: The client used to talk to the API. The REPL reads
                ``client.config.user_reference`` for display rather than
                accepting a separately-passed value, so it can never drift
                from what the client actually sends to the API.
        """
        self.client = client
        self._session_id: str | None = None
        self._commands: dict[str, Callable[[], None]] = {
            "/help": self._cmd_help,
            "/reset": self._cmd_reset,
        }

    def run(self) -> None:
        """Run the REPL loop until the user exits or input is exhausted."""
        self._start_session(announce=False)
        print(f"Connected as {self.client.config.user_reference}. Type /help for commands.")

        try:
            while True:
                try:
                    line = input("You: ").strip()
                except EOFError:
                    print()
                    break
                except KeyboardInterrupt:
                    print()
                    continue

                if not line:
                    continue
                if line.lower() in _EXIT_WORDS:
                    break
                if line.lower() in self._commands:
                    self._commands[line.lower()]()
                    continue

                self._send(line)
        finally:
            self._terminate_session()

    def _start_session(self, *, announce: bool) -> None:
        """Create a new session and optionally print its welcome message.

        Args:
            announce: If ``True``, print a "started a new session" banner
                before any welcome message (used by ``/reset``).
        """
        session = self.client.create_session()
        self._session_id = session.session_id
        if announce:
            print("Started a new session.")
        if session.welcome_text:
            print(f"Agent: {session.welcome_text}")

    def _terminate_session(self) -> None:
        """Best-effort terminate the current session, if one is active."""
        if self._session_id:
            self.client.terminate_session(self._session_id)
            self._session_id = None

    def _send(self, text: str) -> None:
        """Send one line of input to the agent and print the reply.

        A failed turn is reported to the user but does not end the REPL.

        Args:
            text: The user's input text.
        """
        assert self._session_id is not None
        try:
            reply = self.client.execute_turn(self._session_id, text)
        except ArtemisAPIError as exc:
            print(f"Error: {exc}")
            return
        print(f"Agent: {reply}")

    def _cmd_help(self) -> None:
        """Print the list of available REPL commands."""
        print(_HELP_TEXT)

    def _cmd_reset(self) -> None:
        """Terminate the current session and start a fresh one."""
        self._terminate_session()
        self._start_session(announce=True)
