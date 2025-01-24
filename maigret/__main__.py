#! /usr/bin/env python3

"""
Maigret entrypoint
"""

import asyncio
import resources

from .maigret import main

if __name__ == "__main__":
    asyncio.run(main())
