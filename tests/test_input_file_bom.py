import io

import pytest

from maigret.utils import read_input_file

SUPPORTED_IDS = ("username", "vk_id", "gaia_id", "steam_id")


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize(
    "body, expected",
    [
        ("alice\n", [("alice", None)]),
        ("vk_id:123\n", [("123", "vk_id")]),
        ("# comment\nalice\n", [("alice", None)]),
        ("\n# comment\nalice\n", [("alice", None)]),
        ("", []),
    ],
)
def test_read_input_file_skips_leading_utf8_bom(
    source, body, expected, tmp_path, monkeypatch
):
    text = "\ufeff" + body
    if source == "stdin":
        monkeypatch.setattr("sys.stdin", io.StringIO(text))
        path = "-"
    else:
        names = tmp_path / "names.txt"
        names.write_bytes(text.encode("utf-8"))
        path = str(names)

    assert read_input_file(path, SUPPORTED_IDS) == expected


@pytest.mark.parametrize("source", ["file", "stdin"])
def test_read_input_file_preserves_embedded_bom(source, tmp_path, monkeypatch):
    text = "al\ufeffice\n"
    if source == "stdin":
        monkeypatch.setattr("sys.stdin", io.StringIO(text))
        path = "-"
    else:
        names = tmp_path / "names.txt"
        names.write_bytes(text.encode("utf-8"))
        path = str(names)

    assert read_input_file(path, SUPPORTED_IDS) == [("al\ufeffice", None)]
