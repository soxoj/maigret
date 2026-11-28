"""Exercise AI analysis against a local OpenAI-compatible streaming endpoint."""

import asyncio
from unittest.mock import Mock

from aiohttp import web
import pytest

from maigret import ai


@pytest.mark.parametrize(
    "wire",
    [
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: [DONE]\n\n',
        b'data:{"choices":[{"delta":{"content":"Hello"}}]}\n\ndata:[DONE]\n\n',
        b'data: {"choices":\ndata: [{"delta":{"content":"Hello"}}]}\n\ndata: [DONE]\n\n',
        b': heartbeat\r\nevent: message\r\nid: 1\r\ndata:{"choices":[{"delta":{"content":"Hello"}}]}\r\n\r\ndata:[DONE]\r\n\r\n',
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: {"choices":[],"usage":{"total_tokens":1}}\n\ndata: [DONE]\n\n',
        b'data: {"choices":[{"delta":{"role":"assistant","content":""}}]}\n\ndata: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n',
        b'data: not-json\n\ndata: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: [DONE]\n\n',
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata:[DONE]\n\ndata: {"choices":[{"delta":{"content":"ignored"}}]}\n\n',
    ],
    ids=[
        "ordinary",
        "optional-space",
        "multiline-data",
        "fields-and-crlf",
        "usage-only-chunk",
        "role-and-finish",
        "malformed-event",
        "stop-at-done",
    ],
)
def test_local_stream_preserves_analysis(wire, monkeypatch, capsys):
    spinner = Mock()
    monkeypatch.setattr(ai, "_Spinner", Mock(return_value=spinner))

    async def run():
        async def completions(request):
            payload = await request.json()
            assert payload["stream"] is True
            assert payload["messages"][-1]["content"] == "Synthetic report"
            response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
            await response.prepare(request)
            for start in range(0, len(wire), 7):
                await response.write(wire[start : start + 7])
                await asyncio.sleep(0)
            await response.write_eof()
            return response

        app = web.Application()
        app.router.add_post("/v1/chat/completions", completions)
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            port = runner.addresses[0][1]
            return await ai.get_ai_analysis(
                "synthetic-test-key",
                "Synthetic report",
                api_base_url=f"http://127.0.0.1:{port}/v1",
            )
        finally:
            await runner.cleanup()

    assert asyncio.run(run()) == "Hello"
    assert capsys.readouterr().out == "\nHello\n"
    spinner.start.assert_called_once()
    spinner.stop.assert_called_once()


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        ([b'data: {"a":\n', b"data:1}\n", b"\n"], ['{"a":\n1}']),
        ([b"data: first\n", b"data:second\n", b"\n"], ["first", "second"]),
        ([b"data:  keep one space\n", b"\n"], [" keep one space"]),
        ([b": heartbeat\n", b"event: message\n", b"id: 5\n", b"\n"], []),
        ([b"data: incomplete\n"], ["incomplete"]),
        ([b"data: one\n", b"\n", b"data: two\n", b"\n"], ["one", "two"]),
        ([b" data: ignored\n", b"\n"], []),
    ],
    ids=[
        "join-json",
        "split-unframed-lines",
        "strip-one-space",
        "ignore-metadata",
        "flush-at-eof",
        "reset-between-events",
        "literal-field-name",
    ],
)
def test_event_framing(lines, expected):
    async def content():
        for line in lines:
            yield line

    async def read():
        return [event async for event in ai._stream_events(content())]

    assert asyncio.run(read()) == expected
