"""Tests for maigret.ai terminal output."""

import os
import subprocess
import sys


def _run_probe(tmp_path, name, lines, encoding):
    """Run a probe in a child process whose streams really use `encoding`.

    Forcing the encoding rather than mocking the failure is deliberate: this then
    fails on any machine if the guard goes, the same way the banner test does.
    """
    probe = tmp_path / name
    probe.write_text("\n".join(lines) + "\n", encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = encoding
    return subprocess.run(
        [sys.executable, str(probe)],
        capture_output=True,
        encoding=encoding,
        errors="replace",
        env=env,
        cwd=str(tmp_path),
    )


def test_spinner_renders_on_a_stderr_that_cannot_encode_braille(tmp_path):
    """The spinner frames are braille, which cp1252 -- the ANSI codepage of a
    stock Windows install -- cannot encode. Writing one raised UnicodeEncodeError
    inside the spinner's daemon thread: the thread died with a traceback printed
    over the output, and the animation stopped for the rest of the run.
    """
    result = _run_probe(
        tmp_path,
        "spinner_probe.py",
        [
            "import sys, time",
            "from maigret.ai import _Spinner",
            "",
            "spinner = _Spinner('probe')",
            "spinner.start()",
            "time.sleep(0.3)",
            "spinner.stop()",
            "sys.stdout.write('FRAMES=' + ''.join(spinner._frames) + chr(10))",
            "sys.stdout.write('STILL_RUNNING=' + str(spinner._thread.is_alive()) + chr(10))",
            "sys.stdout.write('REACHED_END' + chr(10))",
        ],
        "cp1252",
    )

    assert result.returncode == 0, f"the spinner must not crash the run: stderr={result.stderr!r}"
    assert "REACHED_END" in result.stdout, f"stdout={result.stdout!r}"
    # The daemon thread swallows nothing: an encode failure surfaces as a
    # traceback on stderr and leaves the spinner dead for the rest of the run.
    assert "UnicodeEncodeError" not in result.stderr, f"stderr={result.stderr!r}"
    assert "Exception in thread" not in result.stderr, f"stderr={result.stderr!r}"
    # It still animates, using frames the stream can carry.
    assert "FRAMES=|/-\\" in result.stdout, f"stdout={result.stdout!r}"


def test_spinner_keeps_its_braille_when_the_stream_can_encode_it(tmp_path):
    """The frame set is chosen from the stream, not swapped unconditionally: a
    UTF-8 terminal must still get the original animation."""
    result = _run_probe(
        tmp_path,
        "spinner_utf8_probe.py",
        [
            "import sys",
            "from maigret.ai import _Spinner",
            "",
            "sys.stdout.write('FRAMES=' + ''.join(_Spinner('probe')._frames) + chr(10))",
        ],
        "utf-8",
    )

    assert result.returncode == 0, f"stderr={result.stderr!r}"
    braille = "".join(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
    assert f"FRAMES={braille}" in result.stdout, f"stdout={result.stdout!r}"
