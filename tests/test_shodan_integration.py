import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SHODAN_API_KEY"),
    reason="No SHODAN_API_KEY: integration skipped"
)

from maigret_sites_example.shodan_checker import check

def test_shodan_integration_runs():
    # a light smoke test to ensure the checker runs with a real key
    res = check("github")  # arbitrary username to exercise the call
    assert isinstance(res, dict)
    assert "ids_usernames" in res
