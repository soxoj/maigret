from unittest.mock import Mock

from maigret.errors import CheckError
from maigret.notify import QueryNotifyPrint
from maigret.result import MaigretCheckStatus, MaigretCheckResult, KeywordMatchStatus
from maigret.sites import MaigretSite
from maigret.checking import process_site_result


def test_keyword_match_status_enum():
    assert KeywordMatchStatus.NO_KEYWORDS.value == "No Keywords"
    assert KeywordMatchStatus.KEYWORD_FOUND.value == "Keyword Found"
    assert KeywordMatchStatus.KEYWORDS_NOT_FOUND.value == "Keywords Not Found"
    assert str(KeywordMatchStatus.NO_KEYWORDS) == "No Keywords"
    assert str(KeywordMatchStatus.KEYWORD_FOUND) == "Keyword Found"
    assert str(KeywordMatchStatus.KEYWORDS_NOT_FOUND) == "Keywords Not Found"


def test_result_default_keyword_fields():
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
    )
    assert result.keywords == []
    assert result.keyword_match_status == KeywordMatchStatus.NO_KEYWORDS


def test_result_with_keywords_no_match():
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
        keywords=["nothing"],
        keyword_match_status=KeywordMatchStatus.KEYWORDS_NOT_FOUND,
    )
    assert result.keywords == ["nothing"]
    assert result.keyword_match_status == KeywordMatchStatus.KEYWORDS_NOT_FOUND


def test_result_with_keywords_match():
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
        keywords=["tech", "python"],
        keyword_match_status=KeywordMatchStatus.KEYWORD_FOUND,
    )
    assert result.keywords == ["tech", "python"]
    assert result.keyword_match_status == KeywordMatchStatus.KEYWORD_FOUND
    assert result.is_found() is True


def test_result_json_includes_keywords():
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
        keywords=["tech"],
        keyword_match_status=KeywordMatchStatus.KEYWORD_FOUND,
    )
    data = result.json()
    assert data["keywords"] == ["tech"]
    assert data["keyword_match_status"] == "Keyword Found"


def test_notify_claimed_keyword_match():
    n = QueryNotifyPrint(color=False)
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
        keywords=["tech"],
        keyword_match_status=KeywordMatchStatus.KEYWORD_FOUND,
    )
    assert n.update(result) == "[++] SITE: http://example.com/test"


def test_notify_claimed_no_keywords():
    n = QueryNotifyPrint(color=False)
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
        keywords=[],
        keyword_match_status=KeywordMatchStatus.NO_KEYWORDS,
    )
    assert n.update(result) == "[+] SITE: http://example.com/test"


def test_notify_claimed_keywords_not_found():
    n = QueryNotifyPrint(color=False)
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
        keywords=["nonexistent"],
        keyword_match_status=KeywordMatchStatus.KEYWORDS_NOT_FOUND,
    )
    assert n.update(result) == "[+] SITE: http://example.com/test"


def test_notify_available():
    n = QueryNotifyPrint(color=False)
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.AVAILABLE,
    )
    assert n.update(result) == "[-] SITE: Not found!"


def test_notify_unknown():
    n = QueryNotifyPrint(color=False)
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.UNKNOWN,
    )
    result.error = CheckError("Type", "Reason")
    assert n.update(result) == "[?] SITE: Type error: Reason"


# ---------------------------------------------------------------------------
# Integration tests — exercise the keyword detection block inside
# process_site_result with real ``html_text`` and a MaigretSite object.
# ---------------------------------------------------------------------------

def _make_site(data_overrides=None):
    base = {
        "url": "https://x/{username}",
        "urlMain": "https://x",
        "checkType": "status_code",
        "usernameClaimed": "a",
        "usernameUnclaimed": "b",
    }
    if data_overrides:
        base.update(data_overrides)
    return MaigretSite("TestSite", base)


def test_process_site_result_no_keywords_yields_no_keywords():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a", "keywords": []}
    out = process_site_result(("python developer", 200, None), Mock(), Mock(), info, site)
    assert out["status"].keyword_match_status == KeywordMatchStatus.NO_KEYWORDS


def test_process_site_result_keyword_found_in_html():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a", "keywords": ["python"]}
    out = process_site_result(("I love python programming", 200, None), Mock(), Mock(), info, site)
    assert out["status"].keyword_match_status == KeywordMatchStatus.KEYWORD_FOUND


def test_process_site_result_keyword_not_found_in_html():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a", "keywords": ["python"]}
    out = process_site_result(("I love rust programming", 200, None), Mock(), Mock(), info, site)
    assert out["status"].keyword_match_status == KeywordMatchStatus.KEYWORDS_NOT_FOUND


def test_process_site_result_keyword_case_insensitive():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a", "keywords": ["Python"]}
    out = process_site_result(("I love python programming", 200, None), Mock(), Mock(), info, site)
    assert out["status"].keyword_match_status == KeywordMatchStatus.KEYWORD_FOUND


def test_process_site_result_empty_html_yields_no_keywords():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a", "keywords": ["python"]}
    out = process_site_result(("", 200, None), Mock(), Mock(), info, site)
    assert out["status"].keyword_match_status == KeywordMatchStatus.NO_KEYWORDS


def test_process_site_result_keywords_one_of_many_found():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a", "keywords": ["rust", "python"]}
    out = process_site_result(("I love rust programming", 200, None), Mock(), Mock(), info, site)
    assert out["status"].keyword_match_status == KeywordMatchStatus.KEYWORD_FOUND
