"""Allows running the CLI via ``python -m artemis_api``."""

import sys

from artemis_api.cli import main

if __name__ == "__main__":
    sys.exit(main())
