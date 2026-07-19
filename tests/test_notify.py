from colorama import Fore, Style

from maigret.errors import CheckError
from maigret.notify import QueryNotifyPrint
from maigret.result import MaigretCheckStatus, MaigretCheckResult


def test_notify_illegal():
    n = QueryNotifyPrint(color=False)

    assert (
        n.update(
            MaigretCheckResult(
                username="test",
                status=MaigretCheckStatus.ILLEGAL,
                site_name="TEST_SITE",
                site_url_user="http://example.com/test",
            )
        )
        == "[-] TEST_SITE: Illegal Username Format For This Site!"
    )


def test_notify_claimed():
    n = QueryNotifyPrint(color=False)

    assert (
        n.update(
            MaigretCheckResult(
                username="test",
                status=MaigretCheckStatus.CLAIMED,
                site_name="TEST_SITE",
                site_url_user="http://example.com/test",
            )
        )
        == "[+] TEST_SITE: http://example.com/test"
    )


def test_notify_available():
    n = QueryNotifyPrint(color=False)

    assert (
        n.update(
            MaigretCheckResult(
                username="test",
                status=MaigretCheckStatus.AVAILABLE,
                site_name="TEST_SITE",
                site_url_user="http://example.com/test",
            )
        )
        == "[-] TEST_SITE: Not found!"
    )


def test_notify_unknown():
    n = QueryNotifyPrint(color=False)
    result = MaigretCheckResult(
        username="test",
        status=MaigretCheckStatus.UNKNOWN,
        site_name="TEST_SITE",
        site_url_user="http://example.com/test",
    )
    result.error = CheckError('Type', 'Reason')

    assert n.update(result) == "[?] TEST_SITE: Type error: Reason"


# `warning(message, symbol, advice=None)` was added so that the "Too many
# errors..." summary can render the count line bold and the advice in
# normal weight. The pieces must stay visually distinct because the advice
# is multi-line guidance, not part of the alarm.


def _capture_warning_string(monkeypatch, **warning_kwargs):
    """Patch builtins.print so we capture the *exact* string warning passed —
    independent of colorama's terminal/TTY heuristics, which strip ANSI in
    capsys mode. We care about what notify generated, not what colorama
    decided to do with it on a captured pipe."""
    captured = []
    import builtins
    monkeypatch.setattr(builtins, 'print', lambda *a, **kw: captured.append(a[0] if a else ''))
    n = QueryNotifyPrint(color=warning_kwargs.pop('color', True))
    n.warning(**warning_kwargs)
    assert captured, "warning() did not call print()"
    return captured[0]


def test_warning_no_advice_renders_as_single_yellow_bold_line(monkeypatch):
    out = _capture_warning_string(
        monkeypatch, color=True, message='something happened', symbol='!',
    )
    # Existing behaviour preserved for the no-advice path
    assert out == Style.BRIGHT + Fore.YELLOW + '[!] something happened'


def test_warning_with_advice_keeps_header_bold_and_advice_normal(monkeypatch):
    """Advice must come after Style.NORMAL so terminals stop boldfacing it.
    The Fore.YELLOW colour stays — the visual cue is weight, not colour."""
    out = _capture_warning_string(
        monkeypatch, color=True, message='count line', symbol='!', advice='do the thing',
    )
    # Header is bold...
    assert out.startswith(Style.BRIGHT + Fore.YELLOW + '[!] count line')
    # ...advice is preceded by Style.NORMAL so the boldface ends before it
    assert Style.NORMAL + '. do the thing' in out
    # ...and the whole line resets all SGR state at the end so no styling
    # leaks into the next print
    assert out.endswith(Style.RESET_ALL)


def test_warning_with_advice_no_color_uses_plain_dot_separator(monkeypatch):
    """In no-colour mode the visual distinction is impossible to render, so
    a plain ". " separator between the count line and the advice is enough.
    No ANSI codes must leak into the output."""
    out = _capture_warning_string(
        monkeypatch, color=False, message='count line', symbol='!', advice='do the thing',
    )
    assert out == '[!] count line. do the thing'
    # Defence in depth: no escape codes survived the no-colour branch
    assert '\x1b[' not in out


def _capture_print(monkeypatch):
    captured = []
    import builtins
    monkeypatch.setattr(builtins, 'print', lambda *a, **kw: captured.append(a[0] if a else ''))
    return captured


def _capture_stdout_writes(monkeypatch):
    """Capture both sys.stdout.write and print — enrich() writes a bare
    line-clear escape via stdout.write and then calls print for the message."""
    import builtins, sys
    captured = []
    monkeypatch.setattr(builtins, 'print', lambda *a, **kw: captured.append(a[0] if a else ''))
    monkeypatch.setattr(sys.stdout, 'write', lambda s: captured.append(('write', s)))
    return captured


def test_enrich_uses_magenta_and_star_symbol(monkeypatch):
    captured = _capture_print(monkeypatch)
    QueryNotifyPrint(color=True).enrich('hello')
    assert Style.BRIGHT + Fore.MAGENTA + '[*] hello' in captured


def test_enrich_no_color_is_plain(monkeypatch):
    captured = _capture_print(monkeypatch)
    QueryNotifyPrint(color=False).enrich('hello')
    assert '[*] hello' in captured
    assert all('\x1b[' not in c for c in captured)


def test_enrich_writes_line_clear_before_print(monkeypatch):
    """Clears the alive_progress 'on N:' prefix from the current line before printing.

    Colorama strips the ANSI escape when stdout looks non-TTY (monkeypatched
    stdout does), collapsing '\\x1b[1K\\r' to '\\r'. Either form is a valid
    line-clear signal to the terminal, so accept both."""
    captured = _capture_stdout_writes(monkeypatch)
    QueryNotifyPrint(color=False).enrich('hello')
    op, text = captured[0]
    assert op == 'write'
    assert text in ('\x1b[1K\r', '\r')
    assert '[*] hello' in captured


def test_enrich_verbose_only_hidden_by_default(monkeypatch):
    captured = _capture_print(monkeypatch)
    QueryNotifyPrint(color=False, verbose=False).enrich('diagnostic', verbose_only=True)
    assert captured == []


def test_enrich_verbose_only_shown_when_verbose(monkeypatch):
    captured = _capture_print(monkeypatch)
    QueryNotifyPrint(color=False, verbose=True).enrich('diagnostic', verbose_only=True)
    assert '[*] diagnostic' in captured




def _claimed_result_with_ids(ids_data):
    r = MaigretCheckResult(
        username="u", site_name="S", site_url_user="https://s/u",
        status=MaigretCheckStatus.CLAIMED,
    )
    r.ids_data = ids_data
    return r


def test_update_hides_extractor_field_by_default(monkeypatch):
    captured = _capture_print(monkeypatch)
    n = QueryNotifyPrint(color=False, verbose=False)
    n.update(_claimed_result_with_ids({"uid": "42", "_extractor": "SomeSchemeAPI"}))
    out = "\n".join(captured)
    assert "uid: 42" in out
    assert "_extractor" not in out


def test_update_shows_extractor_field_when_verbose(monkeypatch):
    captured = _capture_print(monkeypatch)
    n = QueryNotifyPrint(color=False, verbose=True)
    n.update(_claimed_result_with_ids({"uid": "42", "_extractor": "SomeSchemeAPI"}))
    out = "\n".join(captured)
    assert "uid: 42" in out
    assert "_extractor: SomeSchemeAPI" in out
