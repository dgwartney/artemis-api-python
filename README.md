# artemis-api

[![CI](https://github.com/dgwartney/artemis-api-python/actions/workflows/ci.yml/badge.svg)](https://github.com/dgwartney/artemis-api-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/artemis-api.svg)](https://pypi.org/project/artemis-api/)
[![Python versions](https://img.shields.io/pypi/pyversions/artemis-api.svg)](https://pypi.org/project/artemis-api/)

A REPL chat client and library for the Kore.ai Agent Platform ("Artemis") Agentic App API.

## Features

- Interactive REPL chat client (`artemis`) for talking to a deployed Kore.ai Agentic App.
- Named connection profiles for switching between multiple agents/apps.
- Zero runtime dependencies — built entirely on the Python standard library
  (`urllib`, `argparse`, `logging`, `json`).
- Usable as a library: `ArtemisClient` and `Config` can be imported and used directly.
- Fully typed (`py.typed`) and documented.

## Installation

From PyPI:

```bash
pip install artemis-api
# or
uv add artemis-api
```

From GitHub:

```bash
pip install git+https://github.com/dgwartney/artemis-api-python.git
```

From source:

```bash
git clone https://github.com/dgwartney/artemis-api-python.git
cd artemis-api-python
uv sync
```

## Getting your App ID and API key

Before you can use this client, you need an Agentic App deployed in Kore.ai's Agent
Platform Studio, plus an API key scoped to it. This repository does not cover how to
build or configure an agent in Studio — see the official documentation:

- [Deploying an agent](https://docs.kore.ai/agent-platform/deployment) — deploy to an
  environment (`development`, `staging`, or `production`), which becomes your `--env-name`.
- [API key management](https://docs.kore.ai/agent-platform/v1/apis/agentic-apps/api-key-mgmt) —
  create an API scope and generate a key for your app; keys are app-specific and are
  required in the `x-api-key` header.
- [Sessions API reference](https://docs.kore.ai/agent-platform/v1/apis/agentic-apps/sessions)
  and [Runs (execute) API reference](https://docs.kore.ai/agent-platform/v1/apis/agentic-apps/execute) —
  the underlying HTTP contract this client wraps.

Your app's ID (`--app-id`) is visible in Studio once the app is created; the environment
name must match the one you deployed to.

## Quick Start

```bash
# Save a profile for one agent
artemis profile add my-agent --app-id aa-1234 --api-key kg-abcd

# Start chatting using that profile
artemis --profile my-agent
```

Example transcript:

```
$ artemis --profile my-agent
Connected as repl-a1b2c3d4. Type /help for commands.
Agent: Welcome! How can I help you today?
You: What can you do?
Agent: I can help you with...
You: /reset
Started a new session.
You: exit
```

## Configuration

Configuration is resolved in this order of precedence (highest to lowest):

1. Explicit CLI flags (`--host`, `--app-id`, `--env-name`, `--api-key`, `--user-reference`, `--timeout`)
2. Environment variables
3. A named profile (`--profile NAME`)
4. Built-in defaults

| Environment variable       | Default                    |
|-----------------------------|-----------------------------|
| `ARTEMIS_HOST`               | `https://agents.kore.ai`   |
| `ARTEMIS_APP_ID`             | *(required)*                |
| `ARTEMIS_ENV_NAME`           | `production`                |
| `ARTEMIS_API_KEY`            | *(required)*                |
| `ARTEMIS_USER_REFERENCE`     | randomly generated per run  |
| `ARTEMIS_TIMEOUT`            | `30`                         |

Only `app_id` and `api_key` are strictly required — `host` defaults to the standard Kore.ai
Agent Platform domain.

### Managing profiles

Profiles are stored in `~/.artemis/profiles.json` (created with `0700`/`0600` permissions).

```bash
artemis profile add my-agent --app-id aa-1234 --api-key kg-abcd
artemis profile list                 # API keys masked by default
artemis profile list --show-keys     # show unmasked keys
artemis profile set-default my-agent
artemis profile delete my-agent
```

## Usage

### REPL commands

| Command   | Description                                             |
|-----------|----------------------------------------------------------|
| `/help`   | Show available commands                                  |
| `/reset`  | Terminate the current session and start a new one         |
| `exit`    | End the chat session                                      |
| `quit`    | End the chat session                                      |

Anything else you type is sent to the agent as a message.

### CLI flags

Run `artemis --help` or `artemis profile --help` for the full flag reference. Common flags:

- `--profile NAME` — use a saved profile
- `--host`, `--app-id`, `--env-name`, `--api-key`, `--user-reference`, `--timeout` — override
  individual settings
- `-v`/`--verbose` — enable debug logging
- `--log-level LEVEL`, `--log-file PATH` — logging configuration

## Using it as a library

```python
from artemis_api import ArtemisClient, Config

config = Config(host="https://agents.kore.ai", app_id="aa-1234", api_key="kg-abcd")
client = ArtemisClient(config)

session = client.create_session()
print(session.welcome_text)

reply = client.execute_turn(session.session_id, "Hello!")
print(reply)

client.terminate_session(session.session_id)
```

## Development

```bash
uv sync --all-extras
uv run pytest --cov=artemis_api --cov-report=term-missing
uv run ruff check src/ tests/
```

## Publishing

```bash
uv build
uv publish
```

Verify `[project.authors]` in `pyproject.toml` is up to date before publishing.

## License

MIT — see [LICENSE](LICENSE).
