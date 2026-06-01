#! /usr/bin/env python3

"""
Maigret entrypoint
"""

import asyncio
import sys

from .maigret import main

if __name__ == "__main__":
    # First Ctrl+C is caught inside main() (search loop → falls through to
    # report generation with partial results). A *second* Ctrl+C during
    # report generation, or any uncaught Ctrl+C before the search loop runs,
    # reaches asyncio.run as KeyboardInterrupt — exit with the conventional
    # SIGINT code (130) instead of dumping a traceback.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nMaigret interrupted.', file=sys.stderr)
        sys.exit(130)
