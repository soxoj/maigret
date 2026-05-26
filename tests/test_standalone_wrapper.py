"""Unit tests for the PyInstaller Windows wrapper.

The wrapper at ``pyinstaller/maigret_standalone.py`` lives outside the
``maigret`` package, so we load it by path.
"""
import importlib.util
import os
import sys
from unittest import mock

import pytest


WRAPPER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    "pyinstaller",
    "maigret_standalone.py",
)


@pytest.fixture
def wrapper():
    spec = importlib.util.spec_from_file_location(
        "maigret_standalone_under_test", WRAPPER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_returns_false_on_non_windows(wrapper):
    with mock.patch.object(wrapper.platform, "system", return_value="Darwin"):
        assert wrapper._launched_by_double_click() is False


def test_returns_false_when_username_argument_present(wrapper):
    # Extra argv => user invoked from a shell with a username; never a double-click.
    with mock.patch.object(wrapper.platform, "system", return_value="Windows"), \
         mock.patch.object(wrapper.sys, "argv", ["maigret_standalone.exe", "alice"]):
        assert wrapper._launched_by_double_click() is False


def test_double_click_detected_when_only_our_process_attached(wrapper):
    fake_ctypes = mock.MagicMock()
    fake_ctypes.windll.kernel32.GetConsoleProcessList.return_value = 1

    with mock.patch.object(wrapper.platform, "system", return_value="Windows"), \
         mock.patch.object(wrapper.sys, "argv", ["maigret_standalone.exe"]), \
         mock.patch.dict(sys.modules, {"ctypes": fake_ctypes}):
        assert wrapper._launched_by_double_click() is True


def test_cmd_invocation_detected_when_shell_also_attached(wrapper):
    fake_ctypes = mock.MagicMock()
    fake_ctypes.windll.kernel32.GetConsoleProcessList.return_value = 2

    with mock.patch.object(wrapper.platform, "system", return_value="Windows"), \
         mock.patch.object(wrapper.sys, "argv", ["maigret_standalone.exe"]), \
         mock.patch.dict(sys.modules, {"ctypes": fake_ctypes}):
        assert wrapper._launched_by_double_click() is False


def test_returns_false_when_console_api_raises(wrapper):
    fake_ctypes = mock.MagicMock()
    fake_ctypes.windll.kernel32.GetConsoleProcessList.side_effect = OSError("boom")

    with mock.patch.object(wrapper.platform, "system", return_value="Windows"), \
         mock.patch.object(wrapper.sys, "argv", ["maigret_standalone.exe"]), \
         mock.patch.dict(sys.modules, {"ctypes": fake_ctypes}):
        assert wrapper._launched_by_double_click() is False


def test_main_runs_cli_when_not_double_click(wrapper):
    sentinel = object()
    with mock.patch.object(wrapper, "_launched_by_double_click", return_value=False), \
         mock.patch.object(wrapper.asyncio, "run") as run_mock, \
         mock.patch.object(wrapper.maigret, "cli", new=mock.Mock(return_value=sentinel)) as cli_mock:
        wrapper.main()

    cli_mock.assert_called_once_with()
    run_mock.assert_called_once_with(sentinel)


def test_main_prompts_and_runs_search_on_double_click(wrapper):
    sentinel = object()
    original_argv = ["maigret_standalone.exe"]
    inputs = iter(["alice", ""])  # username prompt, then pause prompt

    with mock.patch.object(wrapper, "_launched_by_double_click", return_value=True), \
         mock.patch.object(wrapper.sys, "argv", list(original_argv)), \
         mock.patch("builtins.input", side_effect=lambda *_: next(inputs)) as input_mock, \
         mock.patch.object(wrapper.asyncio, "run") as run_mock, \
         mock.patch.object(wrapper.maigret, "cli", new=mock.Mock(return_value=sentinel)):
        wrapper.main()
        # argv was rewritten to feed argparse the entered username.
        assert wrapper.sys.argv == ["maigret_standalone.exe", "alice"]

    run_mock.assert_called_once_with(sentinel)
    assert input_mock.call_count == 2  # username prompt + final pause


def test_main_skips_search_on_empty_username(wrapper):
    inputs = iter(["", ""])  # empty username, then pause prompt

    with mock.patch.object(wrapper, "_launched_by_double_click", return_value=True), \
         mock.patch.object(wrapper.sys, "argv", ["maigret_standalone.exe"]), \
         mock.patch("builtins.input", side_effect=lambda *_: next(inputs)) as input_mock, \
         mock.patch.object(wrapper.asyncio, "run") as run_mock, \
         mock.patch.object(wrapper.maigret, "cli") as cli_mock:
        wrapper.main()

    cli_mock.assert_not_called()
    run_mock.assert_not_called()
    assert input_mock.call_count == 2  # asked for username, then paused


def test_main_pauses_even_when_cli_raises_system_exit(wrapper):
    inputs = iter(["alice", ""])

    with mock.patch.object(wrapper, "_launched_by_double_click", return_value=True), \
         mock.patch.object(wrapper.sys, "argv", ["maigret_standalone.exe"]), \
         mock.patch("builtins.input", side_effect=lambda *_: next(inputs)) as input_mock, \
         mock.patch.object(wrapper.asyncio, "run", side_effect=SystemExit(2)), \
         mock.patch.object(wrapper.maigret, "cli", new=mock.Mock()):
        with pytest.raises(SystemExit):
            wrapper.main()

    # Both inputs should have fired: username prompt + final pause via finally.
    assert input_mock.call_count == 2


def test_main_treats_keyboard_interrupt_at_prompt_as_empty(wrapper):
    def fake_input(*_args, **_kwargs):
        if fake_input.calls == 0:
            fake_input.calls += 1
            raise KeyboardInterrupt
        fake_input.calls += 1
        return ""
    fake_input.calls = 0

    with mock.patch.object(wrapper, "_launched_by_double_click", return_value=True), \
         mock.patch.object(wrapper.sys, "argv", ["maigret_standalone.exe"]), \
         mock.patch("builtins.input", side_effect=fake_input), \
         mock.patch.object(wrapper.asyncio, "run") as run_mock, \
         mock.patch.object(wrapper.maigret, "cli") as cli_mock:
        wrapper.main()

    cli_mock.assert_not_called()
    run_mock.assert_not_called()
