"""Activation routing through local HTTP CONNECT and SOCKS5 peers."""

import asyncio
import json
from types import SimpleNamespace
from urllib.parse import urlsplit
from unittest.mock import Mock

import pytest

from maigret.checking import CurlCffiChecker, SimpleAiohttpChecker, check_site_for_username
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretSite


@pytest.fixture(params=['http', 'socks5', 'socks5h'])
async def proxy_peer(request: pytest.FixtureRequest):
    peer = SimpleNamespace(requests=[], activation_status=200, connect_status=200)
    connections = set()

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        connections.add(task)
        try:
            if request.param != 'http':
                _, count = await reader.readexactly(2)
                await reader.readexactly(count)
                writer.write(b'\x05\x00')
                await writer.drain()
                assert await reader.readexactly(4) == b'\x05\x01\x00\x03'
                size = (await reader.readexactly(1))[0]
                await reader.readexactly(size + 2)
                writer.write(b'\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x50')
                await writer.drain()
            raw = await reader.readuntil(b'\r\n\r\n')
            if raw.startswith(b'CONNECT '):
                writer.write(f'HTTP/1.1 {peer.connect_status} Tunnel\r\n\r\n'.encode())
                await writer.drain()
                if peer.connect_status != 200:
                    return
                raw = await reader.readuntil(b'\r\n\r\n')
            lines = raw.decode().split('\r\n')
            method, target, _ = lines[0].split(' ')
            headers = dict(line.split(': ', 1) for line in lines[1:] if ': ' in line)
            headers = {key.lower(): value for key, value in headers.items()}
            await reader.readexactly(int(headers.get('content-length', '0')))
            path = urlsplit(target).path
            peer.requests.append((method, path, headers))
            status, extra = 200, ''
            if path == '/activate':
                status, body = 302, ''
                extra = 'Location: http://redirect.invalid/token\r\n'
            elif path == '/token':
                status = peer.activation_status
                body = json.dumps({'guest_token': 'secret-token', 'jwt': 'secret-token',
                                   'UID': 'uid', 'AccessToken': 'secret-token',
                                   'data': {'sub': 'secret-token', 'subp': 'subp'}})
                extra = 'Set-Cookie: session=secret-token; Path=/\r\n'
            else:
                body = 'PROFILE' if 'secret-token' in str(headers) else 'CHALLENGE'
            writer.write(
                f'HTTP/1.1 {status} Test\r\nContent-Type: application/json\r\n'
                f'Content-Length: {len(body)}\r\nConnection: close\r\n{extra}\r\n{body}'.encode()
            )
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            connections.discard(task)

    server = await asyncio.start_server(handle, '127.0.0.1', 0)
    peer.url = f'{request.param}://127.0.0.1:{server.sockets[0].getsockname()[1]}'
    try:
        yield peer
    finally:
        server.close()
        await server.wait_closed()
        tasks = list(connections)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def make_site(method: str) -> MaigretSite:
    return MaigretSite('Local', {
        'url': 'http://profile.invalid/{username}', 'urlMain': 'http://profile.invalid',
        'checkType': 'message', 'presenseStrs': ['PROFILE'], 'headers': {},
        'activation': {'method': method, 'url': 'http://activation.invalid/activate',
                       'marks': ['CHALLENGE'], 'src': 'guest_token', 'static_param': 'static',
                       'checksum_indexes': [0, 1], 'checksum_constant': 0, 'format': '{}:{:x}'},
    })


async def check(site: MaigretSite, proxy: str, checker_type: type = SimpleAiohttpChecker):
    options = {
        'proxy': proxy, 'checkers': {site.protocol: lambda: checker_type(proxy=proxy, logger=Mock())},
        'parsing': False, 'forced': True, 'id_type': 'username', 'timeout': 1,
    }
    return (await check_site_for_username(site, 'alice', options, Mock(), Mock()))[1]


@pytest.mark.parametrize('method', ['twitter', 'vimeo', 'onlyfans', 'proton', 'weibo'])
@pytest.mark.parametrize('checker_type', [SimpleAiohttpChecker, CurlCffiChecker])
async def test_profile_activation_redirect_and_retry_share_route(
    proxy_peer: SimpleNamespace, method: str, checker_type: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('http_proxy', 'http://127.0.0.1:1')
    monkeypatch.setenv('NO_PROXY', '*')
    monkeypatch.setenv('no_proxy', '*')
    site = make_site(method)
    result = await check(site, proxy_peer.url, checker_type)
    assert result['status'].status == MaigretCheckStatus.CLAIMED
    assert [row[1] for row in proxy_peer.requests] == ['/alice', '/activate', '/token', '/alice']
    assert 'secret-token' in str(proxy_peer.requests[-1][2])
    assert site.headers == {}  # Routed activation must not mutate a shared database.


@pytest.mark.parametrize('status', [403, 407])
async def test_failed_activation_is_unknown(proxy_peer: SimpleNamespace, status: int) -> None:
    proxy_peer.activation_status = status
    result = await check(make_site('twitter'), proxy_peer.url)
    assert result['status'].status == MaigretCheckStatus.UNKNOWN
    assert result['status'].error.type == 'Activation'
    assert [row[1] for row in proxy_peer.requests] == ['/alice', '/activate', '/token']


@pytest.mark.parametrize('protocol', ['tor', 'i2p'])
async def test_activation_uses_checker_route_not_clearweb_option(
    proxy_peer: SimpleNamespace, protocol: str
) -> None:
    site = make_site('twitter')
    site.protocol = protocol
    options = {'proxy': 'http://127.0.0.1:1',
               'checkers': {protocol: lambda: SimpleAiohttpChecker(proxy=proxy_peer.url)},
               'parsing': False, 'forced': True, 'id_type': 'username', 'timeout': 1}
    _, result = await check_site_for_username(site, 'alice', options, Mock(), Mock())
    assert result['status'].status == MaigretCheckStatus.CLAIMED
    assert len(proxy_peer.requests) == 4


@pytest.mark.parametrize('proxy_peer', ['http'], indirect=True)
@pytest.mark.parametrize('status', [403, 407])
@pytest.mark.parametrize('checker_type', [SimpleAiohttpChecker, CurlCffiChecker])
async def test_connect_failure_is_not_a_site_response(
    proxy_peer: SimpleNamespace, status: int, checker_type: type
) -> None:
    proxy_peer.connect_status = status
    checker = checker_type(proxy=proxy_peer.url)
    checker.prepare('https://profile.invalid/alice', timeout=1)
    html, code, error = await checker.check()
    assert error is not None and code == 0 and not html
    assert proxy_peer.requests == []


@pytest.mark.parametrize('checker_type', [SimpleAiohttpChecker, CurlCffiChecker])
async def test_unsupported_proxy_is_rejected(checker_type: type) -> None:
    with pytest.raises(ValueError, match='Unsupported proxy scheme'):
        checker_type(proxy='ftp://127.0.0.1:1')
