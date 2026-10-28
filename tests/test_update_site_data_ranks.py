"""Tests for the rank sources of utils.update_site_data (no network calls)."""

import utils.update_site_data as update_site_data


class _FakeResponse:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_netapi_top1m_parses_rank_and_domain(monkeypatch):
    csv_text = "NetAPI_Rank,Domain\n1,google.com\n533,Letras.mus.br\n\n"
    monkeypatch.setattr(
        update_site_data.requests,
        "get",
        lambda url, stream=True: _FakeResponse(csv_text),
    )

    ranks = update_site_data.fetch_netapi_top1m()

    assert ranks == {"google.com": 1, "letras.mus.br": 533}


def test_fetch_netapi_top1m_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setattr(
        update_site_data.requests,
        "get",
        lambda url, stream=True: _FakeResponse("", status=503),
    )

    assert update_site_data.fetch_netapi_top1m() == {}
