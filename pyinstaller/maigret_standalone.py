#!/usr/bin/env python3
import asyncio
import platform
import sys

import maigret


DOUBLE_CLICK_INTRO = """\
Maigret runs from the command line. You can:

  - call it from cmd/PowerShell:  maigret_standalone.exe USERNAME [options]
  - or enter a username below for a default search.

Full options:    maigret_standalone.exe --help
Documentation:   https://maigret.readthedocs.io/
"""


def _launched_by_double_click() -> bool:
    # On Windows, Explorer spawns a fresh console just for our process, so
    # GetConsoleProcessList returns 1. When launched from an existing cmd /
    # PowerShell session the count is >= 2 (the shell is attached too).
    if platform.system() != "Windows":
        return False
    if len(sys.argv) > 1:
        return False
    try:
        import ctypes

        buf = (ctypes.c_uint * 4)()
        count = ctypes.windll.kernel32.GetConsoleProcessList(buf, 4)
        return count <= 1
    except Exception:
        return False


def _pause() -> None:
    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass


def _prompt_for_username() -> str:
    try:
        return input("Username to search: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def main() -> None:
    if not _launched_by_double_click():
        asyncio.run(maigret.cli())
        return

    print(DOUBLE_CLICK_INTRO)
    username = _prompt_for_username()

    if not username:
        print(
            "\nNo username entered. Re-run with one, e.g.\n"
            "    maigret_standalone.exe alice"
        )
        _pause()
        return

    # Inject the username so maigret's argparse sees it like a normal CLI run.
    sys.argv = [sys.argv[0], username]
    try:
        asyncio.run(maigret.cli())
    finally:
        _pause()


if __name__ == "__main__":
    main()
