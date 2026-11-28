"""--cookies-jar-file must not escape as a traceback when the path cannot be read."""

import logging

import pytest


@pytest.mark.parametrize('cookie_path', ['/nope/cookies.txt', '/tmp'])
@pytest.mark.asyncio
async def test_cli_rejects_unreadable_cookie_file(cookie_path, tmp_path, monkeypatch, capsys):
    """A missing or non-regular --cookies-jar-file must exit 2 with a one-line error.

    ``import_aiohttp_cookies()`` used to let ``FileNotFoundError`` /
    ``IsADirectoryError`` escape from ``MozillaCookieJar.load()``, so a typo in
    the flag produced a 20-frame traceback instead of the ``can't read ...``
    message the other file-path options already print.
    """
    from maigret import maigret as cli

    monkeypatch.setattr(logging.getLogger('maigret'), 'level', logging.NOTSET)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        'sys.argv',
        ['maigret', 'alice', '--cookies-jar-file', cookie_path, '--no-color'],
    )

    with pytest.raises(SystemExit) as exc:
        await cli.main()

    assert exc.value.code == 2
    assert f"can't read cookie file: {cookie_path}" in capsys.readouterr().err
