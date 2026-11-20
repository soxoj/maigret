"""Cookie-file delivery and isolation for TLS-impersonated profile checks."""

import asyncio
import logging
from unittest.mock import Mock

import pytest
from werkzeug.wrappers import Response

from maigret.checking import maigret
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretSite


def cookie_file(tmp_path, rows, name="cookies.txt"):
    path = tmp_path / name
    path.write_text("# Netscape HTTP Cookie File\n" + "\n".join(rows) + "\n")
    return path


def cookie_row(
    name="demo",
    value="present",
    domain="localhost",
    path="/",
    secure=False,
    expires="2147483647",
    include_subdomains=False,
):
    return "\t".join(
        [
            domain,
            "TRUE" if include_subdomains else "FALSE",
            path,
            "TRUE" if secure else "FALSE",
            expires,
            name,
            value,
        ]
    )


def local_url(httpserver, path):
    return httpserver.url_for(path).replace("127.0.0.1", "localhost")


async def scan(
    url, cookies=None, tls=True, username="local-demo", proxy=None, enrich=False
):
    site = MaigretSite(
        "Local",
        {
            "urlMain": url.rsplit("/", 1)[0],
            "url": url,
            "checkType": "status_code",
            "protection": ["tls_fingerprint"] if tls else [],
        },
    )
    result = await maigret(
        username,
        {site.name: site},
        logging.getLogger(__name__),
        query_notify=Mock(),
        cookies=str(cookies) if cookies is not None else None,
        proxy=proxy,
        is_enrich_enabled=enrich,
        no_progressbar=True,
        timeout=3,
    )
    return result[site.name]["status"]


@pytest.mark.asyncio
@pytest.mark.parametrize("tls", [False, True])
async def test_cookie_file_reaches_profile_transport(httpserver, tmp_path, tls):
    observed = []

    def gated(request):
        observed.append(dict(request.cookies))
        return Response(
            "profile", status=200 if request.cookies.get("demo") == "present" else 404
        )

    httpserver.expect_request("/profile").respond_with_handler(gated)
    cookies = cookie_file(tmp_path, [cookie_row()])
    result = await scan(local_url(httpserver, "/profile"), cookies=cookies, tls=tls)
    assert observed == [{"demo": "present"}]
    assert result.status == MaigretCheckStatus.CLAIMED


@pytest.mark.asyncio
async def test_curl_cookie_domains_and_paths_are_scoped(httpserver, tmp_path):
    observed = []

    def capture(request):
        observed.append(dict(request.cookies))
        return Response("profile")

    httpserver.expect_request("/profile/user").respond_with_handler(capture)
    cookies = cookie_file(
        tmp_path,
        [
            cookie_row(),
            cookie_row("path_cookie", "yes", path="/profile"),
            cookie_row("other_path", "no", path="/elsewhere"),
            cookie_row("foreign", "no", domain="foreign.test"),
        ],
    )
    await scan(local_url(httpserver, "/profile/user"), cookies=cookies)
    assert observed == [{"demo": "present", "path_cookie": "yes"}]


@pytest.mark.asyncio
async def test_curl_does_not_forward_cookies_to_other_redirect_host(
    httpserver, tmp_path
):
    observed = []

    def first(request):
        observed.append(dict(request.cookies))
        destination = httpserver.url_for("/destination").replace(
            "localhost", "127.0.0.1"
        )
        return Response(status=302, headers={"Location": destination})

    def last(request):
        observed.append(dict(request.cookies))
        return Response("profile")

    httpserver.expect_request("/profile").respond_with_handler(first)
    httpserver.expect_request("/destination").respond_with_handler(last)
    cookies = cookie_file(tmp_path, [cookie_row()])
    await scan(local_url(httpserver, "/profile"), cookies=cookies)
    assert observed == [{"demo": "present"}, {}]


@pytest.mark.asyncio
async def test_curl_rechecks_cookie_path_on_redirect(httpserver, tmp_path):
    observed = []

    def first(request):
        observed.append(dict(request.cookies))
        return Response(
            status=302, headers={"Location": local_url(httpserver, "/other/user")}
        )

    def last(request):
        observed.append(dict(request.cookies))
        return Response("profile")

    httpserver.expect_request("/profile/user").respond_with_handler(first)
    httpserver.expect_request("/other/user").respond_with_handler(last)
    cookies = cookie_file(
        tmp_path,
        [
            cookie_row(),
            cookie_row("profile", "one", path="/profile"),
            cookie_row("other", "two", path="/other"),
        ],
    )
    await scan(local_url(httpserver, "/profile/user"), cookies=cookies)
    assert observed == [
        {"demo": "present", "profile": "one"},
        {"demo": "present", "other": "two"},
    ]


