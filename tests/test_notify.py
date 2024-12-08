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
