"""A failed DNS query is not evidence that a domain is available."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import aiodns
import pytest

from maigret import checking, errors
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretSite


@pytest.fixture
def resolver(monkeypatch):
    stub = SimpleNamespace(query=AsyncMock())
    monkeypatch.setattr(checking.aiodns, "DNSResolver", lambda **kwargs: stub)
    return stub


def domain_site():
    return MaigretSite(
        "Domain",
        {
            "url": "{username}.example.test",
            "protocol": "dns",
            "checkType": "status_code",
        },
    )


async def search(retries=0, check_domains=True):
    return await checking.maigret(
        "synthetic",
        {"Domain": domain_site()},
        logging.getLogger(__name__),
        query_notify=Mock(),
        no_progressbar=True,
        check_domains=check_domains,
        retries=retries,
        timeout=1,
    )


@pytest.mark.parametrize(
    "code",
    [
        aiodns.error.ARES_ETIMEOUT,
        aiodns.error.ARES_ESERVFAIL,
        aiodns.error.ARES_EREFUSED,
        aiodns.error.ARES_ECONNREFUSED,
        aiodns.error.ARES_EBADRESP,
    ],
)
async def test_resolver_failures_are_unknown_and_retryable(resolver, code):
    resolver.query.side_effect = aiodns.error.DNSError(
        code, "synthetic resolver failure"
    )
    results = await search()
    status = results["Domain"]["status"]
    assert status.status == MaigretCheckStatus.UNKNOWN
    assert status.error.type == "DNS query failed"
    assert "synthetic resolver failure" in status.error.desc
    assert results["Domain"]["http_status"] == 0
    assert checking.get_failed_sites(results) == ["Domain"]
    resolver.query.assert_awaited_once_with("synthetic.example.test", "A")


@pytest.mark.parametrize(
    "code",
    [
        aiodns.error.ARES_ENOTFOUND,
        aiodns.error.ARES_ENODATA,
        aiodns.error.ARES_EBADNAME,
    ],
)
async def test_absent_or_invalid_name_keeps_existing_negative_result(resolver, code):
    resolver.query.side_effect = aiodns.error.DNSError(code, "synthetic absence")
    results = await search(retries=2)
    status = results["Domain"]["status"]
    assert status.status == MaigretCheckStatus.AVAILABLE
    assert status.error is None
    assert results["Domain"]["http_status"] == 404
    assert checking.get_failed_sites(results) == []
    assert resolver.query.await_count == 1


async def test_retry_recovers_a_domain_after_resolver_outage(resolver):
    resolver.query.side_effect = [
        aiodns.error.DNSError(aiodns.error.ARES_ETIMEOUT, "synthetic timeout"),
        [SimpleNamespace(host="192.0.2.1")],
    ]
    results = await search(retries=1)
    status = results["Domain"]["status"]
    assert status.status == MaigretCheckStatus.CLAIMED
    assert status.error is None
    assert resolver.query.await_count == 2


async def test_retry_exhaustion_keeps_domain_unknown(resolver):
    resolver.query.side_effect = aiodns.error.DNSError(
        aiodns.error.ARES_ESERVFAIL, "synthetic outage"
    )
    results = await search(retries=1)
    assert results["Domain"]["status"].status == MaigretCheckStatus.UNKNOWN
    assert resolver.query.await_count == 2


async def test_successful_a_record_keeps_existing_positive_result(resolver):
    resolver.query.return_value = [SimpleNamespace(host="192.0.2.1")]
    results = await search()
    assert results["Domain"]["status"].status == MaigretCheckStatus.CLAIMED
    assert results["Domain"]["http_status"] == 200
    assert results["Domain"]["status"].error is None


async def test_domain_checks_remain_opt_in(resolver):
    results = await search(check_domains=False)
    assert results["Domain"]["status"].status == MaigretCheckStatus.ILLEGAL
    resolver.query.assert_not_awaited()


def test_domain_query_advice_does_not_offer_http_only_resolver_flag():
    advice = errors.solution_of("DNS query failed")
    assert "domain" in advice
    assert "--dns-resolver" not in advice
    assert not errors.is_permanent("DNS query failed")
