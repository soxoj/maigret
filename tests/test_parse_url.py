"""--parse must not let a requests error escape as a traceback."""

import logging

import pytest


@pytest.mark.parametrize(
    'parse_url',
    [
        'not a url',
        'example.com',
        'http://127.0.0.1:1/',
    ],
)
@pytest.mark.asyncio
async def test_cli_rejects_unfetchable_parse_url(parse_url, tmp_path, monkeypatch, capsys):
    """A malformed or unreachable --parse URL must exit 2 with a one-line error.

    ``extract_ids_from_page()`` calls ``socid_extractor.parse()``, which goes
    through ``requests``; ``InvalidURL`` / ``MissingSchema`` / ``ConnectionError``
    used to escape ``main()`` as a 20-frame traceback instead of the
    ``can't read ...`` style message the other URL and path options print.
    """
    from maigret import maigret as cli

    monkeypatch.setattr(logging.getLogger('maigret'), 'level', logging.NOTSET)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        'sys.argv',
        ['maigret', '--parse', parse_url, '--no-color'],
    )

    with pytest.raises(SystemExit) as exc:
        await cli.main()

    assert exc.value.code == 2
    assert f"can't parse page {parse_url}" in capsys.readouterr().err
