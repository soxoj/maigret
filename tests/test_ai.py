"""Tests for maigret.ai terminal output."""

import io
import os
import subprocess
import sys

import pytest

from maigret.ai import _stream_response, _write_encodable


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


# --- the analysis itself, which goes to stdout --------------------------------

CYRILLIC = "Привет"


def cp1252(errors):
    """A real cp1252 text stream, so the codec decides rather than a mock."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors=errors)


def read_back(stream):
    stream.flush()
    return stream.buffer.getvalue().decode("cp1252")


def test_raw_write_to_a_cp1252_stdout_is_what_fails():
    """Pin the defect itself, so these tests fail if the platform changes.

    surrogateescape is what sys.stdout actually carries here, and it is not a
    guard against this: it rescues lone surrogates only, so an ordinary
    unencodable character still raises.
    """
    stream = cp1252("surrogateescape")

    with pytest.raises(UnicodeEncodeError):
        stream.write(CYRILLIC)
        stream.flush()


@pytest.mark.parametrize("errors", ["strict", "surrogateescape"])
def test_a_reply_outside_the_codepage_does_not_raise(errors):
    stream = cp1252(errors)

    _write_encodable(stream, CYRILLIC)

    assert read_back(stream) == "?" * len(CYRILLIC)


def test_a_reply_the_codepage_can_carry_is_written_unchanged():
    """The replacement is a fallback, not the normal path."""
    stream = cp1252("strict")

    _write_encodable(stream, "Ana Gómez, née Muñoz")

    assert read_back(stream) == "Ana Gómez, née Muñoz"


def test_a_stream_that_does_not_raise_is_left_to_its_own_handler():
    """The straight write comes first; replacement is only the recovery path.

    A backslashreplace stream -- which is what sys.stderr carries -- encodes
    without raising, so the helper must not reach for its fallback and flatten
    the escapes to '?'. Without this case, always replacing passes every other
    test here: the strings the codepage can carry round-trip unchanged, and the
    ones it cannot raise either way.
    """
    stream = cp1252("backslashreplace")

    _write_encodable(stream, CYRILLIC)

    assert read_back(stream) == CYRILLIC.encode("cp1252", "backslashreplace").decode("cp1252")
    assert "?" not in read_back(stream)


def test_streaming_an_international_reply_finishes(monkeypatch):
    """The end-to-end path. The exception propagated out of the coroutine and
    ended the analysis mid-sentence, with the earlier tokens left on screen.
    """
    import asyncio

    class FakeContent:
        def __aiter__(self):
            return self._lines()

        async def _lines(self):
            for token in ("Найден ", "профиль", " 完了"):
                yield b'data: {"choices":[{"delta":{"content":"' + token.encode() + b'"}}]}'
            yield b"data: [DONE]"

    class FakeResp:
        content = FakeContent()

    class FakeSpinner:
        def stop(self):
            pass

    stream = cp1252("surrogateescape")
    monkeypatch.setattr(sys, "stdout", stream)

    _, analysis = asyncio.run(_stream_response(FakeResp(), FakeSpinner(), first_token=True))

    # The value handed back to the caller is the real text; only the terminal
    # copy is degraded to what the codepage can show.
    assert analysis == "Найден профиль 完了"
    assert "?" in read_back(stream)