@pytest.mark.asyncio
async def test_cookie_files_remain_isolated_between_concurrent_scans(
    httpserver, tmp_path
):
    observed = {}

    def capture(request):
        observed[request.path] = dict(request.cookies)
        return Response("profile")

    httpserver.expect_request("/one").respond_with_handler(capture)
    httpserver.expect_request("/two").respond_with_handler(capture)
    one = cookie_file(tmp_path, [cookie_row(value="one")], name="one.txt")
    two = cookie_file(tmp_path, [cookie_row(value="two")], name="two.txt")
    await asyncio.gather(
        scan(local_url(httpserver, "/one"), cookies=one),
        scan(local_url(httpserver, "/two"), cookies=two),
    )
    assert observed == {"/one": {"demo": "one"}, "/two": {"demo": "two"}}


@pytest.mark.asyncio
async def test_curl_without_cookie_file_still_has_no_supplied_cookie(httpserver):
    observed = []

    def capture(request):
        observed.append(dict(request.cookies))
        return Response("profile")

    httpserver.expect_request("/profile").respond_with_handler(capture)
    result = await scan(local_url(httpserver, "/profile"))
    assert result.status == MaigretCheckStatus.CLAIMED
    assert observed == [{}]


@pytest.mark.asyncio
async def test_curl_native_jar_respects_secure_and_expiry_over_local_proxy(
    httpserver, tmp_path
):
    observed = []

    def capture(request):
        observed.append((request.host, dict(request.cookies)))
        return Response('profile')

    httpserver.expect_request('/profile').respond_with_handler(capture)
    domain = 'profile.example.test'
    cookies = cookie_file(
        tmp_path,
        [
            cookie_row(domain=domain),
            cookie_row('secure_only', 'no', domain=domain, secure=True),
            cookie_row('expired', 'no', domain=domain, expires='1'),
        ],
    )
    # The local server is the HTTP proxy. No DNS resolution or request to the
    # reserved target hostname occurs outside this process's local test server.
    result = await scan(
        'http://profile.example.test/profile',
        cookies=cookies,
        proxy=httpserver.url_for('/'),
    )
    assert result.status == MaigretCheckStatus.CLAIMED
    assert observed == [('profile.example.test', {'demo': 'present'})]


@pytest.mark.asyncio
async def test_curl_preserves_host_only_vs_domain_cookies_on_redirect(
    httpserver, tmp_path
):
    observed = []

    def capture(request):
        observed.append((request.host, dict(request.cookies)))
        if request.host == 'profile.example.test':
            return Response(
                status=302,
                headers={'Location': 'http://sub.profile.example.test/profile'},
            )
        return Response('profile')

    httpserver.expect_request('/profile').respond_with_handler(capture)
    cookies = cookie_file(
        tmp_path,
        [
            cookie_row('host_only', 'one', domain='profile.example.test'),
            cookie_row(
                'domain_cookie', 'two', domain='.example.test', include_subdomains=True
            ),
        ],
    )
    await scan(
        'http://profile.example.test/profile',
        cookies=cookies,
        proxy=httpserver.url_for('/'),
    )
    assert observed == [
        ('profile.example.test', {'host_only': 'one', 'domain_cookie': 'two'}),
        ('sub.profile.example.test', {'domain_cookie': 'two'}),
    ]


@pytest.mark.asyncio
async def test_curl_retains_cookie_file_and_server_cookie_for_enrichment(
    httpserver, tmp_path, monkeypatch
):
    from maigret import checking

    observed = []

    def primary(request):
        observed.append(dict(request.cookies))
        return Response('profile', headers={'Set-Cookie': 'added=two; Path=/'})

    def secondary(request):
        observed.append(dict(request.cookies))
        return Response('extra data')

    httpserver.expect_request('/profile').respond_with_handler(primary)
    httpserver.expect_request('/secondary').respond_with_handler(secondary)
    monkeypatch.setattr(
        checking, 'mutate_url', lambda url: [(local_url(httpserver, '/secondary'), {})]
    )
    cookies = cookie_file(tmp_path, [cookie_row()])
    await scan(local_url(httpserver, '/profile'), cookies=cookies, enrich=True)
    assert observed == [{'demo': 'present'}, {'demo': 'present', 'added': 'two'}]
