import json
from pathlib import Path

DATA_JSON = Path(__file__).resolve().parents[1] / "maigret" / "resources" / "data.json"


def _sites():
    with DATA_JSON.open(encoding="utf-8") as f:
        return json.load(f)["sites"]


def test_opensea_checks_profile_title_not_status_code():
    """OpenSea serves HTTP 200 for missing usernames; require the profile title."""
    site = _sites()["OpenSea"]
    assert site["checkType"] == "message"
    assert " - Profile | OpenSea" in site["presenseStrs"]
