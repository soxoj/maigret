from maigret.errors import CheckError
from maigret.notify import QueryNotifyPrint
from maigret.result import MaigretCheckStatus, MaigretCheckResult, KeywordMatchStatus


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


def test_keyword_match_still_claimed():
    result = MaigretCheckResult(
        username="test",
        site_name="SITE",
        site_url_user="http://example.com/test",
        status=MaigretCheckStatus.CLAIMED,
        keywords=["tech"],
        keyword_match_status=KeywordMatchStatus.KEYWORD_FOUND,
    )
    assert result.is_found() is True
