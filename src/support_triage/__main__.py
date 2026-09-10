"""Point d'entrée du paquet : permet `python -m support_triage`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
