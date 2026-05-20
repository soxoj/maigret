import pytest

from maigret.web.app import sanitize_username_for_path


@pytest.mark.parametrize(
    "input_username, expected",
    [
        ("../../tmp/x", "_.._tmp_x"),
        ("..", "_"),
        ("....", "_"),
        ("foo/bar", "foo_bar"),
        ("\0foo", "_foo"),
        ("normaluser123", "normaluser123"),
    ],
)
def test_sanitize_username_for_path(input_username, expected):
    result = sanitize_username_for_path(input_username)
    assert result == expected
    # Verify no path separators or null bytes remain
    assert "/" not in result
    assert "\\" not in result
    assert "\0" not in result
    # Verify result is not empty
    assert len(result) > 0
    # Verify no leading/trailing dots
    assert not result.startswith(".")
    assert not result.endswith(".")
