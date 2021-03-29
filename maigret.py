#!/usr/bin/env python3
import asyncio
import sys

from maigret.maigret import main


def run():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print('Maigret is interrupted.')
        sys.exit(1)


if __name__ == "__main__":
    run()