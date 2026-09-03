"""Tests for AI module non-UTF-8 stream encoding support."""

import os
import subprocess
import sys
import textwrap


def test_ai_spinner_and_streaming_survive_cp1252(tmp_path):
    """The AI spinner uses braille characters that cp1252 cannot encode.
    When sys.stderr is cp1252, _Spinner must gracefully switch to ASCII frames
    and must not crash daemon thread or print UnicodeEncodeError tracebacks.
    """
    probe = tmp_path / "ai_probe.py"
    probe.write_text(
        textwrap.dedent(
            """
            import asyncio
            import time
            from maigret.ai import _Spinner, print_streaming

            # Test spinner on cp1252 stderr
            spinner = _Spinner("Analyzing with AI...")
            assert spinner._frames == spinner.ASCII_FRAMES, (
                f"Expected ASCII frames, got {spinner._frames}"
            )
            spinner.start()
            time.sleep(0.3)
            spinner.stop()

            # Test streaming on cp1252 stdout
            asyncio.run(print_streaming(
                "AI response with unicode: ⠋ → ♥ complete",
                delay=0.01,
            ))
            """
        ),
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"
    result = subprocess.run(
        [sys.executable, str(probe)],
        capture_output=True,
        encoding="cp1252",
        errors="replace",
        env=env,
        cwd=str(tmp_path),
    )

    assert result.returncode == 0, (
        f"AI spinner/streaming must not crash on cp1252: "
        f"stderr={result.stderr!r}"
    )
    assert "Exception in thread" not in result.stderr
    assert "UnicodeEncodeError" not in result.stderr
    assert "AI response with unicode" in result.stdout
